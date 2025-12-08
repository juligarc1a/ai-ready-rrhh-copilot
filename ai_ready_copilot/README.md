# AI Ready RRHH Copilot

Un copiloto de IA para gestión de recursos humanos.

## Requisitos previos

- Python >= 3.14
- [Poetry](https://python-poetry.org/docs/#installation)

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

### Modo producción

Para ejecutar en modo producción (sin recarga automática):

```bash
poetry run uvicorn ai_ready_copilot.src.ai_ready_copilot.app:app
```

## Desarrollo

### Ejecutar tests

```bash
poetry run pytest
```

### Ejecutar tests con cobertura

```bash
poetry run pytest --cov=ai_ready_copilot
```

## Estructura del proyecto

```
ai_ready_copilot/
├── src/
│   └── ai_ready_copilot/
│       ├── __init__.py
│       └── app.py          # Aplicación FastAPI principal
├── tests/                  # Tests unitarios
├── pyproject.toml          # Configuración de Poetry
├── README.md               # Este archivo
└── .env                    # Variables de entorno (no versionado)
```

## Dependencias principales

- **FastAPI**: Framework web asincrónico
- **Uvicorn**: Servidor ASGI
- **Pydantic**: Validación de datos
- **python-dotenv**: Gestión de variables de entorno

## Licencia

MIT
