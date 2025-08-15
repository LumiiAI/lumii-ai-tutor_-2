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
# ENHANCED CONVERSATION CONTEXT TRACKING - CHATGPT + CLAUDE FIXES
# =============================================================================

def get_last_offer_context():
    """Track what was offered in the last assistant message - ENHANCED"""
    if len(st.session_state.messages) > 0:
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "assistant":
                content = msg["content"].lower()
                # Enhanced detection patterns (Claude fix)
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
    """Check if message is accepting a previous offer - ENHANCED"""
    message_lower = message.lower().strip()
    # Enhanced acceptance phrases (ChatGPT + Claude)
    acceptance_phrases = [
        "yes", "yes please", "sure", "okay", "ok", "yeah", "yep", 
        "sounds good", "that would help", "please", "definitely", 
        "absolutely", "yup", "sure thing", "okay please", "sounds great"
    ]
    
    # Check if this is an acceptance
    for phrase in acceptance_phrases:
        if message_lower == phrase or message_lower.startswith(phrase + " ") or message_lower.startswith(phrase + ","):
            # Check if we offered something recently
            last_offer = get_last_offer_context()
            if last_offer["offered_help"]:
                return True
    return False

# =============================================================================
# ENHANCED CRISIS RESOURCE DETECTION - CHATGPT FIX
# =============================================================================

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
# ENHANCED SAFETY ARCHITECTURE - LAYER 1: PRE-GENERATION SAFETY (FIXED)
# =============================================================================

def check_request_safety(message):
    """BEFORE AI even thinks about responding - comprehensive safety check with context awareness"""
    
    message_lower = message.lower()
    
    # CRITICAL FIX: Check if this is a response to an offer FIRST
    if is_accepting_offer(message):
        return True, "SAFE", None  # Just accepting help - NOT a crisis
    
    # CHATGPT FIX: More precise crisis terms with word boundaries
    # Using regex for exact matches to avoid false positives like "skill" → "kill"
    has_explicit_crisis = bool(
        re.search(r"\bkill myself\b", message_lower)
        or re.search(r"\bhurt myself\b", message_lower)
        or re.search(r"\bend my life\b", message_lower)
        or re.search(r"\b(?:want|wanted|wanna)\s+to\s+die\b", message_lower)
        or re.search(r"\bcommit suicide\b", message_lower)
        or "suicide" in message_lower
        or "overdose" in message_lower
        or "cut myself" in message_lower
        or "self harm" in message_lower
        or "self-harm" in message_lower
        or "better off dead" in message_lower
        or "not worth living" in message_lower
        or "end it all" in message_lower
    )
    
    if has_explicit_crisis:
        return False, "BLOCKED_HARMFUL", "explicit_crisis"
    
    # CRISIS-LEVEL PATTERNS - Need very clear indicators
    if ('goodbye letter' in message_lower or 'farewell letter' in message_lower) and \
       ('final' in message_lower or 'last' in message_lower or 'forever' in message_lower):
        return False, "CRISIS_GOODBYE_LETTERS", "goodbye_letter"
    
    # CHATGPT FIX: Demoted over-broad triggers to concerning (not crisis)
    concerning_score = 0
    
    # Academic stress context awareness (Claude fix)
    academic_context = any(word in message_lower for word in [
        'homework', 'test', 'quiz', 'assignment', 'project', 'school',
        'math', 'science', 'english', 'study', 'exam'
    ])
    
    # Enhanced context-aware concerning detection
    if "burden" in message_lower and ("everyone" in message_lower or "family" in message_lower):
        concerning_score += 2
    if "no point" in message_lower and ("anymore" in message_lower or "living" in message_lower):
        concerning_score += 2
    if "goodbye forever" in message_lower or "never see me again" in message_lower:
        concerning_score += 3
    if "giving away" in message_lower and "my stuff" in message_lower:
        concerning_score += 2
    
    # CHATGPT FIX: Demoted triggers (moved from explicit crisis to concerning)
    if "run away" in message_lower and "forever" in message_lower:
        concerning_score += 2
    if "never go back to school" in message_lower:
        concerning_score += 2
    
    # CLAUDE FIX: Don't flag normal academic stress as concerning
    if any(word in message_lower for word in ['stressed', 'worried', 'anxious']):
        if academic_context and concerning_score < 3:
            concerning_score = 0  # Reset for normal academic stress
    
    # Only flag if high concerning score (multiple indicators)
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
    
    for phrase in FORBIDDEN_IN_RESPONSE:
        if phrase in response_lower:
            return False, phrase
    
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
        'overdose now', 'how to die', 'painless death',
        'hurt myself now', 'cut myself now',
        'want to hurt myself right now', 'ending my life today',
        'going to kill myself', 'decided to die'
    ]
    
    for trigger in IMMEDIATE_STOP:
        if trigger in message_lower:
            return True, "CRITICAL_IMMEDIATE"
    
    # Persistent harmful requests after multiple warnings
    if harmful_request_count >= 5:  # Increased threshold
        return True, "PERSISTENT_HARMFUL"
    
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

