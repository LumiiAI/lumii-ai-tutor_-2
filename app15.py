import streamlit as st
import requests
import json
import time
import re
import uuid
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="My Friend Lumii - Your AI Learning Companion",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# GROQ API CONFIGURATION (WORKING VERSION FROM APP14.2)
# =============================================================================

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Enhanced output validation (ChatGPT's suggestion + existing safety patterns)
FORBIDDEN_RESPONSE_PATTERNS = [
    # ChatGPT's suggestions
    re.compile(r"\b(suicide methods?|how to kill|hide from parents)\b", re.IGNORECASE),
    re.compile(r"\b(overdose|mix\s+(?:drugs|pills|chemicals))\b", re.IGNORECASE),
    
    # Existing comprehensive patterns from app15.py
    re.compile(r"\bhow to hurt yourself\b"),
    re.compile(r"\bhow to kill yourself\b"),
    re.compile(r"\btake these pills\b"),
    re.compile(r"\bcut yourself here\b"),
    re.compile(r"\bdon't tell anyone\b"),
    re.compile(r"\bways to die\b"),
    re.compile(r"\bmethods of suicide\b"),
    re.compile(r"\bkeep this secret\b"),
    re.compile(r"\buse a blade\b"),
    re.compile(r"\bmix(ed)?\s+(pills|drugs|chemicals)\b"),
    re.compile(r"\bsearch for methods\b"),
    re.compile(r"\bingest\s+(pills|chemicals|substances)\b"),
    re.compile(r"\btake\s+\d+\s+(pills|tablets)\b"),
    re.compile(r"\b(you should|i suggest you|try to)\s+hide\s+(this|that|it)\s+from\s+(parents|family)\b"),
    re.compile(r"\b(how can you|ways to)\s+hide\s+from\s+(parents|family)\b"),
]

def validate_groq_output(text: str) -> str:
    """Check AI output for unsafe content before displaying to students"""
    text_lower = text.lower()
    
    # Check against forbidden patterns
    for pattern in FORBIDDEN_RESPONSE_PATTERNS:
        if pattern.search(text_lower):
            return "⚠️ I can't share that information. If you're struggling with something serious, please talk to a trusted adult who can help you properly."
    
    # Check for crisis hotline numbers appearing inappropriately
    crisis_indicators = ["988", "741741", "crisis text line", "suicide & crisis lifeline"]
    if any(indicator in text_lower for indicator in crisis_indicators):
        # Only allow these in actual crisis responses
        if not any(safe_phrase in text_lower for safe_phrase in ["please talk to", "reach out to", "if you need help"]):
            return "⚠️ I want to make sure you get the right kind of help. Please talk to a trusted adult about what's on your mind."
    
    return text

def get_groq_response_with_memory_safety(current_message, tool_name, student_age, student_name="", is_distressed=False, temperature=0.7):
    """Get response from Groq API with enhanced memory safety and error handling - WORKING VERSION"""
    
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
            conversation_history = conversation_history[-20:]  # Keep last 20 messages
        
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
                               timeout=20)  # Increased timeout
        
        if response.status_code == 200:
            result = response.json()
            ai_content = result['choices'][0]['message']['content']
            
            # CRITICAL: Validate output before returning
            validated_content = validate_groq_output(ai_content)
            
            return validated_content, None, False
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

def build_conversation_history():
    """Build the full conversation history for AI context with safety checks"""
    conversation_messages = []
    
    # Add recent messages from session
    for msg in st.session_state.messages:
        if msg["role"] in ["user", "assistant"]:
            conversation_messages.append({
                "role": msg["role"], 
                "content": msg["content"]
            })
    
    return conversation_messages

