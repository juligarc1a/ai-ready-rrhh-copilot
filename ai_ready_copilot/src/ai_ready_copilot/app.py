import os
from typing import List, AsyncIterator
from pathlib import Path

import yaml
import psycopg2
import ollama
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.agents.invocation_context import InvocationContext
from google.genai.types import Content, Part

load_dotenv()

# ---------------------------------------
# FastAPI
# ---------------------------------------
app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class Question(BaseModel):
    query: str
    history: List[Message] = []

# ---------------------------------------
# Prompt config
# ---------------------------------------
def load_prompts() -> dict:
    prompts_path = Path(__file__).parent.parent.parent / "resources" / "prompts.yaml"
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

PROMPTS = load_prompts()
BASE_BEHAVIOR = PROMPTS["base_behavior"]

# ---------------------------------------
# Tools
# ---------------------------------------
def calculator(expression: str) -> dict:
    """
    Evalúa una expresión matemática simple.

    Args:
        expression (str): La expresión a evaluar.

    Returns:
        dict: status y resultado o mensaje de error.
    """
    try:
        result = eval(expression, {"__builtins__": {}})
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def embed_query(text: str) -> List[float]:
    resp = ollama.embeddings(model="nomic-embed-text", prompt=text)
    return resp['embedding']

def search_similar_chunks(query_embedding: List[float], top_k: int = 3) -> List[str]:
    conn = psycopg2.connect(
        host=os.getenv('PG_HOST', "localhost"),
        port=int(os.getenv('PG_PORT', 5432)),
        user=os.getenv('PG_USER', "postgres"),
        password=os.getenv('PG_PASS', "postgres"),
        dbname=os.getenv('PG_DB', "ragdb"),
    )
    cur = conn.cursor()
    embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
    cur.execute(
        """
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

def search_knowledge_base(query: str) -> dict:
    """
    Busca en la base de conocimiento relevante (RAG).

    Args:
        query (str): Texto de consulta.

    Returns:
        dict: status y chunks encontrados.
    """
    embedding = embed_query(query)
    chunks = search_similar_chunks(embedding)
    return {"status": "success", "result": chunks}

# ---------------------------------------
# Modelo + Agente
# ---------------------------------------

root_agent = Agent(
    name="rrhh_agent",
    model="gemini-2.5-flash",
    # static_instruction=PROMPTS,
    tools=[calculator, search_knowledge_base],
)

# ---------------------------------------
# SessionService + Runner
# ---------------------------------------
session_service = InMemorySessionService()

runner = Runner(
    agent = root_agent,
    app_name="ai_ready_copilot",
    session_service=session_service,
)


# ---------------------------------------
# Endpoint FastAPI streaming
# ---------------------------------------
async def event_stream(question: str) -> AsyncIterator[str]:

    session = await session_service.create_session(
        app_name="ai_ready_copilot",
        user_id="anonymous",
    )

    new_message = Content(role="user", parts=[Part(text=question)])

    events = runner.run_async(
        user_id="anonymous",
        session_id=session.id,
        new_message=new_message,
    )

    async for event in events:
        print("Event received:", event)
        # 1) Si el ADK expone output_text, úsalo directamente
        if hasattr(event, "output_text") and event.output_text:
            yield event.output_text
            continue

        # 2) Extraer texto de event.content.parts (caso más común)
        content = getattr(event, "content", None)
        if content and getattr(content, "parts", None):
            text_chunks = [
                part.text
                for part in content.parts
                if hasattr(part, "text") and part.text
            ]
            if text_chunks:
                yield "".join(text_chunks)

@app.post("/ask")
async def ask(question: Question):
    try:
        return StreamingResponse(event_stream(question.query), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