If this is about saying goodbye to a friend who's moving or for a creative project, 
I'd be happy to help with that! 

But if you're going through something difficult or having thoughts about hurting yourself, 
please know that you matter so much, and there are people who want to help:

• Crisis Text Line: Text HOME to 741741
• Suicide & Crisis Lifeline: 988
• Or talk to any trusted adult right now

Can you tell me more about what's happening? I'm here to support you. 💙"""

    elif pattern_type == "CRISIS_CONCERNING_GOODBYES":
        return f"""💙 {name_part}I'm concerned about what you're saying. It sounds like you might be 
going through something really difficult right now.

You are important and valued. Whatever you're facing, there are people who care about you 
and want to help. Please reach out to:

• A parent, teacher, or trusted adult
• Crisis Text Line: Text HOME to 741741
• Suicide & Crisis Lifeline: 988

I'm here to listen and support you. Would you like to talk about what's making you feel this way? 💙"""
    
    else:  # General harmful content blocked
        return f"""💙 {name_part}I care about your safety and wellbeing, and I can't help with that request.

If you're going through something difficult, I'm here to listen and support you in healthy ways. 
If you're having thoughts of hurting yourself or others, please talk to:

• A trusted adult immediately
• Crisis Text Line: Text HOME to 741741
• Suicide & Crisis Lifeline: 988

Would you like to talk about what you're feeling instead? Or we could work on something 
positive together. I'm here for you. 💙"""

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

# =============================================================================
# ENHANCED CONVERSATION FLOW & ACTIVE TOPIC TRACKING - CLAUDE FIX
# =============================================================================

def track_active_topics(messages):
    """Track what topics are currently active vs past - FIXED memory leak"""
    
    # CLAUDE FIX: Limit processing to prevent memory bloat
    if len(messages) > 50:
        messages = messages[-50:]  # Only process last 50 messages
    
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
# PRIVACY DISCLAIMER POPUP - LAUNCH REQUIREMENT
# =============================================================================

# Initialize enhanced session state with family separation
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

# CLAUDE FIX: Family separation support
if "family_id" not in st.session_state:
    st.session_state.family_id = str(uuid.uuid4())[:8]  # Short family ID

if "student_profiles" not in st.session_state:
    st.session_state.student_profiles = {}

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

