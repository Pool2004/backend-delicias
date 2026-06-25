import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import List, Dict, Any

# Cargar variables de entorno del archivo .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
texto = "Hola"

def get_db_connection():
    """
    Establece una conexión con la base de datos PostgreSQL de Supabase.
    Soporta DATABASE_URL o parámetros individuales.
    """
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )

# Fechas de atencion: miercoles 8 y jueves 9 de julio de 2026
FECHAS_ATENCION = [
    {"etiqueta": "Mié 8/Jul", "fecha": "2026-07-08"},
    {"etiqueta": "Jue 9/Jul", "fecha": "2026-07-09"},
]

# Franjas horarias base de 7 AM a 3 PM (incluyendo las 15:00) con intervalos de 15 minutos
HORAS_BASE = []
for h in range(7, 16):
    for m in ["00", "15", "30", "45"]:
        if h == 15 and m != "00":
            break
        HORAS_BASE.append(f"{h:02d}:{m}")

# Franja de almuerzo excluida por grupo
# Grupo A: no atiende de 12:00 a 12:45
# Grupo B: no atiende de 13:00 a 13:45
ALMUERZO = {
    "A": "12",
    "B": "13"
}


def generar_horarios(grupo: str) -> List[str]:
    """
    Genera la lista completa de franjas horarias disponibles para los dos dias
    de atencion, excluyendo la hora de almuerzo correspondiente al grupo.
    El formato de cada slot es: 'Mie 8/Jul 07:00' o 'Jue 9/Jul 07:00'.
    """
    prefijo_excluido = ALMUERZO.get(grupo, "")
    slots = []
    for fecha in FECHAS_ATENCION:
        for hora in HORAS_BASE:
            if prefijo_excluido and hora.startswith(f"{prefijo_excluido}:"):
                continue
            slots.append(f"{fecha['etiqueta']} {hora}")
    return slots


def obtener_todos_los_grados() -> List[Dict[str, str]]:
    """
    Retorna la lista de docentes disponibles recuperados desde Supabase.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id AS grado, grupo, docente, area FROM docentes ORDER BY id::integer ASC;")
                return list(cur.fetchall())
    except Exception as e:
        print(f"Error al obtener todos los grados desde la DB: {e}")
        return []


def buscar_grado_por_id(grado_id: str) -> Dict[str, Any]:
    """
    Busca un miembro del personal por su identificador único en Supabase.
    Retorna None si no existe.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, docente, area, grupo, correo FROM docentes WHERE id = %s;", (grado_id,))
                res = cur.fetchone()
                if res:
                    res_dict = dict(res)
                    res_dict["horarios_base"] = generar_horarios(res_dict["grupo"])
                    return res_dict
                return None
    except Exception as e:
        print(f"Error al buscar grado por ID en la DB: {e}")
        return None


def leer_citas(correo: str = None) -> List[Dict[str, Any]]:
    """
    Retorna la lista completa de todas las citas agendadas desde Supabase,
    opcionalmente filtrada por correo electrónico.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if correo:
                    cur.execute(
                        "SELECT acudiente, telefono, correo, estudiante, docente_id AS grado, horario, estado FROM citas WHERE correo = %s;",
                        (correo.strip(),)
                    )
                else:
                    cur.execute("SELECT acudiente, telefono, correo, estudiante, docente_id AS grado, horario, estado FROM citas;")
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"Error al leer citas desde la DB: {e}")
        return []


def obtener_cita_por_horario(grado_id: str, horario: str) -> Dict[str, Any]:
    """
    Recupera los detalles de una cita específica por docente y horario.
    Retorna None si no existe.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT acudiente, telefono, correo, estudiante, docente_id AS grado, horario, estado FROM citas WHERE docente_id = %s AND horario = %s LIMIT 1;",
                    (grado_id, horario)
                )
                row = cur.fetchone()
                return dict(row) if row else None
    except Exception as e:
        print(f"Error al obtener cita por horario en la DB: {e}")
        return None


def verificar_cita_existente(grado_id: str, horario: str) -> bool:
    """
    Verifica si ya existe un agendamiento para ese docente y horario en la base de datos.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM citas WHERE docente_id = %s AND horario = %s LIMIT 1;", (grado_id, horario))
                return cur.fetchone() is not None
    except Exception as e:
        print(f"Error al verificar cita existente: {e}")
        return False


def crear_cita(acudiente: str, telefono: str, correo: str, estudiante: str, grado_id: str, horario: str) -> bool:
    """
    Inserta un nuevo registro de cita en la tabla 'citas' en Supabase.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO citas (acudiente, telefono, correo, estudiante, docente_id, horario) VALUES (%s, %s, %s, %s, %s, %s);",
                    (acudiente, telefono, correo, estudiante, grado_id, horario)
                )
                conn.commit()
                return True
    except Exception as e:
        print(f"Error al guardar la cita en la DB: {e}")
        return False


def eliminar_cita(grado_id: str, horario: str) -> bool:
    """
    Elimina una cita específica filtrando por docente y horario.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM citas WHERE docente_id = %s AND horario = %s;", (grado_id, horario))
                conn.commit()
                return True
    except Exception as e:
        print(f"Error al eliminar la cita en la DB: {e}")
        return False


def actualizar_estado_cita(grado_id: str, horario: str, nuevo_estado: str) -> bool:
    """
    Actualiza el estado de una cita específica en Supabase.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE citas SET estado = %s WHERE docente_id = %s AND horario = %s;",
                    (nuevo_estado, grado_id, horario)
                )
                conn.commit()
                return True
    except Exception as e:
        print(f"Error al actualizar el estado de la cita en la DB: {e}")
        return False


def obtener_horarios_disponibles(grado_id: str) -> Dict[str, Any]:
    """
    Retorna el nombre, area y horarios disponibles del funcionario especificado,
    filtrando los que ya han sido reservados por otros acudientes.
    """
    persona = buscar_grado_por_id(grado_id)
    if not persona:
        return None

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT horario FROM citas WHERE docente_id = %s;", (grado_id,))
                citas_existentes = cur.fetchall()
                
        horarios_reservados = {cita["horario"] for cita in citas_existentes}
        
        horarios_disponibles = [
            h for h in persona["horarios_base"]
            if h not in horarios_reservados
        ]

        return {
            "docente": persona["docente"],
            "area": persona["area"],
            "grupo": persona["grupo"],
            "correo": persona["correo"],
            "horarios": horarios_disponibles
        }
    except Exception as e:
        print(f"Error al obtener horarios disponibles desde la DB: {e}")
        return None

def obtener_rol_admin(usuario: str, contrasena: str) -> str:
    """
    Verifica si las credenciales coinciden y retorna el rol del usuario, o None si es inválido.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT rol FROM administrativos WHERE usuario = %s AND contrasena = %s LIMIT 1;",
                    (usuario.strip(), contrasena.strip())
                )
                row = cur.fetchone()
                if row:
                    return row[0]
                return None
    except Exception as e:
        print(f"Error al validar credenciales y obtener rol en la DB: {e}")
        return None

def reprogramar_cita(grado_actual: str, grado_nuevo: str, horario_actual: str, horario_nuevo: str) -> bool:
    """
    Actualiza el docente y horario de una cita específica de forma atómica en Supabase.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE citas SET docente_id = %s, horario = %s WHERE docente_id = %s AND horario = %s;",
                    (grado_nuevo, horario_nuevo, grado_actual, horario_actual)
                )
                conn.commit()
                return True
    except Exception as e:
        print(f"Error al reprogramar la cita en la DB: {e}")
        return False
