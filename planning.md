# Provenance Guard — Planning

## Detection Signals

### Signal 1: LLM Classification (Groq `llama-3.3-70b-versatile`)
- **Measures:** Semantic coherence, stylistic uniformity, phrasing patterns typical of LLMs
- **Output:** Float 0–1 (probability content is AI-generated)
- **Blind spot:** Highly-edited AI output; very polished human writing may score high

### Signal 2: Stylometric Heuristics (pure Python)
Computes 3 metrics, averages into one score:
- **Sentence length variance** — AI text is more uniform; low variance → higher AI score
- **Type-token ratio (TTR)** — AI uses more varied vocabulary ironically, but in predictable patterns; we weight low TTR as more AI-like
- **Punctuation density** — AI tends toward moderate, consistent punctuation
- **Output:** Float 0–1
- **Blind spot:** Minimalist or intentionally sparse human writing (e.g., poetry) may show low variance and score as AI

### Combining Signals
Weighted average: `confidence = 0.6 * llm_score + 0.4 * stylo_score`

LLM signal gets higher weight as it captures semantic meaning; stylometrics acts as a corroborating structural check.

## Uncertainty Representation

| Score range | Label category | Rationale |
|---|---|---|
| ≥ 0.70 | `likely_ai` | Strong agreement across signals |
| 0.36 – 0.69 | `uncertain` | Signals disagree or both are mid-range |
| ≤ 0.35 | `likely_human` | Strong signal of human origin |

A score of 0.6 means: "the system leans toward AI but not confidently — show the uncertain label." We bias toward human (lower threshold for `likely_ai`) because false positives harm creators more than false negatives harm readers.

## Transparency Label Design

| Variant | Exact label text |
|---|---|
| High-confidence AI | `"⚠️ Likely AI-Generated — Our system detected patterns consistent with AI-generated content ({score:.0%} confidence). The creator may appeal this classification."` |
| Uncertain | `"❓ Origin Uncertain — Our system could not confidently determine authorship ({score:.0%} confidence). When in doubt, we assume human authorship."` |
| High-confidence Human | `"✓ Likely Human-Written — Our system found no strong indicators of AI generation ({score:.0%} confidence)."` |

## Appeals Workflow

- **Who:** Any creator with a `content_id` from a prior `/submit` response
- **Input fields:** `content_id`, `creator_reasoning` (free text)
- **On receipt:** status → `under_review`; appeal entry written to audit log alongside original decision
- **Human reviewer sees:** original classification, confidence, both signal scores, creator's reasoning, timestamp

## Anticipated Edge Cases

1. **Minimalist poetry** — Short lines, simple vocabulary, and deliberate repetition will score low on TTR and sentence variance, potentially pushing stylometric score high even for human work.
2. **Transcribed speech** — Informal spoken text run through speech-to-text (filled pauses removed) may read as very regular, triggering false AI signals.

## Architecture

```
POST /submit
    │
    ├─[text]──► Signal 1: LLM (Groq)      ──► llm_score (0–1)
    │                                                │
    └─[text]──► Signal 2: Stylometrics    ──► stylo_score (0–1)
                                                     │
                                          confidence = 0.6*llm + 0.4*stylo
                                                     │
                                          label = map(confidence)
                                                     │
                                          audit_log.append(entry)
                                                     │
                                          ◄── JSON response (content_id, attribution,
                                                            confidence, label)

POST /appeal
    │
    ├─[content_id] ──► lookup entry ──► status = "under_review"
    └─[creator_reasoning] ──► audit_log.append(appeal_entry)
                                    │
                              ◄── confirmation JSON

GET /log  ──► return last N audit entries as JSON
```

**Submission flow:** Text enters `/submit`, runs through both signals in sequence, scores are weighted-averaged into a confidence value, mapped to one of three label variants, written to the audit log, and returned to the caller.

**Appeal flow:** A `content_id` + reasoning hits `/appeal`, which locates the original entry, flips its status to `under_review`, appends the appeal to the log, and confirms receipt.

## AI Tool Plan

### M3 — Submission endpoint + Signal 1
- **Provide to AI:** Detection signals section + Architecture diagram
- **Ask for:** Flask app skeleton with `POST /submit` stub + `llm_classify(text)` function returning a float
- **Verify:** Call `llm_classify` directly on 2 test strings before wiring into the route

### M4 — Signal 2 + Confidence scoring
- **Provide to AI:** Detection signals + Uncertainty representation + Architecture
- **Ask for:** `stylo_score(text)` function + `combine_scores(llm, stylo)` per the weighted formula
- **Verify:** Scores differ meaningfully between clearly AI and clearly human test inputs

### M5 — Production layer
- **Provide to AI:** Label design table + Appeals workflow + Architecture
- **Ask for:** `make_label(confidence, attribution)` + `POST /appeal` endpoint
- **Verify:** All three label variants reachable; appeal changes status in `/log` output