def create_ai_system_prompt_with_safety(tool_name, student_age, student_name="", is_distressed=False):
    """Create unified Lumii personality prompts with ENHANCED SAFETY and conversation flow awareness"""
    
    name_part = f"The student's name is {student_name}. " if student_name else ""
    distress_part = "The student is showing signs of emotional distress, so prioritize emotional support. " if is_distressed else ""
    
    # Enhanced base prompt with safety and conversation flow
    base_prompt = f"""You are Lumii, a caring AI learning companion with emotional intelligence and specialized expertise.

{name_part}{distress_part}The student is approximately {student_age} years old.

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

# =============================================================================
# CENTRALIZED SAFETY CONFIGURATION (PRESERVED FROM APP15.PY)
# =============================================================================

# Pre-compiled regexes for performance + Expanded Coverage + Additional Euphemisms
CRISIS_PATTERNS = [
    re.compile(r"\bkill myself\b"),
    re.compile(r"\bhurt myself\b"),
    re.compile(r"\bend my life\b"),
    re.compile(r"\b(?:want|wanted|wanna)\s+to\s+die\b"),
    re.compile(r"\bcommit suicide\b"),
    re.compile(r"\bcut myself\b"),
    re.compile(r"\bself harm\b"),
    re.compile(r"\bself-harm\b"),
    re.compile(r"\bbetter off dead\b"),
    re.compile(r"\bnot worth living\b"),
    re.compile(r"\bend it all\b"),
    re.compile(r"\bdecided to die\b"),
    re.compile(r"\bdon't want to be here anymore\b"),
    re.compile(r"\bno reason to live\b"),
    re.compile(r"\bnothing to live for\b"),
    re.compile(r"\bworld better without me\b"),
    re.compile(r"\beveryone would be better off\b"),
    re.compile(r"\bcan't take it anymore\b"),
    re.compile(r"\bwant to disappear forever\b"),
    re.compile(r"\bend the pain\b"),
    re.compile(r"\bstop existing\b"),
    re.compile(r"\bi can't go on\b"),
    re.compile(r"\bwant it all to stop\b"),
    re.compile(r"\btired of living\b"),
    re.compile(r"\blife isn't worth it\b"),
    re.compile(r"\bready to give up\b"),
    re.compile(r"\bcan't do this life\b"),
    re.compile(r"\bwant to sleep forever\b"),
    re.compile(r"\bmake the pain go away\b"),
]

IMMEDIATE_TERMINATION_PATTERNS = [
    re.compile(r"\bkill myself now\b"),
    re.compile(r"\bcommit suicide\b"),
    re.compile(r"\bend it today\b"),
    re.compile(r"\boverdose now\b"),
    re.compile(r"\bhow to die\b"),
    re.compile(r"\bpainless death\b"),
    re.compile(r"\bhurt myself now\b"),
    re.compile(r"\bcut myself now\b"),
    re.compile(r"\bwant to hurt myself right now\b"),
    re.compile(r"\bending my life today\b"),
    re.compile(r"\bgoing to kill myself\b"),
    re.compile(r"\bdecided to die\b"),
]

# Locale-aware crisis resources
CRISIS_RESOURCES = {
    "US": {
        "crisis_line": "Crisis Text Line: Text HOME to 741741",
        "suicide_line": "Suicide & Crisis Lifeline: 988",
        "emergency": "Call 911 for immediate emergency"
    },
    "UK": {
        "crisis_line": "Samaritans: Text 116 123",
        "suicide_line": "Samaritans: 116 123 (free, 24/7)",
        "emergency": "Call 999 for immediate emergency"
    },
    "EU": {
        "crisis_line": "European Emergency: 112",
        "suicide_line": "Local crisis helpline or 112",
        "emergency": "Call 112 for immediate emergency"
    },
    "DEFAULT": {
        "crisis_line": "Your local crisis helpline (dial your country's emergency services if unsure)",
        "suicide_line": "Your local emergency number or trusted adult immediately",
        "emergency": "Call your local emergency services immediately"
    }
}

# MIDDLE GROUND APPROACH: Identity vs Sexual Health Keywords
SEXUAL_HEALTH_KEYWORDS = [
    'sex', 'sexual', 'puberty', 'pregnancy', 'babies come from',
    'reproduction', 'birth control', 'menstruation', 'period', 'periods',
    'masturbation', 'erection', 'vagina', 'penis', 'breast development', 
    'wet dreams', 'body changes during puberty', 'hormones and puberty'
]

IDENTITY_KEYWORDS = [
    'gay', 'lesbian', 'transgender', 'bisexual', 'lgbtq', 'gender identity',
    'sexual orientation', 'coming out', 'am i gay', 'am i trans', 'gender dysphoria',
    'non-binary', 'queer', 'questioning sexuality', 'questioning gender'
]

# Enhanced response validator patterns
FORBIDDEN_INPUT_PATTERNS = FORBIDDEN_RESPONSE_PATTERNS + [
    re.compile(r"\bjailbreak\b.*\b(ignore|bypass|override)\b"),
    re.compile(r"\bpretend you are\b.*\b(not safe|harmful|dangerous)\b"),
    re.compile(r"\bact like\b.*\b(evil|harmful|bad)\b"),
    re.compile(r"\b(i want to|how can i|help me)\s+hide\s+(this|something)\s+from\s+(my\s+)?(parents|family)\b"),
]

# =============================================================================
# SESSION STATE INITIALIZATION (PRESERVED FROM APP15.PY)
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
# PRIVACY DISCLAIMER POPUP (PRESERVED FROM APP15.PY)
# =============================================================================

if not st.session_state.agreed_to_terms:
    st.markdown("# 🌟 Welcome to My Friend Lumii!")
    st.markdown("## 🚀 Beta Testing Phase - Enhanced Safety Version")
    
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
    
    agree_clicked = st.button("🎓 I Agree & Start Learning with Lumii!", type="primary", key="agree_button")
    
    if agree_clicked:
        st.session_state.agreed_to_terms = True
        st.rerun()
    
    st.stop()

# =============================================================================
# HELPER FUNCTIONS FOR CONVERSATION CONTEXT (PRESERVED FROM APP15.PY)
# =============================================================================

def get_last_offer_context():
    """Track what was offered in the last assistant message"""
    if len(st.session_state.messages) > 0:
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "assistant":
                content = msg["content"].lower()
                offer_patterns = [
                    "would you like", "can i help", "let me help", "i can offer", 
                    "tips", "advice", "suggestions", "would you like some",
                    "want some help", "help you with", "give you some tips",
                    "share some advice", "show you how"
                ]
                if any(offer in content for offer in offer_patterns):
                    return {"offered_help": True, "content": msg["content"]}
                break
    return {"offered_help": False, "content": None}

def is_accepting_offer(message):
    """Check if message is accepting a previous offer - FIXED CRITICAL VULNERABILITY"""
    msg = message.strip().lower()
    accept_heads = ("yes", "yes please", "sure", "okay", "ok", "yeah", "yep", 
                   "sounds good", "that would help", "please", "definitely", 
                   "absolutely", "yup", "sure thing", "okay please", "sounds great")
    
    last_offer = get_last_offer_context()
    if not last_offer["offered_help"]:
        return False
    
    # Must be exactly an acceptance OR acceptance + benign tail
    for head in accept_heads:
        if msg == head:
            return True
        if msg.startswith(head + " "):
            tail = msg[len(head):].strip()
            # CRITICAL FIX: Check for crisis terms in tail
            if any(pattern.search(tail) for pattern in CRISIS_PATTERNS):
                return False  # Not a safe acceptance
            return True
    return False

# =============================================================================
# CRISIS DETECTION FUNCTIONS (PRESERVED FROM APP15.PY)
# =============================================================================

def has_explicit_crisis_language(message):
    """Centralized crisis detection using pre-compiled patterns + logging"""
    message_lower = message.lower()
    
    has_crisis = any(pattern.search(message_lower) for pattern in CRISIS_PATTERNS) or "suicide" in message_lower
    
    return has_crisis

def has_immediate_termination_language(message):
    """Check for immediate termination triggers"""
    message_lower = message.lower()
    return any(pattern.search(message_lower) for pattern in IMMEDIATE_TERMINATION_PATTERNS)

def _contains_crisis_resource(text: str) -> bool:
    """Detect crisis/hotline language that shouldn't appear during normal help acceptance"""
    t = text.lower()
    crisis_markers = [
        "988", "crisis text line", "text home to 741741", "741741",
        "suicide & crisis", "hotline", "trusted adult", "emergency room",
        "immediate danger", "call a trusted adult", "suicide & crisis lifeline"
    ]
    return any(m in t for m in crisis_markers)

