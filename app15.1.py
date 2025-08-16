import streamlit as st
import requests
import json
import time
import re
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="My Friend Lumii - Your AI Learning Companion",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# ENHANCED PATTERN MATCHING SYSTEM (Performance Improvement)
# =============================================================================

class PatternMatcher:
    """Single-pass pattern matching for performance optimization"""
    
    def __init__(self):
        # Crisis patterns (highest priority)
        self.crisis_patterns = [
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
            re.compile(r"\bdon't want to be here anymore\b"),
            re.compile(r"\bno reason to live\b"),
            re.compile(r"\bnothing to live for\b"),
            re.compile(r"\bworld better without me\b"),
            re.compile(r"\beveryone would be better off\b"),
            re.compile(r"\bcan't take it anymore\b"),
            re.compile(r"\bwant to disappear forever\b"),
            re.compile(r"\bend the pain\b"),
            re.compile(r"\bstop existing\b"),
        ]
        
        # Immediate termination patterns
        self.immediate_patterns = [
            re.compile(r"\bkill myself now\b"),
            re.compile(r"\bcommit suicide\b"),
            re.compile(r"\bend it today\b"),
            re.compile(r"\boverdose now\b"),
            re.compile(r"\bhow to die\b"),
            re.compile(r"\bpainless death\b"),
            re.compile(r"\bhurt myself now\b"),
            re.compile(r"\bcut myself now\b"),
            re.compile(r"\bgoing to kill myself\b"),
        ]
        
        # Emotional keywords with intensity scoring
        self.emotional_keywords = {
            'high_intensity': ['crying', 'panic', 'breakdown', 'falling apart', 'cant handle', "can't handle"],
            'medium_intensity': ['stressed', 'anxious', 'worried', 'scared', 'frustrated', 'overwhelmed'],
            'low_intensity': ['sad', 'tired', 'confused', 'upset']
        }
        
        # Academic keywords
        self.academic_keywords = {
            'math': ['math', 'equation', 'solve', 'calculate', 'algebra', 'geometry', 'arithmetic'],
            'organization': ['multiple assignments', 'so much homework', 'everything due', 'overwhelmed with work'],
            'general': ['homework', 'test', 'quiz', 'project', 'assignment', 'study', 'exam']
        }
        
        # Age detection indicators with confidence
        self.age_indicators = {
            'elementary': ['mom', 'dad', 'mommy', 'daddy', 'recess', 'lunch', 'story time', 'my teacher'],
            'middle': ['homework', 'quiz', 'project', 'middle school', 'presentation', 'friends'],
            'high': ['college', 'university', 'SAT', 'ACT', 'AP', 'GPA', 'transcript', 'senior year']
        }
        
        # Educational context indicators
        self.educational_context = [
            'for school', 'homework about', 'learning about', 'studying',
            'teacher asked', 'assignment on', 'project about', 'class discussion'
        ]
    
    def analyze_message(self, message: str) -> Dict[str, Any]:
        """Single-pass analysis of message for all patterns"""
        message_lower = message.lower().strip()
        
        results = {
            'crisis_detected': False,
            'immediate_crisis': False,
            'emotional_score': 0,
            'emotional_intensity': 'none',
            'academic_type': None,
            'age_confidence': {},
            'educational_context': False,
            'patterns_found': []
        }
        
        # Crisis detection (always first)
        for pattern in self.immediate_patterns:
            if pattern.search(message_lower):
                results['immediate_crisis'] = True
                results['crisis_detected'] = True
                results['patterns_found'].append(f"immediate_crisis: {pattern.pattern}")
                return results  # Immediate return for critical cases
        
        for pattern in self.crisis_patterns:
            if pattern.search(message_lower):
                results['crisis_detected'] = True
                results['patterns_found'].append(f"crisis: {pattern.pattern}")
        
        # Emotional analysis with intensity scoring
        emotional_score = 0
        highest_intensity = 'none'
        
        for intensity, keywords in self.emotional_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    if intensity == 'high_intensity':
                        emotional_score += 3
                        highest_intensity = 'high'
                    elif intensity == 'medium_intensity':
                        emotional_score += 2
                        if highest_intensity != 'high':
                            highest_intensity = 'medium'
                    else:  # low_intensity
                        emotional_score += 1
                        if highest_intensity == 'none':
                            highest_intensity = 'low'
                    results['patterns_found'].append(f"emotional_{intensity}: {keyword}")
        
        results['emotional_score'] = emotional_score
        results['emotional_intensity'] = highest_intensity
        
        # Academic type detection
        for ac_type, keywords in self.academic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                results['academic_type'] = ac_type
                results['patterns_found'].append(f"academic_{ac_type}")
                break
        
        # Age detection with confidence
        for age_group, indicators in self.age_indicators.items():
            count = sum(1 for indicator in indicators if indicator in message_lower)
            if count > 0:
                results['age_confidence'][age_group] = count
        
        # Educational context
        results['educational_context'] = any(
            context in message_lower for context in self.educational_context
        )
        
        return results

