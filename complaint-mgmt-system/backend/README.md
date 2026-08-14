# ⚙️ Backend — FastAPI & LangGraph Agent Service

> **High-performance asynchronous backend providing LangGraph multi-agent triage, Groq LLM integrations, document OCR/parsing, and RESTful QMS endpoints.**

---

## 🏗 Architecture & Modules

```
app/
├── main.py                  # FastAPI app factory, CORS, exception handlers
├── agents/                  # LangGraph Multi-Agent Architecture
│   ├── graph.py             # StateGraph definition and node compilation
│   ├── llm.py               # Groq LLM client with automatic 8B fallback
│   ├── state.py             # TypedDict AgentState representation
│   └── nodes/               # 7 autonomous triage agent nodes
│       ├── intake_parser.py
│       ├── completeness_checker.py
│       ├── duplicate_detector.py
│       ├── risk_classifier.py
│       ├── root_cause_recommender.py
│       ├── capa_recommender.py
│       └── summary_generator.py
├── api/                     # REST API Routers
│   ├── complaints.py        # Complaint ingestion, listing, detail & status PATCH
│   ├── copilot.py           # Conversational chat, field extraction & suggestions
│   ├── analytics.py         # Summary metrics, risk breakdowns, defect trends
│   ├── documents.py         # Multipart PDF & TXT document upload and parsing
│   └── assessments.py       # Quality assessment query endpoints
├── core/
│   └── config.py            # Pydantic Settings (.env configuration)
├── db/
│   ├── base.py              # DeclarativeBase class
│   └── session.py           # Async engine & sessionmaker (aiosqlite/asyncpg)
├── models/                  # SQLAlchemy ORM Models
│   ├── complaint.py
│   ├── assessment.py
│   ├── root_cause.py
│   ├── capa.py
│   └── document.py
└── schemas/                 # Pydantic Request/Response validation models
```

---

## 🚀 Setup & Execution

### 1. Environment Configuration

Create a `.env` file in the `backend` directory:

```env
DATABASE_URL=sqlite+aiosqlite:///./complaints.db
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_FALLBACK_MODEL=llama-3.1-8b-instant
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### 2. Dependency Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Running the Server

```bash
# Start FastAPI with hot-reload
uvicorn app.main:app --reload --port 8000
```

Interactive OpenAPI documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 🧪 Testing

```bash
# Run all unit tests
pytest app/agents/nodes/ -v

# Run verification test runner
python test_runner.py
```
