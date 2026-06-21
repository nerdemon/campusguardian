# 🛡️ CampusGuardian AI
> **The Autonomous Smart Campus Ecosystem**

CampusGuardian AI is a centralized intelligence layer that acts as the nervous system for a modern university. It monitors environments, optimizes energy, secures the premises, and acts as an autonomous academic ledger—all driven by a decentralized multi-domain AI architecture.

## 🌟 The Four Pillars of Automation

1. **Smart Climate & Energy Engine:** Monitors real-time occupancy and environmental telemetry. If a room is empty but lights/HVAC are active, the AI flags energy waste and suggests automated shutdowns.
2. **Autonomous Academic Ledger:** Eliminates manual roll-calls using Network-Layer Proximity. When a student's device connects to the classroom Wi-Fi during a scheduled lecture, they are logged as present dynamically.
3. **Security & Intrusion AI:** Analyzes spatial context after hours. A motion trigger in an empty lab with lights off is instantly classified as a high-severity intrusion by the AI logic router.
4. **Institutional Knowledge RAG:** An automated n8n pipeline ingests campus policies (PDFs) from Google Drive into a ChromaDB vector store. Students can query the AI and receive verified, strictly-cited answers.

## 🏗️ Architecture & Tech Stack

*   **Frontend:** React (Vite) + Tailwind CSS + Lucide Icons
*   **Backend Layer:** FastAPI (Python)
*   **Database / State:** Supabase (PostgreSQL)
*   **Reasoning Engine:** Google Gemini 2.5 Flash
*   **Vector DB / RAG:** ChromaDB
*   **Ingestion Pipeline:** n8n 
*   **Telemetry Simulation:** Python Digital Twin Injector (Stress-tests the backend with high-volume, randomized room data).

## 🚀 Running Locally

To run the full simulation on your local machine:

**1. Clone & Set Environment Variables**
Create a `.env` file in the root directory:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
GEMINI_API_KEY=your_gemini_api_key
```

**2. Start the FastAPI Backend**
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

**3. Start the React Dashboard**
```bash
cd campus-dashboard
npm install
npm run dev
```

**4. Start the Digital Twin Injector**
```bash
# In a new terminal, run the simulator to flood the backend with live data
python simulator.py
```

## 🧠 How the AI Routing Works
To maintain low latency and reduce compute costs, we utilize an **Agentic Router Pattern**. The FastAPI backend deterministically evaluates the context of incoming sensor payloads. Standard telemetry is logged instantly, but anomalies (e.g., overcrowding, after-hours motion) trigger the Gemini 2.5 Flash engine for advanced contextual evaluation and recommendation generation.
