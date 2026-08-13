# Complaint Management System

> A full-stack AI-powered complaint management platform built with React + FastAPI + LangGraph + Groq.

---

## 📁 Monorepo Structure

```
complaint-mgmt-system/
├── frontend/          # React 18 + Vite + Redux Toolkit
├── backend/           # FastAPI + LangGraph + Groq
└── README.md
```

---

## 🛠 Tech Stack

### Frontend — `/frontend`

| Concern         | Technology                              |
|-----------------|-----------------------------------------|
| UI Framework    | React 18                                |
| Build Tool      | Vite                                    |
| State Management| Redux Toolkit + React-Redux             |
| Typography      | Inter (via `@fontsource/inter`)         |
| API Client      | Native `fetch` wrapper (`src/api/`)     |

**Source layout:**
```
src/
├── app/          # Redux store configuration
├── api/          # API client / fetch wrappers
├── features/     # Redux slices + feature-level components (one folder per domain)
└── components/   # Shared, reusable UI components
```

---

### Backend — `/backend`

| Concern         | Technology                                  |
|-----------------|---------------------------------------------|
| API Framework   | FastAPI + Uvicorn                           |
| Database        | PostgreSQL (via SQLAlchemy async + asyncpg) |
| Migrations      | Alembic                                     |
| Settings        | pydantic-settings (`.env` file)             |
| AI Agents       | LangGraph (StateGraph-based pipelines)      |
| LLM Provider    | Groq                                        |
| LLMs Available  | `gemma2-9b-it` · `llama-3.3-70b-versatile` |
| HTTP Client     | httpx                                       |

**Source layout:**
```
app/
├── main.py        # FastAPI app entry point, CORS middleware
├── api/           # Route handlers (APIRouter)
├── models/        # SQLAlchemy ORM models
├── schemas/       # Pydantic request/response schemas
├── agents/        # LangGraph agent graphs & nodes
├── db/            # DB engine, session, base
└── core/          # Config (settings), security utilities
```

> **Why `requirements.txt` over Poetry?**
> `requirements.txt` was chosen for simplicity and maximum compatibility with deployment environments (Docker, Railway, Render, etc.) that natively support `pip install -r requirements.txt` without any extra tooling. Switch to Poetry if you need dependency groups, lock-file reproducibility, or workspace features.

---

## 🤖 LangGraph Agent Architecture (Planned)

Complaint triage and routing will be powered by **LangGraph** stateful agent graphs:

- **Triage Agent** — classifies complaint type and urgency using `gemma2-9b-it` (fast)
- **Resolution Agent** — drafts resolution suggestions using `llama-3.3-70b-versatile` (high-quality)
- **Escalation Node** — routes complex complaints to human agents

---

## 🚀 Getting Started

### Prerequisites

- Node.js ≥ 18
- Python ≥ 3.11
- PostgreSQL

### Frontend

```bash
cd frontend
npm install
cp .env.example .env        # set VITE_API_BASE_URL
npm run dev                 # http://localhost:5173
```

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env        # set DATABASE_URL and GROQ_API_KEY
uvicorn app.main:app --reload --port 8000
```

API docs auto-generated at: `http://localhost:8000/docs`

---

## 🔑 Environment Variables

| Variable         | Location           | Description                          |
|------------------|--------------------|--------------------------------------|
| `VITE_API_BASE_URL` | `frontend/.env` | Backend base URL                    |
| `DATABASE_URL`   | `backend/.env`     | PostgreSQL connection string         |
| `GROQ_API_KEY`   | `backend/.env`     | Groq API key for LLM access          |

---

## 📌 Roadmap

- [ ] Database schema & Alembic migrations
- [ ] Authentication (JWT)
- [ ] Complaint submission & tracking API
- [ ] LangGraph triage agent implementation
- [ ] Frontend complaint dashboard
- [ ] Admin panel for resolution management
- [ ] Real-time status updates (WebSocket)
