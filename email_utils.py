import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno del archivo .env (buscando en la carpeta raíz del proyecto)
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Credenciales de Brevo API configuradas mediante variables de entorno.
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")

def send_email_brevo(to, subject, html, text, sender_name="Comfandi Las Delicias") -> bool:
    """
    Envia un correo electronico utilizando la API REST v3 de Brevo.
    Evita el bloqueo de puertos SMTP de Render Free.
    Retorna True si el envio fue exitoso, False en caso contrario.
    """
    if not EMAIL_SENDER:
        print("[Correo] Error: EMAIL_SENDER no está configurada.")
        return False
    if not BREVO_API_KEY:
        print("[Correo] Error: BREVO_API_KEY no está configurada.")
        return False

    # Formatear destinatarios
    if isinstance(to, str):
        destinatarios = [email.strip() for email in to.replace(";", ",").split(",") if email.strip()]
    elif isinstance(to, (list, tuple, set)):
        destinatarios = [str(email).strip() for email in to if str(email).strip()]
    else:
        destinatarios = [str(to).strip()]

    if not destinatarios:
        print("[Correo] Error: No se especificaron destinatarios válidos.")
        return False

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    # Payload para Brevo API v3
    payload = {
        "sender": {
            "name": sender_name,
            "email": EMAIL_SENDER
        },
        "to": [{"email": email} for email in destinatarios],
        "subject": subject
    }

    if html:
        payload["htmlContent"] = html
    if text:
        payload["textContent"] = text

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if 200 <= response.status_code < 300:
            print(f"[Correo] Correo enviado exitosamente a {destinatarios} vía Brevo API (Status: {response.status_code})")
            return True
        else:
            print(f"[Correo] Error al enviar correo via Brevo API. Status: {response.status_code}")
            print(f"[Correo] Response Body: {response.text}")
            return False
    except Exception as e:
        print(f"[Correo] Error inesperado al conectar con Brevo API: {e}")
        return False


def formatear_horario_completo(horario: str):
    """
    Convierte un horario tipo "Mié 8/Jul 07:00" en:
    dia_completo: "Miércoles, 8 de Julio de 2026"
    hora_completa: "07:00"
    """
    partes = [p.strip() for p in horario.split(" ") if p.strip()]
    if len(partes) < 3:
        return horario, ""

    dia_abrev = partes[0]
    fecha_abrev = partes[1]
    hora = partes[2]

    dias_semana = {
        "Lun": "Lunes", "Mar": "Martes", "Mié": "Miércoles",
        "Jue": "Jueves", "Vie": "Viernes", "Sáb": "Sábado", "Dom": "Domingo"
    }

    meses = {
        "Ene": "Enero", "Feb": "Febrero", "Mar": "Marzo",
        "Abr": "Abril", "May": "Mayo", "Jun": "Junio",
        "Jul": "Julio", "Ago": "Agosto", "Sep": "Septiembre",
        "Oct": "Octubre", "Nov": "Noviembre", "Dic": "Diciembre"
    }

    dia_nombre = dias_semana.get(dia_abrev, dia_abrev)

    partes_fecha = fecha_abrev.split("/")
    if len(partes_fecha) == 2:
        num_dia = partes_fecha[0]
        mes_abrev = partes_fecha[1]
        mes_nombre = meses.get(mes_abrev, mes_abrev)
        dia_completo = f"{dia_nombre}, {num_dia} de {mes_nombre} de 2026"
    else:
        dia_completo = f"{dia_nombre} {fecha_abrev}"

    return dia_completo, hora


def formatear_horario_completo_string(horario: str) -> str:
    dia_completo, hora = formatear_horario_completo(horario)
    if hora:
        return f"{dia_completo} a las {hora}"
    return dia_completo



