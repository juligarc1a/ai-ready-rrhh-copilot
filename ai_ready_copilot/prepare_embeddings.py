import os
import psycopg2
import ollama

# ------------------- CONFIGURACIÓN -----------------------
PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "postgres",
    "dbname": "ragdb"
}
TXT_DIRECTORY = "./texts"  # Directorio con archivos .txt
EMBEDDING_DIM = 768        # Cambia según tu modelo
CHUNK_SIZE = 500           # Caracteres por chunk (modifica según lo que prefieras)
CHUNK_OVERLAP = 50         # Superposición de caracteres entre chunks para mejor contexto
OLLAMA_MODEL = 'nomic-embed-text'  # Modelo a usar en Ollama
# ---------------------------------------------------------

def chunk_text(text, chunk_size=500, overlap=50):
    """Divide el texto en chunks de tamaño y overlap especificado."""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == text_len:
            break
        start += chunk_size - overlap
    return chunks

def main():
    # Conexión a base de datos
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute("DROP TABLE IF EXISTS items;")

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            filename TEXT,
            chunk_index INT,
            content TEXT,
            embedding vector({EMBEDDING_DIM})
        );
    """)
    conn.commit()

    for filename in os.listdir(TXT_DIRECTORY):
        if filename.endswith(".txt"):
            file_path = os.path.join(TXT_DIRECTORY, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)

            for idx, chunk in enumerate(chunks):
                # Obtiene el embedding real del chunk usando Ollama
                response = ollama.embeddings(model=OLLAMA_MODEL, prompt=chunk)
                # El embedding viene en response['embedding']
                embedding = response['embedding']
                embedding_str = str(list(embedding))

                print(f"Insertando {filename} (chunk {idx+1}/{len(chunks)}) en la base de datos...")

                cur.execute(
                    "INSERT INTO items (filename, chunk_index, content, embedding) VALUES (%s, %s, %s, %s)",
                    (filename, idx, chunk, embedding_str)
                )
                conn.commit()
                print(f"Insertado {filename} (chunk {idx+1}) correctamente.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()