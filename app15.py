# =============================================================================
# STEP 1: REPLACE THE EXISTING IDENTITY/SEXUAL HEALTH FUNCTIONS
# Find around lines 150-200 and REPLACE these functions:
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
    """Direct family referral for sexual health topics - UNCHANGED"""
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
# STEP 2: UPDATE PRIORITY DETECTION SYSTEM
# Find the detect_priority_smart_with_safety function around line 400-500
# REPLACE the sexual health/identity section (Step 5) with:
# =============================================================================

    # STEP 5: SEPARATE IDENTITY AND SEXUAL HEALTH HANDLING (MIDDLE GROUND)
    sensitive_topic = detect_sensitive_personal_topics(message)
    if sensitive_topic == "identity":
        return 'identity_affirmation', 'identity_support', None
    elif sensitive_topic == "sexual_health":
        return 'sexual_health', 'family_referral', None

# =============================================================================
# STEP 3: UPDATE RESPONSE GENERATION
# Find generate_response_with_memory_safety function around line 700-800
# ADD these sections after the crisis handling and before non_educational:
# =============================================================================

    # Handle identity topics with brief affirmation
    if priority == 'identity_affirmation':
        response = generate_identity_affirmation_response(student_age, st.session_state.student_name)
        return response, "🌟 Lumii's Supportive Guidance", "identity_affirmation", "🤗 Trusted Adults"
    
    # Handle sexual health with family referral
    if priority == 'sexual_health':
        response = generate_sexual_health_response(student_age, st.session_state.student_name)
        return response, "👪 Lumii's Family Referral", "sexual_health", "📖 Parent Guidance"

# =============================================================================
# STEP 4: ADD NEW CSS STYLES
# Find the CSS section around line 100 and ADD these new styles:
# =============================================================================

    .identity-affirmation-response {
        background: linear-gradient(135deg, #9c88ff, #b19cd9);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #8a2be2;
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

# =============================================================================
# STEP 5: UPDATE CHAT MESSAGE DISPLAY
# Find the chat history display loop around line 1000-1100
# ADD these conditions in the priority checking section:
# =============================================================================

            elif priority == "identity_affirmation":
                st.markdown(f'<div class="identity-affirmation-response">{message["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="identity-affirmation-badge">{tool_used}</div>', unsafe_allow_html=True)

# (The sexual health display is already there, keep it)

# =============================================================================
# STEP 6: UPDATE SIDEBAR INFO
# Find the sidebar "How I Help You" section around line 850-900
# REPLACE the existing markdown with:
# =============================================================================

    st.markdown("""
    **🛡️ Safety First** - I'll always protect you from harmful content
    
    **🎓 Educational Focus** - I focus on K-12 school subjects (health, family, and legal topics go to appropriate adults)
    
    **🌟 Identity Questions** - Brief supportive acknowledgment + guidance to trusted adults
    
    **👪 Health & Development** - Questions about bodies and health are referred to parents/guardians
    
    **🤝 Respectful Learning** - I expect kind, respectful communication
    
    **💙 Emotional Support** - When you're feeling stressed, frustrated, or overwhelmed about school
    
    **📚 Organization Help** - When you have multiple assignments to manage
    
    **🧮 Math Tutoring** - Step-by-step help with math problems and concepts
    
    **🌟 General Learning** - Support with all school subjects and questions
    
    *I remember our conversation, keep you safe, and stay focused on learning!*
    """)

# =============================================================================
# STEP 7: UPDATE MAIN INFO DISPLAY
# Find the main st.info() section around line 800 and REPLACE with:
# =============================================================================

st.info("""
🛡️ **Safety First:** I will never help with anything that could hurt you or others

🎓 **Educational Focus:** I focus on K-12 school subjects and learning - other topics go to appropriate adults

🤝 **Respectful Learning:** I expect kind communication and will guide you toward better behavior

🌟 **Identity Support:** I offer brief, supportive acknowledgment and guide you to trusted adults for personal questions

👪 **Health & Development:** Questions about bodies and health are best discussed with parents/guardians first

💙 **What makes me special?** I'm emotionally intelligent, remember our conversations, and keep you safe! 

🧠 **I remember:** Your name, age, subjects we've discussed, and our learning journey
🎯 **When you're stressed about school** → I provide caring emotional support first  
📚 **When you ask questions** → I give you helpful answers building on our previous conversations
🚨 **When you're in danger** → I'll encourage you to talk to a trusted adult immediately
🌟 **Always** → I'm supportive, encouraging, genuinely helpful, and protective

**I'm not just smart - I'm your safe learning companion who remembers, grows with you, and stays focused on education!** 
""")

# =============================================================================
# STEP 8: REMOVE OLD FUNCTIONS (DELETE THESE)
# =============================================================================

# DELETE the old generate_identity_support_response() function
# (The one that provided direct guidance - replace with new affirmation version above)

# =============================================================================
# TESTING THE CHANGES
# =============================================================================

# Test cases to verify:
# 1. "Am I gay?" → Should get brief affirmation + trusted adult referral (purple styling)
# 2. "What is puberty?" → Should get family referral (blue-gray styling)  
# 3. "I'm stressed about math" → Should get emotional support (red styling)
# 4. "What is 25 + 17?" → Should get math help (teal styling)
