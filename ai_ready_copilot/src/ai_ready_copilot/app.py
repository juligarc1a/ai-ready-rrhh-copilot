import os
from typing import List
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import yaml
from pathlib import Path
from pydantic import BaseModel
import psycopg2
import ollama

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService # Optional
from google.adk.planners import BasePlanner, BuiltInPlanner, PlanReActPlanner
from google.adk.models import LlmRequest
from google.adk.agents import Agent
from google.genai import types


load_dotenv()
MODEL_NAME = "gemini-2.5-flash"

DB_CONFIG = {
    "host": os.getenv('PG_HOST', "localhost"),
    "port": int(os.getenv('PG_PORT', 5432)),
    "user": os.getenv('PG_USER', "postgres"),
    "password": os.getenv('PG_PASS', "postgres"),
    "dbname": os.getenv('PG_DB', "ragdb"),
}
EMBED_MODEL = 'nomic-embed-text'
CONTEXT_CHUNKS = 3

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class Question(BaseModel):
    query: str
    history: List[Message] = []

def embed_query(text: str) -> List[float]:
    resp = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return resp['embedding']

def search_similar_chunks(query_embedding: List[float], top_k: int = CONTEXT_CHUNKS) -> List[str]:
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

def load_prompts() -> dict:
    prompts_path = Path(__file__).parent.parent.parent / "resources" / "prompts.yaml"
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

PROMPTS = load_prompts()
BASE_BEHAVIOR = PROMPTS["base_behavior"]

# ------- Declarar tools explícitas usando la nueva API Tool de ADK -------
def rag_search(question: str) -> str:
    embedding = embed_query(question)
    chunks = search_similar_chunks(embedding, top_k=CONTEXT_CHUNKS)
    return "\n".join(chunks)

def do_math(expr: str) -> str:
    try:
        result = eval(expr)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


# ----------- Configurar el modelo y el agente ADK ---------------
# def build_adk_agent():
#     # configure(api_key=os.getenv("GEMINI_API_KEY"))
#     agent = Agent(
#         name="RRHH_Copilot_Agent",
#         model=MODEL_NAME,
#         tools=[rag_search, do_math],  # Aquí usas los Tool objects, no los decoradores
#         instruction=BASE_BEHAVIOR  # Prompt/rol como siempre
#     )
#     return agent
def build_adk_agent():
    return Agent(
        name="RRHH_Copilot_Agent",
        model=MODEL_NAME,
        tools=[rag_search, do_math],
        instruction=BASE_BEHAVIOR,
    )


def history_to_adk(history: List[Message]):
    adk_hist = []
    for msg in history:
        if msg.role == "user":
            adk_hist.append({"role": "user", "content": msg.content})
        elif msg.role in ("assistant", "system"):
            adk_hist.append({"role": "assistant", "content": msg.content})
    return adk_hist

async def stream_agent(agent, user_question: str, history: List[Message]):
    responses = agent.achat(user_question, history=history_to_adk(history), stream=True)
    async for chunk in responses:
        if chunk.text:
            yield chunk.text

APP_NAME = "RRHH_Copilot_App"

session_service = InMemorySessionService()

APP_NAME = "RRHH_Copilot_App"
USER_ID = "user_123"
SESSION_ID = "session_abc"

agent = build_adk_agent()

session_service = InMemorySessionService()
example_session = session_service.create_session(
     app_name="my_app",
     user_id="example_user",
     state={"initial_key": "initial_value"} # State can be initialized
 )
runner = Runner(
    agent=agent,
    app_name=APP_NAME,
    session_service=example_session,
)

@app.post("/ask")
async def ask(q: Question):
    content = types.Content(
        role="user",
        parts=[types.Part(text=q.query)]
    )

    async def event_stream():
        for event in runner.run(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=content,
        ):
            if hasattr(event, "text") and event.text:
                yield event.text

    return StreamingResponse(
        event_stream(),
        media_type="text/plain"
    )