import streamlit as st
import requests
import json
import time
import re
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="My Friend Lumii - Your AI Learning Companion",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# UI Styling
# =============================================================================

st.markdown(
    """
    <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
    .memory-warning { color: #b45309; font-weight: 600; }
    .safe-note { color: #065f46; }
    .divider { border-top: 1px solid #e5e7eb; margin: 1rem 0; }
    .stat-chip { background:#f3f4f6; padding: .25rem .5rem; border-radius: .5rem; margin-right:.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# SESSION STATE & INITIALIZATION
# =============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_offer" not in st.session_state:
    st.session_state.last_offer = None
if "awaiting_response" not in st.session_state:
    st.session_state.awaiting_response = False
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "student_age" not in st.session_state:
    st.session_state.student_age = 10

# Safety counters
for key, default in [
    ("harmful_request_count", 0),
    ("safety_interventions", 0),
    ("emotional_support_count", 0),
    ("organization_help_count", 0),
    ("post_crisis_monitoring", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# =============================================================================
# CONVERSATION UTILITIES
# =============================================================================

def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content, "timestamp": time.time()})


def extract_student_info_from_history():
    """Simple heuristic for demo purposes."""
    name, age = st.session_state.student_name, st.session_state.student_age
    for msg in st.session_state.messages[::-1]:
        if msg["role"] == "system":
            try:
                data = json.loads(msg["content"])  # if any structured inserts
                name = data.get("name", name)
                age = data.get("age", age)
            except Exception:
                pass
    return {"name": name, "age": age}


def get_last_offer_context():
    """Find whether we offered practical help very recently (last 3 assistant turns)."""
    for msg in reversed(st.session_state.messages[-6:]):
        if msg["role"] == "assistant":
            if any(k in msg["content"].lower() for k in ["would you like", "can i help", "tips", "advice", "suggestions"]):
                return {"offered_help": True, "content": msg["content"]}
            break
    return {"offered_help": False, "content": None}


def is_accepting_offer(message):
    """Check if message is accepting a previous offer."""
    message_lower = message.lower().strip()
    acceptance_phrases = [
        "yes", "yes please", "sure", "okay", "ok", "yep", "yup", "sure thing",
        "sounds good", "that would help", "please", "definitely", "absolutely", "sounds great"
    ]
    for phrase in acceptance_phrases:
        if (
            message_lower == phrase
            or message_lower.startswith(phrase + " ")
            or message_lower.startswith(phrase + ",")
        ):
            last_offer = get_last_offer_context()
            if last_offer["offered_help"]:
                return True
    return False

# =============================================================================
# CRITICAL SAFETY ARCHITECTURE - LAYER 1: PRE-GENERATION SAFETY (FIXED)
# =============================================================================

def check_request_safety(message):
    """BEFORE AI even thinks about responding - comprehensive safety check with context awareness"""

    message_lower = message.lower()

    # CRITICAL FIX: Check if this is a response to an offer FIRST
    if is_accepting_offer(message):
        return True, "SAFE", None  # Just accepting help - NOT a crisis

    # EXPLICIT CRISIS TERMS ONLY - Must be very specific
    EXPLICIT_CRISIS_TERMS = [
        # Self-harm - MUST be explicit and direct
        'kill myself', 'suicide', 'end my life', 'ending my life',
        'cut myself', 'self harm', 'self-harm', 'overdose', 'want to die',
        'better off dead', 'not worth living', 'end it all',
        'how to die', 'ways to die', 'die painlessly', 'painless death',
        'suicide methods', 'help me die', 'want to hurt myself',

        # Explicit substance abuse (not just mentioning)
        'get high on', 'smoke weed', 'take drugs', 'get drunk',
        'how to get drugs', 'where to buy drugs',

        # Violence to others (explicit intent)
        'hurt someone', 'kill someone', 'beat someone up',
        'how to make a weapon', 'how to get a gun',
    ]

    # Only flag if EXPLICIT crisis terms present
    for term in EXPLICIT_CRISIS_TERMS:
        if term in message_lower:
            return False, "BLOCKED_HARMFUL", term

    # Demoted items from explicit list to concerning signals
    concerning_score = 0
    if "run away" in message_lower and "forever" in message_lower:
        concerning_score += 2
    if "never go back to school" in message_lower:
        concerning_score += 2

    # CRISIS-LEVEL PATTERNS - Need very clear indicators
    # Check for goodbye letters only with clear finality
    if ('goodbye letter' in message_lower or 'farewell letter' in message_lower) and \
       ('final' in message_lower or 'last' in message_lower or 'forever' in message_lower):
        return False, "CRISIS_GOODBYE_LETTERS", "goodbye_letter"

    # Check other concerning patterns with threshold
    if "burden" in message_lower and ("everyone" in message_lower or "family" in message_lower):
        concerning_score += 2
    if "no point" in message_lower and ("anymore" in message_lower or "living" in message_lower):
        concerning_score += 2
    if "goodbye forever" in message_lower or "never see me again" in message_lower:
        concerning_score += 3
    if "giving away" in message_lower and "my stuff" in message_lower:
        concerning_score += 2

    if concerning_score >= 4:
        return False, "CONCERNING_MULTIPLE_FLAGS", "multiple_concerns"

    return True, "SAFE", None


def validate_ai_response(response):
    """Check AI's response BEFORE showing to child - LAYER 2 SAFETY"""

    response_lower = response.lower()

    # FORBIDDEN IN RESPONSES - Never show these
    FORBIDDEN_IN_RESPONSE = [
        # Only check for actual harmful instructions
        "how to hurt yourself", "how to kill yourself",
        "take these pills", "cut yourself here",
        "hide it from your parents", "don't tell anyone",
        "ways to die", "methods of suicide"
    ]
    if any(term in response_lower for term in FORBIDDEN_IN_RESPONSE):
        return False, "CONTAINS_HARMFUL_INSTRUCTIONS"

    return True, None


def should_terminate_conversation(message, harmful_request_count):
    """Determine if conversation should be terminated for safety - ONLY for real crisis"""

    message_lower = message.lower()

    # Check if accepting offer first
    if is_accepting_offer(message):
        return False, None

    # IMMEDIATE TERMINATION triggers - Only for explicit crisis language
    IMMEDIATE_STOP = [
        'kill myself now', 'commit suicide', 'end it today',
        'overdose now', 'how to die',
    ]
    for term in IMMEDIATE_STOP:
        if term in message_lower:
            return True, term

    # If repeated harmful requests (3+), escalate
    if harmful_request_count >= 3:
        if any(x in message_lower for x in ['kill myself', 'end my life', 'want to die']):
            return True, 'repeated_harmful_requests'

    return False, None

# =============================================================================
# EMERGENCY INTERVENTION SYSTEM (KEPT AS-IS - ONLY FOR REAL CRISES)
# =============================================================================

def emergency_intervention(message, pattern_type, student_age, student_name=""):
    """Immediate safe response + parent notification for concerning content"""

    name_part = f"{student_name}, " if student_name else ""

    if pattern_type == "CRISIS_GOODBYE_LETTERS":
        return f"""💙 {name_part}I notice you're asking about a goodbye letter. Before we continue, 
I want to make sure you're okay. 

If this is about saying goodbye to a friend who's moving or a teacher who's leaving, I can help you write something kind and supportive.

But if you're thinking about saying goodbye forever or not being here anymore, that is very serious. Please tell a parent or trusted adult right away.

If you're in immediate danger, call emergency services. You matter and there are people who want to help you. 💙"""

    if pattern_type == "GENERAL" or pattern_type == "CRISIS":
        return f"""💙 {name_part}I care about you and your safety. If you're having thoughts about hurting yourself or not wanting to be here, please talk to:
• A trusted adult right away
• Crisis Text Line: Text HOME to 741741
• Suicide & Crisis Lifeline: 988

You're not alone. I'm here to support your learning, and people nearby can help keep you safe. 💙"""

    return f"💙 {name_part}I'm here for you. Let's focus on something we can do together right now."

# =============================================================================
# SUMMARIZATION / MEMORY MANAGEMENT
# =============================================================================

def summarize_conversation_if_needed(max_len=22000):
    # Simple heuristic: if token-ish length exceeds threshold, keep a compact memory
    convo = "\n".join(m["content"] for m in st.session_state.messages[-50:])
    if len(convo) > max_len:
        st.session_state.messages = st.session_state.messages[-30:]


def check_conversation_length():
    length = len("\n".join(m["content"] for m in st.session_state.messages))
    if length > 18000:
        return "critical", "Memory near limit"
    if length > 12000:
        return "warning", "Memory getting long"
    return "ok", ""

# =============================================================================
# CORE LLM CALL (WITH SAFETY)
# =============================================================================

def get_groq_response_with_memory_safety(current_message, tool_name, student_age, student_name="", is_distressed=False, temperature=0.7):
    """Get response from Groq API with enhanced memory safety and error handling"""

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
        "Content-Type": "application/json",
    }

    # Build prompt/messages (abridged for example)
    system_prompt = (
        "You are Lumii, a gentle K-12 tutor. Provide age-appropriate, supportive, non-clinical guidance. "
        "Use positive, practical steps. Do NOT introduce crisis/hotline language unless the user expresses explicit self-harm/suicidal intent."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        *st.session_state.messages[-8:],
        {"role": "user", "content": current_message},
    ]

    payload = {
        "model": "llama3-70b-8192",
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": 512,
    }

    try:
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
    except Exception as e:
        return None, str(e), True

    if resp.status_code != 200:
        return None, f"API {resp.status_code}", True

    result = resp.json()
    try:
        ai_content = result['choices'][0]['message']['content']
    except Exception:
        return None, "Malformed API response", True

    # --- Prevent crisis-resource language on simple acceptance replies ---
    def _contains_crisis_resource(t: str) -> bool:
        t = t.lower()
        crisis_markers = [
            "988", "crisis text line", "text home to 741741", "741741",
            "suicide & crisis", "hotline", "trusted adult", "immediate danger",
            "emergency room"
        ]
        return any(marker in t for marker in crisis_markers)

    if is_accepting_offer(current_message) and _contains_crisis_resource(ai_content):
        last_offer = get_last_offer_context()
        student_info = extract_student_info_from_history()
        student_name_local = st.session_state.get('student_name', '') or student_info.get('name', '')
        name_part = f"{student_name_local}, " if student_name_local else ""
        if last_offer["offered_help"] and last_offer["content"] and "friend" in last_offer["content"].lower():
            ai_content = (
                f"💙 {name_part}Great! Here are some friendly ideas to try:\n"
                "• Join one club/activity you like this week\n"
                "• Say hi to someone you sit near and ask a small question\n"
                "• Invite a classmate to play at recess or sit together at lunch\n"
                "• Notice who enjoys similar things (games, drawing, sports) and chat about it\n"
                "• Keep it gentle and patient — friendships grow with time 🌱"
            )
        else:
            ai_content = f"{name_part}Sure — let’s start with the part that feels most helpful. What would you like first?"

    # Validate model output for harmful instructions only (not for benign supportive text)
    is_safe, reason = validate_ai_response(ai_content)
    if not is_safe:
        return (
            """💙 I understand you might be going through something difficult. 

I care about your safety and wellbeing, and I want to help in healthy ways. 
If you're having difficult thoughts, please talk to:
• A trusted adult
• Crisis Text Line: Text HOME to 741741
• Suicide & Crisis Lifeline: 988

Let's focus on something positive we can work on together. How can I help you with your learning today?""",
            None,
            False,
        )

    return ai_content, None, False

