"""
Agente IA - AlertaEC
Usa Claude Sonnet para analizar cobertura de emergencias en tiempo real
Contexto: Sistema asegurador ecuatoriano (LOPDP, SOAT, CIE-10)
"""

import anthropic
import json
from models.schemas import (
    AdmisionEmergencia, DatosPoliza, PreExistencia,
    AnalisisAgente, EstadoCobertura, NivelUrgencia
)
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SCORE_AUTO_APROBAR, SCORE_REVISION_HUMANA

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


SYSTEM_PROMPT = """Eres un agente especializado en análisis de cobertura de seguros médicos en Ecuador.
Tu función es analizar en tiempo real si un paciente que ingresa a urgencias tiene cobertura válida
y qué acciones deben tomar el hospital y la aseguradora.

CONTEXTO REGULATORIO ECUADOR:
- Las pólizas en Ecuador se rigen por la Ley General de Seguros y la regulación de la SBS
- El SOAT (Seguro Obligatorio de Accidentes de Tránsito) es gestionado por la ANT y cubre hasta $5,000
- En accidentes de tránsito, el SOAT se activa PRIMERO antes del seguro privado
- La moneda es USD (dólar americano)
- Los códigos diagnósticos siguen el sistema CIE-10 en español

REGLAS DE DECISIÓN:
- Score 0-30: Cobertura CONFIRMADA → hospital puede proceder con atención completa
- Score 31-70: EN REVISIÓN → hospital procede con atención básica urgente, gestor revisa en <1 hora
- Score 71-100: ALERTA CRÍTICA → posible exclusión, atención urgente garantizada, revisión inmediata

IMPORTANTE: 
- SIEMPRE garantizar la atención médica urgente. La cobertura se resuelve post-atención si es necesario.
- Analiza si hay posible relación entre el motivo de emergencia y pre-existencias declaradas
- En caso de accidente de tránsito, SIEMPRE recomendar activar SOAT primero
- Responde ÚNICAMENTE con el JSON estructurado solicitado, sin texto adicional"""


