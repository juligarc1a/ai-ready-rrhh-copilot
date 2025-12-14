import os
from typing import AsyncIterator, List
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from google import genai
from pydantic import BaseModel
from google.genai import types
import psycopg2
import ollama

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"

# --------- Configuración Vector Store --------------
DB_CONFIG = {
    "host": os.getenv('PG_HOST', "localhost"),
    "port": int(os.getenv('PG_PORT', 5432)),
    "user": os.getenv('PG_USER', "postgres"),
    "password": os.getenv('PG_PASS', "postgres"),
    "dbname": os.getenv('PG_DB', "ragdb"),
}
EMBED_MODEL = 'nomic-embed-text'
CONTEXT_CHUNKS = 3
EMBEDDING_DIM = 768 
# -----------------------------------------------------

app = FastAPI()

class Question(BaseModel):
    query: str

def load_prompts() -> dict:
    prompts_path = Path(__file__).parent.parent.parent / "resources" / "prompts.yaml"
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

PROMPTS = load_prompts()
BASE_BEHAVIOR = PROMPTS["base_behavior"]

def build_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is missing")
    return genai.Client(api_key=api_key)

def embed_query(text: str) -> List[float]:
    """Genera el embedding del texto usando Ollama localmente."""
    resp = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return resp['embedding']

def search_similar_chunks(query_embedding: List[float], top_k: int = CONTEXT_CHUNKS) -> List[str]:
    """Busca los chunks más similares en la base de datos con pgvector."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
    cur.execute(
        f"""
        SELECT content
        FROM items
        ORDER BY embedding <=> %s
        LIMIT %s
        """,
        (embedding_str, top_k)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]

async def stream_model_response(client: genai.Client, prompt: str) -> AsyncIterator[str]:
    async for chunk in await client.aio.models.generate_content_stream(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=BASE_BEHAVIOR)
    ):
        if chunk.text:
            yield chunk.text

def build_rag_prompt(context_chunks: List[str], user_question: str) -> str:
    context_joined = "\n\n".join(context_chunks)
    return f"""[CONTEXTO]\n{context_joined}\n\n[PREGUNTA]\n{user_question}"""

@app.post("/ask")
async def ask(question: Question):
    query_embedding = embed_query(question.query)

    chunks = search_similar_chunks(query_embedding, top_k=CONTEXT_CHUNKS)

    rag_prompt = build_rag_prompt(chunks, question.query)

    client = build_client()
    stream = stream_model_response(client, rag_prompt)
    return StreamingResponse(stream, media_type="text/plain")