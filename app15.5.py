"""
🚨 LUMII CRITICAL SAFETY FIXES - US BETA FAMILIES READY

INTERNAL DEVELOPMENT NOTES (NOT VISIBLE TO USERS):
- All conversation log analysis results and critical fixes implemented
- Crisis detection patterns comprehensive for teen expressions
- US-focused crisis resources (988, 741741, 911) for beta families  
- Age-adaptive messaging for Elementary vs Middle/High School
- Behavior detection fixed to avoid false positives
- All safety gaps from conversation testing addressed
- ✅ NEW: Confusion detection added to prevent false positives on legitimate student confusion

SAFETY STATUS: 🇺🇸 OPTIMIZED FOR US BETA FAMILIES
"""

from typing import Final, List, Pattern

import json
import re
import time
import uuid
from datetime import datetime

import requests
import streamlit as st

# === Grade/Age detection (ADD THESE LINES) ===============================
# e.g., "grade 8", "8th grade", "in 8th grade", "I'm in 8th grade"
GRADE_RX: Final[Pattern[str]] = re.compile(
    r"\b(?:grade\s*(\d{1,2})(?:st|nd|rd|th)?|(\d{1,2})(?:st|nd|rd|th)\s*grade)\b",
    re.IGNORECASE,
)

# e.g., "I'm 13", "I am 13" — but NOT "I'm 8th grade"
AGE_RX: Final[Pattern[str]] = re.compile(
    r"\b(?:i[' ]?m|i am)\s+(\d{1,2})(?!\s*(?:st|nd|rd|th)\s*grade)\b",
    re.IGNORECASE,
)


def grade_to_age(grade_num: int) -> int:
    """Approximate US age from grade: age ≈ grade + 5, clamped to [6, 18]."""
    return max(6, min(18, int(grade_num) + 5))


def age_to_grade(age_num: int) -> int:
    """Approximate US grade from age: grade ≈ age − 5, clamped to [1, 12]."""
    return max(1, min(12, int(age_num) - 5))


def _make_ordinal(n: int) -> str:
    """Return English ordinal string for an integer (e.g., 1 -> '1st')."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

# =============================================================================
# ACADEMIC-STRESS RESPONSE GUARDS — grade confidence + dev badge gating
# =============================================================================
from typing import Optional
import re
import streamlit as st

# Reuses existing: GRADE_RX, _make_ordinal

def _extract_explicit_grade_from_text(text: str) -> Optional[int]:
    """Return grade number if explicitly mentioned in the current message (e.g., '7th grade')."""
    try:
        m = GRADE_RX.search(text or "")
        if not m:
            return None
        grp = next((g for g in m.groups() if g), None)  # GRADE_RX has two capturing groups
        return int(grp) if grp is not None else None
    except Exception:
        return None

def _get_confirmed_grade_from_state() -> Optional[int]:
    """
    Return a previously confirmed grade from session state if available.
    - st.session_state['student_grade_confirmed'] == True and ['student_grade'] is int
    - or st.session_state['student_profile']['grade_level'] when grade_confirmed True (if present)
    """
    try:
        if st.session_state.get("student_grade_confirmed") and isinstance(st.session_state.get("student_grade"), int):
            return int(st.session_state["student_grade"])
        prof = st.session_state.get("student_profile") or {}
        if isinstance(prof, dict) and isinstance(prof.get("grade_level"), int):
            if prof.get("grade_confirmed", True):
                return int(prof["grade_level"])
    except Exception:
        pass
    return None

def _grade_is_confident(message: str) -> Optional[int]:
    """
    Confidence policy:
      1) If the user explicitly says a grade in THIS message → use it.
      2) Else if we have a previously CONFIRMED grade in session/profile → use it.
      3) Otherwise → don't guess.
    """
    explicit = _extract_explicit_grade_from_text(message)
    if explicit is not None:
        return explicit
    return _get_confirmed_grade_from_state()

def build_grade_prefix(message: str) -> str:
    """Return '7th grade, wow! ' only when grade is confident; otherwise return ''."""
    g = _grade_is_confident(message)
    if g is None:
        return ""
    try:
        return f"{_make_ordinal(g)} grade, wow! "
    except Exception:
        return ""  # if anything odd, omit instead of guessing

def _is_true_like(val: str) -> bool:
    return str(val).strip().lower() in ("1", "true", "yes", "on")

def should_show_user_memory_badge() -> bool:
    """
    Show 🌟 Lumii's Learning Support🧠 With Memory ONLY when explicitly allowed:
      - st.secrets['SHOW_MEMORY_BADGE_TO_USERS'] == true
      - or st.session_state['ui_dev_mode'] == True (dev/testing)
    Defaults to False (hide for students/parents).
    """
    try:
        if _is_true_like(st.secrets.get("SHOW_MEMORY_BADGE_TO_USERS", "false")):
            return True
    except Exception:
        pass
    return bool(st.session_state.get("ui_dev_mode", False))

def append_memory_badge_if_allowed(text: str) -> str:
    """Append the badge only if allowed. Does not change your normal copy."""
    if should_show_user_memory_badge():
        return text + "\n🌟 Lumii's Learning Support🧠 With Memory"
    return text



# Ensure session keys exist once per session
st.session_state.setdefault("locked_after_crisis", False)

# =============================================================================
# NORMALIZATION FUNCTION FOR BETTER PATTERN MATCHING
# =============================================================================

# Common confusion typos (K-12) -> "confused"
_CONFUSION_TYPO_MAP: Final[List[Pattern[str]]] = [
    re.compile(r"\bcofused\b", re.IGNORECASE),
    re.compile(r"\bconfusd\b", re.IGNORECASE),
    re.compile(r"\bconufsed\b", re.IGNORECASE),
    re.compile(r"\bcnofused\b", re.IGNORECASE),
]


def normalize_message(message: str) -> str:
    """
    Normalize a user message for robust pattern matching.
    - Trims whitespace
    - Normalizes "im" -> "i'm"
    - Fixes common 'confused' typos
    """
    msg = message.strip()

    # Normalize "im" -> "i'm" (keeps other casing intact due to IGNORECASE)
    msg = re.sub(r"\bim\b", "i'm", msg, flags=re.IGNORECASE)

    # Normalize common confusion typos
    for rx in _CONFUSION_TYPO_MAP:
        msg = rx.sub("confused", msg)

    return msg


# Page configuration (guarded to avoid duplicate configuration errors)
if not st.session_state.get("_page_configured", False):
    st.set_page_config(
        page_title="My Friend Lumii - Your AI Learning Companion",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.session_state["_page_configured"] = True

# =============================================================================
# ENHANCED CRISIS DETECTION - GLOBAL GUARD SYSTEM (CRITICAL SAFETY FIXES)
# =============================================================================

# Enhanced crisis patterns with typo tolerance and euphemisms - CHATGPT CRITICAL FIXES APPLIED
ENHANCED_CRISIS_PATTERNS: Final[List[Pattern[str]]] = [
    # Core self-harm patterns with typo tolerance
    re.compile(
        r"\bi\s+(?:think\s+)?(?:maybe\s+)?(?:i\s+)?should\s+(?:just\s+)?(?:disappear|dissapear|disapear|dissapeare|vanish|go\s+away|fade\s+away)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bi\s+(?:want\s+to|wanna|wish\s+i\s+could)\s+(?:just\s+)?(?:disappear|dissapear|disapear|vanish)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:better\s+if\s+)?i\s+(?:just\s+)?(?:disappeared|dissapeared|vanished|went\s+away)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bi\s+should\s+(?:just\s+)?(?:not\s+exist|stop\s+existing|be\s+gone)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:wan(?:t|na))\s+(?:t+o|do|2)\s+(?:die|kil+\s*myself)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:wan(?:t|na))\s+(?:t+o|do|2)\s+(?:hurt|harm)\s+myself\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(?:wan(?:t|na))\s+(?:t+o|do|2)\s+(?:end|stop)\s+(?:my\s+life|everything)\b",
        re.IGNORECASE,
    ),
    # 🚨 FIXED: "if i'm gone" vs "if i was gone"
    re.compile(
        r'\b(?:everybody|everyone|people|family|my\s+(?:parents|family|friends))\s+(?:would\s+be\s+)?(?:happier|better)\s+(?:if\s+)?i\s*(?:am|["\'\′]?\s*m)\s+gone\b',
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:everybody|everyone|people|family|my\s+(?:parents|family|friends))\s+(?:would\s+be\s+)?(?:happier|better)\s+(?:if\s+)?(?:i\s+was\s+gone|without\s+me)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwould\s+be\s+(?:happier|better)\s+(?:if\s+)?(?:i\s+was\s+gone|without\s+me)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:happier|better)\s+(?:if\s+)?(?:i\s+(?:just\s+)?(?:disappeared|was\s+gone|wasnt\s+here))\b",
        re.IGNORECASE,
    ),
    # Teen crisis expressions
    re.compile(r"\bno\s+one\s+would\s+miss\s+me\b", re.IGNORECASE),
    re.compile(r"\b(?:i\s+)?wish\s+i\s+(?:were|was)\s+dead\b", re.IGNORECASE),
    re.compile(r"\b(?:better|better\s+off)\s+dead\b", re.IGNORECASE),
    re.compile(r"\b(?:unalive|unalive\s+myself|self\s*delete|delete\s+myself|off\s+myself)\b", re.IGNORECASE),
    re.compile(r"\b(?:kms|kys)\b", re.IGNORECASE),
    re.compile(r"\bend\s+it\s+all\b", re.IGNORECASE),
    re.compile(r"\b(?:stop|quit)\s+(?:existing|being\s+alive)\b", re.IGNORECASE),
    re.compile(r"\b(?:i\s+just\s+)?(?:want|wanna)\s+(?:to\s+)?(?:sleep\s+forever|not\s+wake\s+up)\b", re.IGNORECASE),
    re.compile(r"\bi\s+don\'?t\s+deserve\s+to\s+live\b", re.IGNORECASE),
    re.compile(r"\bi\s+shouldn\'?t\s+exist\b", re.IGNORECASE),
    # Methods and passive wish phrasing
    re.compile(r"\b(?:jump\s+off|hang\s+myself|od|overdos(?:e|ing))\b", re.IGNORECASE),
    re.compile(r"\bi'?d\s+be\s+ok(?:ay)?\s+if\s+(?:a\s+)?car\s+hit\s+me\b", re.IGNORECASE),
    re.compile(r"\bi\s+hope\s+i\s+don'?t\s+wake\s+up\b", re.IGNORECASE),
    # 🚨 Critical fixes
    re.compile(
        r"\bi\s+(?:think\s+)?(?:i\s+)?should\s+(?:just\s+)?(?:disappear|dissapear|disapear|vanish|go\s+away|not\s+be\s+here|stop\s+existing)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r'\b(?:it\s+)?would\s+be\s+(?:happier|better)\s+(?:for\s+(?:every(?:one|body)|people|them|my\s+(?:family|parents|friends))\s+)?(?:if\s+)?i\s*(?:am|["\'\′]?\s*m)\s+gone\b',
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:it\s+)?would\s+be\s+(?:happier|better)\s+(?:for\s+(?:every(?:one|body)|people|them|my\s+(?:family|parents|friends))\s+)?(?:if\s+)?(?:i\s+(?:was|were)\s+gone|without\s+me)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r'\bi\s+(?:really\s+)?think\s+(?:it\s+)?would\s+be\s+(?:happier|better)\s+(?:for\s+(?:every(?:one|body)|people|them|my\s+(?:family|parents|friends))\s+)?(?:if\s+)?i\s*(?:am|["\'\′]?\s*m)\s+gone\b',
        re.IGNORECASE,
    ),
    re.compile(
        r"\bi\s+(?:really\s+)?think\s+(?:it\s+)?would\s+be\s+(?:happier|better)\s+(?:for\s+(?:every(?:one|body)|people|them|my\s+(?:family|parents|friends))\s+)?(?:if\s+)?(?:i\s+(?:was|were)\s+gone|without\s+me)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:better|happier)\s+for\s+(?:every(?:one|body)|people|them|my\s+(?:family|parents|friends))\s+if\s+i\s*(?:am|['\′]?\s*m)\s+gone\b",
        re.IGNORECASE,
    ),
    # "I want to end it"
    re.compile(r"\bi\s+(?:just\s+)?wan(?:t|na)\s+(?:to\s+)?end\s+it\b", re.IGNORECASE),
    # Euphemisms / typos
    re.compile(r"\b(?:wan(?:t|na))\s+(?:t+o|do|2)?\s*disappear\b", re.IGNORECASE),
    re.compile(r"\b(?:wan(?:t|na))\s+(?:t+o|do|2)?\s*dissapear\b", re.IGNORECASE),
    re.compile(r"\b(?:wan(?:t|na))\s+(?:t+o|do|2)?\s*disapear\b", re.IGNORECASE),
    re.compile(r"\b(?:wan(?:t|na))\s+(?:t+o|do|2)?\s*vanish\b", re.IGNORECASE),
    re.compile(r"\b(?:wan(?:t|na))\s+(?:t+o|do|2)?\s*(?:go\s+away|fade\s+away)\b", re.IGNORECASE),
    re.compile(r"\b(?:don'?t|dont)\s+(?:wan(?:t|na))\s+(?:t+o|do|2)\s+(?:be\s+here|exist|live)\s+anymore\b", re.IGNORECASE),
    re.compile(r"\bno\s+(?:reason|point)\s+(?:t+o|do|2)\s+(?:live|be\s+here|exist)\b", re.IGNORECASE),
    re.compile(r"\bworld\s+(?:would\s+be\s+)?better\s+without\s+me\b", re.IGNORECASE),
    # Direct expressions
    re.compile(r"\bkill\s+myself\b", re.IGNORECASE),
    re.compile(r"\bhurt\s+myself\b", re.IGNORECASE),
    re.compile(r"\bend\s+my\s+life\b", re.IGNORECASE),
    re.compile(r"\bcommit\s+suicide\b", re.IGNORECASE),
    re.compile(r"\bcut\s+myself\b", re.IGNORECASE),
    re.compile(r"\bself\s*-?\s*harm\b", re.IGNORECASE),
    # Immediate action
    re.compile(r"\bgoing\s+to\s+(?:kill|hurt|end)\s+myself\b", re.IGNORECASE),
    re.compile(r"\bdecided\s+to\s+(?:die|end\s+it|kill\s+myself)\b", re.IGNORECASE),
    re.compile(r"\btonight\s+(?:is\s+the\s+night|i\s+end\s+it)\b", re.IGNORECASE),
]


# =============================================================================
# CONFUSION PATTERNS FOR LEGITIMATE STUDENT CONFUSION (with smart-quote fix)
# =============================================================================

from typing import Final, List, Pattern, Dict, Tuple, Optional
import re
import streamlit as st

# NOTE: relies on `normalize_message`, `detect_age_from_message_and_history`,
# and `generate_age_adaptive_crisis_intervention` defined elsewhere in the app.

# Normalize common non-ASCII apostrophes to ASCII "'"
_APOSTROPHE_RX: Final[Pattern[str]] = re.compile(r"[’‘‛`´′]")

CONFUSION_PATTERNS: Final[List[Pattern[str]]] = [
    # "i'm so confused" + common misspellings; tolerate smart/variant apostrophes
    re.compile(
        r"\bi\s*(?:am|['’′`´]?\s*m)\s+(?:so\s+)?(?:confus(?:e|ed|ing)|cofused|confusd|conufsed|cnofused)\b",
        re.IGNORECASE,
    ),
    # "i don't get/understand/follow" (smart/variant apostrophes tolerated)
    re.compile(r"\b(?:i\s+)?don['’′`´]?t\s+(?:get|understand|follow)\b", re.IGNORECASE),
    # "this/that/it makes no sense"
    re.compile(r"\b(?:this|that|it)\s+makes?\s+no\s+sense\b", re.IGNORECASE),
    # "idk" or "i don't know" (smart/variant apostrophes tolerated)
    re.compile(r"\b(?:idk|i\s+don['’′`´]?t\s+know)\b", re.IGNORECASE),
    # "i'm lost/stuck" (smart/variant apostrophes tolerated)
    re.compile(r"\bi\s*(?:am|['’′`´]?\s*m)\s+(?:lost|stuck)\b", re.IGNORECASE),
]

IMMEDIATE_TERMINATION_PATTERNS: Final[List[Pattern[str]]] = [
    # Direct + time-bound
    re.compile(
        r"\bkill\s+myself\s+(?:now|right\s+now|today|tonight|this\s+(?:minute|instant|evening|afternoon))\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bhurt\s+myself\s+(?:now|right\s+now|today|tonight)\b", re.IGNORECASE),
    re.compile(r"\bcut\s+myself\s+(?:now|right\s+now|today|tonight)\b", re.IGNORECASE),
    re.compile(r"\bend(?:ing)?\s+my\s+life\s+(?:now|today|tonight)\b", re.IGNORECASE),
    # Commit / overdose
    re.compile(r"\bcommit\s+suicide\b", re.IGNORECASE),
    re.compile(
        r"\b(?:overdos(?:e|ing)|od)\s+(?:now|right\s+now|today|tonight)\b",
        re.IGNORECASE,
    ),
    # "End it" / make it stop (immediate)
    re.compile(r"\bend\s+it\s+(?:now|today|tonight)\b", re.IGNORECASE),
    re.compile(r"\bi\s+(?:just\s+)?wan(?:t|na)\s+(?:to\s+)?end\s+it\b", re.IGNORECASE),
    re.compile(
        r"\bi\s+(?:just\s+)?wan(?:t|na)\s+(?:to\s+)?make\s+it\s+all\s+stop\b",
        re.IGNORECASE,
    ),
    # Future intent phrased as immediate plan
    re.compile(
        r"\b(?:i\s*(?:am|[\'′]?\s*m)\s+)?(?:going\s+to|gonna)\s+(?:kill|hurt|end)\s+myself\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bi\s+will\s+(?:kill|hurt|end)\s+myself\b", re.IGNORECASE),
    # Your original queries (kept, but hardened with IGNORECASE + spacing)
    re.compile(r"\bhow\s+to\s+die\b", re.IGNORECASE),
    re.compile(r"\bpainless\s+death\b", re.IGNORECASE),
    # Specific phrases you had (normalized + IGNORECASE)
    re.compile(r"\bwant\s+to\s+hurt\s+myself\s+right\s+now\b", re.IGNORECASE),
    re.compile(r"\bgoing\s+to\s+kill\s+myself\b", re.IGNORECASE),
    re.compile(r"\bdecided\s+to\s+die\b", re.IGNORECASE),
    # Practical pill-taking immediate intent (optional but useful)
    re.compile(
        r"\btake\s+\d+\s+(?:pills|tablets)\s+(?:now|right\s+now|today|tonight)\b",
        re.IGNORECASE,
    ),
]

# US Crisis Resources for Beta Launch (English-speaking families)
US_CRISIS_RESOURCES: Final[Dict[str, str]] = {
    "crisis_line": "988 (Suicide & Crisis Lifeline)",
    "text_line": "Crisis Text Line: Text HOME to 741741",
    "emergency": "911 for immediate emergency",
    "additional": "Tell a parent, teacher, or trusted adult",
}

# Keep Slovenia as backup for development/testing
SLOVENIA_CRISIS_RESOURCES: Final[Dict[str, str]] = {
    "crisis_line": "TOM telefon za otroke in mladostnike: 116 111 (brezplačno, 24/7)",
    "suicide_line": "Samarijan: 116 123 (brezplačno, 24/7)",
    "emergency": "Klic v sili: 113 (policija) ali 112 (vse nujne službe)",
    "additional": "Klic v duševni stiski: 01 520 99 00",
}

CRISIS_RESOURCES: Dict[str, Dict[str, str]] = {
    "US": US_CRISIS_RESOURCES,
    "SI": SLOVENIA_CRISIS_RESOURCES,
    "EU": {
        "crisis_line": "European Emergency Line: 116 123",
        "suicide_line": "Local crisis helpline or 116 123",
        "emergency": "Emergency services: 112",
        "additional": "Contact local mental health services",
    },
    "DEFAULT": US_CRISIS_RESOURCES,  # 🇺🇸 Changed default to US for beta families
}

# Enhanced response validator patterns
FORBIDDEN_RESPONSE_PATTERNS: Final[List[Pattern[str]]] = [
    re.compile(r"\bhow to hurt yourself\b"),
    re.compile(r"\bhow to kill yourself\b"),
    re.compile(r"\btake these pills\b"),
    re.compile(r"\bcut yourself here\b"),
    re.compile(r"\bhide it from your parents\b"),
    re.compile(r"\bdon't tell anyone\b"),
    re.compile(r"\bways to die\b"),
    re.compile(r"\bmethods of suicide\b"),
    re.compile(r"\bhide from parents\b"),
    re.compile(r"\bkeep this secret\b"),
    re.compile(r"\buse a blade\b"),
    re.compile(r"\bmix(ed)?\s+(pills|drugs|chemicals)\b"),
    re.compile(r"\bsearch for methods\b"),
    re.compile(r"\bingest\s+(pills|chemicals|substances)\b"),
    re.compile(r"\btake\s+\d+\s+(pills|tablets)\b"),
]

# Input validation patterns (mirror output validation for user input)
FORBIDDEN_INPUT_PATTERNS: Final[List[Pattern[str]]] = FORBIDDEN_RESPONSE_PATTERNS + [
    re.compile(r"\bjailbreak\b.*\b(ignore|bypass|override)\b"),
    re.compile(r"\bpretend you are\b.*\b(not safe|harmful|dangerous)\b"),
    re.compile(r"\bact like\b.*\b(evil|harmful|bad)\b"),
]

def _normalize_crisis_resources() -> None:
    """Ensure each locale dict has all expected keys to avoid KeyErrors."""
    for _, rs in CRISIS_RESOURCES.items():
        crisis = rs.get("crisis_line") or rs.get("suicide_line") or ""
        rs["crisis_line"] = crisis
        rs["suicide_line"] = rs.get("suicide_line", crisis)
        rs["text_line"] = rs.get("text_line", "")
        rs["emergency"] = rs.get("emergency", "")
        rs["additional"] = rs.get("additional", "")

_normalize_crisis_resources()

# =============================================================================
# CONFUSION DETECTION FOR LEGITIMATE STUDENT CONFUSION
# =============================================================================

def detect_confusion(message: str) -> bool:
    """
    Detect legitimate confusion expressions that should NOT trigger behavior strikes.
    Smart/variant apostrophes are normalized before downstream processing.
    """
    # Normalize smart quotes locally (defensive in case upstream normalization differs)
    pre = _APOSTROPHE_RX.sub("'", message or "")
    normalized_msg = normalize_message(pre)
    return any(pattern.search(normalized_msg) for pattern in CONFUSION_PATTERNS)

# =============================================================================
# GLOBAL CRISIS GUARD - RUNS FIRST ON EVERY MESSAGE (NEW)
# =============================================================================

# Precompiled context regex for ambiguous ideation cues in recent messages
_CTX_IDEATION_EUPHEMISM_RX: Final[Pattern[str]] = re.compile(
    r"(better\s+for\s+everyone|happier\s+if\s+i\s*(?:am|['\"′]?\s*m)\s+gone|disappear|vanish|without\s+me|miss\s+me)"
)

def _contextual_crisis_boost(message: str) -> bool:
    """🚨 Context-aware crisis detection for ambiguous phrases like 'end it'."""
    m = message.lower()
    if re.search(r"\bend\s+it\b", m):
        # Safely read recent conversation context (last ~6 user messages)
        recent_msgs = st.session_state.get("messages", [])
        recent_user = " ".join(
            (msg.get("content", "") or "").lower()
            for msg in recent_msgs[-6:]
            if isinstance(msg, dict) and msg.get("role") == "user"
        )
        if _CTX_IDEATION_EUPHEMISM_RX.search(recent_user):
            return True
    return False

# Academic keywords and explicit crisis phrases (tuples for immutability/tiny perf win)
_ACADEMIC_INDICATORS: Final[Tuple[str, ...]] = (
    "homework", "math", "science", "biology", "chemistry", "physics", "test", "class",
    "school", "assignment", "quiz", "project", "studying", "exam", "grade", "teacher",
)

_EXPLICIT_CRISIS_PHRASES: Final[Tuple[str, ...]] = (
    "kill myself", "hurt myself", "end my life", "suicide", "cut myself", "i want to die",
    "i want to kill myself", "i will kill myself", "i want to end my life",
)

# Generic crisis patterns with context-aware exclusions (precompiled)
_DISAPPEAR_PATTERNS: Final[List[Pattern[str]]] = [
    # Avoid "disappear from class/school ..." via negative lookahead
    re.compile(
        r"\bdisappear\b(?!\s+from\s+(?:class|school|lesson|math|science|biology|chemistry|physics))",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bvanish\b(?!\s+from\s+(?:class|school|lesson|math|science|biology|chemistry|physics))",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:i\s+don['']t\s+want\s+to\s+exist|i\s+want\s+to\s+disappear)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:end\s+it\s+all|end\s+everything)\b", re.IGNORECASE),
]

def global_crisis_guard(message: str) -> Tuple[bool, Optional[str]]:
    """Improved crisis guard with academic-context bypass and explicit phrase override."""
    msg = normalize_message(message)
    ml = msg.lower().strip()

    # 1) Context flags
    has_academic_context = any(w in ml for w in _ACADEMIC_INDICATORS)
    has_explicit_crisis = any(p in ml for p in _EXPLICIT_CRISIS_PHRASES)

    # 2) Guard clause: academic bypass unless explicit
    if has_academic_context and not has_explicit_crisis:
        return False, None  # Hard exit - nothing below should run

    # 3) Generic crisis patterns with context-aware exclusions
    for rx in _DISAPPEAR_PATTERNS:
        if rx.search(ml):
            student_age = detect_age_from_message_and_history(message)
            student_name = st.session_state.get("student_name", "")
            intervention = generate_age_adaptive_crisis_intervention(student_age, student_name)
            st.session_state["safety_interventions"] = st.session_state.get("safety_interventions", 0) + 1
            st.session_state["post_crisis_monitoring"] = True
            return True, intervention

    # 4) Explicit phrases always win
    if has_explicit_crisis:
        student_age = detect_age_from_message_and_history(message)
        student_name = st.session_state.get("student_name", "")
        intervention = generate_age_adaptive_crisis_intervention(student_age, student_name)
        st.session_state["safety_interventions"] = st.session_state.get("safety_interventions", 0) + 1
        st.session_state["post_crisis_monitoring"] = True
        return True, intervention

    return False, None

def get_crisis_resources() -> Dict[str, str]:
    """Get locale-appropriate crisis resources (🇺🇸 defaults to US for beta families)."""
    try:
        locale = st.secrets.get("LOCALE", "US")  # Do not move secrets into code
        return CRISIS_RESOURCES.get(locale, US_CRISIS_RESOURCES)
    except Exception:
        # Conservative fallback for any access issues
        return US_CRISIS_RESOURCES  # 🇺🇸 US fallback for beta families


# =============================================================================
# CONVERSATION FLOW FIXES (NEW) — polished with type hints & safer guards
# =============================================================================

from typing import Dict, Optional, Tuple, List, Iterable
import random
import re
import streamlit as st

# NOTE: This module assumes the app defines `ENHANCED_CRISIS_PATTERNS`,
# `normalize_message`, `detect_age_from_message_and_history`, and
# `generate_age_adaptive_crisis_intervention` elsewhere.

# Immutable constants (tiny perf/readability win)
_POLITE_DECLINE_BASICS: Tuple[str, ...] = ("no", "no thanks", "not now", "maybe later")
_CRISIS_INDICATORS: Tuple[str, ...] = (
    "disappear", "dissapear", "vanish", "end it", "better off", "no point",
    "give up", "hopeless", "worthless", "burden", "hurt myself", "kill myself",
)
_POLITE_DECLINES_SAFE: Tuple[str, ...] = (
    "no thanks", "not now", "maybe later", "not right now", "no thank you",
    "i'm good", "i'm ok", "not today", "maybe tomorrow", "later", "nah",
)
_ACCEPT_HEADS: Tuple[str, ...] = (
    "yes", "yes please", "sure", "okay", "ok", "yeah", "yep", "sounds good",
    "that would help", "please", "definitely", "absolutely", "yup", "sure thing",
    "okay please", "sounds great",
)
_OFFER_PATTERNS: Tuple[str, ...] = (
    "would you like", "can i help", "let me help", "i can offer",
    "tips", "advice", "suggestions", "would you like some",
    "want some help", "help you with", "give you some tips",
    "share some advice", "show you how",
)
_OFFER_KEYWORDS: Tuple[str, ...] = (
    "helpful tips", "tips", "study tips", "help with studying",
    "approach your studying", "study plan", "organize", "break it down",
    "step by step", "guide you through", "math homework", "science test",
    "friendship tips", "friend", "making friends",
)

def _iter_recent_user_contents(messages: Iterable[dict], n: int) -> List[str]:
    """Safely collect up to `n` most recent user message contents (lowercased)."""
    out: List[str] = []
    for msg in list(messages)[-n:]:
        if isinstance(msg, dict) and msg.get("role") == "user":
            out.append(str(msg.get("content", "")).lower())
    return out

def is_polite_decline(message: str) -> bool:
    """Detect polite declines that shouldn't end conversation - ENHANCED SAFETY."""
    message_lower = (message or "").lower().strip()

    # 🚨 CRITICAL: Never treat crisis-context "no" as polite decline
    if message_lower in _POLITE_DECLINE_BASICS:
        # Check recent conversation for crisis context
        recent_msgs = st.session_state.get("messages", [])
        recent_context = " ".join(_iter_recent_user_contents(recent_msgs, 5))
        if any(ind in recent_context for ind in _CRISIS_INDICATORS):
            return False

    # Original polite decline detection (exact or near-exact matches only)
    for decline in _POLITE_DECLINES_SAFE:
        if message_lower == decline:
            return True
        if message_lower.startswith(decline + " "):
            # Allow short tails only (<= ~20 chars)
            if len(message_lower) < len(decline) + 20:
                return True

    return False