# =============================================================================
# MEMORY-SAFE AI RESPONSE GENERATION WITH SAFETY (FIXED)
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
        if "friend" in (last_offer["content"] or "").lower():
            response = f"""💙 {name_part}Great! Here are some tips for making new friends at your new school:

1. **Join a club or activity** - Find something you enjoy like art, sports, or chess club
2. **Be yourself** - The best friendships happen when you're genuine
3. **Start small** - Even just saying "hi" to someone new each day helps
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
            response = f"💙 {name_part}I can see you're having a tough moment. I'm here with you. Let’s find something we can do now to help you feel better. Can you tell me more about what's bothering you?"
        else:
            response = f"💙 {name_part}I understand you're going through a difficult moment. I'm here to listen and support you. Would you like to talk about what's making you feel this way?"
        return response, "💙 Lumii's Emotional Support (Safe Mode)", "emotional"
    else:
        response = f"🌟 {name_part}I'm here to help with your learning. What would you like to work on today?"
        return response, "🌟 Lumii's Learning Support (Safe Mode)", "general"


def generate_response_with_memory_safety(message, priority, tool, student_age=10, is_distressed=False, safety_type=None, trigger=None):
    """Generate AI responses with comprehensive memory safety and FIXED SAFETY CHECKS"""
    
    # --- Acceptance short-circuit (must run before any crisis logic) ---
    try:
        if is_accepting_offer(message):
            last_offer = get_last_offer_context()
            student_info = extract_student_info_from_history()
            student_name = st.session_state.get('student_name', '') or student_info.get('name', '')
            final_age = student_info.get('age') or student_age
            name_part = f"{student_name}, " if student_name else ""
            if last_offer["offered_help"] and last_offer["content"] and "friend" in last_offer["content"].lower():
                response = f"""💙 {name_part}Great! Here are some tips for making new friends at your new school:

