import re
import threading
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from data import (
    obtener_todos_los_grados,
    obtener_horarios_disponibles,
    leer_citas,
    buscar_grado_por_id,
    verificar_cita_existente,
    crear_cita,
    eliminar_cita,
    obtener_rol_admin,
    reprogramar_cita,
    obtener_cita_por_horario,
    actualizar_estado_cita
)
from email_utils import (
    enviar_correo_confirmacion,
    enviar_correo_docente,
    enviar_correo_cancelacion,
    enviar_correo_reprogramacion,
    enviar_correos_nuevo_agendamiento
)

router = APIRouter(prefix="/api")

# Modelo de Pydantic para validar los datos de la cita recibida
class CitaSchema(BaseModel):
    acudiente: str = Field(..., min_length=2, description="Nombre completo del acudiente")
    telefono: str = Field(..., min_length=7, description="Número de teléfono de contacto")
    correo: str = Field(..., description="Correo electrónico de contacto")
    estudiante: str = Field(..., min_length=2, description="Nombre completo del estudiante")
    grado: str = Field(..., description="Grado seleccionado")
    horario: str = Field(..., description="Horario seleccionado")

# Modelo de Pydantic para el inicio de sesión administrativo
class LoginSchema(BaseModel):
    usuario: str = Field(..., min_length=1, description="Nombre de usuario del administrativo")
    contrasena: str = Field(..., min_length=1, description="Contraseña del administrativo")

# Modelo de Pydantic para reprogramar citas
class ReprogramarCitaSchema(BaseModel):
    grado_actual: str = Field(..., description="ID actual del docente/grado")
    grado_nuevo: str = Field(..., description="Nuevo ID del docente/grado")
    horario_actual: str = Field(..., description="Horario actual de la cita")
    horario_nuevo: str = Field(..., description="Nuevo horario solicitado")

# Modelo de Pydantic para actualizar el estado de una cita (ej: Atendido)
class CitaEstadoSchema(BaseModel):
    grado: str = Field(..., description="ID del docente/grado")
    horario: str = Field(..., description="Horario de la cita")
    estado: str = Field(..., description="Nuevo estado de la cita")

# Expresión regular sencilla para validar el formato de correo electrónico sin dependencias adicionales
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

@router.get("/grados", response_model=List[Dict[str, str]])
def list_grados():
    """
    Retorna la lista de todos los grados con su grupo y docente asignado.
    """
    return obtener_todos_los_grados()

@router.get("/horarios/{grado}", response_model=Dict[str, Any])
def get_horarios(grado: str):
    """
    Retorna el docente y los horarios disponibles para el grado especificado.
    Lanza error 404 si el grado no existe.
    """
    horarios_info = obtener_horarios_disponibles(grado)
    if not horarios_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El grado '{grado}' no está registrado en el sistema."
        )
    return horarios_info

@router.post("/citas", response_model=Dict[str, Any])
def create_cita(cita: CitaSchema):
    """
    Registra una nueva cita si pasa todas las validaciones:
    - Campos obligatorios no vacíos (manejado por Pydantic y validación manual de espacios).
    - Email con formato correcto.
    - El grado especificado debe existir.
    - El horario debe ser uno de los horarios base del grado.
    - Evita reservas duplicadas: el horario para este grado no debe estar ya reservado.
    """
    # Limpieza de espacios en blanco al inicio y al final de los textos
    acudiente = cita.acudiente.strip()
    telefono = cita.telefono.strip()
    correo = cita.correo.strip()
    estudiante = cita.estudiante.strip()
    grado_id = cita.grado.strip()
    horario = cita.horario.strip()

    # Validaciones manuales de campos obligatorios para asegurar que no contengan solo espacios
    if not acudiente or not telefono or not correo or not estudiante or not grado_id or not horario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todos los campos son obligatorios y no deben contener únicamente espacios."
        )

    # Validación de formato de correo electrónico
    if not EMAIL_REGEX.match(correo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ingresado no tiene un formato válido."
        )

    # Validar que el grado exista en el sistema
    grado_info = buscar_grado_por_id(grado_id)
    if not grado_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El grado '{grado_id}' no existe."
        )

    # Validar que el horario propuesto pertenezca a los horarios base de ese grado
    if horario not in grado_info["horarios_base"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El horario '{horario}' no pertenece al cronograma del docente asignado al grado {grado_id}."
        )

    # Evitar reservas duplicadas: verificar si ya existe una cita registrada para ese grado y horario
    if verificar_cita_existente(grado_id, horario):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El horario '{horario}' para el grado {grado_id} ya ha sido reservado por otro acudiente."
        )

    # Crear la nueva cita y guardarla en la base de datos
    if not crear_cita(acudiente, telefono, correo, estudiante, grado_id, horario):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al intentar guardar la cita en la base de datos."
        )

    # Enviar correos de confirmación (acudiente y docente) en segundo plano
    # usando una sola conexión SMTP secuencial para evitar conflictos de login con Office 365.
    correo_docente = grado_info.get("correo")
    hilo_correo = threading.Thread(
        target=enviar_correos_nuevo_agendamiento,
        kwargs={
            "correo_padre": correo,
            "correo_docente": correo_docente,
            "acudiente": acudiente,
            "estudiante": estudiante,
            "grado": grado_id,
            "grupo": grado_info["grupo"],
            "docente": grado_info["docente"],
            "horario": horario,
            "telefono": telefono,
            "area": grado_info["area"] if grado_info else ""
        },
        daemon=True
    )
    hilo_correo.start()

    return {
        "success": True,
        "message": "Agendamiento registrado correctamente. Se ha enviado un correo de confirmacion a su direccion de correo electronico (si no lo recibe, por favor revise la carpeta de correo no deseado o spam)."
    }