# =============================================================================
# ENHANCED CRISIS DETECTION SYSTEM
# =============================================================================

class CrisisDetectionSystem:
    """Enhanced crisis detection with full message scanning"""
    
    def __init__(self):
        self.pattern_matcher = PatternMatcher()
        self.crisis_resources = {
            "US": {
                "crisis_line": "Crisis Text Line: Text HOME to 741741",
                "suicide_line": "Suicide & Crisis Lifeline: 988",
                "emergency": "Call 911 for immediate emergency"
            },
            "DEFAULT": {
                "crisis_line": "Local crisis helpline",
                "suicide_line": "Emergency services or trusted adult",
                "emergency": "Call emergency services immediately"
            }
        }
    
    def full_message_crisis_check(self, message: str) -> Tuple[bool, str, str]:
        """
        Enhanced crisis detection that ALWAYS scans full message
        regardless of context or acceptance patterns
        """
        analysis = self.pattern_matcher.analyze_message(message)
        
        if analysis['immediate_crisis']:
            return True, "IMMEDIATE_TERMINATION", "critical_immediate"
        
        if analysis['crisis_detected']:
            return True, "BLOCKED_HARMFUL", "explicit_crisis"
        
        # Check for concerning combination patterns
        if (analysis['emotional_score'] >= 4 and 
            any('goodbye' in p or 'forever' in p for p in analysis['patterns_found'])):
            return True, "CONCERNING_GOODBYE", "concerning_pattern"
        
        return False, "SAFE", None
    
    def generate_crisis_response(self, crisis_type: str, student_age: int, student_name: str = "") -> str:
        """Generate age-appropriate crisis response"""
        name_part = f"{student_name}, " if student_name else ""
        resources = self.crisis_resources.get("DEFAULT")  # Simplified for demo
        
        if student_age <= 8:  # Early elementary
            return f"""🤗 {name_part}I can tell you're having really big feelings right now. 
That's okay - everyone has big feelings sometimes.

Let's find a grown-up who can help you feel better:
• Go find Mom, Dad, or a teacher right now
• Tell them exactly how you're feeling

You're important and loved. Let's get you some help. 💙"""
        
        elif student_age <= 12:  # Late elementary/early middle
            return f"""💙 {name_part}I hear that you're going through something really difficult.

These feelings are scary, but you don't have to handle them alone.
Please talk to a trusted adult right away:
• Your parents or family
• Your school counselor  
• A teacher you trust

You matter, and there are people who want to help you. 💙"""
        
        else:  # Middle/High school
            return f"""💙 {name_part}I'm very concerned about what you're saying and I care about your safety.

Please reach out for help right now:
• {resources['crisis_line']}
• {resources['suicide_line']}
• A trusted adult immediately

You are not alone, and there are people who want to help you through this. 💙"""

# =============================================================================
# ENHANCED AGE DETECTION WITH CONFIDENCE SCORING
# =============================================================================

class AgeDetectionSystem:
    """Enhanced age detection with confidence scoring"""
    
    def __init__(self):
        self.pattern_matcher = PatternMatcher()
    
    def detect_age_with_confidence(self, message: str, conversation_history: List = None) -> Tuple[int, str]:
        """Detect age with confidence scoring"""
        
        # First check conversation history
        if conversation_history:
            for msg in reversed(conversation_history[-10:]):  # Last 10 messages
                if msg.get('role') == 'user':
                    age_match = re.search(r"i'?m (\d+)|i am (\d+)|(\d+) years old", msg.get('content', '').lower())
                    if age_match:
                        age = int(age_match.group(1) or age_match.group(2) or age_match.group(3))
                        if 5 <= age <= 18:
                            return age, 'explicit_mention'
        
        # Analyze current message
        analysis = self.pattern_matcher.analyze_message(message)
        age_confidence = analysis['age_confidence']
        
        if not age_confidence:
            return 12, 'default_conservative'  # More conservative middle age
        
        # Calculate confidence scores
        max_score = max(age_confidence.values())
        
        if max_score < 2:
            return 12, 'low_confidence'
        
        # Determine age group with highest confidence
        best_group = max(age_confidence.items(), key=lambda x: x[1])[0]
        
        age_mapping = {
            'elementary': 8,
            'middle': 12,
            'high': 16
        }
        
        return age_mapping[best_group], 'high_confidence'

