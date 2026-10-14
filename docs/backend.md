# InkFlow Backend Specification & Architecture

> **Target Audience**: Professionals, university students, researchers, educators, and office workers (ages 20+).  
> **Core Value**: An adaptive writing twin that replaces generic AI slop with authentic personal cadence, backed by verifiable quality gates, resilient fallback, and complete data sovereignty.

---

## 1. System Overview & Technology Stack

```
InkFlow Backend (FastAPI on Render.com)
├── Runtime: Python 3.11+ / FastAPI / Uvicorn (async event loop)
├── Data Layer: MongoDB Atlas (via Motor async driver)
├── Primary Model: openai/gpt-oss-120b (Groq Cloud API, deep reasoning, high fidelity)
├── Fallback Model: openai/gpt-oss-20b (Groq Cloud API, blazing fast instant failover)
├── Auth Layer: Firebase Admin SDK (token verification middleware)
├── Payments: Razorpay Python SDK (Orders, Payment Verification, Webhooks)
└── Monitoring: Sentry Python SDK (sentry-sdk[fastapi] with Agent Tracing)
```

---

## 2. Directory Structure (`/backend`)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application factory, CORS, Sentry init
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic BaseSettings (env vars, timeouts, model IDs)
│   │   ├── database.py             # Motor async MongoDB client & collections
│   │   ├── security.py             # Firebase Auth token verification dependency
│   │   └── sentry.py               # Custom Sentry tracing helpers & tags
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                 # User document, quota limits & subscription schemas
│   │   ├── genome.py               # Style Genome & personality memory schemas
│   │   └── rewrite.py              # Rewrite document, diff logs & eval score schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── providers.py            # Resilient Groq two-tier LLM client (70B -> 8B fallback)
│   │   ├── pipeline.py             # 4-stage sequential quality pipeline & retry gate
│   │   ├── grill.py                # Onboarding drill analyzer & genome extractor
│   │   ├── evals.py                # Slop, Style, Semantic, and Burstiness scorers
│   │   ├── adaptive.py             # 5-10 session edit recurrence analyzer
│   │   ├── quota.py                # Lazy weekly word limit reset & usage enforcement
│   │   └── payments.py             # Razorpay order creation and signature verification
│   └── api/
│       ├── __init__.py
│       ├── deps.py                 # FastAPI dependency injection (current_user, db)
│       └── v1/
│           ├── __init__.py
│           ├── auth.py             # User profile sync & session check
│           ├── grill.py            # Timed drill questions & submission endpoint
│           ├── rewrite.py          # Rewrite pipeline endpoint & accept-edit endpoint
│           ├── analytics.py        # Evolution stats, metrics history, and evals log
│           └── payments.py         # Razorpay checkout & webhook routes
├── tests/
│   ├── __init__.py
│   ├── test_providers.py           # Provider fallback & timeout tests
│   ├── test_pipeline.py            # 4-stage pipeline & meaning gate retry tests
│   ├── test_grammar_pass.py        # Punctuation preservation tests
│   ├── test_quota.py               # Weekly word limit & lazy reset tests
│   └── test_adaptive.py            # Edit noise filter & recurrence tests
├── requirements.txt
├── Dockerfile
└── render.yaml                     # Render.com deployment manifest
```

---

## 3. LLM Provider Hierarchy & Resilient Client (Two-Tier Groq Setup)

### Primary vs Fallback Matrix
| Role | Model Identifier | Host / Runtime | Connection Timeout | Read Timeout | Provider Tag |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary** | `openai/gpt-oss-120b` | Groq Cloud API | **2.5s** (fail-fast on network latency) | **9.0s** (active inference) | `groq_gpt_oss_120b` |
| **Fallback** | `openai/gpt-oss-20b` | Groq Cloud API | **2.0s** | **8.0s** (sub-second instant) | `groq_gpt_oss_20b` |

### Implementation Contract (`app/services/providers.py`)
```python
import httpx
import sentry_sdk
from app.core.config import settings

