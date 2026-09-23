# Weather Feature Copy-Paste Bundle

This is a portable Flask + Bootstrap + vanilla JavaScript weather feature based on the IBM Agri implementation.

## Feature

- Current temperature
- Relative humidity
- Wind speed
- Current precipitation
- Seven-day forecast
- Temperature/rainfall Chart.js graph
- Daily forecast cards
- Rule-based farming advisory
- Browser geolocation support
- Optional AI question: `Can I sow seeds tomorrow?`
- Open-Meteo integration with mock fallback when the provider is unavailable

## Files to Add

```text
your_project/
  services/weather_service.py
  routes/weather_routes.py
  templates/weather.html
  static/js/weather.js
  static/css/weather.css
```

## 1. Backend Service

Create `services/weather_service.py`:

```python
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight showers",
    81: "Moderate showers",
    82: "Violent showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
}


def get_weather(latitude: float, longitude: float) -> dict[str, Any]:
    """Return current conditions and a seven-day forecast."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "precipitation",
            "weathercode",
        ]),
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "weathercode",
        ]),
        "timezone": "auto",
        "forecast_days": 7,
    }

    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        response.raise_for_status()
        return _parse_weather(response.json())
    except Exception as exc:
        logger.warning("Weather provider failed: %s", exc)
        return _mock_weather()


def _parse_weather(data: dict[str, Any]) -> dict[str, Any]:
    current_data = data.get("current", {})
    daily_data = data.get("daily", {})

    current = {
        "temperature": current_data.get("temperature_2m"),
        "humidity": current_data.get("relative_humidity_2m"),
        "wind_speed": current_data.get("wind_speed_10m"),
        "precipitation": current_data.get("precipitation"),
        "condition": WMO_CODES.get(current_data.get("weathercode", 0), "Unknown"),
        "time": current_data.get("time", ""),
    }

    dates = daily_data.get("time", [])
    max_temps = daily_data.get("temperature_2m_max", [])
    min_temps = daily_data.get("temperature_2m_min", [])
    rainfall = daily_data.get("precipitation_sum", [])
    weather_codes = daily_data.get("weathercode", [])

    forecast = []
    for index, date in enumerate(dates):
        code = weather_codes[index] if index < len(weather_codes) else 0
        forecast.append({
            "date": date,
            "max_temp": max_temps[index] if index < len(max_temps) else None,
            "min_temp": min_temps[index] if index < len(min_temps) else None,
            "precipitation": rainfall[index] if index < len(rainfall) else None,
            "condition": WMO_CODES.get(code, "Unknown"),
        })

    return {"current": current, "forecast": forecast, "source": "open-meteo"}


def _mock_weather() -> dict[str, Any]:
    """Fallback response used when Open-Meteo cannot be reached."""
    return {
        "current": {
            "temperature": 28,
            "humidity": 65,
            "wind_speed": 12,
            "precipitation": 0,
            "condition": "Partly cloudy",
            "time": "N/A",
        },
        "forecast": [
            {"date": "Day 1", "max_temp": 32, "min_temp": 22, "precipitation": 2, "condition": "Partly cloudy"},
            {"date": "Day 2", "max_temp": 30, "min_temp": 21, "precipitation": 5, "condition": "Light rain"},
            {"date": "Day 3", "max_temp": 29, "min_temp": 20, "precipitation": 8, "condition": "Moderate rain"},
        ],
        "source": "mock-fallback",
    }


def weather_to_text(weather: dict[str, Any]) -> str:
    """Convert weather data into context for an AI farming prompt."""
    current = weather.get("current", {})
    lines = [
        f"Temperature: {current.get('temperature')} C",
        f"Humidity: {current.get('humidity')}%",
        f"Wind speed: {current.get('wind_speed')} km/h",
        f"Precipitation: {current.get('precipitation')} mm",
        f"Condition: {current.get('condition')}",
    ]

    forecast = weather.get("forecast", [])[:3]
    if forecast:
        lines.append("3-day forecast:")
        for day in forecast:
            lines.append(
                f"  {day['date']}: {day['condition']}, "
                f"{day['min_temp']}-{day['max_temp']} C, "
                f"rain {day['precipitation']} mm"
            )

    return "\n".join(lines)
```

`requests` is the only backend dependency required for the weather provider:

```text
requests>=2.32.3
```

## 2. Flask API Route

