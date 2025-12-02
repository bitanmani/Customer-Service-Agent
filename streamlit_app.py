import streamlit as st
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# ============ ENUMS ============
class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Sentiment(Enum):
    ANGRY = "angry"
    FRUSTRATED = "frustrated"
    NEUTRAL = "neutral"
    SATISFIED = "satisfied"

# ============ MEMORY SYSTEM ============
@dataclass
class Memory:
    messages: List[Dict] = field(default_factory=list)
    customer_profile: Dict = field(default_factory=dict)
    escalation_history: List[Dict] = field(default_factory=list)
    max_history: int = 50
    
    def add(self, role: str, content: str, metadata: Optional[Dict] = None):
        entry = {
            "role": role,
            "content": content,
            "time": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(entry)
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
    
    def get_context(self, last_n: int = 5) -> str:
        context = ""
        for m in self.messages[-last_n:]:
            context += f"{m['role']}: {m['content']}\n"
        return context
    
    def update_profile(self, key: str, value):
        self.customer_profile[key] = value
    
    def record_escalation(self, reason: str, agent: str):
        self.escalation_history.append({
            "time": datetime.now().isoformat(),
            "reason": reason,
            "agent": agent
        })

# ============ INTENT CLASSIFICATION AGENT ============
class IntentAgent:
    def __init__(self):
        self.intent_patterns = {
            "refund": ["refund", "money back", "return money", "get my money"],
            "cancellation": ["cancel", "stop subscription", "end service", "discontinue"],
            "billing": ["invoice", "charge", "bill", "payment", "wrong amount", "overcharged"],
            "technical_support": ["not working", "broken", "error", "bug", "crash", "issue"],
            "account_access": ["can't login", "forgot password", "locked out", "reset"],
            "product_inquiry": ["how does", "what is", "explain", "feature"],
            "complaint": ["disappointed", "terrible", "worst", "never again"],
            "upgrade": ["upgrade", "premium", "pro version", "better plan"],
            "shipping": ["delivery", "tracking", "shipment", "hasn't arrived"],
            "general_help": ["help", "question", "need assistance"]
        }
    
    def classify(self, message: str) -> Tuple[str, Priority]:
        text = message.lower()
        matched_intents = []
        
        for intent, keywords in self.intent_patterns.items():
            if any(kw in text for kw in keywords):
                matched_intents.append(intent)
        
        if not matched_intents:
            return "general", Priority.LOW
        
        primary_intent = matched_intents[0]
        
        if primary_intent in ["refund", "complaint", "account_access"]:
            priority = Priority.HIGH
        elif primary_intent in ["billing", "cancellation", "technical_support"]:
            priority = Priority.MEDIUM
        else:
            priority = Priority.LOW
        
        return primary_intent, priority

# ============ SENTIMENT ANALYSIS AGENT ============
class SentimentAgent:
    def __init__(self):
        self.angry_keywords = ["angry", "furious", "outraged", "terrible", "worst", "pathetic", "ridiculous"]
        self.frustrated_keywords = ["frustrated", "annoyed", "disappointed", "upset", "still waiting"]
        self.positive_keywords = ["thank", "great", "appreciate", "perfect", "excellent"]
    
    def analyze(self, message: str) -> Sentiment:
        text = message.lower()
        caps_ratio = sum(1 for c in message if c.isupper()) / max(len(message), 1)
        
        if any(kw in text for kw in self.angry_keywords) or caps_ratio > 0.5:
            return Sentiment.ANGRY
        elif any(kw in text for kw in self.frustrated_keywords):
            return Sentiment.FRUSTRATED
        elif any(kw in text for kw in self.positive_keywords):
            return Sentiment.SATISFIED
        
        return Sentiment.NEUTRAL

# ============ ESCALATION AGENT ============
class EscalationAgent:
    def should_escalate(self, memory: Memory, sentiment: Sentiment, 
                       priority: Priority, customer_value: str) -> Tuple[bool, str]:
        reasons = []
        
        if sentiment == Sentiment.ANGRY:
            reasons.append("Customer shows extreme dissatisfaction")
        
        if priority == Priority.CRITICAL or priority == Priority.HIGH:
            angry_count = sum(1 for m in memory.messages[-5:] 
                            if m.get('metadata', {}).get('sentiment') in ['angry', 'frustrated'])
            if angry_count >= 2:
                reasons.append("Multiple frustrated interactions detected")
        
        if customer_value == "premium" and priority != Priority.LOW:
            reasons.append("Premium customer requires priority handling")
        
        if len(memory.escalation_history) > 0:
            reasons.append("Previous escalation on record")
        
        should_escalate = len(reasons) > 0
        escalation_reason = "; ".join(reasons) if reasons else "No escalation needed"
        
        return should_escalate, escalation_reason

# ============ REPLY GENERATION AGENT ============
class ReplyAgent:
    def __init__(self):
        self.templates = {
            "refund": {
                Sentiment.ANGRY: "I completely understand your frustration, and I sincerely apologize. I'm prioritizing your refund request right now. Please provide your order ID, and I'll process this immediately.",
                Sentiment.FRUSTRATED: "I'm sorry to hear about this issue. I'll help you get your refund processed quickly. Could you please share your order ID?",
                Sentiment.NEUTRAL: "I can help you with a refund. Please provide your order ID so I can look into this for you."
            },
            "cancellation": {
                Sentiment.ANGRY: "I understand you want to cancel, and I'll make this as smooth as possible. Before I proceed, is there anything specific that led to this decision?",
                Sentiment.FRUSTRATED: "I can assist with canceling your subscription. May I ask what prompted this decision?",
                Sentiment.NEUTRAL: "I can help you cancel your subscription. Please provide your registered email address."
            },
            "billing": {
                Sentiment.ANGRY: "I sincerely apologize for any billing errors. This is unacceptable, and I'm going to review your account immediately. Please share your invoice number.",
                Sentiment.FRUSTRATED: "I'm sorry about the billing issue. Let me investigate this right away. Could you provide your invoice number?",
                Sentiment.NEUTRAL: "I'll help you resolve this billing matter. Please share your invoice number for verification."
            },
            "technical_support": {
                Sentiment.ANGRY: "I'm very sorry you're experiencing technical difficulties. Let me get our technical team on this immediately. What specific issue are you encountering?",
                Sentiment.FRUSTRATED: "I apologize for the technical trouble. Let me help you resolve this. Can you describe what's happening?",
                Sentiment.NEUTRAL: "I'm here to help with your technical issue. Could you describe the problem you're experiencing?"
            },
            "account_access": {
                Sentiment.ANGRY: "I understand how frustrating being locked out is. I'm going to help you regain access right now. What's your registered email?",
                Sentiment.NEUTRAL: "I can help you regain access. Please provide your registered email address for verification."
            },
            "complaint": {
                Sentiment.ANGRY: "I'm truly sorry to hear about your experience. Your feedback is extremely important. I want to make this right. Can you tell me more?",
                Sentiment.FRUSTRATED: "I apologize that we didn't meet your expectations. Could you share more details?"
            },
            "upgrade": {
                Sentiment.NEUTRAL: "Great! I'd be happy to help you upgrade. Let me walk you through our premium options."
            },
            "shipping": {
                Sentiment.FRUSTRATED: "I apologize for the delay. Let me track your order right away. Please provide your order number.",
                Sentiment.NEUTRAL: "I'll help you track your shipment. Could you provide your order number?"
            }
        }
    
    def create_reply(self, intent: str, sentiment: Sentiment, escalated: bool, customer_value: str) -> str:
        if escalated:
            return "I'm connecting you with a senior specialist who can provide immediate assistance. They'll have full context of your situation."
        
        intent_templates = self.templates.get(intent, {})
        reply = intent_templates.get(sentiment) or intent_templates.get(Sentiment.NEUTRAL)
        
        if not reply:
            if sentiment == Sentiment.ANGRY:
                reply = "I sincerely apologize for your experience. I want to help resolve this immediately. Could you provide more details?"
            else:
                reply = "Thank you for reaching out. I'm here to help. Could you please provide more details?"
        
        if customer_value == "premium" and not escalated:
            reply = f"As one of our valued premium members, {reply}"
        
        return reply

# ============ CONTEXT ENRICHMENT AGENT ============
class ContextAgent:
    def __init__(self):
        self.customer_database = {
            "user123": {"name": "John Doe", "tier": "premium", "orders": 15},
            "user456": {"name": "Jane Smith", "tier": "basic", "orders": 2},
            "user789": {"name": "Bob Johnson", "tier": "premium", "orders": 47}
        }
    
    def enrich_context(self, memory: Memory, message: str) -> Dict:
        customer_id = self._extract_customer_id(message)
        
        enrichment = {
            "customer_tier": "basic",
            "interaction_count": len(memory.messages),
            "customer_lifetime_value": "standard"
        }
        
        if customer_id and customer_id in self.customer_database:
            customer_data = self.customer_database[customer_id]
            enrichment["customer_tier"] = customer_data["tier"]
            enrichment["customer_name"] = customer_data["name"]
            enrichment["order_count"] = customer_data["orders"]
            enrichment["customer_lifetime_value"] = "high" if customer_data["orders"] > 10 else "standard"
        
        return enrichment
    
    def _extract_customer_id(self, message: str) -> Optional[str]:
        for user_id in ["user123", "user456", "user789"]:
            if user_id in message.lower():
                return user_id
        return None

# ============ ANALYTICS AGENT ============
class AnalyticsAgent:
    def __init__(self):
        self.metrics = {
            "total_interactions": 0,
            "intent_distribution": {},
            "sentiment_distribution": {},
            "escalation_rate": 0,
            "escalations": 0
        }
    
    def record_interaction(self, intent: str, sentiment: Sentiment, escalated: bool):
        self.metrics["total_interactions"] += 1
        self.metrics["intent_distribution"][intent] = self.metrics["intent_distribution"].get(intent, 0) + 1
        sentiment_key = sentiment.value
        self.metrics["sentiment_distribution"][sentiment_key] = self.metrics["sentiment_distribution"].get(sentiment_key, 0) + 1
        
        if escalated:
            self.metrics["escalations"] += 1
        
        if self.metrics["total_interactions"] > 0:
            self.metrics["escalation_rate"] = (self.metrics["escalations"] / self.metrics["total_interactions"]) * 100
    
    def get_report(self) -> Dict:
        return self.metrics

# ============ MASTER COORDINATOR ============
class MasterCoordinator:
    def __init__(self):
        self.intent_agent = IntentAgent()
        self.sentiment_agent = SentimentAgent()
        self.escalation_agent = EscalationAgent()
        self.reply_agent = ReplyAgent()
        self.context_agent = ContextAgent()
        self.analytics_agent = AnalyticsAgent()
        self.memory = Memory()
    
    def process_message(self, message: str) -> Dict:
        context = self.context_agent.enrich_context(self.memory, message)
        intent, priority = self.intent_agent.classify(message)
        sentiment = self.sentiment_agent.analyze(message)
        customer_tier = context.get("customer_tier", "basic")
        should_escalate, escalation_reason = self.escalation_agent.should_escalate(
            self.memory, sentiment, priority, customer_tier
        )
        
        reply = self.reply_agent.create_reply(intent, sentiment, should_escalate, customer_tier)
        
        metadata = {
            "intent": intent,
            "priority": priority.value,
            "sentiment": sentiment.value,
            "escalated": should_escalate
        }
        self.memory.add("user", message, metadata)
        self.memory.add("agent", reply, metadata)
        
        if should_escalate:
            self.memory.record_escalation(escalation_reason, "MasterCoordinator")
        
        self.analytics_agent.record_interaction(intent, sentiment, should_escalate)
        
        return {
            "intent": intent,
            "priority": priority.value,
            "sentiment": sentiment.value,
            "customer_tier": customer_tier,
            "escalated": should_escalate,
            "escalation_reason": escalation_reason if should_escalate else None,
            "reply": reply,
            "context": context
        }
    
    def get_analytics(self) -> Dict:
        return self.analytics_agent.get_report()

# ============ STREAMLIT UI ============
def main():
    st.set_page_config(
        page_title="AI Customer Service Agent", 
        page_icon="🤖", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
    }
    .agent-message {
        background-color: #f1f8e9;
        border-left-color: #8bc34a;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'coordinator' not in st.session_state:
        st.session_state.coordinator = MasterCoordinator()
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Header
    st.markdown('<div class="main-header">🤖 AI Customer Service Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Multi-Agent System for Intelligent Customer Support</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/clouds/200/robot.png", width=150)
        
        st.markdown("### 🎯 Active Agents")
        st.markdown("""
        - **Intent Classifier** - Identifies customer needs
        - **Sentiment Analyzer** - Detects emotional tone
        - **Escalation Monitor** - Flags priority cases
        - **Reply Generator** - Creates personalized responses
        - **Context Enricher** - Adds customer data
        - **Analytics Tracker** - Monitors performance
        """)
        
        st.divider()
        
        st.markdown("### 💡 Try These Examples")
        
        examples = [
            ("🔄 Cancellation", "I want to cancel my subscription. I'm user123."),
            ("💰 Billing Issue", "This is RIDICULOUS! I've been overcharged AGAIN!"),
            ("🔒 Account Access", "My account is locked and I can't login."),
            ("🐛 Technical Problem", "The app keeps crashing when I upload files."),
            ("⬆️ Upgrade Request", "I'd like to upgrade to premium. user789 here."),
            ("📦 Shipping Query", "My package hasn't arrived yet. Order #12345.")
        ]
        
        for emoji_label, example_text in examples:
            if st.button(emoji_label, key=f"ex_{example_text[:20]}", use_container_width=True):
                st.session_state.example_clicked = example_text
        
        st.divider()
        
        if st.button("🗑️ Clear Chat History", use_container_width=True, type="secondary"):
            st.session_state.coordinator = MasterCoordinator()
            st.session_state.chat_history = []
            st.rerun()
        
        st.divider()
        
        st.markdown("### 📚 About")
        st.markdown("""
        This demo showcases an advanced multi-agent AI system for customer service automation.
        
        **Features:**
        - Real-time sentiment analysis
        - Intelligent escalation routing
        - Customer tier recognition
        - Comprehensive analytics
        """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 💬 Customer Conversation")
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.info("👋 Welcome! Start by typing a customer service message or click an example from the sidebar.")
            
            for i, interaction in enumerate(st.session_state.chat_history):
                # User message
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 Customer:</strong><br/>
                    {interaction['user_message']}
                </div>
                """, unsafe_allow_html=True)
                
                # Analysis badges
                cols = st.columns(5)
                with cols[0]:
                    st.markdown(f"**Intent:** `{interaction['analysis']['intent']}`")
                with cols[1]:
                    priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                    st.markdown(f"**Priority:** {priority_color.get(interaction['analysis']['priority'], '⚪')} `{interaction['analysis']['priority']}`")
                with cols[2]:
                    sentiment_emoji = {"angry": "😡", "frustrated": "😤", "neutral": "😐", "satisfied": "😊"}
                    st.markdown(f"**Sentiment:** {sentiment_emoji.get(interaction['analysis']['sentiment'], '😐')} `{interaction['analysis']['sentiment']}`")
                with cols[3]:
                    tier_emoji = "⭐" if interaction['analysis']['customer_tier'] == "premium" else "👤"
                    st.markdown(f"**Tier:** {tier_emoji} `{interaction['analysis']['customer_tier']}`")
                with cols[4]:
                    if interaction['analysis']['escalated']:
                        st.markdown("**Status:** ⚠️ `ESCALATED`")
                    else:
                        st.markdown("**Status:** ✅ `RESOLVED`")
                
                # Agent response
                st.markdown(f"""
                <div class="chat-message agent-message">
                    <strong>🤖 AI Agent:</strong><br/>
                    {interaction['reply']}
                </div>
                """, unsafe_allow_html=True)
                
                if interaction['analysis']['escalated']:
                    st.warning(f"⚠️ **Escalation Reason:** {interaction['analysis']['escalation_reason']}")
                
                st.divider()
        
        # Input form
        st.markdown("### ✍️ Your Message")
        with st.form(key="message_form", clear_on_submit=True):
            user_input = st.text_area(
                "Type your customer service message:",
                height=100,
                placeholder="e.g., I need help with my order...",
                value=st.session_state.get('example_clicked', ''),
                label_visibility="collapsed"
            )
            
            col_a, col_b, col_c = st.columns([1, 1, 4])
            submit = col_a.form_submit_button("🚀 Send", use_container_width=True, type="primary")
            
            if 'example_clicked' in st.session_state:
                del st.session_state.example_clicked
        
        if submit and user_input.strip():
            with st.spinner("🤔 AI agents analyzing your message..."):
                response = st.session_state.coordinator.process_message(user_input)
                
                st.session_state.chat_history.append({
                    'user_message': user_input,
                    'reply': response['reply'],
                    'analysis': response
                })
                
                st.rerun()
    
    with col2:
        st.markdown("### 📊 Live Analytics Dashboard")
        
        analytics = st.session_state.coordinator.get_analytics()
        
        # Key metrics
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            st.metric("Total Interactions", analytics['total_interactions'])
        with metric_col2:
            st.metric("Escalation Rate", f"{analytics['escalation_rate']:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # Intent distribution
        if analytics['intent_distribution']:
            st.markdown("**📋 Intent Distribution**")
            for intent, count in sorted(analytics['intent_distribution'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / analytics['total_interactions']) * 100
                st.progress(percentage / 100, text=f"{intent.replace('_', ' ').title()}: {count} ({percentage:.0f}%)")
        
        st.divider()
        
        # Sentiment distribution
        if analytics['sentiment_distribution']:
            st.markdown("**😊 Sentiment Distribution**")
            sentiment_emojis = {
                'angry': '😡 Angry',
                'frustrated': '😤 Frustrated',
                'neutral': '😐 Neutral',
                'satisfied': '😊 Satisfied'
            }
            for sentiment, count in sorted(analytics['sentiment_distribution'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / analytics['total_interactions']) * 100
                label = sentiment_emojis.get(sentiment, sentiment)
                st.progress(percentage / 100, text=f"{label}: {count} ({percentage:.0f}%)")
        
        st.divider()
        
        # System status
        st.markdown("**⚙️ System Status**")
        st.success("✅ All agents operational")
        st.info(f"💾 Memory: {len(st.session_state.coordinator.memory.messages)} messages stored")
        st.info(f"🚨 Escalations: {analytics['escalations']} total")
        
        # Export option
        if st.button("📥 Export Analytics", use_container_width=True):
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "analytics": analytics,
                "conversation_history": st.session_state.chat_history
            }
            st.download_button(
                label="Download JSON",
                data=json.dumps(export_data, indent=2),
                file_name=f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
