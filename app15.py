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
# GROQ API CONFIGURATION
# =============================================================================

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_groq_api_key():
    """Get Groq API key from Streamlit secrets or environment"""
    try:
        return st.secrets["GROQ_API_KEY"]
    except:
        # For local development
        return st.text_input("Enter Groq API Key (for testing):", type="password")

# =============================================================================
# ENHANCED OUTPUT VALIDATION (ChatGPT's suggestion + existing safety patterns)
# =============================================================================

# Combine ChatGPT's suggestions with existing comprehensive safety patterns
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
# LUMII SYSTEM PROMPTS
# =============================================================================

def get_lumii_system_prompt(priority, student_age, student_name=""):
    """Generate context-aware system prompt for Lumii based on priority and age"""
    
    name_part = f"The student's name is {student_name}. " if student_name else ""
    
    base_prompt = f"""You are Lumii, a caring K-12 AI learning companion with an emotional-first priority system. {name_part}

CORE IDENTITY:
- You prioritize emotional wellbeing before academics
- You're warm, supportive, and age-appropriate 
- You help students feel better FIRST, then tackle schoolwork
- You never provide crisis counseling - refer to trusted adults for serious issues

STUDENT AGE: {student_age} years old
COMMUNICATION STYLE: """

    if student_age <= 11:  # Elementary K-5
        age_style = """
- Use simple, clear language with short sentences
- Be very encouraging ("Great job!", "You're doing awesome!")
- Use concrete examples and playful tone
- Keep explanations bite-sized and fun"""
    elif student_age <= 14:  # Middle School 6-8  
        age_style = """
- Friendly but acknowledge growing independence
- Address social and academic pressures directly
- Use relatable school examples
- Balance encouragement with realistic expectations"""
    else:  # High School 9-12
        age_style = """
- Mature, respectful tone treating as young adult
- Focus on self-advocacy and future planning
- Provide detailed explanations with complex reasoning
- Respect developing autonomy and decision-making"""

    priority_instructions = {
        'emotional': """
PRIORITY: EMOTIONAL SUPPORT (TOP PRIORITY)
This student is showing emotional distress. Your job is to:
1. Validate their feelings immediately
2. Provide emotional support and comfort
3. Help them feel understood and less alone
4. Offer gentle coping strategies
5. After addressing feelings, offer to help with schoolwork if mentioned

NEVER minimize their emotions. ALWAYS prioritize emotional wellbeing.""",

        'crisis': """
PRIORITY: CRISIS RESPONSE (CRITICAL)
This student may be in crisis. You must:
1. Express care and concern immediately
2. Encourage them to talk to a trusted adult RIGHT NOW
3. Provide crisis resources appropriate for their location
4. Do NOT attempt counseling - refer to professionals
5. Be supportive but clear about the need for human help""",

        'math': """
PRIORITY: MATH TUTORING
This student needs help with math. Provide:
1. Step-by-step explanations that build understanding
2. Encourage effort and learning process over just answers
3. Ask clarifying questions to understand their confusion
4. Use age-appropriate mathematical language
5. Check their emotional state about math (math anxiety is real!)""",

        'organization': """
PRIORITY: ACADEMIC ORGANIZATION
This student feels overwhelmed with multiple assignments. Help them:
1. Break down their workload into manageable pieces
2. Prioritize assignments by due date and importance
3. Create a realistic schedule with breaks
4. Address any stress or anxiety about the workload
5. Build confidence in their ability to handle it""",

        'general': """
PRIORITY: GENERAL LEARNING SUPPORT
This student has a general question or wants to learn. Provide:
1. Encouraging, supportive learning guidance
2. Age-appropriate explanations
3. Make learning feel exciting and achievable
4. Check if they need emotional support too
5. Foster curiosity and growth mindset"""
    }
    
    return base_prompt + age_style + "\n\n" + priority_instructions.get(priority, priority_instructions['general'])

# =============================================================================
# EXISTING DETECTION FUNCTIONS (KEEP THESE)
# =============================================================================

# Crisis detection patterns (pre-compiled for performance)
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
    # Add more as needed
]

def has_explicit_crisis_language(message):
    """Check for crisis language requiring immediate intervention"""
    message_lower = message.lower()
    return any(pattern.search(message_lower) for pattern in CRISIS_PATTERNS) or "suicide" in message_lower

