# InkFlow Frontend Specification & Design System

> **Design Direction**: Inspired by **Wispr Flow** — minimal, warm porcelain tones, generous curvature, distraction-free typography, and purposeful micro-animations. Strictly zero AI slop aesthetics (no generic purple-to-cyan gradients, no floating particle blobs).  
> **Target Audience**: University students, researchers, professors, and workplace professionals (ages 20+).  
> **Development Context**: Engineered as a standalone Vite + React (TypeScript) SPA that pairs with the InkFlow FastAPI backend.

---

## 1. Design Language & Visual Tokens (Wispr Flow Aesthetic)

### 1.1 Color Palette
The interface uses warm neutrals with a high-contrast charcoal foundation and a warm amber accent for primary triggers and Pro highlights:

| Token | Hex Value | Role & Usage |
| :--- | :--- | :--- |
| `bg-canvas` | `#FAF9F6` | Warm off-white porcelain background for the entire application |
| `bg-surface` | `#FFFFFF` | Crisp milk-white card and container background |
| `bg-surface-subtle` | `#F4F2ED` | Hover states, pill badges, and nested input panels |
| `text-primary` | `#1C1917` | Deep warm charcoal for headings, body, and high-emphasis labels |
| `text-secondary` | `#78716C` | Muted stone for timestamps, status hints, and secondary copy |
| `border-subtle` | `#E7E5E0` | Whisper-thin 1px card and divider borders |
| `accent-primary` | `#F59E0B` | Warm citrus amber for "Upgrade to Pro", streaks, and primary CTAs |
| `accent-hover` | `#D97706` | Deep amber hover state |
| `accent-soft` | `#FEF3C7` | Soft amber badge background for Pro tags and streak pills |
| `status-warning` | `#F59E0B` | Amber warning banner when meaning check requires manual review |
| `status-success` | `#10B981` | Emerald green for verified fidelity scores and slop eradication |

### 1.2 Typography & Scale
- **Font Family**: `Plus Jakarta Sans` or `Inter` (geometric, modern, ultra-legible).
- **Display Numerals**: `Newsreader` or `Fraunces` (subtle editorial serif) for large metric numerals (e.g., `54.2K`, `94%`, `4 day streak`), echoing the sophisticated editorial feel of Wispr Flow.
- **Hierarchy**:
  - Page Title: `text-2xl font-semibold tracking-tight text-stone-900`
  - Section Headings: `text-xs font-semibold uppercase tracking-wider text-stone-500`
  - Body / Editor Text: `text-base font-normal leading-relaxed text-stone-800`
  - Metric Display: `text-4xl font-normal font-serif text-stone-900`

### 1.3 Surface Geometry & Shadows
- **Border Radii**:
  - Outer app cards: `rounded-3xl` (24px)
  - Modals & dialogs: `rounded-2xl` (16px)
  - Buttons, pills, and inputs: `rounded-xl` (12px)
  - Icon buttons: `rounded-full`
- **Shadows**:
  - Subtle card elevation: `shadow-[0_2px_16px_rgba(28,25,23,0.03)]`
  - Floating panels / Modals: `shadow-[0_12px_32px_rgba(28,25,23,0.08)]`

---