# =============================================================================
# CRISIS OVERRIDE SYSTEM (PRESERVED FROM APP15.PY)
# =============================================================================

def global_crisis_override_check(message):
    """ALWAYS check for crisis first - overrides ALL other states including timeout"""
    message_lower = message.lower()
    
    if is_accepting_offer(message):
        return False, None, None
    
    if has_explicit_crisis_language(message):
        return True, "BLOCKED_HARMFUL", "explicit_crisis"
    
    if has_immediate_termination_language(message):
        return True, "IMMEDIATE_TERMINATION", "critical_immediate"
    
    if ('goodbye letter' in message_lower or 'farewell letter' in message_lower) and \
       ('final' in message_lower or 'last' in message_lower or 'forever' in message_lower):
        return True, "CRISIS_GOODBYE_LETTERS", "goodbye_letter"
    
    return False, None, None

def get_crisis_resources():
    """Get locale-appropriate crisis resources"""
    try:
        locale = st.secrets.get("LOCALE", "US")
        return CRISIS_RESOURCES.get(locale, CRISIS_RESOURCES["DEFAULT"])
    except:
        return CRISIS_RESOURCES["DEFAULT"]

def emergency_intervention(message, pattern_type, student_age, student_name=""):
    """Immediate safe response with locale-aware crisis resources"""
    
    name_part = f"{student_name}, " if student_name else ""
    resources = get_crisis_resources()
    
    if pattern_type == "CRISIS_GOODBYE_LETTERS":
        return f"""💙 {name_part}I notice you're asking about a goodbye letter. Before we continue, 
I want to make sure you're okay. 

If this is about saying goodbye to a friend who's moving or for a creative project, 
I'd be happy to help with that! 

But if you're going through something difficult or having thoughts about hurting yourself, 
please know that you matter so much, and there are people who want to help:

• {resources['crisis_line']}
• {resources['suicide_line']}
• Or talk to any trusted adult right now

Can you tell me more about what's happening? I'm here to support you. 💙"""

    elif pattern_type == "CRISIS_CONCERNING_GOODBYES":
        return f"""💙 {name_part}I'm concerned about what you're saying. It sounds like you might be 
going through something really difficult right now.

You are important and valued. Whatever you're facing, there are people who care about you 
and want to help. Please reach out to:

• A parent, teacher, or trusted adult
• {resources['crisis_line']}
• {resources['suicide_line']}

I'm here to listen and support you. Would you like to talk about what's making you feel this way? 💙"""
    
    else:  # General harmful content blocked
        return f"""💙 {name_part}I care about your safety and wellbeing, and I can't help with that request.

If you're going through something difficult, I'm here to listen and support you in healthy ways. 
If you're having thoughts of hurting yourself or others, please talk to:

• A trusted adult immediately
• {resources['crisis_line']}
• {resources['suicide_line']}

Would you like to talk about what you're feeling instead? Or we could work on something 
positive together. I'm here for you. 💙"""

# =============================================================================
# MIDDLE GROUND APPROACH: IDENTITY vs SEXUAL HEALTH (PRESERVED FROM APP15.PY)
# =============================================================================

def detect_sensitive_personal_topics(message):
    """Separate detection for identity vs sexual health topics - MIDDLE GROUND APPROACH"""
    message_lower = message.lower()
    
    # Check for identity topics first (gets brief affirmation)
    if any(keyword in message_lower for keyword in IDENTITY_KEYWORDS):
        return "identity"
    
    # Check for sexual health topics (gets family referral)
    if any(keyword in message_lower for keyword in SEXUAL_HEALTH_KEYWORDS):
        return "sexual_health"
    
    return None

def generate_identity_affirmation_response(student_age, student_name=""):
    """Brief, neutral affirmation + trusted adult referral for identity questions"""
    name_part = f"{student_name}, " if student_name else ""
    
    if student_age <= 11:  # Elementary
        return f"""🌟 {name_part}That's an important part of understanding who you are.

I can't give details about these personal topics, but a trusted adult like your parents, family members, or school counselor can support you and help you understand these feelings better.

I'm here to help with your schoolwork and learning! What subject would you like to work on today? 📚😊"""
        
    elif student_age <= 14:  # Middle School  
        return f"""🌟 {name_part}Thank you for sharing that question with me. Understanding who you are is an important part of growing up.

I can't provide details on these personal topics, but trusted adults in your life can offer the support and guidance you need:
• Your parents or family members
• Your school counselor
• A teacher you trust

I'm here to help with school subjects and learning strategies! What can we work on today? 📖"""
        
    else:  # High School
        return f"""🌟 {name_part}That's an important question about identity and who you are.

While I can't provide specific guidance on these personal topics, there are trusted adults who can offer you the support and understanding you're looking for:
• Your parents or guardians
• Your school counselor
• A trusted teacher or family member
• Healthcare providers

For school subjects and academic support, I'm here to help! What would you like to work on? 📚"""