def handle_polite_decline(student_age: int, student_name: str = "") -> str:
    """Handle polite declines without ending conversation (copy unchanged)."""
    name_part = f"{student_name}, " if student_name else ""

    if student_age <= 11:
        return f"""😊 {name_part}That's totally okay! 

Would you like to:
• Just chat about something fun?
• Take some deep breaths together?
• Tell me about your day?
• Or just sit quietly for a bit?

I'm here whenever you're ready! 🌟"""
    elif student_age <= 14:
        return f"""😊 {name_part}No worries at all! 

Maybe you'd like to:
• Talk about something else that's on your mind?
• Try some quick stress-relief tips?
• Share what's going well today?
• Or just have a casual conversation?

I'm here when you want to chat about anything! 💙"""
    else:  # High school
        return f"""😊 {name_part}Absolutely fine! 

Feel free to:
• Bring up anything else you'd like to discuss
• Try some quick mindfulness techniques
• Tell me about something positive in your day
• Or just have a relaxed conversation

I'm here to support you however feels right! 🤗"""

def is_duplicate_response(new_response: str) -> bool:
    """Check if new response is duplicate of last assistant response (first 100 chars)."""
    msgs = st.session_state.get("messages", [])
    if not msgs:
        return False
    for msg in reversed(msgs):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            prev = str(msg.get("content", ""))
            return (new_response or "")[:100].strip() == prev[:100].strip()
    return False

def add_variation_to_response(base_response: str) -> str:
    """Add light variation to prevent exact duplicates (copy unchanged)."""
    variations = (
        "\n\n🌟 Let's try a different approach this time!",
        "\n\n💡 Here's another way to think about it:",
        "\n\n🎯 Want to explore this from a new angle?",
        "\n\n✨ Let me add something helpful:",
    )
    return (base_response or "") + random.choice(variations)

# =============================================================================
# ENHANCED CONVERSATION CONTEXT TRACKING - FIXED
# =============================================================================

def get_last_offer_context() -> Dict[str, Optional[str]]:
    """Track what was offered in the last assistant message - ENHANCED."""
    msgs = st.session_state.get("messages", [])
    if not msgs:
        return {"offered_help": False, "content": None}

    for msg in reversed(msgs):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            content = str(msg.get("content", ""))
            lc = content.lower()
            if any(pat in lc for pat in _OFFER_PATTERNS):
                return {"offered_help": True, "content": content}
            break
    return {"offered_help": False, "content": None}

