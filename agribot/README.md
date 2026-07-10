# 🌾 AgriBot – AI Agent for Smart Farming Advice

> **IBM Hackathon – Problem Statement No. 9**
> Powered by IBM Watsonx.ai · IBM Granite Foundation Models · RAG · Flask · Bootstrap 5

---

## ✨ Features

| Module | Description |
|---|---|
| 🤖 **AI Chat** | ChatGPT-style interface with chat history, typing animation, markdown, copy button |
| 🌤️ **Weather** | Real-time weather dashboard via Open-Meteo API (no key needed) + farming advisory |
| 🌱 **Soil Analysis** | AI-powered crop & fertilizer recommendations from NPK + soil data |
| 🌾 **Crop Advisor** | Top 5 crop recommendations by season, soil, location, rainfall |
| 🐛 **Pest Detection** | AI diagnosis from symptoms + image upload with organic/chemical treatment |
| 📊 **Market Prices** | Live mandi prices with trend indicators and AI Q&A |
| 📚 **Knowledge Base** | Upload PDFs/TXT, build RAG vector index, semantic search |
| 👨‍🌾 **Farmer Profile** | Store personal and farm details |
| 🎛️ **Dashboard** | Unified view with weather, quick chat, market snapshot, soil health |

---

## 🚀 Quick Start

### 1. Clone / enter the project
```bash
cd agribot
```

### 2. Create virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note:** `sentence-transformers` and `faiss-cpu` are optional but recommended for semantic RAG search.
> Without them the app falls back to keyword search automatically.

### 4. Configure environment
```bash
cp .env.example .env
```
Open `.env` and fill in:
```
IBM_API_KEY=<your IBM Cloud API key>
IBM_PROJECT_ID=<your Watsonx.ai project ID>
IBM_WATSONX_URL=https://au-syd.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
```

### 5. Run the application
```bash
python app.py
```
Open your browser at **http://localhost:5000**

The console will print the active Granite model:
```
[AgriBot] ✅  Active Watsonx model: ibm/granite-3-8b-instruct
```

---

## 🔑 IBM Cloud Lite Setup

1. Create a free IBM Cloud account at https://cloud.ibm.com
2. Navigate to **Watsonx.ai** → Create a project
3. Go to **IAM** → **API Keys** → Create a new key
4. Copy your **Project ID** from Watsonx project settings
5. Use **Sydney (au-syd)** region: `https://au-syd.ml.cloud.ibm.com`
6. Paste both values into your `.env` file

### Supported Lite-Compatible Granite Models (auto-fallback order)
| Model ID | Description |
|---|---|
| `ibm/granite-3-8b-instruct` | ✅ Best quality – recommended |
| `ibm/granite-3-2b-instruct` | ✅ Faster, lower tokens |
| `ibm/granite-13b-instruct-v2` | ✅ Alternative |
| `ibm/granite-13b-chat-v2` | ✅ Fallback |

If the configured model is unavailable, AgriBot automatically tries the next one.

---

## 📂 Project Structure

```
agribot/
├── app.py                     # Flask app factory + page routes + seed data
├── config.py                  # All configuration + AGENT_INSTRUCTIONS
├── models.py                  # SQLAlchemy database models
├── requirements.txt
├── .env.example
├── .gitignore
│
├── routes/                    # Flask Blueprint API routes
│   ├── chat_routes.py         # POST /api/chat/message, GET /api/chat/history
│   ├── weather_routes.py      # GET /api/weather/current
│   ├── soil_routes.py         # POST /api/soil/analyze
│   ├── crop_routes.py         # POST /api/crop/recommend
│   ├── pest_routes.py         # POST /api/pest/detect
│   ├── market_routes.py       # GET /api/market/prices
│   ├── profile_routes.py      # GET/POST /api/profile/
│   └── rag_routes.py          # POST /api/rag/upload, /search, /documents
│
├── services/
│   ├── watsonx_service.py     # IBM Watsonx.ai SDK wrapper + model fallback
│   ├── weather_service.py     # Open-Meteo free weather API
│   └── market_service.py      # Crop mandi price service
│
├── rag/
│   ├── rag_pipeline.py        # FAISS + sentence-transformers RAG engine
│   └── seeds/                 # Auto-generated agricultural knowledge texts
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Sidebar + topbar layout
│   ├── dashboard.html
│   ├── chat.html
│   ├── weather.html
│   ├── soil.html
│   ├── crop.html
│   ├── pest.html
│   ├── market.html
│   ├── knowledge.html
│   └── profile.html
│
├── static/
│   ├── css/style.css          # Main stylesheet (glassmorphism, dark mode)
│   └── js/
│       ├── app.js             # Global helpers (sidebar, dark mode, apiFetch)
│       ├── dashboard.js
│       ├── chat.js
│       ├── weather.js
│       ├── soil.js
│       ├── crop.js
│       ├── pest.js
│       ├── market.js
│       ├── knowledge.js
│       └── profile.js
│
└── uploads/                   # Farmer uploaded images and documents
```

---

## 🤖 Customising AgriBot

Edit `AGENT_INSTRUCTIONS` in [`config.py`](config.py) to change:
- Personality & tone
- Farming expertise areas
- Languages
- Organic vs chemical preference
- Response format
- Safety rules

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/chat/message` | Send a message to AgriBot |
| GET | `/api/chat/history` | Get session chat history |
| POST | `/api/chat/clear` | Clear chat history |
| GET | `/api/weather/current?lat=&lon=` | Get weather data |
| POST | `/api/soil/analyze` | Analyze soil composition |
| POST | `/api/crop/recommend` | Get crop recommendations |
| POST | `/api/pest/detect` | Detect pests/diseases |
| GET | `/api/market/prices` | Get all crop prices |
| POST | `/api/rag/upload` | Upload & index a document |
| POST | `/api/rag/search` | Semantic search knowledge base |
| GET | `/api/rag/documents` | List indexed documents |
| GET | `/health` | Health check + active model ID |

---

## 🛡️ Error Handling

| Error | Handling |
|---|---|
| Invalid API Key | Friendly error message in chat |
| Missing Project ID | Startup warning in console |
| Unsupported Model | Automatic fallback to next model |
| Network Failure | User-friendly error + retry |
| Empty Input | Input validation before API call |
| Missing Documents | Knowledge base works without uploads |

---

## 📦 Tech Stack

- **Backend:** Python 3.10+, Flask 3.x, SQLAlchemy, SQLite
- **AI:** IBM Watsonx.ai SDK, IBM Granite 3.x (Instruct)
- **RAG:** sentence-transformers (all-MiniLM-L6-v2), FAISS
- **Frontend:** Bootstrap 5.3, Chart.js 4.x, marked.js, Bootstrap Icons
- **Weather:** Open-Meteo (free, no API key)

---

## 🏆 IBM Hackathon Compliance

- ✅ IBM Watsonx.ai + Granite Foundation Models
- ✅ IBM Cloud Lite compatible (au-syd region)
- ✅ Latest IBM Watsonx.ai SDK (`ibm-watsonx-ai>=1.1.2`)
- ✅ No deprecated APIs used
- ✅ Auto model fallback if configured model is unsupported
- ✅ Secrets only in `.env` — never hardcoded
- ✅ RAG pipeline with agricultural knowledge base
- ✅ Complete production-ready application

---

*Built for IBM Hackathon – Problem Statement No. 9 | AgriBot v1.0*
