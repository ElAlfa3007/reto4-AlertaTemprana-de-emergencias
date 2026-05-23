"""
Servicio de notificaciones multi-canal
SMS via Twilio + Email via SendGrid
Notificación simultánea: Hospital + Aseguradora
"""

import asyncio
from datetime import datetime
from typing import List
from models.schemas import (
    AdmisionEmergencia, DatosPoliza, AnalisisAgente,
    EstadoCobertura, NotificacionEvento
)
from config import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_FROM,
    SENDGRID_API_KEY, EMAIL_FROM, ENVIRONMENT
)

# ── Íconos de estado para notificaciones ─────────────────────────────────────
ICONOS_ESTADO = {
    EstadoCobertura.CONFIRMADA: "✅",
    EstadoCobertura.EN_REVISION: "⚠️",
    EstadoCobertura.ALERTA_CRITICA: "🚨",
    EstadoCobertura.SIN_COBERTURA: "❌",
}


async def enviar_alertas(
    admision: AdmisionEmergencia,
    poliza: DatosPoliza,
    analisis: AnalisisAgente,
    caso_id: str,
    notion_url: str,
) -> List[NotificacionEvento]:
    """
    Envía notificaciones simultáneas al hospital y a la aseguradora.
    Retorna lista de eventos de notificación con estado de envío.
    """
    tareas = [
        _notificar_hospital(admision, poliza, analisis, caso_id),
        _notificar_aseguradora(admision, poliza, analisis, caso_id, notion_url),
    ]
    resultados = await asyncio.gather(*tareas, return_exceptions=True)

    notificaciones = []
    for resultado in resultados:
        if isinstance(resultado, list):
            notificaciones.extend(resultado)
        elif isinstance(resultado, Exception):
            print(f"[Notificaciones] Error en tarea: {resultado}")

    return notificaciones


async def _notificar_hospital(
    admision: AdmisionEmergencia,
    poliza: DatosPoliza,
    analisis: AnalisisAgente,
    caso_id: str,
) -> List[NotificacionEvento]:
    """Notifica al médico de admisión del hospital."""
    icono = ICONOS_ESTADO.get(analisis.estado_cobertura, "ℹ️")
    alertas_txt = "\n".join(f"  • {a}" for a in analisis.alertas) if analisis.alertas else "  • Ninguna"
    recs_txt = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(analisis.recomendaciones_hospital))
    docs_txt = "\n".join(f"  • {d}" for d in analisis.documentos_requeridos) if analisis.documentos_requeridos else "  • Ninguno adicional"

    cuerpo_email = f"""
SISTEMA ALERTAEC — VALIDACIÓN DE COBERTURA EN TIEMPO REAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{icono} ESTADO DE COBERTURA: {analisis.estado_cobertura.value}
   Score de riesgo: {analisis.score_cobertura}/100
   Urgencia clínica: {analisis.nivel_urgencia.value}

📋 CASO ID: {caso_id}
   Paciente: {admision.nombre_paciente} | CI: {admision.cedula_paciente}
   Hora de ingreso: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

💊 RESUMEN DEL CASO:
{analisis.resumen_ejecutivo}

💰 COBERTURA FINANCIERA:
   Aseguradora: {poliza.aseguradora} — Póliza: {poliza.numero_poliza}
   Plan: {poliza.plan}
   Límite disponible: ${analisis.limite_disponible_estimado:,.2f} USD
   Deducible: ${poliza.deducible:,.2f} | Coaseguro paciente: {poliza.porcentaje_coaseguro}%
   {f'⚠️ Costo estimado de atención: ${analisis.costo_estimado_emergencia:,.2f}' if analisis.costo_estimado_emergencia else ''}

⚠️ ALERTAS:
{alertas_txt}

📌 RECOMENDACIONES PARA ADMISIONES:
{recs_txt}

📄 DOCUMENTOS REQUERIDOS:
{docs_txt}

{'🚗 SOAT: Este caso involucra accidente de tránsito. ACTIVAR SOAT ANT Ecuador ANTES del seguro privado.' if analisis.verifica_soat else ''}

👤 GESTOR DE CASOS (ASEGURADORA):
   {poliza.gestor_casos_nombre}
   📞 {poliza.gestor_casos_telefono}
   ✉️  {poliza.gestor_casos_email}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AlertaEC — Sistema de Alerta Temprana de Emergencias | hackIAthon Viamatica
Este mensaje fue generado automáticamente. No responder a este correo.
"""

    cuerpo_sms = (
        f"AlertaEC [{caso_id}] {icono} "
        f"{admision.nombre_paciente} | {poliza.aseguradora} "
        f"Cobertura: {analisis.estado_cobertura.value} "
        f"Disponible: ${analisis.limite_disponible_estimado:,.0f} "
        f"Gestor: {poliza.gestor_casos_telefono}"
    )

    notifs = []

    if admision.email_medico:
        notifs.append(await _enviar_email(
            destinatario=admision.email_medico,
            asunto=f"AlertaEC [{analisis.estado_cobertura.value}] {admision.nombre_paciente} — CI {admision.cedula_paciente}",
            cuerpo=cuerpo_email,
        ))

    return notifs