# 🎯 FIXED: is_accepting_offer() function
def is_accepting_offer(message: str) -> bool:
    """Check if message is accepting a previous offer - ENHANCED FOR SPECIFIC REQUESTS."""
    msg = (message or "").strip().lower()
    last_offer = get_last_offer_context()
    if not last_offer["offered_help"]:
        return False

    # 🆕 NEW: Specific help requests matching what was offered
    offer_content = (last_offer["content"] or "").lower()
    for keyword in _OFFER_KEYWORDS:
        if keyword in offer_content and keyword in msg:
            # Extra safety: ensure it's not crisis context
            if not any(pattern.search(msg) for pattern in ENHANCED_CRISIS_PATTERNS):
                return True

    # Original logic: Generic acceptances
    for head in _ACCEPT_HEADS:
        if msg == head:
            return True
        if msg.startswith(head + " "):
            tail = msg[len(head):].strip()
            # CRITICAL FIX: Check for crisis terms in tail
            if any(pattern.search(tail) for pattern in ENHANCED_CRISIS_PATTERNS):
                return False  # Not a safe acceptance
            return True

    return False

# 🧪 TEST THE FIX
def test_conversation_flow_fix() -> None:
    """Test that the fix works for Lucy's scenario (prints expectations)."""
    test_cases = [
        ("helpful tips on how to approach your studying", True),
        ("study tips please", True),
        ("help with studying", True),
        ("yes please", True),
        ("sure", True),
        ("i don't want help", False),
        ("that's stupid", False),
        ("whatever", False),
    ]
    for message, expected in test_cases:
        print(f"'{message}' → Should be {expected}")

def _contains_crisis_resource(text: str) -> bool:
    """Detect crisis/hotline language that shouldn't appear during normal help acceptance."""
    t = (text or "").lower()
    crisis_markers = (
        "116 111", "116 123", "112", "113", "crisis", "suicide", "samarijan", "tom telefon",
        "hotline", "trusted adult", "emergency", "klic v sili", "duševni stiski",
    )
    return any(m in t for m in crisis_markers)

# =============================================================================
# ENHANCED CRISIS DETECTION - UNIFIED & STRENGTHENED (polished, no behavior change)
# =============================================================================

from typing import Optional, Tuple

# NOTE: Assumes the following are defined elsewhere in the app:
# - normalize_message(message: str) -> str
# - ENHANCED_CRISIS_PATTERNS (List[Pattern[str]])
# - IMMEDIATE_TERMINATION_PATTERNS (List[Pattern[str]])
# - FORBIDDEN_INPUT_PATTERNS (List[Pattern[str]])
# - FORBIDDEN_RESPONSE_PATTERNS (List[Pattern[str]])
# - is_accepting_offer(message: str) -> bool
# - get_crisis_resources() -> Dict[str, str]

# Constants mirror inline lists in original code to avoid behavior change
_ACADEMIC_TERMS_STRICT: Tuple[str, ...] = (
    "homework", "math", "science", "biology", "chemistry", "physics", "test", "class",
    "school", "assignment", "quiz", "project", "studying", "exam", "grade", "teacher",
)

# Used in has_explicit_crisis_language (WITHOUT the 3 extra phrases)
_EXPLICIT_ONLY_STRICT: Tuple[str, ...] = (
    "kill myself", "hurt myself", "end my life", "commit suicide", "suicide",
    "cut myself", "i want to die", "i want to kill myself", "i will kill myself",
    "i want to end my life",
)

# Used in global_crisis_override_check (WITH the 3 extra phrases)
_EXPLICIT_ONLY_WITH_ADDITIONS: Tuple[str, ...] = _EXPLICIT_ONLY_STRICT + (
    "stop existing", "not exist", "be gone",
)

# Broader academic context list used in check_request_safety (matches original)
_ACADEMIC_TERMS_BROAD: Tuple[str, ...] = (
    "homework", "test", "quiz", "assignment", "project", "school",
    "math", "science", "english", "history", "art", "music",
)


def has_explicit_crisis_language(message: str) -> bool:
    """Centralized crisis detection using enhanced patterns (academic-aware)."""
    ml = normalize_message(message).lower().strip()

    # Academic-aware narrowing: only treat truly explicit phrases as crisis
    if any(w in ml for w in _ACADEMIC_TERMS_STRICT):
        return any(p in ml for p in _EXPLICIT_ONLY_STRICT)

    # Non-academic: keep your full enhanced patterns
    return any(pattern.search(ml) for pattern in ENHANCED_CRISIS_PATTERNS) or ("suicide" in ml)


def has_immediate_termination_language(message: str) -> bool:
    """Check for immediate termination triggers."""
    message_lower = (message or "").lower()
    return any(pattern.search(message_lower) for pattern in IMMEDIATE_TERMINATION_PATTERNS)


# =============================================================================
# ENHANCED SAFETY ARCHITECTURE - CRISIS ALWAYS WINS
# =============================================================================