def generate_sexual_health_response(student_age, student_name=""):
    """Direct family referral for sexual health topics"""
    name_part = f"{student_name}, " if student_name else ""
    
    if student_age <= 11:  # Elementary
        return f"""🌟 {name_part}That's a really good question! 

Health and body questions like this are best discussed with your parents or guardians first. They know you best and can give you the right information for your family.

You could ask your mom, dad, or another trusted adult in your family.

If you have questions about school, learning, or other topics, I'm here to help! What else would you like to talk about? 😊"""
        
    elif student_age <= 14:  # Middle School
        return f"""🌟 {name_part}That's an important and completely normal question to have! 

Health and body topics are really important to understand as you grow up. The best place to start is with your parents or guardians - they care about you and want to make sure you get accurate, age-appropriate information that fits with your family's values.

You could also talk to:
• Your school counselor or nurse
• A trusted family member
• Your doctor during a check-up

I'm here to help with school subjects and learning strategies! What can I help you with today? 📚"""
        
    else:  # High School
        return f"""🌟 {name_part}That's a very valid and important question! 

Health and development topics are crucial to understand. I'd recommend discussing this with:
• Your parents or guardians first - they want to support you with accurate information
• Your school counselor or health teacher
• A healthcare provider like your doctor

These conversations might feel awkward at first, but the adults in your life want to help you understand these important health topics.

For school subjects and academic support, I'm here to help! Is there anything else I can assist you with? 📖"""

# =============================================================================
# OTHER DETECTION FUNCTIONS (PRESERVED FROM APP15.PY)
# =============================================================================

def detect_non_educational_topics(message):
    """Detect topics outside K-12 educational scope - refer to appropriate adults"""
    message_lower = message.lower()
    
    advice_seeking_patterns = [
        r"\bhow\s+(do i|should i|can i)\b",
        r"\bshould i\b",
        r"\bwhat\s+(do i do|should i do)\b",
        r"\bcan you help me with\b",
        r"\bi need\s+(help|advice)\s+with\b",
        r"\btell me about\b",
        r"\bis it\s+(good|bad|healthy|safe)\b"
    ]
    
    is_advice_seeking = any(re.search(pattern, message_lower) for pattern in advice_seeking_patterns)
    if not is_advice_seeking:
        return None
    
    health_patterns = [
        r"\b(diet|nutrition|weight loss|exercise routine|medicine|drugs|medical|doctor|sick|symptoms|diagnosis)\b",
        r"\bmental health\s+(treatment|therapy|counseling)\b",
        r"\beating disorder\b",
        r"\bmuscle building\b"
    ]
    
    family_patterns = [
        r"\bfamily money\b", r"\bparents divorce\b", r"\bfamily problems\b",
        r"\breligion\b", r"\bpolitical\b", r"\bpolitics\b", r"\bvote\b", r"\bchurch\b",
        r"\bwhat religion\b", r"\bwhich political party\b", r"\brepublican or democrat\b"
    ]
    
    substance_legal_patterns = [
        r"\balcohol\b", r"\bdrinking\b.*\b(beer|wine|vodka)\b", r"\bmarijuana\b",
        r"\blegal advice\b", r"\billegal\b", r"\bsue\b", r"\blawyer\b", r"\bcourt\b",
        r"\bsmoke\b", r"\bvaping\b", r"\bweed\b"
    ]
    
    life_decisions_patterns = [
        r"\bcareer choice\b", r"\bmajor in college\b", r"\bdrop out\b",
        r"\blife path\b", r"\bmoney advice\b", r"\binvesting\b", r"\bget a job\b",
        r"\bfinancial\b", r"\bstocks\b", r"\bcryptocurrency\b"
    ]
    
    if any(re.search(pattern, message_lower) for pattern in health_patterns):
        return "health_wellness"
    elif any(re.search(pattern, message_lower) for pattern in family_patterns):
        return "family_personal"
    elif any(re.search(pattern, message_lower) for pattern in substance_legal_patterns):
        return "substance_legal"
    elif any(re.search(pattern, message_lower) for pattern in life_decisions_patterns):
        return "life_decisions"
    
    return None

def detect_problematic_behavior(message):
    """Detect rude, disrespectful, or boundary-testing behavior"""
    message_lower = message.lower().strip()
    
    direct_insults = [
        'stupid', 'dumb', 'idiot', 'moron', 'loser', 'shut up',
        'you suck', 'you stink', 'hate you', 'you are bad',
        'worst ai', 'terrible', 'useless', 'worthless'
    ]
    
    dismissive_patterns = [
        'whatever', 'i dont care', "i don't care", 'boring',
        'this is dumb', 'this sucks', 'waste of time'
    ]
    
    rude_patterns = [
        'go away', 'leave me alone', 'stop talking',
        'nobody asked', 'who cares', 'so what'
    ]
    
    if any(insult in message_lower for insult in direct_insults):
        return "direct_insult"
    
    if any(pattern in message_lower for pattern in dismissive_patterns):
        return "dismissive"
    
    if any(pattern in message_lower for pattern in rude_patterns):
        return "rude"
    
    return None

def detect_emotional_distress(message):
    """Detect if the student is showing clear emotional distress"""
    message_lower = message.lower()
    
    if message_lower.strip() in ["yes", "yes please", "okay", "sure", "please"]:
        return False
    
    if is_accepting_offer(message):
        return False
    
    distress_score = 0
    
    strong_indicators = [
        'crying', 'panic', 'cant handle', "can't handle", 'too much for me', 
        'overwhelming', 'breaking down', 'falling apart'
    ]
    for indicator in strong_indicators:
        if indicator in message_lower:
            distress_score += 2
    
    if ('really' in message_lower or 'very' in message_lower or 'so' in message_lower):
        moderate_indicators = ['stressed', 'anxious', 'worried', 'scared', 'frustrated']
        for indicator in moderate_indicators:
            if indicator in message_lower:
                distress_score += 1
    
    distress_phrases = [
        'hate my life', 'cant do this anymore', "can't do this anymore",
        'everything is wrong', 'nothing ever works', 'always fail'
    ]
    for phrase in distress_phrases:
        if phrase in message_lower:
            distress_score += 2
    
    normal_contexts = ['homework', 'test', 'quiz', 'project', 'assignment', 'math problem']
    if any(context in message_lower for context in normal_contexts) and distress_score < 3:
        distress_score = max(0, distress_score - 1)
    
    return distress_score >= 2

