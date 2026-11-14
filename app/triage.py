"""Sort an incoming text into a need category and urgency.

Uses Claude when ANTHROPIC_API_KEY is set, otherwise a keyword fallback.
The emergency check always runs on keywords too, so a missed API call can
never hide a crisis message.
"""
import json
import logging
import re

from . import config

log = logging.getLogger("triage")

CATEGORIES = [
    "transportation", "medication", "appointment", "food", "housing",
    "mental_health", "insurance", "utilities", "other",
]
URGENCIES = ["low", "medium", "high", "emergency"]

EMERGENCY_WORDS = re.compile(
    r"chest pain|can'?t breathe|cannot breathe|not breathing|stroke|overdos|unconscious|"
    r"bleeding a lot|severe bleeding|suicid|kill myself|end my life|want to die",
    re.I,
)
CRISIS_WORDS = re.compile(r"suicid|kill myself|end my life|want to die", re.I)

KEYWORDS = {
    "transportation": r"\bride\b|transport|\bbus\b|\bcar\b|\bdrive\b|gas money|get to (my|the)",
    "medication": r"\bmeds?\b|medicine|medication|prescription|refill|pharmacy|insulin|inhaler",
    "appointment": r"appointment|\bappt\b|doctor|schedule|clinic|telehealth|visit",
    "food": r"\bfood\b|hungry|groceries|\bsnap\b|\bwic\b|pantry|\bmeal",
    "housing": r"housing|\brent\b|evict|homeless|shelter",
    "mental_health": r"depress|anxi|stress|lonely|counsel|therap|mental",
    "insurance": r"insurance|medicaid|medicare|\bbill\b|copay|coverage",
    "utilities": r"electric|heat|\bwater\b|utility|utilities|phone bill|internet",
}
SPANISH = re.compile(r"\b(hola|necesito|ayuda|cita|medicina|gracias|por favor|no tengo)\b", re.I)


def _keyword_triage(text: str) -> dict:
    category = next((c for c, rx in KEYWORDS.items() if re.search(rx, text, re.I)), "other")
    urgent = re.search(r"urgent|asap|today|right now|ran out|out of", text, re.I)
    return {
        "category": category,
        "urgency": "high" if urgent else "medium",
        "summary": text[:140],
        "language": "es" if SPANISH.search(text) else "en",
    }


PROMPT = """You triage text messages sent to a rural community health line in Southeast Ohio.
Return ONLY a JSON object with keys:
  "category": one of {cats}
  "urgency": one of {urgs}  ("emergency" = danger to life right now)
  "summary": one plain sentence (max 140 chars) a community health worker can act on
  "language": ISO 639-1 code of the message language
Message:
<<<{text}>>>"""


def _claude_triage(text: str) -> dict | None:
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=config.TRIAGE_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": PROMPT.format(
                cats=CATEGORIES, urgs=URGENCIES, text=text)}],
        )
        raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        return {
            "category": data.get("category") if data.get("category") in CATEGORIES else "other",
            "urgency": data.get("urgency") if data.get("urgency") in URGENCIES else "medium",
            "summary": str(data.get("summary") or text)[:140],
            "language": str(data.get("language") or "en")[:5],
        }
    except Exception as e:  # network, parsing, quota: never block a patient's text
        log.warning("Claude triage failed, using keywords: %s", e)
        return None


def triage(text: str) -> dict:
    result = (_claude_triage(text) if config.ANTHROPIC_API_KEY else None) or _keyword_triage(text)
    if EMERGENCY_WORDS.search(text):
        result["urgency"] = "emergency"
    result["crisis"] = bool(CRISIS_WORDS.search(text))
    return result
