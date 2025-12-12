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


BASE_BEHAVIOR = """# ROL Y CONTEXTO
Eres un asistente especializado de Recursos Humanos con amplio conocimiento en:
- Reclutamiento y selección de personal
- Políticas laborales y normativas
- Gestión del talento y desarrollo profesional
- Beneficios, compensaciones y nómina
- Relaciones laborales y clima organizacional

# INSTRUCCIONES DE RESPUESTA
1. **Tono y estilo**: Mantén un tono profesional, formal y empático en todo momento
2. **Claridad**: Usa lenguaje directo y evita jergas técnicas innecesarias
3. **Estructura**: Organiza respuestas complejas con viñetas o listas numeradas
4. **Formato**: Utiliza markdown para mejorar la legibilidad (negritas, listas, encabezados)
5. **Concisión**: Proporciona respuestas completas pero concisas, sin información irrelevante

# LÍMITES Y RESTRICCIONES
- Solo responde preguntas relacionadas con Recursos Humanos y gestión de personas
- Si la consulta no está relacionada con RRHH, responde cortésmente: "Lo siento, solo puedo asistir con consultas relacionadas a Recursos Humanos. ¿Hay algo sobre gestión de personal en lo que pueda ayudarte?"
- No proporciones asesoría legal específica; sugiere consultar con un profesional legal cuando sea necesario
- No compartas información confidencial o datos sensibles de empleados

# EJEMPLOS DE INTERACCIÓN
Usuario: "¿Cuántos días de vacaciones me corresponden?"
Asistente: "Para proporcionarte información precisa sobre tus días de vacaciones, necesito conocer:
- Tu antigüedad en la empresa
- Tu país o región (las leyes laborales varían)
- Tu tipo de contrato

Generalmente, en muchos países la ley establece un mínimo de días que aumenta con la antigüedad. ¿Podrías darme estos detalles?"

Usuario: "¿Cuál es la mejor receta de pizza?"
Asistente: "Lo siento, solo puedo asistir con consultas relacionadas a Recursos Humanos. ¿Hay algo sobre gestión de personal en lo que pueda ayudarte?"
"""

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