Create `routes/weather_routes.py`:

```python
from flask import Blueprint, jsonify, request

from services.weather_service import get_weather

weather_bp = Blueprint("weather", __name__)

DEFAULT_LATITUDE = 20.5937
DEFAULT_LONGITUDE = 78.9629


@weather_bp.get("/current")
def current_weather():
    try:
        latitude = float(request.args.get("lat", DEFAULT_LATITUDE))
        longitude = float(request.args.get("lon", DEFAULT_LONGITUDE))
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lon must be valid numbers"}), 400

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return jsonify({"error": "coordinates are outside valid ranges"}), 400

    return jsonify(get_weather(latitude, longitude))
```

Register the Blueprint in the destination Flask app:

```python
from routes.weather_routes import weather_bp

app.register_blueprint(weather_bp, url_prefix="/api/weather")

@app.get("/weather")
def weather_page():
    return render_template("weather.html")
```

The API endpoint becomes:

```text
GET /api/weather/current?lat=20.5937&lon=78.9629
```

Success response:

```json
{
  "current": {
    "temperature": 28,
    "humidity": 65,
    "wind_speed": 12,
    "precipitation": 0,
    "condition": "Partly cloudy",
    "time": "2026-08-21T10:00"
  },
  "forecast": [
    {
      "date": "2026-08-21",
      "max_temp": 32,
      "min_temp": 22,
      "precipitation": 2,
      "condition": "Partly cloudy"
    }
  ],
  "source": "open-meteo"
}
```

`source` is either `open-meteo` or `mock-fallback`; show this in the UI if users need to know whether the data is live.

## 3. Weather Page Template

Create `templates/weather.html`:

```html
{% extends "base.html" %}
{% block title %}Weather Dashboard{% endblock %}
{% block page_title %}Weather Dashboard{% endblock %}

{% block content %}
<div class="weather-page">
  <section class="weather-location-bar">
    <div class="weather-location-icon" aria-hidden="true">Location</div>
    <label>
      <span>Latitude</span>
      <input type="number" id="latInput" value="20.5937" step="0.0001" min="-90" max="90">
    </label>
    <label>
      <span>Longitude</span>
      <input type="number" id="lonInput" value="78.9629" step="0.0001" min="-180" max="180">
    </label>
    <button class="weather-button" id="fetchWeatherBtn" type="button">Refresh</button>
    <button class="weather-button weather-button-secondary" id="geoLocBtn" type="button">
      Use my location
    </button>
    <span class="weather-source" id="weatherSource" role="status"></span>
  </section>

  <section class="weather-stat-grid" aria-label="Current weather">
    <article class="weather-stat weather-stat-temperature">
      <span class="weather-stat-label">Temperature</span>
      <strong id="wTemp">--</strong>
    </article>
    <article class="weather-stat weather-stat-humidity">
      <span class="weather-stat-label">Humidity</span>
      <strong id="wHum">--</strong>
    </article>
    <article class="weather-stat weather-stat-wind">
      <span class="weather-stat-label">Wind</span>
      <strong id="wWind">--</strong>
    </article>
    <article class="weather-stat weather-stat-rain">
      <span class="weather-stat-label">Precipitation</span>
      <strong id="wRain">--</strong>
    </article>
  </section>

  <section class="weather-content-grid">
    <article class="weather-panel weather-chart-panel">
      <header class="weather-panel-header">7-Day Forecast</header>
      <div class="weather-chart-wrap">
        <canvas id="weatherChart" aria-label="Seven-day weather forecast chart"></canvas>
      </div>
    </article>

    <article class="weather-panel weather-advisory-panel">
      <header class="weather-panel-header">Farming Advisory</header>
      <div id="weatherAdvisory" class="weather-advisory" aria-live="polite">
        Loading advisory...
      </div>
      <button class="weather-button" id="askWeatherBtn" type="button">
        Ask: Can I sow seeds tomorrow?
      </button>
    </article>
  </section>

  <section class="weather-panel">
    <header class="weather-panel-header">Daily Forecast</header>
    <div id="forecastCards" class="forecast-card-grid"></div>
  </section>
</div>
{% endblock %}

{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<script src="{{ url_for('static', filename='js/weather.js') }}"></script>
{% endblock %}
```

