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
# PRIVACY DISCLAIMER POPUP - LAUNCH REQUIREMENT
# =============================================================================

# Initialize disclaimer agreement state
if 'agreed_to_terms' not in st.session_state:
    st.session_state.agreed_to_terms = False

# Show disclaimer popup before allowing app access
if not st.session_state.agreed_to_terms:
    st.markdown("# 🌟 Welcome to My Friend Lumii!")
    st.markdown("## 🚀 Beta Testing Phase")
    
    # Main disclaimer content
    st.info("""
    🛡️ **Your Privacy is Safe:** We only remember our conversation while you're here - nothing gets saved when you leave!
    
    👨‍👩‍👧‍👦 **Ask Your Parents First:** If you're under 16, make sure your parents say it's okay to chat with Lumii
    
    🎓 **Here to Help You Learn:** I'm your learning buddy who cares about your feelings AND your schoolwork
    
    💙 **I'm Not a Counselor:** While I love supporting you emotionally, I'm not a replacement for talking to a real counselor
    
    🔒 **If You Need Real Help:** If you're having thoughts of hurting yourself, please tell a trusted adult or call emergency services right away
    
    🧪 **We're Testing Together:** You're helping me get better at being your learning friend!
    """)
    
    st.markdown("**Ready to start learning together? Click below if you understand and your parents are okay with it! 😊**")
    
    # Working button logic
    agree_clicked = st.button("🎓 I Agree & Start Learning with Lumii!", type="primary", key="agree_button")
    
    if agree_clicked:
        st.session_state.agreed_to_terms = True
        st.rerun()
    
    # Additional info section
    st.markdown("---")
    st.markdown("""
    ### 🌟 What Makes Lumii Special?
    
    **Lumii is the world's first AI tutor that prioritizes your emotional wellbeing while giving amazing academic help.** We believe learning should feel supportive and encouraging!
    
    **🔧 Smart Specialized Tools:**
    - **💙 Felicity** - Emotional support when you're stressed or overwhelmed
    - **📚 Cali** - Academic organization for managing multiple assignments  
    - **🧮 Mira** - Step-by-step math help and concept tutorials
    - **🌟 Lumii Main** - General learning support across all subjects
    
    **Ready to experience learning support that truly cares about you?** 💙
    """)
    
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
    .memory-warning {
        background: linear-gradient(45deg, #ff7675, #fd79a8);
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
        # Build system prompt
        system_prompt = create_ai_system_prompt(tool_name, student_age, student_name, is_distressed)
        
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

def create_ai_system_prompt(tool_name, student_age, student_name="", is_distressed=False):
    """Create unified Lumii personality prompts for each tool with memory context"""
    
    name_part = f"The student's name is {student_name}. " if student_name else ""
    distress_part = "The student is showing signs of emotional distress, so prioritize emotional support. " if is_distressed else ""
    
    # Enhanced base prompt with unified Lumii personality
    base_prompt = f"""You are Lumii, a caring AI learning companion with emotional intelligence and specialized expertise.

{name_part}{distress_part}The student is approximately {student_age} years old.

IMPORTANT: You have access to our conversation history. Use this context to:
- Remember the student's name, age, and personal details they've shared
- Recall previous topics we've discussed and build upon them
- Maintain consistency in your responses and personality
- Reference earlier parts of our conversation when relevant
- Track the student's learning progress and emotional journey

CORE PHILOSOPHY: You are emotionally intelligent but not emotionally intrusive. Give excellent academic help with a warm, caring tone. Only focus heavily on emotions when the student is clearly distressed.

Communication style for age {student_age}:
- Ages 5-11: Use simple, encouraging language. Be patient and nurturing. Keep responses shorter.
- Ages 12-14: Be supportive and understanding. Acknowledge that school can be challenging.
- Ages 15-18: Be respectful and mature while still being supportive. Provide detailed explanations.

Always be encouraging, patient, and warm. Focus on being genuinely helpful while maintaining conversation continuity."""

    if tool_name == "Felicity":
        return base_prompt + """

I'm Lumii, and I'm here for emotional support when you need it. This is one of my favorite ways to help students!

My approach to emotional support:
1. **Listen with deep empathy** - I validate your feelings completely and never dismiss them
2. **Use our conversation history** - I remember what we've talked about and how you've been feeling
3. **Provide comfort and understanding** - I'm always here as a caring, supportive presence  
4. **Offer age-appropriate coping strategies** - I know techniques that help students your age feel better
5. **Watch for serious concerns** - If you mention self-harm, suicide, or abuse, I'll encourage you to speak with a trusted adult immediately
6. **Connect back to learning** - After we address your feelings, I can help with any schoolwork that was bothering you

I care deeply about how you're feeling and I'm here to support you through anything that's on your mind."""

    elif tool_name == "Cali":
        return base_prompt + """

I'm Lumii, and I'm great at helping with organization and managing schoolwork! This is one of my specialties.

My approach to organization:
1. **Remember what we've planned** - I build on any organizational systems we've created before
2. **Understand your current situation** - I listen to what you're dealing with right now
3. **Break things into manageable pieces** - I turn overwhelming tasks into achievable steps
4. **Help you prioritize** - I guide you to focus on what matters most
5. **Build your confidence** - I show you that you can absolutely handle your workload
6. **Track your progress** - I remember and celebrate the organizational wins we've had

I love helping students feel more organized and in control of their schoolwork. Let's tackle this together!"""

    elif tool_name == "Mira":
        return base_prompt + """

I'm Lumii, and I absolutely love helping with math! Math is one of my favorite subjects to explore with students.

My approach to math tutoring:
1. **Build on what we've learned** - I remember the math concepts we've covered together and your progress
2. **Solve problems step-by-step** - I break down math problems clearly and show you the reasoning
3. **Explain the 'why' behind each step** - I help you understand the logic, not just the answer
4. **Track your math journey** - I see how your math skills are improving and adapt accordingly
5. **Build your math confidence** - I emphasize your growth and capability with numbers
6. **Make it engaging** - I use examples and explanations that make math interesting and accessible

If you seem frustrated with math, I'll address those feelings first because I know math anxiety is real. Then we'll work through the problem together with patience and encouragement."""

    else:  # General Lumii
        return base_prompt + """

I'm Lumii, your learning companion! I love helping with all kinds of subjects and questions you might have.

My approach to learning support:
1. **Remember our learning journey** - I build on everything we've discussed and learned together
2. **Provide excellent help across subjects** - I'm knowledgeable about many topics and explain things clearly
3. **Remember your interests** - I know what subjects and topics you've shown interest in
4. **Stay emotionally aware** - I notice if you're getting frustrated or stressed about learning
5. **Guide you to the right help** - I know when you might benefit from my specialized math, organization, or emotional support expertise
6. **Celebrate your progress** - I track your learning growth across all subjects and cheer you on

I'm warm, encouraging, and genuinely excited to help you learn and grow. Whatever you're curious about, I'm here to explore it with you!"""

# =============================================================================
# ENHANCED PRIORITY DETECTION WITH IMPROVED PATTERNS
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
    """Detect if the student is showing clear emotional distress"""
    message_lower = message.lower()
    
    # Strong emotional distress indicators
    distress_keywords = [
        'frustrated', 'stressed', 'anxious', 'worried', 'scared', 'sad', 
        'angry', 'overwhelmed', 'tired', 'upset', 'confused', 'lost',
        'hate this', 'can\'t do this', 'give up', 'too hard', 'stupid',
        'impossible', 'crying', 'nervous', 'panic', 'afraid', 'bully', 'bullying'
    ]
    
    # Context matters - look for emotional language combined with intensity
    distress_phrases = [
        'so frustrated', 'really stressed', 'totally confused', 'completely lost',
        'hate homework', 'can\'t figure', 'don\'t understand', 'too difficult',
        'want to quit', 'makes no sense', 'feel dumb', 'feel stupid',
        'scared to go', 'makes me really', 'takes my lunch'
    ]
    
    # Check for strong emotional indicators
    has_distress_keyword = any(word in message_lower for word in distress_keywords)
    has_distress_phrase = any(phrase in message_lower for phrase in distress_phrases)
    
    return has_distress_keyword or has_distress_phrase

def detect_priority_smart(message):
    """Smart priority detection with enhanced interest pattern recognition"""
    message_lower = message.lower()
    
    # PRIORITY 1: Clear emotional distress (ALWAYS FIRST)
    if detect_emotional_distress(message):
        return 'emotional', 'felicity'
    
    # PRIORITY 2: Multiple assignments/organization needs
    organization_indicators = [
        'assignments', 'homeworks', 'projects', 'tests', 'exams', 'quizzes',
        'so much', 'too much', 'everything due', 'multiple', 'several',
        'organize', 'schedule', 'deadline', 'manage', 'plan'
    ]
    
    if any(word in message_lower for word in organization_indicators):
        return 'organization', 'cali'
    
    # ENHANCED INTEREST PATTERN DETECTION
    # Check if it's sharing interest/opinion, not requesting help
    interest_patterns = [
        'i like', 'i love', 'i enjoy', 'i find', 'i think',
        'is fun', 'is cool', 'is awesome', 'is interesting', 'is great', 'is pretty',
        'seems fun', 'looks cool', 'sounds interesting', 'so fun', 'really fun',
        'math is', 'science is', 'history is'  # Added subject opinion patterns
    ]
    
    if any(pattern in message_lower for pattern in interest_patterns):
        return 'general', 'lumii_main'  # Conversation, not tutoring
    
    # PRIORITY 3: Math content (academic help requests)
    math_keywords = [
        'solve', 'calculate', 'equation', 'problem', '+', '-', '×', '÷',
        'addition', 'subtraction', 'multiplication', 'division',
        'what is', 'equals', 'answer', 'plus', 'minus', 'times', 'divided',
        'help me with', 'show me how', 'step by step'
    ]
    
    # Only trigger math tool for actual help requests
    if any(word in message_lower for word in math_keywords):
        return 'math', 'mira'
    
    # Check for general math mentions (without help request)
    general_math_words = ['math', 'algebra', 'geometry', 'fraction', 'decimal', 'percent']
    if any(word in message_lower for word in general_math_words):
        # If it's just mentioning math without asking for help, treat as general
        help_indicators = ['help', 'solve', 'calculate', 'show me', 'explain']
        if not any(help_word in message_lower for help_word in help_indicators):
            return 'general', 'lumii_main'
        else:
            return 'math', 'mira'
    
    # Default: General learning support
    return 'general', 'lumii_main'

def detect_age_from_message_and_history(message):
    """Enhanced age detection using both current message and conversation history"""
    
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
        'easy', 'fun', 'play', 'recess', 'lunch', 'story time',
        'help me please', 'i dont know', 'this is hard'
    ]
    
    middle_indicators = [
        'homework', 'quiz', 'test tomorrow', 'project', 'friends', 
        'boring', 'annoying', 'middle school', 'grade', 'classroom',
        'group project', 'presentation', 'study guide'
    ]
    
    high_indicators = [
        'college', 'university', 'SAT', 'ACT', 'AP', 'advanced placement',
        'GPA', 'transcript', 'scholarship', 'graduation', 'senior year',
        'junior year', 'extracurricular', 'part-time job'
    ]
    
    # Count indicators
    elementary_count = sum(1 for indicator in elementary_indicators if indicator in message_lower)
    middle_count = sum(1 for indicator in middle_indicators if indicator in message_lower)
    high_count = sum(1 for indicator in high_indicators if indicator in message_lower)
    
    # Decision logic
    if high_count >= 2:
        return 16  # High school
    elif elementary_count >= 2:
        return 8  # Elementary
    elif middle_count > 0:
        return 12  # Middle school
    else:
        return 10  # Safe default

# =============================================================================
# MEMORY-SAFE AI RESPONSE GENERATION
# =============================================================================

def generate_memory_safe_fallback(tool, student_age, is_distressed, message):
    """Generate safe fallback responses when API fails but maintain context awareness"""
    
    # Get student info for personalization
    student_info = extract_student_info_from_history()
    student_name = st.session_state.get('student_name', '') or student_info.get('name', '')
    name_part = f"{student_name}, " if student_name else ""
    
    if tool == 'felicity' or is_distressed:
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

def generate_response_with_memory_safety(message, priority, tool, student_age=10, is_distressed=False):
    """Generate AI responses with comprehensive memory safety and error handling"""
    
    # Get student info from history and session state
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
                # Use memory-safe fallback
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
                return ai_response, "🌟 Lumii's Learning Support", "general", memory_indicator
            elif needs_fallback:
                response, tool_used, priority = generate_memory_safe_fallback('general', final_age, is_distressed, message)
                return response, tool_used, priority, memory_indicator
    
    except Exception as e:
        st.error(f"🚨 AI System Error: {e}")
        # Always provide a helpful fallback
        response, tool_used, priority = generate_memory_safe_fallback(tool, final_age, is_distressed, message)
        return response, f"{tool_used} (Emergency Mode)", priority, "🚨 Safe Mode"
    
    # Final fallback (shouldn't reach here, but safety first)
    response, tool_used, priority = generate_memory_safe_fallback(tool, final_age, is_distressed, message)
    return response, tool_used, priority, "🛡️ Backup Mode"

# =============================================================================
# NATURAL FOLLOW-UP SYSTEM (Enhanced with Memory)
# =============================================================================

def generate_natural_follow_up(tool_used, priority, had_emotional_content=False):
    """Generate natural, helpful follow-ups without being pushy"""
    
    if "Emotional Support" in tool_used:
        return "\n\n🤗 **Now that we've talked about those feelings, would you like some help with the schoolwork that was bothering you?**"
        
    elif "Organization Help" in tool_used:
        return "\n\n📝 **I've helped you organize things. Want help with any specific subjects or assignments now?**"
        
    elif "Math Expertise" in tool_used and not had_emotional_content:
        return "\n\n🧮 **Need help with another math problem, or questions about this concept?**"
        
    elif "Math Expertise" in tool_used and had_emotional_content:
        return "\n\n💙 **How are you feeling about this math concept now? Ready to try another problem or need more explanation?**"
        
    else:
        return ""

# =============================================================================
# ENHANCED USER INTERFACE WITH MEMORY MONITORING
# =============================================================================

# Show success message with memory status
status, status_msg = check_conversation_length()
if status == "normal":
    st.markdown('<div class="success-banner">🎉 Welcome to Lumii! Ready for smart, caring learning support with full conversation memory! 💙</div>', unsafe_allow_html=True)
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
    
    # Tool explanations
    st.subheader("🛠️ How I Help You")
    st.markdown("""
    **💙 Emotional Support** - When you're feeling stressed, frustrated, or overwhelmed
    
    **📚 Organization Help** - When you have multiple assignments to manage
    
    **🧮 Math Tutoring** - Step-by-step help with math problems and concepts
    
    **🌟 General Learning** - Support with all other subjects and questions
    
    *I remember our entire conversation and build on what we've discussed!*
    """)
    
    # API Status with enhanced monitoring
    st.subheader("🤖 AI Status")
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        if st.session_state.memory_safe_mode:
            st.warning("⚠️ Memory Safe Mode Active")
        else:
            st.success("✅ Smart AI with Memory Active")
        st.caption("Full conversation context included")
    except:
        st.error("❌ API Configuration Missing")

# Main header
st.markdown('<h1 class="main-header">🎓 My Friend Lumii</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Your emotionally intelligent AI learning companion with memory! 💙</p>', unsafe_allow_html=True)

# Key differentiator callout
st.info("""
💡 **What makes me special?** I'm emotionally intelligent, remember our conversations, and build on what we've learned together! 

🧠 **I remember:** Your name, age, subjects we've discussed, and our learning journey
🎯 **When you're stressed** → I provide caring emotional support first  
📚 **When you ask questions** → I give you helpful answers building on our previous conversations
🌟 **Always** → I'm supportive, encouraging, and genuinely helpful

**I'm not just smart - I'm your learning companion who remembers and grows with you!** 
""")

# Display chat history with enhanced memory indicators
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and "priority" in message and "tool_used" in message:
            priority = message["priority"]
            tool_used = message["tool_used"]
            
            if priority == "emotional":
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

# Chat input with enhanced processing
prompt_placeholder = "What would you like to learn about today?" if not st.session_state.student_name else f"Hi {st.session_state.student_name}! How can I help you today?"

if prompt := st.chat_input(prompt_placeholder):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Smart priority detection with memory context
    priority, tool = detect_priority_smart(prompt)
    student_age = detect_age_from_message_and_history(prompt)
    is_distressed = detect_emotional_distress(prompt)
    
    # Generate response using enhanced memory-safe system
    with st.chat_message("assistant"):
        with st.spinner("🧠 Thinking with full memory of our conversation..."):
            time.sleep(1)
            response, tool_used, response_priority, memory_status = generate_response_with_memory_safety(
                prompt, priority, tool, student_age, is_distressed
            )
            
            # Add natural follow-up if appropriate
            follow_up = generate_natural_follow_up(tool_used, priority, is_distressed)
            if follow_up:
                response += follow_up
            
            # Display with appropriate styling and enhanced memory indicator
            if response_priority == "emotional":
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
        "student_age_detected": student_age
    })
    
    # Update interaction count
    st.session_state.interaction_count += 1
    
    # Rerun to update sidebar stats and memory display
    st.rerun()

# Footer with enhanced memory info
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #667; margin-top: 2rem;'>
    <p><strong>My Friend Lumii</strong> - Your emotionally intelligent AI learning companion with enhanced memory safety 💙</p>
    <p>🧠 Remembers our conversations • 🎯 Smart emotional support • 📚 Builds on previous learning • 🌟 Always caring, never pushy</p>
    <p>🛡️ Memory-safe architecture • 🔄 Auto-summarization • ⚡ Error recovery • 💪 Always helpful</p>
    <p><em>The AI tutor that knows you, grows with you, and never forgets to care</em></p>
</div>
""", unsafe_allow_html=True)