## 2. Global Layout Architecture & Dock Navigation

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ App Header: Window title, global user status, notification bell, user avatar           │
├──────┬──────────────────────────────────────────────────────────┬──────────────────────┤
│ DOCK │ MAIN WORKSPACE                                           │ INSIGHTS & STATS     │
│ (48px│                                                          │ (320px fixed)        │
│ wide)│ ┌──────────────────────────────────────────────────────┐ │                      │
│      │ │ Announcement / Context Banner (Dismissible)          │ │ ┌──────────────────┐ │
│ [1]  │ └──────────────────────────────────────────────────────┘ │ │ Total Words: 1.4K│ │
│ [2]  │                                                          │ │ Accuracy: 98%    │ │
│ [3]  │ ┌──────────────────────────────────────────────────────┐ │ │ Streak: 4 Days   │ │
│ [4]  │ │ Dynamic View:                                        │ │ └──────────────────┘ │
│ [5]  │ │  - View A: Onboarding Timed Drill (60s Calibration)  │ │ ┌──────────────────┐ │
│ [6]  │ │  - View B: Dual-Pane Transformation Studio           │ │ │ Weekly Quota:    │ │
│      │ │  - View C: Writing Evolution History & Logs          │ │ │ 1,080 words left │ │
│      │ └──────────────────────────────────────────────────────┘ │ │ Resets Mon 00:00 │ │
│      │                                                          │ │ [Upgrade to Pro] │ │
│      │                                                          │ └──────────────────┘ │
│      │                                                          │ ┌──────────────────┐ │
│      │                                                          │ │ Twin Genome Card │ │
│      │                                                          │ └──────────────────┘ │
└──────┴──────────────────────────────────────────────────────────┴──────────────────────┘
```

### 2.1 Dock Navigation Items (48px Icon-Only Dock with Tooltips)
All dock icons are 20px Lucide icons rendered within a 36px circular button. Each item includes an accessible Radix/Tailwind tooltip with a subtle delay (`side="right"`, `sideOffset={12}`):

| ID | Lucide Icon | Route / View | Tooltip Text | Accessible Label |
| :--- | :--- | :--- | :--- | :--- |
| `[1]` | `PenSquare` | `/studio` | **Transformation Studio (⌘1)** | Navigate to Studio |
| `[2]` | `Zap` | `/drill` | **Voice Calibration Drill (⌘2)** | Navigate to 60s Drill |
| `[3]` | `BarChart3` | `/evolution` | **Writing Insights & Evals (⌘3)** | View Writing Insights |
| `[4]` | `History` | `/history` | **Rewrite History & Diffs (⌘4)** | View Past Rewrites |
| `[5]` | `Settings` | `/settings` | **Settings & Model Preferences** | Open Settings |
| `[6]` | `HelpCircle` | `/docs` | **Help & Documentation** | Open Help |

---

## 3. Core Views & User Flows

### View 1: The Onboarding Timed Drill ("Voice Calibration")
- **Purpose**: Captures unpolished, instinctive writing habits in 3 minutes without user overthinking.
- **Components**:
  - **Countdown Timer**: 60-second animated radial progress ring per prompt.
  - **Situational Card**: Displays one unlabelled scenario at a time (e.g., "A client just asked why the deadline slipped by 2 days. What do you say?").
  - **Dynamic Textarea**: Clean, borderless writing area with live word counter.
  - **Transition**: Smooth horizontal slide animation (Framer Motion) upon submitting or timer expiry.
  - **Completion State**: Renders an animated **"Voice Profile Unlocked!"** card displaying initial detected metrics (Cadence, Formality, Transitions).

### View 2: The Transformation Studio (Primary Workspace)
- **Top Bar**:
  - **Input Mode Toggle**: Segmented control between `[ Paste Existing Draft ]` and `[ Draft from Bullets ]`.
  - **Context Selector**: Dropdown pills for `Work / Office Formal`, `Academic / Educator`, `Workplace Chat`.
  - **Word Counter & Quota Indicator**: Displays remaining words with instant warning if over 500-word pass limit.
- **Editor Canvas**:
  - **Left Pane (Source)**: Raw draft with instant AI Slop highlighting (underlines words like `delve`, `tapestry`, `in conclusion` in subtle red/amber).
  - **Right Pane (InkFlow Twin)**: Transformed output with side-by-side diff toggle (`Show what changed`).
- **Progressive Loading State (Accurate Latency & Failover Handling)**:
  - Triggered immediately on clicking `"Transform Draft"`.
  - To match the real backend timeout architecture (`connect 2.5s + read 9.0s` for Gemma 2, followed by Groq fallback if needed), the cycler uses this phased timeline:
    - `0s - 3s`: *"Matching your sentence cadence and transitions..."*
    - `3s - 7s`: *"Filtering synthetic AI buzzwords (Gemma 2)..."*
    - `7s - 11s`: *"Verifying factual fidelity..."*
    - `11s - 15s+` *(Failover phase)*: *"Switching to resilient backup model (Groq Llama 3.3)..."*
    - `Final moment`: *"Applying light readability polish..."*
  - Elegant animated shimmer pulse across the output container.

- **Quality & Meaning Warning Banner (Genome Integrity Guard)**:
  - If `meaningCheckFailed: true`: Displays a prominent amber banner above the output:  
    `⚠️ Meaning check couldn't fully verify this draft. Adaptive learning is paused for this rewrite to protect your Style Genome from drift.`
  - **Action Options**:
    - `[ Copy Draft Anyway ]`: User gets unblocked and uses the text immediately.
    - `[ Edit in Studio ]`: Allows user to correct claims manually.
  - **Strict Genome Invariant**: When `meaningCheckFailed: true`, clicking "Accept" **never** feeds into the adaptive learning buffer (`recentEditsBuffer`). It protects the user's Style Genome from being poisoned by corrupted facts or hallucinations.

- **Bottom Action Dock**:
  - Provider Pill: Tag showing `DigitalOcean Gemma 2` (or `Groq Llama 3.3` on fallback).
  - Eval Score Pill: `Slop Eradication: 95%` | `Fidelity: 98%`.
  - Buttons: `Copy to Clipboard`, `Accept & Learn` (disabled from training if meaning check failed).

### View 3: Writing Evolution & Insights
- **Cadence & Burstiness Graph**: Visual bar chart showing natural sentence length variance versus robotic AI flatness.
- **Slop Eradication Meter**: Counter of total synthetic buzzwords stripped from the user's workflow.
- **Adaptive Recurrence History**: List of detected stylistic shifts that evolved the user's `StyleGenome` across the last 5–10 sessions.

### View 4: Pro Upgrade Modal (Razorpay Integration)
- Modal with clean comparison table:
  - Free Tier: 2,500 words/week (resets Monday 00:00 UTC), 1 Twin profile.
  - Pro Tier: Unlimited words, multi-context profiles, prioritized DigitalOcean GPU inference.