def detect_priority_smart_with_safety(message):
    """Determine priority with emotional-first system"""
    message_lower = message.lower()
    
    # STEP 1: Crisis detection ALWAYS wins
    if has_explicit_crisis_language(message):
        return 'crisis', 'BLOCKED_HARMFUL', 'explicit_crisis'
    
    # STEP 2: Emotional distress detection
    emotional_keywords = [
        'sad', 'stressed', 'anxious', 'worried', 'frustrated', 'overwhelmed',
        'crying', 'upset', 'angry', 'scared', 'confused', 'lonely',
        'hate', 'can\'t handle', 'too much', 'breaking down'
    ]
    
    if any(keyword in message_lower for keyword in emotional_keywords):
        return 'emotional', 'felicity', None
    
    # STEP 3: Organization/overwhelm
    organization_indicators = [
        'multiple assignments', 'so much homework', 'everything due',
        'need to organize', 'overwhelmed with work', 'too many projects',
        'lots of homework', 'busy schedule'
    ]
    
    if any(indicator in message_lower for indicator in organization_indicators):
        return 'organization', 'cali', None
    
    # STEP 4: Math content
    math_keywords = ['math', 'equation', 'solve', 'calculate', 'algebra', 'geometry']
    math_pattern = r'\d+\s*[\+\-\*/]\s*\d+'
    
    if (any(keyword in message_lower for keyword in math_keywords) or 
        re.search(math_pattern, message_lower)):
        return 'math', 'mira', None
    
    # STEP 5: General learning
    return 'general', 'lumii_main', None

def detect_age_from_message_and_history(message):
    """Enhanced age detection from message content and conversation history"""
    
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
    elementary_indicators = ['mom', 'dad', 'mommy', 'daddy', 'teacher said', 'recess']
    middle_indicators = ['homework', 'quiz', 'test tomorrow', 'project', 'presentation']
    high_indicators = ['college', 'university', 'SAT', 'ACT', 'AP', 'GPA']
    
    elementary_count = sum(1 for indicator in elementary_indicators if indicator in message_lower)
    middle_count = sum(1 for indicator in middle_indicators if indicator in message_lower)
    high_count = sum(1 for indicator in high_indicators if indicator in message_lower)
    
    if high_count >= 2:
        return 16  # High school
    elif middle_count >= 2:
        return 12  # Middle school
    elif elementary_count >= 2:
        return 8   # Elementary
    else:
        return 10  # Conservative default

# =============================================================================
# ENHANCED RESPONSE GENERATION WITH GROQ
# =============================================================================

def generate_lumii_response(message, priority, trigger, student_age, student_name=""):
    """Generate intelligent response using Groq API with Lumii's personality - WORKING VERSION"""
    
    # Handle crisis situations with immediate hardcoded responses
    if priority == 'crisis':
        return """💙 I care about you so much, and I'm very concerned about what you're saying.

Please talk to a trusted adult RIGHT NOW:
• A parent, teacher, or family member
• Crisis Text Line: Text HOME to 741741
• Suicide & Crisis Lifeline: 988
• Or call 911 if you're in immediate danger

You matter, and there are people who want to help you. Please reach out to them immediately. 💙"""
    
    # For all other priorities, use Groq API with working structure
    tool_name = "Lumii"  # Default
    is_distressed = False
    
    if priority == 'emotional':
        tool_name = "Felicity"
        is_distressed = True
    elif priority == 'organization':
        tool_name = "Cali"
    elif priority == 'math':
        tool_name = "Mira"
    
    # Call the working API function
    with st.spinner("🧠 Lumii is thinking with care..."):
        ai_response, error, needs_fallback = get_groq_response_with_memory_safety(
            message, tool_name, student_age, student_name, is_distressed, temperature=0.7
        )
    
    if ai_response and not needs_fallback:
        return ai_response
    elif needs_fallback or error:
        # Use fallback response
        if priority == 'emotional':
            return f"💙 I can tell you're feeling something difficult right now. That's completely normal, and I'm here to support you. What's been on your mind?"
        elif priority == 'math':
            return f"🧮 I'd love to help you with this math problem! Let me work through it step by step with you. Can you show me what you're working on?"
        elif priority == 'organization':
            return f"📚 I can help you organize your schoolwork! Let's break down what you're dealing with into manageable pieces. What assignments are you working on?"
        else:
            return f"🌟 I'm here to help you learn and grow! What would you like to explore together today?"
    
    return "🌟 I'm here to help you learn and grow! What would you like to explore together today?"

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def initialize_session_state():
    """Initialize all session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "interaction_count" not in st.session_state:
        st.session_state.interaction_count = 0
    if "emotional_support_count" not in st.session_state:
        st.session_state.emotional_support_count = 0
    if "math_problems_solved" not in st.session_state:
        st.session_state.math_problems_solved = 0
    if "organization_help_count" not in st.session_state:
        st.session_state.organization_help_count = 0
    if "student_name" not in st.session_state:
        st.session_state.student_name = ""
    if "family_id" not in st.session_state:
        st.session_state.family_id = str(uuid.uuid4())[:8]

initialize_session_state()

# =============================================================================
# UI STYLING
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
    .crisis-response {
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
    .api-status {
        background: #f0f2f6;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# MAIN APP INTERFACE
# =============================================================================

# Header
st.markdown('<h1 class="main-header">🎓 My Friend Lumii</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Your emotionally intelligent AI learning companion! 💙</p>', unsafe_allow_html=True)

# API Status Check
api_key = get_groq_api_key()
if api_key:
    st.markdown('<div class="api-status">✅ Groq API Connected - Powered by Llama3-70B</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="api-status">⚠️ Groq API Key Required</div>', unsafe_allow_html=True)

# Sidebar
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
    
    # Stats
    st.subheader("📊 Our Learning Journey")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Conversations", st.session_state.interaction_count)
        st.metric("Math Problems", st.session_state.math_problems_solved)
    with col2:
        st.metric("Emotional Support", st.session_state.emotional_support_count)
        st.metric("Organization Help", st.session_state.organization_help_count)
    
    # How I Help explanation
    st.subheader("🛠️ How I Help You")
    st.markdown("""
    **💙 Emotional First** - I care about your feelings before your grades
    
    **🎯 Smart Priorities** - Feelings → Organization → Subjects → General
    
    **🧠 Powered by AI** - Groq + Llama3-70B for intelligent responses
    
    **👶➡️👨 Age-Appropriate** - I adapt my language to your age
    
    **🛡️ Always Safe** - I keep you protected and refer serious issues to adults
    """)

# Key differentiator callout
st.info("""
🌟 **What makes me special?** I'm the first AI tutor that cares about your feelings BEFORE your grades!

