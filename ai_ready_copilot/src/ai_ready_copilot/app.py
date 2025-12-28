from typing import AsyncIterator
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.agents.invocation_context import InvocationContext
from google.genai.types import Content, Part

from .tools.calculator import calculator
from .tools.rag import search_knowledge_base
from .tools.vacation_requester import request_vacation

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
    session_id: str | None = None

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
# Modelo + Agente
# ---------------------------------------

root_agent = Agent(
    name="rrhh_agent",
    model="gemini-2.5-flash",
    static_instruction=BASE_BEHAVIOR,
    tools=[calculator, search_knowledge_base, request_vacation],
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
async def event_stream(question: str, session_id: str) -> AsyncIterator[str]:

    new_message = Content(role="user", parts=[Part(text=question)])

    events = runner.run_async(
        user_id="anonymous",
        session_id=session_id,
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
        session_id = question.session_id

        if session_id:
            existing = await session_service.get_session(
                app_name="ai_ready_copilot",
                user_id="anonymous",
                session_id=session_id,
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            # Si no viene, crear una nueva sesión.
            session = await session_service.create_session(
                app_name="ai_ready_copilot",
                user_id="anonymous",
            )
            session_id = session.id
            print(f"Created new session with ID: {session_id}")

        response = StreamingResponse(
            event_stream(question.query, session_id),
            media_type="text/plain",
        )
        response.headers["X-Session-Id"] = session_id
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
