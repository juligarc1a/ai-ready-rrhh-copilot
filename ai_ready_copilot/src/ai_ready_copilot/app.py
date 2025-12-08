from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os


app = FastAPI()
load_dotenv()

class Question(BaseModel):
    query: str

@app.post("/ask")
async def ask(question: Question):
    api_key = os.getenv("API_KEY", "NO_API_KEY_FOUND")
    return { "response": f"Soy el Copiloto de RRHH, pronto podré ayudarte. Mi api key del .env es: {api_key}" }