# MedRAG System Execution & Commands Guide

This guide provides a step-by-step process with exact terminal commands to set up, configure, verify, and run all components of the MedRAG application.

---

## 📋 Prerequisites

Ensure you have the following installed on your machine:
- **Node.js** (v20+)
- **Python** (3.11+)
- **Docker Desktop** (latest version, running)
- **Git**

---

## 🛠️ Step-by-Step Setup and Launch

### Step 1: Open Docker Desktop
Ensure the Docker daemon is active. On macOS, you can launch Docker from the command line:
```bash
open -a Docker
```
*(Wait 10-15 seconds for the daemon to start before moving to the next step).*

---

### Step 2: Spin Up Infrastructure (Docker Containers)
From the root of the project (`MedRAG/`), run the container stack containing **Qdrant** (Vector Database), **PostgreSQL pgvector** (Full-text & Metadata Database), and **Redis** (Cache & Task broker):
```bash
docker-compose up -d
```
Verify that all services are active and healthy:
```bash
docker-compose ps
```

---

### Step 3: Configure Environment Variables
Create the backend environment file from the provided example:
```bash
cp .env.example backend/.env
```
Open `backend/.env` and update the key variables. Example of a fully functional **Gemini + Local Embeddings** configuration:
```env
# ── LLM (Google Gemini Studio) ──────────────────
GEMINI_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-2.0-flash

# ── Embeddings (Local Free Model) ───────────────
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
QDRANT_VECTOR_SIZE=384

# ── Databases ───────────────────────────────────
QDRANT_URL=http://localhost:6333
DATABASE_URL=postgresql+asyncpg://medrag_user:medrag_pass@localhost:5433/medrag
REDIS_URL=redis://localhost:6379

# ── PubMed Access ───────────────────────────────
NCBI_API_KEY=your_ncbi_api_key_here
NCBI_EMAIL=your_email@domain.com
```

---

### Step 4: Set Up & Verify the Python Backend Environment
Navigate to the `backend/` directory, set up your Python virtual environment, install dependencies, and run the verification test suite:

```bash
# Navigate to backend
cd backend

# Create virtual environment (if not already done)
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run full system validation tests
pytest
```
Ensure all 26 integration, retriever, and hallucination guard tests pass cleanly.

---

### Step 5: Start the Backend Server
Launch the FastAPI application development server:
```bash
# Assuming you are in backend/ with venv active
uvicorn app.main:app --reload --port 8000
```
- **API Server URL**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Step 6: Start the Frontend Application
Open a new terminal window or tab, navigate to the `frontend/` directory, install package dependencies, and run the Vite server:
```bash
# Navigate to frontend from the root project directory
cd frontend

# Install packages
npm install

# Start Vite dev server
npm run dev
```
- **Local Application URL**: [http://localhost:5173/](http://localhost:5173/)

---

### Step 7: Seed Initial Medical Literature (Required!)
Since the database starts empty, you must index literature for topics you wish to query. You can do this by submitting a simple HTTP POST request using `curl` or by using the Swagger interface at `/docs`:

```bash
# Index Metformin literature for diabetes
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "type 2 diabetes mellitus management metformin",
    "max_results": 50
  }'

# Index ACE Inhibitors literature for hypertension via Trip Database
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "hypertension treatment ACE inhibitors guidelines",
    "max_results": 20,
    "sources": ["trip"]
  }'
```

---

## 🔄 Optional: Start the Weekly Publications Auto-Updater
To start Celery workers that poll PubMed every Sunday at 02:00 UTC and automatically index the latest medical literature:

```bash
# Terminal 1 — Start Celery Worker
celery -A app.ingestion.tasks worker --loglevel=info

# Terminal 2 — Start Celery Beat Scheduler
celery -A app.ingestion.tasks beat --loglevel=info
```
*(Requires Redis to be running via Docker).*
