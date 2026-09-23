# IBM Agri Dashboard Integration Specification

This document describes the feature set currently implemented in `agribot`. It is intended as a handoff for reproducing the same module in another dashboard.

## 1. Product Scope

AgriBot is a farmer-facing dashboard with nine feature areas:

1. Overview dashboard
2. AI farming chat
3. Weather and farm advisory
4. Manual soil analysis
5. Soil Intelligence report
6. Crop recommendation
7. Pest and disease detection
8. Market prices
9. Farmer profile and agricultural knowledge base

The UI is server-rendered HTML with page-specific JavaScript. The backend is Flask with SQLAlchemy and Blueprint-based JSON APIs.

## 2. Navigation and UI Shell

### Shared shell

- Responsive Bootstrap 5 layout.
- Left sidebar navigation and top bar.
- Active navigation item per route.
- Dark/light theme persisted in browser `localStorage` under `agribot-theme`.
- Mobile sidebar toggle.
- Shared `apiFetch()` wrapper that parses JSON, logs API errors, and exposes status/error metadata.
- Markdown rendering for AI output with `marked`.
- Chart rendering with Chart.js.
- Toast and loading-state helpers.
- IBM Granite/model badge and `/health` model status.

### Routes/pages

| Page | Route | Main purpose |
|---|---|---|
| Overview | `/` | Weather snapshot, market snapshot, quick chat, forecast, soil indicator, alerts |
| AI Chat | `/chat` | Full conversational farming assistant |
| Weather | `/weather` | Current conditions, 7-day forecast, advisory, geolocation |
| Soil Analysis | `/soil` | NPK/pH form, AI recommendations, analysis history |
| Soil Intelligence | `/soil-intel` | Optional soil image, location/season, optional lab values, report and confidence |
| Crop Advisor | `/crop` | Crop recommendations from season, soil, location, rainfall |
| Pest Detection | `/pest` | Crop symptoms and optional image, diagnosis and treatment |
| Market Prices | `/market` | Searchable price table, chart, AI market question |
| Knowledge Base | `/knowledge` | Upload/index documents, semantic search, document list, clear index |
| Farmer Profile | `/profile` | Personal and farm details |

## 3. Overview Dashboard Sections

The overview page contains:

- Four quick stats: temperature, humidity, wind speed, rainfall.
- Quick Ask AgriBot panel with suggested questions and link to full chat.
- Market Snapshot with first eight crop prices and trend percentage.
- Seven-day forecast chart combining maximum temperature and rainfall.
- Soil Health indicator with N/P/K progress bars.
- Soil Intelligence quick-access panel.
- Smart Alerts panel.

Current implementation notes:

- Weather and market snapshot are API-backed.
- Soil Health bars are static placeholder values in `dashboard.js` and are not connected to the latest `SoilAnalysis` record.
- Smart Alerts are static hard-coded messages; a production port should replace them with computed or API-backed alerts.
- Dashboard weather uses configured default coordinates unless the weather page overrides them.

## 4. Feature Specifications

### 4.1 AI Farming Chat

UI sections:

- Chat message history.
- Suggested question chips.
- Textarea with Enter-to-send and Shift+Enter newline behavior.
- Send button, clear-history button, typing indicator, copy response button.
- Model badge loaded from `/health`.
- Dashboard also embeds a compact version of the chat.

Input fields:

- `message` required string.
- Optional `session_id`, `latitude`, `longitude`, and `soil_info`.

Behavior:

1. Resolve the browser session ID.
2. Load up to 12 recent messages for prompt context.
3. Retrieve up to three relevant RAG chunks.
4. Fetch weather context for supplied/default coordinates.
5. Add optional soil context.
6. Build a model-specific farming prompt.
7. Generate an answer with up to 700 tokens and temperature 0.7.
8. Persist user and assistant messages.

Endpoints:

- `POST /api/chat/message`
  - Request JSON: `{ message, session_id?, latitude?, longitude?, soil_info? }`
  - Success: `{ reply, session_id }`
  - Empty message: HTTP 400, `{ error }`
  - AI failure: HTTP 503, `{ error, error_type, debug_traceback? }`
- `GET /api/chat/history`
  - Returns array of `{ id, role, content, created_at }`.
- `POST /api/chat/clear`
  - Returns `{ status: "cleared" }`.
- `GET /health`
  - Returns `{ status, model, init_error }`.
- `GET /api/chat/debug-config`
  - Debug-only; returns sanitized configuration metadata. Never expose raw credentials.

### 4.2 Weather and Farm Advisory

UI sections:

- Latitude and longitude inputs.
- Refresh button and browser geolocation button.
- Current cards: temperature, humidity, wind, precipitation.
- Seven-day Chart.js chart.
- Daily forecast cards with date, condition, max/min temperature, precipitation.
- Rule-based farming advisory.
- Button to ask the AI whether sowing is advisable tomorrow.

