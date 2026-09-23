/* AgriBot – Dashboard JS */

let forecastChartInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
  await loadWeather();
  loadSoilPlaceholders();
  loadAlerts();
});

async function loadWeather() {
  if (!navigator.geolocation) return;

  try {
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: false,
        timeout: 10000,
        maximumAge: 300000,
      });
    });
    const { latitude, longitude } = position.coords;
    const data = await apiFetch(`/api/weather/current?lat=${latitude}&lon=${longitude}`);
    const c = data.current;
    setText("dashTemp",     `${c.temperature}°C`);
    setText("dashHumidity", `${c.humidity}%`);
    setText("dashWind",     `${c.wind_speed} km/h`);
    setText("dashRain",     `${c.precipitation} mm`);

    // Build chart
    const labels  = data.forecast.map(d => d.date.slice(5));
    const maxTemps = data.forecast.map(d => d.max_temp);
    const rain    = data.forecast.map(d => d.precipitation);

    const ctx = document.getElementById("forecastChart");
    if (ctx) {
      if (forecastChartInstance) forecastChartInstance.destroy();
      forecastChartInstance = new Chart(ctx, {
        data: {
          labels,
          datasets: [
            { type: "line", label: "Max Temp (°C)", data: maxTemps,
              borderColor: "#ea580c", backgroundColor: "rgba(234,88,12,.1)",
              fill: true, tension: .4, yAxisID: "y" },
            { type: "bar", label: "Rain (mm)", data: rain,
              backgroundColor: "rgba(37,99,235,.5)", yAxisID: "y1" },
          ],
        },
        options: {
          responsive: true,
          interaction: { mode: "index", intersect: false },
          scales: {
            y:  { type: "linear", position: "left",  title: { display: true, text: "Temp °C" } },
            y1: { type: "linear", position: "right", title: { display: true, text: "Rain mm" }, grid: { drawOnChartArea: false } },
          },
          plugins: { legend: { position: "top" } },
        },
      });
    }
  } catch (e) { console.warn("Weather load failed", e); }
}

function loadSoilPlaceholders() {
  setBarValue("soilN", "soilNBar", "Medium (180 kg/ha)", 55);
  setBarValue("soilP", "soilPBar", "Low (60 kg/ha)",    30);
  setBarValue("soilK", "soilKBar", "High (220 kg/ha)",  70);
}

function setBarValue(textId, barId, text, pct) {
  setText(textId, text);
  const bar = document.getElementById(barId);
  if (bar) bar.style.width = `${pct}%`;
}

function loadAlerts() {
  const el = document.getElementById("dashAlerts");
  if (!el) return;
  const alerts = [
    { type: "warning", icon: "exclamation-triangle-fill", text: "Apply fertilizer within 3 days for optimal crop health." },
    { type: "info",    icon: "cloud-rain-fill",           text: "Moderate rainfall expected in next 48 hours. Delay irrigation." },
    { type: "success", icon: "check-circle-fill",         text: "Soil moisture levels are adequate for sowing." },
  ];
  el.innerHTML = alerts.map(a => `
    <div class="alert alert-${a.type} py-2 mb-2 d-flex gap-2">
      <i class="bi bi-${a.icon}"></i>
      <span class="small">${a.text}</span>
    </div>`).join("");
}

// ── Dash Quick Chat ────────────────────────────────────────────
const dashBox   = document.getElementById("dashChatMessages");
const dashInput = document.getElementById("dashChatInput");
const dashSend  = document.getElementById("dashChatSend");

function dashAppend(role, text) {
  if (!dashBox) return;
  const isUser = role === "user";
  const div = document.createElement("div");
  div.className = `chat-message ${isUser ? "user-msg" : ""} mb-1`;
  div.innerHTML = `
    <div class="chat-avatar" style="width:28px;height:28px;font-size:.8rem;">
      <i class="bi bi-${isUser ? 'person-fill' : 'robot'}"></i>
    </div>
    <div class="chat-bubble" style="font-size:.82rem;padding:7px 12px;">
      ${isUser ? text : renderMarkdown(text)}
    </div>`;
  dashBox.appendChild(div);
  dashBox.scrollTop = dashBox.scrollHeight;
}

async function dashSendMsg(text) {
  const msg = (text || dashInput?.value || "").trim();
  if (!msg) return;
  if (dashInput) dashInput.value = "";
  dashAppend("user", msg);
  dashAppend("assistant", '<div class="typing-dots"><span></span><span></span><span></span></div>');

  try {
    const data = await apiFetch("/api/chat/message", {
      method: "POST", body: JSON.stringify({ message: msg }),
    });
    dashBox.lastElementChild.querySelector(".chat-bubble").innerHTML = renderMarkdown(data.reply);
  } catch (err) {
    dashBox.lastElementChild.querySelector(".chat-bubble").textContent = `Error: ${err.message}`;
  }
}

function dashQuick(q) { dashSendMsg(q); }
if (dashSend)  dashSend.addEventListener("click", () => dashSendMsg());
if (dashInput) dashInput.addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); dashSendMsg(); }
});

// ── Helpers ───────────────────────────────────────────────────
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
