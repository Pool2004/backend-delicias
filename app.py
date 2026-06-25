from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router

# Inicialización de la aplicación FastAPI con metadatos descriptivos
app = FastAPI(
    title="Sistema de Agendamiento de Citas de Padres",
    description="API REST para coordinar y reservar citas entre padres y docentes.",
    version="1.0.0"
)

# Configuración del middleware CORS para evitar problemas de comunicación entre el frontend y el backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones desde cualquier origen
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos HTTP (GET, POST, etc.)
    allow_headers=["*"],  # Permite todas las cabeceras HTTP en las solicitudes
)

# Inclusión del enrutador que contiene todas las llamadas de la API
app.include_router(router)

# Ruta base para verificar que la API está en funcionamiento
@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Servidor de Agendamiento de Citas Docente-Acudiente funcionando correctamente."
    }
