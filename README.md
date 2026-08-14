# 🏥 CUSTOMERai — AI-Powered Quality & Complaint Management System

> **Enterprise-grade Medical & Pharmaceutical Quality Management System (QMS) powered by LangGraph multi-agent intelligence, FastAPI, React 19, and Groq LLMs.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.0.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6.x-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.28-FF9900.svg)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/Groq-Llama%203.3%20%7C%20Gemma%202-F55036.svg)](https://groq.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.35-red.svg)](https://www.sqlalchemy.org)

---

## 🌟 Key Capabilities

- 🤖 **Interactive 3D Robot Copilot (`CustomerHelperAI`)**: Real-time conversational agent with animated thinking and talking states, capable of bi-directional synchronization with all 16+ complaint form fields.
- ⚡ **Autonomous 7-Stage LangGraph Agent Pipeline**:
  1. **Intake Parser**: Extracts structured metadata from unstructured text or uploaded documents (PDF, TXT, EML).
  2. **Completeness Evaluator**: Dynamically scores intake completeness and highlights missing critical data.
  3. **Duplicate & Similarity Detector**: Vector-based cosine similarity to identify related batches or recurring defects.
  4. **Risk & Severity Classifier**: Categorizes risk matrix levels, criticality, and FDA/MDR regulatory reportability.
  5. **Root Cause Recommender**: Formulates Ishikawa (Fishbone) and 5-Whys root cause hypotheses.
  6. **CAPA Action Generator**: Auto-generates targeted Corrective & Preventive Action plans with assignees and SLAs.
  7. **Executive QMS Summarizer**: Drafts formal complaint summaries and standardized regulatory disclosures.
- 📊 **Executive Quality Analytics Dashboard**: Real-time tracking of complaint volumes, severity distributions, product risk heatmaps, status lifecycles, and Mean Time to Resolution (MTTR).
- 🗂 **Advanced Complaint Management Portal**: Multi-column filtering, search, pagination, status lifecycle transitions, and document attachments.
- 🔄 **Multi-Model LLM Resilience**: Dynamic failover mechanism between high-reasoning models (`llama-3.3-70b-versatile`) and high-throughput low-latency fallbacks (`llama-3.1-8b-instant`).

---

## 🏗 System Architecture

```mermaid
flowchart TD
    subgraph Frontend ["Frontend (React 19 + Vite + Redux Toolkit)"]
        UI_Form["Complaint Intake Form (16+ Fields)"]
        UI_Dash["Executive Quality Analytics Dashboard"]
        UI_Table["Complaint Management Table"]
        UI_Copilot["Interactive 3D Avatar Copilot"]
    end

    subgraph Backend ["Backend API (FastAPI + SQLAlchemy)"]
        API_Routes["REST API (/api/v1)"]
        DB_Layer[(SQLite / PostgreSQL Database)]
        Doc_Parser["Document Ingestion Engine (pdfplumber)"]
    end

    subgraph AI_Engine ["LangGraph Multi-Agent Pipeline"]
        N1["1. Intake Parser Node"]
        N2["2. Completeness Evaluator Node"]
        N3["3. Duplicate Detector Node"]
        N4["4. Risk & Severity Classifier Node"]
        N5["5. Root Cause Analysis Node"]
        N6["6. CAPA Recommender Node"]
        N7["7. Summary Generator Node"]
    end

    subgraph LLM_Cloud ["Groq Cloud Infrastructure"]
        M1["Llama 3.3 70B Versatile (Primary)"]
        M2["Llama 3.1 8B Instant (Resilient Fallback)"]
    end

    UI_Form <-->|Live Bi-directional Sync| UI_Copilot
    UI_Form -->|Submit / Upload| API_Routes
    UI_Dash -->|Fetch Analytics| API_Routes
    UI_Table -->|Search / Filter / Update| API_Routes
    API_Routes --> DB_Layer
    API_Routes --> Doc_Parser
    API_Routes --> AI_Engine
    AI_Engine --> N1 --> N2 --> N3 --> N4 --> N5 --> N6 --> N7
    AI_Engine <--> LLM_Cloud
```

---

## 📁 Repository Structure

```
customerAI/
├── README.md                           # Main Project Overview & Architecture
├── .gitignore                          # Repository-level ignore rules
└── complaint-mgmt-system/
    ├── README.md                       # Subsystem Technical Documentation
    ├── frontend/                       # React 19 Frontend Web Application
    │   ├── src/
    │   │   ├── api/                    # RTK Query API endpoints & base queries
    │   │   ├── app/                    # Redux store configuration
    │   │   ├── components/             # Reusable UI & 3D Copilot Avatar components
    │   │   └── features/
    │   │       ├── complaints/         # Intake form & list views
    │   │       ├── copilot/            # Live chat, suggestions & form synchronization
    │   │       └── dashboard/          # Analytics metrics & Recharts visualizations
    │   ├── package.json
    │   └── vite.config.js
    ├── backend/                        # FastAPI Backend Application
    │   ├── app/
    │   │   ├── agents/                 # LangGraph state machine & 7 agent nodes
    │   │   ├── api/                    # Route controllers (complaints, copilot, analytics)
    │   │   ├── core/                   # App configuration & settings
    │   │   ├── db/                     # SQLAlchemy async database session & engine
    │   │   ├── models/                 # ORM models (Complaints, CAPA, RootCause, etc.)
    │   │   ├── schemas/                # Pydantic validation models
    │   │   └── main.py                 # FastAPI application factory & middleware
    │   ├── alembic/                    # Database migrations
    │   └── requirements.txt
    └── sample_data/                    # Standardized test complaints (.pdf, .txt, .eml)
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Node.js** ≥ 18.x
- **Python** ≥ 3.11
- **Groq API Key** (Get free at [console.groq.com](https://console.groq.com))

---

### 1. Backend Setup

```bash
# Navigate to backend directory
cd complaint-mgmt-system/backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

Ensure your `.env` contains:
```env
DATABASE_URL=sqlite+aiosqlite:///./complaints.db
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_FALLBACK_MODEL=llama-3.1-8b-instant
ENVIRONMENT=development
```

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```
API Documentation will be live at: `http://localhost:8000/docs`

---

### 2. Frontend Setup

```bash
# In a separate terminal, navigate to frontend directory
cd complaint-mgmt-system/frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env
```

Ensure your `frontend/.env` contains:
```env
VITE_API_BASE_URL=http://localhost:8000
```

Start the Vite development server:
```bash
npm run dev
```
Open your browser at: `http://localhost:5173`

---

## 📡 API Endpoint Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/complaints/` | Submit a new complaint and trigger AI triage |
| `GET` | `/api/v1/complaints/` | List complaints with search, pagination & filters |
| `GET` | `/api/v1/complaints/{id}` | Retrieve comprehensive complaint details |
| `PATCH` | `/api/v1/complaints/{id}` | Partial update of complaint fields |
| `POST` | `/api/v1/copilot/chat` | Chat with CustomerHelperAI copilot |
| `POST` | `/api/v1/copilot/extract-fields` | Auto-extract form fields from raw input text |
| `POST` | `/api/v1/copilot/suggest-improvements` | Get AI recommendations for missing fields |
| `GET` | `/api/v1/analytics/summary` | Aggregate KPI statistics for Quality Dashboard |
| `POST` | `/api/v1/documents/upload` | Ingest and parse PDF/TXT complaint attachments |

---

## 🧪 Testing & Verification

Run backend unit and agent verification test suite:
```bash
cd complaint-mgmt-system/backend
pytest app/agents/nodes/ -v
python test_runner.py
```

Run frontend build check & linting:
```bash
cd complaint-mgmt-system/frontend
npm run build
```

---

## 🛡 License

This project is licensed under the MIT License.
