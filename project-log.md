# Provenance Guard — Project Completion Log

Complete step-by-step record of how this project was built, verified, and submitted.

---

## Step 1 — Convert Course PDF to Markdown

**What:** Converted the course PDF `Show (Project): Week 4` into `show-project-week4.md` so the project spec was readable and LLM-accessible as plain text.

**Files created:** `show-project-week4.md`

---

## Step 2 — Read and Understand the Spec

**What:** Read `show-project-week4.md` in full to understand:
- 29 points total (25 required + 4 stretch)
- 6 milestones to complete
- 7 required features: submission endpoint, multi-signal detection, confidence scoring, transparency labels, appeals workflow, rate limiting, audit log
- Key format requirements: label variants must be written as text in README; architecture diagram must be in `planning.md`

---

## Step 3 — Milestone 1: Architecture Design

**What:** Verified Milestone 1 checkpoint was satisfied by `planning.md`:
- Architecture narrative written in plain English
- Two detection signals chosen (LLM + stylometrics) with blind spots documented
- API surface defined: `POST /submit`, `POST /appeal`, `GET /log`
- ASCII architecture diagram drawn showing submission and appeal flows with labeled arrows

**Files created:** `planning.md` (initial version)

**Checkpoint:** ✓ Passed

---

## Step 4 — Milestone 2: Write the Spec

**What:** Verified all five required spec questions were answered in `planning.md`:
1. **Detection signals** — output format (float 0–1), combining formula
2. **Uncertainty representation** — thresholds (≥0.70 = likely_ai, 0.36–0.69 = uncertain, ≤0.35 = likely_human)
3. **Transparency label design** — exact text for all 3 variants written out
4. **Appeals workflow** — who, what info, status changes, what reviewer sees
5. **Anticipated edge cases** — minimalist poetry, transcribed speech

Also confirmed `## Architecture` and `## AI Tool Plan` sections present covering M3, M4, M5.

**Checkpoint:** ✓ Passed

---

## Step 5 — Milestone 3: Build Submission Endpoint + First Signal

**What:** Implemented the Flask app with Signal 1 (Groq LLM) and audit log.

**Files created:**
- `app.py` — Flask app with `POST /submit`, `POST /appeal`, `GET /log`; Flask-Limiter (10/min, 100/day)
- `signals.py` — `llm_classify()` using Groq `llama-3.3-70b-versatile`, returns float 0–1
- `audit.py` — JSON-backed audit log with `log_submission()`, `log_appeal()`, `get_log()`

**Port issue:** macOS AirPlay occupies port 5000 — changed to port 5001 in `app.py`.

**Live tests run:**
| Submission | Confidence | Label |
|---|---|---|
| AI-generated text | 0.61 | `uncertain` |
| Human-written text | 0.22 | `likely_human` |
| Formal human text | 0.63 | `uncertain` |

**Checkpoint:** ✓ Passed — `POST /submit` returns `content_id`, attribution, confidence, label; audit log writes structured entries; `GET /log` returns JSON.

---

## Step 6 — Milestone 4: Second Signal + Confidence Scoring

**What:** Signal 2 (stylometric heuristics) was already implemented alongside Signal 1. Ran the required 4th test input to complete the milestone.

**Signal 2 sub-metrics in `signals.py`:**
- Sentence-length variance
- Type-token ratio (TTR)
- Punctuation density

**Combining formula:** `confidence = 0.6 * llm + 0.4 * stylo`

**4-input test results:**
| Input | LLM | Stylo | Confidence | Label |
|---|---|---|---|---|
| Clearly AI | 0.80 | 0.33 | 0.61 | `uncertain` |
| Clearly human | 0.20 | 0.26 | 0.22 | `likely_human` |
| Formal human | 0.80 | 0.38 | 0.63 | `uncertain` |
| Lightly edited AI | 0.40 | 0.37 | 0.39 | `uncertain` |

**Checkpoint:** ✓ Passed — both signals running, scores combined, audit log records individual signal scores, 4 inputs tested.

---

## Step 7 — Milestone 5: Production Layer

**What:** Verified all 4 production features. Identified 2 gaps and closed them:

**Gap 1 — `likely_ai` label not yet triggered:**
- Submitted heavily AI-patterned text → confidence 0.77 → `⚠️ Likely AI-Generated` label confirmed

**Gap 2 — Rate limit test not run:**
- Sent 12 rapid requests → got 9×200 then 3×429
- Captured actual output in README as grading evidence

**All 4 production features verified:**
- Transparency label varies by confidence level ✓
- Appeals update status to `under_review` in audit log ✓
- Rate limiting fires at correct threshold ✓
- Audit log has ≥3 structured entries with all required fields ✓

**Checkpoint:** ✓ Passed

---

## Step 8 — Milestone 6: Documentation

**What:** Wrote `README.md` covering all required sections.