@router.get("/citas", response_model=List[Dict[str, Any]])
def list_citas(correo: str = None):
    """
    Retorna la lista de todas las citas agendadas, opcionalmente filtradas por correo electrónico.
    """
    return leer_citas(correo)

@router.delete("/citas")
def delete_cita(grado: str, horario: str):
    """
    Cancela un agendamiento existente buscando por grado y horario.
    """
    grado_id = grado.strip()
    horario_str = horario.strip()

    if not verificar_cita_existente(grado_id, horario_str):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún agendamiento para el grado y horario especificados."
        )

    # Obtener detalles de la cita y docente antes de eliminar
    cita_info = obtener_cita_por_horario(grado_id, horario_str)

    if not eliminar_cita(grado_id, horario_str):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al intentar guardar los cambios en la base de datos."
        )

    if cita_info:
        grado_info = buscar_grado_por_id(grado_id)
        grupo_str = grado_info["grupo"] if grado_info else ""
        docente_str = grado_info["docente"] if grado_info else ""
        correo_docente = grado_info.get("correo") if grado_info else None
        
        hilo_correo = threading.Thread(
            target=enviar_correo_cancelacion,
            kwargs={
                "destinatario_padre": cita_info["correo"],
                "correo_docente": correo_docente,
                "acudiente": cita_info["acudiente"],
                "estudiante": cita_info["estudiante"],
                "grado": grado_id,
                "grupo": grupo_str,
                "docente": docente_str,
                "horario": horario_str,
                "telefono": cita_info["telefono"],
                "area": grado_info["area"] if grado_info else ""
            },
            daemon=True
        )
        hilo_correo.start()

    return {
        "success": True,
        "message": "El agendamiento ha sido cancelado con éxito y el horario ha sido liberado."
    }

@router.post("/login")
def login(credentials: LoginSchema):
    """
    Autentica a un administrativo con usuario y contraseña y retorna su rol.
    """
    rol = obtener_rol_admin(credentials.usuario, credentials.contrasena)
    if rol:
        return {
            "success": True,
            "message": "Inicio de sesión exitoso",
            "rol": rol
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

@router.put("/citas/reprogramar")
def route_reprogramar_cita(payload: ReprogramarCitaSchema):
    """
    Reprograma un agendamiento liberando el horario anterior, reasignando docente y horario,
    y enviando notificaciones por correo electrónico al acudiente y docentes involucrados.
    """
    grado_actual = payload.grado_actual.strip()
    grado_nuevo = payload.grado_nuevo.strip()
    horario_actual = payload.horario_actual.strip()
    horario_nuevo = payload.horario_nuevo.strip()
    
    # Validar disponibilidad del nuevo horario para el docente/grado destino
    if verificar_cita_existente(grado_nuevo, horario_nuevo):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El horario '{horario_nuevo}' ya se encuentra reservado para este grado."
        )
        
    # Obtener detalles de la cita antes de reprogramar
    cita_info = obtener_cita_por_horario(grado_actual, horario_actual)
    if not cita_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el agendamiento original a reprogramar."
        )
        
    # Obtener información de los docentes involucrados
    docente_antiguo_info = buscar_grado_por_id(grado_actual)
    docente_nuevo_info = buscar_grado_por_id(grado_nuevo)
    
    if not docente_nuevo_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El nuevo docente/grado seleccionado no existe."
        )
        
    # Intentar la reprogramación en base de datos
    if not reprogramar_cita(grado_actual, grado_nuevo, horario_actual, horario_nuevo):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al intentar reprogramar la cita en la base de datos."
        )
        
    # Enviar notificaciones por correo en segundo plano
    hilo_correo = threading.Thread(
        target=enviar_correo_reprogramacion,
        kwargs={
            "destinatario_padre": cita_info["correo"],
            "correo_docente_antiguo": docente_antiguo_info.get("correo") if docente_antiguo_info else None,
            "correo_docente_nuevo": docente_nuevo_info.get("correo"),
            "acudiente": cita_info["acudiente"],
            "estudiante": cita_info["estudiante"],
            "telefono": cita_info["telefono"],
            "docente_antiguo": docente_antiguo_info["docente"] if docente_antiguo_info else "Docente Anterior",
            "docente_nuevo": docente_nuevo_info["docente"],
            "grado_antiguo": grado_actual,
            "grado_nuevo": grado_nuevo,
            "grupo_antiguo": docente_antiguo_info["grupo"] if docente_antiguo_info else "",
            "grupo_nuevo": docente_nuevo_info["grupo"],
            "horario_antiguo": horario_actual,
            "horario_nuevo": horario_nuevo,
            "area_antigua": docente_antiguo_info["area"] if docente_antiguo_info else "",
            "area_nueva": docente_nuevo_info["area"] if docente_nuevo_info else ""
        },
        daemon=True
    )
    hilo_correo.start()
    
    return {
        "success": True,
        "message": "La cita ha sido reprogramada con éxito."
    }


@router.put("/citas/estado", response_model=Dict[str, Any])
def update_cita_estado(payload: CitaEstadoSchema):
    """
    Actualiza el estado de un agendamiento existente.
    """
    grado = payload.grado.strip()
    horario = payload.horario.strip()
    nuevo_estado = payload.estado.strip()

    # Validar que el agendamiento exista
    if not verificar_cita_existente(grado, horario):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún agendamiento para el grado y horario especificados."
        )

    # Actualizar el estado en la base de datos
    if not actualizar_estado_cita(grado, horario, nuevo_estado):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al intentar actualizar el estado de la cita en la base de datos."
        )

    return {
        "success": True,
        "message": f"El estado del agendamiento ha sido actualizado a '{nuevo_estado}' con éxito."
    }

