# 🎬 ClipForge AI

**Turn long-form videos into viral short-form content using 100% local AI.**

ClipForge AI is a free, open-source, self-hosted application that analyzes long-form videos, podcasts, and webinars, discovers the most engaging moments, scores and ranks them across 6 psychological dimensions, and exports ready-to-publish 9:16 vertical Shorts with blurred background padding and burned-in stylized captions.

> 🔒 **100% Offline & Private:** Zero cloud APIs. No OpenAI, Claude, or Gemini keys required. No subscriptions. Everything runs directly on your computer using free open-source tools (`faster-whisper`, `FFmpeg`, NLP heuristics).

---

## ✨ Key Capabilities

### 1. 🎙️ Local Speech Recognition (Faster-Whisper)
- Powered by `faster-whisper` running locally on your CPU or GPU.
- **Voice Activity Detection (VAD)**: Automatically skips long silences and dead air.
- **Timestamped Segments**: Produces frame-accurate word/segment boundaries.
- **Automatic Caching**: Transcripts are persisted as JSON to avoid redundant re-processing.

### 2. 🧠 Clip Intelligence Engine (0–100 Viral Quality Score)
- **Natural Boundary Detection**: Extracts 15–90 second clips aligned to natural sentence and thought boundaries (optimizing for the 30–60s sweet spot).
- **6-Dimension Scoring System**:
  - **Hook Strength (0–20 pts)**: Detects opening questions, curiosity gaps, surprising statistics, and power words.
  - **Information Value (0–20 pts)**: Rewards actionable advice, tutorials, step-by-step logic, and specific data.
  - **Emotional Interest (0–15 pts)**: Identifies surprise, passion, strong opinions, and humor.
  - **Standalone Context (0–20 pts)**: Rewards self-contained ideas and penalizes references to other video chapters.
  - **Completeness (0–15 pts)**: Verifies clean sentence beginnings, thought arcs, and resolved conclusions.
  - **Pacing (0–10 pts)**: Evaluates conversational speech rate (words per second) and pause frequency.
- **Deduplication**: Suppresses overlapping moments (>50% temporal overlap) and similar phrasing (>70% Jaccard similarity), keeping only the highest-scoring candidate.
- **Explainable Reasons**: Transparent insights into why each moment was picked.

### 3. ✂️ Video Cutting & 9:16 Shorts Export Engine
- **Frame-Accurate Cutting**: Powered by FFmpeg stream-accurate seeking.
- **9:16 Vertical Framing Modes**:
  - **`blur_background` (Creator Standard)**: 1080x1920 canvas with the source video scaled to fit the width and centered, surrounded by a zoomed, blurred ambient background of the video itself.
  - **`crop`**: Center-crops the video to fill the full 1080x1920 vertical canvas.
  - **`fit`**: Letterboxes with clean black bars.
  - **`1:1` Square & `original`**: Supports square feeds and source aspect ratio cuts.
- **Automated Caption Burn-in**:
  - Generates styled Advanced SubStation Alpha (`.ass`) and standard `.srt` subtitle files.
  - Formatted with bold, high-contrast typography (Yellow, White, Cyan, Neon Green) with thick outlines.
  - Placed in the vertical **safe zone** (above platform UI buttons on YouTube Shorts, Instagram Reels, and TikTok).
  - Burned directly into the MP4 via FFmpeg's `libass` filter.

### 4. 🖥️ Modern Web Interface (Apple Design & Liquid Glass)
- Clean, dark-mode dashboard built with React, TypeScript, and Vite.
- Drag-and-drop file upload with format validation and file metadata preview.
- **Interactive Transcript Viewer**: Click any speech segment to immediately seek the video.
- **Viral Clips Gallery**: Cards with circular score badges, 6-dimension breakdown, and reason tags.
- **Live 9:16 Phone Simulator**: Real-time simulated phone frame showing blurred background framing and animated captions as the video plays.
- **One-Click Export**: Instant modal customizer and direct `.mp4` download.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Modern Web Frontend (Vite + React)          │
│   • Apple Liquid Glass UI  • Interactive Transcript Viewer   │
│   • 9:16 Shorts Simulator  • Viral Clip Gallery & Scorer     │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON API (:3000 -> :8000)
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Service                  │
│  /api/videos   /api/transcription   /api/clips   /api/export│
└───────┬──────────────────────┬──────────────────────┬───────┘
        │                      │                      │