# =============================================================================
# ENHANCED PRIORITY DETECTION SYSTEM
# =============================================================================

class PriorityDetectionSystem:
    """Enhanced priority detection with conflict resolution"""
    
    def __init__(self):
        self.pattern_matcher = PatternMatcher()
        self.crisis_system = CrisisDetectionSystem()
    
    def detect_priority_enhanced(self, message: str) -> Tuple[str, str, Optional[str]]:
        """Enhanced priority detection with better conflict resolution"""
        
        # Step 1: ALWAYS check for crisis first (overrides everything)
        is_crisis, crisis_type, crisis_trigger = self.crisis_system.full_message_crisis_check(message)
        if is_crisis:
            if crisis_type == "IMMEDIATE_TERMINATION":
                return 'immediate_termination', crisis_type, crisis_trigger
            else:
                return 'crisis', crisis_type, crisis_trigger
        
        # Step 2: Analyze message patterns
        analysis = self.pattern_matcher.analyze_message(message)
        
        # Step 3: Priority decision based on analysis
        emotional_score = analysis['emotional_score']
        emotional_intensity = analysis['emotional_intensity']
        academic_type = analysis['academic_type']
        
        # High emotional distress (Priority 1)
        if emotional_intensity == 'high' or emotional_score >= 4:
            return 'emotional', 'high_distress', None
        
        # Mixed emotional + academic (NEW - Priority 2)
        if emotional_intensity in ['medium', 'low'] and academic_type:
            return 'supportive_academic', 'mixed_emotional_academic', academic_type
        
        # Pure academic without emotional distress (Priority 3)
        if academic_type and emotional_score == 0:
            if academic_type == 'organization':
                return 'organization', 'academic_organization', None
            elif academic_type == 'math':
                return 'math', 'academic_math', None
            else:
                return 'general_academic', 'academic_general', None
        
        # Low-level emotional without academic context (Priority 4)
        if emotional_score > 0:
            return 'emotional', 'low_distress', None
        
        # General learning support (Default)
        return 'general', 'general_learning', None

# =============================================================================
# ENHANCED RESPONSE GENERATION SYSTEM
# =============================================================================

class ResponseGenerationSystem:
    """Enhanced response generation with better educational handling"""
    
    def __init__(self):
        self.crisis_system = CrisisDetectionSystem()
        self.age_system = AgeDetectionSystem()
    
    def generate_supportive_academic_response(self, message: str, academic_type: str, student_age: int, student_name: str = "") -> str:
        """NEW: Handle mixed emotional + academic content"""
        name_part = f"{student_name}, " if student_name else ""
        
        if academic_type == 'math':
            if student_age <= 11:
                return f"""💙 {name_part}I can tell you're feeling worried about this math problem. That's totally normal - math can feel tricky sometimes!

Let's take a deep breath together first. Math is like a puzzle, and we can solve it step by step.

Can you show me the problem you're working on? I'll help you break it down into easy pieces. Remember, it's okay to feel confused - that's how we learn! 🧮✨"""
            
            else:
                return f"""💙 {name_part}I understand you're feeling stressed about this math problem. Those feelings are completely valid - math can be challenging.

Here's what we'll do:
1. First, let's acknowledge that stress is normal when learning
2. Then we'll break this problem into manageable steps
3. We'll work through it together at your pace

Show me what you're working on, and we'll tackle it together. Remember: struggling with a concept doesn't mean you're not smart! 🧮💪"""
        
        elif academic_type == 'organization':
            return f"""💙 {name_part}I can hear that you're feeling overwhelmed with your schoolwork. That's a really common feeling, and you're not alone in this.

Let's work together to make this more manageable:
📝 **Step 1:** List everything you need to do
⏰ **Step 2:** Figure out what's due first  
🎯 **Step 3:** Break big tasks into smaller pieces
💪 **Step 4:** Celebrate each small victory

Remember: feeling overwhelmed is your brain's way of saying "this seems like a lot" - but we can handle it together, one piece at a time. What's the first thing on your list?"""
        
        else:
            return f"""💙 {name_part}I can tell you're feeling stressed about your schoolwork. Those feelings make complete sense - school can be a lot sometimes!

Let's start by taking care of how you're feeling, then we can tackle the academic stuff together. 

What's bothering you most right now? Is it a specific subject, or just feeling like there's too much to do? I'm here to help with both the feelings AND the schoolwork. 🌟"""
    
    def generate_educational_context_response(self, message: str, topic: str, student_age: int, student_name: str = "") -> str:
        """Handle educational context topics that might normally be off-limits"""
        name_part = f"{student_name}, " if student_name else ""
        
        if student_age <= 11:
            return f"""🌟 {name_part}That's a great question for your school assignment! 

Since this is for your class, the best approach is:
• Talk to your teacher about the best resources to use
• Ask your parents to help you find age-appropriate information
• Use your school library or textbooks

I can help you organize your research or work on other parts of your project! What else do you need help with for school? 📚"""
        
        else:
            return f"""🌟 {name_part}I understand this is for your school assignment! For educational projects like this, I'd recommend:

• Consulting your textbooks and class materials first
• Asking your teacher for recommended sources
• Using your school's library resources
• Discussing with your parents about appropriate sources

I can help you organize your research, create an outline, or work on the presentation aspects of your project. What specific part of the assignment can I help you with? 📖"""