async def _notificar_aseguradora(
    admision: AdmisionEmergencia,
    poliza: DatosPoliza,
    analisis: AnalisisAgente,
    caso_id: str,
    notion_url: str,
) -> List[NotificacionEvento]:
    """Notifica al gestor de casos y al departamento de la aseguradora."""
    icono = ICONOS_ESTADO.get(analisis.estado_cobertura, "ℹ️")
    recs_txt = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(analisis.recomendaciones_aseguradora))
    preex_nota = "⚠️ POSIBLE RELACIÓN CON PRE-EXISTENCIA — Revisar urgentemente" if analisis.posible_preexistencia else "Sin relación aparente con pre-existencias"

    cuerpo_email = f"""
ALERTAEC — NUEVO INGRESO A EMERGENCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{icono} ESTADO: {analisis.estado_cobertura.value} | Score: {analisis.score_cobertura}/100

📋 CASO: {caso_id}
🔗 Ver en Notion: {notion_url}

PACIENTE:  {admision.nombre_paciente} | CI: {admision.cedula_paciente}
HOSPITAL:  {admision.hospital_id}
MÉDICO:    {admision.medico_admision}
INGRESO:   {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

MOTIVO DE EMERGENCIA:
{admision.motivo_emergencia}
Tipo: {admision.tipo_emergencia.value}
{f'CIE-10: {admision.codigo_cie10}' if admision.codigo_cie10 else ''}

ANÁLISIS IA:
{analisis.resumen_ejecutivo}

PRE-EXISTENCIAS: {preex_nota}

IMPACTO FINANCIERO:
  Póliza: {poliza.numero_poliza} — {poliza.plan}
  Consumido este año: ${poliza.consumido_anual:,.2f} / ${poliza.limite_anual:,.2f}
  Disponible: ${analisis.limite_disponible_estimado:,.2f}
  {f'Costo estimado: ${analisis.costo_estimado_emergencia:,.2f}' if analisis.costo_estimado_emergencia else ''}

{'🚗 SOAT ACTIVO: Caso de accidente de tránsito. Coordinar con ANT Ecuador para activación.' if analisis.verifica_soat else ''}

ACCIONES REQUERIDAS:
{recs_txt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AlertaEC | hackIAthon Viamatica Ecuador
"""

    notifs = []

    if poliza.gestor_casos_email:
        notifs.append(await _enviar_email(
            destinatario=poliza.gestor_casos_email,
            asunto=f"NUEVO CASO {icono} [{analisis.estado_cobertura.value}] {admision.nombre_paciente} — {poliza.numero_poliza}",
            cuerpo=cuerpo_email,
        ))

    if poliza.email_aseguradora and poliza.email_aseguradora != poliza.gestor_casos_email:
        notifs.append(await _enviar_email(
            destinatario=poliza.email_aseguradora,
            asunto=f"Alerta Emergencia [{caso_id}] — {admision.nombre_paciente}",
            cuerpo=cuerpo_email,
        ))

    if poliza.gestor_casos_telefono:
        sms_body = (
            f"AlertaEC [{caso_id}] {icono} {analisis.estado_cobertura.value}: "
            f"{admision.nombre_paciente} ingresó a {admision.hospital_id}. "
            f"Score: {analisis.score_cobertura}/100. "
            f"Disponible: ${analisis.limite_disponible_estimado:,.0f}. "
            f"Revisar Notion: {notion_url}"
        )
        notifs.append(await _enviar_sms(poliza.gestor_casos_telefono, sms_body))

    return notifs


async def _enviar_email(destinatario: str, asunto: str, cuerpo: str) -> NotificacionEvento:
    """Envía email via SendGrid. En modo dev, imprime en consola."""
    if ENVIRONMENT == "development" or not SENDGRID_API_KEY:
        print(f"\n{'='*60}")
        print(f"[EMAIL SIMULADO → {destinatario}]")
        print(f"Asunto: {asunto}")
        print(cuerpo[:500] + "..." if len(cuerpo) > 500 else cuerpo)
        print('='*60)
        return NotificacionEvento(
            destinatario=destinatario, canal="email",
            asunto=asunto, cuerpo=cuerpo, enviado=True,
        )

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content
        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        message = Mail(
            from_email=Email(EMAIL_FROM, "AlertaEC"),
            to_emails=To(destinatario),
            subject=asunto,
            plain_text_content=Content("text/plain", cuerpo),
        )
        response = sg.client.mail.send.post(request_body=message.get())
        enviado = response.status_code in (200, 202)
        return NotificacionEvento(
            destinatario=destinatario, canal="email",
            asunto=asunto, cuerpo=cuerpo, enviado=enviado,
        )
    except Exception as e:
        return NotificacionEvento(
            destinatario=destinatario, canal="email",
            asunto=asunto, cuerpo=cuerpo, enviado=False, error=str(e),
        )


async def _enviar_sms(telefono: str, mensaje: str) -> NotificacionEvento:
    """Envía SMS via Twilio. En modo dev, imprime en consola."""
    if ENVIRONMENT == "development" or not TWILIO_ACCOUNT_SID:
        print(f"\n[SMS SIMULADO → {telefono}]\n{mensaje}\n")
        return NotificacionEvento(
            destinatario=telefono, canal="sms", cuerpo=mensaje, enviado=True,
        )

    try:
        from twilio.rest import Client
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = twilio_client.messages.create(
            body=mensaje[:1600],
            from_=TWILIO_PHONE_FROM,
            to=telefono,
        )
        return NotificacionEvento(
            destinatario=telefono, canal="sms", cuerpo=mensaje,
            enviado=message.status in ("queued", "sending", "sent"),
        )
    except Exception as e:
        return NotificacionEvento(
            destinatario=telefono, canal="sms",
            cuerpo=mensaje, enviado=False, error=str(e),
        )