┌───────▼────────┐     ┌───────▼────────┐     ┌───────▼───────┐
│ Video Pipeline │     │ Whisper Engine │     │ Clip Engine   │
│ • Validation   │     │ • faster-whisper│    │ • 6D Scoring  │
│ • FFprobe Meta │     │ • VAD Filter   │     │ • Deduplicator│
│ • Audio Extract│     │ • JSON Caching │     │ • CandidateGen│
└────────────────┘     └────────────────┘     └───────┬───────┘
                                                      │
                                              ┌───────▼───────┐
                                              │ Shorts Export │
                                              │ • FFmpeg 9:16 │
                                              │ • Blur Bars   │
                                              │ • ASS Captions│
                                              └───────────────┘
```

---

## 📋 Prerequisites

Make sure you have the following installed on your system:

- **Python** 3.11+ (Tested on Python 3.13)
- **Node.js** 18+ (Tested on Node.js 24)
- **FFmpeg** 5.0+ installed and added to your system `PATH`
- **Git**

Verify your environment:
```bash
python --version
node --version
ffmpeg -version
```

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/clipforge-ai.git
cd "ClipForge AI"
```

### 2. Configure Environment
```bash
# Copy example configuration
cp .env.example .env
```

### 3. Backend Setup
```bash
cd backend

# Create and activate Python virtual environment
python -m venv venv

# Windows (PowerShell / Command Prompt):
venv\Scripts\activate

# macOS / Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Frontend Setup
```bash
cd ../frontend

# Install node dependencies
npm install
```

---

## 📖 Complete Step-by-Step Tutorial

### Step 1: Start the Backend Server
In your first terminal (inside `backend/` with `venv` activated):
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
You should see:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000
```
Interactive API documentation will be available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Step 2: Start the Frontend Application
In your second terminal:
```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 3000
```
Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

### Step 3: Uploading & Discovering Clips

1. **Upload a Video**:
   - On the homepage, drag and drop any long-form video (`.mp4`, `.mov`, `.webm`, `.mkv`), or click to select a file.
   - *Quick Test*: Click the **"Try With Sample Video"** button to immediately run a demo using the built-in sample file without uploading anything!
2. **Automated Analysis**:
   - The app automatically steps through:
     1. Video validation and format inspection via `ffprobe`.
     2. 16 kHz mono audio extraction via `ffmpeg`.
     3. Local speech transcription via `faster-whisper` with VAD silence removal.
     4. Candidate grouping and 6-dimension viral scoring.
3. **Explore Ranked Clips**:
   - When processing completes, you enter the **Studio Workspace**.
   - Review candidate clips ranked by their **Clip Quality Score (0–100)**.
   - Click **"Quality Score Breakdown"** on any card to see individual points for Hook, Information, Emotion, Context, Completeness, and Pacing.
4. **Interactive Transcript**:
   - Click the **"Full Transcript"** tab to view all transcribed speech segments.
   - Click any timestamp badge to instantly jump the video player to that exact line.

---

### Step 4: Previewing in the 9:16 Shorts Simulator

1. In the right column, select **"9:16 Shorts Simulator"**.
2. Click **"Preview"** or **"Play"** on any clip.
3. Watch the simulated vertical smartphone frame render the clip with:
   - Centered crisp video framing.
   - Ambient blurred background bars.
   - Synchronized stylized captions appearing at the bottom safe zone in real-time!

---

### Step 5: Exporting & Downloading Shorts

1. Click **"Export Short"** on any clip card.
2. The export drawer opens with customization options:
   - **Aspect Ratio**: Select `9:16 Shorts`, `1:1 Square`, or `Original`.
   - **9:16 Framing Layout**:
     - `Blurred Background` (recommended for podcasts/landscape videos)
     - `Center Crop` (zooms and fills the vertical canvas)
     - `Letterbox (Fit)` (black borders)
   - **Captions**: Toggle caption burning and select your font highlight color (`Electric Yellow`, `Clean White`, `Cyber Cyan`, or `Neon Green`).
