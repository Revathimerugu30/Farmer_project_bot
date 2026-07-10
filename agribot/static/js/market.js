/* AgriBot – Market Prices JS */

let allPrices = [];
let marketChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
  loadPrices();
  document.getElementById("refreshMarketBtn")?.addEventListener("click", loadPrices);
  document.getElementById("marketSearch")?.addEventListener("input", filterTable);
  document.getElementById("marketAskBtn")?.addEventListener("click", askMarket);
  document.getElementById("marketAskInput")?.addEventListener("keydown", e => {
    if (e.key === "Enter") askMarket();
  });
});

async function loadPrices() {
  try {
    allPrices = await apiFetch("/api/market/prices");
    renderTable(allPrices);
    renderChart(allPrices.slice(0, 8));
  } catch (err) {
    showToast("Failed to load prices: " + err.message, "danger");
  }
}

function renderTable(prices) {
  const tbody = document.getElementById("marketTable");
  if (!tbody) return;
  tbody.innerHTML = prices.map(p => `
    <tr>
      <td class="fw-semibold">${p.crop}</td>
      <td>₹${p.today_price}</td>
      <td class="text-muted">₹${p.yesterday_price}</td>
      <td class="${p.trend === 'up' ? 'text-success' : p.trend === 'down' ? 'text-danger' : 'text-muted'}">
        ${p.trend === "up" ? "▲" : p.trend === "down" ? "▼" : "–"} ${Math.abs(p.change_pct)}%
      </td>
      <td><span class="badge ${p.trend === 'up' ? 'bg-success' : p.trend === 'down' ? 'bg-danger' : 'bg-secondary'}">
        ${p.trend}</span>
      </td>
    </tr>`).join("");
}

function renderChart(prices) {
  const ctx = document.getElementById("marketChart");
  if (!ctx) return;
  if (marketChartInstance) marketChartInstance.destroy();

  marketChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: prices.map(p => p.crop),
      datasets: [{
        label: "Today ₹/quintal",
        data: prices.map(p => p.today_price),
        backgroundColor: prices.map(p =>
          p.trend === "up" ? "rgba(22,163,74,.7)" :
          p.trend === "down" ? "rgba(220,38,38,.7)" : "rgba(99,102,241,.7)"
        ),
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { callback: v => "₹" + v } },
        x: { ticks: { font: { size: 10 } } },
      },
    },
  });
}

function filterTable() {
  const q = document.getElementById("marketSearch")?.value.toLowerCase() || "";
  renderTable(allPrices.filter(p => p.crop.toLowerCase().includes(q)));
}

async function askMarket() {
  const input = document.getElementById("marketAskInput");
  const reply = document.getElementById("marketAiReply");
  const msg   = input?.value.trim();
  if (!msg) return;

  if (reply) reply.textContent = "Thinking…";

  // Build price context
  const ctx = allPrices.slice(0, 10).map(p =>
    `${p.crop}: ₹${p.today_price}/quintal (${p.trend})`).join(", ");

  try {
    const data = await apiFetch("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({ message: msg + `\n\nMarket prices context: ${ctx}` }),
    });
    if (reply) reply.innerHTML = renderMarkdown(data.reply);
  } catch (err) {
    if (reply) reply.textContent = "Error: " + err.message;
  }
}