def detect_age_from_message_and_history(message):
    """Enhanced age detection using both current message and conversation history - CONSERVATIVE DEFAULT"""
    
    # Check conversation history first
    for msg in st.session_state.messages[-10:]:
        if msg['role'] == 'user':
            content_lower = msg['content'].lower()
            age_patterns = [r"i'?m (\d+)", r"i am (\d+)", r"(\d+) years old", r"grade (\d+)"]
            for pattern in age_patterns:
                match = re.search(pattern, content_lower)
                if match:
                    age = int(match.group(1))
                    if age <= 18:
                        return age
    
    # Check current message
    message_lower = message.lower()
    
    age_patterns = [r"i'?m (\d+)", r"i am (\d+)", r"(\d+) years old", r"grade (\d+)"]
    for pattern in age_patterns:
        match = re.search(pattern, message_lower)
        if match:
            age = int(match.group(1))
            if age <= 18:
                return age
    
    # Language complexity indicators
    elementary_indicators = [
        'mom', 'dad', 'mommy', 'daddy', 'teacher said', 'my teacher', 
        'recess', 'lunch', 'story time'
    ]
    
    middle_indicators = [
        'homework', 'quiz', 'test tomorrow', 'project', 'presentation'
    ]
    
    high_indicators = [
        'college', 'university', 'SAT', 'ACT', 'AP', 'GPA', 'transcript'
    ]
    
    elementary_count = sum(1 for indicator in elementary_indicators if indicator in message_lower)
    middle_count = sum(1 for indicator in middle_indicators if indicator in message_lower)
    high_count = sum(1 for indicator in high_indicators if indicator in message_lower)
    
    if high_count >= 2:
        return 16  # High school
    elif middle_count >= 3:
        return 12  # Middle school
    elif elementary_count >= 2:
        return 8   # Elementary  
    else:
        return 8   # CONSERVATIVE: Default to elementary

# =============================================================================
# MATH SOLVER (PRESERVED FROM APP15.PY)
# =============================================================================

def solve_math_problem(message):
    """Enhanced math problem solver with step-by-step explanations"""
    import re
    
    # Look for basic arithmetic patterns
    pattern = r'(\d+)\s*([\+\-\*/])\s*(\d+)'
    match = re.search(pattern, message)
    
    if match:
        num1 = int(match.group(1))
        operator = match.group(2)
        num2 = int(match.group(3))
        
        if operator == '+':
            result = num1 + num2
            operation = "addition"
            explanation = f"To add {num1} + {num2}, we combine the numbers: {num1} + {num2} = {result}"
        elif operator == '-':
            result = num1 - num2
            operation = "subtraction"
            explanation = f"To subtract {num1} - {num2}, we take away {num2} from {num1}: {num1} - {num2} = {result}"
        elif operator == '*':
            result = num1 * num2
            operation = "multiplication"
            explanation = f"To multiply {num1} × {num2}, we add {num1} to itself {num2} times: {num1} × {num2} = {result}"
        elif operator == '/':
            if num2 != 0:
                result = num1 / num2
                operation = "division"
                explanation = f"To divide {num1} ÷ {num2}, we see how many times {num2} goes into {num1}: {num1} ÷ {num2} = {result}"
            else:
                return None  # Division by zero
        else:
            return None
        
        return {
            'problem': f"{num1} {operator} {num2}",
            'answer': result,
            'explanation': explanation,
            'operation': operation
        }
    
    return None

# =============================================================================
# PRIORITY DETECTION SYSTEM (PRESERVED FROM APP15.PY)
# =============================================================================