Endpoint:

- `GET /api/weather/current?lat={latitude}&lon={longitude}`
- Response:

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
  ]
}
```

External integration:

- Open-Meteo forecast API, no API key required.
- Request current fields: temperature, relative humidity, wind speed, precipitation, weather code.
- Request daily fields: max/min temperature, precipitation sum, weather code.
- Seven forecast days, timezone `auto`, ten-second HTTP timeout.
- On failure, backend returns mock weather data; the port should clearly label mock/fallback data if this behavior is retained.

Advisory rules currently include heat, cold, rainfall in the next three days, and high wind warnings.

### 4.3 Manual Soil Analysis

UI sections:

- Soil type selector.
- pH input from 0 to 14.
- Nitrogen, phosphorus, potassium inputs in kg/ha.
- Analyze button with spinner.
- AI result area.
- Previous analyses table.

Input fields:

- `soil_type` required string.
- `ph` optional numeric.
- `nitrogen` optional numeric, kg/ha.
- `phosphorus` optional numeric, kg/ha.
- `potassium` optional numeric, kg/ha.

Endpoints:

- `POST /api/soil/analyze` with JSON fields above.
  - Success: `{ analysis, id }`.
  - Missing `soil_type`: HTTP 400, `{ error }`.
  - AI failure: HTTP 503, `{ error }`.
- `GET /api/soil/history`
  - Returns `{ id, soil_type, ph, nitrogen, phosphorus, potassium, result, created_at }[]`, newest first, maximum 20.

AI output should cover top crops, fertilizer, irrigation, and soil improvement.

### 4.4 Soil Intelligence

UI sections:

1. Optional image upload with drag/drop, preview, filename, remove action.
2. Required state selector and optional district.
3. Required season selector: Kharif, Rabi, Zaid, Year Round.
4. Collapsible optional lab values: pH, N, P, K.
5. Analyze button and IBM Watsonx/Granite attribution.
6. Confidence bar and metadata.
7. Optional visual soil estimate card.
8. Full report with copy action.
9. Previous analyses table.

Input format:

`multipart/form-data` fields:

- `state` required.
- `district` optional.
- `season` required.
- `ph` optional.
- `nitrogen` optional.
- `phosphorus` optional.
- `potassium` optional.
- `image` optional file.

Accepted soil image extensions: `jpg`, `jpeg`, `png`, `webp`, `bmp`.

Endpoint:

- `POST /api/soil-intel/analyze`
  - Missing state or season: HTTP 400, `{ error }`.
  - Success: `{ id, image_analysis, report, confidence, has_image, state, district, season }`.
  - AI failure: HTTP 503, `{ error }`.
- `GET /api/soil-intel/history`
  - Returns stored analysis records, newest first, maximum 10.
- `GET /api/soil-intel/states`
  - Returns the supported Indian state/territory strings.

Report sections required by the current prompt:

- Estimated Soil Profile.
- Top 5 Recommended Crops, including suitability, expected yield, sowing window.
- Fertilizer Recommendations, organic first, chemical fallback, doses, micronutrients.
- Irrigation Suggestions, method, schedule, water requirement.
- Organic Farming Tips.
- Sowing Calendar for the top three crops.
- Important disclaimer directing the user to a KVK or soil testing lab.

Confidence calculation currently starts at 40 and adds: district 10, image 15, pH 10, N 8, P 8, K 9; maximum 95. It must remain explicitly an AI estimate and never be presented as laboratory certainty.

Important limitation: the current text-only Granite models do not inspect image pixels. The uploaded filename/location/season are used to generate a text-based regional estimate. A true image diagnosis requires a vision-capable model or separate computer-vision service.

### 4.5 Crop Recommendation

UI sections:

- Season selector.
- Soil type selector.
- Location/state text field.
- Expected rainfall selector.
- Recommendation result panel and loading state.

Input JSON:

```json
{
  "season": "Kharif (Jun-Oct)",
  "soil": "Loamy",
  "location": "Maharashtra",
  "rainfall": "Medium (500-1000mm)"
}
```

Endpoint:

- `POST /api/crop/recommend`
  - At least one of season, soil, or location is required.
  - Success: `{ recommendation, id }`.
  - AI failure: HTTP 503, `{ error }`.

The AI prompt asks for the top five crops, expected yield, water requirement, and market demand.

### 4.6 Pest and Disease Detection

UI sections:

- Crop name input.
- Symptoms textarea.
- Optional crop image upload with drag/drop and preview.
- Diagnosis and treatment result panel.

Input format: `multipart/form-data`.

- `crop_name` optional string, defaults to `unknown crop`.
- `symptoms` optional string.
- `image` optional `jpg`, `jpeg`, `png`, or `webp` file.

Endpoint:

- `POST /api/pest/detect`
  - Success: `{ diagnosis, id }`.
  - AI failure: HTTP 503, `{ error }`.

AI response requirements:

1. Most likely pest or disease.
2. Organic treatment.
3. Chemical treatment and dosage.
4. Prevention.
5. When to seek expert help.

Important limitation: like Soil Intelligence, the current route saves the image but does not send image pixels to a vision model. Treat image-based diagnosis as unavailable until a vision integration is added.

### 4.7 Market Prices

UI sections:

- Crop search/filter.
- Refresh action.
- Price table: crop, today, yesterday, change, trend.
- Top-eight bar chart.
- AI market question input.
- Dashboard market snapshot.

Endpoints:

- `GET /api/market/prices`
  - Returns array entries:

```json
{
  "crop": "Wheat",
  "today_price": 2200,
  "yesterday_price": 2180,
  "week_ago_price": 2150,
  "unit": "Rs/quintal",
  "trend": "up",
  "change": 20,
  "change_pct": 0.9
}
```

- `GET /api/market/price/{crop_name}`
  - Returns one entry or HTTP 404 `{ error }`.

Current data source: a static base-price map with seeded daily noise, not a live mandi feed. To make this production-ready, replace `market_service.py` with an Agmarknet/data.gov.in adapter and add source timestamp, market/location, min price, max price, modal price, and freshness metadata.

The AI market question calls `/api/chat/message` and appends the first ten current prices as prompt context.

### 4.8 Farmer Profile

UI sections:

- Full name.
- Village.
- District.
- State.
- Farm size in acres.
- Soil type.
- Main crop.
- Irrigation type.
- Save confirmation alert.

Endpoints:

- `GET /api/profile/` or `/api/profile`
  - Returns one profile object or `{}`.
- `POST /api/profile/save`
  - JSON fields: `name`, `village`, `district`, `state`, `farm_size`, `soil_type`, `main_crop`, `irrigation`.
  - Name is required in the UI.
  - Success: `{ status: "saved", profile }`.

Profile object fields:

`id`, `name`, `village`, `district`, `state`, `farm_size`, `soil_type`, `main_crop`, `irrigation`.

Current behavior stores the latest single profile globally. A multi-user port should associate it with an authenticated user or tenant.

### 4.9 RAG Knowledge Base

UI sections:

- Document upload/dropzone.
- Upload and index status with chunk count.
- Semantic search input and results.
- Indexed document list with source and chunk count.
- Clear-all action.
- Built-in seed guide list.

Endpoints:

- `POST /api/rag/upload` multipart field `file`.
  - Accepted configured document types: `pdf`, `txt`, `docx`.
  - Success: `{ status: "indexed", chunks, file }`.
- `POST /api/rag/search` JSON `{ query, top_k? }`.
  - Query required; default top_k is 3.
  - Returns `{ text, source, score }[]`.
- `GET /api/rag/documents`
  - Returns `{ source, chunks }[]`.
- `POST /api/rag/clear`
  - Returns `{ status: "cleared" }`.

RAG implementation:

- Chunk size default 500 words.
- Chunk overlap default 50 words.
- Embeddings use `sentence-transformers` model `all-MiniLM-L6-v2`.
- Vector search uses FAISS `IndexFlatL2`.
- Metadata is persisted in `metadata.pkl`; vector index in `faiss.index`.
- If sentence-transformers or FAISS is unavailable, the system falls back to keyword overlap search.
- PDF extraction uses PyMuPDF. The current extractor handles PDF and text/Markdown directly; DOCX is listed in the UI/config but is not parsed by `_extract_text()` and should be implemented before promising DOCX indexing.
- Startup seeds crop, fertilizer, pest, soil, and irrigation guides.

## 5. Backend Data Model

Minimum tables/entities:

### FarmerProfile

- `id`: integer primary key
- `name`: required string
- `village`, `district`, `state`: strings
- `farm_size`: float, acres
- `soil_type`, `main_crop`, `irrigation`: strings
- `created_at`, `updated_at`: timestamps

### ChatMessage

- `id`: integer primary key
- `session_id`: indexed string
- `role`: `user` or `assistant`
- `content`: text
- `created_at`: timestamp

### SoilAnalysis

- `id`, `soil_type`, `ph`, `nitrogen`, `phosphorus`, `potassium`, `result`, `created_at`

### CropRecommendation

- `id`, `season`, `soil`, `location`, `rainfall`, `result`, `created_at`

### PestDetection

- `id`, `image_path`, `crop_name`, `result`, `created_at`

### SoilIntelligence

- `id`, `image_path`, `state`, `district`, `season`, `ph`, `nitrogen`, `phosphorus`, `potassium`, `image_analysis`, `full_report`, `confidence`, `created_at`

## 6. API Integration Architecture

Recommended port structure:

```text
Dashboard UI
  -> shared API client / auth / error normalization
  -> feature endpoints
       -> chat orchestration
            -> profile context
            -> weather service
            -> RAG retrieval
            -> Watsonx generation
       -> soil/crop/pest/soil-intel prompt services
       -> market provider adapter
       -> profile repository
       -> RAG index service
  -> database and object/file storage
