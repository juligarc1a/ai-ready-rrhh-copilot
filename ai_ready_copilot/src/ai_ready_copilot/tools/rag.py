import psycopg2
import ollama
import os
from typing import List


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
    Esta posee información sobre RRHH.

    Args:
        query (str): Texto de consulta.

    Returns:
        dict: status y chunks encontrados.
    """
    embedding = embed_query(query)
    chunks = search_similar_chunks(embedding)
    return {"status": "success", "result": chunks}