3. Click **"Render & Export Short"**.
4. FFmpeg will cut the clip, generate the custom `.ass` subtitle file, apply the filtergraph, and burn the captions into an optimized `.mp4`.
5. Click **"Download MP4"** to save your ready-to-post Short to your computer!
6. All exported clips remain accessible in the **"Exported Shorts"** tab for instant redownload at any time.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status and app version |
| `POST` | `/api/videos/upload` | Upload video file (multipart form data) |
| `GET` | `/api/videos/{id}/metadata` | Fetch resolution, duration, codec, and fps |
| `POST` | `/api/videos/{id}/extract-audio`| Extract 16kHz mono WAV audio track |
| `POST` | `/api/transcription/{id}/transcribe` | Run local faster-whisper speech-to-text |
| `GET` | `/api/transcription/{id}` | Retrieve cached timestamped transcript |
| `POST` | `/api/clips/{id}/generate` | Generate and rank clips via 6D scoring engine |
| `GET` | `/api/clips/{id}` | Retrieve saved clip candidates |
| `GET` | `/api/clips/{id}/{clip_index}` | Retrieve a specific clip candidate |
| `POST` | `/api/export/{id}` | Cut and render 9:16 Short with captions |
| `GET` | `/api/export/{export_id}` | Get export metadata and file status |
| `GET` | `/api/export/{export_id}/download` | Direct MP4 file download |
| `GET` | `/api/export/list/{id}` | List all exported Shorts for a video |

---

## 🧪 Running Automated Tests

ClipForge AI includes a comprehensive test suite covering all services, scoring modules, video pipelines, and API endpoints.

To run all 67 tests:
```bash
cd backend
venv\Scripts\activate
python -m pytest tests/ -v
```

Test coverage breakdown:
- `tests/test_health.py`: 3 tests (FastAPI app lifespan & health checks)
- `tests/test_video.py`: 22 tests (File validation, metadata probing, audio extraction)
- `tests/test_transcription.py`: 12 tests (Faster-whisper service, VAD, segment persistence)
- `tests/test_clips.py`: 19 tests (Text cleaner, 6 scorers, candidate grouping, deduplication)
- `tests/test_export.py`: 11 tests (ASS/SRT subtitle generation, 9:16 FFmpeg layouts, export API)

---

## 📂 Directory Structure

```text
ClipForge AI/
├── backend/
│   ├── app/
│   │   ├── api/                  # REST API routers (videos, transcription, clips, export)
│   │   ├── core/                 # Config & settings (Pydantic BaseSettings)
│   │   ├── schemas/              # Pydantic data transfer models
│   │   └── services/
│   │       ├── video_service.py         # FFmpeg/ffprobe upload & audio extraction
│   │       ├── transcription_service.py # Faster-whisper model caching & VAD
│   │       ├── subtitle_service.py      # Styled ASS & SRT caption generation
│   │       ├── export_service.py        # 9:16 layout rendering & clip cutting
│   │       └── clip_engine/             # NLP Viral Discovery Engine
│   │           ├── text_cleaner.py      # Punctuation & filler removal
│   │           ├── candidate_generator.py # Sliding-window clip segmenter
│   │           ├── duplicate_detector.py  # Temporal overlap & Jaccard deduplication
│   │           ├── engine.py            # Master discovery orchestrator
│   │           └── scoring/             # 6 scoring dimensions (Hook, Info, etc.)
│   ├── tests/                    # 67 automated pytest test cases
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api.ts                # Fully-typed API client
│   │   ├── App.tsx               # Master studio dashboard & phone simulator
│   │   ├── App.css               # Studio layout & 9:16 phone mockup styling
│   │   └── index.css             # Apple Design token system & Liquid Glass styles
│   ├── public/                   # Static assets & demo sample video
│   ├── vite.config.ts            # Vite config with backend proxy
│   └── package.json
├── storage/                      # Local video, audio, transcript, and export files
└── README.md
```

---

## 📄 License

This project is open-source software licensed under the [MIT License](LICENSE).