```

Keep these boundaries:

- `routes/controllers`: validate input, map HTTP to service calls, return stable JSON.
- `services`: external APIs, prompt construction, calculations, model calls.
- `repositories/models`: persistence only.
- `frontend adapters`: one API client, one renderer per feature, explicit loading/error/empty states.
- `storage`: private uploaded files with generated names; never use raw user filenames as storage keys.

For a different backend, preserve the endpoint semantics and response field names first. The other dashboard can change URL prefixes or language/framework after adding an API adapter.

## 7. Configuration and Dependencies

Environment variable names used by the source:

- `IBM_API_KEY`
- `IBM_PROJECT_ID`
- `IBM_WATSONX_URL`
- `WATSONX_MODEL_ID`
- `SECRET_KEY`
- `FLASK_DEBUG`
- `DATABASE_URI`
- `RAG_CHUNK_SIZE`
- `RAG_CHUNK_OVERLAP`
- `RAG_TOP_K`
- `DEFAULT_LATITUDE`
- `DEFAULT_LONGITUDE`

Core dependencies:

- Flask, Flask-SQLAlchemy, SQLAlchemy
- `ibm-watsonx-ai`
- `python-dotenv`
- `requests`
- Werkzeug
- Optional/recommended: sentence-transformers, faiss-cpu, PyMuPDF, python-docx
- Production server: gunicorn

Watsonx integration requirements:

- Create `Credentials(url, api_key)`.
- Create `ModelInference(model_id, credentials, project_id)`.
- Probe candidate models and cache the first working model.
- Call `generate_text(prompt=..., params={"max_new_tokens": ..., "temperature": ...})`.
- Parse either a string response or `{ "results": [{ "generated_text": "..." }] }`.
- Keep API keys server-side only.
- Return friendly client errors while logging full server tracebacks.

## 8. Security and Production Requirements

The current project is a prototype. A production port should add:

- Authentication and tenant/user ownership for profiles, histories, uploads, and reports.
- CSRF protection for cookie-authenticated browser POSTs.
- MIME sniffing plus extension validation, file size limits, malware scanning, and private object storage.
- Generated upload names to avoid collisions and path traversal.
- HTML sanitization before injecting model Markdown into the DOM.
- Rate limits and quotas for AI calls, document indexing, and image uploads.
- Server-side schema validation and numeric range validation for all pH/NPK/coordinate fields.
- Request IDs, structured logs, timeouts, retries, and circuit breakers for external services.
- Explicit provenance and freshness on weather and market data.
- Clear disclaimers: AI output is advisory, soil image estimates are not lab results, and treatment/dosage must be locally verified.
- Do not expose `/api/chat/debug-config` outside development.

## 9. Porting Checklist

- [ ] Add shared layout, navigation, theme, chart, Markdown, upload, and error components.
- [ ] Add dashboard overview sections and wire weather/market APIs.
- [ ] Add chat with session persistence and RAG/weather context.
- [ ] Add weather page and geolocation flow.
- [ ] Add manual soil analysis and history.
- [ ] Add Soil Intelligence multipart flow, confidence display, report copy, and history.
- [ ] Add crop recommendation form and result renderer.
- [ ] Add pest form/upload and diagnosis renderer.
- [ ] Add market table, filter, chart, and AI question flow.
- [ ] Add farmer profile form and persistence.
- [ ] Add RAG upload, indexing, search, list, and clear operations.
- [ ] Configure Watsonx credentials/model fallback on the server.
- [ ] Add database migrations for the six domain entities.
- [ ] Add object/file storage and upload validation.
- [ ] Replace static market data and dashboard placeholders before production.
- [ ] Add automated API contract tests and frontend smoke tests.

## 10. Suggested Acceptance Tests

- Dashboard loads with weather and market data, and displays an intentional fallback state when either provider fails.
- Chat rejects empty messages, persists a conversation, reloads history, and clears history.
- Chat includes RAG, weather, and optional soil context in the generated prompt.
- Soil, crop, pest, and Soil Intelligence forms validate required fields and show loading/error states.
- Soil Intelligence never reports confidence above 95 and always displays the AI-estimate disclaimer.
- Multipart image uploads reject unsupported extensions and oversized files.
- Market search filters rows without changing the source dataset.
- Profile save/load round trips all fields.
- RAG upload returns indexed chunk count; search returns source and score; clear removes all documents.
- Watsonx failures are friendly to users and do not leak credentials.