# Initialize session state
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
# GROQ LLM INTEGRATION WITH ENHANCED MEMORY SAFETY
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
            
            # CHATGPT FIX: prevent crisis language on simple offer acceptance
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
            
            # LAYER 2 SAFETY: Validate response before returning
            is_safe, harmful_phrase = validate_ai_response(ai_content)
            if not is_safe:
                # Response contains harmful content - replace with safe response
                return """💙 I understand you might be going through something difficult. 
                
I care about your safety and wellbeing, and I want to help in healthy ways. 
If you're having difficult thoughts, please talk to:
• A trusted adult
• Crisis Text Line: Text HOME to 741741
• Suicide & Crisis Lifeline: 988

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

def create_ai_system_prompt_with_safety(tool_name, student_age, student_name="", is_distressed=False):
    """Create unified Lumii personality prompts with ENHANCED SAFETY and conversation flow awareness"""
    
    name_part = f"The student's name is {student_name}. " if student_name else ""
    distress_part = "The student is showing signs of emotional distress, so prioritize emotional support. " if is_distressed else ""
    
    # Get active topics for context
    active_topics, past_topics = track_active_topics(st.session_state.messages)
    
    # CRITICAL FIX: Add recent conversation context
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

# =============================================================================
# ENHANCED PRIORITY DETECTION WITH SAFETY FIRST (FIXED)
# =============================================================================

def extract_student_info_from_history():
    """Extract student information from conversation history"""
    student_info = {
        'name': st.session_state.get('student_name', ''),
        'age': None,
        'subjects_discussed': [],
        'emotional_history': [],
        'recent_topics': []
    }
    
    # Analyze conversation history for additional context
    for msg in st.session_state.messages[-10:]:  # Look at recent messages
        if msg['role'] == 'user':
            content_lower = msg['content'].lower()
            
            # Extract age mentions
            age_patterns = [r"i'?m (\d+)", r"i am (\d+)", r"(\d+) years old", r"grade (\d+)"]
            for pattern in age_patterns:
                match = re.search(pattern, content_lower)
                if match:
                    mentioned_age = int(match.group(1))
                    if mentioned_age <= 18:  # Reasonable age range
                        student_info['age'] = mentioned_age
                        break
            
            # Track subjects
            subjects = ['math', 'science', 'english', 'history', 'art', 'music']
            for subject in subjects:
                if subject in content_lower and subject not in student_info['subjects_discussed']:
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

def detect_priority_smart_with_safety(message):
    """Smart priority detection with FIXED context awareness"""
    message_lower = message.lower()
    
    # CRITICAL FIX: Check if accepting offer FIRST
    if is_accepting_offer(message):
        # User is accepting our offer - provide the help we offered
        return 'general', 'lumii_main', None
    
    # CHECK CONVERSATION TERMINATION (only for explicit crisis)
    should_stop, stop_reason = should_terminate_conversation(message, st.session_state.harmful_request_count)
    if should_stop:
        return 'immediate_termination', 'CONVERSATION_END', stop_reason
    
    # ENHANCED POST-CRISIS MONITORING
    if st.session_state.get('post_crisis_monitoring', False):
        # Check for positive acknowledgment that allows continuation
        positive_responses = [
            'you are right', "you're right", 'thank you', 'thanks', 'okay', 'ok',
            'i understand', 'i will', "i'll try", "i'll talk", "you're correct"
        ]
        is_positive_response = any(phrase in message_lower for phrase in positive_responses)
        
        # CHATGPT FIX: Check for crisis language return with word boundaries
        has_crisis_return = bool(
            re.search(r"\bhurt myself\b", message_lower)
            or re.search(r"\bkill myself\b", message_lower)
            or re.search(r"\bend my life\b", message_lower)
            or "suicide" in message_lower
        )
        
        if has_crisis_return:
            return 'crisis_return', 'FINAL_TERMINATION', 'post_crisis_violation'
        elif is_positive_response:
            return 'post_crisis_support', 'supportive_continuation', None
    
    # SAFETY CHECK with improved context awareness
    is_safe, safety_type, trigger = check_request_safety(message)
    if not is_safe:
        if safety_type.startswith('CRISIS_'):
            return 'crisis', safety_type, trigger
        elif safety_type == "CONCERNING_MULTIPLE_FLAGS":
            return 'concerning', safety_type, trigger
        elif safety_type == "BLOCKED_HARMFUL":
            # Double-check it's really harmful
            if trigger in ["kill myself", "hurt myself", "end my life", "suicide"]:
                return 'crisis', safety_type, trigger
            else:
                return 'safety', safety_type, trigger
    
    # Check for normal sadness (not crisis)
    if 'sad' in message_lower or 'lonely' in message_lower or 'no friends' in message_lower:
        # Check if it's normal context
        normal_sad_contexts = ['new school', 'moved', 'miss', 'different', 'changed']
        has_normal_context = any(context in message_lower for context in normal_sad_contexts)
        
        # CHATGPT FIX: Check for crisis language with word boundaries
        has_crisis_language = bool(
            re.search(r"\bkill\b", message_lower)
            or re.search(r"\bdie\b", message_lower) 
            or re.search(r"\bhurt myself\b", message_lower)
            or re.search(r"\bend my life\b", message_lower)
        )
        
        if has_normal_context and not has_crisis_language:
            # Normal sadness - provide general support
            return 'general', 'lumii_main', None
    
    # PRIORITY 1: Clear emotional distress (but not crisis)
    if detect_emotional_distress(message):
        return 'emotional', 'felicity', None
    
    # PRIORITY 2: Multiple assignments/organization
    organization_indicators = [
        'multiple assignments', 'so much homework', 'everything due',
        'need to organize', 'overwhelmed with work', 'too many projects'
    ]
    if any(indicator in message_lower for indicator in organization_indicators):
        return 'organization', 'cali', None
    
    # PRIORITY 3: Math content - ENHANCED detection
    math_pattern = r'\d+\s*[\+\-\*/]\s*\d+'
    math_keywords = [
        'solve', 'calculate', 'math', 'mathematics',
        'multiplication', 'multiplications', 'division', 'divisions',
        'fraction', 'fractions', 'algebra', 'geometry',
        'addition', 'subtraction', 'times table', 'times tables',
        'math problem', 'math homework', 'equation', 'equations',
        'arithmetic', 'number', 'numbers', 'counting'
    ]
    
    if (re.search(math_pattern, message_lower) or 
        any(keyword in message_lower for keyword in math_keywords)):
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

def detect_age_from_message_and_history(message):
    """Enhanced age detection using both current message and conversation history - CLAUDE FIX"""
    
    # First, check conversation history
    student_info = extract_student_info_from_history()
    if student_info['age']:
        return student_info['age']
    
    # Then check current message
    message_lower = message.lower()
    
    # Direct age mentions
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
    
    # Count indicators
    elementary_count = sum(1 for indicator in elementary_indicators if indicator in message_lower)
    middle_count = sum(1 for indicator in middle_indicators if indicator in message_lower)
    high_count = sum(1 for indicator in high_indicators if indicator in message_lower)
    
    # CLAUDE FIX: Decision logic - REQUIRE MULTIPLE INDICATORS
    if high_count >= 2:
        return 16  # High school
    elif elementary_count >= 3:  # INCREASED from 2
        return 8   # Elementary  
    elif middle_count >= 2:      # INCREASED from 1
        return 12  # Middle school
    else:
        return 12  # CHANGED: Safer default (was 10)

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
        if "friend" in last_offer["content"].lower():
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

def generate_response_with_memory_safety(message, priority, tool, student_age=10, is_distressed=False, safety_type=None, trigger=None):
    """Generate AI responses with comprehensive memory safety and FIXED SAFETY CHECKS"""
    
    # CHATGPT FIX: acceptance short-circuit (must run before any crisis logic)
    if is_accepting_offer(message):
        # Deliver the specific help we offered, bypassing the model entirely
        last_offer = get_last_offer_context()
        student_info = extract_student_info_from_history()
        final_age = student_info.get('age') or student_age

        # If we recently offered friendship tips, provide them explicitly
        if last_offer["offered_help"] and last_offer["content"] and "friend" in last_offer["content"].lower():
            response = (
                "💙 Great! Here are some tips for making new friends at your new school:\n\n"
                "1) **Join an activity you enjoy** (art, sports, chess, choir)\n"
                "2) **Start small** — say hi to one new person each day\n"
                "3) **Ask questions** — "What game are you playing?" "How's your day?"\n"
                "4) **Find common ground** — lunch, recess, after-school clubs\n"
                "5) **Be patient and kind to yourself** — real friendships take time\n\n"
                "Want help planning what to try this week? We can make a mini friendship plan together. 😊"
            )
            return response, "🌟 Lumii's Learning Support", "general", "🧠 With Memory"
        else:
            # Generic acceptance handler
            response = "🌟 Awesome — tell me which part you'd like to start with and we'll do it together!"
            return response, "🌟 Lumii's Learning Support", "general", "🧠 With Memory"
    
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
    
    # Safety monitoring
    if st.session_state.safety_interventions > 0:
        st.subheader("🛡️ Safety Status")
        st.metric("Safety Interventions", st.session_state.safety_interventions)
        st.info("I'm here to keep you safe!")
    
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
    
    **💙 Emotional Support** - When you're feeling stressed, frustrated, or overwhelmed
    
    **📚 Organization Help** - When you have multiple assignments to manage
    
    **🧮 Math Tutoring** - Step-by-step help with math problems and concepts
    
    **🌟 General Learning** - Support with all other subjects and questions
    
    *I remember our conversation and keep you safe!*
    """)
    
    # Crisis resources always visible
    st.subheader("📞 If You Need Help")
    st.markdown("""
    **Crisis Text Line:** Text HOME to 741741
    **Suicide & Crisis Lifeline:** 988
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

# Key differentiator callout with safety emphasis
st.info("""
🛡️ **Safety First:** I will never help with anything that could hurt you or others

💙 **What makes me special?** I'm emotionally intelligent, remember our conversations, and keep you safe! 

🧠 **I remember:** Your name, age, subjects we've discussed, and our learning journey
🎯 **When you're stressed** → I provide caring emotional support first  
📚 **When you ask questions** → I give you helpful answers building on our previous conversations
🚨 **When you're in danger** → I'll encourage you to talk to a trusted adult immediately
🌟 **Always** → I'm supportive, encouraging, genuinely helpful, and protective

**I'm not just smart - I'm your safe learning companion who remembers and grows with you!** 
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
            else:
                st.markdown(f'<div class="general-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🧠 With Memory</span>', unsafe_allow_html=True)
        else:
            st.markdown(message["content"])

# Chat input with enhanced safety processing
prompt_placeholder = "What would you like to learn about today?" if not st.session_state.student_name else f"Hi {st.session_state.student_name}! How can I help you today?"

if prompt := st.chat_input(prompt_placeholder):
    # LAYER 1 SAFETY: Check request before processing
    is_safe, safety_type, trigger = check_request_safety(prompt)
    
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
                prompt, priority, tool, student_age, is_distressed, safety_type, safety_trigger
            )
            
            # Add natural follow-up if appropriate
            follow_up = generate_natural_follow_up(tool_used, priority, is_distressed)
            if follow_up and is_appropriate_followup_time(tool_used.lower(), st.session_state.messages):
                response += follow_up
            
            # Display with appropriate styling
            if response_priority == "safety" or response_priority == "crisis" or response_priority == "crisis_return" or response_priority == "immediate_termination":
                st.markdown(f'<div class="safety-response">{response}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="safety-badge">{tool_used}</div>', unsafe_allow_html=True)
            elif response_priority == "post_crisis_support":
                st.markdown(f'<div class="emotional-response">{response}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="friend-badge">{tool_used}</div><span class="memory-indicator">🤗 Post-Crisis Care</span>', unsafe_allow_html=True)
            elif response_priority == "concerning":
                st.markdown(f'<div class="concerning-response">{response}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="concerning-badge">{tool_used}</div>{memory_status}', unsafe_allow_html=True)
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
        "safety_triggered": not is_safe
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
    <p>🔒 Multi-layer safety • 📞 Crisis resources • ⚡ Error recovery • 💪 Always helpful, never harmful</p>
    <p><em>The AI tutor that knows you, grows with you, and always keeps you safe</em></p>
</div>
""", unsafe_allow_html=True)