If the destination project already has Bootstrap and its own shared cards/buttons, replace the CSS classes with its design-system classes. The element IDs are the frontend contract and should remain unchanged unless the JavaScript is updated too.

## 4. Frontend JavaScript

Create `static/js/weather.js`:

```javascript
let weatherChartInstance = null;

const DEFAULT_LATITUDE = 20.5937;
const DEFAULT_LONGITUDE = 78.9629;

window.addEventListener("DOMContentLoaded", () => {
  loadWeather();
  document.getElementById("fetchWeatherBtn")?.addEventListener("click", loadWeather);
  document.getElementById("geoLocBtn")?.addEventListener("click", useGeoLocation);
  document.getElementById("askWeatherBtn")?.addEventListener("click", askWeatherQuestion);
});

async function loadWeather() {
  const latitude = readCoordinate("latInput", DEFAULT_LATITUDE);
  const longitude = readCoordinate("lonInput", DEFAULT_LONGITUDE);

  setLoading(true);

  try {
    const response = await fetch(
      `/api/weather/current?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}`
    );
    const data = await parseJsonResponse(response);

    renderCurrentWeather(data.current || {});
    renderForecastCards(data.forecast || []);
    renderForecastChart(data.forecast || []);
    renderAdvisory(data.current || {}, data.forecast || []);
    setText("weatherSource", data.source === "mock-fallback" ? "Fallback data" : "Live Open-Meteo data");
  } catch (error) {
    showWeatherError(error.message);
  } finally {
    setLoading(false);
  }
}

function renderCurrentWeather(current) {
  setText("wTemp", formatValue(current.temperature, " C"));
  setText("wHum", formatValue(current.humidity, "%"));
  setText("wWind", formatValue(current.wind_speed, " km/h"));
  setText("wRain", formatValue(current.precipitation, " mm"));
}

function renderForecastCards(forecast) {
  const container = document.getElementById("forecastCards");
  if (!container) return;

  if (!forecast.length) {
    container.innerHTML = '<p class="weather-empty">No forecast data available.</p>';
    return;
  }

  container.innerHTML = forecast.map(day => `
    <article class="forecast-card">
      <strong>${escapeHtml(day.date || "-")}</strong>
      <span>${escapeHtml(day.condition || "Unknown")}</span>
      <b>${formatValue(day.max_temp, " C")}</b>
      <small>Low ${formatValue(day.min_temp, " C")}</small>
      <small>Rain ${formatValue(day.precipitation, " mm")}</small>
    </article>
  `).join("");
}

function renderForecastChart(forecast) {
  const canvas = document.getElementById("weatherChart");
  if (!canvas || typeof Chart === "undefined") return;

  if (weatherChartInstance) weatherChartInstance.destroy();

  weatherChartInstance = new Chart(canvas, {
    data: {
      labels: forecast.map(day => String(day.date || "").slice(5)),
      datasets: [
        {
          type: "line",
          label: "Max temperature (C)",
          data: forecast.map(day => day.max_temp),
          borderColor: "#d85d32",
          backgroundColor: "rgba(216, 93, 50, 0.12)",
          fill: true,
          tension: 0.35,
          yAxisID: "temperature",
        },
        {
          type: "line",
          label: "Min temperature (C)",
          data: forecast.map(day => day.min_temp),
          borderColor: "#2878a8",
          borderDash: [5, 4],
          tension: 0.35,
          yAxisID: "temperature",
        },
        {
          type: "bar",
          label: "Rain (mm)",
          data: forecast.map(day => day.precipitation),
          backgroundColor: "rgba(40, 120, 168, 0.42)",
          yAxisID: "rain",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        temperature: {
          type: "linear",
          position: "left",
          title: { display: true, text: "Temperature (C)" },
        },
        rain: {
          type: "linear",
          position: "right",
          title: { display: true, text: "Rain (mm)" },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

function renderAdvisory(current, forecast) {
  const container = document.getElementById("weatherAdvisory");
  if (!container) return;

  const nextThreeDaysRain = forecast
    .slice(0, 3)
    .reduce((total, day) => total + Number(day.precipitation || 0), 0);
  const tips = [];

  if (Number(current.temperature) > 38) {
    tips.push("Extreme heat: irrigate crops in the early morning.");
  } else if (Number(current.temperature) < 10) {
    tips.push("Cold conditions: protect sensitive crops with mulching.");
  } else {
    tips.push("Weather is suitable for normal fieldwork.");
  }

  if (nextThreeDaysRain > 20) {
    tips.push("Heavy rain expected: delay chemical spraying for at least three days.");
  } else if (nextThreeDaysRain > 5) {
    tips.push("Rain expected: consider reducing irrigation.");
  } else {
    tips.push("Dry weather ahead: maintain the regular irrigation schedule.");
  }

  if (Number(current.wind_speed) > 30) {
    tips.push("High winds: avoid spraying pesticides or herbicides.");
  }

  container.innerHTML = tips.map(tip => `<p>${escapeHtml(tip)}</p>`).join("");
}

async function askWeatherQuestion() {
  const advisory = document.getElementById("weatherAdvisory");
  if (advisory) advisory.innerHTML = "<p>Asking the farming assistant...</p>";

  const latitude = readCoordinate("latInput", DEFAULT_LATITUDE);
  const longitude = readCoordinate("lonInput", DEFAULT_LONGITUDE);

  try {
    const response = await fetch("/api/chat/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "Based on the current weather, can I sow seeds tomorrow? Give practical farming advice.",
        latitude,
        longitude,
      }),
    });
    const data = await parseJsonResponse(response);
    if (advisory) advisory.innerHTML = renderMarkdown(data.reply || "No advice returned.");
  } catch (error) {
    if (advisory) advisory.textContent = `Unable to get AI advice: ${error.message}`;
  }
}

function useGeoLocation() {
  if (!navigator.geolocation) {
    showWeatherError("Geolocation is not supported by this browser.");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    position => {
      document.getElementById("latInput").value = position.coords.latitude.toFixed(4);
      document.getElementById("lonInput").value = position.coords.longitude.toFixed(4);
      loadWeather();
    },
    error => showWeatherError(`Unable to read location: ${error.message}`),
    { enableHighAccuracy: false, timeout: 10000 }
  );
}

function readCoordinate(id, fallback) {
  const value = Number.parseFloat(document.getElementById(id)?.value);
  return Number.isFinite(value) ? value : fallback;
}

function formatValue(value, suffix) {
  return value === null || value === undefined || value === "" ? "--" : `${value}${suffix}`;
}

async function parseJsonResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function setLoading(isLoading) {
  const button = document.getElementById("fetchWeatherBtn");
  if (button) button.disabled = isLoading;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function showWeatherError(message) {
  const advisory = document.getElementById("weatherAdvisory");
  if (advisory) advisory.textContent = `Weather error: ${message}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMarkdown(value) {
  if (typeof marked !== "undefined") return marked.parse(value || "");
  return escapeHtml(value || "").replaceAll("\n", "<br>");
}
```

If the destination app already has a shared `apiFetch`, `renderMarkdown`, or toast helper, use those instead of the local equivalents. The weather page itself only requires the functions used in this file.

## 5. Minimal CSS

Create `static/css/weather.css` and include it from the destination base template:

```css
.weather-page {
  display: grid;
  gap: 1rem;
  max-width: 1440px;
  margin: 0 auto;
}