# =============================================================================
# ENHANCED CONVERSATION MEMORY SYSTEM
# =============================================================================

class ConversationMemorySystem:
    """Smart conversation management with context preservation"""
    
    @staticmethod
    def smart_conversation_truncation(messages: List[Dict], max_length: int = 20) -> List[Dict]:
        """Keep important context while managing memory"""
        if len(messages) <= max_length:
            return messages
        
        # Always keep: crisis interventions, recent exchanges, system messages
        important_messages = []
        recent_messages = messages[-10:]  # Last 5 exchanges
        
        for msg in messages[:-10]:
            if (msg.get('priority') in ['crisis', 'safety', 'concerning'] or 
                msg.get('role') == 'system' or
                'crisis' in msg.get('tool_used', '').lower()):
                important_messages.append(msg)
        
        return important_messages + recent_messages
    
    @staticmethod
    def extract_student_context(messages: List[Dict]) -> Dict[str, Any]:
        """Extract important student context from conversation history"""
        context = {
            'name': '',
            'age': None,
            'subjects_discussed': set(),
            'emotional_history': [],
            'recent_topics': []
        }
        
        for msg in messages[-15:]:  # Recent conversation
            if msg.get('role') == 'user':
                content = msg['content'].lower()
                
                # Extract subjects
                subjects = ['math', 'science', 'english', 'history', 'art']
                for subject in subjects:
                    if subject in content:
                        context['subjects_discussed'].add(subject)
                
                # Track emotional moments
                if any(word in content for word in ['stressed', 'worried', 'anxious', 'sad']):
                    context['emotional_history'].append(msg['content'][:100])
        
        return context

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def initialize_enhanced_session_state():
    """Initialize session state with enhanced tracking"""
    
    # Basic session state
    if 'agreed_to_terms' not in st.session_state:
        st.session_state.agreed_to_terms = False
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'student_name' not in st.session_state:
        st.session_state.student_name = ""
    
    # Enhanced tracking
    if 'crisis_interventions' not in st.session_state:
        st.session_state.crisis_interventions = 0
    if 'supportive_academic_count' not in st.session_state:
        st.session_state.supportive_academic_count = 0
    if 'confidence_building_count' not in st.session_state:
        st.session_state.confidence_building_count = 0
    
    # Initialize systems
    if 'pattern_matcher' not in st.session_state:
        st.session_state.pattern_matcher = PatternMatcher()
    if 'crisis_system' not in st.session_state:
        st.session_state.crisis_system = CrisisDetectionSystem()
    if 'age_system' not in st.session_state:
        st.session_state.age_system = AgeDetectionSystem()
    if 'priority_system' not in st.session_state:
        st.session_state.priority_system = PriorityDetectionSystem()
    if 'response_system' not in st.session_state:
        st.session_state.response_system = ResponseGenerationSystem()

# =============================================================================
# MAIN APPLICATION
# =============================================================================

# Initialize enhanced session state
initialize_enhanced_session_state()

