import os
import json
import uuid
from http.server import BaseHTTPRequestHandler
from supabase import create_client
from google import genai
from google.genai import types

EMBEDDING_MODEL = "gemini-embedding-001"

def chunk_text(text: str, max_chars: int = 1000) -> list:
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for i in range(0, len(para), max_chars):
                chunks.append(para[i:i + max_chars].strip())
            continue
        if len(current) + len(para) + 1 <= max_chars:
            current = f"{current}\n{para}" if current else para
        else:
            if current:
                chunks.append(current.strip())
            current = para
    if current:
        chunks.append(current.strip())
    return chunks

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            filename = body.get('filename', 'unknown.pdf')
            text = body.get('text', '')

            if not text:
                self._respond(400, {"detail": "No text provided"})
                return

            # Chunk the text
            chunks = chunk_text(text)
            if not chunks:
                self._respond(400, {"detail": "No chunks generated from text"})
                return

            # Embed each chunk using Gemini and store in Supabase
            ai = genai.Client(api_key=os.environ.get('VITE_GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY', ''))
            sb = create_client(
                os.environ.get('VITE_SUPABASE_URL') or os.environ.get('SUPABASE_URL', ''),
                os.environ.get('VITE_SUPABASE_KEY') or os.environ.get('SUPABASE_KEY', '')
            )

            rows = []
            for idx, chunk in enumerate(chunks):
                emb_res = ai.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=chunk,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
                )
                embedding = emb_res.embeddings[0].values
                rows.append({
                    "id": f"{filename}-{uuid.uuid4().hex[:8]}-{idx}",
                    "filename": filename,
                    "chunk_index": idx,
                    "content": chunk,
                    "embedding": embedding
                })

            # Insert into Supabase document_chunks table
            sb.table("document_chunks").insert(rows).execute()

            self._respond(200, {
                "status": "success",
                "message": f"Indexed {len(chunks)} chunks from {filename}"
            })
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
