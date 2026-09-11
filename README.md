# ClipForge AI

**Turn long-form videos into short-form content using local AI.**

ClipForge AI is a free, open-source, self-hosted application that analyzes long videos, discovers meaningful and engaging moments, ranks potential clips, and lets you export them as Shorts — all running locally on your machine with no paid APIs or cloud services required.

---

## ✨ Features (MVP Roadmap)

- 🎬 Upload long-form videos (MP4, MKV, MOV, WEBM)
- 🎙️ Local transcription via faster-whisper (no API keys)
- 🧠 Intelligent clip detection using NLP and scoring rules
- 📊 Clip Quality Score (0–100) with explainable reasons
- ✂️ Preview, edit, and export clips via FFmpeg
- 🔍 Semantic transcript search
- 🖥️ Modern web interface (Next.js + Tailwind CSS)

---

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend   │────▶│   Workers    │
│  (Next.js)   │◀────│  (FastAPI)  │◀────│ (Background) │
└─────────────┘     └──────┬──────┘     └──────────────┘
                           │
                    ┌──────┴──────┐
                    │  PostgreSQL  │
                    │  + pgvector  │
                    └─────────────┘
```

---

## 📋 Requirements

- **Python** 3.11+
- **Node.js** 18+
- **FFmpeg** (must be on PATH)
- **Git**
- **PostgreSQL** (Phase 2+)
- **Redis** (Phase 2+)

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone <repo-url>
cd "ClipForge AI"
```

### 2. Set up environment

```bash
cp .env.example .env
```

### 3. Install backend dependencies

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 4. Run the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 5. Verify

Open [http://localhost:8000/api/health](http://localhost:8000/api/health) in your browser.

---

## 📁 Project Structure

```
ClipForge AI/
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── api/          # API route handlers
│   │   ├── core/         # Configuration & shared logic
│   │   ├── models/       # Database models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── utils/        # Utility functions
│   │   └── workers/      # Background job processors
│   └── tests/            # Backend tests
├── frontend/             # Next.js frontend (Phase 5)
├── storage/              # Local file storage
├── docker/               # Docker configuration (post-MVP)
├── docs/                 # Documentation
└── scripts/              # Helper scripts
```

---

## ⚙️ Configuration

All configuration is managed through environment variables. See [`.env.example`](.env.example) for all available options with descriptions.

---

## 🗺️ Roadmap

- [x] Phase 1: Foundation (project structure, FastAPI backend)
- [ ] Phase 2: Video Processing (upload, validation, audio extraction)
- [ ] Phase 3: Local Transcription (faster-whisper)
- [ ] Phase 4: Clip Intelligence Engine (scoring, ranking, deduplication)
- [ ] Phase 5: Web Interface (Next.js dashboard, clip editor)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
