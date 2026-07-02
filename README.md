# Provenance Guard

A backend API that classifies creative text as human- or AI-written using a 3-signal ensemble pipeline, returns a transparency label, supports creator appeals, enforces rate limiting, and logs every decision.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env
python app.py
```

Server runs on `http://localhost:5001`.

---

## Architecture Overview

A submission enters `POST /submit`. The text runs through three independent detection signals: an LLM call to Groq (semantic), stylometric heuristics (structural), and transition phrase density (vocabulary-level). Their scores are weighted into a single confidence value, mapped to a transparency label, logged to `audit_log.json`, and returned to the caller.

An appeal enters `POST /appeal` with the `content_id`. The original log entry is updated to `under_review` and the creator's reasoning is stored alongside the original decision.

```
POST /submit → llm_classify() + stylo_score() + transition_score()
            → combine_scores() → attribution() → make_label()
            → audit log → response

POST /appeal → lookup content_id → status="under_review" → audit log → response

GET  /log       → return last 20 audit entries
GET  /analytics → return detection patterns and appeal rate
```

---

## Detection Signals

### Signal 1 — LLM Classification (Groq `llama-3.3-70b-versatile`)
Prompts the model to return a single float (0 = human, 1 = AI). Captures semantic coherence, phrasing uniformity, and stylistic patterns holistically. Weight: **50%**.

**Why chosen:** LLMs are best positioned to recognise LLM output patterns at a semantic level — patterns that are invisible to statistical heuristics.

**Blind spot:** Heavily-edited AI output and highly-polished human prose may both score mid-range.

### Signal 2 — Stylometric Heuristics (pure Python)
Three sub-metrics averaged into one score:
- **Sentence-length variance** — AI text is more uniform; low variance → higher AI score
- **Type-token ratio (TTR)** — measures vocabulary diversity; extreme values → more AI-like
- **Punctuation density** — AI tends toward moderate, consistent punctuation; extremes suggest AI

Weight: **30%**.

**Why chosen:** Purely structural — independent of the semantic signal. Requires no external API call and adds a corroborating data point that is hard for lightly-edited AI output to fake.

**Blind spot:** Minimalist poetry or transcribed speech can exhibit low variance and trigger false positives.

### Signal 3 — Transition Phrase Density (pure Python)
Counts AI-typical hedging and transitional phrases per 100 words — "furthermore", "it is important to note", "moreover", "in conclusion", "additionally", etc.

Weight: **20%**.

**Why chosen:** Captures vocabulary-level patterns completely independent of Signals 1 and 2. A text can have varied sentence lengths (fooling Signal 2) and ambiguous semantics (fooling Signal 1) but still betray itself through formulaic transitions.

**Blind spot:** Academic human writing also uses formal transitions — essays may score higher than expected.

---

## Confidence Scoring

Combined score: `confidence = 0.5 × llm_score + 0.3 × stylo_score + 0.2 × transition_score`

| Score | Label |
|---|---|
| ≥ 0.70 | `likely_ai` |
| 0.36 – 0.69 | `uncertain` |
| ≤ 0.35 | `likely_human` |

The threshold for `likely_ai` is intentionally high (0.70) because **false positives harm creators more than false negatives harm readers**. A score of 0.51 produces an `uncertain` label; a score of 0.95 produces a `likely_ai` label — these are meaningfully different responses to the user.

### Example submissions

| Input | LLM | Stylo | Transition | Confidence | Label |
|---|---|---|---|---|---|
| "It is important to note that the implementation of AI necessitates a comprehensive framework for ethical governance. Furthermore, enterprises must prioritize transparency…" | 0.80 | 0.51 | 1.00 | **0.75** | `likely_ai` |
| "ok so i finally tried that new ramen place downtown and honestly? underwhelming. the broth was fine but they put WAY too much sodium in it…" | 0.20 | 0.26 | 0.00 | **0.22** | `likely_human` |

---

## Transparency Labels

All three exact variants as displayed to users:

| Variant | Label text |
|---|---|
| High-confidence AI | `"⚠️ Likely AI-Generated — Our system detected patterns consistent with AI-generated content (75% confidence). The creator may appeal this classification."` |
| Uncertain | `"❓ Origin Uncertain — Our system could not confidently determine authorship (61% confidence). When in doubt, we assume human authorship."` |
| High-confidence Human | `"✓ Likely Human-Written — Our system found no strong indicators of AI generation (22% confidence)."` |

---

## Rate Limiting

Applied to `POST /submit`:
- **10 requests per minute**
- **100 requests per day**

**Reasoning:** A legitimate creator submitting their own work might send 2–3 pieces in a session; 10/minute comfortably covers that. 100/day is generous for any single author. An adversarial script trying to probe or flood the classifier would hit the per-minute cap immediately, keeping Groq API costs bounded and preventing log pollution.

### Evidence (rate limit test)

```bash
for i in $(seq 1 12); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:5001/submit \
    -H "Content-Type: application/json" \
    -d '{"text": "test", "creator_id": "tester"}'
done
```
Actual output:
```
200
200
200
200
200
200
200
200
200
429
429
429
```

---

## Appeals Workflow

