import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client
from google import genai
from google.genai import types

# Campus policy context (replaces ChromaDB for Vercel deployment)
CAMPUS_POLICY_CONTEXT = """
CAMPUS POLICIES & RULES - Official Handbook

HOSTEL REGULATIONS:
- Students must be inside hostel premises by 10:00 PM as per handbook.
- Hostel gates close at 10:30 PM on weekdays and 11:30 PM on weekends.
- Late entries require a signed register and a valid reason.
- Exceeding three late entries per semester leads to a meeting with the Dean.
- Visitors are allowed in common rooms between 4:00 PM and 8:00 PM with a registered photo ID.
- Male visitors are not permitted in female hostel blocks and vice versa.

LABORATORY & SAFETY RULES:
- Students in the electronics lab must wear static-free wristbands at all times.
- Never leave soldering irons or heating equipment unattended.
- In emergencies like fires or chemical spills, evacuate to the South Field immediately.
- Avoid using elevators during any emergency evacuation.
- Lab equipment must be signed out before use and signed back in after.
- Food and beverages are strictly prohibited inside all laboratories.

ENERGY CONSERVATION:
- The last person to leave any room is responsible for turning off lights and AC.
- Air conditioning should not be set below 24°C as per energy policy.
- Report any equipment left running unnecessarily to the facilities helpdesk.

ACADEMIC INTEGRITY & DISCIPLINE:
- Ragging is strictly prohibited and results in immediate suspension and possible expulsion.
- Plagiarism in academic submissions leads to a zero grade and disciplinary action.
- Mobile phones must be on silent mode during all lectures and examinations.
- Attendance below 75% in any subject leads to detention from examinations.

CAFETERIA & COMMON AREAS:
- Cafeteria timings: Breakfast 7:30-9:00 AM, Lunch 12:00-2:00 PM, Dinner 7:00-9:00 PM.
- Students must clear their trays and maintain cleanliness in common areas.
- Smoking and consumption of alcohol on campus premises is strictly prohibited.

LIBRARY RULES:
- Library hours: Monday-Saturday 8:00 AM to 9:00 PM, Sunday 10:00 AM to 5:00 PM.
- Books can be borrowed for 14 days with a fine of Rs. 5 per day for overdue returns.
- Silence must be maintained in the library at all times.
- A maximum of 3 books can be borrowed at one time per student.
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

            # Fetch live sensor data from Supabase
            sb = create_client(
                os.environ.get('VITE_SUPABASE_URL', ''),
                os.environ.get('VITE_SUPABASE_KEY', '')
            )
            sensor_res = sb.table("sensor_data").select("*").limit(5).execute()
            live_data = "CURRENT LIVE SENSOR READINGS:\n"
            for row in (sensor_res.data or []):
                live_data += f"- {row['room_id']}: {row['temperature']}°C, Occupancy: {row['occupancy']}, Lights: {row['light_level']}%\n"

            prompt = f"""You are CampusGuardian AI, a highly advanced campus monitoring assistant.
You have access to official campus policy documents AND live hardware sensor data.

Answer the user's question using ONLY the Document Context and Live Sensor Data below.
If the answer is not contained in either, explicitly state you don't have that information. Do not guess.
Provide your answer in plain text. Do NOT use markdown formatting, asterisks, or bold tags. Keep it conversational and clean.

{live_data}

DOCUMENT CONTEXT:
{CAMPUS_POLICY_CONTEXT}

QUESTION: {question}

ANSWER:"""

            ai = genai.Client(api_key=os.environ.get('VITE_GEMINI_API_KEY', ''))
            res = ai.models.generate_content(
                model='gemini-2.0-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2)
            )
            self._respond(200, {"answer": res.text, "source": "Campus_Policies_Handbook.pdf"})
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
