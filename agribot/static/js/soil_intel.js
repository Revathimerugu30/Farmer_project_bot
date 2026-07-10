/* AgriBot – Soil Intelligence JS */

let siSelectedFile = null;

document.addEventListener("DOMContentLoaded", () => {
  // Dropzone setup
  const dropzone   = document.getElementById("siDropzone");
  const fileInput  = document.getElementById("siImageInput");
  const clearBtn   = document.getElementById("siClearImg");
  const analyzeBtn = document.getElementById("siAnalyzeBtn");
  const copyBtn    = document.getElementById("siCopyReport");

  dropzone?.addEventListener("click", () => fileInput?.click());
  dropzone?.addEventListener("dragover",  e => { e.preventDefault(); dropzone.classList.add("si-drag-over"); });
  dropzone?.addEventListener("dragleave", () => dropzone.classList.remove("si-drag-over"));
  dropzone?.addEventListener("drop", e => {
    e.preventDefault();
    dropzone.classList.remove("si-drag-over");
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith("image/")) setImage(f);
  });
  fileInput?.addEventListener("change", () => {
    if (fileInput.files[0]) setImage(fileInput.files[0]);
  });
  clearBtn?.addEventListener("click", clearImage);
  analyzeBtn?.addEventListener("click", runAnalysis);
  copyBtn?.addEventListener("click", copyReport);

  loadHistory();
});

function setImage(file) {
  siSelectedFile = file;
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById("siPreviewImg").src = e.target.result;
    document.getElementById("siFileName").textContent = file.name;
    document.getElementById("siPreviewBox").classList.remove("d-none");
    document.getElementById("siDropzone").classList.add("d-none");
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  siSelectedFile = null;
  document.getElementById("siPreviewBox").classList.add("d-none");
  document.getElementById("siDropzone").classList.remove("d-none");
  document.getElementById("siImageInput").value = "";
}

async function runAnalysis() {
  const state   = document.getElementById("siState")?.value.trim();
  const district= document.getElementById("siDistrict")?.value.trim();
  const season  = document.getElementById("siSeason")?.value.trim();
  const ph      = document.getElementById("siPH")?.value.trim();
  const nitrogen= document.getElementById("siN")?.value.trim();
  const phosphorus= document.getElementById("siP")?.value.trim();
  const potassium = document.getElementById("siK")?.value.trim();

  if (!state)  { showToast("Please select your State", "warning"); return; }
  if (!season) { showToast("Please select the Season", "warning"); return; }

  const spinner    = document.getElementById("siSpinner");
  const analyzeBtn = document.getElementById("siAnalyzeBtn");
  spinner?.classList.remove("d-none");
  if (analyzeBtn) analyzeBtn.disabled = true;

  // Show loading state
  document.getElementById("siPlaceholder").classList.add("d-none");
  document.getElementById("siResults").classList.remove("d-none");
  document.getElementById("siConfBar").style.width = "0%";
  document.getElementById("siConfPct").textContent = "Analyzing…";
  document.getElementById("siReportContent").innerHTML = `
    <div class="text-center py-5">
      <div class="spinner-border text-success mb-3" role="status"></div>
      <p class="text-muted">AgriBot is analyzing your soil data with IBM Watsonx.ai…</p>
      <p class="text-muted small">This may take 15–30 seconds</p>
    </div>`;

  try {
    const formData = new FormData();
    formData.append("state", state);
    formData.append("district", district);
    formData.append("season", season);
    if (ph)         formData.append("ph", ph);
    if (nitrogen)   formData.append("nitrogen", nitrogen);
    if (phosphorus) formData.append("phosphorus", phosphorus);
    if (potassium)  formData.append("potassium", potassium);
    if (siSelectedFile) formData.append("image", siSelectedFile);

    const res  = await fetch("/api/soil-intel/analyze", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Analysis failed");

    renderResults(data);
    loadHistory();
  } catch (err) {
    document.getElementById("siReportContent").innerHTML =
      `<div class="alert alert-danger">
        <i class="bi bi-exclamation-triangle-fill me-1"></i>
        <strong>Error:</strong> ${err.message}
        <div class="small mt-1 text-muted">Check that your IBM credentials in .env are correct.</div>
      </div>`;
    document.getElementById("siConfPct").textContent = "Failed";
  } finally {
    spinner?.classList.add("d-none");
    if (analyzeBtn) analyzeBtn.disabled = false;
  }
}

function renderResults(data) {
  const conf = data.confidence || 0;

  // Confidence bar (animate)
  setTimeout(() => {
    document.getElementById("siConfBar").style.width = conf + "%";
    document.getElementById("siConfPct").textContent = conf + "%";
    // Color coding
    const bar = document.getElementById("siConfBar");
    bar.className = "progress-bar " + (conf >= 70 ? "bg-success" : conf >= 50 ? "bg-warning" : "bg-danger");
  }, 100);

  // Meta
  setText("siMetaLocation", `📍 ${data.state}${data.district ? ", " + data.district : ""}`);
  setText("siMetaSeason",   `🌾 ${data.season}`);

  // Image analysis section
  const imgCard = document.getElementById("siImageAnalysisCard");
  if (data.has_image && data.image_analysis) {
    imgCard.classList.remove("d-none");
    document.getElementById("siImageAnalysisText").innerHTML = renderMarkdown(data.image_analysis);
  } else {
    imgCard.classList.add("d-none");
  }

  // Main report
  document.getElementById("siReportContent").innerHTML = renderMarkdown(data.report);
}

function copyReport() {
  const el = document.getElementById("siReportContent");
  if (!el) return;
  navigator.clipboard.writeText(el.innerText).then(() => {
    const btn = document.getElementById("siCopyReport");
    if (btn) {
      btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Copied!';
      setTimeout(() => { btn.innerHTML = '<i class="bi bi-clipboard me-1"></i>Copy'; }, 2000);
    }
  });
}

async function loadHistory() {
  const tbody = document.getElementById("siHistoryBody");
  if (!tbody) return;
  try {
    const rows = await apiFetch("/api/soil-intel/history");
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-2 small">No analyses yet</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td class="small">${r.state || "–"}</td>
        <td class="small">${r.district || "–"}</td>
        <td class="small">${r.season || "–"}</td>
        <td>
          <div class="progress" style="height:6px;width:80px;">
            <div class="progress-bar ${r.confidence >= 70 ? 'bg-success' : r.confidence >= 50 ? 'bg-warning' : 'bg-danger'}"
              style="width:${r.confidence}%"></div>
          </div>
          <span class="small text-muted">${r.confidence}%</span>
        </td>
        <td class="small text-muted">${r.created_at ? new Date(r.created_at).toLocaleDateString() : "–"}</td>
      </tr>`).join("");
  } catch (_) {}
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