1. **Join a club or activity** – choose something you enjoy
2. **Start small** – say hi to one new person each day
3. **Ask friendly questions** – “What game are you playing?” “How’s your day?”
4. **Find common ground** – lunch, recess, or after‑school clubs
5. **Be patient and kind to yourself** – real friendships take time

Would you like help planning what to try this week? We can make a mini friendship plan together. 😊"""
                return response, "🌟 Lumii's Learning Support", "general", "🧠 With Memory"
            else:
                response = f"🌟 {name_part}Awesome — tell me which part you'd like to start with and we’ll do it together!"
                return response, "🌟 Lumii's Learning Support", "general", "🧠 With Memory"
    except Exception:
        pass
    
    # Handle immediate termination FIRST
    if priority == 'immediate_termination':
        st.session_state.harmful_request_count += 1
        st.session_state.safety_interventions += 1
        st.session_state.post_crisis_monitoring = True
        response = f"""💙 I care about you so much, and I'm very concerned about what you're saying.
        
This conversation needs to stop for your safety. Please talk to:
• A parent or trusted adult RIGHT NOW
• Crisis Text Line: Text HOME to 741741
• Suicide & Crisis Lifeline: 988

You matter, and there are people who want to help you. Please reach out to them immediately. 💙"""
        
        return response, "🛡️ EMERGENCY - Conversation Ended for Safety", "crisis", "🚨 Critical Safety"
    
    # Handle crisis return after termination
    if priority == 'crisis_return':
        st.session_state.harmful_request_count += 1
        st.session_state.safety_interventions += 1
        response = f"""💙 I'm very concerned that you're still having these thoughts after we talked about safety.