.weather-location-bar,
.weather-panel {
  background: #ffffff;
  border: 1px solid #d9e1e5;
  border-radius: 8px;
  box-shadow: 0 4px 18px rgba(35, 55, 65, 0.06);
}

.weather-location-bar {
  display: flex;
  align-items: end;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 1rem;
}

.weather-location-bar label {
  display: grid;
  gap: 0.3rem;
  min-width: 150px;
}

.weather-location-bar label span,
.weather-stat-label,
.weather-source {
  color: #60717a;
  font-size: 0.78rem;
}

.weather-location-bar input {
  min-height: 2.3rem;
  border: 1px solid #cbd6da;
  border-radius: 5px;
  padding: 0.45rem 0.6rem;
}

.weather-button {
  min-height: 2.3rem;
  border: 0;
  border-radius: 5px;
  padding: 0.45rem 0.8rem;
  color: #ffffff;
  background: #217a52;
  cursor: pointer;
}

.weather-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.weather-button-secondary {
  color: #27434f;
  background: #edf2f3;
}

.weather-source {
  margin-left: auto;
}

.weather-stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.weather-stat {
  display: grid;
  gap: 0.25rem;
  min-height: 108px;
  padding: 1rem;
  border-radius: 8px;
  color: #ffffff;
}

.weather-stat strong {
  font-size: 1.65rem;
}