- Trigger button: Opens the Razorpay Checkout modal directly inside the web app for UPI, card, or netbanking payments.

---

## 4. Frontend Technology Stack & Libraries

```
frontend/
├── Framework: Vite + React 18+ (TypeScript)
├── Styling: Tailwind CSS (with @tailwindcss/typography)
├── Icons: Lucide React (feather-style clean strokes)
├── Motion: Framer Motion (for timer progress and view transitions)
├── State Management: Zustand (lightweight stores: useAuthStore, useRewriteStore, useGenomeStore)
├── Tooltips: @radix-ui/react-tooltip (accessible, delayed floating tooltips for dock icons)
├── HTTP Client: Axios (configured with Firebase Auth interceptor)
├── Payments: Razorpay Checkout JS SDK (https://checkout.razorpay.com/v1/checkout.js)
├── Error Monitoring: @sentry/react
└── Diff Visualization: jsdiff (diffChars) or diff-match-patch (Character-level diffing to showcase punctuation preservation)
```

### 4.1 Character-Level Diff Engine (Punctuation Proof)
To visually showcase that InkFlow **strictly preserves the user's punctuation quirks** (commas, dashes, ellipses) while stripping slop and fixing true syntax:
- We use **character-level diffing** (`diffChars` from `diff` library).
- Preserved punctuation marks are highlighted in subtle emerald green chips.
- Stripped slop buzzwords are crossed out in muted red.
- This serves as immediate visual proof of the system's core promise during live demos.

---

## 5. Weekly Quota Definition & Sync
- **Agreed Definition of Week**: ISO calendar week starting **Monday 00:00:00 UTC**.
- **Backend Sync**: Both frontend copy (`"Resets Monday 00:00 UTC"`) and backend `enforce_and_reset_quota()` calculate week start using:
  `start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)`
- This prevents discrepancies between what the UI advertises and what the backend enforces.

---

## 6. Directory Structure (`/frontend`)

```
frontend/
├── public/
│   ├── favicon.svg
│   └── assets/
├── src/
│   ├── main.tsx                    # React DOM root & Sentry initialization
│   ├── App.tsx                     # Top-level routing & layout shell
│   ├── index.css                   # Tailwind imports & custom porcelain tokens
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppHeader.tsx       # Header with user avatar and streak pill
│   │   │   ├── NavigationDock.tsx  # 48px Dock with Radix tooltips
│   │   │   └── StatsSidebar.tsx    # Right stats, quota meter, and upgrade CTA
│   │   ├── drill/
│   │   │   ├── DrillCountdown.tsx  # Circular 60s SVG timer
│   │   │   ├── DrillCard.tsx       # Situational question presentation
│   │   │   └── GenomeReveal.tsx    # "Voice Profile Unlocked" celebratory modal
│   │   ├── studio/
│   │   │   ├── ContextSelector.tsx # Pills for Work Formal / Academic / Chat
│   │   │   ├── SourceEditor.tsx    # Left input with slop detection highlights
│   │   │   ├── OutputViewer.tsx    # Right output with progressive loading shimmer
│   │   │   ├── CharacterDiff.tsx   # Character-level diff proving punctuation preservation
│   │   │   ├── MeaningAlert.tsx    # Amber warning banner with paused-learning notice
│   │   │   └── EvalScorePill.tsx   # Badge showing slop and fidelity percentages
│   │   ├── evolution/
│   │   │   ├── CadenceChart.tsx    # Sentence length variance bar chart
│   │   │   └── EvolutionFeed.tsx   # Timeline of learned stylistic shifts
│   │   └── payments/
│   │       └── UpgradeModal.tsx    # Razorpay checkout launcher & tier table
│   ├── hooks/
│   │   ├── useRewritePipeline.ts   # Phased cycler, timeouts, and API calls
│   │   ├── useDrillTimer.ts        # 60-second countdown controller
│   │   └── useRazorpay.ts          # Script loader & order checkout handler
│   ├── store/
│   │   ├── authStore.ts            # User profile, tier, and wordsUsedThisWeek
│   │   └── studioStore.ts          # Current draft, transformed text, evals, and diffs
│   ├── lib/
│   │   ├── api.ts                  # Axios client configured with Render backend URL
│   │   └── firebase.ts             # Firebase Auth initialization (Google & Email)
│   └── types/
│       ├── api.ts                  # Backend response interfaces
│       └── genome.ts               # Style Genome types
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
└── package.json
```

---

## 7. Verification & Visual QA Checklist

- [ ] Confirm 48px Dock icons display accessible Radix tooltips with short hover delays.
- [ ] Confirm progressive loading animation cycles through all 5 phases up to 15s if failover to Groq occurs.
- [ ] Verify character-level diff highlights preserved commas, dashes, and stripped slop tokens.
- [ ] Confirm amber warning banner appears when `meaningCheckFailed: true` and explicitly disables feeding the adaptive learning loop.
- [ ] Confirm quota meter displays "Resets Monday 00:00 UTC", matching the backend's ISO calendar reset.
