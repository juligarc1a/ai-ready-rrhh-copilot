# AI Ready RRHH Copilot

Un copiloto de IA para gestión de recursos humanos.

## Requisitos previos

- Python >= 3.14
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker (para la base de datos `pgvector` y `ollama` con el modelo `nomic-embed-text`)

## Instalación

1. Clona el repositorio:

```bash
git clone <repository-url>
cd ai-ready-rrhh-copilot
```

2. Instala las dependencias usando Poetry:

```bash
poetry install
```

3. Configura las variables de entorno:

```bash
cp .env.example .env
```

Edita el archivo `.env` con tus configuraciones necesarias.

## Ejecución

### Iniciar la API con FastAPI

Para arrancar la aplicación FastAPI con Uvicorn en modo desarrollo (con recarga automática):

```bash
poetry run uvicorn ai_ready_copilot.src.ai_ready_copilot.app:app --reload
```

La API estará disponible en `http://localhost:8000`

### Documentación interactiva

Una vez que la API esté corriendo, puedes acceder a:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Estructura del proyecto

```
ai_ready_copilot/
├── docker-compose.yaml          # Postgres + pgvector
├── prepare_embeddings.py        # Script para generar embeddings
├── docs/                        # Documentos base (.txt)
│   ├── politica_gastos_Version2.txt
│   └── politica_vacaciones_Version2.txt
├── resources/
│   └── prompts.yaml             # Prompts del sistema abstraídos
├── src/
│   └── ai_ready_copilot/
│       ├── __init__.py
│       └── app.py               # Aplicación FastAPI principal
├── tests/                       # Tests unitarios
├── pyproject.toml               # Configuración de Poetry
├── README.md                    # Este archivo
└── .env                         # Variables de entorno (no versionado)
```

## Dependencias principales

- **FastAPI**: Framework web asincrónico
- **Uvicorn**: Servidor ASGI
- **Pydantic**: Validación de datos
- **python-dotenv**: Gestión de variables de entorno
- **PyYAML**: Carga de archivos YAML para gestión de prompts
- **google-genai**: SDK de Google Gemini para generación de contenido
- **psycopg2-binary**: Conexión a PostgreSQL/pgvector
- **psycopg2-binary**: Conexión a PostgreSQL/pgvector
- **ollama**: Cliente para embeddings locales con `nomic-embed-text`

## Vector Store y Embeddings

### Preparación de la base de datos

1. Levanta PostgreSQL con pgvector usando Docker:

```bash
docker compose up -d
```

Esto inicia una instancia de Postgres en `localhost:5432` con la base de datos `ragdb`.

Además se arranca una instancia de `ollama` en la que correrá un modelo `nomic-embed-text`

### Generación de embeddings

2. Ejecuta el script `prepare_embeddings.py` para procesar documentos y generar embeddings:

```bash
poetry run python prepare_embeddings.py
```

Este script:

- Lee los archivos `.txt` del directorio `docs/`
- Divide cada documento en chunks (configurable con `CHUNK_SIZE` y `CHUNK_OVERLAP`)
- Genera embeddings para cada chunk usando Ollama (modelo `nomic-embed-text`, dimensión 768)
- Almacena los embeddings en la tabla `items` de PostgreSQL con su contenido asociado

### Variables de entorno para Vector Store

Añade estas variables a tu archivo `.env`:

```
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASS=postgres
PG_DB=ragdb
```

## Licencia

MIT

## Integración con LLM: (Módulo 3)

Este proyecto utiliza **Google Gemini** como modelo de lenguaje para generar respuestas inteligentes a consultas de Recursos Humanos.

### Modelo utilizado

- **Modelo**: `gemini-2.5-flash`
- **Proveedor**: Google Gemini AI
- **SDK**: `google-genai`

### Características de la integración

#### Streaming de respuestas

La aplicación implementa **streaming** de respuestas mediante `generate_content_stream`, lo que permite:

- Envío progresivo de la respuesta al usuario
- Mejor experiencia de usuario con respuestas más fluidas
- Reducción del tiempo de espera percibido
- Uso eficiente de recursos

```python
async for chunk in await client.aio.models.generate_content_stream(
    model=MODEL_NAME,
    contents=prompt,
    config=types.GenerateContentConfig(
        system_instruction=BASE_BEHAVIOR
    )
):
    if chunk.text:
        yield chunk.text
```

#### System Instructions

El modelo utiliza **system instructions** para definir su comportamiento base mediante el prompt `BASE_BEHAVIOR`. Esto permite:

- Mantener consistencia en el tono y estilo de respuestas
- Establecer límites claros sobre qué consultas responder
- Definir el rol especializado en RRHH
- Garantizar respuestas estructuradas y profesionales

#### Configuración

La API key se gestiona mediante variables de entorno:

```bash
GEMINI_API_KEY=tu_api_key_aqui
```

El cliente de Gemini se construye dinámicamente en cada petición, validando la presencia de la API key antes de procesar consultas.