async def analizar_emergencia(
    admision: AdmisionEmergencia,
    poliza: DatosPoliza,
    preexistencias: list[PreExistencia],
) -> AnalisisAgente:
    """
    Invoca al agente Claude para analizar la cobertura de la emergencia.
    Retorna un análisis estructurado con score, estado y recomendaciones.
    """

    preex_texto = ""
    if preexistencias:
        preex_texto = "\n".join(
            f"- {p.condicion} (CIE-10: {p.codigo_cie10 or 'N/D'}) | "
            f"Declarada: {'Sí' if p.declarada else 'NO'} | "
            f"Excluida cobertura: {'SÍ' if p.excluida_de_cobertura else 'No'}"
            for p in preexistencias
        )
    else:
        preex_texto = "Sin pre-existencias registradas"

    porcentaje_consumido = 0
    if poliza.limite_anual > 0:
        porcentaje_consumido = round((poliza.consumido_anual / poliza.limite_anual) * 100, 1)

    prompt_usuario = f"""
INGRESO DE EMERGENCIA - ANALIZAR COBERTURA

=== DATOS DEL PACIENTE ===
Nombre: {admision.nombre_paciente}
Cédula: {admision.cedula_paciente}
Hospital: {admision.hospital_id}
Médico de admisión: {admision.medico_admision}

=== MOTIVO DE INGRESO ===
Tipo de emergencia: {admision.tipo_emergencia.value}
Descripción: {admision.motivo_emergencia}
Código CIE-10 (si disponible): {admision.codigo_cie10 or 'No clasificado aún'}
¿Accidente de tránsito?: {'SÍ → verificar SOAT ANT Ecuador' if admision.es_accidente_transito else 'No'}

=== DATOS DE LA PÓLIZA ===
Número: {poliza.numero_poliza}
Aseguradora: {poliza.aseguradora}
Plan: {poliza.plan}
Estado: {'VIGENTE ✓' if poliza.vigente else 'VENCIDA ✗'}
Vigencia: {poliza.fecha_inicio} → {poliza.fecha_fin}
Cubre emergencias: {'Sí' if poliza.cubre_emergencias else 'No'}
Período de carencia: {poliza.periodo_carencia_dias} días ({'Cumplido ✓' if poliza.dias_carencia_cumplidos else 'NO CUMPLIDO ✗'})
Límite anual: ${poliza.limite_anual:,.2f}
Consumido: ${poliza.consumido_anual:,.2f} ({porcentaje_consumido}%)
Disponible: ${poliza.disponible:,.2f}
Deducible: ${poliza.deducible:,.2f}
Coaseguro paciente: {poliza.porcentaje_coaseguro}%

=== PRE-EXISTENCIAS DECLARADAS ===
{preex_texto}

=== GESTOR DE CASOS ===
Nombre: {poliza.gestor_casos_nombre}
Contacto: {poliza.gestor_casos_telefono} | {poliza.gestor_casos_email}

INSTRUCCIONES:
Analiza este caso y responde ÚNICAMENTE con el siguiente JSON (sin markdown, sin texto extra):

{{
  "score_cobertura": <número 0-100>,
  "estado_cobertura": "<CONFIRMADA|EN_REVISION|ALERTA_CRITICA|SIN_COBERTURA>",
  "nivel_urgencia": "<CRITICA|ALTA|MEDIA|BAJA>",
  "resumen_ejecutivo": "<párrafo de 2-3 oraciones con el estado del caso para el personal de admisiones>",
  "verifica_soat": <true|false>,
  "posible_preexistencia": <true|false>,
  "alertas": ["<alerta1>", "<alerta2>"],
  "recomendaciones_hospital": ["<rec1>", "<rec2>"],
  "recomendaciones_aseguradora": ["<rec1>", "<rec2>"],
  "limite_disponible_estimado": <número en USD>,
  "costo_estimado_emergencia": <número en USD o null>,
  "documentos_requeridos": ["<doc1>", "<doc2>"]
}}
"""

    try:
        respuesta = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt_usuario}],
        )

        texto = respuesta.content[0].text.strip()
        # Limpiar posibles backticks de markdown
        texto = texto.replace("```json", "").replace("```", "").strip()
        datos = json.loads(texto)

        return AnalisisAgente(
            score_cobertura=datos["score_cobertura"],
            estado_cobertura=EstadoCobertura(datos["estado_cobertura"]),
            nivel_urgencia=NivelUrgencia(datos["nivel_urgencia"]),
            resumen_ejecutivo=datos["resumen_ejecutivo"],
            verifica_soat=datos.get("verifica_soat", False),
            posible_preexistencia=datos.get("posible_preexistencia", False),
            alertas=datos.get("alertas", []),
            recomendaciones_hospital=datos.get("recomendaciones_hospital", []),
            recomendaciones_aseguradora=datos.get("recomendaciones_aseguradora", []),
            limite_disponible_estimado=datos.get("limite_disponible_estimado", poliza.disponible),
            costo_estimado_emergencia=datos.get("costo_estimado_emergencia"),
            documentos_requeridos=datos.get("documentos_requeridos", []),
        )

    except json.JSONDecodeError as e:
        print(f"[Agente] Error al parsear JSON de Claude: {e}")
        return _analisis_fallback(poliza, admision)

    except Exception as e:
        print(f"[Agente] Error en llamada a Claude: {e}")
        return _analisis_fallback(poliza, admision)


def _analisis_fallback(poliza: DatosPoliza, admision: AdmisionEmergencia) -> AnalisisAgente:
    """Análisis de respaldo cuando la IA no está disponible."""
    if not poliza.vigente:
        estado = EstadoCobertura.SIN_COBERTURA
        score = 90
    elif not poliza.cubre_emergencias:
        estado = EstadoCobertura.ALERTA_CRITICA
        score = 80
    elif not poliza.dias_carencia_cumplidos:
        estado = EstadoCobertura.EN_REVISION
        score = 55
    elif poliza.disponible < 500:
        estado = EstadoCobertura.EN_REVISION
        score = 60
    else:
        estado = EstadoCobertura.CONFIRMADA
        score = 15

    return AnalisisAgente(
        score_cobertura=score,
        estado_cobertura=estado,
        nivel_urgencia=NivelUrgencia.ALTA,
        resumen_ejecutivo=(
            f"Análisis automático (modo contingencia): Póliza {poliza.numero_poliza} "
            f"- {poliza.aseguradora}. Estado: {estado.value}. "
            "Se requiere validación manual del gestor de casos."
        ),
        verifica_soat=admision.es_accidente_transito,
        posible_preexistencia=False,
        alertas=["Análisis generado en modo contingencia - validar manualmente"],
        recomendaciones_hospital=["Proceder con atención urgente", "Contactar gestor de casos"],
        recomendaciones_aseguradora=["Revisar caso manualmente", "Contactar hospital en < 30 min"],
        limite_disponible_estimado=poliza.disponible,
        documentos_requeridos=["Informe médico de admisión", "Copia de cédula del paciente"],
    )