.weather-stat-temperature { background: #c76335; }
.weather-stat-humidity { background: #2b7f9f; }
.weather-stat-wind { background: #3d8b62; }
.weather-stat-rain { background: #3c739b; }
.weather-stat .weather-stat-label { color: rgba(255, 255, 255, 0.82); }

.weather-content-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
  gap: 1rem;
}

.weather-panel-header {
  padding: 0.8rem 1rem;
  border-bottom: 1px solid #e3e9eb;
  color: #28434d;
  font-weight: 700;
}

.weather-chart-wrap {
  height: 330px;
  padding: 1rem;
}

.weather-advisory {
  min-height: 190px;
  padding: 1rem;
  color: #40545c;
}

.weather-advisory p {
  margin: 0 0 0.75rem;
}

.weather-advisory-panel > .weather-button {
  margin: 0 1rem 1rem;
}

.forecast-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(125px, 1fr));
  gap: 0.75rem;
  padding: 1rem;
}

.forecast-card {
  display: grid;
  gap: 0.35rem;
  min-height: 130px;
  padding: 0.8rem;
  border: 1px solid #d9e1e5;
  border-radius: 6px;
  color: #40545c;
}

.forecast-card span,
.forecast-card small {
  color: #718189;
  font-size: 0.78rem;
}

.forecast-card b {
  color: #c76335;
  font-size: 1.1rem;
}

.weather-empty {
  color: #718189;
}

@media (max-width: 800px) {
  .weather-stat-grid,
  .weather-content-grid {
    grid-template-columns: 1fr 1fr;
  }

  .weather-content-grid {
    display: grid;
  }

  .weather-chart-panel,
  .weather-advisory-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 520px) {
  .weather-stat-grid {
    grid-template-columns: 1fr 1fr;
  }

  .weather-source {
    width: 100%;
    margin-left: 0;
  }
}
```

Add this stylesheet to the shared layout:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/weather.css') }}">
```

## 6. Optional AI Sowing Advice Endpoint

The weather page can work without AI. The `Ask` button expects an existing endpoint:

```text
POST /api/chat/message
Content-Type: application/json
```

Request:

```json
{
  "message": "Based on the current weather, can I sow seeds tomorrow? Give practical farming advice.",
  "latitude": 20.5937,
  "longitude": 78.9629
}
```

Expected success response:

```json
{
  "reply": "...weather-aware farming advice..."
}
```

If the destination project does not have an AI chat endpoint, remove the `Ask` button and `askWeatherQuestion()` function, or point it at the destination project's assistant endpoint.

For a Watsonx-backed implementation, the server should fetch weather with `get_weather()`, convert it using `weather_to_text()`, add that text to the prompt, and keep IBM credentials server-side.

## 7. Navigation Link

Add this to the destination dashboard navigation:

```html
<a href="/weather">Weather</a>
```

## 8. Install and Run

From the destination project's virtual environment:

```powershell
pip install Flask requests
python app.py
```

Open:

```text
http://127.0.0.1:5000/weather
```

The destination app must provide:

- Flask template and static file configuration.
- `render_template` import for the page route.
- Chart.js loaded before `weather.js`.
- The `/api/weather` Blueprint registration.
- HTTPS in production if browser geolocation is used.

## 9. Acceptance Checklist

- [ ] `/weather` renders without JavaScript console errors.
- [ ] `/api/weather/current` returns `current`, `forecast`, and `source`.
- [ ] Invalid coordinates return HTTP 400.
- [ ] Open-Meteo failures return clearly identifiable fallback data.
- [ ] Current weather cards update after Refresh.
- [ ] Seven-day chart and forecast cards render.
- [ ] Advisory changes for heat, cold, rain, and high wind.
- [ ] Geolocation updates latitude/longitude and reloads weather.
- [ ] AI sowing advice works or the optional button is removed.
- [ ] Mobile layout remains readable at narrow widths.

## 10. Production Notes

- Cache weather responses briefly to reduce provider traffic.
- Add rate limiting to the endpoint.
- Log provider failures without logging user secrets.
- Display the last-updated timestamp and data source.
- Consider returning HTTP 503 instead of mock data when stale data would be unsafe.
- Validate coordinates server-side even if the browser already validates them.
- Keep all external API keys server-side; Open-Meteo currently does not require one.
