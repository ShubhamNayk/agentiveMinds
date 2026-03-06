import streamlit as st
import json
import requests
from datetime import datetime, timedelta, timezone
from groq import Groq

# ==========================================
# --- CONFIGURATION (USING SECRETS NOW) ---
# ==========================================
# We are pulling these securely from Streamlit!
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
HACKATHON_API_KEY = st.secrets["HACKATHON_API_KEY"]

# CampaignX Endpoints
COHORT_URL = "https://campaignx.inxiteout.ai/api/v1/get_customer_cohort"
SEND_CAMPAIGN_URL = "https://campaignx.inxiteout.ai/api/v1/send_campaign"
REPORT_URL = "https://campaignx.inxiteout.ai/api/v1/get_report"

# --- STATE MANAGEMENT (The Agent's Memory) ---
if "stage" not in st.session_state:
    st.session_state.stage = "input"
if "generated_data" not in st.session_state:
    st.session_state.generated_data = None
if "cohort_ids" not in st.session_state:
    st.session_state.cohort_ids = []
if "rejection_count" not in st.session_state:
    st.session_state.rejection_count = 0
if "campaign_id" not in st.session_state:
    st.session_state.campaign_id = None
if "report" not in st.session_state:
    st.session_state.report = None

# ==========================================
# --- AGENT FUNCTIONS ---
# ==========================================

def fetch_customer_ids():
    """Fetches the live customer cohort from the Hackathon API."""
    headers = {"X-API-Key": HACKATHON_API_KEY}
    response = requests.get(COHORT_URL, headers=headers)
    if response.status_code == 200:
        data = response.json().get("data", [])
        # Grabbing all customers
        return [customer["customer_id"] for customer in data]
    else:
        st.error(f"Failed to fetch cohort: {response.text}")
        return []

def generate_campaign_assets(brief, feedback_context=""):
    """Uses Groq to generate strategy, subject, and body in JSON format."""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        # If human rejected it, add context
        retry_context = ""
        if st.session_state.rejection_count > 0:
            retry_context = f"WARNING: The human manager REJECTED your last {st.session_state.rejection_count} draft(s). Change your strategy and text completely."

        system_prompt = f"""
        You are an autonomous AI Marketing Agent. 
        Your job is to read a campaign brief and generate email content.
        
        {retry_context}
        {feedback_context}
        
        STRICT RULES:
        1. The email body MUST contain this exact URL: https://superbfsi.com/xdeposit/explore/
        2. You must decide whether to use emojis in the body, and where to put them.
        3. You must use markdown for font variations (like **bold** or *italics*) in the body.
        4. The subject line must be text only (no emojis).
        
        You MUST respond with ONLY a valid JSON object in this exact format:
        {{
            "strategy_reasoning": "A 1-sentence explanation of why you chose this tone.",
            "subject_line": "The email subject",
            "email_body": "The full email body formatting."
        }}
        """
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the brief: {brief}"}
            ],
            temperature=0.8, 
            response_format={"type": "json_object"} 
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