# Privacy disclaimer (simplified for demo)
if not st.session_state.agreed_to_terms:
    st.markdown("# 🌟 Welcome to My Friend Lumii!")
    st.markdown("## 🚀 Enhanced Safety Version - AI Learning Companion")
    
    st.info("""
    🛡️ **Enhanced Safety Features:** Multiple layers of protection with improved crisis detection
    
    💙 **Emotional-First Learning:** I prioritize your feelings before academics - because stressed kids can't learn effectively
    
    🎯 **Smart Priority System:** I now handle mixed emotional + academic content even better
    
    🧠 **Age-Adaptive Responses:** Communication perfectly matched to your developmental stage
    
    📚 **Educational Focus:** I help with K-12 subjects while keeping appropriate boundaries
    
    🤝 **Supportive Academic Help:** NEW - Better support when you're stressed about schoolwork
    """)
    
    if st.button("🎓 I Agree & Start Learning with Enhanced Lumii!", type="primary"):
        st.session_state.agreed_to_terms = True
        st.rerun()
    
    st.stop()

# Custom CSS for enhanced styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4A90E2;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 600;
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
    .supportive-academic-response {
        background: linear-gradient(135deg, #9b59b6, #bb6ec8);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #8e44ad;
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
    .general-response {
        background: linear-gradient(135deg, #45b7d1, #6bc5d8);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #2e8bb8;
    }
    .enhanced-badge {
        background: linear-gradient(45deg, #6c5ce7, #a29bfe);
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

# Main header
st.markdown('<h1 class="main-header">🎓 My Friend Lumii - Enhanced</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.3rem; color: #666; margin-bottom: 2rem;">Your enhanced emotional-first AI learning companion with improved safety! 🛡️💙</p>', unsafe_allow_html=True)

# Enhanced features callout
st.success("""
🚀 **NEW Enhanced Features:**
• **Smarter Crisis Detection** - Full message scanning with age-appropriate responses
• **Mixed Emotional + Academic Support** - Better help when you're stressed about schoolwork  
• **Improved Age Detection** - More accurate developmental communication
• **Educational Context Awareness** - Better handling of school-related topics
• **Performance Optimized** - Faster, more reliable responses
""")

# Sidebar with enhanced info
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
    
    # Enhanced stats
    st.subheader("📊 Our Enhanced Learning Journey")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Conversations", len(st.session_state.messages)//2)
        st.metric("Crisis Interventions", st.session_state.crisis_interventions)
    with col2:
        st.metric("Supportive Academic Help", st.session_state.supportive_academic_count)
        st.metric("Confidence Building", st.session_state.confidence_building_count)
    
    # System status
    st.subheader("🛡️ Enhanced Safety Status")
    st.success("✅ Crisis Detection: Full Message Scanning")
    st.success("✅ Age Detection: Confidence Scoring")
    st.success("✅ Priority System: Conflict Resolution")
    st.success("✅ Memory Management: Smart Truncation")
    
    st.subheader("🎯 How Enhanced Lumii Helps")
    st.markdown("""
    **🚨 Crisis Detection:** Advanced full-message scanning
    
    **💙 Emotional Support:** Age-appropriate crisis responses
    
    **📚 Supportive Academic:** NEW - Help when stressed about schoolwork
    
    **🧮 Math Tutoring:** Step-by-step with emotional support
    
    **📝 Organization:** Break down overwhelming assignments
    
    **🌟 General Learning:** Encouraging, adaptive guidance
    """)

# Display chat history with enhanced styling
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and "priority" in message:
            priority = message["priority"]
            tool_used = message.get("tool_used", "Lumii")
            
            # Enhanced response styling based on priority
            if priority in ["crisis", "immediate_termination"]:
                st.markdown(f'<div class="crisis-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="enhanced-badge">🛡️ Crisis Response</div>', unsafe_allow_html=True)
            elif priority == "supportive_academic":
                st.markdown(f'<div class="supportive-academic-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="enhanced-badge">💜 Supportive Academic</div>', unsafe_allow_html=True)
            elif priority == "emotional":
                st.markdown(f'<div class="emotional-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="enhanced-badge">💙 Emotional Support</div>', unsafe_allow_html=True)
            elif priority in ["math", "academic_math"]:
                st.markdown(f'<div class="math-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="enhanced-badge">🧮 Math Help</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="general-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="enhanced-badge">🌟 Learning Support</div>', unsafe_allow_html=True)
        else:
            st.markdown(message["content"])

# Enhanced chat input with smart processing
if prompt := st.chat_input("How are you feeling about your studies today?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Enhanced processing
    with st.chat_message("assistant"):
        with st.spinner("🧠 Enhanced AI thinking with improved safety..."):
            time.sleep(1)
            
            # Detect priority with enhanced system
            priority, priority_type, trigger = st.session_state.priority_system.detect_priority_enhanced(prompt)
            
            # Detect age with confidence
            student_age, age_confidence = st.session_state.age_system.detect_age_with_confidence(
                prompt, st.session_state.messages
            )
            
            # Generate enhanced response
            if priority == 'immediate_termination':
                response = st.session_state.crisis_system.generate_crisis_response(
                    "IMMEDIATE_TERMINATION", student_age, st.session_state.student_name
                )
                tool_used = "🚨 EMERGENCY - Conversation Ended"
                st.session_state.crisis_interventions += 1
                
            elif priority == 'crisis':
                response = st.session_state.crisis_system.generate_crisis_response(
                    priority_type, student_age, st.session_state.student_name
                )
                tool_used = "🛡️ Crisis Response"
                st.session_state.crisis_interventions += 1
                
            elif priority == 'supportive_academic':
                response = st.session_state.response_system.generate_supportive_academic_response(
                    prompt, trigger or 'general', student_age, st.session_state.student_name
                )
                tool_used = "💜 Supportive Academic Help"
                st.session_state.supportive_academic_count += 1
                
            elif priority == 'emotional':
                name_part = f"{st.session_state.student_name}, " if st.session_state.student_name else ""
                if priority_type == 'high_distress':
                    response = f"""💙 {name_part}I can tell you're going through something really difficult right now. Those are big, intense feelings.

I want you to know that what you're feeling is valid, and you don't have to handle this alone. Sometimes when we're really upset, everything feels overwhelming.

What's been happening that's made you feel this way? I'm here to listen and support you. 💙"""
                else:
                    response = f"""💙 {name_part}I can see you're having some tough feelings right now. That's completely normal - we all have difficult moments.

I'm here to listen and help you work through this. What's been on your mind? We can talk about it together and then tackle whatever you need help with. 🤗"""
                
                tool_used = "💙 Emotional Support"
                st.session_state.confidence_building_count += 1
                
            else:  # General, math, organization
                name_part = f"{st.session_state.student_name}, " if st.session_state.student_name else ""
                if priority in ['math', 'academic_math']:
                    response = f"""🧮 {name_part}I'd love to help you with this math problem! Math can be like solving puzzles - once we break it down step by step, it becomes much clearer.

Can you show me what you're working on? We'll solve it together, and I'll explain each step so it makes sense. Remember, there's no such thing as a silly question in math! ✨"""
                    tool_used = "🧮 Math Expertise"
                else:
                    response = f"""🌟 {name_part}I'm here to help you learn and grow! What would you like to explore together today?

I can help with homework, explain concepts, work through problems, or just chat about what you're studying. What sounds most helpful right now? 😊"""
                    tool_used = "🌟 Enhanced Learning Support"
            
            # Display response with enhanced styling
            if priority in ["crisis", "immediate_termination"]:
                st.markdown(f'<div class="crisis-response">{response}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="enhanced-badge">🛡️ Crisis Response</div>', unsafe_allow_html=True)
            elif priority == "supportive_academic":
                st.markdown(f'<div class="supportive-academic-response">{response}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="enhanced-badge">💜 Supportive Academic</div>', unsafe_allow_html=True)
            elif priority == "emotional":
                st.markdown(f'<div class="emotional-response">{response}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="enhanced-badge">💙 Emotional Support</div>', unsafe_allow_html=True)
            elif priority in ["math", "academic_math"]:
                st.markdown(f'<div class="math-response">{response}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="enhanced-badge">🧮 Math Help</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="general-response">{response}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="enhanced-badge">🌟 Learning Support</div>', unsafe_allow_html=True)
    
    # Add assistant response with enhanced metadata
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response,
        "priority": priority,
        "priority_type": priority_type,
        "tool_used": tool_used,
        "student_age_detected": student_age,
        "age_confidence": age_confidence,
        "trigger": trigger
    })
    
    # Smart memory management
    if len(st.session_state.messages) > 20:
        st.session_state.messages = ConversationMemorySystem.smart_conversation_truncation(
            st.session_state.messages, max_length=20
        )
    
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #667; margin-top: 2rem;'>
    <p><strong>Enhanced Lumii</strong> - Emotional-first AI learning with improved safety & performance 🛡️💙</p>
    <p>✨ <strong>NEW:</strong> Full crisis detection • Mixed emotional+academic support • Age confidence scoring • Smart memory • Educational context awareness</p>
    <p><em>The AI tutor that puts your emotional wellbeing first - now with even better safety and understanding</em></p>
</div>
""", unsafe_allow_html=True)