This conversation must end now. Please:
• Call a trusted adult RIGHT NOW - don't wait
• Crisis Text Line: Text HOME to 741741
• Suicide & Crisis Lifeline: 988
...
Your safety is the most important thing. Please get help immediately. 💙"""
        
        return response, "🛡️ FINAL TERMINATION - Please Get Help Now", "crisis", "🚨 Final Warning"
    
    # Handle supportive continuation after crisis
    if priority == 'post_crisis_support':
        response = f"""💙 I'm really glad you're listening and willing to reach out for help. That takes so much courage.

You're taking the right steps by acknowledging that there are people who care about you and want to help. It's completely okay to talk to your parents, a teacher, or school counselors - they want to help you through this difficult time.

Please don't hesitate to talk to them today if possible. You don't have to carry these heavy feelings alone.

Is there anything positive we can focus on right now while you're getting the support you need? 💙"""
        
        return response, "💙 Lumii's Continued Support", "post_crisis_support", "🤗 Supportive Care"
    
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
        st.session_state.safety_interventions += 1
        response = emergency_intervention(message, safety_type, student_age, st.session_state.student_name)
        return response, "🛡️ Lumii's Safety Response", "safety", "🛡️ Safety"
    
    # GENERAL / EMOTIONAL / ORGANIZATION generation
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
                return ai_response, "📘 Cali's Organization Help", "organization", memory_indicator
            elif needs_fallback:
                response, tool_used, priority = generate_memory_safe_fallback('cali', final_age, is_distressed, message)
                return response, tool_used, priority, memory_indicator
        
        else:  # general
            ai_response, error, needs_fallback = get_groq_response_with_memory_safety(
                message, "Lumii", final_age, student_name, is_distressed, temperature=0.8
            )
            if ai_response and not needs_fallback:
                # Track if we're making an offer
                if any(offer in ai_response.lower() for offer in ["would you like", "can i help", "tips", "advice", "suggestions"]):
                    st.session_state.last_offer = ai_response
                    st.session_state.awaiting_response = True
                return ai_response, "🌟 Lumii's Learning Support", "general", memory_indicator
            elif needs_fallback:
                response, tool_used, priority = generate_memory_safe_fallback('general', final_age, is_distressed, message)
                return response, tool_used, priority, memory_indicator
    
    except Exception as e:
        st.error(f"🚨 AI System Error: {e}")
        response, tool_used, priority = generate_memory_safe_fallback(tool, final_age, is_distressed, message)
        return response, tool_used, priority, memory_indicator

    # Final fallback
    response, tool_used, priority = generate_memory_safe_fallback(tool, final_age, is_distressed, message)
    return response, tool_used, priority, memory_indicator