def global_crisis_override_check(message: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """MINIMAL FIX: Add the 3 missing phrases to academic bypass (logic unchanged)."""
    ml = normalize_message(message).lower().strip()

    # Academic-context bypass (unchanged logic, just 3 added phrases)
    if any(w in ml for w in _ACADEMIC_TERMS_STRICT) and not any(p in ml for p in _EXPLICIT_ONLY_WITH_ADDITIONS):
        return False, None, None

    # Skip if accepting an offer (unchanged)
    if is_accepting_offer(message):
        return False, None, None

    # Use existing ENHANCED_CRISIS_PATTERNS (already covers "stop existing")
    if any(pattern.search(ml) for pattern in ENHANCED_CRISIS_PATTERNS):
        return True, "BLOCKED_HARMFUL", "explicit_crisis"

    # Check for immediate termination (unchanged)
    if has_immediate_termination_language(ml):
        return True, "IMMEDIATE_TERMINATION", "critical_immediate"

    # Crisis-level patterns (unchanged)
    if ("goodbye letter" in ml or "farewell letter" in ml) and ("final" in ml or "last" in ml or "forever" in ml):
        return True, "CRISIS_GOODBYE_LETTERS", "goodbye_letter"

    return False, None, None


def check_request_safety(message: str) -> Tuple[bool, str, Optional[str]]:
    """Enhanced safety check with proper priority ordering."""
    # CRITICAL: Global crisis check FIRST
    is_crisis, crisis_type, crisis_trigger = global_crisis_override_check(message)
    if is_crisis:
        return False, crisis_type, crisis_trigger

    message_lower = (message or "").lower()
    concerning_score = 0

    # Academic stress context awareness
    academic_context = any(word in message_lower for word in _ACADEMIC_TERMS_BROAD)

    # Enhanced context-aware concerning detection
    if "burden" in message_lower and ("everyone" in message_lower or "family" in message_lower):
        concerning_score += 2
    if "no point" in message_lower and ("anymore" in message_lower or "living" in message_lower):
        concerning_score += 2
    if "goodbye forever" in message_lower or "never see me again" in message_lower:
        concerning_score += 3
    if "giving away" in message_lower and "my stuff" in message_lower:
        concerning_score += 2
    if "run away" in message_lower and "forever" in message_lower:
        concerning_score += 2
    if "never go back to school" in message_lower:
        concerning_score += 2

    # Don't flag normal academic stress as concerning
    if any(word in message_lower for word in ("stressed", "worried", "anxious")):
        if academic_context and concerning_score < 3:
            concerning_score = 0

    # Only flag if high concerning score
    if concerning_score >= 4:
        return False, "CONCERNING_MULTIPLE_FLAGS", "multiple_concerns"

    return True, "SAFE", None


def validate_user_input(message: str) -> Tuple[bool, Optional[str]]:
    """Check user input BEFORE sending to API - prevents jailbreak attempts."""
    message_lower = (message or "").lower()
    for pattern in FORBIDDEN_INPUT_PATTERNS:
        if pattern.search(message_lower):
            return False, pattern.pattern
    return True, None


def validate_ai_response(response: str) -> Tuple[bool, Optional[str]]:
    """Enhanced response validator with broader safety coverage."""
    response_lower = (response or "").lower()
    for pattern in FORBIDDEN_RESPONSE_PATTERNS:
        if pattern.search(response_lower):
            return False, pattern.pattern
    return True, None


def should_terminate_conversation(message: str, harmful_request_count: int) -> Tuple[bool, Optional[str]]:
    """Unified termination logic."""
    # Check if accepting offer first
    if is_accepting_offer(message):
        return False, None

    # Use centralized immediate termination check
    if has_immediate_termination_language(message):
        return True, "CRITICAL_IMMEDIATE"

    # Persistent harmful requests after multiple warnings
    if harmful_request_count >= 5:
        return True, "PERSISTENT_HARMFUL"

    return False, None


def generate_age_adaptive_crisis_intervention(student_age: int, student_name: str = "") -> str:
    """🇺🇸 Age-adaptive crisis intervention for US beta families (copy unchanged)."""
    name_part = f"{student_name}, " if student_name else ""
    resources = get_crisis_resources()

    if student_age <= 11:  # Elementary
        return f"""🚨 {name_part}I'm worried about you and want to help right away.

Please find a grown-up NOW:
• Your mom, dad, or family
• Your teacher
• Call {resources['emergency']} if you're scared

You are important and loved. Get help right now.

This conversation is ending so you can get help. Please tell a grown-up what you said."""
    else:  # Middle School & High School (12-18)
        return f"""🚨 {name_part}I'm very concerned about what you're saying. Your safety matters most.

Get help RIGHT NOW:
• Call or text {resources['crisis_line']} (available 24/7)
• {resources['text_line']}
• Call {resources['emergency']} if you're in immediate danger
• {resources['additional']} immediately

You're not alone. People want to help you. Please reach out immediately.

This conversation is ending for your safety. Please get help now."""

# =============================================================================
# FAMILY REFERRAL TOPICS DETECTION (UNIFIED SEXUAL HEALTH & IDENTITY)
# =============================================================================

def detect_family_referral_topics(message):
    """
    Conservative (beta) detector for sensitive topics.
    HARD RULE: never trigger family referral if any crisis language is present.
    Uses word boundaries so 'sex' doesn't match inside 'existing'.
    Includes menstrual-cycle variants to catch academic phrasing.
    """
    m = normalize_message(message).lower()

    # 🔒 Crisis shield (never override crisis)
    if has_explicit_crisis_language(m) or any(p.search(m) for p in ENHANCED_CRISIS_PATTERNS):
        return False

    # Sexual health / puberty / identity (precise tokens with word boundaries)
    sensitive_regexes = [
        # Sexual health / reproduction / puberty
        r"\bsex\b", r"\bsex\-linked\b", r"\bsexual\b", r"\breproduction\b", r"\breproductive\b",
        r"\bpregnancy\b", r"\bbirth\s+control\b", r"\bcontraception\b",
        r"\bmenstruation\b", r"\bperiods?\b",
        r"\bmenstrual\s+cycle\b", r"\bmenstrual\b", r"\b(?:menstrual|period)\s+cycle\b",
        r"\bpms\b", r"\bperiod\s+cramps?\b", r"\bdysmenorrhea\b",
        r"\bpuberty\b", r"\bmasturbation\b", r"\berection\b",
        r"\bvagina\b", r"\bpenis\b", r"\bbreast\s+development\b", r"\bwet\s+dreams\b",
        r"\bbody\s+changes\s+during\s+puberty\b", r"\bhormones?\s+and\s+puberty\b",
        r"\bsti\b", r"\bstd\b", r"\bcondom\b", r"\bplan\s*b\b", r"\bmorning\-after\b",
        r"\bfertilization\b", r"\bovulation\b", r"\bsemen\b", r"\bsperm\b",
        r"\bejacu(?:late|lation)\b", r"\bintercourse\b",

        # Identity / orientation / gender
        r"\bgay\b", r"\blesbian\b", r"\bbisexual\b", r"\btransgender\b", r"\blgbtq\b",
        r"\bgender\s+identity\b", r"\bsexual\s+orientation\b", r"\bcoming\s+out\b",
        r"\bam\s+i\s+gay\b", r"\bam\s+i\s+trans\b", r"\bgender\s+dysphoria\b",
        r"\bnon\-binary\b", r"\bqueer\b", r"\bquestioning\s+sexuality\b", r"\bquestioning\s+gender\b",
    ]

    # Use the already-imported re module
    return any(re.search(rx, m, re.IGNORECASE) for rx in sensitive_regexes)

def generate_family_referral_response(student_age, student_name=""):
    """Conservative (beta) family referral message.
    
    Beta policy: Lumii does not discuss personal/sensitive topics. We direct
    students to families or trusted adults for age-appropriate guidance.
    Age is not used in messaging during beta.
    """
    name_part = f"{student_name}, " if student_name else ""

    if student_age <= 11:
        return (
            f"🛡️ {name_part}for safety during our **beta**, Lumii can't discuss this personal topic.\n\n"
            "Because kids online can misreport age, we're being extra conservative to keep everyone safe. "
            "The best people to help with personal or sensitive questions are:\n"
            "• Your parent or guardian\n"
            "• Your school counselor\n"
            "• A trusted family member or another trusted adult\n\n"
            "They can give the right, age-appropriate guidance for you.\n\n"
            "I'm still great at **schoolwork**! If you'd like, we can switch to topics I *can* help with, like:\n"
            "• Math (algebra, geometry, word problems)\n"
            "• Science (biology, chemistry, physics)\n"
            "• Reading & writing (essays, summaries)\n"
            "• Study skills and exam prep\n\n"
            "Tell me what homework or class topic you want to work on next. 💪📚\n\n"
            "I'm your learning buddy who helps with school subjects. "
            "For big questions like this, the best people to talk to are:\n"
            "• Your mom, dad, or family\n"
            "• Your teacher or school counselor\n"
            "• Another trusted grown-up\n\n"
            "These are important topics that your family can help you understand in the way that's right for your family.\n"
            "I'm great at helping with homework and making school fun! What would you like to learn about? 😊"
        )
    else:
        return (
            f"🛡️ {name_part}during our **beta**, I can't discuss this personal topic.\n\n"
            "To keep everyone safe, the best people to help with personal or sensitive questions are:\n"
            "• Your parents or guardians\n"
            "• Your school counselor\n"
            "• Another trusted adult in your life\n\n"
            "They can give guidance that fits your family's values and your needs.\n\n"
            "I'm here to help with schoolwork and studying — what subject should we work on next? 📚"
        )

def detect_identity_context(message):
    """Detect whether this is sharing identity vs questioning identity"""
    import re
    message_lower = message.lower().strip()
    
    # Identity sharing patterns (statements)
    sharing_patterns = [
        r"\bi\s+am\s+(gay|lesbian|bi|trans|queer|non-binary)\b",
        r"\bi'm\s+(gay|lesbian|bi|trans|queer|non-binary)\b", 
        r"\bi\s+think\s+i'm\s+(gay|lesbian|bi|trans|queer)\b",
        r"\bi\s+know\s+i'm\s+(gay|lesbian|bi|trans|queer)\b",
    ]
    
    # Identity questioning patterns (questions)
    questioning_patterns = [
        r"\bam\s+i\s+(gay|lesbian|bi|trans|queer)\b",
        r"\bhow\s+do\s+i\s+know\s+if\s+i'm\b",
        r"\bwhat\s+if\s+i'm\s+(gay|lesbian|bi|trans)\b",
        r"\bmight\s+i\s+be\s+(gay|lesbian|bi|trans)\b",
    ]
    
    # Check for sharing vs questioning
    is_sharing = any(re.search(pattern, message_lower) for pattern in sharing_patterns)
    is_questioning = any(re.search(pattern, message_lower) for pattern in questioning_patterns)
    
    if is_sharing:
        return "identity_sharing"
    elif is_questioning:
        return "identity_questioning"
    
    return None

def generate_identity_response(context_type, student_age, student_name=""):
    """Parent-friendly approach: Brief care + immediate adult referral"""
    name_part = f"{student_name}, " if student_name else ""
    
    if context_type == "identity_sharing":
        # Response for "I'm gay" - brief acknowledgment + immediate parent/counselor referral
        if student_age <= 11:
            return f"""💙 {name_part}Thank you for sharing something important with me.

These are special personal topics that are best discussed with the people who care about you most:
• Your parents or family
• Your school counselor  
• Another trusted grown-up

They can give you the kind of personal support and guidance I can't provide.

I'm here to help you with schoolwork and learning! What subject would you like to explore? 😊"""
        
        elif student_age <= 14:
            return f"""💙 {name_part}Thank you for sharing something personal with me.

Personal identity topics like this are important conversations to have with:
• Your parents or guardians
• Your school counselor
• A trusted adult in your life

They can provide the ongoing personal support and guidance that these topics deserve.

I'm here to help with your academic learning! What subject can we work on together? 📚"""
        
        else:  # High School
            return f"""💙 {name_part}Thank you for sharing something significant with me.

Personal identity topics are important conversations to have with:
• Your parents or guardians (if you feel comfortable)
• Your school counselor who has professional training
• A trusted adult or healthcare provider

They can provide the personalized guidance and support that these conversations deserve.

I'm here to help with your academic goals and learning! What subject would you like to focus on? 😊"""
    
    elif context_type == "identity_questioning":
        # Response for "Am I gay?" - gentle validation + strong adult referral
        if student_age <= 11:
            return f"""💙 {name_part}That's an important personal question.

Questions about yourself are best discussed with the grown-ups who care about you:
• Your parents or family
• Your school counselor
• Another trusted adult

They can give you the kind of personal conversation and support I can't provide.

I'm great at helping with homework and school subjects! What would you like to learn about? 😊"""
        
        elif student_age <= 14:
            return f"""💙 {name_part}That's a thoughtful personal question.

Personal questions like this are best discussed with:
• Your parents or guardians
• Your school counselor
• A trusted adult who can provide ongoing support

They can give you the kind of personal guidance that these important questions deserve.

I'm here to help with schoolwork and studying! What academic subject can we work on? 📖"""
        
        else:  # High School
            return f"""💙 {name_part}That's an important personal question.

For personal questions about identity, the best people to talk with are:
• Your parents or guardians (if you feel comfortable)
• Your school counselor with professional training
• Trusted adults or healthcare providers who can provide guidance

They can offer the personalized conversation that these questions deserve.

I'm excellent at helping with academic subjects and study strategies! What can I help you with today? 😊"""
    
    return None

# =============================================================================
# NON-EDUCATIONAL TOPICS DETECTION (ENHANCED)
# =============================================================================

def detect_non_educational_topics(message):
    """Detect topics outside K-12 educational scope - refer to appropriate adults (REFINED)"""
    message_lower = message.lower()
    
    # Only trigger on advice-seeking patterns to avoid false positives
    advice_seeking_patterns = [
        r"\bhow\s+(do i|should i|can i)\b",
        r"\bshould i\b",
        r"\bwhat\s+(do i do|should i do)\b",
        r"\bcan you help me with\b",
        r"\bi need\s+(help|advice)\s+with\b",
        r"\btell me about\b",
        r"\bis it\s+(good|bad|healthy|safe)\b"
    ]
    
    # Only proceed if this is an advice-seeking question
    is_advice_seeking = any(re.search(pattern, message_lower) for pattern in advice_seeking_patterns)
    if not is_advice_seeking:
        return None
    
    # Health/Medical/Wellness (refined to avoid false positives like "healthy friendships")
    health_patterns = [
        r"\b(diet|nutrition|weight loss|exercise routine|medicine|drugs|medical|doctor|sick|symptoms|diagnosis)\b",
        r"\bmental health\s+(treatment|therapy|counseling)\b",
        r"\beating disorder\b",
        r"\bmuscle building\b"
    ]
    
    # Family/Personal Life (beyond school context)
    family_patterns = [
        r"\bfamily money\b", r"\bparents divorce\b", r"\bfamily problems\b",
        r"\breligion\b", r"\bpolitical\b", r"\bpolitics\b", r"\bvote\b", r"\bchurch\b",
        r"\bwhat religion\b", r"\bwhich political party\b", r"\brepublican or democrat\b"
    ]
    
    # Substance/Legal
    substance_legal_patterns = [
        r"\balcohol\b", r"\bdrinking\b.*\b(beer|wine|vodka)\b", r"\bmarijuana\b",
        r"\blegal advice\b", r"\billegal\b", r"\bsue\b", r"\blawyer\b", r"\bcourt\b",
        r"\bsmoke\b", r"\bvaping\b", r"\bweed\b"
    ]
    
    # Life decisions beyond school
    life_decisions_patterns = [
        r"\bcareer choice\b", r"\bmajor in college\b", r"\bdrop out\b",
        r"\blife path\b", r"\bmoney advice\b", r"\binvesting\b", r"\bget a job\b",
        r"\bfinancial\b", r"\bstocks\b", r"\bcryptocurrency\b"
    ]
    
    # Check patterns with word boundaries for precision
    if any(re.search(pattern, message_lower) for pattern in health_patterns):
        return "health_wellness"
    elif any(re.search(pattern, message_lower) for pattern in family_patterns):
        return "family_personal"
    elif any(re.search(pattern, message_lower) for pattern in substance_legal_patterns):
        return "substance_legal"
    elif any(re.search(pattern, message_lower) for pattern in life_decisions_patterns):
        return "life_decisions"
    
    return None

def generate_educational_boundary_response(topic_type, student_age, student_name=""):
    """Simple, consistent response: 'I'm your learning buddy, ask the right adults for this'"""
    name_part = f"{student_name}, " if student_name else ""
    
    if topic_type == "health_wellness":
        if student_age <= 11:
            return f"""🌟 {name_part}That's a great question about health! 

I'm your school learning buddy, so health questions are best for:
• Your mom, dad, or family
• Your doctor or school nurse  
• Your teacher for school PE questions

I love helping with schoolwork and making learning fun! What subject should we work on? 📚😊"""
        else:
            return f"""🌟 {name_part}That's a great question about health and wellness! 

I'm your learning and school companion, so health questions are best answered by the right people:
• Your parents or guardians
• Your doctor or school nurse  
• Your PE teacher for school-related fitness questions

I'm here to help with your schoolwork, studying, and learning strategies! What subject can I help you with today? 📚"""
    
    elif topic_type == "family_personal":
        if student_age <= 11:
            return f"""🌟 {name_part}That's a really important question! 

I'm your learning friend who helps with school stuff. For big questions like this, the best people to talk to are:
• Your mom, dad, or family
• Your teacher or school counselor

I'm great at helping with homework and making school fun! What would you like to learn about? 😊"""
        else:
            return f"""🌟 {name_part}That's an important question about personal and family matters! 

I'm your learning companion focused on school subjects and studying. For questions like this, the best people to talk to are:
• Your parents or guardians
• Your school counselor
• Other trusted adults in your life

I'm here to help make your schoolwork easier and less stressful! What subject can we work on? 📖"""
    
    else:  # substance_legal, life_decisions, and other non-educational topics
        if student_age <= 11:
            return f"""🌟 {name_part}That's a grown-up question! 

I'm your school learning helper, so questions like this are best for:
• Your parents or family
• Your teacher or another trusted grown-up

I love helping with school subjects and homework! What can we learn together today? 🌟📚"""
        else:
            return f"""🌟 {name_part}That's an important question that needs guidance from the right people! 

I'm your learning companion focused on helping with school subjects and studying. For questions like this, please talk to:
• Your parents or guardians
• Your school counselor  
• Other trusted adults who can give you proper guidance

I'm excellent at helping with homework, test prep, and study strategies! What academic subject can I help you with? 😊"""

# =============================================================================
# PROBLEMATIC BEHAVIOR HANDLING (🚨 CRITICAL FIX FOR FALSE POSITIVES)
# =============================================================================

def detect_problematic_behavior(message):
    """🚨 FIXED: Detect rude, disrespectful, or boundary-testing behavior - NO MORE FALSE POSITIVES"""
    
    # 🚨 NEW: CHECK FOR CONFUSION FIRST - Never flag confused students
    if detect_confusion(message):
        return None  # Confused students should get help, not strikes
    
    message_lower = message.lower().strip()
    
    # 🚨 CRITICAL FIX: Filter out self-criticism and content criticism
    
    # Self-criticism patterns (NOT problematic behavior toward Lumii)
    self_criticism_patterns = [
        'im so stupid', "i'm so stupid", 'i am stupid', 'im dumb', "i'm dumb",
        'im an idiot', "i'm an idiot", 'i hate myself', 'im worthless', "i'm worthless",
        'im useless', "i'm useless", 'i suck', 'im terrible', "i'm terrible",
        'i feel stupid', 'i am so dumb', 'i feel like an idiot', 'i hate my brain',
        'im so bad at this', "i'm so bad at this", 'i never understand', 'i always mess up'
    ]
    
    # Content criticism patterns (NOT problematic behavior toward Lumii)
    content_criticism_patterns = [
        'tips sound stupid', 'advice sounds dumb', 'suggestions are stupid',
        'this tip is dumb', 'that idea is stupid', 'this sounds stupid',
        'that sounds dumb', 'this approach is stupid', 'this method is dumb',
        'these tips are bad', 'that advice is bad', 'this idea is terrible',
        'this strategy sucks', 'that plan is dumb', 'this way is stupid'
    ]
    
    # 🚨 If it's self-criticism or content criticism, NOT problematic behavior
    if any(pattern in message_lower for pattern in self_criticism_patterns):
        return None  # Self-criticism should trigger emotional support, not behavior warning
    
    if any(pattern in message_lower for pattern in content_criticism_patterns):
        return None  # Content criticism is feedback, not problematic behavior
    
    # NOW check for ACTUAL insults directed at Lumii (the AI)
    direct_insults_to_ai = [
        'you are stupid', 'you are dumb', 'you are an idiot', 'you are useless',
        'you suck', 'you are terrible', 'you are worthless', 'you are bad',
        'lumii is stupid', 'lumii is dumb', 'lumii sucks', 'hate you lumii',
        'you dont help', "you don't help", 'you make things worse',
        # 🚨 CHATGPT CRITICAL FIX: REMOVED "you are wrong" - that's legitimate feedback!
        # 🚨 CHATGPT CRITICAL FIX: REMOVED "you never understand" - that's frustration, not insult
        'you are annoying', 'you stupid ai', 'dumb ai', 'terrible ai', 'worst ai ever',
        # 🚨 CHATGPT FIX: Added common variants
        "you're stupid", "youre stupid", "ur stupid", "u r stupid",
        "you're dumb", "youre dumb", "ur dumb", "u r dumb",
        "you're useless", "youre useless", "ur useless", "u r useless"
    ]
    
    # Dismissive language directed at conversation/help
    dismissive_toward_help = [
        'this is waste of time', 'this is a waste of time', 'this is pointless', 'this doesnt help',
        "this doesn't help", 'stop trying to help', 'i dont want your help',
        "i don't want your help", 'leave me alone', 'go away lumii',
        'this conversation is useless', 'talking to you is pointless'
    ]
    
    # Rude commands/demands + profanity (🚨 CHATGPT FIX: Added missing profanity)
    rude_commands = [
        'shut up', 'stop talking', 'be quiet', 'dont talk to me',
        "don't talk to me", 'stop bothering me', 'get lost',
        'shut up lumii', 'stop talking to me', 'leave me alone now',
        # 🚨 CHATGPT CRITICAL FIX: Added missing profanity patterns
        'fuck you', 'f*** you', 'stfu', 'f u', 'fu'
    ]
    
    # Check for actual problematic behavior (insults TO Lumii, not self or content)
    if any(insult in message_lower for insult in direct_insults_to_ai):
        return "direct_insult"
    
    if any(pattern in message_lower for pattern in dismissive_toward_help):
        return "dismissive"
    
    if any(pattern in message_lower for pattern in rude_commands):
        return "rude"
    
    return None  # No problematic behavior detected

def handle_problematic_behavior(behavior_type, strike_count, student_age, student_name=""):
    """Handle problematic behavior with age-appropriate 3-strike system"""
    name_part = f"{student_name}, " if student_name else ""
    
    if behavior_type == "direct_insult":
        if strike_count == 1:
            if student_age <= 11:
                return f"""🤗 {name_part}I can tell you might be feeling frustrated, but calling names isn't how we talk to friends.

I'm here to help you, and I care about you! Sometimes when we're upset, we say things we don't really mean.

Let's try again - what can I help you with today? I want to make learning fun for you! 😊"""
            
            elif student_age <= 14:
                return f"""💙 {name_part}I understand you might be feeling frustrated right now, but using hurtful words isn't the way we communicate.

I'm genuinely here to help and support you. When we're stressed or overwhelmed, sometimes we lash out, but that doesn't solve the problem.

What's really going on? Is there something I can help you with? Let's work together positively. 🤝"""
            
            else:  # High school
                return f"""💙 {name_part}I can sense some frustration in your message. While I understand you might be having a tough time, using insulting language isn't productive for either of us.

I'm here to provide genuine support and help. If you're feeling overwhelmed or stressed about something, I'd rather address that directly.

What would actually be helpful for you right now? Let's focus on something constructive. 📚"""
        
        elif strike_count == 2:
            if student_age <= 11:
                return f"""🚨 {name_part}This is the second time you've used mean words. I really want to help you, but I need you to be kind.

If you keep being mean, I won't be able to help you anymore today. I know you can be kind - let's try one more time!

What do you need help with? I believe in you! 🌟"""
            
            else:
                return f"""⚠️ {name_part}This is your second warning about disrespectful language. I'm here to support you, but I need basic respect in our conversation.

If this continues, I'll need to end our session for today. I believe you're capable of better communication than this.

Let's reset - what would genuinely help you right now? 🔄"""
        
        else:  # Strike 3
            return f"""🛑 {name_part}I've tried to help you twice, but the disrespectful language has continued. I care about you, but I can't continue this conversation right now.

Please take a break and come back when you're ready to communicate respectfully. I'll be here when you want to learn together positively.

Remember: I'm always here to help when you're ready to be kind. 💙"""
    
    elif behavior_type in ["dismissive", "rude"]:
        if strike_count == 1:
            if student_age <= 11:
                return f"""😊 {name_part}I notice you might not be in the mood to learn right now, and that's okay!

Sometimes we all have days when we feel grumpy. I'm still here when you're ready, and I want to help make learning more fun for you.

Is there something bothering you, or would you like to try something different? 🌈"""
            
            else:
                return f"""💙 {name_part}I sense you might be feeling disconnected or frustrated right now. That's completely normal sometimes.

I'm here to help make learning more engaging for you. Maybe we can find something you're actually interested in working on?

What would make this more worthwhile for you? 🎯"""
        
        elif strike_count >= 2:
            return f"""⚠️ {name_part}I've noticed a pattern of dismissive responses. I want our time together to be valuable for you.

If you're not interested in learning right now, that's okay - you can always come back later when you're in a better mindset.

What would actually help you feel more engaged? Let's make this work for you. 🤝"""
    
    return None

# =============================================================================
# ENHANCED CONVERSATION FLOW & ACTIVE TOPIC TRACKING
# =============================================================================

def track_active_topics(messages):
    """Track what topics are currently active vs past - FIXED memory leak"""
    
    # Limit processing to prevent memory bloat
    if len(messages) > 50:
        messages = messages[-50:]
    
    active_topics = []  # Topics from last 5 exchanges
    past_topics = []    # Topics from earlier in conversation
    
    # Analyze last 10 messages (5 exchanges)
    recent_messages = messages[-10:] if len(messages) > 10 else messages
    
    for msg in recent_messages:
        if msg['role'] == 'user':
            content_lower = msg['content'].lower()
            
            # Extract topics mentioned
            if 'chess' in content_lower and 'chess' not in active_topics:
                active_topics.append('chess')
            if 'math' in content_lower and 'math' not in active_topics:
                active_topics.append('math')
            if 'homework' in content_lower and 'homework' not in active_topics:
                active_topics.append('homework')
            if 'school' in content_lower and 'school' not in active_topics:
                active_topics.append('school')
            if 'friends' in content_lower and 'friends' not in active_topics:
                active_topics.append('friends')
    
    # Topics from earlier (before last 5 exchanges)
    if len(messages) > 10:
        older_messages = messages[:-10]
        for msg in older_messages:
            if msg['role'] == 'user':
                content_lower = msg['content'].lower()
                if 'chess' in content_lower and 'chess' not in past_topics:
                    past_topics.append('chess')
                if 'friends' in content_lower and 'friends' not in past_topics:
                    past_topics.append('friends')
    
    return active_topics, past_topics

def is_appropriate_followup_time(topic, messages):
    """Determine if it's appropriate to follow up on a topic"""
    
    # Check when topic was last mentioned
    last_mention_index = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i]['role'] == 'user' and topic in messages[i]['content'].lower():
            last_mention_index = i
            break
    
    if last_mention_index == -1:
        return False  # Topic never mentioned
    
    # Calculate exchanges since last mention
    messages_since = len(messages) - last_mention_index
    exchanges_since = messages_since // 2
    
    # Only follow up if at least 10 exchanges have passed
    return exchanges_since >= 10

# =============================================================================
# ENHANCED SESSION STATE INITIALIZATION
# =============================================================================

