from typing import AsyncIterator
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from google import genai
from pydantic import BaseModel
from google.genai import types

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"

app = FastAPI()

class Question(BaseModel):
    query: str


BASE_BEHAVIOR = (
    "Eres un asistente de un equipo de recursos humanos que responde de manera formal y clara. "
    "Evita jergas y mantén un tono educado en todas las respuestas." \
    "Tu respuesta debe ser concisa y directa al punto." \
    "Debes usar markdown para formatear las respuestas cuando sea apropiado." \
    "Si la pregunta es irrelevante para recursos humanos, responde que no puedes ayudar con esa consulta."
)

def build_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is missing")
    return genai.Client(api_key=api_key)


async def stream_model_response(client: genai.Client, prompt: str) -> AsyncIterator[str]:
    async for chunk in await client.aio.models.generate_content_stream(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=BASE_BEHAVIOR
        )
    ):
        if chunk.text:
            yield chunk.text


@app.post("/ask")
async def ask(question: Question):
    client = build_client()
    stream = stream_model_response(client, question.query)
    return StreamingResponse(stream, media_type="text/plain")