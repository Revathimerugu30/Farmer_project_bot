"""Validation for the locally curated official scheme dataset."""
from __future__ import annotations

from urllib.parse import urlparse

REQUIRED_FIELDS = {
    "scheme_id", "scheme_name", "level", "state", "department", "description",
    "benefits", "eligibility", "documents", "official_source_url", "last_verified",
}


def validate_scheme(record: dict) -> list[str]:
    errors = sorted(REQUIRED_FIELDS - record.keys())
    if not isinstance(record.get("benefits"), list):
        errors.append("benefits must be a list")
    if not isinstance(record.get("documents"), list):
        errors.append("documents must be a list")
    if not isinstance(record.get("eligibility"), dict):
        errors.append("eligibility must be an object")
    source = record.get("official_source_url", "")
    parsed = urlparse(source) if isinstance(source, str) else None
    if not parsed or parsed.scheme != "https" or not parsed.netloc:
        errors.append("official_source_url must be an https URL")
    if record.get("level") not in {"Central", "State"}:
        errors.append("level must be Central or State")
    return errors


def validate_dataset(records: list[dict]) -> None:
    problems = []
    for index, record in enumerate(records):
        for error in validate_scheme(record):
            problems.append(f"record {index}: {error}")
    if problems:
        raise ValueError("Invalid scheme dataset: " + "; ".join(problems))
