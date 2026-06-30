import re
import os
from groq import Groq

_client = None

def _groq():
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


def llm_classify(text: str) -> float:
    """Return probability (0–1) that text is AI-generated via Groq."""
    prompt = (
        "Rate the probability this text is AI-generated. "
        "Reply with ONLY a number between 0.0 (definitely human) and 1.0 (definitely AI). "
        "No explanation.\n\nText:\n" + text[:2000]
    )
    resp = _groq().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )
    raw = resp.choices[0].message.content.strip()
    try:
        score = float(re.search(r"[\d.]+", raw).group())
        return max(0.0, min(1.0, score))
    except Exception:
        return 0.5


def stylo_score(text: str) -> float:
    """Return probability (0–1) text is AI-generated from stylometric heuristics."""
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if len(sentences) < 2:
        return 0.5

    # Sentence length variance (low variance → more AI-like)
    lengths = [len(s.split()) for s in sentences]
    mean_len = sum(lengths) / len(lengths)
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    # Normalise: variance > 40 = very human-like, variance < 5 = very AI-like
    var_score = max(0.0, min(1.0, 1.0 - (variance / 40.0)))

    # Type-token ratio (lower TTR → more repetitive → slightly more AI-like)
    words = re.findall(r"\b\w+\b", text.lower())
    ttr = len(set(words)) / len(words) if words else 0.5
    # TTR < 0.4 is repetitive, > 0.8 is very diverse
    ttr_score = max(0.0, min(1.0, 1.0 - ((ttr - 0.4) / 0.4)))

    # Punctuation density (very low or very high → more AI-like)
    punct_count = sum(1 for c in text if c in ",.;:!?")
    punct_density = punct_count / max(len(text), 1)
    # Moderate density (0.04–0.08) is human; extremes are AI
    punct_score = max(0.0, min(1.0, abs(punct_density - 0.06) / 0.06))

    return round((var_score + ttr_score + punct_score) / 3, 4)


def combine_scores(llm: float, stylo: float) -> float:
    return round(0.6 * llm + 0.4 * stylo, 4)


def attribution(confidence: float) -> str:
    if confidence >= 0.70:
        return "likely_ai"
    if confidence <= 0.35:
        return "likely_human"
    return "uncertain"


def make_label(confidence: float, attr: str) -> str:
    pct = f"{confidence:.0%}"
    if attr == "likely_ai":
        return (
            f"⚠️ Likely AI-Generated — Our system detected patterns consistent with "
            f"AI-generated content ({pct} confidence). The creator may appeal this classification."
        )
    if attr == "likely_human":
        return (
            f"✓ Likely Human-Written — Our system found no strong indicators of "
            f"AI generation ({pct} confidence)."
        )
    return (
        f"❓ Origin Uncertain — Our system could not confidently determine authorship "
        f"({pct} confidence). When in doubt, we assume human authorship."
    )
