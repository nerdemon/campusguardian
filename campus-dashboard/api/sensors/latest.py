import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            sb = create_client(
                os.environ.get('SUPABASE_URL', ''),
                os.environ.get('SUPABASE_KEY', '')
            )
            res = sb.table("sensor_data").select("*").order("id", desc=True).limit(50).execute()
            latest = {}
            for row in (res.data or []):
                room = row.get("room_id")
                if room and room not in latest:
                    latest[room] = row

            self._respond(200, {"status": "success", "data": list(latest.values())})
        except Exception as e:
            self._respond(500, {"status": "error", "message": str(e)})

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