def enviar_correo_confirmacion(
    destinatario: str,
    acudiente: str,
    estudiante: str,
    grado: str,
    grupo: str,
    docente: str,
    horario: str,
    telefono: str,
    servidor=None,
    area: str = ""
) -> bool:
    """
    Envia un correo electronico de confirmacion al acudiente con los detalles
    del agendamiento de matricula academica registrado en el sistema.

    Retorna True si el envio fue exitoso, False en caso contrario.
    """
    

    # Separar el dia y la hora del horario para mostrarlo de forma mas clara
    dia_cita, hora_cita = formatear_horario_completo(horario)

    label_grado = "Grado" if area else "Grado a matricular"
    valor_grado = area if area else f"Grado {grado} (Grupo {grupo})"

    # Construccion del cuerpo HTML del correo con todos los detalles del agendamiento
    cuerpo_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f7f6;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 580px;
                margin: 32px auto;
                background-color: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            }}
            .header {{
                background-color: #264fa0;
                padding: 28px 32px;
                text-align: center;
            }}
            .header h1 {{
                color: #ffffff;
                margin: 0;
                font-size: 20px;
                font-weight: 700;
            }}
            .header p {{
                color: #b3c9f0;
                margin: 6px 0 0;
                font-size: 13px;
            }}
            .body {{
                padding: 28px 32px;
            }}
            .greeting {{
                font-size: 15px;
                color: #334155;
                margin-bottom: 16px;
                line-height: 1.6;
            }}
            .detail-box {{
                background-color: #f0f5ff;
                border-left: 4px solid #264fa0;
                border-radius: 8px;
                padding: 20px 24px;
                margin: 20px 0;
            }}
            .detail-box h2 {{
                color: #264fa0;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin: 0 0 14px;
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                font-size: 14px;
                padding: 6px 0;
                border-bottom: 1px solid #dbeafe;
            }}
            .detail-row:last-child {{
                border-bottom: none;
            }}
            .detail-label {{
                color: #64748b;
                font-weight: 600;
            }}
            .detail-value {{
                color: #1e293b;
                font-weight: 500;
                text-align: right;
            }}
            .notice {{
                background-color: #fffbeb;
                border: 1px solid #fde68a;
                border-radius: 8px;
                padding: 14px 18px;
                font-size: 13px;
                color: #92400e;
                line-height: 1.6;
                margin-top: 20px;
            }}
            .docs-box {{
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 20px 24px;
                margin: 20px 0;
            }}
            .docs-box h2 {{
                color: #1e293b;
                font-size: 14px;
                font-weight: 700;
                margin: 0 0 12px;
            }}
            .docs-list {{
                padding-left: 20px;
                margin: 0;
                font-size: 13px;
                color: #475569;
                line-height: 1.6;
            }}
            .docs-list li {{
                margin-bottom: 8px;
            }}
            .footer {{
                background-color: #264fa0;
                padding: 16px 32px;
                text-align: center;
                font-size: 12px;
                color: #b3c9f0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Confirmacion de Agendamiento de Matricula</h1>
                <p>Sistema de Agendamiento Academico - Comfandi Las Delicias</p>
            </div>
            <div class="body">
                <p class="greeting">
                    Estimado/a <strong>{acudiente}</strong>,<br><br>
                    Le confirmamos que su agendamiento de cita para el proceso de
                    <strong>Matricula Academica 2026 - 2027</strong> ha sido registrado correctamente
                    en nuestro sistema. A continuacion encontrara los detalles de su cita:
                </p>

                <div class="detail-box">
                    <h2>Detalles del Agendamiento</h2>
                    <div class="detail-row">
                        <span class="detail-label">Estudiante:</span>
                        <span class="detail-value">{estudiante}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">{label_grado}:</span>
                        <span class="detail-value">{valor_grado}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Docente encargado:</span>
                        <span class="detail-value">{docente}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Dia de la cita:</span>
                        <span class="detail-value">{dia_cita}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Hora de atencion:</span>
                        <span class="detail-value">{hora_cita}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Telefono de contacto:</span>
                        <span class="detail-value">{telefono}</span>
                    </div>
                </div>

                <div class="docs-box">
                    <h2>Documentos requeridos para formalizar la matrícula:</h2>
                    <ul class="docs-list">
                        <li>Ficha de matrícula (se entrega en el colegio)</li>
                        <li>Contrato de Matrícula*</li>
                        <li>Consentimiento informado para atención en psicología*</li>
                        <li>Formato Ley 2300 formato para autorización de medidas de protección al derecho de intimidad de los consumidores Comfandi</li>
                        <li>Pagaré y Carta de Instrucciones para firmar un pagaré en blanco</li>
                        <li>Fotocopia del Informe descriptivo - explicativo final del grado anterior.</li>
                        <li>Certificados de estudio originales de años anteriores cursados y aprobados.</li>
                        <li>Paz y Salvo de costos educativos y constancia de retiro del SIMAT del colegio anterior.</li>
                        <li>Fotocopia del registro civil y la tarjeta de identidad del estudiante. (en los casos que aplique)</li>
                        <li>Fotocopia del carnet actualizado de vacunación.</li>
                        <li>Fotocopias del carnet de crecimiento y desarrollo actualizado.</li>
                        <li>Certificado afiliación EPS</li>
                        <li>1 foto reciente del estudiante tamaño cédula, marcada con nombre completo y grado.</li>
                        <li>Para estudiantes extranjeros, fotocopia de la visa vigente expedida por la autoridad competente, que los faculte para realizar estudios en Colombia.</li>
                        <li>Fotocopia legible de las cédulas de ciudadanía del Deudor y Deudor Solidario.</li>
                        <li>Carta salarial o el último comprobante de pago original del Deudor y Deudor Solidario, estos deben tener impreso el Nit, dirección y teléfono de la empresa y su fecha de expedición debe ser no mayor a tres meses al momento de la matrícula. Los empleados de Comfandi sólo deben anexar el último comprobante de pago de nómina.</li>
                        <li>Presencia simultánea del Deudor y Deudor Solidario para las firmas del pagaré y carta de instrucciones o documentos debidamente firmados y autenticados en notaría, si así lo ha solicitado el padre o acudiente.</li>
                        <li>El deudor solidario no puede ser pensionado.</li>
                        <li>En caso de que el Deudor y/o Deudor Solidario sean trabajadores independientes deberán presentar certificado de ingresos con vigencia NO superior a tres meses y adjuntar la fotocopia de la tarjeta profesional del contador público.</li>
                    </ul>
                </div>

                <div class="notice">
                    <strong>Recuerde:</strong> Asista puntualmente a su cita con la documentacion
                    completa requerida para el proceso de matricula. En caso de no poder asistir,
                    comuniquese con la institucion con la mayor anticipacion posible.
                </div>
            </div>
            <div class="footer">
                Comfandi &mdash; Las Delicias &mdash; 2026<br>
                Este es un mensaje automatico, por favor no responda a este correo.
            </div>
        </div>
    </body>
    </html>
    """

    asunto = f"Confirmacion de Matricula - {estudiante} | Comfandi Las Delicias 2026"
    texto_plano = (
        f"Confirmacion de Agendamiento de Matricula - Comfandi Las Delicias 2026\n\n"
        f"Acudiente: {acudiente}\n"
        f"Estudiante: {estudiante}\n"
        f"{label_grado}: {valor_grado}\n"
        f"Docente: {docente}\n"
        f"Horario: {horario}\n"
        f"Telefono: {telefono}\n\n"
        f"Documentos requeridos para formalizar la matrícula:\n"
        f"• Ficha de matrícula (se entrega en el colegio)\n"
        f"• Contrato de Matrícula*\n"
        f"• Consentimiento informado para atención en psicología*\n"
        f"• Formato Ley 2300 formato para autorización de medidas de protección al derecho de intimidad de los consumidores Comfandi,\n"
        f"• Pagaré y Carta de Instrucciones para firmar un pagaré en blanco\n"
        f"• Fotocopia del Informe descriptivo - explicativo final del grado anterior.\n"
        f"• Certificados de estudio originales de años anteriores cursados y aprobados.\n"
        f"• Paz y Salvo de costos educativos y constancia de retiro del SIMAT del colegio anterior.\n"
        f"• Fotocopia del registro civil y la tarjeta de identidad del estudiante (en los casos que aplique).\n"
        f"• Fotocopia del carnet actualizado de vacunación.\n"
        f"• Fotocopias del carnet de crecimiento y desarrollo actualizado.\n"
        f"• Certificado afiliación EPS\n"
        f"• 1 foto reciente del estudiante tamaño cédula, marcada con nombre completo y grado.\n"
        f"• Para estudiantes extranjeros, fotocopia de la visa vigente expedida por la autoridad competente, que los faculte para realizar estudios en Colombia.\n"
        f"• Fotocopia legible de las cédulas de ciudadanía del Deudor y Deudor Solidario.\n"
        f"• Carta salarial o el último comprobante de pago original del Deudor y Deudor Solidario, estos deben tener impreso el Nit, dirección y teléfono de la empresa y su fecha de expedición debe ser no mayor a tres meses al momento de la matrícula. Los empleados de Comfandi sólo deben anexar el último comprobante de pago de nómina.\n"
        f"• Presencia simultánea del Deudor y Deudor Solidario para las firmas del pagaré y carta de instrucciones o documentos debidamente firmados y autenticados en notaría, si así lo ha solicitado el padre o acudiente.\n"
        f"• El deudor solidario no puede ser pensionado.\n"
        f"• En caso de que el Deudor y/o Deudor Solidario sean trabajadores independientes deberán presentar certificado de ingresos con vigencia NO superior a tres meses y adjuntar la fotocopia de la tarjeta profesional del contador público.\n\n"
        f"Por favor asista puntualmente con la documentacion requerida."
    )

    return send_email_brevo(
        to=destinatario,
        subject=asunto,
        html=cuerpo_html,
        text=texto_plano,
        sender_name="Comfandi Las Delicias"
    )


def enviar_correo_docente(
    correo_docente: str,
    docente: str,
    acudiente: str,
    estudiante: str,
    grado: str,
    grupo: str,
    horario: str,
    telefono: str,
    servidor=None,
    area: str = ""
) -> bool:
    """
    Envia un correo electronico de notificacion al docente con los detalles
    del nuevo agendamiento de matricula academica.
    """
    if not EMAIL_SENDER or not BREVO_API_KEY or not correo_docente:
        return False

    dia_cita, hora_cita = formatear_horario_completo(horario)

    label_grado = "Grado" if area else "Grado a matricular"
    valor_grado = area if area else f"Grado {grado} (Grupo {grupo})"

    cuerpo_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 0; }}
            .container {{ max-width: 580px; margin: 32px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
            .header {{ background-color: #0f766e; padding: 28px 32px; text-align: center; }}
            .header h1 {{ color: #ffffff; margin: 0; font-size: 20px; font-weight: 700; }}
            .header p {{ color: #ccfbf1; margin: 6px 0 0; font-size: 13px; }}
            .body {{ padding: 28px 32px; }}
            .greeting {{ font-size: 15px; color: #334155; margin-bottom: 16px; line-height: 1.6; }}
            .detail-box {{ background-color: #f0fdfa; border-left: 4px solid #0f766e; border-radius: 8px; padding: 20px 24px; margin: 20px 0; }}
            .detail-box h2 {{ color: #0f766e; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 14px; }}
            .detail-row {{ display: flex; justify-content: space-between; font-size: 14px; padding: 6px 0; border-bottom: 1px solid #ccfbf1; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .detail-label {{ color: #64748b; font-weight: 600; }}
            .detail-value {{ color: #1e293b; font-weight: 500; text-align: right; }}
            .footer {{ background-color: #0f766e; padding: 16px 32px; text-align: center; font-size: 12px; color: #ccfbf1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Nuevo Agendamiento Recibido</h1>
                <p>Sistema de Agendamiento Academico - Comfandi Las Delicias</p>
            </div>
            <div class="body">
                <p class="greeting">
                    Hola <strong>{docente}</strong>,<br><br>
                    Se ha registrado un nuevo agendamiento para el proceso de
                    <strong>Matricula Academica 2026 - 2027</strong>. A continuacion, los detalles del estudiante y acudiente asignado a tu cargo:
                </p>

                <div class="detail-box">
                    <h2>Detalles de la Cita</h2>
                    <div class="detail-row">
                        <span class="detail-label">Dia:</span>
                        <span class="detail-value">{dia_cita}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Hora:</span>
                        <span class="detail-value">{hora_cita}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Estudiante:</span>
                        <span class="detail-value">{estudiante}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">{label_grado}:</span>
                        <span class="detail-value">{valor_grado}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Acudiente:</span>
                        <span class="detail-value">{acudiente}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Telefono de contacto:</span>
                        <span class="detail-value">{telefono}</span>
                    </div>
                </div>
            </div>
            <div class="footer">
                Comfandi &mdash; Las Delicias &mdash; 2026<br>
                Este es un mensaje automatico.
            </div>
        </div>
    </body>
    </html>
    """

    asunto = f"Nuevo Agendamiento: {estudiante} | {dia_cita} {hora_cita}"
    texto_plano = (
        f"Nuevo Agendamiento de Matricula - Comfandi Las Delicias\n\n"
        f"Dia: {dia_cita}\n"
        f"Hora: {hora_cita}\n"
        f"Estudiante: {estudiante}\n"
        f"{label_grado}: {valor_grado}\n"
        f"Acudiente: {acudiente}\n"
        f"Telefono: {telefono}\n"
    )

    return send_email_brevo(
        to=correo_docente,
        subject=asunto,
        html=cuerpo_html,
        text=texto_plano,
        sender_name="Sistema de Agendamientos"
    )


def enviar_correo_cancelacion(
    destinatario_padre: str,
    correo_docente: str,
    acudiente: str,
    estudiante: str,
    grado: str,
    grupo: str,
    docente: str,
    horario: str,
    telefono: str,
    area: str = ""
) -> bool:
    """
    Envía correos electrónicos de cancelación al acudiente y al docente.
    """
    horario = formatear_horario_completo_string(horario)
    label_grado_grupo = "Grado" if area else "Grado / Grupo"
    valor_grado_grupo = area if area else f"Grado {grado} (Grupo {grupo})"

    # Correo para el acudiente
    cuerpo_padre = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 0; }}
            .container {{ max-width: 580px; margin: 32px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
            .header {{ background-color: #be123c; padding: 28px 32px; text-align: center; }}
            .header h1 {{ color: #ffffff; margin: 0; font-size: 20px; font-weight: 700; }}
            .header p {{ color: #ffe4e6; margin: 6px 0 0; font-size: 13px; }}
            .body {{ padding: 28px 32px; }}
            .greeting {{ font-size: 15px; color: #334155; margin-bottom: 16px; line-height: 1.6; }}
            .detail-box {{ background-color: #fff1f2; border-left: 4px solid #be123c; border-radius: 8px; padding: 20px 24px; margin: 20px 0; }}
            .detail-box h2 {{ color: #be123c; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 14px; }}
            .detail-row {{ display: flex; justify-content: space-between; font-size: 14px; padding: 6px 0; border-bottom: 1px solid #ffe4e6; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .detail-label {{ color: #64748b; font-weight: 600; }}
            .detail-value {{ color: #1e293b; font-weight: 500; text-align: right; }}
            .footer {{ background-color: #be123c; padding: 16px 32px; text-align: center; font-size: 12px; color: #ffe4e6; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Cancelacion de Agendamiento de Matricula</h1>
                <p>Sistema de Agendamiento Academico - Comfandi Las Delicias</p>
            </div>
            <div class="body">
                <p class="greeting">
                    Estimado/a <strong>{acudiente}</strong>,<br><br>
                    Le informamos que el agendamiento de cita para el proceso de
                    <strong>Matricula Academica 2026 - 2027</strong> ha sido <strong>cancelado</strong>.
                    El horario previamente seleccionado ha quedado libre. A continuacion, los detalles del agendamiento cancelado:
                </p>

                <div class="detail-box">
                    <h2>Detalles de la Cita Cancelada</h2>
                    <div class="detail-row">
                        <span class="detail-label">Estudiante:</span>
                        <span class="detail-value">{estudiante}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">{label_grado_grupo}:</span>
                        <span class="detail-value">{valor_grado_grupo}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Docente encargado:</span>
                        <span class="detail-value">{docente}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Horario:</span>
                        <span class="detail-value">{horario}</span>
                    </div>
                </div>
            </div>
            <div class="footer">
                Comfandi &mdash; Las Delicias &mdash; 2026<br>
                Este es un mensaje automatico.
            </div>
        </div>
    </body>
    </html>
    """

    # Correo para el docente
    cuerpo_docente = None
    if correo_docente:
        cuerpo_docente = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 0; }}
                .container {{ max-width: 580px; margin: 32px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
                .header {{ background-color: #be123c; padding: 28px 32px; text-align: center; }}
                .header h1 {{ color: #ffffff; margin: 0; font-size: 20px; font-weight: 700; }}
                .header p {{ color: #ffe4e6; margin: 6px 0 0; font-size: 13px; }}
                .body {{ padding: 28px 32px; }}
                .greeting {{ font-size: 15px; color: #334155; margin-bottom: 16px; line-height: 1.6; }}
                .detail-box {{ background-color: #fff1f2; border-left: 4px solid #be123c; border-radius: 8px; padding: 20px 24px; margin: 20px 0; }}
                .detail-box h2 {{ color: #be123c; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 14px; }}
                .detail-row {{ display: flex; justify-content: space-between; font-size: 14px; padding: 6px 0; border-bottom: 1px solid #ffe4e6; }}
                .detail-row:last-child {{ border-bottom: none; }}
                .detail-label {{ color: #64748b; font-weight: 600; }}
                .detail-value {{ color: #1e293b; font-weight: 500; text-align: right; }}
                .footer {{ background-color: #be123c; padding: 16px 32px; text-align: center; font-size: 12px; color: #ffe4e6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Cita Cancelada</h1>
                    <p>Sistema de Agendamiento Academico - Comfandi Las Delicias</p>
                </div>
                <div class="body">
                    <p class="greeting">
                        Hola <strong>{docente}</strong>,<br><br>
                        Se ha cancelado la cita programada con el acudiente del estudiante <strong>{estudiante}</strong>.
                        El horario ha quedado liberado.
                    </p>

                    <div class="detail-box">
                        <h2>Detalles de la Cita Cancelada</h2>
                        <div class="detail-row">
                            <span class="detail-label">Estudiante:</span>
                            <span class="detail-value">{estudiante}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Acudiente:</span>
                            <span class="detail-value">{acudiente}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Horario:</span>
                            <span class="detail-value">{horario}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Telefono:</span>
                            <span class="detail-value">{telefono}</span>
                        </div>
                    </div>
                </div>
                <div class="footer">
                    Comfandi &mdash; Las Delicias &mdash; 2026<br>
                    Este es un mensaje automatico.
                </div>
            </div>
        </body>
        </html>
        """

    import time
    max_intentos = 3
    res_padre = False

    asunto_padre = f"Cancelacion de Cita - {estudiante} | Comfandi Las Delicias 2026"
    texto_padre = (
        f"Cancelacion de Agendamiento de Matricula - Comfandi Las Delicias\n\n"
        f"Estimado/a {acudiente},\n\n"
        f"Le informamos que el agendamiento de cita para el proceso de "
        f"Matricula Academica 2026 - 2027 ha sido cancelado.\n"
        f"El horario previamente seleccionado ha quedado libre.\n\n"
        f"Detalles de la Cita Cancelada:\n"
        f"- Estudiante: {estudiante}\n"
        f"- {label_grado_grupo}: {valor_grado_grupo}\n"
        f"- Docente encargado: {docente}\n"
        f"- Horario: {horario}\n"
    )

    for intento in range(1, max_intentos + 1):
        if send_email_brevo(
            to=destinatario_padre,
            subject=asunto_padre,
            html=cuerpo_padre,
            text=texto_padre,
            sender_name="Comfandi Las Delicias"
        ):
            print(f"[Correo] Notificacion de cancelacion enviada a acudiente: {destinatario_padre}")
            res_padre = True
            break
        else:
            print(f"[Correo] Intento {intento} fallido al enviar cancelacion a acudiente")
            if intento < max_intentos:
                time.sleep(2)

    res_docente = True
    if correo_docente and cuerpo_docente:
        res_docente = False
        asunto_docente = f"Cancelacion de Cita: {estudiante} | {horario}"
        texto_docente = (
            f"Cita Cancelada - Sistema de Agendamiento Academico - Comfandi Las Delicias\n\n"
            f"Hola {docente},\n\n"
            f"Se ha cancelado la cita programada con el acudiente del estudiante {estudiante}.\n"
            f"El horario ha quedado liberado.\n\n"
            f"Detalles de la Cita Cancelada:\n"
            f"- Estudiante: {estudiante}\n"
            f"- Acudiente: {acudiente}\n"
            f"- Horario: {horario}\n"
            f"- Telefono: {telefono}\n"
        )
        for intento in range(1, max_intentos + 1):
            if send_email_brevo(
                to=correo_docente,
                subject=asunto_docente,
                html=cuerpo_docente,
                text=texto_docente,
                sender_name="Sistema de Agendamientos"
            ):
                print(f"[Correo] Notificacion de cancelacion enviada a docente: {correo_docente}")
                res_docente = True
                break
            else:
                print(f"[Correo] Intento {intento} fallido al enviar cancelacion a docente")
                if intento < max_intentos:
                    time.sleep(2)

    return res_padre and res_docente


def enviar_correo_reprogramacion(
    destinatario_padre: str,
    correo_docente_antiguo: str,
    correo_docente_nuevo: str,
    acudiente: str,
    estudiante: str,
    telefono: str,
    docente_antiguo: str,
    docente_nuevo: str,
    grado_antiguo: str,
    grado_nuevo: str,
    grupo_antiguo: str,
    grupo_nuevo: str,
    horario_antiguo: str,
    horario_nuevo: str,
    area_antigua: str = "",
    area_nueva: str = ""
) -> bool:
    """
    Envía correos electrónicos de reprogramación al acudiente y a los docentes correspondientes.
    """
    horario_antiguo = formatear_horario_completo_string(horario_antiguo)
    horario_nuevo = formatear_horario_completo_string(horario_nuevo)

    valor_grado_antiguo = area_antigua if area_antigua else f"Grado {grado_antiguo} (Grupo {grupo_antiguo})"
    valor_grado_nuevo = area_nueva if area_nueva else f"Grado {grado_nuevo} (Grupo {grupo_nuevo})"

    # Correo para el acudiente
    cuerpo_padre = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 0; }}
            .container {{ max-width: 580px; margin: 32px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
            .header {{ background-color: #d97706; padding: 28px 32px; text-align: center; }}
            .header h1 {{ color: #ffffff; margin: 0; font-size: 20px; font-weight: 700; }}
            .header p {{ color: #fef3c7; margin: 6px 0 0; font-size: 13px; }}
            .body {{ padding: 28px 32px; }}
            .greeting {{ font-size: 15px; color: #334155; margin-bottom: 16px; line-height: 1.6; }}
            .compare-box {{ display: flex; flex-direction: column; gap: 16px; margin: 20px 0; }}
            .detail-box {{ border-radius: 8px; padding: 18px 22px; }}
            .box-old {{ background-color: #fcf8f2; border-left: 4px solid #d97706; }}
            .box-new {{ background-color: #f0fdf4; border-left: 4px solid #16a34a; }}
            .detail-box h2 {{ font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 10px; }}
            .box-old h2 {{ color: #d97706; }}
            .box-new h2 {{ color: #16a34a; }}
            .detail-row {{ display: flex; justify-content: space-between; font-size: 13px; padding: 5px 0; border-bottom: 1px dashed #e2e8f0; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .detail-label {{ color: #64748b; font-weight: 600; }}
            .detail-value {{ color: #1e293b; font-weight: 500; text-align: right; }}
            .footer {{ background-color: #d97706; padding: 16px 32px; text-align: center; font-size: 12px; color: #fef3c7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Reprogramacion de Agendamiento de Matricula</h1>
                <p>Sistema de Agendamiento Academico - Comfandi Las Delicias</p>
            </div>
            <div class="body">
                <p class="greeting">
                    Estimado/a <strong>{acudiente}</strong>,<br><br>
                    Le confirmamos que su agendamiento de cita para el proceso de
                    <strong>Matricula Academica 2026 - 2027</strong> del estudiante <strong>{estudiante}</strong>
                    ha sido <strong>reprogramado</strong> exitosamente.
                </p>

                <div class="compare-box">
                    <div class="detail-box box-old">
                        <h2>Información Anterior</h2>
                        <div class="detail-row">
                            <span class="detail-label">Docente:</span>
                            <span class="detail-value">{docente_antiguo} ({valor_grado_antiguo})</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Horario:</span>
                            <span class="detail-value">{horario_antiguo}</span>
                        </div>
                    </div>

                    <div class="detail-box box-new">
                        <h2>Nueva Información Asignada</h2>
                        <div class="detail-row">
                            <span class="detail-label">Docente:</span>
                            <span class="detail-value">{docente_nuevo} ({valor_grado_nuevo})</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Horario:</span>
                            <span class="detail-value">{horario_nuevo}</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="footer">
                Comfandi &mdash; Las Delicias &mdash; 2026<br>
                Este es un mensaje automatico.
            </div>
        </div>
    </body>
    </html>
    """

    # Correos para docentes
    emails_to_send = []

    # Si es el mismo docente y el mismo correo, enviamos un solo correo informando el cambio de horario
    if correo_docente_antiguo == correo_docente_nuevo and correo_docente_antiguo:
        cuerpo_doc = f"""
        <html>
        <body>
            <h3>Cita Reprogramada</h3>
            <p>Hola <strong>{docente_antiguo}</strong>,</p>
            <p>Le informamos que la cita del estudiante <strong>{estudiante}</strong> con acudiente <strong>{acudiente}</strong> ha sido reprogramada.</p>
            <p><strong>Horario anterior:</strong> {horario_antiguo}</p>
            <p><strong>Nuevo horario:</strong> {horario_nuevo}</p>
        </body>
        </html>
        """
        texto_doc = (
            f"Cita Reprogramada\n\n"
            f"Hola {docente_antiguo},\n\n"
            f"Le informamos que la cita del estudiante {estudiante} con acudiente {acudiente} ha sido reprogramada.\n"
            f"Horario anterior: {horario_antiguo}\n"
            f"Nuevo horario: {horario_nuevo}\n"
        )
        emails_to_send.append((correo_docente_antiguo, f"Reprogramacion de Cita: {estudiante} | {horario_nuevo}", cuerpo_doc, texto_doc, "Sistema de Agendamientos"))
    else:
        # Docentes diferentes. Notificar a docente antiguo que se canceló/movió, y a docente nuevo que se agendó.
        if correo_docente_antiguo:
            cuerpo_doc_ant = f"""
            <html>
            <body>
                <h3>Cita Cancelada / Reasignada</h3>
                <p>Hola <strong>{docente_antiguo}</strong>,</p>
                <p>La cita programada con el estudiante <strong>{estudiante}</strong> y acudiente <strong>{acudiente}</strong> para el horario <strong>{horario_antiguo}</strong> ha sido cancelada o reasignada a otro docente. Este horario ha quedado libre.</p>
            </body>
            </html>
            """
            texto_doc_ant = (
                f"Cita Cancelada / Reasignada\n\n"
                f"Hola {docente_antiguo},\n\n"
                f"La cita programada con el estudiante {estudiante} y acudiente {acudiente} para el horario {horario_antiguo} ha sido cancelada o reasignada a otro docente. Este horario ha quedado libre.\n"
            )
            emails_to_send.append((correo_docente_antiguo, f"Cancelacion de Cita (Movida): {estudiante} | {horario_antiguo}", cuerpo_doc_ant, texto_doc_ant, "Sistema de Agendamientos"))
        
        if correo_docente_nuevo:
            cuerpo_doc_nue = f"""
            <html>
            <body>
                <h3>Nueva Cita Asignada</h3>
                <p>Hola <strong>{docente_nuevo}</strong>,</p>
                <p>Se le ha asignado una nueva cita debido a la reprogramacion del estudiante <strong>{estudiante}</strong> con acudiente <strong>{acudiente}</strong> (Telefono: {telefono}).</p>
                <p><strong>Horario:</strong> {horario_nuevo}</p>
                <p><strong>Grado:</strong> {valor_grado_nuevo}</p>
            </body>
            </html>
            """
            texto_doc_nue = (
                f"Nueva Cita Asignada\n\n"
                f"Hola {docente_nuevo},\n\n"
                f"Se le ha asignado una nueva cita debido a la reprogramacion del estudiante {estudiante} con acudiente {acudiente} (Telefono: {telefono}).\n"
                f"Horario: {horario_nuevo}\n"
                f"Grado: {valor_grado_nuevo}\n"
            )
            emails_to_send.append((correo_docente_nuevo, f"Nueva Cita Agendada (Reprogramacion): {estudiante} | {horario_nuevo}", cuerpo_doc_nue, texto_doc_nue, "Sistema de Agendamientos"))

    import time
    max_intentos = 3
    res_padre = False

    asunto_padre = f"Reprogramacion de Cita - {estudiante} | Comfandi Las Delicias 2026"
    texto_padre = (
        f"Reprogramacion de Agendamiento de Cita - Comfandi Las Delicias 2026\n\n"
        f"Estimado/a {acudiente},\n\n"
        f"Le confirmamos que su agendamiento de cita para el proceso de "
        f"Matricula Academica 2026 - 2027 del estudiante {estudiante} "
        f"ha sido reprogramado exitosamente.\n\n"
        f"Información Anterior:\n"
        f"- Docente: {docente_antiguo} ({valor_grado_antiguo})\n"
        f"- Horario: {horario_antiguo}\n\n"
        f"Nueva Información Asignada:\n"
        f"- Docente: {docente_nuevo} ({valor_grado_nuevo})\n"
        f"- Horario: {horario_nuevo}\n"
    )

    # 1. Enviar a padre
    for intento in range(1, max_intentos + 1):
        if send_email_brevo(
            to=destinatario_padre,
            subject=asunto_padre,
            html=cuerpo_padre,
            text=texto_padre,
            sender_name="Comfandi Las Delicias"
        ):
            print(f"[Correo] Notificacion de reprogramacion enviada a acudiente: {destinatario_padre}")
            res_padre = True
            break
        else:
            print(f"[Correo] Intento {intento} fallido al enviar reprogramacion a acudiente")
            if intento < max_intentos:
                time.sleep(2)

    # 2. Enviar a docentes
    res_docentes = True
    for dest_email, sub, html_c, text_c, s_name in emails_to_send:
        sent_ok = False
        for intento in range(1, max_intentos + 1):
            if send_email_brevo(
                to=dest_email,
                subject=sub,
                html=html_c,
                text=text_c,
                sender_name=s_name
            ):
                print(f"[Correo] Notificacion de reprogramacion enviada a docente: {dest_email}")
                sent_ok = True
                break
            else:
                print(f"[Correo] Intento {intento} fallido al enviar reprogramacion a docente: {dest_email}")
                if intento < max_intentos:
                    time.sleep(2)
        if not sent_ok:
            res_docentes = False

    return res_padre and res_docentes


def enviar_correos_nuevo_agendamiento(
    correo_padre: str,
    correo_docente: str,
    acudiente: str,
    estudiante: str,
    grado: str,
    grupo: str,
    docente: str,
    horario: str,
    telefono: str,
    area: str = ""
) -> bool:
    """
    Envía la confirmación al acudiente y la notificación al docente en una única sesión SMTP
    para evitar colisiones de conexión/login con Office 365.
    """
    

    import time
    max_intentos = 3
    for intento in range(1, max_intentos + 1):
        try:
            # Enviar al acudiente
            res_confirmacion = enviar_correo_confirmacion(
                destinatario=correo_padre,
                acudiente=acudiente,
                estudiante=estudiante,
                grado=grado,
                grupo=grupo,
                docente=docente,
                horario=horario,
                telefono=telefono,
                area=area
            )
            
            # Enviar al docente si tiene correo
            res_docente = True
            if correo_docente:
                res_docente = enviar_correo_docente(
                    correo_docente=correo_docente,
                    docente=docente,
                    acudiente=acudiente,
                    estudiante=estudiante,
                    grado=grado,
                    grupo=grupo,
                    horario=horario,
                    telefono=telefono,
                    area=area
                )
            
            if res_confirmacion and res_docente:
                return True
            else:
                raise Exception("Fallo al enviar alguno de los correos (confirmacion o docente)")
        except Exception as e:
            print(f"[Correo] Intento {intento} fallido en envio Brevo API combinado: {e}")
            if intento < max_intentos:
                time.sleep(2)
    return False