def schedule_hackathon_campaign(subject, body, customer_ids):
    """Sends the approved campaign to the Hackathon server."""
    headers = {
        "X-API-Key": HACKATHON_API_KEY,
        "Content-Type": "application/json"
    }
    
    # --- TIMEZONE FIX FOR STREAMLIT CLOUD ---
    # 1. Get current time in UTC
    # 2. Add 5 hours and 30 minutes to convert to IST
    # 3. Add 2 minutes to schedule it slightly in the future
    ist_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    scheduled_time = ist_time + timedelta(minutes=2)
    
    # Format the time exactly as the API requires: DD:MM:YY HH:MM:SS
    send_time = scheduled_time.strftime("%d:%m:%y %H:%M:%S")
    
    payload = {
        "subject": subject,
        "body": body,
        "list_customer_ids": customer_ids,
        "send_time": send_time
    }
    
    response = requests.post(SEND_CAMPAIGN_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("campaign_id")
    else:
        st.error(f"API Error: {response.text}")
        return None

def fetch_campaign_report(campaign_id):
    """Fetches the performance report and calculates open/click rates."""
    url = f"{REPORT_URL}?campaign_id={campaign_id}"
    headers = {"X-API-Key": HACKATHON_API_KEY}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        report_data = response.json().get("data", [])
        total_sent = len(report_data)
        if total_sent == 0:
            return None
            
        opens = sum(1 for row in report_data if row.get("EO") == "Y")
        clicks = sum(1 for row in report_data if row.get("EC") == "Y")
        
        return {
            "total_sent": total_sent,
            "open_rate": (opens / total_sent) * 100,
            "click_rate": (clicks / total_sent) * 100
        }
    else:
        st.error(f"Failed to fetch report: {response.text}")
        return None

# ==========================================
# --- STREAMLIT UI ---
# ==========================================
st.set_page_config(page_title="CampaignX Agent", layout="centered")
st.title("🚀 CampaignX: Multi-Agent System")

# STAGE 1: INPUT
if st.session_state.stage == "input":
    st.markdown("### Step 1: Campaign Brief")
    brief = st.text_area("Instructions:", 
                         value="Run email campaign for launching XDeposit, a flagship term deposit product from SuperBFSI... Announce an additional 0.25 percentage point higher returns for female senior citizens.", 
                         height=100)
    
    if st.button("Generate Campaign", type="primary"):
        with st.spinner("Fetching live cohort and generating AI assets..."):
            st.session_state.brief = brief
            st.session_state.cohort_ids = fetch_customer_ids()
            
            if st.session_state.cohort_ids:
                st.session_state.generated_data = generate_campaign_assets(brief)
                st.session_state.stage = "review"
                st.rerun()

# STAGE 2: REVIEW (Human-in-the-Loop)
elif st.session_state.stage == "review":
    st.markdown("### Step 2: Human-in-the-Loop Approval")
    
    result = st.session_state.generated_data
    if "error" in result:
        st.error(f"Groq Error: {result['error']}")
        if st.button("Try Again"):
            st.session_state.stage = "input"
            st.rerun()
    else:
        st.info(f"**🎯 Targeting:** {len(st.session_state.cohort_ids)} customers.")
        st.success(f"**🧠 Agent's Strategy:** {result.get('strategy_reasoning')}")
        st.write(f"**📧 Subject:** {result.get('subject_line')}")
        with st.container(border=True):
            st.markdown(result.get('email_body'))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ APPROVE & Schedule Campaign", use_container_width=True):
                with st.spinner("Sending to CampaignX API..."):
                    campaign_id = schedule_hackathon_campaign(
                        result.get('subject_line'), 
                        result.get('email_body'),
                        st.session_state.cohort_ids
                    )
                    if campaign_id:
                        st.session_state.campaign_id = campaign_id
                        st.session_state.stage = "monitoring"
                        st.rerun()
        with col2:
            if st.button("❌ REJECT & Rewrite", use_container_width=True):
                st.session_state.rejection_count += 1
                with st.spinner("Agent is rewriting..."):
                    st.session_state.generated_data = generate_campaign_assets(st.session_state.brief)
                st.rerun()

# STAGE 3: MONITORING & OPTIMIZATION
elif st.session_state.stage == "monitoring":
    st.markdown("### Step 3: Campaign Active")
    st.success(f"✅ Campaign successfully scheduled! (ID: {st.session_state.campaign_id})")
    
    st.divider()
    st.markdown("### Step 4: Performance Monitoring")
    
    if st.button("Fetch Performance Report", type="primary"):
        with st.spinner("Analyzing data from CampaignX API..."):
            st.session_state.report = fetch_campaign_report(st.session_state.campaign_id)
            
    if st.session_state.report:
        rep = st.session_state.report
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Sent", rep['total_sent'])
        col2.metric("Open Rate", f"{rep['open_rate']:.1f}%")
        col3.metric("Click Rate", f"{rep['click_rate']:.1f}%")
        
        st.info("💡 The AI Agent can analyze these metrics to generate a better variant.")
        
        if st.button("Autonomously Optimize & Relaunch"):
            with st.spinner("Agent is analyzing data and writing V2..."):
                old_subject = st.session_state.generated_data.get('subject_line')
                
                feedback = f"""
                PERFORMANCE FEEDBACK FROM PREVIOUS RUN:
                - Previous Subject: {old_subject}
                - Open Rate: {rep['open_rate']}%
                - Click Rate: {rep['click_rate']}%
                YOUR TASK: Analyze why these might be low and write an optimized version to improve these metrics.
                """
                
                st.session_state.generated_data = generate_campaign_assets(st.session_state.brief, feedback)
                st.session_state.stage = "review" # Send back to approval stage!
                st.rerun()
                
    st.divider()
    if st.button("Start Completely New Campaign"):
        st.session_state.stage = "input"
        st.session_state.rejection_count = 0
        st.session_state.generated_data = None
        st.session_state.report = None
        st.rerun()
