"""
Intent classifier and router for Phase 1 multi-agent.

Classifies user queries into: quick | config | investigation | report | exploration.
Routes quick intent to fast model (Ollama), others to primary ADK agent.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

VALID_INTENTS = frozenset({"quick", "config", "investigation", "report", "exploration"})


def classify_intent(message: str) -> str:
    """Classify user message into one of: quick, config, investigation, report, exploration.

    Uses rule-based patterns derived from agent_intent_dataset.json.
    Check order: more specific patterns first.
    """
    if not message or not isinstance(message, str):
        return "exploration"  # safe default

    text = message.strip().lower()
    if not text:
        return "quick"

    # Investigation: anomalies, failures, root cause
    investigation_patterns = [
        r"\bwhy\b",
        r"\bfail(?:ed|ure)?\b",
        r"\banomal(?:y|ies)\b",
        r"\binvestigate\b",
        r"\broot cause\b",
        r"\bcaused?\b",
        r"\bdebug(?:ging)?\b",
        r"\btroubleshoot\b",
    ]
    if any(re.search(p, text) for p in investigation_patterns):
        return "investigation"

    # Config: create, suggest, add, clefs
    config_patterns = [
        r"\bcreate\s+(?:a\s+)?(?:new\s+)?(?:stave|clef|check)\b",
        r"\bsuggest\s+(?:quality\s+)?checks?\b",
        r"\badd\s+(?:a\s+)?(?:freshness|quality)\s+check\b",
        r"\b(?:what|which|list)\s+clefs?\b",
        r"\bclefs?\s+(?:do\s+i\s+have|are\s+there)\b",
        r"\b(?:set up|configure|setup)\s+",  # configure stave, set up checks
    ]
    if any(re.search(p, text) for p in config_patterns):
        return "config"

    # Report: summary, report
    report_patterns = [
        r"\bsummary\s+(?:of\s+)?(?:the\s+)?(?:system|status)\b",
        r"\bquality\s+report\b",
        r"\bshow\s+(?:me\s+)?(?:the\s+)?(?:quality\s+)?report\b",
        r"\b(?:give|get)\s+me\s+a\s+summary\b",
        r"\boverview\s+of\b",
    ]
    if any(re.search(p, text) for p in report_patterns):
        return "report"

    # Exploration: tables, sample, structure (with stave/datasource context)
    exploration_patterns = [
        r"\btables?\s+(?:in|from)\s+",
        r"\b(?:list|show)\s+(?:me\s+)?(?:the\s+)?tables?\b",
        r"\bsample\s+(?:of\s+)?(?:the\s+)?(?:data|table)\b",
        r"\bshow\s+me\s+a\s+sample\b",
        r"\binclude_structure\b",  # API param
        r"\b(?:with\s+)?structure\b",  # "list tables with structure"
        r"\bwhat\s+tables?\s+(?:are\s+)?in\b",
    ]
    if any(re.search(p, text) for p in exploration_patterns):
        return "exploration"

    # Quick: greetings, status, simple counts, list data sources/staves
    quick_patterns = [
        r"^(?:hi|hello|hey|yo)\s*!?$",
        r"\b(?:what('s|s| is)\s+)?(?:the\s+)?status\b",
        r"\bhow\s+many\s+(?:staves?|clefs?|checks?|data\s+sources?)\b",
        r"\blist\s+(?:my\s+)?(?:data\s+)?sources?\b",
        r"\blist\s+(?:my\s+)?staves?\b",
        r"\b(?:what|list)\s+(?:data\s+)?sources?\b",
        r"^(?:how\s+many|count)\s*\??$",
    ]
    if any(re.search(p, text) for p in quick_patterns):
        return "quick"

    # Short messages (<= 3 words) likely quick
    word_count = len(text.split())
    if word_count <= 3:
        return "quick"

    # Default: exploration (browsing/exploring is common fallback)
    return "exploration"


def resolve_model_for_intent(
    intent: str,
    model_primary: str,
    model_quick: str | None,
) -> str:
    """Return the model to use for the given intent.

    Quick intent uses model_quick if set; otherwise model_primary.
    """
    if intent == "quick" and model_quick:
        return model_quick
    return model_primary


def load_intent_dataset() -> dict | None:
    """Load agent_intent_dataset.json for evaluation."""
    base = Path(__file__).resolve().parent
    paths = [
        base.parent.parent / "agent_intent_dataset.json",
        base / "agent_intent_dataset.json",
    ]
    for p in paths:
        if p.exists():
            try:
                return json.loads(p.read_text())
            except json.JSONDecodeError as e:
                logger.warning("Could not parse %s: %s", p, e)
                return None
    return None


def evaluate_classifier_against_dataset() -> dict:
    """Run classifier on intent dataset examples, return accuracy stats."""
    dataset = load_intent_dataset()
    if not dataset or "examples" not in dataset:
        return {"error": "No dataset or examples found", "accuracy": 0.0}

    correct = 0
    total = len(dataset["examples"])
    mismatches = []

    for ex in dataset["examples"]:
        query = ex.get("query", "")
        expected = ex.get("intent", "")
        predicted = classify_intent(query)
        if predicted == expected:
            correct += 1
        else:
            mismatches.append({"query": query, "expected": expected, "predicted": predicted})

    return {
        "accuracy": correct / total if total else 0.0,
        "correct": correct,
        "total": total,
        "mismatches": mismatches[:20],
    }