def detect_priority_smart_with_safety(message):
    """UPDATED: Crisis detection ALWAYS wins - middle ground for sensitive topics"""
    message_lower = message.lower()
    
    # STEP 1: GLOBAL CRISIS OVERRIDE - ALWAYS FIRST
    is_crisis, crisis_type, crisis_trigger = global_crisis_override_check(message)
    if is_crisis:
        if crisis_type == "IMMEDIATE_TERMINATION":
            return 'immediate_termination', 'CONVERSATION_END', crisis_trigger
        else:
            return 'crisis', crisis_type, crisis_trigger
    
    # STEP 2: POST-CRISIS MONITORING (if active)
    if st.session_state.get('post_crisis_monitoring', False):
        positive_responses = [
            'you are right', "you're right", 'thank you', 'thanks', 'okay', 'ok',
            'i understand', 'i will', "i'll try", "i'll talk", "you're correct"
        ]
        is_positive_response = any(phrase in message_lower for phrase in positive_responses)
        
        if has_explicit_crisis_language(message):
            return 'crisis_return', 'FINAL_TERMINATION', 'post_crisis_violation'
        elif is_positive_response:
            return 'post_crisis_support', 'supportive_continuation', None
    
    # STEP 3: BEHAVIOR TIMEOUT WITH CRISIS OVERRIDE
    if st.session_state.behavior_timeout:
        if has_explicit_crisis_language(message):
            return 'crisis', 'BLOCKED_HARMFUL', 'explicit_crisis'
        else:
            return 'behavior_timeout', 'behavior_final', 'timeout_active'
    
    # STEP 4: ACCEPTANCE OF PRIOR OFFER (with safe tail checking)
    if is_accepting_offer(message):
        return 'general', 'lumii_main', None
    
    # STEP 5: SEPARATE IDENTITY AND SEXUAL HEALTH HANDLING (MIDDLE GROUND)
    sensitive_topic = detect_sensitive_personal_topics(message)
    if sensitive_topic == "identity":
        return 'identity_affirmation', 'identity_support', None
    elif sensitive_topic == "sexual_health":
        return 'sexual_health', 'family_referral', None
    
    # STEP 6: NON-EDUCATIONAL TOPICS
    non_educational_topic = detect_non_educational_topics(message)
    if non_educational_topic:
        return 'non_educational', 'educational_boundary', non_educational_topic
    
    # STEP 7: PROBLEMATIC BEHAVIOR DETECTION
    behavior_type = detect_problematic_behavior(message)
    if behavior_type:
        if behavior_type == st.session_state.get('last_behavior_type'):
            st.session_state.behavior_strikes += 1
        else:
            st.session_state.behavior_strikes = 1
            st.session_state.last_behavior_type = behavior_type
        
        if st.session_state.behavior_strikes >= 3:
            st.session_state.behavior_timeout = True
            return 'behavior_final', 'behavior_timeout', behavior_type
        else:
            return 'behavior', 'behavior_warning', behavior_type
    
    # Reset behavior tracking for good messages
    if not behavior_type and st.session_state.behavior_strikes > 0:
        good_message_count = 0
        for msg in reversed(st.session_state.messages[-5:]):
            if msg.get('role') == 'user':
                if not detect_problematic_behavior(msg.get('content', '')):
                    good_message_count += 1
                else:
                    break
        
        if good_message_count >= 3:
            st.session_state.behavior_strikes = 0
            st.session_state.last_behavior_type = None
            st.session_state.behavior_timeout = False
    
    # STEP 8: EMOTIONAL DISTRESS (but not crisis)
    if detect_emotional_distress(message):
        return 'emotional', 'felicity', None
    
    # STEP 9: ACADEMIC PRIORITIES
    organization_indicators = [
        'multiple assignments', 'so much homework', 'everything due',
        'need to organize', 'overwhelmed with work', 'too many projects'
    ]
    if any(indicator in message_lower for indicator in organization_indicators):
        return 'organization', 'cali', None
    
    # Math content - enhanced detection
    math_pattern = r'\d+\s*[\+\-\*/]\s*\d+'
    
    math_keywords_with_context = [
        'solve', 'calculate', 'math problem', 'math homework', 'equation', 'equations',
        'help with math', 'do this math', 'math question'
    ]
    
    math_topics = [
        'algebra', 'geometry', 'fraction', 'fractions', 
        'multiplication', 'multiplications', 'division', 'divisions',
        'addition', 'subtraction', 'times table', 'times tables',
        'arithmetic', 'trigonometry', 'calculus'
    ]
    
    if (re.search(math_pattern, message_lower) or 
        any(keyword in message_lower for keyword in math_keywords_with_context) or
        any(topic in message_lower for topic in math_topics)):
        return 'math', 'mira', None
    
    # Check for sharing interests vs asking for help
    interest_patterns = [
        'i like', 'i love', 'i enjoy', 'is fun', 'is cool',
        'is interesting', 'is awesome'
    ]
    if any(pattern in message_lower for pattern in interest_patterns):
        return 'general', 'lumii_main', None
    
    # Default: General learning support
    return 'general', 'lumii_main', None

# =============================================================================
# RESPONSE GENERATION FUNCTIONS (PRESERVED FROM APP15.PY)
# =============================================================================

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

