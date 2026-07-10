/* AgriBot – Weather Page JS */

let weatherChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
  fetchWeather();
  document.getElementById("fetchWeatherBtn")?.addEventListener("click", fetchWeather);
  document.getElementById("geoLocBtn")?.addEventListener("click", useGeoLocation);
  document.getElementById("askWeatherBtn")?.addEventListener("click", askWeatherQuestion);
});

async function fetchWeather() {
  const lat = parseFloat(document.getElementById("latInput")?.value || 20.5937);
  const lon = parseFloat(document.getElementById("lonInput")?.value || 78.9629);

  try {
    const data = await apiFetch(`/api/weather/current?lat=${lat}&lon=${lon}`);
    renderCurrentWeather(data.current);
    renderForecastCards(data.forecast);
    renderForecastChart(data.forecast);
    renderAdvisory(data.current, data.forecast);
  } catch (err) {
    showToast("Weather fetch failed: " + err.message, "danger");
  }
}

function renderCurrentWeather(c) {
  setText("wTemp",  `${c.temperature}°C`);
  setText("wHum",   `${c.humidity}%`);
  setText("wWind",  `${c.wind_speed} km/h`);
  setText("wRain",  `${c.precipitation} mm`);
}

function renderForecastCards(forecast) {
  const el = document.getElementById("forecastCards");
  if (!el) return;
  el.innerHTML = forecast.map(day => `
    <div class="col-6 col-md-3 col-lg-auto">
      <div class="card text-center p-2 border" style="min-width:110px;">
        <div class="fw-semibold small">${day.date}</div>
        <div class="text-muted small">${day.condition}</div>
        <div class="fs-6 fw-bold text-warning mt-1">${day.max_temp}° <span class="text-info fs-7">${day.min_temp}°</span></div>
        <div class="small text-primary"><i class="bi bi-cloud-rain-fill"></i> ${day.precipitation} mm</div>
      </div>
    </div>`).join("");
}

function renderForecastChart(forecast) {
  const ctx = document.getElementById("weatherChart");
  if (!ctx) return;
  if (weatherChartInstance) weatherChartInstance.destroy();

  const labels = forecast.map(d => d.date.slice(5));
  weatherChartInstance = new Chart(ctx, {
    data: {
      labels,
      datasets: [
        { type: "line", label: "Max Temp (°C)", data: forecast.map(d => d.max_temp),
          borderColor: "#ea580c", backgroundColor: "rgba(234,88,12,.1)", fill: true, tension: .4, yAxisID: "y" },
        { type: "line", label: "Min Temp (°C)", data: forecast.map(d => d.min_temp),
          borderColor: "#3b82f6", backgroundColor: "rgba(59,130,246,.05)", fill: false, tension: .4, yAxisID: "y", borderDash: [4,3] },
        { type: "bar",  label: "Rain (mm)",     data: forecast.map(d => d.precipitation),
          backgroundColor: "rgba(37,99,235,.45)", yAxisID: "y1" },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      scales: {
        y:  { type: "linear", position: "left",  title: { display: true, text: "Temp (°C)" } },
        y1: { type: "linear", position: "right", title: { display: true, text: "Rain (mm)" }, grid: { drawOnChartArea: false } },
      },
    },
  });
}

function renderAdvisory(current, forecast) {
  const el = document.getElementById("weatherAdvisory");
  if (!el) return;
  const rain3d = forecast.slice(0, 3).reduce((s, d) => s + (d.precipitation || 0), 0);
  const tips = [];

  if (current.temperature > 38) tips.push("⚠️ Extreme heat – irrigate crops in early morning.");
  else if (current.temperature < 10) tips.push("🌡️ Cold wave – protect sensitive crops with mulching.");
  else tips.push("🌤️ Weather is suitable for fieldwork.");

  if (rain3d > 20) tips.push("🌧️ Heavy rain forecast – delay chemical spraying for 3+ days.");
  else if (rain3d > 5)  tips.push("🌦️ Light rain expected – consider reducing irrigation.");
  else tips.push("☀️ Dry weather ahead – maintain regular irrigation schedule.");

  if (current.wind_speed > 30) tips.push("💨 High winds – avoid spraying pesticides/herbicides.");

  el.innerHTML = tips.map(t => `<div class="mb-2 small">${t}</div>`).join("");
}

async function askWeatherQuestion() {
  const lat = parseFloat(document.getElementById("latInput")?.value || 20.5937);
  const lon = parseFloat(document.getElementById("lonInput")?.value || 78.9629);
  const el = document.getElementById("weatherAdvisory");
  if (el) el.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';

  try {
    const data = await apiFetch("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({
        message: "Based on current weather, can I sow seeds tomorrow? Give farming advice.",
        latitude: lat, longitude: lon,
      }),
    });
    if (el) el.innerHTML = `<div class="small">${renderMarkdown(data.reply)}</div>`;
  } catch (err) {
    if (el) el.textContent = "Error: " + err.message;
  }
}

function useGeoLocation() {
  if (!navigator.geolocation) return showToast("Geolocation not supported", "warning");
  navigator.geolocation.getCurrentPosition(pos => {
    document.getElementById("latInput").value = pos.coords.latitude.toFixed(4);
    document.getElementById("lonInput").value = pos.coords.longitude.toFixed(4);
    fetchWeather();
  });
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
