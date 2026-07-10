/* AgriBot – Knowledge Base JS */

document.addEventListener("DOMContentLoaded", () => {
  loadDocuments();

  const dropzone = document.getElementById("docDropzone");
  const fileInput = document.getElementById("docUpload");
  const uploadBtn = document.getElementById("uploadDocBtn");

  dropzone?.addEventListener("click",    () => fileInput?.click());
  dropzone?.addEventListener("dragover",  e => { e.preventDefault(); dropzone.classList.add("drag-over"); });
  dropzone?.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
  dropzone?.addEventListener("drop",      e => {
    e.preventDefault(); dropzone.classList.remove("drag-over");
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  });

  fileInput?.addEventListener("change", () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });
  uploadBtn?.addEventListener("click",  uploadDocument);

  document.getElementById("ragSearchBtn")?.addEventListener("click", doSearch);
  document.getElementById("ragQuery")?.addEventListener("keydown", e => { if (e.key === "Enter") doSearch(); });
  document.getElementById("clearRagBtn")?.addEventListener("click", clearIndex);
});

function setFile(file) {
  const nameEl  = document.getElementById("uploadFileName");
  const btn     = document.getElementById("uploadDocBtn");
  if (nameEl) { nameEl.textContent = `📄 ${file.name}`; nameEl.classList.remove("d-none"); }
  if (btn) btn.disabled = false;
}

async function uploadDocument() {
  const fileInput = document.getElementById("docUpload");
  const file = fileInput?.files[0];
  if (!file) { showToast("Select a file first", "warning"); return; }

  const spinner = document.getElementById("uploadSpinner");
  const btn     = document.getElementById("uploadDocBtn");
  spinner?.classList.remove("d-none");
  if (btn) btn.disabled = true;

  const resultEl = document.getElementById("uploadResult");
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res  = await fetch("/api/rag/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    if (resultEl) resultEl.innerHTML = `<div class="alert alert-success py-1 small">✅ Indexed ${data.chunks} chunks from <strong>${data.file}</strong></div>`;
    loadDocuments();
  } catch (err) {
    if (resultEl) resultEl.innerHTML = `<div class="alert alert-danger py-1 small">❌ ${err.message}</div>`;
  } finally {
    spinner?.classList.add("d-none");
    if (btn) btn.disabled = false;
  }
}

async function doSearch() {
  const query = document.getElementById("ragQuery")?.value.trim();
  if (!query) return;
  const el = document.getElementById("ragResults");
  if (el) el.innerHTML = "Searching…";

  try {
    const results = await apiFetch("/api/rag/search", {
      method: "POST", body: JSON.stringify({ query, top_k: 3 }),
    });
    if (!results.length) { el.innerHTML = '<span class="text-muted">No results found.</span>'; return; }
    el.innerHTML = results.map((r, i) => `
      <div class="card mb-2 border-start border-success border-3 p-2">
        <div class="fw-semibold text-success small mb-1">Result ${i+1} — <span class="text-muted">${r.source}</span></div>
        <div style="font-size:.8rem;line-height:1.5;">${r.text.slice(0,300)}…</div>
      </div>`).join("");
  } catch (err) {
    if (el) el.textContent = "Error: " + err.message;
  }
}

async function loadDocuments() {
  const el = document.getElementById("docList");
  if (!el) return;
  try {
    const docs = await apiFetch("/api/rag/documents");
    if (!docs.length) {
      el.innerHTML = '<p class="text-muted small">No documents indexed yet.</p>'; return;
    }
    el.innerHTML = `<div class="table-responsive"><table class="table table-sm mb-0">
      <thead><tr><th>Document</th><th>Chunks</th></tr></thead>
      <tbody>${docs.map(d => `<tr><td><i class="bi bi-file-earmark-text text-success me-1"></i>${d.source}</td><td><span class="badge bg-secondary">${d.chunks}</span></td></tr>`).join("")}</tbody>
    </table></div>`;
  } catch (_) {}
}

async function clearIndex() {
  if (!confirm("Clear all indexed documents? This cannot be undone.")) return;
  await apiFetch("/api/rag/clear", { method: "POST" });
  showToast("Knowledge base cleared", "warning");
  loadDocuments();
}
