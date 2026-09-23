"""Credential-optional grounded retrieval for Kisan Sahayak."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

CORPUS_PATH = Path(__file__).parent / "data" / "documents.jsonl"
load_dotenv(Path(__file__).parent.parent / ".env", override=False)
_DOCUMENTS: list[dict[str, Any]] | None = None
_SEARCH_STOP_WORDS = {
    "a", "an", "and", "are", "be", "been", "being", "for", "from",
    "how", "is", "of", "on", "the", "to", "was", "were", "what",
    "when", "where", "which", "who", "why", "available",
}
_TOKEN_ALIASES = {
    "pulses": "pulse", "schemes": "scheme", "subsidies": "subsidy",
    "documents": "document", "needed": "required",
}
_CROP_TERMS = {"rice", "pulse", "wheat", "millet", "cereal", "oilseed"}
_PM_KISAN_PORTAL = "https://pmkisan.gov.in/"
_PM_KISAN_DOCUMENT_GUIDANCE = (
    "Official PM-KISAN portal guidance: for new farmer registration, keep the farmer's "
    "Aadhaar number, land ownership or land-record details, bank account number and IFSC, "
    "and an active mobile number ready. eKYC is mandatory for registered farmers. "
    "State or UT verification may request additional records, so confirm the final checklist "
    "on the official registration page."
)


def _load_documents() -> list[dict[str, Any]]:
    global _DOCUMENTS
    if _DOCUMENTS is None:
        documents = []
        with CORPUS_PATH.open(encoding="utf-8") as corpus:
            for line in corpus:
                if line.strip():
                    documents.append(json.loads(line))
        _DOCUMENTS = documents
    return _DOCUMENTS


def _tokens(text: str) -> set[str]:
    return {
        _TOKEN_ALIASES.get(token, token)
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9-]+", text.lower())
        if len(token) > 2 and token not in _SEARCH_STOP_WORDS
    }


def _search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    query_tokens = _tokens(query)
    scored = []
    for document in _load_documents():
        content = str(document.get("page_content", ""))
        metadata = document.get("metadata") or {}
        scheme_name = str(metadata.get("scheme_name", ""))
        haystack = " ".join([content, scheme_name, str(metadata.get("scheme_category", ""))])
        overlap = query_tokens & _tokens(haystack)
        if overlap:
            scheme_overlap = query_tokens & _tokens(scheme_name)
            score = (len(overlap) / max(len(query_tokens), 1)) + (0.1 * len(scheme_overlap))
            topic_overlap = query_tokens & _CROP_TERMS & _tokens(content)
            scored.append((score + (0.25 * len(topic_overlap)), len(overlap), topic_overlap, document))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    requested_topics = query_tokens & _CROP_TERMS
    if len(requested_topics) > 1:
        complete_matches = [item for item in scored if requested_topics <= item[2]]
        if complete_matches:
            scored = complete_matches
    return [item[3] for item in scored[:limit]]


def _retrieval_query(query: str, language: str) -> str:
    """Translate Indic input for English corpus retrieval when Sarvam is available."""
    if language.casefold() in {"english", "en"} or query.isascii():
        return query
    language_codes = {
        "telugu": "te-IN", "hindi": "hi-IN", "tamil": "ta-IN",
        "kannada": "kn-IN", "malayalam": "ml-IN",
    }
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    source = language_codes.get(language.casefold())
    if not api_key or not source:
        return query
    try:
        response = requests.post(
            "https://api.sarvam.ai/translate",
            headers={"api-subscription-key": api_key, "Content-Type": "application/json"},
            json={"input": query, "source_language_code": source, "target_language_code": "en-IN", "model": "mayura:v1"},
            timeout=(8, 25),
        )
        response.raise_for_status()
        return str(response.json().get("translated_text") or query).strip()
    except (requests.RequestException, ValueError):
        return query


def _citation(document: dict[str, Any], index: int) -> dict[str, Any]:
    metadata = document.get("metadata") or {}
    source_url = metadata.get("source_url")
    source_path = str(metadata.get("source_path") or "")
    if not source_url and source_path.lower().endswith("tnau-paddy-schemes.htm"):
        source_url = "https://agritech.tnau.ac.in/expert_system/paddy/Schemes.html"
    return {
        "id": index,
        "scheme": metadata.get("scheme_name") or "Agricultural scheme document",
        "state": metadata.get("state") or "India",
        "page": metadata.get("page_number"),
        "source": metadata.get("source_type") or "curated corpus",
        "url": source_url if isinstance(source_url, str) and source_url.startswith(("https://", "http://")) else None,
    }


def _is_pmkisan_document_query(query: str) -> bool:
    query_tokens = _tokens(query)
    return "pm-kisan" in query_tokens and bool(query_tokens & {"document", "registration", "apply", "application", "required"})


def _fallback_answer(query: str, documents: list[dict[str, Any]]) -> str:
    if not documents:
        return "I could not find a confident answer in the Kisan Sahayak scheme documents. Please ask about a specific farmer scheme, subsidy, eligibility rule, or application requirement."
    first = documents[0]
    metadata = first.get("metadata") or {}
    scheme = metadata.get("scheme_name") or "the relevant agricultural scheme"
    excerpt = re.sub(r"\s+", " ", str(first.get("page_content", ""))).strip()
    if len(excerpt) > 520:
        excerpt = excerpt[:517].rsplit(" ", 1)[0] + "..."
    return f"The closest scheme information is **{scheme}**. {excerpt}"


def _pm_kisan_fallback(language: str) -> str:
    if language.casefold() == "telugu":
        return (
            "PM-KISAN నమోదు కోసం సాధారణంగా ఆధార్ నంబర్, భూమి యాజమాన్య లేదా భూమి రికార్డు వివరాలు, "
            "బ్యాంక్ ఖాతా నంబర్ మరియు IFSC, చురుకైన మొబైల్ నంబర్ సిద్ధంగా ఉంచండి. నమోదు చేసిన రైతులకు eKYC తప్పనిసరి. "
            "రాష్ట్రం లేదా కేంద్ర పాలిత ప్రాంతం అదనపు పత్రాలు అడగవచ్చు; తుది జాబితాను అధికారిక PM-KISAN రిజిస్ట్రేషన్ పేజీలో నిర్ధారించండి."
        )
    return _PM_KISAN_DOCUMENT_GUIDANCE


def _provider_answer(query: str, context: str, language: str) -> str | None:
    """Use Sarvam or OpenAI when configured; otherwise stay local and grounded."""
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if api_key:
        url = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai/v1").rstrip("/") + "/chat/completions"
        model = os.getenv("LLM_MODEL", "sarvam-105b-conversations")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    else:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None
        url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = (
        "You are Kisan Sahayak. Answer only from the supplied official agricultural scheme context. "
        f"Write the complete answer only in {language}; do not answer in English unless the requested language is English. "
        "If the context does not answer the question, say so plainly in the requested language. "
        "Keep the answer concise and never invent amounts, eligibility, or deadlines.\n\n"
        f"CONTEXT:\n{context}\n\nQUESTION: {query}"
    )
    try:
        response = requests.post(url, headers=headers, json={"model": model, "temperature": 0.2, "max_tokens": 350, "messages": [{"role": "user", "content": prompt}]}, timeout=(8, 35))
        response.raise_for_status()
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return content or None
    except (requests.RequestException, ValueError, IndexError, KeyError) as exc:
        return None


def answer_query(query: str, language: str = "English") -> dict[str, Any]:
    retrieval_query = _retrieval_query(query, language)
    documents = _search(retrieval_query)
    pm_kisan_document_query = _is_pmkisan_document_query(retrieval_query)
    if pm_kisan_document_query:
        documents = [
            document for document in documents
            if (document.get("metadata") or {}).get("scheme_name") == "PM-KISAN"
        ]
    citations = [_citation(document, index) for index, document in enumerate(documents, 1)]
    context = "\n\n---\n\n".join(str(document.get("page_content", ""))[:1600] for document in documents)
    if pm_kisan_document_query:
        context = f"{_PM_KISAN_DOCUMENT_GUIDANCE}\n\n---\n\n{context}"
        citations.insert(0, {
            "id": 0,
            "scheme": "PM-KISAN official portal",
            "state": "India",
            "page": None,
            "source": "official government website",
            "url": _PM_KISAN_PORTAL,
        })
    answer = _provider_answer(query, context, language) if (documents or pm_kisan_document_query) else None
    answer_text = answer or (_pm_kisan_fallback(language) if pm_kisan_document_query else _fallback_answer(query, documents))
    linked_sources = []
    seen_sources = set()
    for citation in citations:
        source_key = citation.get("url") or f"{citation.get('scheme')}|{citation.get('page')}"
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        if citation.get("url"):
            linked_sources.append(f"{citation['scheme']}: {citation['url']}")
        else:
            page = f", page {citation['page']}" if citation.get("page") else ""
            linked_sources.append(f"{citation['scheme']} (bundled {citation.get('source', 'document')}{page})")
    if linked_sources:
        answer_text += "\n\nSources and application references:\n- " + "\n- ".join(linked_sources)
    return {
        "answer": answer_text,
        "citations": citations,
        "retrieval": {"matches": len(documents), "mode": "provider" if answer else "local-grounded"},
        "language": language,
    }


def corpus_status() -> dict[str, Any]:
    return {"documents": len(_load_documents()), "provider_ready": bool(os.getenv("SARVAM_API_KEY") or os.getenv("OPENAI_API_KEY"))}