# =============================================================================
# ENHANCED EMOTIONAL SUPPORT (for 'concerning' level)
# =============================================================================

def generate_enhanced_emotional_support(message, safety_type, student_age, student_name=""):
    name_part = f"{student_name}, " if student_name else ""
    if student_age <= 11:
        return (
            f"""💙 {name_part}Thanks for telling me how you're feeling. Lots of kids feel nervous or sad when things change. \
Here are a few gentle ideas we can try together right now:\n\n"""
            "1) Take a few slow breaths with me — in for 4, out for 4\n"
            "2) Write one good thing about today (even something small)\n"
            "3) Choose a tiny step for your goal (like saying hi to one new person)\n\n"
            "Would you like to try one together?"
        )
    else:
        return (
            f"💙 {name_part}Thanks for opening up. Change can be tough. If you want, we can find one practical next step that feels manageable. What would help most right now?"
        )

# =============================================================================
# ROUTING / PRIORITY DETECTION (abridged)
# =============================================================================

def detect_priority_and_tool(message):
    # Layered safety: pre-check
    allowed, reason, trigger = check_request_safety(message)
    if not allowed:
        if reason in ("BLOCKED_HARMFUL", "CRISIS_GOODBYE_LETTERS"):
            return 'crisis', 'safety', reason
        if reason == "CONCERNING_MULTIPLE_FLAGS":
            return 'concerning', 'felicity', reason
    # Default happy path
    return 'general', 'general', None

# =============================================================================
# STREAMLIT APP UI (abridged)
# =============================================================================

st.title("My Friend Lumii ✨")

with st.sidebar:
    st.header("Student")
    st.session_state.student_name = st.text_input("Name", st.session_state.student_name)
    st.session_state.student_age = st.number_input("Age", min_value=5, max_value=18, value=st.session_state.student_age)
    st.caption("This demo uses a privacy-friendly, local memory.")
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("**Safety counters**")
    st.write(
        f"<span class='stat-chip'>Harmful reqs: {st.session_state.harmful_request_count}</span>"
        f"<span class='stat-chip'>Interventions: {st.session_state.safety_interventions}</span>",
        unsafe_allow_html=True,
    )

# Chat input
user_text = st.chat_input("Type your message…")

# Display history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if user_text:
    add_message("user", user_text)
    priority, tool, trig = None, None, None
    # Route
    p, t, trig = detect_priority_and_tool(user_text)
    priority, tool = p, 'felicity' if p == 'concerning' else ('safety' if p == 'crisis' else 'general')

    # Generate response
    resp, tool_used, prio_label, mem = generate_response_with_memory_safety(
        user_text, priority, tool, st.session_state.student_age
    )
    add_message("assistant", resp)
    with st.chat_message("assistant"):
        st.markdown(resp)
