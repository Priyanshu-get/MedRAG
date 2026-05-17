# MedRAG — Hallucination-Free Medical Evidence Assistant

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-DC143C?style=flat-square)
![Claude](https://img.shields.io/badge/LLM-Claude%20Sonnet%204-FF6B35?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**A production-grade RAG chat system that answers medical queries exclusively from peer-reviewed literature.**  
Zero hallucination tolerance — if evidence doesn't exist, the system says so.

[Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [API Reference](#-api-reference) · [Configuration](#️-configuration) · [Tech Stack](#-tech-stack)

</div>

---

## ✨ Features

- 🔬 **Evidence-only answers** — every response cites `[Source N]` from PubMed, PMC, Semantic Scholar, or ClinicalTrials.gov
- 🛡️ **7-layer hallucination guard** — LLM-as-judge validates context *before* generating any answer
- 📚 **Hybrid retrieval** — dense (Qdrant semantic) + sparse (PostgreSQL BM25/FTS) merged with Reciprocal Rank Fusion
- 🔄 **Medical query expansion** — Claude rewrites queries into MeSH-optimized PubMed search variants
- ⚡ **Redis caching** — repeat queries return instantly with zero LLM cost
- 🧬 **Cross-encoder re-ranking** — `ms-marco-MiniLM-L-6-v2` precision scoring
- 🎨 **Premium dark UI** — glassmorphism, confidence bar, citation cards, backend status indicator
- 📅 **Weekly auto-updates** — Celery scheduler ingests latest PubMed publications every Sunday

---

## 🏗️ Architecture

<div align="center">
  <img src="docs/architecture.png" alt="MedRAG Architecture Diagram" width="680" />
</div>

The system is built around a **7-stage pipeline** that processes every query sequentially, with hard exit gates at stages 1 and 5 to prevent hallucination:

### Anti-Hallucination Strategy (7 Layers)

| Layer | Where | What it does |
|---|---|---|
| 1 | `pipeline.py` | Abort immediately if 0 chunks retrieved |
| 2 | `hallucination_guard.py` | LLM-as-judge checks context sufficiency; aborts if confidence < 0.65 |
| 3 | `answer_generator.py` | 10-rule system prompt banning all external knowledge |
| 4 | `answer_generator.py` | Post-generation: reject answer if it contains 0 `[Source N]` citations |
| 5 | Guard prompt | Flags tangentially related but non-specific evidence as insufficient |
| 6 | `pipeline.py` | 3 rigid "I don't know" response templates for each failure scenario |
| 7 | Every response | Mandatory medical disclaimer appended unconditionally |

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| Docker Desktop | Latest | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Git | Any | [git-scm.com](https://git-scm.com) |

### 1 — Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/MedRAG.git
cd MedRAG
```

### 2 — Set Up Environment Variables

```bash
cp .env.example backend/.env
```

Open `backend/.env` and fill in your API keys (see [Configuration](#️-configuration) for details):

```env
ANTHROPIC_API_KEY=sk-ant-api03-...      # Required
OPENAI_API_KEY=sk-...                   # Required if EMBEDDING_PROVIDER=openai
NCBI_API_KEY=your_ncbi_key             # Free — get at ncbi.nlm.nih.gov/account/
NCBI_EMAIL=your@email.com              # Required by NCBI
```

### 3 — Start Infrastructure (Docker)

```bash
docker-compose up -d
```

This starts:
- **Qdrant** at `http://localhost:6333` (vector database)
- **PostgreSQL 16 + pgvector** at `localhost:5432` (metadata + full-text search)
- **Redis** at `localhost:6379` (query cache + Celery broker)

Verify all services are healthy:
```bash
docker-compose ps
```

### 4 — Start the Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies (~3-5 min first time, downloads ML models)
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --port 8000
```

✅ API running at: `http://localhost:8000`  
📖 Interactive docs: `http://localhost:8000/docs`

### 5 — Start the Frontend

```bash
# Open a new terminal
cd frontend
npm install
npm run dev
```

✅ UI running at: `http://localhost:5173`

### 6 — Seed Medical Literature (Required Before First Query!)

The vector store starts empty. Index some literature before querying:

```bash
# Option A — via curl
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "hypertension treatment ACE inhibitors guidelines",
    "max_results": 50,
    "sources": ["pubmed", "semantic_scholar"]
  }'

# Option B — via Swagger UI
# Open http://localhost:8000/docs → POST /api/v1/ingest
```

**Recommended topics to seed initially:**

```bash
# Run each of these ingestion calls to build a useful knowledge base
curl -X POST http://localhost:8000/api/v1/ingest -H "Content-Type: application/json" \
  -d '{"topic": "type 2 diabetes mellitus management metformin", "max_results": 50}'

curl -X POST http://localhost:8000/api/v1/ingest -H "Content-Type: application/json" \
  -d '{"topic": "myocardial infarction thrombolysis treatment", "max_results": 50}'

curl -X POST http://localhost:8000/api/v1/ingest -H "Content-Type: application/json" \
  -d '{"topic": "COVID-19 long term effects post-acute sequelae", "max_results": 50}'

curl -X POST http://localhost:8000/api/v1/ingest -H "Content-Type: application/json" \
  -d '{"topic": "immunotherapy checkpoint inhibitors NSCLC", "max_results": 50}'
```

---

## ⚙️ Configuration

All configuration lives in `backend/.env`. Copy from `.env.example` to get started.

### Required Keys

| Variable | Description | Where to get |
|---|---|---|
| `ANTHROPIC_API_KEY` | Powers the query rewriter, hallucination guard, and answer generator | [console.anthropic.com](https://console.anthropic.com) |
| `NCBI_API_KEY` | PubMed search (10 req/sec with key, 3/sec without) | [ncbi.nlm.nih.gov/account](https://www.ncbi.nlm.nih.gov/account/) — **free** |
| `NCBI_EMAIL` | Required by NCBI E-utilities terms of service | Your email address |

### Embedding Provider (Choose One)

#### Option A — OpenAI (Best Quality, Paid)
```env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
QDRANT_VECTOR_SIZE=3072
```
Cost: ~$0.13 per million tokens

#### Option B — Local BAAI/bge (Free, Runs on CPU)
```env
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
QDRANT_VECTOR_SIZE=1024
```
No API key needed. Downloads ~1.3 GB model on first run.

### Full Configuration Reference

```env
# ── LLM ───────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...                      # Only needed if EMBEDDING_PROVIDER=openai
LLM_MODEL=claude-sonnet-4-20250514         # Claude model for RAG pipeline

# ── Embeddings ─────────────────────────────────────────────────────────────────
EMBEDDING_PROVIDER=openai                  # "openai" | "local"
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
LOCAL_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5

# ── Qdrant (Vector Database) ───────────────────────────────────────────────────
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=medrag_docs
QDRANT_VECTOR_SIZE=3072                    # 3072 for OpenAI, 1024 for BAAI/bge

# ── PostgreSQL (Metadata + Full-Text Search) ───────────────────────────────────
DATABASE_URL=postgresql+asyncpg://medrag_user:medrag_pass@localhost:5432/medrag

# ── Redis (Cache + Task Queue) ─────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379
CACHE_TTL_SECONDS=3600                     # How long to cache query results (1 hour)

# ── PubMed / NCBI ──────────────────────────────────────────────────────────────
NCBI_API_KEY=your_ncbi_key                 # Free at ncbi.nlm.nih.gov/account/
NCBI_EMAIL=your@email.com                  # Required by NCBI ToS

# ── Semantic Scholar ────────────────────────────────────────────────────────────
SEMANTIC_SCHOLAR_API_KEY=                  # Optional — increases rate limits

# ── RAG Pipeline Thresholds ────────────────────────────────────────────────────
MAX_RETRIEVED_CHUNKS=20                    # Chunks fetched from vector DB per query
RERANK_TOP_K=5                             # Top N chunks passed to answer generator
SIMILARITY_THRESHOLD=0.72                  # Min cosine similarity for retrieval
HALLUCINATION_CONFIDENCE_THRESHOLD=0.65    # Min guard confidence to allow an answer
MAX_CONTEXT_TOKENS=8000                    # Max tokens in assembled context window

# ── App ────────────────────────────────────────────────────────────────────────
APP_ENV=development                        # "development" | "production"
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 📡 API Reference

### `POST /api/v1/chat`

Submit a medical query.

**Request:**
```json
{
  "query": "What is the first-line treatment for hypertension?",
  "max_sources": 5
}
```

**Response (evidence found):**
```json
{
  "query": "What is the first-line treatment for hypertension?",
  "answer": "ACE inhibitors are recommended as first-line agents... [Source 1]. Thiazide diuretics are an alternative... [Source 2].",
  "sources": [
    {
      "title": "2014 Evidence-Based Guideline for the Management of High Blood Pressure",
      "authors_short": "James PA et al.",
      "journal": "JAMA",
      "pub_date": "2014-02",
      "citation_url": "https://doi.org/10.1001/jama.2013.284427",
      "abstract_snippet": "Recommendations for antihypertensive treatment...",
      "pmid": "24352797",
      "rerank_score": 2.31
    }
  ],
  "confidence": 0.87,
  "has_answer": true,
  "source_count": 2,
  "disclaimer": "This response is derived solely from indexed peer-reviewed literature..."
}
```

**Response (no evidence found — no hallucination):**
```json
{
  "answer": "No relevant medical literature was found for this query...",
  "sources": [],
  "confidence": 0.08,
  "has_answer": false
}
```

### `POST /api/v1/ingest`

Index medical literature for a topic.

```json
{
  "topic": "CRISPR gene therapy sickle cell disease",
  "max_results": 50,
  "sources": ["pubmed", "pmc", "semantic_scholar", "clinical_trials"]
}
```

Valid sources: `pubmed`, `pmc`, `semantic_scholar`, `clinical_trials`

### `GET /api/v1/health`

```json
{
  "status": "healthy",
  "qdrant": "ok",
  "postgres": "ok",
  "redis": "ok",
  "embedding_provider": "openai",
  "llm_model": "claude-sonnet-4-20250514",
  "indexed_documents": 8432
}
```

---

## 🧪 Running Tests

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

**Test coverage:**

| File | Tests |
|---|---|
| `test_hallucination_guard.py` | Guard rejects empty/irrelevant context; accepts relevant context; enforces confidence rule; stress tests with 4 fictional diseases |
| `test_rag_pipeline.py` | Zero-retrieval exit; guard rejection; full grounded answer; disclaimer always present |
| `test_retriever.py` | RRF merging; deduplication; PostgreSQL row normalization; graceful error handling |
| `test_ingestion.py` | Chunker unique IDs; PubMed XML parser; text cleaner HTML stripping |

---

## 🔄 Automated Weekly Updates (Celery)

Start background workers for weekly PubMed ingestion:

```bash
# Terminal 1 — Celery worker
cd backend && source venv/bin/activate
celery -A app.ingestion.tasks worker --loglevel=info

# Terminal 2 — Beat scheduler (runs every Sunday 02:00 UTC)
celery -A app.ingestion.tasks beat --loglevel=info
```

Covers 16 medical topics including cardiology, oncology, neurology, infectious disease, and more.

---

## 📁 Project Structure

```
MedRAG/
├── .env.example                     # Environment variable template
├── docker-compose.yml               # Qdrant + PostgreSQL + Redis
├── README.md
│
├── backend/
│   ├── .env                         # Your API keys (git-ignored)
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── init.sql                     # PostgreSQL schema
│   ├── Dockerfile
│   │
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── config.py                # Pydantic settings
│   │   │
│   │   ├── rag/                     # 7-stage pipeline
│   │   │   ├── pipeline.py          # Orchestrator
│   │   │   ├── query_rewriter.py    # Stage 1
│   │   │   ├── retriever.py         # Stage 2
│   │   │   ├── reranker.py          # Stage 3
│   │   │   ├── context_builder.py   # Stage 4
│   │   │   ├── hallucination_guard.py # Stage 5 ← Critical
│   │   │   ├── answer_generator.py  # Stage 6
│   │   │   └── citation_injector.py # Stage 7
│   │   │
│   │   ├── ingestion/
│   │   │   ├── sources/             # PubMed, PMC, SemanticScholar, ClinicalTrials, CrossRef
│   │   │   ├── chunker.py
│   │   │   ├── embedder.py
│   │   │   ├── indexer.py
│   │   │   └── tasks.py             # Celery jobs
│   │   │
│   │   ├── db/                      # Qdrant, PostgreSQL, Redis clients
│   │   ├── models/                  # Pydantic schemas
│   │   ├── routers/                 # /chat, /ingest, /health
│   │   └── utils/                   # Logger, NER, text cleaner
│   │
│   └── tests/                       # pytest test suite
│
└── frontend/
    ├── src/
    │   ├── App.tsx
    │   ├── types.ts
    │   ├── api/medrag.ts            # Axios client
    │   ├── store/chatStore.ts       # Zustand
    │   ├── hooks/                   # useChat, useBackendStatus
    │   └── components/              # ChatWindow, MessageBubble, CitationCard,
    │                                # ConfidenceBar, QueryInput, NoAnswerCard
    ├── vite.config.ts
    └── package.json
```

---

## ⚠️ Important Limitations

1. **Research tool only** — not a clinical diagnostic system; always include a licensed clinician
2. **Index-bound** — can only answer from indexed literature; run `/ingest` for new topics
3. **PMC full-text** — only open-access articles have full-text; others use abstracts only
4. **NCBI rate limits** — 10 req/sec with API key; 3/sec without (always register a key)
5. **Context window** — assembled context capped at 8,000 tokens per query
6. **HIPAA** — query logs store only SHA-256 hashes, never raw queries; review before clinical use
7. **Cold start** — first query after startup is slow (~30s) while reranker model loads into memory

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25499/) for PubMed access
- [Semantic Scholar API](https://api.semanticscholar.org/) for open research graph
- [Qdrant](https://qdrant.tech/) for the vector database
- [Anthropic](https://anthropic.com/) for Claude claude-sonnet-4-20250514
- [sentence-transformers](https://www.sbert.net/) for the cross-encoder reranker

---

*MedRAG v1.0 — For academic and research use. Not for clinical deployment without regulatory review.*