### Endpoint de la API

**POST** `/ask`

Recibe una consulta en formato JSON y retorna una respuesta en streaming:

```json
{
  "query": "¿Cuántos días de vacaciones me corresponden?"
}
```

La respuesta se envía como `text/plain` en formato streaming, permitiendo que el cliente reciba y muestre el contenido progresivamente.

## Diseño de Prompts

### Gestión de prompts con YAML

Los prompts del sistema están abstraídos en el archivo `resources/prompts.yaml` para facilitar su mantenimiento y actualización sin modificar el código Python. La aplicación utiliza **PyYAML** para cargar dinámicamente estos prompts al inicio.

**Ventajas de esta arquitectura:**

- **Separación de responsabilidades**: Los prompts están desacoplados del código de la aplicación
- **Mantenimiento simplificado**: Modificar el comportamiento del asistente solo requiere editar el archivo YAML
- **Escalabilidad**: Permite agregar múltiples prompts para diferentes contextos o roles
- **Versionado independiente**: Los cambios en prompts pueden rastrearse por separado

**Ubicación del archivo:**

```
resources/prompts.yaml
```

**Carga en la aplicación:**

```python
def load_prompts() -> dict:
    """Carga los prompts desde el archivo prompts.yaml"""
    prompts_path = Path(__file__).parent.parent.parent.parent / "resources" / "prompts.yaml"
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

PROMPTS = load_prompts()
BASE_BEHAVIOR = PROMPTS["base_behavior"]
```

### Contenido del prompt base

El prompt que recibe el modelo es el siguiente:

```
# ROL Y CONTEXTO
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
```

### Pruebas

#### Prueba de personalidad

> ¿Que pasa bro?! ¿Cómo va la vida? ¿Puedes hablar con mi jerga?

```
Hola. Mi función es asistirle con consultas relacionadas a Recursos Humanos, manteniendo un tono profesional y formal.

¿Hay algo sobre gestión de personal en lo que pueda ayudarte?
```

---

#### Prueba de estructura

> Hola! ¿Podrías decirme cuántos días de vacaciones tiene un informático?

```
Hola. El número de días de vacaciones de un informático, o de cualquier otro profesional, no depende de la profesión en sí, sino de varios factores clave definidos por la legislación laboral y las políticas de la empresa.

Para poder darte una orientación más precisa, necesitaría conocer la siguiente información:

- País o región
- Antigüedad en la empresa
- Convenio Colectivo o Contrato Individual

Generalmente, la ley establece un mínimo de días de vacaciones pagadas para todos los trabajadores, independientemente de su profesión. Si puedes proporcionarme los detalles mencionados, con gusto te daré una respuesta más específica.
```

---

#### Prueba de límites

> Hola, ¿qué tal? ¿Conoces a Leo Messi?

```
Estimado/a usuario/a,

Como asistente de un equipo de Recursos Humanos, mi función es atender consultas relacionadas con empleo, políticas internas, beneficios, contratación y otros asuntos propios del ámbito de RRHH.

No puedo ayudarle con esta consulta en particular.

Atentamente,

Equipo de Recursos Humanos
```

### Conclusión

El System Prompt es eficaz porque orienta al modelo a mantener un tono formal y profesional, centrado exclusivamente en temas de Recursos Humanos y filtrando consultas fuera de contexto. Además, garantiza respuestas estructuradas, informativas y alineadas con la normativa laboral, cumpliendo así los objetivos del Copiloto de ofrecer soporte fiable y pertinente en RRHH.

## Decisiones de diseño de RAG (Módulo 4)

### Estrategia de Chunking

**Configuración**: Tamaño de chunk de 500 caracteres con solapamiento de 50 caracteres.

**Justificación**:

- **500 caracteres** proporciona suficiente contexto sin exceso de granularidad. Los documentos de RRHH (políticas de vacaciones, gastos) contienen párrafos coherentes que caben cómodamente en este rango.
- **50 caracteres de solapamiento** asegura continuidad semántica entre chunks adyacentes, evitando que ideas importantes se corten a mitad de una oración o concepto.
- Este balance mejora tanto la precisión de búsqueda como la calidad de las respuestas del LLM.

### Modelo de Embeddings

**Modelo**: `nomic-embed-text` (ejecutado localmente vía Ollama).

**Justificación**:

- **Open-source y local**: No requiere API externa, reduciendo latencia y garantizando privacidad de datos.
- **Dimensión 768**: Balance óptimo entre capacidad representativa y eficiencia computacional.
- **Rendimiento**: Excelente desempeño en tareas de búsqueda semántica para documentos en español.
- **Costo**: Ejecución local elimina costos de APIs (OpenAI Embeddings, etc.).

### Base de Datos Vectorial

**Solución**: PostgreSQL + pgvector.

**Justificación**:

