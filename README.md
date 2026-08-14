# CUSTOMERai

A comprehensive AI-powered Complaint Management System.

This monorepo consists of a **React Frontend** and a **FastAPI Backend** powered by LangGraph and Groq.

## 📁 Project Structure
- `complaint-mgmt-system/frontend`: React 19 + Vite + Redux Toolkit application
- `complaint-mgmt-system/backend`: FastAPI + SQLAlchemy + LangGraph service

## 🛠 Tech Stack

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite 8
- **State Management**: Redux Toolkit & react-redux
- **HTTP Client**: Axios
- **UI & Typography**: Recharts, Inter Font (`@fontsource/inter`)
- **Linting**: Oxlint

### Backend
- **Framework**: FastAPI (v0.115.0) & Uvicorn (v0.30.6)
- **Database & ORM**: PostgreSQL / SQLite, SQLAlchemy (v2.0.35), asyncpg, Alembic
- **AI Agents**: LangGraph (v0.2.28), LangChain, Groq SDK
- **Data Processing**: scikit-learn, pdfplumber
- **Async & Tools**: aiofiles, httpx, pydantic-settings

## 🚀 Getting Started

Please see the [detailed setup instructions in the sub-project directory](complaint-mgmt-system/README.md).
