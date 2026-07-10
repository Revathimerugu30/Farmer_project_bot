/* AgriBot – Soil Analysis JS */

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("analyzeSoilBtn")?.addEventListener("click", analyzeSoil);
  loadSoilHistory();
});

async function analyzeSoil() {
  const soilType  = document.getElementById("soilType")?.value;
  const ph        = document.getElementById("soilPH")?.value;
  const nitrogen  = document.getElementById("soilN")?.value;
  const phosphorus= document.getElementById("soilP")?.value;
  const potassium = document.getElementById("soilK")?.value;

  if (!soilType) { showToast("Please select a soil type", "warning"); return; }

  const spinner = document.getElementById("soilSpinner");
  const btn     = document.getElementById("analyzeSoilBtn");
  spinner?.classList.remove("d-none");
  if (btn) btn.disabled = true;

  const resultEl = document.getElementById("soilResult");
  if (resultEl) resultEl.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-success"></div><p class="mt-2 text-muted small">Analyzing soil data…</p></div>';

  try {
    const data = await apiFetch("/api/soil/analyze", {
      method: "POST",
      body: JSON.stringify({ soil_type: soilType, ph, nitrogen, phosphorus, potassium }),
    });
    if (resultEl) resultEl.innerHTML = renderMarkdown(data.analysis);
    loadSoilHistory();
  } catch (err) {
    if (resultEl) resultEl.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
  } finally {
    spinner?.classList.add("d-none");
    if (btn) btn.disabled = false;
  }
}

async function loadSoilHistory() {
  const tbody = document.getElementById("soilHistory");
  if (!tbody) return;
  try {
    const rows = await apiFetch("/api/soil/history");
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${r.soil_type || "–"}</td>
        <td>${r.ph ?? "–"}</td>
        <td>${r.nitrogen ?? "–"}</td>
        <td>${r.phosphorus ?? "–"}</td>
        <td>${r.potassium ?? "–"}</td>
        <td><small class="text-muted">${new Date(r.created_at || Date.now()).toLocaleDateString()}</small></td>
      </tr>`).join("") || '<tr><td colspan="6" class="text-center text-muted py-3">No analyses yet</td></tr>';
  } catch (_) {}
}
