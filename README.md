# 🖋️ InkFlow

**An adaptive writing twin that removes AI slop, preserves your real voice, and guards your facts.**

[![Live Demo](https://img.shields.io/badge/Live_Demo-ink--flow--twin.vercel.app-16a34a?style=for-the-badge)](https://ink-flow-twin.vercel.app)
[![Backend API](https://img.shields.io/badge/Render_API-Online-amber?style=for-the-badge)](https://inkflow-backend-73hf.onrender.com/api/v1)
[![AI Engine](https://img.shields.io/badge/Open--Weight_AI-Groq_120B_%2F_20B-purple?style=for-the-badge)](https://groq.com)
[![Tests](https://img.shields.io/badge/Tests-Passing-blue?style=for-the-badge)](./backend/tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](./LICENSE)

---

## 🌟 What is InkFlow?

Most AI writing assistants make everyone sound identical. They flatten your sentences and pepper your drafts with synthetic clichés like *"delve"*, *"tapestry"*, *"in conclusion"*, and *"it is important to note"*. Generic "humanizers" aren't much better—they often just swap words with awkward synonyms or inject fake typos.

**InkFlow** takes a different approach: it creates your personal **writing twin**.

Through a quick 3-minute onboarding drill, InkFlow learns how you naturally write—your typical sentence lengths, how you transition between thoughts, and the punctuation quirks you love. When you feed it a rough draft or quick bullet points, it rewrites the text in your authentic cadence, verifies that your core facts didn't get scrambled, and continuously learns from your edits over time.

![InkFlow Studio Preview](frontend/src/assets/hero.png)

---

## 💡 Why Open-Weight Models?

1. **Your Words Stay Private**: Your personal emails, research drafts, and workplace memos are never fed back into closed corporate training sets. InkFlow runs on open-weight models (`openai/gpt-oss-120b` and `20b`) via Groq's high-speed cloud with zero data retention.
2. **Sounds Like You, Not a Corporate Memo**: Closed commercial models are tuned to sound uniform, safe, and generic. Open-weight models allow us to steer tone freely, preserving short punchy sentences, natural fragments, and genuine conversational transitions.
3. **Fair, Predictable Pricing**: Efficient open-weight models let us keep hosting costs low and offer simple, sustainable plans without charging users per token.

---

## ✨ Core Capabilities

- **3-Minute Voice Calibration Drill**: A short, timed exercise using three classic writing prompts (stream of consciousness, visual description, and personal narrative) to discover your natural sentence rhythm, vocabulary variety, and transition habits.
- **4-Stage Rewrite Pipeline**: Moves your writing through four clear steps: Ingestion & Expansion → Tone Transformation → Fact-Checking Gate → Light Grammar Polish.
- **Meaning Gate with Guided Retries**: If a rewrite accidentally changes a key date, name, or claim, InkFlow catches the drift, explains what changed, and automatically tries again. If it's still unsure, it flags the draft with an amber warning instead of crashing or changing your facts.
- **Punctuation Protection**: Never strips away your em-dashes, semicolons, or conversational commas. Your punctuation habits remain completely intact.
- **Adaptive Learning**: When you make manual edits in the studio, InkFlow watches for recurring patterns across multiple sessions before updating your profile. One-off typos or unique phrasing won't mess up your Style Genome.
- **Distraction-Free Studio**: Designed with warm porcelain tones inspired by Wispr Flow, featuring live slop keyword detection, character diffs, and real-time quota tracking.

---

## 🏗️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 19 + Vite 8 SPA)                                │
│                                                                                        │
│  [Navigation Dock] ──► [Voice Calibration Drill] ──► [Dual-Pane Transformation Studio] │
│          │                       │                                     │               │
│  [Writing Insights]      [60s Radial Timer]            [Live Slop Underlines & Diffs]  │
│          │                       │                                     │               │
│  [Google / Email Auth]           │                     [Phased Loading Messages]       │
└──────────┬───────────────────────┼─────────────────────────────────────┬───────────────┘
           │                       │                                     │
           ▼                       ▼                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        BACKEND API (FastAPI on Render.com)                             │
│                                                                                        │
│  [POST /api/v1/auth/sync]  [POST /api/v1/grill/submit]  [POST /api/v1/rewrite]         │
│  [GET  /api/v1/auth/me]    [GET  /api/v1/grill/prompts] [POST /api/v1/rewrite/accept]  │
│                                                         [POST /api/v1/payments/*]      │
│                                                                                        │
│  ├── In-Flight Weekly Quota Reset (resets every Monday at 00:00 UTC)                   │
│  ├── 4-Stage Sequential Rewrite Pipeline (Draft ─► Voice ─► Meaning Gate ─► Grammar)   │
│  ├── Automated Writing Evals (Slop Detection, Style Alignment, Semantic Check)         │
│  └── Multi-Session Recurrence Filter (requires repeat edits before updating profile)  │
└──────────┬─────────────────────────────────────────────────────────────┬───────────────┘
           │                                                             │
           ▼                                                             ▼
┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────┐
│         TWO-TIER RESILIENT GROQ ENGINE       │  │         DATABASE & SERVICES          │
│                                              │  │                                      │
│  Primary:  openai/gpt-oss-120b               │  │  MongoDB Atlas:                      │
│            Deep reasoning & style matching   │  │  ├── users (auth & quotas)           │
│                     │                        │  │  ├── style_genomes (voice profiles)  │
│             [Fast Failover]                  │  │  ├── rewrites (history & diffs)      │
│                     ▼                        │  │  └── drills (calibration logs)       │
│  Fallback: openai/gpt-oss-20b                │  │                                      │
│            Instant backup if primary times   │  │  Razorpay: Secure subscription checkout│
│            out or hits rate limits           │  │  Sentry: Performance & error tracking│
└──────────────────────────────────────────────┘  └──────────────────────────────────────┘
```

---

### Pipeline 1: Rewriting & Fact-Checking (`/api/v1/rewrite`)

```text
[User Submits Draft or Bullets]
        │
        ▼
[Quota Check (backend/app/services/quota.py)]
 ├── Checks if a new calendar week has started (Monday 00:00 UTC)
 ├── Resets weekly word count automatically with zero background cron jobs
 └── Verifies user quota (Free Tier vs Pro Tier)
        │
        ▼
[Stage 1: Ingestion & Expansion (backend/app/services/pipeline.py)]
 ├── Raw text: passes through with original formatting intact
 └── Bullet points: expanded into a clean draft
        │
        ▼
[Stage 2: Tone Transformation (Style Genome Injection)]
 ├── Injects your average sentence length, formality level, and transition words
 ├── Uses real writing samples from your calibration drill as anchor references
 └── Replaces robotic AI buzzwords with your natural phrasing
        │
        ▼
[Stage 3: Meaning Verification Gate]
 ├── Compares original text against the rewrite to check if facts match
 │
 ├── [Facts Preserved] ──► Advances to Stage 4
 │
 └── [Factual Drift Detected]
      │
      ▼
   [Guided Correction Retry]
    ├── Re-runs Stage 2 with the exact mistake explained in the prompt
    │
    ├── [Retry Successful] ──► Advances to Stage 4
    │
    └── [Still Uncertain]  ──► Completes rewrite with an amber warning badge
                               (You get your draft immediately; demo never crashes)
        │
        ▼
[Stage 4: Light Grammar Polish]
 ├── Fixes accidental typos and subject-verb mismatches
 └── Strict Rule: Leaves your em-dashes, commas, and conversational pauses untouched
        │
        ▼
[Output Ready]
 ├── Shows side-by-side diffs and slop reduction highlights in Studio
 └── Records rewrite telemetry in MongoDB
```

---

### Pipeline 2: 3-Minute Voice Calibration Drill (`/api/v1/grill`)

```text
[User Starts Calibration (frontend/src/components/drill/)]
        │
        ▼
[Prompt 1: Stream of Consciousness (60s)]
 └── Write whatever comes to mind; captures small words, pronouns, and natural speed
        │
        ▼
[Prompt 2: Detail Description (60s)]
 └── Describe a scene; measures how you organize details and use descriptive words
        │
        ▼
[Prompt 3: Personal Story (60s)]
 └── Tell a quick story; observes how you resolve tension and shift sentence pace
        │
        ▼
[Voice Profile Created (backend/app/services/grill.py)]
 ├── Computes your baseline sentence length and sentence variety
 ├── Measures vocabulary richness and identifies your go-to transition words
 ├── Catalogs your punctuation habits (dashes, commas, parentheses)
 ├── Builds context profiles: Work Formal, Academic, and Workplace Chat
 └── Saves your Style Genome to MongoDB Atlas
```

---

### Pipeline 3: Adaptive Learning (`/api/v1/rewrite/accept`)

```text
[User Edits Output in Studio & Clicks "Accept & Learn"]
        │
        ▼
[Safety Gate Check]
 ├── Did this draft have a meaning warning?
 │   ├── YES: Learning is paused for this draft to protect your profile from errors.
 │   └── NO:  Proceed to analyze the edit.
 │
        ▼
[Edit Analysis (backend/app/services/adaptive.py)]
 ├── Computes the diff between what InkFlow wrote and what you edited
 ├── Stores the edit pattern in a temporary buffer
 │
        ▼
[Repeat Pattern Check]
 ├── Ignores one-off typo fixes or unusual words used just once
 ├── Looks for consistent writing habits that show up across multiple sessions
 │   (for example: you always prefer shorter sentences or specific transition words)
 │
        ▼
[Profile Update]
 └── Gradually updates your Style Genome so your writing twin evolves with you
```

---

## 🛠️ Key Engineering Safeguards

### 1. Two-Tier Groq Failover
If the primary large model (`openai/gpt-oss-120b`) is slow to respond, cold-starts, or encounters rate limits, the backend automatically switches to `openai/gpt-oss-20b` in under a few seconds. The user never sees a timeout error.

### 2. Fact Protection & Soft Fallback
If the model drops an important detail (like a deadline or number), it gets one guided retry with the mistake explicitly called out. If the model is still unsure, it flags the output with an amber warning banner. You can still copy the draft, but InkFlow pauses adaptive learning so flawed facts never corrupt your profile.

### 3. Punctuation Invariance
Most grammar checkers aggressively strip em-dashes and commas to fit textbook rules. InkFlow's grammar pass is strictly instructed to fix genuine agreement errors while leaving your punctuation habits untouched.

### 4. Zero-Cron Quota Resets
Instead of relying on fragile background workers or cron daemons to reset word counts, InkFlow checks the calendar week (Monday 00:00 UTC) lazily whenever a request arrives. It resets in memory and writes the update in-flight.

### 5. Smooth Studio Experience
During generation, the Studio cycles honest, reassuring status messages (*"Matching sentence cadence..."*, *"Filtering AI buzzwords..."*, *"Verifying facts..."*) so wait time feels purposeful and intentional.

### 6. Clean Checkout Flow
The Razorpay upgrade modal resets its loading state immediately whenever the user cancels or closes the window. The close button and backdrop can always be clicked, preventing frozen screens or tap loops on mobile.

---

## 📊 Practical Highlights

| Feature | How It Works | What You Get |
| :--- | :--- | :--- |
| **Dual Model Resilience** | Groq 120B primary with automated failover to 20B. | Deep reasoning when available, fast backup if busy. |
| **Slop Eradication** | Detects synthetic clichés and replaces them with your natural transitions. | Writing that sounds like a real person, not a chatbot. |
| **Fact-Checking Gate** | Compares draft claims against original points before finishing. | Catches hallucinations before you send your document. |
| **Punctuation Protection** | Strict rules preventing the removal of dashes, commas, and pauses. | Keeps your unique voice and writing style intact. |
| **Smart Adaptive Learning** | Only adopts habits that appear across multiple writing sessions. | One-off typo edits won't distort your long-term profile. |
| **Automatic Quota Reset** | Checks calendar week in-flight every Monday at 00:00 UTC. | Quota resets work reliably without server cron jobs. |

---

## 🧰 Tech Stack

- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS, Framer Motion, Lucide Icons, Canvas Confetti.
- **Backend**: FastAPI (Python 3.11+), Uvicorn, Motor (Async MongoDB), Pydantic v2, HTTPX, Sentry SDK.
- **AI Models**: `openai/gpt-oss-120b` (Primary) & `openai/gpt-oss-20b` (Fallback) via Groq Cloud.
- **Database**: MongoDB Atlas (Users, Style Genomes, Rewrites, Drills).
- **Auth & Payments**: Firebase Auth (Google & Email) & Razorpay Checkout.
- **Hosting**: Render.com (Backend API & Frontend) and Vercel.

---

## 🚀 Quick Start & Local Setup

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 20+ (`npm` 10+)
- **MongoDB**: Local instance or a free MongoDB Atlas URI
- **Groq API Key**: Free key from [console.groq.com](https://console.groq.com)

---

### 1. Backend Setup (`FastAPI`)

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate on Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Activate on macOS/Linux:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up your environment file
cp .env.example .env
```

Add your keys to `backend/.env`:
```env
PROJECT_NAME="InkFlow API"
ENVIRONMENT="development"
DEBUG=True
API_V1_STR="/api/v1"

SECRET_KEY="your-secret-key-for-development"
MONGODB_URI="mongodb://localhost:27017"
MONGODB_DB_NAME="inkflow"

# Groq API
GROQ_BASE_URL="https://api.groq.com/openai/v1"
GROQ_API_KEY="gsk_your_groq_api_key"
GROQ_PRIMARY_MODEL="openai/gpt-oss-120b"
GROQ_FALLBACK_MODEL="openai/gpt-oss-20b"

# Quotas
FREE_TIER_DAILY_WORD_LIMIT=1500
FREE_TIER_WEEKLY_WORD_LIMIT=5000

# Razorpay Test Keys
PAYMENT_PROVIDER="razorpay"
RAZORPAY_KEY_ID="rzp_test_your_key_id"
RAZORPAY_KEY_SECRET="your_key_secret"

CORS_ORIGINS="http://localhost:3000,http://localhost:5173,https://ink-flow-twin.vercel.app"
```

Start the backend:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API documentation will be available at `http://localhost:8000/docs`.

---

### 2. Frontend Setup (`React + Vite`)

```bash
cd frontend

# Install dependencies
npm install

# Set up environment file
cp .env.example .env
```

Add your keys to `frontend/.env`:
```env
VITE_API_URL=http://localhost:8000/api/v1

# Firebase Auth
VITE_FIREBASE_API_KEY="your_firebase_api_key"
VITE_FIREBASE_AUTH_DOMAIN="your-app.firebaseapp.com"
VITE_FIREBASE_PROJECT_ID="your-project-id"

# Razorpay Test Key
VITE_RAZORPAY_KEY_ID="rzp_test_your_key_id"
```

Start the frontend:
```bash
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## 🧪 Running Tests

Run the backend test suite:
```bash
pytest backend/tests
```
All unit and integration tests (providers, pipeline, evals, quota, adaptive learning, payments) will run and report passing.

Check frontend build:
```bash
npm --prefix frontend run build
```

---

## 🛡️ Privacy & Data Security

- **Zero Data Retention**: Your text is sent directly to open-weight models via encrypted connections and is never used to train future foundation models.
- **Secure Token Checks**: API endpoints verify signed Firebase ID tokens, rejecting unauthorized requests.
- **Cryptographic Payments**: Subscriptions are verified with HMAC-SHA256 signatures before activating Pro features.
- **Clean Local Sessions**: All draft buffers and authentication tokens are stored in your browser session and cleared completely on sign-out.

---

## 📜 License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for details.

Created with ❤️ by [Soumya Ghosh](https://github.com/SoumyaGhosh2006).
