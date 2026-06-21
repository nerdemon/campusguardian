import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client
from google import genai
from google.genai import types

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Extract room_id from path: /api/evaluate/ROOM_ID
            room_id = self.path.rstrip('/').split('/')[-1]

            sb = create_client(
                os.environ.get('VITE_SUPABASE_URL') or os.environ.get('SUPABASE_URL', ''),
                os.environ.get('VITE_SUPABASE_KEY') or os.environ.get('SUPABASE_KEY', '')
            )
            res = sb.table("sensor_data").select("*").eq("room_id", room_id).order("timestamp", desc=True).limit(1).execute()

            if not res.data:
                self._respond(404, {"detail": "No sensor data found for this room."})
                return

            data = res.data[0]
            prompt = f"""You are an Autonomous Campus Monitoring Agent. Evaluate the following room conditions:
- Occupancy: {data['occupancy']}
- Temperature: {data['temperature']}°C
- Motion Detected: {data['motion']}
- Lights On Level: {data['light_level']}

Analyze the risk. If occupancy > 100 and temp > 30, it's Critical overcrowding. If occupancy is 0 but lights are high, it's Warning energy waste. Otherwise it's Safe.
Output exactly one valid JSON object with these keys:
"risk_level" (Safe, Warning, or Critical),
"reason" (Short explanation),
"recommendation" (Actionable advice)"""

            ai = genai.Client(api_key=os.environ.get('VITE_GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY', ''))
            ai_res = ai.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            raw = ai_res.text.strip().replace("```json", "").replace("```", "").strip()
            self._respond(200, {"status": "success", "agent_analysis": json.loads(raw)})
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
