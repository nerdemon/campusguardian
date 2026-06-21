import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client
from google import genai
from google.genai import types

# Fallback campus policy (used if no documents ingested yet)
FALLBACK_POLICY = """
CAMPUS POLICIES & RULES - Official Handbook

HOSTEL REGULATIONS:
- Students must be inside hostel premises by 10:00 PM as per handbook.
- Hostel gates close at 10:30 PM on weekdays and 11:30 PM on weekends.
- Late entries require a signed register and a valid reason.
- Exceeding three late entries per semester leads to a meeting with the Dean.
- Visitors are allowed in common rooms between 4:00 PM and 8:00 PM with a registered photo ID.

LABORATORY & SAFETY RULES:
- Students in the electronics lab must wear static-free wristbands at all times.
- Never leave soldering irons or heating equipment unattended.
- In emergencies like fires or chemical spills, evacuate to the South Field immediately.
- Avoid using elevators during any emergency evacuation.
- Food and beverages are strictly prohibited inside all laboratories.

ENERGY CONSERVATION:
- The last person to leave any room is responsible for turning off lights and AC.
- Air conditioning should not be set below 24 degrees C as per energy policy.

ACADEMIC INTEGRITY & DISCIPLINE:
- Ragging is strictly prohibited and results in immediate suspension and possible expulsion.
- Attendance below 75% in any subject leads to detention from examinations.
- Mobile phones must be on silent mode during all lectures and examinations.

CAFETERIA TIMINGS:
- Breakfast 7:30-9:00 AM, Lunch 12:00-2:00 PM, Dinner 7:00-9:00 PM.

LIBRARY RULES:
- Library hours: Monday-Saturday 8:00 AM to 9:00 PM, Sunday 10:00 AM to 5:00 PM.
- Books can be borrowed for 14 days; fine of Rs. 5 per day for overdue returns.
- Maximum 3 books can be borrowed at one time.
"""

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            question = body.get('question', '')

            if not question:
                self._respond(400, {"detail": "Question is required"})
                return

            sb = create_client(
                os.environ.get('VITE_SUPABASE_URL') or os.environ.get('SUPABASE_URL', ''),
                os.environ.get('VITE_SUPABASE_KEY') or os.environ.get('SUPABASE_KEY', '')
            )

            # Try to get document chunks from Supabase (ingested via n8n)
            doc_context = FALLBACK_POLICY
            source = "Campus_Policies_Handbook.pdf"
            try:
                chunks_res = sb.table("document_chunks").select("content, filename").limit(10).execute()
                if chunks_res.data:
                    doc_context = "\n\n---\n\n".join(row["content"] for row in chunks_res.data)
                    source = chunks_res.data[0].get("filename", source)
            except Exception:
                pass  # Fall back to embedded policy

            # Fetch live sensor data
            sensor_res = sb.table("sensor_data").select("*").limit(5).execute()
            live_data = "CURRENT LIVE SENSOR READINGS:\n"
            for row in (sensor_res.data or []):
                live_data += f"- {row['room_id']}: {row['temperature']}°C, Occupancy: {row['occupancy']}, Lights: {row['light_level']}%\n"

            prompt = f"""You are CampusGuardian AI, a highly advanced campus monitoring assistant.
You have access to official campus policy documents AND live hardware sensor data.

Answer the user's question using ONLY the Document Context and Live Sensor Data below.
If the answer is not contained in either, explicitly state you don't have that information.
Provide your answer in plain text. Do NOT use markdown formatting or asterisks.

{live_data}

DOCUMENT CONTEXT:
{doc_context}

QUESTION: {question}

ANSWER:"""

            ai = genai.Client(api_key=os.environ.get('VITE_GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY', ''))
            res = ai.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2)
            )
            self._respond(200, {"answer": res.text, "source": source})
        except Exception as e:
            self._respond(500, {"detail": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, *args):
        pass