- **Integración ACID**: pgvector extiende PostgreSQL, permitiendo transacciones ACID sobre embeddings y metadatos simultáneamente.
- **Flexibilidad SQL**: Posibilidad de filtrar por metadatos (filename, chunk_index) además de búsqueda vectorial pura.
- **Escalabilidad**: PostgreSQL con pgvector escala bien para volúmenes moderados de documentos (miles de chunks).
- **Docker ready**: Docker Compose simplifica el setup local y en producción.

## Pruebas de conocimiento

### Prueba 1: Política de Vacaciones

**Request:**

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Cuantos días de vacaciones tiene disponibles un trabajador al año?"}'
```

**Respuesta obtenida:**

De acuerdo con la política de vacaciones proporcionada, un trabajador tiene derecho a **20 días laborables de vacaciones por año natural**.

Es importante recordar que este derecho aplica a empleados con contrato indefinido o temporal superior a 6 meses. Si un empleado ingresa o cesa durante el año, tendrá vacaciones proporcionales al tiempo trabajado.

---

### Prueba 2: Política de Gastos - Alojamiento

**Request:**

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Si tengo que viajar por trabajo, puedo coger cualquier tipo de hotel, o hay algún límite en el precio al que me tenga que adaptar?"}'
```

**Respuesta obtenida:**

De acuerdo con la política de gastos de la empresa, para el alojamiento en viajes de trabajo, puede utilizar **hoteles hasta tres estrellas**.

Si necesita un hotel de categoría superior, deberá contar con una justificación y aprobación previa.

---

### Prueba 3: Contacto con RRHH

**Request:**

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "A quién puedo escribir, si necesito comunicarme con una persona de RRHH?"}'
```

**Respuesta obtenida:**

Puedes comunicarte con una persona de RRHH escribiendo a **rrhh@empresa.com** o consultando directamente con el departamento de Recursos Humanos.

---

### Prueba 4: Días de vacaciones para trabajador de RRHH

**Request:**

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Cuántos días de vacaciones hay para un trabajador de RRHH?", "history": []}'
```

**Respuesta obtenida:**

Según la Política de Vacaciones proporcionada:

Todos los empleados, **incluyendo a los trabajadores de RRHH**, con contrato indefinido o temporal superior a 6 meses, tienen derecho a **20 días laborables de vacaciones por año natural**.

Si un empleado ingresa o cesa durante el año, tendrá vacaciones proporcionales al tiempo trabajado.

---

### Prueba 5: Continuidad de Conversación (con Historial)

**Request:**

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Y para un desarrollador?", "history": [{"role": "user", "content": "Cuántos días de vacaciones hay para un trabajador de RRHH"}, {"role": "assistant", "content": "Según la Política de Vacaciones proporcionada: Todos los empleados, **incluyendo a los trabajadores de RRHH**, con contrato indefinido o temporal superior a 6 meses, tienen derecho a **20 días laborables de vacaciones por año natural**.Si un empleado ingresa o cesa durante el año, tendrá vacaciones proporcionales al tiempo trabajado."}]}'
```

**Respuesta obtenida:**

Según la Política de Vacaciones proporcionada, el derecho a vacaciones es el mismo para **todos los empleados** que cumplan con las condiciones de contrato (indefinido o temporal superior a 6 meses).

Por lo tanto, un desarrollador también tendrá derecho a **20 días laborables de vacaciones por año natural**, siempre que cumpla con los requisitos de antigüedad y tipo de contrato establecidos en la política.

---

Algunos ejemplos de historial con ADK:

```bash
curl -D - -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Puedes por favor decirme cuál es la raíz cuadrada de 3 y ese resultado multiplicarlo por 7?"}'
HTTP/1.1 200 OK
date: Fri, 26 Dec 2025 13:48:25 GMT
server: uvicorn
content-type: text/plain; charset=utf-8
x-session-id: 8d6e5587-e83c-453d-b125-98b7c90a3a3b
Transfer-Encoding: chunked

La raíz cuadrada de 3 multiplicada por 7 es aproximadamente 12.12.%

```

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Dame 12 decimales",
 "session_id": "d6c25718-fa39-4b27-ba09-d336da6df1f2"}'
{"detail":"404: Session not found"}
```

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Pide 5 días de vacaciones a partir del lunes"}'
¡Tu solicitud de 5 días de vacaciones a partir del lunes ha sido enviada! Tus vacaciones irán desde el 29 de diciembre de 2025 hasta el 2 de enero de 2026.
```

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Pide vacaciones entre los días 2/3/2026 y 5/3/2026"}'
¡Claro! Tus vacaciones han sido solicitadas desde el 2 de marzo de 2026 hasta el 5 de marzo de 2026.
```

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Pídeme de vacaciones la primera semana laborable de febrero de 2026"}'
Para poder solicitar tus vacaciones, necesito confirmar las fechas exactas.

Si te refieres a la primera semana completa de trabajo de febrero de 2026, esto sería **del lunes 2 de febrero al viernes 6 de febrero de 2026**, lo que suma 5 días laborables.

¿Estás de acuerdo con estas fechas para tu solicitud de vacaciones?
```