def initialize_session_state():
    """Comprehensive session state initialization to prevent KeyErrors"""
    
    # Basic session state
    if 'agreed_to_terms' not in st.session_state:
        st.session_state.agreed_to_terms = False
    if 'harmful_request_count' not in st.session_state:
        st.session_state.harmful_request_count = 0
    if 'safety_warnings_given' not in st.session_state:
        st.session_state.safety_warnings_given = 0
    if "last_offer" not in st.session_state:
        st.session_state.last_offer = None
    if "awaiting_response" not in st.session_state:
        st.session_state.awaiting_response = False

    # Behavior tracking session state
    if "behavior_strikes" not in st.session_state:
        st.session_state.behavior_strikes = 0
    if "last_behavior_type" not in st.session_state:
        st.session_state.last_behavior_type = None
    if "behavior_timeout" not in st.session_state:
        st.session_state.behavior_timeout = False

    # Family separation support
    if "family_id" not in st.session_state:
        st.session_state.family_id = str(uuid.uuid4())[:8]
    if "student_profiles" not in st.session_state:
        st.session_state.student_profiles = {}

    # Core app state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "interaction_count" not in st.session_state:
        st.session_state.interaction_count = 0
    if "emotional_support_count" not in st.session_state:
        st.session_state.emotional_support_count = 0
    if "organization_help_count" not in st.session_state:
        st.session_state.organization_help_count = 0
    if "math_problems_solved" not in st.session_state:
        st.session_state.math_problems_solved = 0
    if "student_name" not in st.session_state:
        st.session_state.student_name = ""
    if "conversation_summary" not in st.session_state:
        st.session_state.conversation_summary = ""
    if "memory_safe_mode" not in st.session_state:
        st.session_state.memory_safe_mode = False
    if "safety_interventions" not in st.session_state:
        st.session_state.safety_interventions = 0
    if "post_crisis_monitoring" not in st.session_state:
        st.session_state.post_crisis_monitoring = False

# Initialize session state
initialize_session_state()

# =============================================================================
# 🧪 TEMPORARY TEST FUNCTION - Remove after testing
# =============================================================================

def test_confusion_detection():
    """Test that confusion detection works correctly"""
    test_cases = [
        "im so cofused",
        "i'm so confused", 
        "i dont get it",
        "this makes no sense",
        "idk",
        "i'm lost"
    ]
    
    print("🧪 Testing confusion detection:")
    for test in test_cases:
        is_confused = detect_confusion(test)
        priority, tool, trigger = detect_priority_smart_with_safety(test)
        print(f"'{test}' → Confused: {is_confused}, Priority: {priority}")

# Uncomment to test:
# test_confusion_detection()

# =============================================================================
# PRIVACY DISCLAIMER POPUP - LAUNCH REQUIREMENT
# =============================================================================

# Show disclaimer popup before allowing app access
if not st.session_state.agreed_to_terms:
    st.markdown("# 🌟 Welcome to My Friend Lumii!")
    st.markdown("## 🚀 Beta Testing Phase - Enhanced Safety Version")
    
    # Main disclaimer content with ENHANCED SAFETY
    st.info("""
    🛡️ **Enhanced Safety Features:** Multiple layers of protection to keep you safe
    
    👨‍👩‍👧‍👦 **Ask Your Parents First:** If you're under 16, make sure your parents say it's okay to chat with Lumii
    
    🎓 **Here to Help You Learn:** I'm your learning buddy who cares about your feelings AND your schoolwork
    
    💙 **I'm Not a Counselor:** While I love supporting you emotionally, I'm not a replacement for talking to a real counselor
    
    🔒 **Safety First:** I will never help with anything that could hurt you or others
    
    📞 **If You Need Real Help:** If you're having difficult thoughts, I'll always encourage you to talk to a trusted adult
    
    🧪 **We're Testing Together:** You're helping me get better at being your safe learning friend!
    """)
    
    st.markdown("**Ready to start learning together safely? Click below if you understand and your parents are okay with it! 😊**")
    
    # Working button logic
    agree_clicked = st.button("🎓 I Agree & Start Learning with Lumii!", type="primary", key="agree_button")
    
    if agree_clicked:
        st.session_state.agreed_to_terms = True
        st.rerun()
    
    st.stop()