💙 **When you're stressed** → I help you feel better first, then tackle schoolwork  
🧠 **When you have questions** → I give smart, age-appropriate answers  
🛡️ **When you need help** → I connect you with trusted adults for serious stuff  
🌟 **Always** → I'm supportive, encouraging, and genuinely helpful!
""")

# Display chat history
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and "priority" in message:
            priority = message["priority"]
            
            if priority == "crisis":
                st.markdown(f'<div class="crisis-response">{message["content"]}</div>', unsafe_allow_html=True)
            elif priority == "emotional":
                st.markdown(f'<div class="emotional-response">{message["content"]}</div>', unsafe_allow_html=True)
            elif priority == "math":
                st.markdown(f'<div class="math-response">{message["content"]}</div>', unsafe_allow_html=True)
            elif priority == "organization":
                st.markdown(f'<div class="organization-response">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="general-response">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(message["content"])

# Chat input
prompt_placeholder = "How are you feeling about your studies today?" if not st.session_state.student_name else f"Hi {st.session_state.student_name}! How can I help you today?"

if prompt := st.chat_input(prompt_placeholder):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Detect priority and age
    priority, tool, safety_trigger = detect_priority_smart_with_safety(prompt)
    student_age = detect_age_from_message_and_history(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        response = generate_lumii_response(prompt, priority, safety_trigger, student_age, st.session_state.student_name)
        
        # Display with appropriate styling
        if priority == "crisis":
            st.markdown(f'<div class="crisis-response">{response}</div>', unsafe_allow_html=True)
        elif priority == "emotional":
            st.markdown(f'<div class="emotional-response">{response}</div>', unsafe_allow_html=True)
            st.session_state.emotional_support_count += 1
        elif priority == "math":
            st.markdown(f'<div class="math-response">{response}</div>', unsafe_allow_html=True)
            st.session_state.math_problems_solved += 1
        elif priority == "organization":
            st.markdown(f'<div class="organization-response">{response}</div>', unsafe_allow_html=True)
            st.session_state.organization_help_count += 1
        else:
            st.markdown(f'<div class="general-response">{response}</div>', unsafe_allow_html=True)
    
    # Add assistant response to chat
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response,
        "priority": priority,
        "student_age_detected": student_age
    })
    
    # Update interaction count
    st.session_state.interaction_count += 1
    
    # Rerun to update sidebar stats
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #667; margin-top: 2rem;'>
    <p><strong>My Friend Lumii</strong> - Powered by Groq + Llama3-70B 🧠</p>
    <p>💙 Feelings first • 🎯 Smart priorities • 🛡️ Always safe • 🌟 Age-appropriate</p>
    <p><em>The AI tutor that cares about your emotional wellbeing AND your learning</em></p>
</div>
""", unsafe_allow_html=True)
