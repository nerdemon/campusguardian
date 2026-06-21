import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. Load environment variables FIRST before importing anything else
load_dotenv()

# Now it is safe to import Gemini and your local rag_agent
from google import genai
from google.genai import types
import rag_agent

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in .env file")
if not GEMINI_API_KEY:
    raise ValueError("Missing Gemini API Key in .env file")

# 2. Initialize Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

from fastapi.middleware.cors import CORSMiddleware

# 3. Initialize Server
app = FastAPI(title="CampusGuardian AI - Backend")

# Add this block right here!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows your React app to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Define Data Models
class SensorPayload(BaseModel):
    room_id: str
    temperature: float
    humidity: float
    occupancy: int
    light_level: float
    motion: bool

class KnowledgeQuestion(BaseModel):
    question: str

class IngestPayload(BaseModel):
    filename: str
    text: str


# --- ENDPOINTS ---

@app.post("/api/sensors")
async def receive_sensor_data(payload: SensorPayload):
    try:
        response = supabase.table("sensor_data").insert(payload.model_dump()).execute()
        return {"status": "success", "message": "Sensor data saved to database.", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/evaluate/{room_id}")
async def evaluate_room(room_id: str):
    try:
        # Fetch the latest reading for this specific room
        response = supabase.table("sensor_data").select("*").eq("room_id", room_id).order("timestamp", desc=True).limit(1).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="No sensor data found for this room.")
            
        data = response.data[0]
        
        prompt = f"""
        You are an Autonomous Campus Monitoring Agent. Evaluate the following room conditions:
        - Occupancy: {data['occupancy']}
        - Temperature: {data['temperature']}°C
        - Motion Detected: {data['motion']}
        - Lights On Level: {data['light_level']}
        
        Analyze the risk. If occupancy is > 100 and temp is > 30, it's Critical overcrowding. If occupancy is 0 but lights are high, it's Warning energy waste. Otherwise it's Safe.
        Output exactly one valid JSON object with these keys: 
        "risk_level" (Safe, Warning, or Critical), 
        "reason" (Short explanation), 
        "recommendation" (Actionable advice)
        """
        
        ai_response = ai_client.models.generate_content(
            model='gemini-flash-lite-latest',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # Clean the response just in case Gemini adds markdown formatting
        raw_text = ai_response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
        ai_json = json.loads(raw_text)
        
        # WE DELETED THE DATABASE INSERT HERE! Just return it to the UI directly.
        
        return {
            "status": "success",
            "agent_analysis": ai_json
        }
        
    except Exception as e:
        print(f"EVALUATION ERROR: {str(e)}") # This will print the exact error to your terminal if it fails again
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/ask")
async def ask_knowledge_base(payload: KnowledgeQuestion):
    try:
        question = payload.question
        
        # 1. Retrieve top matching context chunks from ChromaDB (PDFs)
        matches = rag_agent.query_knowledge_base(question, n_results=2)
        context_block = "\n\n---\n\n".join(m["text"] for m in matches) if matches else "No document context found."
        primary_source = matches[0]["filename"] if matches else "None"
        
        # 2. NEW: Secretly fetch the live sensor data from Supabase!
        sensor_response = supabase.table("sensor_data").select("*").limit(5).execute()
        live_data_str = "CURRENT LIVE SENSOR READINGS:\n"
        if sensor_response.data:
            for row in sensor_response.data:
                live_data_str += f"- {row['room_id']}: {row['temperature']}°C, Occupancy: {row['occupancy']}, Lights: {row['light_level']}%\n"
        else:
            live_data_str += "No live data available right now.\n"
        
        # 3. Fuse everything into the ultimate Grounding Prompt
        grounding_prompt = f"""You are CampusGuardian AI, a highly advanced campus monitoring assistant.
        You have access to both static campus rulebooks AND live hardware sensor data.
        
        Answer the user's question using ONLY the provided Document Context and Live Sensor Data below. 
        If the answer is not contained in either, explicitly state that you don't have the information. Do not guess.
        
        IMPORTANT: Provide your answer in plain text. Do NOT use markdown formatting, asterisks (*), or bold tags. Keep it conversational and clean.

        {live_data_str}

        DOCUMENT CONTEXT:
        {context_block}

        QUESTION:
        {question}

        ANSWER:"""
        
        # 4. Call Gemini Flash Lite
        response = ai_client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=grounding_prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        
        return {
            "answer": response.text,
            "source": primary_source,
        }
    except Exception as e:
        print(f"CHAT ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/ingest")
async def ingest_document(payload: IngestPayload):
    try:
        # Pass the raw text to your RAG agent to chunk, embed, and store
        chunks_saved = rag_agent.add_document_to_vector_store(
            filename=payload.filename,
            text=payload.text
        )
        
        return {
            "status": "success",
            "message": f"Successfully indexed {chunks_saved} chunks from {payload.filename} into ChromaDB."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sensors/latest")
async def get_latest_sensors():
    try:
        # Fetch the most recent rows to get real-time data
        response = supabase.table("sensor_data").select("*").order("id", desc=True).limit(50).execute()
        
        # Deduplicate so we only send the LATEST reading per room to the UI
        latest_rooms = {}
        if response.data:
            for row in response.data:
                room = row.get("room_id")
                if room and room not in latest_rooms:
                    latest_rooms[room] = row
                    
        return {"status": "success", "data": list(latest_rooms.values())}
    except Exception as e:
        return {"status": "error", "message": str(e)}