```bash
# Submit content
curl -s -X POST http://localhost:5001/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "My poem text here...", "creator_id": "alice"}'
# → note the content_id in the response

# File an appeal
curl -s -X POST http://localhost:5001/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "<ID>", "creator_reasoning": "I wrote this by hand — it reflects my personal style."}'

# Verify status updated
curl -s http://localhost:5001/log
```

The audit log entry will show `"status": "under_review"` and `"appeal_reasoning"` populated.

---

## Audit Log

Format (JSON, stored in `audit_log.json`). Retrieve live: `GET http://localhost:5001/log`

```json
[
  {
    "content_id": "302b09eb-eb00-4c3a-a11c-a181d8f464e1",
    "creator_id": "test-user-1",
    "timestamp": "2026-06-30T06:15:03.792381+00:00",
    "attribution": "uncertain",
    "confidence": 0.6129,
    "llm_score": 0.8,
    "stylo_score": 0.3322,
    "transition_score": 0.0,
    "status": "under_review",
    "appeal_reasoning": "I wrote this myself for my ethics essay — the formal tone is intentional, not AI-generated."
  },
  {
    "content_id": "65ae0329-beab-4e13-ad7c-0d8e1473a216",
    "creator_id": "test-user-2",
    "timestamp": "2026-06-30T06:15:11.279615+00:00",
    "attribution": "likely_human",
    "confidence": 0.2229,
    "llm_score": 0.2,
    "stylo_score": 0.2572,
    "transition_score": 0.0,
    "status": "classified",
    "appeal_reasoning": null
  },
  {
    "content_id": "21948fe1-5e29-49a5-a4e0-ce14dbd4a9e2",
    "creator_id": "ensemble-test",
    "timestamp": "2026-06-30T07:02:15.123456+00:00",
    "attribution": "likely_ai",
    "confidence": 0.7536,
    "llm_score": 0.8,
    "stylo_score": 0.512,
    "transition_score": 1.0,
    "status": "classified",
    "appeal_reasoning": null
  }
]
```

---

## Known Limitations

**Minimalist poetry** will likely be misclassified as AI. Short, rhythmically regular lines with simple vocabulary produce low sentence-length variance and may have atypical TTR — both push the stylometric score toward AI. The LLM signal may partially compensate if the poem's voice is distinctive, but the combined score will often land in `uncertain` at best. This is a property of the stylometric signal's inability to account for intentional formal constraint.

---

## Spec Reflection

**Where the spec helped:** Deciding confidence thresholds before writing any code (`planning.md`) meant the label logic in `signals.py` had a concrete contract to implement against. There was no "figure it out later" moment — the 0.70 / 0.35 thresholds were already justified before a single line of Flask code existed.

**Where implementation diverged:** The spec described a separate storage lookup for appeals. In practice, the audit log itself serves as both the event log and the mutable state store — `log_appeal()` mutates the existing entry rather than appending a new one. This is simpler and sufficient at this scale, but would not work in a distributed system.

---

## AI Usage

1. **Groq prompt design:** I directed the LLM to return only a bare float with no explanation. Initial output sometimes included reasoning text ("The probability is 0.7 because..."). I added a regex extraction fallback in `llm_classify()` to strip surrounding text, which the AI hadn't included.

2. **Stylometric scoring normalisation:** Asked Claude to suggest normalisation ranges for sentence-length variance. The initial suggestion used variance > 100 as the "fully human" cap. After testing on real inputs, I tightened it to 40 — variance > 40 is already quite human-like for prose, and the original range compressed most real inputs into a narrow band near 0.

---

## Stretch Features

### Ensemble Detection (3rd Signal)

Added **transition phrase density** as Signal 3 — counts AI-typical hedging and transitional phrases ("furthermore", "it is important to note", "moreover", "in conclusion", etc.) per 100 words.

**Why distinct from Signals 1 & 2:** Captures vocabulary-level patterns independent of both semantic LLM scoring and structural stylometrics. A text can have varied sentence lengths (fooling Signal 2) and ambiguous semantics (fooling Signal 1) but still betray itself through formulaic transition phrases.

**Updated weighting:**
```
confidence = 0.5 × llm_score + 0.3 × stylo_score + 0.2 × transition_score
```

**Blind spot:** Academic human writing also uses formal transitions — essays and research writing may score higher than expected.

**Live test result:**
```json
{
  "signals": { "llm_score": 0.8, "stylo_score": 0.51, "transition_score": 1.0 },
  "confidence": 0.75,
  "attribution": "likely_ai"
}
```

### Analytics Dashboard

`GET /analytics` returns detection patterns across all submissions:

```bash
curl http://localhost:5001/analytics
```

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

- **Attribution breakdown** — distribution across all three label categories
- **Appeal rate** — % of submissions that received an appeal
- **Average confidence** — overall system certainty across all decisions

---

## File Structure

```
app.py          # Flask routes: POST /submit, POST /appeal, GET /log, GET /analytics
signals.py      # llm_classify(), stylo_score(), transition_score(), combine_scores(), make_label()
audit.py        # JSON-backed audit log helpers
planning.md     # Architecture, spec, stretch features, AI tool plan
audit_log.json  # Generated at runtime (git-ignored)
.env            # GROQ_API_KEY (git-ignored)
requirements.txt
```
