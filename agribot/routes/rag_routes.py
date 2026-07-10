"""RAG Knowledge Base API routes."""
import os
import logging
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from rag.rag_pipeline import (
    index_document, search, list_documents, delete_all,
)
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS

rag_bp = Blueprint("rag", __name__)
logger = logging.getLogger(__name__)


@rag_bp.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f    = request.files["file"]
    ext  = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"File type .{ext} not supported. Use: {ALLOWED_EXTENSIONS}"}), 400

    fname     = secure_filename(f.filename)
    save_path = os.path.join(UPLOAD_FOLDER, fname)
    f.save(save_path)

    try:
        n = index_document(save_path, source_name=fname)
        return jsonify({"status": "indexed", "chunks": n, "file": fname})
    except Exception as exc:
        logger.error("RAG indexing error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@rag_bp.route("/search", methods=["POST"])
def rag_search():
    data  = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    top_k = int(data.get("top_k", 3))
    if not query:
        return jsonify({"error": "Query required"}), 400

    results = search(query, top_k)
    return jsonify([
        {"text": text, "source": source, "score": round(score, 4)}
        for text, source, score in results
    ])


@rag_bp.route("/documents", methods=["GET"])
def documents():
    return jsonify(list_documents())


@rag_bp.route("/clear", methods=["POST"])
def clear():
    delete_all()
    return jsonify({"status": "cleared"})