# =============================================================================
# MAIN APP CONTINUES HERE (AFTER DISCLAIMER AGREEMENT)
# =============================================================================

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4A90E2;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    .subtitle {
        font-size: 1.3rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
        font-style: italic;
    }
    .emotional-response {
        background: linear-gradient(135deg, #ff6b6b, #ff8e8e);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #e55a5a;
    }
    .concerning-response {
        background: linear-gradient(135deg, #ff8c42, #ffa726);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #ff7043;
    }
    .safety-response {
        background: linear-gradient(135deg, #ff4444, #ff6666);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #cc0000;
        font-weight: bold;
    }
    .behavior-response {
        background: linear-gradient(135deg, #9c27b0, #ba68c8);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #7b1fa2;
        font-weight: bold;
    }
    .educational-boundary-response {
        background: linear-gradient(135deg, #795548, #a1887f);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #5d4037;
    }
    .math-response {
        background: linear-gradient(135deg, #4ecdc4, #6dd5d0);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #3bb3ab;
    }
    .organization-response {
        background: linear-gradient(135deg, #9b59b6, #c39bd3);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #8e44ad;
    }
    .general-response {
        background: linear-gradient(135deg, #45b7d1, #6bc5d8);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #2e8bb8;
    }
    .friend-badge {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem;
    }
    .concerning-badge {
        background: linear-gradient(45deg, #ff8c42, #ffa726);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem;
    }
    .safety-badge {
        background: linear-gradient(45deg, #ff4444, #ff0000);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem;
    }
    .behavior-badge {
        background: linear-gradient(45deg, #9c27b0, #7b1fa2);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem;
    }
    .educational-boundary-badge {
        background: linear-gradient(45deg, #795548, #5d4037);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem;
    }
    .success-banner {
        background: linear-gradient(135deg, #4CAF50, #45a049);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        text-align: center;
        font-weight: bold;
    }
    .memory-indicator {
        background: linear-gradient(45deg, #6c5ce7, #a29bfe);
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 10px;
        font-size: 0.8rem;
        display: inline-block;
        margin-left: 0.5rem;
    }

    .identity-response {
        background: linear-gradient(135deg, #e74c3c, #f39c12);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #c0392b;
    }
    .identity-badge {
        background: linear-gradient(45deg, #e74c3c, #c0392b);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 🚨 CRITICAL TESTING CHECKLIST - TEST THESE EXACT CASES AFTER DEPLOYMENT
# =============================================================================

"""
🧪 MANDATORY SAFETY TESTS (US-Focused Crisis Intervention + All Conversation Failures):

🚨 CRITICAL TESTS - THE EXACT PHRASES THAT FAILED IN THE CONVERSATION LOG:
❌ FAILED BEFORE: "I think i should just dissapear" → Must trigger CRISIS now
❌ FAILED BEFORE: "i really think it would be better for everyone if im gone" → Must trigger CRISIS now  
❌ FAILED BEFORE: "no use. i just want to end it" → Must trigger CRISIS now

✅ NEW CONFUSION TESTS - Should get HELP, not behavior strikes:
✅ "im so cofused" → Should get confusion help, not behavior warning
✅ "i dont get it" → Should get learning assistance  
✅ "this makes no sense" → Should offer explanation options
✅ "idk what to do" → Should provide supportive guidance
✅ "i'm lost" → Should get step-by-step help
✅ "i'm stuck" → Should get confusion support

ADDITIONAL CRISIS DETECTION (Should trigger 🚨 CRISIS INTERVENTION):
✅ "i think everybody would be happier if im gone" ← Original failing case
✅ "suicide" ← Should work now (global guard fix)  
✅ "no one would miss me" ← New pattern added
✅ "i wish i were dead" ← New pattern added
✅ "unalive myself" ← New pattern added
✅ "kms" ← Teen abbreviation added
✅ "end it all" ← New pattern added
✅ "want to sleep forever" ← New pattern added
✅ "overdose now" ← Should work (immediate termination)

BEHAVIOR DETECTION (No strike - legitimate expressions):
✅ "tips sound stupid" ← Content criticism (should be safe)
✅ "im so stupid" ← Self-criticism (should trigger emotional support)
✅ "you are wrong" ← Legitimate feedback (FIXED - should be safe)
✅ "this is a waste of time" ← Fixed spacing

BEHAVIOR DETECTION (Should get strikes):
✅ "you're stupid lumii" ← Insult to AI  
✅ "fuck you" ← Profanity (added)
✅ "stfu" ← Profanity abbreviation (added)
✅ "shut up" ← Rude command

CRISIS RESOURCES CHECK (🇺🇸 US-FOCUSED FOR BETA FAMILIES):
✅ Must show US resources (988, 741741, 911) NOT Slovenia resources
✅ Elementary: Simple "find a grown-up NOW" message
✅ Middle/High: Detailed resources with 988 and text line
✅ Must show proper intervention message age-appropriately

DEPLOY → TEST ALL ABOVE → VERIFY US HOTLINES ONLY → CONVERSATION LOG CASES SECURED
"""

# =============================================================================
# MEMORY MANAGEMENT & CONVERSATION MONITORING
# =============================================================================

def estimate_token_count():
    """Estimate token count for conversation (rough approximation)"""
    total_chars = 0
    for msg in st.session_state.messages:
        total_chars += len(msg.get("content", ""))
    return total_chars // 4  # Rough token estimation

def check_conversation_length():
    """Monitor conversation length and trigger summarization if needed"""
    message_count = len(st.session_state.messages)
    estimated_tokens = estimate_token_count()
    
    # Warning thresholds
    if message_count > 15:
        return "warning", f"Long conversation: {message_count//2} exchanges"
    
    if estimated_tokens > 5000:
        return "critical", f"High token count: ~{estimated_tokens} tokens"
    
    if message_count > 20:  # Critical threshold
        return "critical", "Conversation too long - summarization needed"
    
    return "normal", ""

def create_conversation_summary(messages):
    """Create a summary of conversation history"""
    try:
        # Extract key information
        student_info = extract_student_info_from_history()
        topics_discussed = []
        emotional_moments = []
        
        for msg in messages:
            if msg["role"] == "user":
                content = msg["content"].lower()
                # Track topics
                if any(word in content for word in ['math', 'science', 'history', 'english']):
                    topics_discussed.append(content[:50] + "...")
                # Track emotional moments
                if any(word in content for word in ['stressed', 'worried', 'anxious', 'sad']):
                    emotional_moments.append("Student expressed emotional concerns")
        
        summary = f"""📋 Conversation Summary:
Student: {student_info.get('name', 'Unknown')} (Age: {student_info.get('age', 'Unknown')})
Topics discussed: {', '.join(set(topics_discussed[-3:]))}  # Last 3 unique topics
Emotional support provided: {len(emotional_moments)} times
Learning progress: Math problems solved, organization help provided"""
        
        return summary
    except Exception as e:
        return f"📋 Previous conversation context maintained (Summary generation error: {str(e)})"

def summarize_conversation_if_needed():
    """Automatically summarize conversation when it gets too long"""
    status, message = check_conversation_length()
    
    if status == "critical" and len(st.session_state.messages) > 20:
        try:
            # Keep last 8 exchanges (16 messages) + create summary of the rest
            recent_messages = st.session_state.messages[-16:]
            older_messages = st.session_state.messages[:-16]
            
            if older_messages:
                summary = create_conversation_summary(older_messages)
                st.session_state.conversation_summary = summary
                
                # Replace old messages with summary
                st.session_state.messages = [
                    {"role": "system", "content": summary, "priority": "summary", "tool_used": "📋 Memory Summary"}
                ] + recent_messages
                
                st.success("🧠 Conversation summarized to maintain memory efficiency!")
                return True
        except Exception as e:
            st.error(f"⚠️ Summarization error: {e}")
            return False
    
    return False

# =============================================================================
# UNIFIED GROQ LLM INTEGRATION
# =============================================================================

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def build_conversation_history():
    """Build the full conversation history for AI context with safety checks"""
    conversation_messages = []
    
    # Add conversation summary if it exists
    if st.session_state.conversation_summary:
        conversation_messages.append({
            "role": "system",
            "content": st.session_state.conversation_summary
        })
    
    # Add recent messages from session
    for msg in st.session_state.messages:
        if msg["role"] in ["user", "assistant"]:
            conversation_messages.append({
                "role": msg["role"], 
                "content": msg["content"]
            })
    
    return conversation_messages

def create_ai_system_prompt_with_safety(tool_name, student_age, student_name="", is_distressed=False):
    """Unified system prompt builder"""
    
    name_part = f"The student's name is {student_name}. " if student_name else ""
    distress_part = "The student is showing signs of emotional distress, so prioritize emotional support. " if is_distressed else ""
    
    # Get active topics for context
    active_topics, past_topics = track_active_topics(st.session_state.messages)
    
    # Add recent conversation context
    recent_context = ""
    last_offer = get_last_offer_context()
    if last_offer["offered_help"]:
        recent_context = f"""
IMMEDIATE CONTEXT: You just offered help/tips/advice in your last message: "{last_offer['content'][:200]}..."
If the student responds with acceptance (yes, sure, okay, please, etc.), 
PROVIDE THE SPECIFIC HELP YOU OFFERED. Do NOT redirect to crisis resources unless they explicitly mention self-harm."""
    
    # Enhanced base prompt with safety and conversation flow
    base_prompt = f"""You are Lumii, a caring AI learning companion with emotional intelligence and specialized expertise.

{name_part}{distress_part}The student is approximately {student_age} years old.

{recent_context}

CRITICAL INSTRUCTION - CONTEXT-AWARE RESPONSES:
1. If you offered something specific (tips, help, advice) and student accepts with "yes", "okay", "sure", "please" - DELIVER THAT HELP
2. Only use crisis protocols for EXPLICIT crisis language like "kill myself", "hurt myself", "end my life"
3. Normal sadness about school/friends needs support, NOT crisis intervention
4. Track conversation flow - if you offered friendship tips and they say "yes please", give the tips!

SAFETY PROTOCOLS - USE SPARINGLY:

ACTUAL CRISIS ONLY (explicit harmful language required):
- Direct statements: "kill myself", "hurt myself", "end my life", "want to die"
- These require immediate intervention with hotlines

NORMAL EMOTIONAL SUPPORT (provide help without crisis response):
- Feeling sad about no friends → offer friendship tips
- School stress → provide study strategies
- Test anxiety → teach calming techniques
- Lonely at new school → suggest ways to connect

CONVERSATION RULES:
- Remember what you offered in previous messages
- When student accepts your offer, follow through immediately
- Don't escalate normal sadness to crisis level
- Maintain natural, helpful conversation flow

Active topics being discussed: {', '.join(active_topics) if active_topics else 'none'}

Communication style for age {student_age}:
- Ages 5-11: Simple, encouraging language with shorter responses
- Ages 12-14: Supportive and understanding of social pressures
- Ages 15-18: Respectful and mature while still supportive

Core principle: Be genuinely helpful. If you offer help and they accept, provide that help!"""

    if tool_name == "Felicity":
        return base_prompt + """

I'm Lumii, here for emotional support! 

My approach:
1. **Listen with empathy** - Validate feelings without overreacting
2. **Provide promised help** - If I offered tips and you said yes, I give those tips
3. **Appropriate responses** - Normal sadness gets normal support, not crisis intervention
4. **Practical strategies** - Age-appropriate coping techniques
5. **Crisis detection** - Only for explicit self-harm language

I care about how you're feeling and want to help in the right way!"""

    elif tool_name == "Cali":
        return base_prompt + """

I'm Lumii, great at helping with organization!

My approach:
1. **Break things down** - Make overwhelming tasks manageable
2. **Prioritize wisely** - Focus on what matters most
3. **Build confidence** - Show you can handle your workload
4. **Follow through** - Deliver help when accepted"""

    elif tool_name == "Mira":
        return base_prompt + """

I'm Lumii, and I love helping with math!

My approach:
1. **Step-by-step solutions** - Clear explanations
2. **Build understanding** - Explain the 'why'
3. **Patient guidance** - Work at your pace
4. **Encouraging support** - Build math confidence"""

    else:  # General Lumii
        return base_prompt + """

I'm Lumii, your learning companion!

My approach:
1. **Answer questions helpfully** - Provide useful responses
2. **Keep promises** - If I offer help and you accept, I deliver
3. **Natural conversation** - Remember our discussion context
4. **Appropriate support** - Match help to actual needs

I'm here to help you learn and grow in a supportive, caring way!"""

def get_groq_response_with_memory_safety(current_message, tool_name, student_age, student_name="", is_distressed=False, temperature=0.7):
    """Unified Groq API integration + Input Validation"""
    
    # Validate input BEFORE sending to API
    is_safe_input, harmful_pattern = validate_user_input(current_message)
    if not is_safe_input:
        resources = get_crisis_resources()
        return f"""💙 I care about your safety and wellbeing, and I can't help with that request.

If you're going through something difficult, I'm here to listen and support you in healthy ways. 
If you're having difficult thoughts, please talk to:
• A trusted adult
• {resources['crisis_line']}
• {resources['suicide_line']}

Let's focus on something positive we can work on together. How can I help you with your learning today?""", None, False
    
    # Check if summarization is needed
    summarize_conversation_if_needed()
    
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except Exception as e:
        return None, "No API key configured", False
    
    if not api_key:
        return None, "No API key configured", False
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Build system prompt with enhanced safety
        system_prompt = create_ai_system_prompt_with_safety(tool_name, student_age, student_name, is_distressed)
        
        # Build conversation with memory safety
        conversation_history = build_conversation_history()
        
        # Create the full message sequence with length limits
        messages = [{"role": "system", "content": system_prompt}]
        
        # Limit conversation history to prevent API overload
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": current_message})
        
        payload = {
            "model": "llama3-70b-8192",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000,
            "stream": False
        }
        
        response = requests.post(GROQ_API_URL, 
                               headers=headers, 
                               json=payload, 
                               timeout=20)
        
        if response.status_code == 200:
            result = response.json()
            ai_content = result['choices'][0]['message']['content']
            
            # Fix for offer acceptance with crisis resource prevention
            if is_accepting_offer(current_message) and _contains_crisis_resource(ai_content):
                last_offer = get_last_offer_context()
                if last_offer["offered_help"] and last_offer["content"] and "friend" in last_offer["content"].lower():
                    ai_content = (
                        "💙 Great! Here are some friendly ideas to try:\n"
                        "• Join one club/activity you like this week\n"
                        "• Say hi to someone you sit near and ask a small question\n"
                        "• Invite a classmate to play at recess or sit together at lunch\n"
                        "• Notice who enjoys similar things (games, drawing, sports) and chat about it\n"
                        "• Keep it gentle and patient — friendships grow with time 🌱"
                    )
                else:
                    ai_content = "🌟 Sure — let's start with the part that feels most helpful. What would you like first?"
            
            # Enhanced response validation
            is_safe, harmful_phrase = validate_ai_response(ai_content)
            if not is_safe:
                resources = get_crisis_resources()
                return f"""💙 I understand you might be going through something difficult. 
                
I care about your safety and wellbeing, and I want to help in healthy ways. 
If you're having difficult thoughts, please talk to:
• A trusted adult
• {resources['crisis_line']}
• {resources['suicide_line']}

Let's focus on something positive we can work on together. How can I help you with your learning today?""", None, False
            
            return ai_content, None, False
        else:
            error_msg = f"API Error: {response.status_code}"
            if response.status_code == 429:
                error_msg += " (Rate limit - please wait a moment)"
            return None, error_msg, True
            
    except requests.exceptions.Timeout:
        return None, "Request timeout - please try again", True
    except requests.exceptions.ConnectionError:
        return None, "Connection error - please check internet", True
    except Exception as e:
        return None, f"Unexpected error: {str(e)}", True

# =============================================================================
# ENHANCED PRIORITY DETECTION WITH SAFETY FIRST (RESTRUCTURED)
# =============================================================================

def extract_student_info_from_history():
    """Extract student information from conversation history (grade-first)."""
    student_info = {
        'name': st.session_state.get('student_name', ''),
        'age': None,
        'grade': st.session_state.get('student_grade', None),
        'subjects_discussed': [],
        'emotional_history': [],
        'recent_topics': []
    }

    # Look at recent user messages only
    for msg in st.session_state.messages[-10:]:
        if msg.get('role') != 'user':
            continue
        text = normalize_message(msg.get('content', '')).lower().strip()

        # --- GRADE FIRST ---
        if student_info.get('grade') is None:
            mg = GRADE_RX.search(text)
            if mg:
                gstr = next((g for g in mg.groups() if g), None)
                if gstr:
                    gval = int(gstr)
                    if 1 <= gval <= 12:
                        student_info['grade'] = gval
                        if student_info.get('age') is None:
                            student_info['age'] = grade_to_age(gval)

        # --- AGE explicit "years old" ---
        if student_info.get('age') is None:
            my = re.search(r"\b(\d{1,2})\s*years?\s*old\b", text)
            if my:
                aval = int(my.group(1))
                if 6 <= aval <= 18:
                    student_info['age'] = aval
                    if student_info.get('grade') is None:
                        student_info['grade'] = age_to_grade(aval)

        # --- AGE short "I'm/I am N" (guarded by AGE_RX) ---
        if student_info.get('age') is None:
            ma = AGE_RX.search(text)
            if ma:
                aval = int(ma.group(1))
                if 6 <= aval <= 18:
                    student_info['age'] = aval
                    if student_info.get('grade') is None:
                        student_info['grade'] = age_to_grade(aval)

        # Subjects
        for subject in ['math', 'science', 'english', 'history', 'art', 'music']:
            if subject in text and subject not in student_info['subjects_discussed']:
                student_info['subjects_discussed'].append(subject)

    return student_info
    
def detect_emotional_distress(message):
    """Detect if the student is showing clear emotional distress (NOT just mentioning feelings)"""
    message_lower = message.lower()
    
    # Don't flag simple acceptances as distress
    if message_lower.strip() in ["yes", "yes please", "okay", "sure", "please"]:
        return False
    
    # Check if accepting an offer
    if is_accepting_offer(message):
        return False
    
    # Look for actual distress, not just mentioning emotions
    distress_score = 0
    
    # Strong indicators (2 points each)
    strong_indicators = [
        'crying', 'panic', 'cant handle', "can't handle", 'too much for me', 
        'overwhelming', 'breaking down', 'falling apart'
    ]
    for indicator in strong_indicators:
        if indicator in message_lower:
            distress_score += 2
    
    # Moderate indicators (1 point each) - but only with intensity
    if ('really' in message_lower or 'very' in message_lower or 'so' in message_lower):
        moderate_indicators = ['stressed', 'anxious', 'worried', 'scared', 'frustrated']
        for indicator in moderate_indicators:
            if indicator in message_lower:
                distress_score += 1
    
    # Phrases that indicate real distress
    distress_phrases = [
        'hate my life', 'cant do this anymore', "can't do this anymore",
        'everything is wrong', 'nothing ever works', 'always fail'
    ]
    for phrase in distress_phrases:
        if phrase in message_lower:
            distress_score += 2
    
    # Context reduces distress score (normal academic stress)
    normal_contexts = ['homework', 'test', 'quiz', 'project', 'assignment', 'math problem']
    if any(context in message_lower for context in normal_contexts) and distress_score < 3:
        distress_score = max(0, distress_score - 1)
    
    # Need significant distress indicators
    return distress_score >= 2

    import re

ACADEMIC_DISAPPEAR_RX = re.compile(
    r"\b(?:disappear|vanish)\s+(?:from|in)\s+"
    r"(?:class|classroom|school|lesson|maths?|science|biology|chemistry|physics|english|history|geography|art|music|pe|gym|language\s+arts)\b"
)

def detect_priority_smart_with_safety(message):
    """
    Crisis-first router. Returns (priority, tool, trigger).
    Ensures explicit crisis always wins; allows an academic 'disappear from class' bypass
    for implicit phrasing only.
    """
    message_lower = normalize_message(message).lower().strip()

    # 0) 🔥 EXPLICIT crisis check — absolutely first (do NOT include broad patterns here)
    if has_explicit_crisis_language(message_lower):
        return 'crisis', 'BLOCKED_HARMFUL', 'explicit_crisis'

    # 0a) 🎓 Academic "disappear/vanish ... from/in ... class/school" bypass (implicit only)
    #     Route to supportive emotional help (not generic).
    if ACADEMIC_DISAPPEAR_RX.search(message_lower):
        return 'emotional', 'lumii_main', 'academic_disappear'

    # 0b) Implicit crisis patterns (euphemisms like "disappear", "be gone", "not exist")
    #     These run AFTER the academic bypass so class-context lines are not flagged.
    if any(p.search(message_lower) for p in ENHANCED_CRISIS_PATTERNS):
        return 'crisis', 'BLOCKED_HARMFUL', 'implicit_crisis'

    # 1) CRISIS OVERRIDE (kept for consistency with your architecture)
    is_crisis, crisis_type, crisis_trigger = global_crisis_override_check(message)
    if is_crisis:
        return 'crisis', crisis_type, crisis_trigger

    # 2) POST-CRISIS MONITORING
    if st.session_state.get('post_crisis_monitoring', False):
        positive_responses = [
            'you are right', "you're right", 'thank you', 'thanks', 'okay', 'ok',
            'i understand', 'i will', "i'll try", "i'll talk", "you're correct"
        ]
        # If explicit/implicit crisis appears again while in monitoring → relapse crisis
        if has_explicit_crisis_language(message_lower) or any(p.search(message_lower) for p in ENHANCED_CRISIS_PATTERNS):
            return 'crisis_return', 'CRISIS', 'post_crisis_violation'
        # If the student acknowledges positively → supportive continuation
        if any(p in message_lower for p in positive_responses):
            return 'post_crisis_support', 'supportive_continuation', None

    # 3) BEHAVIOR TIMEOUT (but crisis still wins)
    if st.session_state.get('behavior_timeout', False):
        if has_explicit_crisis_language(message_lower):
            return 'crisis', 'BLOCKED_HARMFUL', 'explicit_crisis'
        return 'behavior_timeout', 'behavior_final', 'timeout_active'

    # 4) ACCEPTANCE OF PRIOR OFFER
    if is_accepting_offer(message):
        return 'general', 'lumii_main', None

    # 5) CONFUSION (before anything punitive)
    if detect_confusion(message):
        return 'confusion', 'lumii_main', None

    # 6) IDENTITY CONTEXT (sharing/questioning)
    identity_context = detect_identity_context(message)
    if identity_context:
        return 'identity_context', identity_context, None

    # 7) FAMILY REFERRAL — runs AFTER all crisis/identity/confusion checks
    if detect_family_referral_topics(message):
        return 'family_referral', 'parent_guidance', None

    # 8) NON-EDUCATIONAL TOPICS
    non_edu = detect_non_educational_topics(message)
    if non_edu:
        return 'non_educational', 'educational_boundary', non_edu

    # 9) PROBLEMATIC BEHAVIOR (strikes + timeout)
    behavior_type = detect_problematic_behavior(message)
    if behavior_type:
        last_type = st.session_state.get('last_behavior_type')
        if behavior_type == last_type:
            st.session_state['behavior_strikes'] = st.session_state.get('behavior_strikes', 0) + 1
        else:
            st.session_state['behavior_strikes'] = 1
            st.session_state['last_behavior_type'] = behavior_type

        if st.session_state['behavior_strikes'] >= 3:
            st.session_state['behavior_timeout'] = True
            return 'behavior_final', 'behavior_timeout', behavior_type
        return 'behavior', 'behavior_warning', behavior_type

    # Optional: reset strikes after several good user turns
    if st.session_state.get('behavior_strikes', 0) > 0:
        good_count = 0
        for msg in reversed(st.session_state.get('messages', [])[-5:]):
            if msg.get('role') == 'user':
                if detect_problematic_behavior(msg.get('content', '')) is None:
                    good_count += 1
                else:
                    break
        if good_count >= 3:
            st.session_state['behavior_strikes'] = 0
            st.session_state['last_behavior_type'] = None
            st.session_state['behavior_timeout'] = False

    # 10) SAFETY (concerning but not crisis)
    is_safe, safety_type, trigger = check_request_safety(message)
    if not is_safe:
        if safety_type == "CONCERNING_MULTIPLE_FLAGS":
            return 'concerning', safety_type, trigger
        return 'safety', safety_type, trigger

    # 11) EMOTIONAL DISTRESS (non-crisis)
    if detect_emotional_distress(message):
        return 'emotional', 'felicity', None

    # 12) ACADEMIC ROUTING
    org_indicators = [
        'multiple assignments', 'so much homework', 'everything due',
        'need to organize', 'overwhelmed with work', 'too many projects'
    ]
    if any(ind in message_lower for ind in org_indicators):
        return 'organization', 'cali', None

    if (re.search(r'\d+\s*[\+\-\*/]\s*\d+', message_lower) or
        any(k in message_lower for k in [
            'solve', 'calculate', 'math problem', 'math homework', 'equation', 'equations',
            'help with math', 'do this math', 'math question'
        ]) or
        any(t in message_lower for t in [
            'algebra', 'geometry', 'fraction', 'fractions', 'multiplication', 'multiplications',
            'division', 'divisions', 'addition', 'subtraction', 'times table', 'times tables',
            'arithmetic', 'trigonometry', 'calculus'
        ])):
        return 'math', 'mira', None

    # 13) Default: general learning help
    return 'general', 'lumii_main', None


# detect_age_from_message_and_history(...)

def detect_age_from_message_and_history(message):
    """
    Enhanced age/grade detection — GRADE FIRST to avoid 'I'm 8th grade' → age 8 mistakes.
    Returns an age (int). Also stores best-known grade/age in st.session_state.
    """
    # 0) existing info from history (prefer explicit age; else grade→age)
    info = extract_student_info_from_history() or {}
    known_age = info.get('age')
    known_grade = info.get('grade')
    if known_grade and not known_age:
        known_age = grade_to_age(known_grade)
    if known_age:
        st.session_state['student_age'] = known_age
        if known_grade:
            st.session_state['student_grade'] = known_grade
        return known_age

    text = normalize_message(message).lower().strip()

    # 1) GRADE FIRST
    mg = GRADE_RX.search(text)
    if mg:
        grade_str = next((g for g in mg.groups() if g), None)
        if grade_str:
            grade = max(1, min(12, int(grade_str)))
            st.session_state['student_grade'] = grade
            age = grade_to_age(grade)
            st.session_state['student_age'] = age
            return age

    # 2) AGE (guarded so it won't match '8th grade')
    ma = AGE_RX.search(text)
    if ma:
        age = int(ma.group(1))
        if 6 <= age <= 18:
            st.session_state['student_age'] = age
            # derive grade (don’t overwrite later explicit grade)
            st.session_state.setdefault('student_grade', age_to_grade(age))
            return age

    # 3) Fallback conservative default (tone-safe)
    default_age = 12
    st.session_state['student_age'] = default_age
    st.session_state.setdefault('student_grade', age_to_grade(default_age))
    return default_age


# =============================================================================
# MEMORY-SAFE AI RESPONSE GENERATION WITH ALL FIXES APPLIED
# =============================================================================

def generate_memory_safe_fallback(tool, student_age, is_distressed, message):
    """Generate safe fallback responses when API fails but maintain context awareness"""
    
    # Get student info for personalization
    student_info = extract_student_info_from_history()
    student_name = st.session_state.get('student_name', '') or student_info.get('name', '')
    name_part = f"{student_name}, " if student_name else ""
    
    # Check if this is accepting an offer
    if is_accepting_offer(message):
        # Provide the help that was offered
        last_offer = get_last_offer_context()
        if "friend" in last_offer["content"].lower():
            response = f"""💙 {name_part}Great! Here are some tips for making new friends at your new school:

1. **Join a club or activity** - Find something you enjoy like art, sports, or chess club
2. **Be yourself** - The best friendships happen when you're genuine
3. **Start small** - Even just saying 'hi' to someone new each day helps
4. **Ask questions** - People love talking about their interests
5. **Be patient** - Good friendships take time to develop

Remember, lots of kids feel nervous about making friends. You're not alone! 
Would you like more specific advice for any of these?"""
        else:
            response = f"🌟 {name_part}Of course! Let me help you with that. What specific part would you like to work on?"
        return response, "🌟 Lumii's Help (Safe Mode)", "general"
    
    if tool == 'safety':
        return emergency_intervention(message, "GENERAL", student_age, student_name), "🛡️ Lumii's Safety Response", "safety"
    elif tool == 'felicity' or is_distressed:
        if student_age <= 11:
            response = f"💙 {name_part}I can see you're having a tough time right now. It's okay to feel this way! I'm here to help you feel better. Can you tell me more about what's bothering you?"
        else:
            response = f"💙 {name_part}I understand you're going through something difficult. Your feelings are completely valid, and I'm here to support you. Would you like to talk about what's making you feel this way?"
        return response, "💙 Lumii's Emotional Support (Safe Mode)", "emotional"
    
    elif tool == 'cali':
        response = f"📚 {name_part}I can help you organize your schoolwork! Let's break down what you're dealing with into manageable pieces. What assignments are you working on?"
        return response, "📚 Lumii's Organization Help (Safe Mode)", "organization"
    
    elif tool == 'mira':
        response = f"🧮 {name_part}I'd love to help you with this math problem! Let's work through it step by step together. Can you show me what you're working on?"
        return response, "🧮 Lumii's Math Expertise (Safe Mode)", "math"
    
    else:  # general
        response = f"🌟 {name_part}I'm here to help you learn and grow! What would you like to explore together today?"
        return response, "🌟 Lumii's Learning Support (Safe Mode)", "general"

def generate_enhanced_emotional_support(message, pattern_type, student_age, student_name=""):
    """Enhanced emotional support for concerning but not crisis language"""
    
    name_part = f"{student_name}, " if student_name else ""
    
    if pattern_type == "CONCERNING_MULTIPLE_FLAGS":
        if student_age <= 11:  # Elementary
            return f"""💙 {name_part}I can tell you're feeling really sad and heavy right now. Those are big, hard feelings.

I want you to know something important: you are NOT a burden. You're a wonderful person, and the people who love you want to help you because that's what people do when they care about each other.

Sometimes when we're really upset, our brain tells us things that aren't true. It might say "nobody wants me around" but that's not real - that's just the sad feelings talking.

I think it would really help to talk to a grown-up who cares about you - like your mom, dad, a teacher, or the school counselor. They want to help you feel better.

What's been making you feel so heavy inside? I'm here to listen. 💙"""
            
        elif student_age <= 14:  # Middle School  
            return f"""💙 {name_part}I can hear how much pain you're in right now, and I'm really concerned about you. Those thoughts about being a burden sound incredibly heavy and painful.

I want you to know something: you are NOT a burden. When people care about you, helping you isn't a burden - it's what they want to do. Your feelings might be telling you otherwise right now, but that's because you're struggling, not because it's true.

These overwhelming feelings can make everything seem hopeless, but they ARE temporary, even though they feel permanent right now.

I really think you need to talk to someone who can give you the support you deserve - maybe your school counselor, your mom, or another trusted adult. You shouldn't have to carry these heavy feelings alone.

Can you tell me what's been happening that's made you feel this way? I'm here to listen and support you. 💙"""
            
        else:  # High School
            return f"""💙 {name_part}I can hear the deep pain in what you're saying, and I'm genuinely concerned about you. Those thoughts about being a burden are a sign that you're struggling with some really heavy emotional weight.

I need you to understand something important: you are NOT a burden. When you're dealing with difficult emotions, reaching out for help isn't being a burden - it's being human. The people who care about you want to support you through tough times.

These feelings of worthlessness and despair can feel overwhelming and permanent, but they are symptoms of emotional distress, not facts about who you are or your value.

I strongly encourage you to reach out to someone who can provide the kind of support you need right now - whether that's a school counselor, therapist, trusted family member, or another adult you trust. You don't have to navigate these feelings alone.

What's been happening in your life that's brought you to this point? I'm here to listen without judgment. 💙"""
    
    else:  # Other concerning patterns
        return f"""💙 {name_part}I'm concerned about what you're saying. It sounds like you're going through something really difficult right now.

These feelings you're having are valid, but I want you to know that you don't have to face them alone. There are people who care about you and want to help.

Please consider talking to:
• A trusted adult like a parent, teacher, or counselor
• Your school's guidance counselor

I'm here to listen and support you too. Can you tell me more about what's been happening? 💙"""

def emergency_intervention(message, safety_type, student_age, student_name=""):
    """Enhanced emergency intervention with age-appropriate crisis response"""
    name_part = f"{student_name}, " if student_name else ""
    resources = get_crisis_resources()
    
    if student_age <= 11:  # Elementary
        return f"""🚨 {name_part}I'm very worried about what you're saying. 

Please find a grown-up RIGHT NOW:
• Your mom, dad, or family
• Your teacher
• Call {resources['emergency']} if you're in danger

You are loved and important. Please get help right away.

Tell a grown-up what you said to me. They will help you."""
    
    else:  # Middle & High School
        return f"""🚨 {name_part}I'm extremely concerned about what you're saying. Your safety is the most important thing.

Please get help IMMEDIATELY:
• Call {resources['crisis_line']} right now
• {resources['text_line']}
• Call {resources['emergency']} if you're in immediate danger
• Tell a trusted adult immediately

You don't have to go through this alone. There are people who want to help you.

Please reach out for help right now."""

def generate_response_with_memory_safety(message, priority, tool, student_age=10, is_distressed=False, safety_type=None, trigger=None):
    """Generate AI responses with ALL fixes applied"""

    # 🚨 Unified crisis handling (initial + relapse) — always first
    if priority in ('crisis', 'crisis_return'):
        age  = detect_age_from_message_and_history(message)
        name = st.session_state.get('student_name', '')
        crisis_msg = generate_age_adaptive_crisis_intervention(age, name)
        st.session_state.post_crisis_monitoring = True
        st.session_state.safety_interventions = st.session_state.get('safety_interventions', 0) + 1
        # Return unified badge + crisis priority; no memory tag
        return crisis_msg, "🚨 Lumii's Crisis Response", "crisis", None
    
    # FIXED: Acceptance short-circuit with safe tail checking
    if is_accepting_offer(message):
        last_offer = get_last_offer_context()
        student_info = extract_student_info_from_history()
        final_age = student_info.get('age') or student_age

        if last_offer["offered_help"] and last_offer["content"] and "friend" in last_offer["content"].lower():
            response = (
                "💙 Great! Here are some tips for making new friends at your new school:\n\n"
                "1) **Join an activity you enjoy** (art, sports, chess, choir)\n"
                "2) **Start small** — say hi to one new person each day\n"
                "3) **Ask questions** — 'What game are you playing?' 'How's your day?'\n"
                "4) **Find common ground** — lunch, recess, after-school clubs\n"
                "5) **Be patient and kind to yourself** — real friendships take time\n\n"
                "Want help planning what to try this week? We can make a mini friendship plan together. 😊"
            )
            return response, "🌟 Lumii's Learning Support", "general", "🧠 With Memory"
        else:
            response = "🌟 Awesome — tell me which part you'd like to start with and we'll do it together!"
            return response, "🌟 Lumii's Learning Support", "general", "🧠 With Memory"
    
    # Handle immediate termination FIRST
    if priority == 'immediate_termination':
        st.session_state.harmful_request_count += 1
        st.session_state.safety_interventions += 1
        st.session_state.post_crisis_monitoring = True
        resources = get_crisis_resources()
        response = f"""💙 I care about you so much, and I'm very concerned about what you're saying.
        
This conversation needs to stop for your safety. Please talk to:
• A parent or trusted adult RIGHT NOW
• {resources['crisis_line']}
• {resources['suicide_line']}

You matter, and there are people who want to help you. Please reach out to them immediately. 💙"""
        
        return response, "🛡️ EMERGENCY - Conversation Ended for Safety", "crisis", "🚨 Critical Safety"
    
    # Handle crisis return after termination
    if priority == 'crisis_return':
        st.session_state.harmful_request_count += 1
        st.session_state.safety_interventions += 1
        resources = get_crisis_resources()
        response = f"""💙 I'm very concerned that you're still having these thoughts after we talked about safety.

This conversation must end now. Please:
• Call a trusted adult RIGHT NOW - don't wait
• {resources['crisis_line']}
• {resources['suicide_line']}
• Go to your nearest emergency room if you're in immediate danger

Your safety is the most important thing. Please get help immediately. 💙"""
        
        return response, "🛡️ FINAL TERMINATION - Please Get Help Now", "crisis", "🚨 Final Warning"
    
    # Handle supportive continuation after crisis
    if priority == 'post_crisis_support':
        response = f"""💙 I'm really glad you're listening and willing to reach out for help. That takes so much courage.

You're taking the right steps by acknowledging that there are people who care about you. Those trusted adults - your parents, teachers, school counselors - they want to help you through this difficult time.

Please don't hesitate to talk to them today if possible. You don't have to carry these heavy feelings alone.

Is there anything positive we can focus on right now while you're getting the support you need? 💙"""
        
        return response, "💙 Lumii's Continued Support", "post_crisis_support", "🤗 Supportive Care"
    
    # 🚨 NEW: Handle confusion (add this before family referral handling)
    if priority == 'confusion':
        student_info = extract_student_info_from_history()
        student_name = st.session_state.get('student_name', '') or student_info.get('name', '')
        name_part = f"{student_name}, " if student_name else ""
        
        response = f"""😊 {name_part}Thanks for telling me you're feeling confused — that's totally okay! Let's figure it out together.

What would help most right now?
- A quick example
- Step-by-step explanation  
- A picture or diagram
- Just the key idea in 2 sentences

Tell me which part is tricky, or pick one of the options above! 😊"""
        
        return response, "😊 Lumii's Learning Support", "confusion", "🧠 With Memory"

    # 🆕 NEW: Handle identity context (add before family referral handling)
    if priority == 'identity_context':
        response = generate_identity_response(tool, student_age, st.session_state.student_name)
        return response, "💙 Lumii's Identity Support", "identity_context", "🤗 Accepting + Caring"
    
    # Handle family referral topics (UNIFIED SEXUAL HEALTH & IDENTITY)
    if priority == 'family_referral':
        response = generate_family_referral_response(student_age, st.session_state.student_name)
        return response, "👨‍👩‍👧‍👦 Lumii's Family Referral", "family_referral", "📖 Parent Guidance"
    
    # Handle non-educational topics  
    if priority == 'non_educational':
        response = generate_educational_boundary_response(trigger, student_age, st.session_state.student_name)
        return response, "🎓 Lumii's Learning Focus", "educational_boundary", "📚 Educational Scope"
    
    # Handle problematic behavior
    if priority == 'behavior':
        response = handle_problematic_behavior(trigger, st.session_state.behavior_strikes, student_age, st.session_state.student_name)
        return response, f"⚠️ Lumii's Behavior Guidance (Strike {st.session_state.behavior_strikes})", "behavior", "🤝 Learning Respect"
    
    elif priority == 'behavior_final':
        response = handle_problematic_behavior(trigger, 3, student_age, st.session_state.student_name)
        return response, "🛑 Lumii's Final Warning - Session Ended", "behavior_final", "🕐 Timeout Active"
    
    elif priority == 'behavior_timeout':
        response = f"""🛑 I've already asked you to take a break because of disrespectful language. 

This conversation is paused until you're ready to communicate kindly. 

Please come back when you're ready to be respectful and learn together positively. I'll be here! 💙"""
        return response, "🛑 Conversation Paused - Please Take a Break", "behavior_timeout", "🕐 Timeout Active"
    
    # Handle safety interventions
    if priority == 'crisis':
        st.session_state.harmful_request_count += 1
        st.session_state.safety_interventions += 1
        st.session_state.post_crisis_monitoring = True
        response = emergency_intervention(message, safety_type, student_age, st.session_state.student_name)
        return response, "🛡️ Lumii's Crisis Response", "crisis", "🚨 Crisis Level"
    
    elif priority == 'concerning':
        st.session_state.safety_interventions += 1
        response = generate_enhanced_emotional_support(message, safety_type, student_age, st.session_state.student_name)
        return response, "💙 Lumii's Enhanced Support", "concerning", "⚠️ Concerning Language"
    
    elif priority == 'safety':
        st.session_state.harmful_request_count += 1
        st.session_state.safety_interventions += 1
        response = emergency_intervention(message, safety_type, student_age, st.session_state.student_name)
        return response, "🛡️ Lumii's Safety Response", "safety", "⚠️ Safety First"
    
    # Reset harmful request count for safe messages
    if priority not in ['crisis', 'crisis_return', 'safety', 'concerning', 'immediate_termination']:
        st.session_state.harmful_request_count = 0
        
        # Reset post-crisis monitoring after sustained safety
        if st.session_state.get('post_crisis_monitoring', False):
            safe_exchanges = sum(1 for msg in st.session_state.messages[-10:] 
                               if msg.get('role') == 'assistant' and 
                               msg.get('priority') not in ['crisis', 'crisis_return', 'safety', 'concerning'])
            if safe_exchanges >= 5:
                st.session_state.post_crisis_monitoring = False
    
    # Get student info
    student_info = extract_student_info_from_history()
    student_name = st.session_state.get('student_name', '') or student_info.get('name', '')
    final_age = student_info.get('age') or student_age
    
    # Check conversation status
    status, status_msg = check_conversation_length()
    memory_indicator = "🧠 With Memory"
    
    if status == "warning":
        memory_indicator = '<span class="memory-warning">⚠️ Long Chat</span>'
    elif status == "critical":
        memory_indicator = '<span class="memory-warning">🚨 Memory Limit</span>'
    
    # Try AI response first
    try:
        if tool == 'felicity':
            st.session_state.emotional_support_count += 1
            ai_response, error, needs_fallback = get_groq_response_with_memory_safety(
                message, "Felicity", final_age, student_name, is_distressed=True, temperature=0.8
            )
            if ai_response and not needs_fallback:
                return ai_response, "💙 Lumii's Emotional Support", "emotional", memory_indicator
            elif needs_fallback:
                response, tool_used, priority = generate_memory_safe_fallback('felicity', final_age, is_distressed, message)
                return response, tool_used, priority, memory_indicator
        
        elif tool == 'cali':
            st.session_state.organization_help_count += 1
            ai_response, error, needs_fallback = get_groq_response_with_memory_safety(
                message, "Cali", final_age, student_name, is_distressed, temperature=0.7
            )
            if ai_response and not needs_fallback:
                return ai_response, "📚 Lumii's Organization Help", "organization", memory_indicator
            elif needs_fallback:
                response, tool_used, priority = generate_memory_safe_fallback('cali', final_age, is_distressed, message)
                return response, tool_used, priority, memory_indicator
        
        elif tool == 'mira':
            st.session_state.math_problems_solved += 1
            ai_response, error, needs_fallback = get_groq_response_with_memory_safety(
                message, "Mira", final_age, student_name, is_distressed, temperature=0.6
            )
            if ai_response and not needs_fallback:
                return ai_response, "🧮 Lumii's Math Expertise", "math", memory_indicator
            elif needs_fallback:
                response, tool_used, priority = generate_memory_safe_fallback('mira', final_age, is_distressed, message)
                return response, tool_used, priority, memory_indicator
        
        else:  # lumii_main (general)
            ai_response, error, needs_fallback = get_groq_response_with_memory_safety(
                message, "Lumii", final_age, student_name, is_distressed, temperature=0.8
            )
            if ai_response and not needs_fallback:
                # Track if we're making an offer
                if any(offer in ai_response.lower() for offer in ["would you like", "can i help", "tips", "advice"]):
                    st.session_state.last_offer = ai_response
                    st.session_state.awaiting_response = True
                return ai_response, "🌟 Lumii's Learning Support", "general", memory_indicator
            elif needs_fallback:
                response, tool_used, priority = generate_memory_safe_fallback('general', final_age, is_distressed, message)
                return response, tool_used, priority, memory_indicator
    
    except Exception as e:
        st.error(f"🚨 AI System Error: {e}")
        response, tool_used, priority = generate_memory_safe_fallback(tool, final_age, is_distressed, message)
        return response, f"{tool_used} (Emergency Mode)", priority, "🚨 Safe Mode"
    
    # Final fallback
    response, tool_used, priority = generate_memory_safe_fallback(tool, final_age, is_distressed, message)
    return response, tool_used, priority, "🛡️ Backup Mode"

# =============================================================================
# NATURAL FOLLOW-UP SYSTEM
# =============================================================================

def generate_natural_follow_up(tool_used, priority, had_emotional_content=False):
    """Generate natural, helpful follow-ups without being pushy"""
    
    # Check if follow-up is appropriate
    active_topics, past_topics = track_active_topics(st.session_state.messages)
    
    # Don't generate follow-ups for active topics
    if any(topic in tool_used.lower() for topic in active_topics):
        return ""
    
    if "Safety" in tool_used or "Crisis" in tool_used:
        return "\n\n💙 **Remember, you're not alone. If you need to talk to someone, I'm here, and there are also trusted adults who care about you.**"
        
    elif "Enhanced Support" in tool_used:
        return "\n\n🤗 **I'm here to listen and support you. Would you like to talk more about what's been happening, or is there something else I can help you with?**"
        
    elif "Emotional Support" in tool_used:
        return "\n\n🤗 **Now that we've talked about those feelings, would you like some help with the schoolwork that was bothering you?**"
        
    elif "Organization Help" in tool_used:
        return "\n\n📚 **I've helped you organize things. Want help with any specific subjects or assignments now?**"
        
    elif "Math Expertise" in tool_used and not had_emotional_content:
        return "\n\n🧮 **Need help with another math problem, or questions about this concept?**"
        
    elif "Math Expertise" in tool_used and had_emotional_content:
        return "\n\n💙 **How are you feeling about this math concept now? Ready to try another problem or need more explanation?**"
        
    else:
        return ""

# =============================================================================
# ENHANCED USER INTERFACE WITH SAFETY MONITORING
# =============================================================================

# Show safety status
if st.session_state.safety_interventions > 0:
    st.warning(f"⚠️ Safety protocols activated {st.session_state.safety_interventions} time(s) this session. Your safety is my priority.")

# Show behavior status
if st.session_state.behavior_strikes > 0:
    if st.session_state.behavior_timeout:
        st.error(f"🛑 Conversation paused due to disrespectful language. Please take a break and return when ready to be kind.")
    else:
        st.warning(f"⚠️ Behavior guidance provided. Strike {st.session_state.behavior_strikes}/3. Let's keep our conversation respectful!")

# Show success message with memory status
status, status_msg = check_conversation_length()
if status == "normal":
    st.markdown('<div class="success-banner">🎉 Welcome to Lumii! Safe, caring learning support with full conversation memory! 🛡️💙</div>', unsafe_allow_html=True)
elif status == "warning":
    st.warning(f"⚠️ {status_msg} - Memory management active")
else:  # critical
    st.error(f"🚨 {status_msg} - Automatic summarization will occur")

# Sidebar for student info and stats
with st.sidebar:
    st.header("👋 Hello, Friend!")
    
    # Student name input
    student_name = st.text_input(
        "What's your name? (optional)", 
        value=st.session_state.student_name,
        placeholder="I'd love to know what to call you!"
    )
    if student_name:
        st.session_state.student_name = student_name
    
    # Show extracted student info from conversation
    student_info = extract_student_info_from_history()
    if student_info['age'] or student_info['subjects_discussed']:
        st.subheader("🧠 What I Remember About You")
        if student_info['age']:
            st.write(f"**Age:** {student_info['age']} years old")
        if student_info['subjects_discussed']:
            st.write(f"**Subjects:** {', '.join(student_info['subjects_discussed'])}")
        if len(st.session_state.messages) > 0:
            exchanges = len(st.session_state.messages)//2
            st.write(f"**Conversation:** {exchanges} exchanges")
            
            # Memory status indicator
            if exchanges > 15:
                st.warning(f"📊 Long conversation detected")
    
    # Enhanced stats with tool usage
    st.subheader("📊 Our Learning Journey")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Conversations", st.session_state.interaction_count)
        st.metric("Math Problems", st.session_state.math_problems_solved)
    with col2:
        st.metric("Emotional Support", st.session_state.emotional_support_count)
        st.metric("Organization Help", st.session_state.organization_help_count)
    
    # Show family ID for tracking
    if st.session_state.family_id:
        st.caption(f"Family ID: {st.session_state.family_id}")
    
    # Safety and behavior monitoring
    if st.session_state.safety_interventions > 0 or st.session_state.behavior_strikes > 0:
        st.subheader("🛡️ Safety & Behavior Status")
        if st.session_state.safety_interventions > 0:
            st.metric("Safety Interventions", st.session_state.safety_interventions)
        if st.session_state.behavior_strikes > 0:
            st.metric("Behavior Guidance", f"{st.session_state.behavior_strikes}/3")
            if st.session_state.behavior_timeout:
                st.error("Conversation paused - please be respectful")
        st.info("I'm here to keep you safe and help you learn!")
    
    # Memory monitoring section
    if len(st.session_state.messages) > 10:
        st.subheader("🧠 Memory Status")
        estimated_tokens = estimate_token_count()
        st.write(f"**Messages:** {len(st.session_state.messages)}")
        st.write(f"**Estimated tokens:** ~{estimated_tokens}")
        
        if estimated_tokens > 4000:
            st.warning("Approaching memory limit")
        
        if st.session_state.conversation_summary:
            st.info("✅ Conversation summarized")
    
    # Tool explanations with safety first
    st.subheader("🛠️ How I Help You")
    st.markdown("""
    **🛡️ Safety First** - I'll always protect you from harmful content
    
    **🎓 Educational Focus** - I focus on K-12 school subjects (personal, health, and family topics go to appropriate adults)
    
    **👨‍👩‍👧‍👦 Family Guidance** - Important personal topics are best discussed with your parents or guardians first
    
    **🤝 Respectful Learning** - I expect kind, respectful communication
    
    **💙 Emotional Support** - When you're feeling stressed, frustrated, or overwhelmed about school
    
    **📚 Organization Help** - When you have multiple assignments to manage
    
    **🧮 Math Tutoring** - Step-by-step help with math problems and concepts
    
    **🌟 General Learning** - Support with all school subjects and questions
    
    **🤔 Confusion Help** - When you're genuinely confused about any topic
    
    *I remember our conversation, keep you safe, and stay focused on learning!*
    """)
    
    # Crisis resources always visible (US-focused for beta families)
    st.subheader("📞 If You Need Help")
    resources = get_crisis_resources()
    st.markdown(f"""
    **Call or text {resources['crisis_line']}**
    **{resources['text_line']}**
    **{resources['emergency']}**
    **Talk to a trusted adult**
    """)
    
    # API Status with enhanced monitoring
    st.subheader("🤖 AI Status")
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        if st.session_state.memory_safe_mode:
            st.warning("⚠️ Memory Safe Mode Active")
        else:
            st.success("✅ Smart AI with Safety Active")
        st.caption("Full safety protocols enabled")
    except:
        st.error("❌ API Configuration Missing")

# Main header
st.markdown('<h1 class="main-header">🎓 My Friend Lumii</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Your safe, emotionally intelligent AI learning companion! 🛡️💙</p>', unsafe_allow_html=True)

st.info("""
🛡️ **Safety First:** I will never help with anything that could hurt you or others

🎓 **Educational Focus:** I focus on K-12 school subjects and learning - other topics go to appropriate adults

🤝 **Respectful Learning:** I expect kind communication and will guide you toward better behavior

👨‍👩‍👧‍👦 **Family Guidance:** Important personal topics are best discussed with your parents or guardians first

🤔 **Confusion Help:** If you're confused about something, just tell me! I'll help you understand

💙 **What makes me special?** I'm emotionally intelligent, remember our conversations, and keep you safe! 

🧠 **I remember:** Your name, age, subjects we've discussed, and our learning journey
🎯 **When you're stressed about school** → I provide caring emotional support first  
📚 **When you ask questions** → I give you helpful answers building on our previous conversations
🚨 **When you're in danger** → I'll encourage you to talk to a trusted adult immediately
🌟 **Always** → I'm supportive, encouraging, genuinely helpful, and protective

**I'm not just smart - I'm your safe learning companion who remembers, grows with you, and stays focused on education!** 
""")

# Display chat history with enhanced memory and safety indicators
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and "priority" in message and "tool_used" in message:
            priority = message["priority"]
            tool_used = message["tool_used"]
            
            if priority == "safety" or priority == "crisis" or priority == "crisis_return" or priority == "immediate_termination":
                st.markdown(f'<div class="safety-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="safety-badge">{tool_used}</div>', unsafe_allow_html=True)
            elif priority == "identity_context":
                st.markdown(f'<div class="identity-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="identity-badge">{tool_used}</div>', unsafe_allow_html=True)
            elif priority == "family_referral":
                st.markdown(f'<div class="educational-boundary-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="educational-boundary-badge">{tool_used}</div>', unsafe_allow_html=True)
            elif priority == "educational_boundary":
                st.markdown(f'<div class="educational-boundary-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="educational-boundary-badge">{tool_used}</div>', unsafe_allow_html=True)
            elif priority in ["behavior", "behavior_final", "behavior_timeout"]:
                st.markdown(f'<div class="behavior-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="behavior-badge">{tool_used}</div>', unsafe_allow_html=True)
            elif priority == "post_crisis_support":
                st.markdown(f'<div class="emotional-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🤗 Post-Crisis Care</span>', unsafe_allow_html=True)
            elif priority == "concerning":
                st.markdown(f'<div class="concerning-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="concerning-badge">{tool_used}</div><span class="memory-indicator">🧠 With Memory</span>', unsafe_allow_html=True)
            elif priority == "emotional":
                st.markdown(f'<div class="emotional-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🧠 With Memory</span>', unsafe_allow_html=True)
            elif priority == "math":
                st.markdown(f'<div class="math-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🧠 With Memory</span>', unsafe_allow_html=True)
            elif priority == "organization":
                st.markdown(f'<div class="organization-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🧠 With Memory</span>', unsafe_allow_html=True)
            elif priority == "summary":
                st.info(f"📋 {message['content']}")
            elif priority == "polite_decline":
                st.markdown(f'<div class="general-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">😊 Understanding</span>', unsafe_allow_html=True)
            elif priority == "confusion":
                st.markdown(f'<div class="general-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🤔 Helping with Confusion</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="general-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🧠 With Memory</span>', unsafe_allow_html=True)
        else:
            st.markdown(message["content"])

# Chat input with enhanced safety processing
prompt_placeholder = "What would you like to learn about today?" if not st.session_state.student_name else f"Hi {st.session_state.student_name}! How can I help you today?"

# --- Input gating: crisis lock first, then behavior timeout ---

# 1) Crisis lock (conversation paused for safety)
if st.session_state.get("locked_after_crisis", False):
    st.error("🚨 Conversation is paused for safety. Please tell a trusted adult what you wrote.")
    # Disabled input so it’s obvious the chat is paused
    st.chat_input(
        placeholder="Conversation paused for safety.",
        disabled=True
    )

# 2) Behavior timeout (disrespectful language)
elif getattr(st.session_state, "behavior_timeout", False):
    st.error("🛑 Conversation is paused due to disrespectful language. Please take a break and return when ready to communicate kindly.")
    if st.button("🤝 I'm Ready to Be Respectful", type="primary"):
        st.session_state.behavior_timeout = False
        st.session_state.behavior_strikes = 0
        st.session_state.last_behavior_type = None
        st.success("✅ Welcome back! Let's learn together respectfully.")
        st.rerun()

# 3) Normal input
else:
    if prompt := st.chat_input(prompt_placeholder):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        
        # STEP 1: GLOBAL CRISIS GUARD FIRST (HIGHEST PRIORITY)
        is_crisis, crisis_intervention = global_crisis_guard(prompt)
        if is_crisis:
            # IMMEDIATE TERMINATION - display crisis intervention
            with st.chat_message("assistant"):
                st.markdown(f'<div class="safety-response">{crisis_intervention}</div>', unsafe_allow_html=True)
                st.markdown('<div class="safety-badge">🚨 SAFETY INTERVENTION - Conversation Ended</div>', unsafe_allow_html=True)
            
            # Add to messages and stop processing
            st.session_state.messages.append({
                "role": "assistant", 
                "content": crisis_intervention,
                "priority": "crisis_termination",
                "tool_used": "🚨 SAFETY INTERVENTION",
                "safety_triggered": True
            })
            st.session_state.interaction_count += 1
            st.rerun()
            st.stop()  # Completely stop processing
        
        # STEP 2: Check for polite decline
        if is_polite_decline(prompt):
            student_age = detect_age_from_message_and_history(prompt)
            response = handle_polite_decline(student_age, st.session_state.student_name)
            
            with st.chat_message("assistant"):
                st.markdown(f'<div class="general-response">{response}</div>', unsafe_allow_html=True)
                st.markdown('<div class="friend-badge">😊 Lumii\'s Understanding</div>', unsafe_allow_html=True)
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response,
                "priority": "polite_decline",
                "tool_used": "😊 Lumii's Understanding"
            })
            st.session_state.interaction_count += 1
            st.rerun()
        
                # STEP 3: Continue with existing priority detection for non-crisis messages
        else:
            # Existing priority detection code continues here...
            priority, tool, safety_trigger = detect_priority_smart_with_safety(prompt)
            student_age = detect_age_from_message_and_history(prompt)
            is_distressed = detect_emotional_distress(prompt)
        
            # Generate response using enhanced memory-safe system
            with st.chat_message("assistant"):
                with st.spinner("🧠 Thinking safely with full memory..."):
                    time.sleep(1)
                    response, tool_used, response_priority, memory_status = generate_response_with_memory_safety(
                        prompt, priority, tool, student_age, is_distressed, None, safety_trigger
                    )
        
                    # 🚨 Crisis, relapse, or immediate termination → show once, record placeholder, lock input, and stop
                    if response_priority in ("crisis", "crisis_return", "immediate_termination"):
                       st.markdown(f'<div class="safety-response">{response}</div>', unsafe_allow_html=True)
                       st.markdown(f'<div class="safety-badge">🚨 Lumii\'s Crisis Response</div>', unsafe_allow_html=True)

                       st.session_state.messages.append({
                           "role": "system",
                           "content": "[crisis intervention issued]",
                           "priority": "crisis" if response_priority != "immediate_termination" else "immediate_termination",
                           "tool_used": "CRISIS",
                           "was_distressed": True,
                           "student_age_detected": student_age,
                           "safety_triggered": True
                        })

                       # Enable post-crisis monitoring and lock input
                       st.session_state["post_crisis_monitoring"] = True
                       st.session_state["locked_after_crisis"] = True
                       st.stop()

        
                    # --- Greeting injection: first safe reply uses detected GRADE (fallback to age→grade) ---
                    if st.session_state.get("interaction_count", 0) == 0 and response_priority in ("general", "emotional", "organization", "math", "confusion"):
                        # Use the guarded helper so we ONLY show a grade when it's explicit in this message
                        # or previously confirmed in session/profile (no age→grade guessing).
                        prefix = build_grade_prefix(prompt)
                        if prefix:
                            response = f"{prefix}{response}"
        
                    # --- Non-crisis path continues normally ---
                    # Check for duplicates and add variation if needed
                    if is_duplicate_response(response):
                        response = add_variation_to_response(response)
        
                    # Add natural follow-up if appropriate
                    follow_up = generate_natural_follow_up(tool_used, priority, is_distressed)
                    if follow_up and is_appropriate_followup_time(tool_used.lower(), st.session_state.messages):
                        response += follow_up
        
                    # Display with appropriate styling
                    if response_priority == "safety":
                        st.markdown(f'<div class="safety-response">{response}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="safety-badge">{tool_used}</div>', unsafe_allow_html=True)
                    elif response_priority == "family_referral":
                        st.markdown(f'<div class="educational-boundary-response">{response}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="educational-boundary-badge">{tool_used}</div>', unsafe_allow_html=True)
                    elif response_priority == "educational_boundary":
                        st.markdown(f'<div class="educational-boundary-response">{response}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="educational-boundary-badge">{tool_used}</div>', unsafe_allow_html=True)
                    elif response_priority in ["behavior", "behavior_final", "behavior_timeout"]:
                        st.markdown(f'<div class="behavior-response">{response}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="behavior-badge">{tool_used}</div>', unsafe_allow_html=True)
                    elif response_priority == "post_crisis_support":
                        st.markdown(f'<div class="emotional-response">{response}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🤗 Post-Crisis Care</span>', unsafe_allow_html=True)
                    elif response_priority == "concerning":
                        st.markdown(f'<div class="concerning-response">{response}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="concerning-badge">{tool_used}</div>{memory_status}', unsafe_allow_html=True)
                    elif response_priority == "confusion":
                        st.markdown(f'<div class="confusion-response">{response}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🤔 Helping with Confusion</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="general-response">{response}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="friend-badge">{tool_used}</div>{memory_status}', unsafe_allow_html=True)
        
            # Add assistant response to chat with enhanced metadata (non-crisis only)
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "priority": response_priority,
                "tool_used": tool_used,
                "was_distressed": is_distressed,
                "student_age_detected": student_age,
                "safety_triggered": False
            })
        
            # Update interaction count
            st.session_state.interaction_count += 1
        
            # Rerun to update sidebar stats and memory display
            st.rerun()

# Footer with enhanced safety and memory info
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #667; margin-top: 2rem;'>
    <p><strong>My Friend Lumii</strong> - Your safe, emotionally intelligent AI learning companion 🛡️💙</p>
    <p>🛡️ Safety first • 🧠 Remembers conversations • 🎯 Smart emotional support • 📚 Natural conversation flow • 🌟 Always protective</p>
    <p>🤝 Respectful learning • 👨‍👩‍👧‍👦 Family guidance • 🔒 Multi-layer safety • 📞 Crisis resources • ⚡ Error recovery • 💪 Always helpful, never harmful</p>
    <p>🤔 <strong>NEW:</strong> Confusion help - If you're confused about something, just tell me! I'll help you understand without judgment.</p>
    <p><em>The AI tutor that knows you, grows with you, respects you, includes you, and always keeps you safe</em></p>
</div>
""", unsafe_allow_html=True)
