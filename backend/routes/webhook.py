"""
Ruta principal del webhook de admisión de emergencias
POST /api/webhook/admision
Este es el corazón del sistema AlertaEC
"""

import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.schemas import AdmisionEmergencia, AlertaEmergenciaResponse, EstadoCobertura
from services.notion_service import obtener_poliza, obtener_preexistencias, crear_caso_notion
from services.notification_service import enviar_alertas
from agents.emergencia_agent import analizar_emergencia

router = APIRouter()

# Almacenamiento en memoria para demo (en producción: Redis o DB)
casos_activos: dict = {}


def _validar_cedula_ecuatoriana(cedula: str) -> bool:
    """
    Valida una cédula de identidad ecuatoriana usando el algoritmo oficial.
    Los primeros 2 dígitos representan la provincia (01-24) o 30 (IESS).
    """
    if len(cedula) != 10 or not cedula.isdigit():
        return False
    provincia = int(cedula[:2])
    if not (1 <= provincia <= 24 or provincia == 30):
        return False
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for i, coef in enumerate(coeficientes):
        valor = int(cedula[i]) * coef
        if valor >= 10:
            valor -= 9
        total += valor
    digito_verificador = int(cedula[9])
    residuo = total % 10
    return (residuo == 0 and digito_verificador == 0) or (10 - residuo == digito_verificador)


@router.post("/admision", response_model=AlertaEmergenciaResponse, status_code=200)
async def admision_emergencia(admision: AdmisionEmergencia):
    """
    Webhook principal: recibe el ingreso de un paciente a urgencias.
    
    Proceso completo en < 5 segundos:
    1. Valida cédula ecuatoriana
    2. Consulta póliza en Notion
    3. Consulta pre-existencias en Notion  
    4. Invoca agente Claude para análisis
    5. Crea caso en Notion
    6. Envía notificaciones simultáneas (hospital + aseguradora)
    7. Retorna respuesta estructurada
    """
    # ── 1. Validación de cédula ──────────────────────────────────────────────
    if not _validar_cedula_ecuatoriana(admision.cedula_paciente):
        raise HTTPException(
            status_code=400,
            detail=f"Cédula ecuatoriana inválida: {admision.cedula_paciente}. "
                   "Debe tener 10 dígitos y pasar el algoritmo de verificación.",
        )

    # ── 2. Consultas paralelas a Notion ──────────────────────────────────────
    poliza, preexistencias = await asyncio.gather(
        obtener_poliza(admision.cedula_paciente),
        obtener_preexistencias(admision.cedula_paciente),
    )

    if poliza is None:
        # Paciente sin póliza registrada
        caso_id = f"EC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        return AlertaEmergenciaResponse(
            caso_id=caso_id,
            timestamp=datetime.now(),
            paciente=admision.nombre_paciente,
            cedula=admision.cedula_paciente,
            hospital=admision.hospital_id,
            estado_cobertura=EstadoCobertura.SIN_COBERTURA,
            score_cobertura=95,
            nivel_urgencia=_evaluar_urgencia_tipo(admision.tipo_emergencia.value),
            resumen=(
                f"Paciente {admision.nombre_paciente} no tiene póliza registrada en el sistema. "
                "Proceder con atención urgente según protocolo de pacientes sin seguro. "
                "Evaluar alternativas: IESS, MSP, pago particular."
            ),
            alertas=[
                "SIN PÓLIZA REGISTRADA en el sistema",
                "Verificar si el paciente tiene seguro IESS",
                "Consultar si aplica cobertura MSP",
            ],
            limite_disponible=0.0,
            notificaciones_enviadas=[],
        )

    # ── 3. Análisis con agente IA ────────────────────────────────────────────
    analisis = await analizar_emergencia(admision, poliza, preexistencias)

    # ── 4. Generar ID único del caso ─────────────────────────────────────────
    caso_id = f"EC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    # ── 5. Crear registro en Notion + Enviar notificaciones (paralelo) ───────
    notion_url, notificaciones = await asyncio.gather(
        crear_caso_notion(
            caso_id=caso_id,
            cedula=admision.cedula_paciente,
            nombre=admision.nombre_paciente,
            hospital_id=admision.hospital_id,
            estado=analisis.estado_cobertura.value,
            score=analisis.score_cobertura,
            resumen=analisis.resumen_ejecutivo,
        ),
        enviar_alertas(admision, poliza, analisis, caso_id, "pendiente"),
    )

    notion_url = notion_url or f"https://notion.so/caso/{caso_id}"

    # ── 6. Guardar en memoria para dashboard ─────────────────────────────────
    casos_activos[caso_id] = {
        "caso_id": caso_id,
        "timestamp": datetime.now().isoformat(),
        "paciente": admision.nombre_paciente,
        "cedula": admision.cedula_paciente,
        "hospital": admision.hospital_id,
        "tipo_emergencia": admision.tipo_emergencia.value,
        "motivo": admision.motivo_emergencia,
        "estado_cobertura": analisis.estado_cobertura.value,
        "score_cobertura": analisis.score_cobertura,
        "nivel_urgencia": analisis.nivel_urgencia.value,
        "aseguradora": poliza.aseguradora,
        "poliza": poliza.numero_poliza,
        "disponible": analisis.limite_disponible_estimado,
        "gestor": poliza.gestor_casos_nombre,
        "alertas": analisis.alertas,
        "verifica_soat": analisis.verifica_soat,
        "notion_url": notion_url,
        "activo": True,
    }

    notifs_enviadas = [
        f"{n.canal.upper()} → {n.destinatario}: {'✓' if n.enviado else '✗'}"
        for n in notificaciones
    ]

    return AlertaEmergenciaResponse(
        caso_id=caso_id,
        timestamp=datetime.now(),
        paciente=admision.nombre_paciente,
        cedula=admision.cedula_paciente,
        hospital=admision.hospital_id,
        estado_cobertura=analisis.estado_cobertura,
        score_cobertura=analisis.score_cobertura,
        nivel_urgencia=analisis.nivel_urgencia,
        resumen=analisis.resumen_ejecutivo,
        alertas=analisis.alertas,
        limite_disponible=analisis.limite_disponible_estimado,
        notificaciones_enviadas=notifs_enviadas,
        notion_caso_url=notion_url,
    )


@router.get("/casos")
async def listar_casos_activos():
    """Retorna todos los casos activos registrados en la sesión actual."""
    return {
        "total": len(casos_activos),
        "casos": list(casos_activos.values()),
    }


@router.get("/casos/{caso_id}")
async def obtener_caso(caso_id: str):
    """Retorna el detalle de un caso específico."""
    caso = casos_activos.get(caso_id)
    if not caso:
        raise HTTPException(status_code=404, detail=f"Caso {caso_id} no encontrado")
    return caso


def _evaluar_urgencia_tipo(tipo: str) -> str:
    urgencia_map = {
        "TRAUMA": "CRITICA",
        "CARDIOVASCULAR": "CRITICA",
        "NEUROLOGICO": "CRITICA",
        "OBSTETRICO": "ALTA",
        "RESPIRATORIO": "ALTA",
        "DIGESTIVO": "MEDIA",
        "PEDIATRICO": "ALTA",
        "OTRO": "MEDIA",
    }
    return urgencia_map.get(tipo, "ALTA")
