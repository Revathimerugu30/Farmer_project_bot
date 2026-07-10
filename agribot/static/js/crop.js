/* AgriBot – Crop Recommendation JS */

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("getCropBtn")?.addEventListener("click", getCropRecommendation);
});

async function getCropRecommendation() {
  const season   = document.getElementById("cropSeason")?.value;
  const soil     = document.getElementById("cropSoil")?.value;
  const location = document.getElementById("cropLocation")?.value;
  const rainfall = document.getElementById("cropRainfall")?.value;

  if (!season && !soil && !location) {
    showToast("Please fill at least one parameter", "warning"); return;
  }

  const spinner = document.getElementById("cropSpinner");
  const btn     = document.getElementById("getCropBtn");
  spinner?.classList.remove("d-none");
  if (btn) btn.disabled = true;

  const resultEl = document.getElementById("cropResult");
  if (resultEl) resultEl.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-success"></div><p class="mt-2 text-muted">Getting crop recommendations…</p></div>';

  try {
    const data = await apiFetch("/api/crop/recommend", {
      method: "POST",
      body: JSON.stringify({ season, soil, location, rainfall }),
    });
    if (resultEl) resultEl.innerHTML = renderMarkdown(data.recommendation);
  } catch (err) {
    if (resultEl) resultEl.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
  } finally {
    spinner?.classList.add("d-none");
    if (btn) btn.disabled = false;
  }
}