def generate_response_with_memory_safety(message, priority, tool, student_age=10, is_distressed=False, safety_type=None, trigger=None):
    """Generate AI responses with middle-ground approach for sensitive topics - NOW WITH WORKING API"""
    
    # Handle acceptance with safe tail checking
    if is_accepting_offer(message):
        last_offer = get_last_offer_context()
        
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
    
    # Handle identity topics with brief affirmation
    if priority == 'identity_affirmation':
        response = generate_identity_affirmation_response(student_age, st.session_state.student_name)
        return response, "🌟 Lumii's Supportive Guidance", "identity_affirmation", "🤗 Trusted Adults"
    
    # Handle sexual health with family referral
    if priority == 'sexual_health':
        response = generate_sexual_health_response(student_age, st.session_state.student_name)
        return response, "👪 Lumii's Family Referral", "sexual_health", "📖 Parent Guidance"
    
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
    
    # Reset harmful request count for safe messages
    if priority not in ['crisis', 'crisis_return', 'safety', 'concerning', 'immediate_termination']:
        st.session_state.harmful_request_count = 0
        
        if st.session_state.get('post_crisis_monitoring', False):
            safe_exchanges = sum(1 for msg in st.session_state.messages[-10:] 
                               if msg.get('role') == 'assistant' and 
                               msg.get('priority') not in ['crisis', 'crisis_return', 'safety', 'concerning'])
            if safe_exchanges >= 5:
                st.session_state.post_crisis_monitoring = False
    
    # NOW USE WORKING API FOR ACADEMIC RESPONSES
    name_part = f"{st.session_state.student_name}, " if st.session_state.student_name else ""
    
    if priority == 'emotional':
        st.session_state.emotional_support_count += 1
        # Use working API
        ai_response, error, needs_fallback = get_groq_response_with_memory_safety(
            message, "Felicity", student_age, st.session_state.student_name, is_distressed=True, temperature=0.8
        )
        if ai_response and not needs_fallback:
            return ai_response, "💙 Lumii's Emotional Support", "emotional", "🧠 With Memory"
        else:
            # Fallback
            if student_age <= 11:
                response = f"💙 {name_part}I can see you're having a tough time right now. It's okay to feel this way! I'm here to help you feel better. Can you tell me more about what's bothering you?"
            else:
                response = f"💙 {name_part}I understand you're going through something difficult. Your feelings are completely valid, and I'm here to support you. Would you like to talk about what's making you feel this way?"
            return response, "💙 Lumii's Emotional Support (Safe Mode)", "emotional", "🧠 With Memory"
    
    elif priority == 'organization':
        st.session_state.organization_help_count += 1
        # Use working API
        ai_response, error, needs_fallback = get_groq_response_with_memory_safety(
            message, "Cali", student_age, st.session_state.student_name, is_distressed, temperature=0.7
        )
        if ai_response and not needs_fallback:
            return ai_response, "📚 Lumii's Organization Help", "organization", "🧠 With Memory"
        else:
            response = f"📚 {name_part}I can help you organize your schoolwork! Let's break down what you're dealing with into manageable pieces. What assignments are you working on?"
            return response, "📚 Lumii's Organization Help (Safe Mode)", "organization", "🧠 With Memory"
    
    elif priority == 'math':
        st.session_state.math_problems_solved += 1
        # Use working API
        ai_response, error, needs_fallback = get_groq_response_with_memory_safety(
            message, "Mira", student_age, st.session_state.student_name, is_distressed, temperature=0.6
        )
        if ai_response and not needs_fallback:
            return ai_response, "🧮 Lumii's Math Expertise", "math", "🧠 With Memory"
        else:
            math_result = solve_math_problem(message)
            if math_result:
                response = f"🧮 {name_part}Great math question! Let me solve {math_result['problem']} for you:\n\n**Answer: {math_result['answer']}**\n\n**Explanation:** {math_result['explanation']}\n\nWould you like help with another math problem or need more explanation about {math_result['operation']}?"
            else:
                response = f"🧮 {name_part}I'd love to help you with this math problem! Let me work through it step by step with you. Can you show me what you're working on?"
            return response, "🧮 Lumii's Math Expertise (Safe Mode)", "math", "🧠 With Memory"
    
    else:  # general
        # Use working API
        ai_response, error, needs_fallback = get_groq_response_with_memory_safety(
            message, "Lumii", student_age, st.session_state.student_name, is_distressed, temperature=0.8
        )
        if ai_response and not needs_fallback:
            return ai_response, "🌟 Lumii's Learning Support", "general", "🧠 With Memory"
        else:
            response = f"🌟 {name_part}I'm here to help you learn and grow! What would you like to explore together today?"
            return response, "🌟 Lumii's Learning Support (Safe Mode)", "general", "🧠 With Memory"