PRIMARY_TIMEOUT = httpx.Timeout(connect=2.5, read=9.0, write=5.0, pool=5.0)
FALLBACK_TIMEOUT = httpx.Timeout(connect=2.0, read=8.0, write=5.0, pool=5.0)

async def generate_llm_completion(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> tuple[str, str]:
    """
    Attempts Groq openai/gpt-oss-120b first. If connection fails or times out,
    transparently falls back to Groq openai/gpt-oss-20b.
    Returns: (generated_text, provider_tag)
    """
    groq_base = settings.GROQ_BASE_URL.rstrip("/")
    groq_url = f"{groq_base}/chat/completions" if groq_base.endswith("/v1") else f"{groq_base}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

    # 1. Attempt Primary (Groq openai/gpt-oss-120b)
    try:
        async with httpx.AsyncClient(timeout=PRIMARY_TIMEOUT) as client:
            response = await client.post(
                groq_url,
                headers=headers,
                json={
                    "model": settings.GROQ_PRIMARY_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            sentry_sdk.set_tag("llm.provider", "groq_gpt_oss_120b")
            return content, "groq_gpt_oss_120b"

    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
        sentry_sdk.capture_message(
            f"Primary Groq openai/gpt-oss-120b failed ({type(exc).__name__}). Failing over to openai/gpt-oss-20b.",
            level="warning"
        )

    # 2. Resilient Fallback (Groq openai/gpt-oss-20b)
    try:
        async with httpx.AsyncClient(timeout=FALLBACK_TIMEOUT) as client:
            response = await client.post(
                groq_url,
                headers=headers,
                json={
                    "model": settings.GROQ_FALLBACK_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            sentry_sdk.set_tag("llm.provider", "groq_gpt_oss_20b")
            return content, "groq_gpt_oss_20b"

    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        raise RuntimeError(f"Both LLM providers failed: {exc}") from exc
```

---

## 4. Sequential 4-Stage Quality Pipeline

Input length is capped at **500 words per pass** to prevent latency degradation.

```
[Input: Raw Draft OR Prompt/Bullets]
         │
         ▼
┌─────────────────────────────────┐
│ Stage 1: Generate               │ ──► Produces raw draft (contains AI slop)
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Stage 2: Tone Transform         │ ──► Injects Style Genome (cadence, transitions)
└─────────────────────────────────┘     Strips typical AI slop words naturally
         │
         ▼
┌─────────────────────────────────┐
│ Stage 3: Meaning Check (Gate)   │ ──► Compares input vs transformed claims
└─────────────────────────────────┘
         ├─► Passed (Fidelity >= 85%): Proceed to Stage 4
         └─► Drifted (< 85%): RETRY Stage 2 ONCE with specific drift reason injected
               ├─► Retry Passed: Proceed to Stage 4
               └─► Retry Failed: Continue to Stage 4 with meaningCheckFailed: true
                     (Soft UI warning: avoids breaking live demo / user experience)
         │
         ▼
┌─────────────────────────────────┐
│ Stage 4: Light Grammar Pass     │ ──► Fixes broken syntax & agreement
└─────────────────────────────────┘     INVARIANT: Preserves dashes & commas
         │
         ▼
[Final Output + meaningCheckFailed Flag + Stage Evals Log]
```

### Stage Rules & Implementation Details

#### 4.1 UX Latency Handling & Progressive Loading State
Because a healthy, active DigitalOcean Gemma 2 call can take 6–9 seconds to generate full tokens (and up to 15s if failover to Groq occurs), the UI must **never look stuck or frozen**:
- Immediately on request start, the client enters an active loading state: `"Personalizing your draft..."`.
- The UI cycles subtle status micro-copy:
  - `0s - 3s`: *"Matching your sentence cadence and transitions..."*
  - `3s - 7s`: *"Filtering synthetic AI buzzwords..."*
  - `7s - 10s`: *"Verifying factual fidelity..."*
  - `10s+`: *"Final readability check..."*
- This transforms latency into perceived high-value craftsmanship.

#### 4.2 Stage 1 (Generate)
- If user supplies raw text: passes directly into Stage 2.
- If user supplies bullet points: calls `generate_llm_completion()` with a neutral drafting prompt.

#### 4.3 Stage 2 (Tone Transform)
- Feeds user's `StyleGenome` metrics (average sentence length, transition habits, formality offset) + 2 raw exemplar anchors into the prompt.
- Strips AI buzzwords naturally by rewriting in the user's authentic cadence.

#### 4.4 Stage 3 (Meaning Gate with Reason-Aware Retry & Soft Fallback)
1. **Initial Verification**: Evaluates factual consistency between original input and Stage 2 draft, returning JSON:
   ```json
   {
     "meaning_preserved": false,
     "semantic_score": 74.0,
     "drift_reason": "The output dropped the critical deadline date (Friday 5 PM) and changed the reason from API downtime to general maintenance."
   }
   ```
2. **Reason-Aware Retry (Stage 2 retry)**:
   If `meaning_preserved == False`, triggers **one immediate retry** of Stage 2 at `temperature=0.3`, injecting the exact failure reason:
   ```
   CRITICAL CORRECTION REQUIRED:
   Your previous attempt distorted the core meaning with the following error:
   "{drift_reason}"
   You must strictly preserve this fact while keeping the user's authentic style.
   ```
3. **Soft Warning State (No Hard 422 Blockers)**:
   If the retry *still* fails Stage 3 verification:
   - **Do NOT raise HTTP 422**.
   - Advance to Stage 4 (Light Grammar Pass) so the user still receives usable text.
   - Return response with:
     ```json
     {
       "meaningCheckFailed": true,
       "meaningWarning": "Meaning check couldn't fully verify this draft. Please double-check core facts before sending."
     }
     ```
   - The UI displays an amber warning badge above the output, ensuring the live demo never dead-ends.

#### 4.5 Stage 4 (Light Grammar Pass)
- Explicit system prompt instruction:  
  `"Fix only broken grammatical structures, subject-verb disagreements, and missing words that break basic readability. EXPLICITLY DO NOT adjust commas, em-dashes, or conversational punctuation pauses. Retain the exact punctuation quirks of the input text."`

---

## 5. Weekly Word Limit & Quota Enforcement

### 5.1 Quota Tiers
- **Free Tier**: 2,500 words per week (`weeklyWordLimit: 2500`).
- **Pro Tier**: Unlimited words (`tier: "pro"`).

### 5.2 Lazy Weekly Reset Architecture
No external cron job or background scheduler is needed. The reset check runs in-flight on request arrival:

```python
from datetime import datetime, timezone, timedelta

def enforce_and_reset_quota(user: dict, requested_words: int) -> tuple[dict, bool, str | None]:
    """
    Checks if a new calendar week (Monday 00:00 UTC) has elapsed since lastWeekReset.
    If so, resets wordsUsedThisWeek to 0.
    Enforces word limits on Free tier users.
    Returns: (updated_user_dict, allowed, error_message)
    """
    now = datetime.now(timezone.utc)
    # Start of current week (Monday 00:00:00 UTC)
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    
    last_reset = user.get("lastWeekReset")
    if last_reset is None or last_reset < start_of_week:
        user["wordsUsedThisWeek"] = 0
        user["lastWeekReset"] = start_of_week
        # Persist reset to MongoDB in the background

    # If Pro, allow unconditionally
    if user.get("tier") == "pro":
        return user, True, None

    # Free Tier Quota Check
    limit = user.get("weeklyWordLimit", 2500)
    current_used = user.get("wordsUsedThisWeek", 0)
    
    if current_used + requested_words > limit:
        remaining = max(0, limit - current_used)
        return user, False, (
            f"Weekly limit reached ({current_used}/{limit} words used). "
            f"You have {remaining} words remaining this week. Upgrade to Pro for unlimited rewrites."
        )

    return user, True, None
```

- If `allowed == False`, the pipeline endpoint returns `HTTP 403 Forbidden` with:
  ```json
  {
    "status": "QUOTA_EXCEEDED",
    "message": "You've hit your weekly word limit.",
    "wordsUsed": 2500,
    "limit": 2500,
    "resetsAt": "Monday 00:00 UTC",
    "upgradeRequired": true
  }
  ```

---

## 6. Noise-Resistant Adaptive Learning Engine

```
User edits rewrite before clicking "Accept"
                    │
                    ▼
Calculate Stylistic Delta (Token changes, sentence length shift, transition delta)
                    │
                    ▼
Fetch User's Last 5–10 Accepted Rewrites from MongoDB
                    │
                    ▼
Check Recurrence Pattern
    ├── If pattern appears >= 3 times across separate sessions:
    │     └── Shift Style Genome baseline & log evolution event
    └── If pattern appears < 3 times (e.g. single typo or isolated edit):
          └── Discard from genome update (prevents profile instability)
```

### Evolution Metrics Tracked
- `avgSentenceLength`: Rolling average across verified sessions.
- `vocabularyRichnessTTR`: Type-Token Ratio calculated on user-accepted drafts.
- `formalityScore`: Calibrated against workplace vs educational context toggles.
- `transitionHabits`: Dynamic frequency list of favorite sentence starters.

---

## 7. MongoDB Atlas Data Schemas

### `users` Collection
```json
{
  "_id": "ObjectId",
  "firebaseUid": "string (unique index)",
  "email": "string",
  "displayName": "string",
  "tier": "free | pro",
  "razorpaySubscriptionId": "string | null",
  "wordsUsedThisWeek": 1420,
  "weeklyWordLimit": 2500,
  "lastWeekReset": "ISODate",
  "streakDays": 4,
  "createdAt": "ISODate",
  "updatedAt": "ISODate"
}
```

### `style_genomes` Collection
```json
{
  "_id": "ObjectId",
  "userId": "string (index)",
  "version": 1,
  "baselineGenome": {
    "avgSentenceLength": 13.8,
    "sentenceLengthVariance": 7.4,
    "formalityScore": 6.8,
    "vocabularyRichnessTTR": 0.65,
    "transitionHabits": ["basically", "at the end of the day", "look,"],
    "punctuationHabits": {
      "commaFrequency": "moderate",
      "emDashUsage": "rare",
      "parenthesesUsage": "frequent"
    }
  },
  "contextProfiles": {
    "work_formal": { "formalityOffset": 1.5 },
    "academic_educator": { "formalityOffset": 1.0 },
    "workplace_chat": { "formalityOffset": -1.0 }
  },
  "exemplars": [
    "Raw response from drill question 1...",
    "Raw response from drill question 2..."
  ],
  "recentEditsBuffer": [
    {
      "rewriteId": "ObjectId",
      "timestamp": "ISODate",
      "editType": "shortened_sentences",
      "detail": "reduced words per sentence by 18%"
    }
  ]
}
```

### `rewrites` Collection
```json
{
  "_id": "ObjectId",
  "userId": "string (index)",
  "context": "work_formal",
  "originalInput": "string",
  "stageOutputs": {
    "stage1_generate": "string",
    "stage2_tone_transform": "string",
    "stage3_meaning_checked": true,
    "stage3_retried": false,
    "stage3_drift_reason": null,
    "stage4_grammar_passed": "string"
  },
  "finalOutput": "string",
  "meaningCheckFailed": false,
  "meaningWarning": null,
  "userEdited": true,
  "acceptedAt": "ISODate",
  "provider": "groq_gpt_oss_120b | groq_gpt_oss_20b",
  "evalScores": {
    "slopReductionScore": 94.2,
    "styleAlignmentScore": 87.5,
    "semanticFidelityScore": 98.0,
    "burstinessVariance": 11.2
  }
}
```

---

## 8. REST API Endpoints Specification

### Auth & Onboarding Drill
- `POST /api/v1/auth/sync`  
  Verifies Firebase Bearer token and creates/retrieves user profile in MongoDB.
- `GET /api/v1/grill/prompts`  
  Returns 3 unlabelled situational scenarios for the 60-second timed drill.
- `POST /api/v1/grill/analyze`  
  Ingests the 3 raw drill responses, computes initial `StyleGenome`, and saves to MongoDB.

### Transformation & Studio
- `POST /api/v1/rewrite/pipeline`  
  Body: `{ input: string, inputType: "raw_draft" | "bullet_points", context: "work_formal" | "academic" | "chat" }`  
  1. Runs `enforce_and_reset_quota()`. If limit exceeded $\rightarrow$ returns `403 Forbidden` (`QUOTA_EXCEEDED`).
  2. Executes 4-stage pipeline with reason-aware Stage 3 retry and soft warning fallback.
  3. Increments `wordsUsedThisWeek` on success.
  4. Returns `{ finalOutput: string, meaningCheckFailed: bool, meaningWarning: string | null, provider: string, evalScores: dict }`.
- `POST /api/v1/rewrite/accept`  
  Body: `{ rewriteId: string, finalUserText: string }`  
  Records accepted text. **Genome Integrity Protection**: If the rewrite had `meaningCheckFailed: true`, it saves the accepted record for history but **explicitly skips the adaptive learning loop** (does not push to `recentEditsBuffer`, does not shift `StyleGenome`). Only drafts with verified semantic fidelity are permitted to train the user's personal Style Genome. Otherwise, computes edit delta and evaluates the 5–10 session recurrence threshold.

### Analytics & Subscription
- `GET /api/v1/analytics/evolution`  
  Returns user's writing streak, word count, vocabulary growth curve, and average eval scores.
- `POST /api/v1/payments/create-order`  
  Creates a Razorpay order for Pro upgrade (supports UPI, cards, netbanking).
- `POST /api/v1/payments/verify`  
  Validates Razorpay payment signature and upgrades user tier to `pro`.

---

## 9. Sentry Tracing & Monitoring Specification

Every call to `/api/v1/rewrite/pipeline` initiates a Sentry transaction:
```python
with sentry_sdk.start_transaction(op="rewrite.pipeline", name="FourStageRewrite"):
    with sentry_sdk.start_span(op="stage.generate"): ...
    with sentry_sdk.start_span(op="stage.tone_transform"): ...
    with sentry_sdk.start_span(op="stage.meaning_check"): ...
    with sentry_sdk.start_span(op="stage.grammar_pass"): ...
    with sentry_sdk.start_span(op="evals.scoring"): ...
```
- Custom tags injected: `llm.provider`, `user.tier`, `pipeline.retried_meaning`, `pipeline.meaning_failed`, `eval.slop_score`.
- Directly fulfills the **Best Use of Sentry Agent Tracing ($100)** prize track.

---

## 10. Verification & Testing Matrix

Run tests locally before deployment:
```bash
# Run provider failover tests (simulates Groq 70B down -> Groq 8B instant fallback)
pytest tests/test_providers.py -v

# Run 4-stage pipeline tests (verifies reason-aware retry and soft warning fallback)
pytest tests/test_pipeline.py -v

# Run punctuation preservation invariant tests
pytest tests/test_grammar_pass.py -v

# Run weekly quota and lazy reset tests
pytest tests/test_quota.py -v

# Run adaptive noise filter tests
pytest tests/test_adaptive.py -v
```

---

## 11. Hackathon Partner Tracks & Prize Alignment

| Partner Category | Target Prize | InkFlow Technical Implementation |
| :--- | :--- | :--- |
| **Best Use of Render** | **$200 USD** | Production FastAPI backend web service deployed and orchestrated on Render.com (`render.yaml`). |
| **Best Use of MongoDB Atlas** | **$100 USD** | Flexible document database storing nested `style_genomes`, evolution logs, diff buffers, and rewrite histories. |
| **Best Use of Sentry Agent Tracing** | **$100 USD** | Full tracing across all 4 pipeline stages (Stage 1-4 latency, fallback activations, eval scores, and `groq_rate_limit_429` alerts). |
| **Best Use of a .tech Domain** | **$100 USD** | Production web application mapped to a free Hacktoberfest `.tech` domain (e.g. `inkflow.tech`). |
| **Best Use of ElevenLabs** *(Bonus)* | **$100 USD** | Voice narration generated for the video walkthrough and demo submission. |
