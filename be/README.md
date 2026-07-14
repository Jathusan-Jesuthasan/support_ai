# SupportAI Backend Platform (Version 1.0)

A multi-tenant, enterprise-grade customer support platform designed to ingest knowledge documents, run real-time vector search (RAG) and generative AI completions, host custom widget endpoints, and track customer analytics.

---

## 🚀 Technology Stack

- **Framework**: Python 3.13 + FastAPI + Async Programming
- **Database**: MongoDB Atlas + Motor (Async driver)
- **Caching & Queue**: Redis + Celery + Celery Beat
- **AI Integrations**: Google Gemini API + Custom Grounding Auditing
- **Authentication**: JWT RFC 7519 + Argon2 Hashing
- **Quality Standards**: Ruff, Mypy, and Pytest (100% pass)

---

## 📁 Repository Structure (Feature-Based Architecture)

```text
app/
├── auth/          # Authentication & Sessions
├── company/       # Multi-tenant workspace management
├── membership/    # RBAC and invitations
├── knowledge/     # Document chunking & background Celery workers
├── ai/            # Google Gemini LLM & embedding providers
├── chat/          # Chat conversation engine & WebSocket streams
├── widget/        # Brand customization & domain whitelist CORS configuration
├── analytics/     # SaaS telemetry log aggregates
├── core/          # App settings, DB connections, global middleware
└── shared/        # Base models and standard envelopes
```

---

## 🛠️ Local Development & Setup

### Prerequisites
- Python 3.13
- MongoDB (Running locally or MongoDB Atlas URI)
- Redis Server (Running locally or Redis URL)

### Installation
1. Clone the repository and navigate to the backend directory:
   ```bash
   cd support-ai/be
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install required libraries:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment variables:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to supply your `GEMINI_API_KEY`, custom `JWT_SECRET_KEY`, and MongoDB/Redis connection URIs.*

### Running the App
Start the development server:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Swagger UI documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Running Tests
Execute the comprehensive pytest test suite:
```bash
pytest -v
```

---

## 🐳 Docker Deployment

To spin up the entire production-ready system (FastAPI API, Celery Workers, Celery Beat scheduler, MongoDB, and Redis) inside Docker:

1. Build and run the services:
   ```bash
   docker compose up -d
   ```
2. Verify services are healthy:
   ```bash
   docker compose ps
   ```
3. View runtime logs:
   ```bash
   docker compose logs -f
   ```
4. Shut down the environment:
   ```bash
   docker compose down
   ```

---

## 🧪 CI/CD & Linting

Automated quality guardrails are configured via GitHub Actions. You can run checks locally before submitting code:

- **Linting check**: `ruff check .`
- **Typing safety check**: `mypy .`
- **Clean compilation verification**: `python -m compileall app/`