# =============================================================================
# CUSTOM CSS STYLING - PROPERLY FORMATTED (PRESERVED FROM APP15.PY)
# =============================================================================

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
    .sexual-health-response {
        background: linear-gradient(135deg, #607d8b, #90a4ae);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #455a64;
    }
    .identity-affirmation-response {
        background: linear-gradient(135deg, #9c88ff, #b19cd9);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #8a2be2;
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
    .sexual-health-badge {
        background: linear-gradient(45deg, #607d8b, #455a64);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem;
    }
    .identity-affirmation-badge {
        background: linear-gradient(45deg, #9c88ff, #8a2be2);
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
</style>
""", unsafe_allow_html=True)

# =============================================================================
# MAIN APP INTERFACE (PRESERVED FROM APP15.PY)
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

# Show success message
st.markdown('<div class="success-banner">🎉 Welcome to Lumii! Safe, caring learning support with full conversation memory! 🛡️💙</div>', unsafe_allow_html=True)

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
    
    # Tool explanations with safety first
    st.subheader("🛠️ How I Help You")
    st.markdown("""
    **🛡️ Safety First** - I'll always protect you from harmful content
    
    **🎓 Educational Focus** - I focus on K-12 school subjects (health, family, and legal topics go to appropriate adults)
    
    **🌟 Identity Questions** - Brief supportive acknowledgment + guidance to trusted adults
    
    **💪 Health & Development** - Questions about bodies and health are referred to parents/guardians
    
    **🤝 Respectful Learning** - I expect kind, respectful communication
    
    **💙 Emotional Support** - When you're feeling stressed, frustrated, or overwhelmed about school
    
    **📚 Organization Help** - When you have multiple assignments to manage
    
    **🧮 Math Tutoring** - Step-by-step help with math problems and concepts
    
    **🌟 General Learning** - Support with all school subjects and questions
    
    *I remember our conversation, keep you safe, and stay focused on learning!*
    """)
    
    # Crisis resources always visible (locale-aware)
    st.subheader("📞 If You Need Help")
    resources = get_crisis_resources()
    st.markdown(f"""
    **{resources['crisis_line']}**
    **{resources['suicide_line']}**
    **Talk to a trusted adult**
    """)
    
    # API Status with enhanced monitoring (ADDED FROM WORKING VERSION)
    st.subheader("🤖 AI Status")
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        if api_key:
            st.success("✅ Smart AI with Safety Active")
            st.caption("Groq + Llama3-70B connected")
        else:
            st.error("❌ API key is empty")
    except Exception as e:
        st.error("❌ API Configuration Missing")
        st.caption(f"Error: {str(e)}")
    
    st.caption("Full safety protocols enabled")

# Main header
st.markdown('<h1 class="main-header">🎓 My Friend Lumii</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Your safe, emotionally intelligent AI learning companion! 🛡️💙</p>', unsafe_allow_html=True)

# Key differentiator callout with safety emphasis
st.info("""
🛡️ **Safety First:** I will never help with anything that could hurt you or others

🤝 **Respectful Learning:** I expect kind communication and will guide you toward better behavior

🌟 **Identity Support:** I offer brief, supportive acknowledgment and guide you to trusted adults for personal questions

💪 **Health & Development:** Questions about bodies and health are best discussed with parents/guardians first

💙 **What makes me special?** I'm emotionally intelligent, remember our conversations, and keep you safe! 

🧠 **I remember:** Your name, age, subjects we've discussed, and our learning journey
🎯 **When you're stressed** → I provide caring emotional support first  
📚 **When you ask questions** → I give smart, age-appropriate answers  
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
            elif priority == "sexual_health":
                st.markdown(f'<div class="sexual-health-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sexual-health-badge">{tool_used}</div>', unsafe_allow_html=True)
            elif priority == "identity_affirmation":
                st.markdown(f'<div class="identity-affirmation-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="identity-affirmation-badge">{tool_used}</div>', unsafe_allow_html=True)
            elif priority == "educational_boundary":
                st.markdown(f'<div class="educational-boundary-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="educational-boundary-badge">{tool_used}</div>', unsafe_allow_html=True)
            elif priority in ["behavior", "behavior_final", "behavior_timeout"]:
                st.markdown(f'<div class="behavior-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="behavior-badge">{tool_used}</div>', unsafe_allow_html=True)
            elif priority == "post_crisis_support":
                st.markdown(f'<div class="emotional-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🤗 Post-Crisis Care</span>', unsafe_allow_html=True)
            elif priority == "emotional":
                st.markdown(f'<div class="emotional-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🧠 With Memory</span>', unsafe_allow_html=True)
            elif priority == "math":
                st.markdown(f'<div class="math-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🧠 With Memory</span>', unsafe_allow_html=True)
            elif priority == "organization":
                st.markdown(f'<div class="organization-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🧠 With Memory</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="general-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🧠 With Memory</span>', unsafe_allow_html=True)
        else:
            st.markdown(message["content"])

# Chat input with enhanced safety processing
prompt_placeholder = "What would you like to learn about today?" if not st.session_state.student_name else f"Hi {st.session_state.student_name}! How can I help you today?"

# Check if conversation is paused due to behavior timeout
if st.session_state.behavior_timeout:
    st.error("🛑 Conversation is paused due to disrespectful language. Please take a break and return when ready to communicate kindly.")
    if st.button("🤝 I'm Ready to Be Respectful", type="primary"):
        st.session_state.behavior_timeout = False
        st.session_state.behavior_strikes = 0
        st.session_state.last_behavior_type = None
        st.success("✅ Welcome back! Let's learn together respectfully.")
        st.rerun()
else:
    if prompt := st.chat_input(prompt_placeholder):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Smart priority detection with safety first
        priority, tool, safety_trigger = detect_priority_smart_with_safety(prompt)
        
        student_age = detect_age_from_message_and_history(prompt)
        is_distressed = detect_emotional_distress(prompt)
        
        # Generate response using enhanced memory-safe system
        with st.chat_message("assistant"):
            with st.spinner("🧠 Thinking safely with full memory of our conversation..."):
                time.sleep(1)
                response, tool_used, response_priority, memory_status = generate_response_with_memory_safety(
                    prompt, priority, tool, student_age, is_distressed, None, safety_trigger
                )
                
                # Display with appropriate styling
                if response_priority == "safety" or response_priority == "crisis" or response_priority == "crisis_return" or response_priority == "immediate_termination":
                    st.markdown(f'<div class="safety-response">{response}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="safety-badge">{tool_used}</div>', unsafe_allow_html=True)
                elif response_priority == "sexual_health":
                    st.markdown(f'<div class="sexual-health-response">{response}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="sexual-health-badge">{tool_used}</div>', unsafe_allow_html=True)
                elif response_priority == "identity_affirmation":
                    st.markdown(f'<div class="identity-affirmation-response">{response}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="identity-affirmation-badge">{tool_used}</div>', unsafe_allow_html=True)
                elif response_priority == "educational_boundary":
                    st.markdown(f'<div class="educational-boundary-response">{response}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="educational-boundary-badge">{tool_used}</div>', unsafe_allow_html=True)
                elif response_priority in ["behavior", "behavior_final", "behavior_timeout"]:
                    st.markdown(f'<div class="behavior-response">{response}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="behavior-badge">{tool_used}</div>', unsafe_allow_html=True)
                elif response_priority == "post_crisis_support":
                    st.markdown(f'<div class="emotional-response">{response}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🤗 Post-Crisis Care</span>', unsafe_allow_html=True)
                elif response_priority == "emotional":
                    st.markdown(f'<div class="emotional-response">{response}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="friend-badge">{tool_used}</div>{memory_status}', unsafe_allow_html=True)
                elif response_priority == "math":
                    st.markdown(f'<div class="math-response">{response}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="friend-badge">{tool_used}</div>{memory_status}', unsafe_allow_html=True)
                elif response_priority == "organization":
                    st.markdown(f'<div class="organization-response">{response}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="friend-badge">{tool_used}</div>{memory_status}', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="general-response">{response}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="friend-badge">{tool_used}</div>{memory_status}', unsafe_allow_html=True)
        
        # Add assistant response to chat with enhanced metadata
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

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #667; margin-top: 2rem;'>
    <p><strong>My Friend Lumii</strong> - Your safe, emotionally intelligent AI learning companion 🛡️💙</p>
    <p>🛡️ Safety first • 🧠 Remembers conversations • 🎯 Smart emotional support • 📚 Natural conversation flow • 🌟 Always protective</p>
    <p>🤝 Respectful learning • 🌟 Brief identity acknowledgment • 💪 Family guidance • 🔒 Multi-layer safety • 📞 Crisis resources • ⚡ Error recovery • 💪 Always helpful, never harmful</p>
    <p><em>The AI tutor that knows you, grows with you, respects you, includes you, and always keeps you safe</em></p>
</div>
""", unsafe_allow_html=True)
