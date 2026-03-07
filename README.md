# 🚀 CampaignX: Multi-Agent System

**🌐 Try it live:** [Agentive Minds App](https://agentiveminds.streamlit.app)

CampaignX is an intelligent, Streamlit-based marketing platform that uses autonomous AI agents to generate, schedule, and optimize email campaigns. Built with Groq's Llama 3.3 model, it features a "Human-in-the-Loop" workflow to ensure marketing assets are reviewed before deployment.

---

## ✨ Key Features

* **Autonomous Content Generation:** Uses an AI Marketing Agent to write email strategies, subject lines, and formatted body copy based on a simple brief.
* **Human-in-the-Loop Approval:** Allows users to review, approve, or reject AI-generated content. If rejected, the AI rewrites the copy taking the rejection into account.
* **Live Cohort Targeting:** Fetches real-time customer data via external APIs.
* **Automated Scheduling:** Handles timezone conversions (UTC to IST) to schedule campaigns slightly in the future.
* **Performance Monitoring:** Retrieves post-campaign analytics (Open Rates and Click Rates).
* **Self-Optimizing Feedback Loop:** Feeds poor performance metrics back to the AI agent to autonomously analyze and generate an optimized "V2" campaign.

---

## 🛠️ Tech Stack

* **Frontend & State Management:** [Streamlit](https://streamlit.io/)
* **LLM Provider:** [Groq](https://groq.com/) (`llama-3.3-70b-versatile`)
* **API Requests:** Python `requests` library

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone [https://github.com/yourusername/campaignx-agent.git](https://github.com/yourusername/campaignx-agent.git)
cd campaignx-agent
