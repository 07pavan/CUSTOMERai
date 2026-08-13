# Backend — FastAPI

See the root README for full stack documentation.

## Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy env file
copy .env.example .env

# Run dev server
uvicorn app.main:app --reload --port 8000
```
