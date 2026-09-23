/* AgriBot - Live Mandi Prices */

let mandiPredictionChart = null;
let latestMandiData = null;

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("mandiSearchForm")?.addEventListener("submit", event => {
    event.preventDefault();
    loadMandiPrices();
  });
  document.getElementById("predictMandiPrices")?.addEventListener("click", predictMandiPrices);
});

async function loadMandiPrices() {
  const crop = document.getElementById("mandiCrop")?.value.trim() || "";
  const state = document.getElementById("mandiState")?.value.trim() || "";
  const status = document.getElementById("mandiStatus");
  const fetchButton = document.getElementById("fetchMandiPrices");
  if (!crop || !state) {
    if (status) status.textContent = "Enter both a crop and state to fetch prices.";
    return;
  }
  if (status) status.textContent = "Fetching live Agmarknet mandi prices...";
  if (fetchButton) {
    fetchButton.disabled = true;
    fetchButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>Fetching...';
  }

  try {
    const data = await apiFetch(`/api/market/live?commodity=${encodeURIComponent(crop)}&state=${encodeURIComponent(state)}&refresh=${Date.now()}`);
    latestMandiData = data;
    renderMandiTable(data.livePrices || []);
    renderPredictions([]);
    if (status) status.textContent = `${data.livePrices.length} real mandi prices found for ${crop} in ${state}. Click Predict for the next seven days.`;
  } catch (error) {
    latestMandiData = null;
    if (status) status.textContent = error.message || "Unable to load live mandi prices.";
    renderMandiTable([]);
    renderPredictions([]);
  } finally {
    if (fetchButton) {
      fetchButton.disabled = false;
      fetchButton.innerHTML = '<i class="bi bi-cloud-download me-1"></i>Fetch Prices';
    }
  }
}

function predictMandiPrices() {
  const status = document.getElementById("mandiStatus");
  if (!latestMandiData) {
    if (status) status.textContent = "Fetch live prices first, then click Predict.";
    return;
  }
  renderPredictions(latestMandiData.predictions || []);
  if (status) status.textContent = `Seven-day prediction generated for ${latestMandiData.crop} in ${latestMandiData.state}.`;
}

function renderMandiTable(rows) {
  const table = document.getElementById("mandiTable");
  if (!table) return;
  table.innerHTML = rows.length ? rows.map(row => `
    <tr><td>${escapeHtml(row.market)}</td><td>${escapeHtml(row.district)}</td>
    <td>${row.modalPrice ? `₹${Number(row.modalPrice).toLocaleString("en-IN")}` : "-"}</td>
    <td>${escapeHtml(row.date)}</td></tr>`).join("")
    : '<tr><td colspan="4" class="text-muted p-4">No mandi records found for this crop and state.</td></tr>';
}

function renderPredictions(predictions) {
  const table = document.getElementById("mandiPredictionTable");
  const notice = document.getElementById("mandiPredictionNotice");
  if (table) table.innerHTML = predictions.length ? predictions.map(item => `
    <tr><td>${item.date}</td><td>${Number(item.predictedModalPrice).toLocaleString("en-IN")}</td></tr>`).join("")
    : '<tr><td colspan="2" class="text-muted">Prediction is unavailable until numeric mandi prices are found.</td></tr>';
  if (notice) {
    if (!predictions.length) {
      notice.textContent = "Fetch live prices, then click Predict to calculate the seven-day trend.";
    } else {
      const firstPrice = Number(predictions[0].predictedModalPrice);
      const lastPrice = Number(predictions[predictions.length - 1].predictedModalPrice);
      const direction = lastPrice > firstPrice ? "increasing" : lastPrice < firstPrice ? "decreasing" : "stable";
      notice.textContent = `Prices are ${direction} over the next 7 days: ₹${firstPrice.toLocaleString("en-IN")} to ₹${lastPrice.toLocaleString("en-IN")}.`;
    }
  }

  const canvas = document.getElementById("mandiPredictionChart");
  if (!canvas || typeof Chart === "undefined") return;
  if (mandiPredictionChart) mandiPredictionChart.destroy();
  mandiPredictionChart = new Chart(canvas, {
    type: "line",
    data: { labels: predictions.map(item => item.date), datasets: [{
      label: "Predicted Modal Price (Rs)", data: predictions.map(item => item.predictedModalPrice),
      borderColor: "#2d8585", backgroundColor: "rgba(45,133,133,.16)", fill: true, tension: .25,
    }]},
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "top" } },
      scales: { y: { ticks: { callback: value => "₹" + Number(value).toLocaleString("en-IN") } } } },
  });
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "-" : String(value);
  return div.innerHTML;
}
