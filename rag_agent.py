import os
import uuid
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv  # <-- Add this import

# Load environment variables explicitly before client creation
load_dotenv()  # <-- Add this line

# Modern google-genai SDK client.
ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Persistent local ChromaDB client
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Create or retrieve the collection used for campus documents
collection = chroma_client.get_or_create_collection(name="campus_docs")

EMBEDDING_MODEL = "gemini-embedding-001"

def chunk_text(text: str, max_chars: int = 1000) -> list[str]:
    """Split text into chunks of at most max_chars characters."""
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
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

def _embed(text: str, task_type: str) -> list[float]:
    """Generate an embedding using modern style."""
    response = ai_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return response.embeddings[0].values

def add_document_to_vector_store(filename: str, text: str, max_chars: int = 1000) -> int:
    """Chunk, embed, and store text inside ChromaDB."""
    chunks = chunk_text(text, max_chars=max_chars)
    if not chunks:
        return 0

    ids = []
    embeddings = []
    metadatas = []
    documents = []

    for idx, chunk in enumerate(chunks):
        chunk_embedding = _embed(chunk, task_type="RETRIEVAL_DOCUMENT")

        ids.append(f"{filename}-{uuid.uuid4().hex[:8]}-{idx}")
        embeddings.append(chunk_embedding)
        documents.append(chunk)
        metadatas.append({
            "filename": filename,
            "chunk_index": idx,
        })

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return len(chunks)

def query_knowledge_base(question: str, n_results: int = 2) -> list[dict]:
    """Query ChromaDB for closest context matches."""
    query_embedding = _embed(question, task_type="RETRIEVAL_QUERY")

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

    matches = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(documents)

    for doc, meta, dist in zip(documents, metadatas, distances):
        matches.append({
            "text": doc,
            "filename": meta.get("filename", "unknown"),
            "distance": dist,
        })

    return matches