**Sections included:**
- Architecture overview with diagram
- Detection signals (what each measures, why chosen, blind spots)
- Confidence scoring with 2 example submissions showing different scores
- Transparency labels — exact text of all 3 variants
- Rate limiting with reasoning and 429 evidence
- Appeals workflow with curl commands
- Audit log sample with ≥3 real entries
- Known limitations (minimalist poetry, tied to signal property)
- Spec reflection (one way spec helped, one divergence)
- AI usage (2 specific instances)
- File structure

**Remaining:** Portfolio walkthrough video (to be recorded by student).

**Checkpoint:** ✓ Passed (excluding video)

---

## Step 9 — Git Setup and First Commit

**What:** Committed all project files to GitHub.

```
git add .gitignore README.md app.py audit.py planning.md requirements.txt signals.py
git commit -m "Add Provenance Guard — Milestones 1–6 complete"
git push -u origin main
```

**Repo:** https://github.com/meenakshi-sethi/ai201-project4-provenance-guard

**`.gitignore` covers:**
- `.env` (GROQ_API_KEY)
- `audit_log.json` (runtime generated)
- `show-project-week4.md` (course file)
- `*.pdf` (course PDF)

---

## Step 10 — Stretch Feature 1: Ensemble Detection (3rd Signal)

**What:** Added Signal 3 — Transition Phrase Density.

**Implementation in `signals.py`:**
- `transition_score()` — counts 20 AI-typical phrases ("furthermore", "it is important to note", "moreover", etc.) per 100 words
- Returns float 0–1; >3 phrases per 100 words = score of 1.0

**Updated weighting:**
- Old: `0.6 * llm + 0.4 * stylo`
- New: `0.5 * llm + 0.3 * stylo + 0.2 * transition`

**`audit.py`** updated to log `transition_score` per entry.

**Live test:** Text with heavy AI transitions scored `transition_score: 1.0` → confidence 0.75 → `likely_ai`.

---

## Step 11 — Stretch Feature 2: Analytics Dashboard

**What:** Added `GET /analytics` endpoint to `app.py`.

**Returns:**
- `total_submissions`
- `attribution_breakdown` — count + % for each label category
- `appeal_rate` — % of submissions with an appeal filed
- `average_confidence` — mean confidence score across all submissions

**Live test result:**
```json
{
  "total_submissions": 15,
  "attribution_breakdown": {
    "likely_ai":    { "count": 2,  "percent": 13.3 },
    "uncertain":    { "count": 12, "percent": 80.0 },
    "likely_human": { "count": 1,  "percent": 6.7  }
  },
  "appeal_rate": 6.7,
  "average_confidence": 0.6335
}
```

---

## Step 12 — Update README and planning.md for Stretch Features

**What:** Fixed all outdated references after stretch features were added.

**README fixes:**
- Architecture overview updated from "two signals" → "three signals"
- Architecture diagram updated to include Signal 3 and `GET /analytics`
- Signal weights corrected (50% / 30% / 20%)
- Confidence formula updated to 3-signal version
- Example table added `transition_score` column with real live values
- Transparency label examples updated to real confidence percentages
- All curl commands updated from port 5000 → 5001
- Audit log sample updated with real entries including `transition_score`
- File structure comments updated

**planning.md fixes:**
- Combining Signals formula updated
- Architecture diagram updated to show all 3 signals + `GET /analytics`
- Submission flow narrative updated
- Appeals section updated from "both signal scores" → "all three signal scores"

---

## Step 13 — Final Commit

```
git add app.py signals.py audit.py planning.md README.md
git commit -m "Add stretch features: ensemble detection (3rd signal) and analytics dashboard"
git push origin main

git add README.md planning.md
git commit -m "Update README and planning.md to reflect 3-signal ensemble and stretch features"
git push origin main
```

---

## Final Project State

| Item | Status |
|---|---|
| Milestone 1 — Architecture | ✓ Complete |
| Milestone 2 — Spec (planning.md) | ✓ Complete |
| Milestone 3 — Submission endpoint + Signal 1 | ✓ Complete + live tested |
| Milestone 4 — Signal 2 + Confidence scoring | ✓ Complete + live tested |
| Milestone 5 — Production layer | ✓ Complete + live tested |
| Milestone 6 — Documentation | ✓ Complete (video pending) |
| Stretch: Ensemble detection (Signal 3) | ✓ Complete + live tested |
| Stretch: Analytics dashboard | ✓ Complete + live tested |
| GitHub repo | ✓ Pushed |
| Portfolio walkthrough video | ⏳ To be recorded by student |

**GitHub:** https://github.com/meenakshi-sethi/ai201-project4-provenance-guard

**Endpoints:**
| Endpoint | Purpose |
|---|---|
| `POST /submit` | Submit text for classification |
| `POST /appeal` | Contest a classification |
| `GET /log` | View audit log entries |
| `GET /analytics` | View detection patterns and appeal rate |
