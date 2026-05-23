"""
Modelos de dominio para AlertaEC
Reto 4 - Sistema de Alerta Temprana de Emergencias
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TipoEmergencia(str, Enum):
    TRAUMA = "TRAUMA"
    CARDIOVASCULAR = "CARDIOVASCULAR"
    RESPIRATORIO = "RESPIRATORIO"
    DIGESTIVO = "DIGESTIVO"
    NEUROLOGICO = "NEUROLOGICO"
    OBSTETRICO = "OBSTETRICO"
    PEDIATRICO = "PEDIATRICO"
    OTRO = "OTRO"


class EstadoCobertura(str, Enum):
    CONFIRMADA = "CONFIRMADA"
    EN_REVISION = "EN_REVISION"
    ALERTA_CRITICA = "ALERTA_CRITICA"
    SIN_COBERTURA = "SIN_COBERTURA"


class NivelUrgencia(str, Enum):
    CRITICA = "CRITICA"       # Riesgo de vida inmediato
    ALTA = "ALTA"             # Atención en < 1 hora
    MEDIA = "MEDIA"           # Atención en < 4 horas
    BAJA = "BAJA"             # Puede esperar turno


# ── Request: lo que envía el hospital al webhook ─────────────────────────────
class AdmisionEmergencia(BaseModel):
    cedula_paciente: str = Field(..., description="Cédula de identidad ecuatoriana (10 dígitos)", example="1723456789")
    nombre_paciente: str = Field(..., description="Nombre completo del paciente")
    hospital_id: str = Field(..., description="ID del hospital que reporta", example="H001")
    motivo_emergencia: str = Field(..., description="Descripción del motivo de ingreso en lenguaje natural")
    tipo_emergencia: TipoEmergencia = Field(default=TipoEmergencia.OTRO)
    codigo_cie10: Optional[str] = Field(None, description="Código CIE-10 si ya fue clasificado", example="S06.0")
    es_accidente_transito: bool = Field(default=False, description="¿Es accidente de tránsito? Activa verificación SOAT")
    medico_admision: str = Field(..., description="Nombre del médico de admisión")
    email_medico: Optional[str] = Field(None)
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)


# ── Datos recuperados de Notion ──────────────────────────────────────────────
class DatosPoliza(BaseModel):
    numero_poliza: str
    aseguradora: str
    plan: str
    vigente: bool
    fecha_inicio: str
    fecha_fin: str
    limite_anual: float
    consumido_anual: float
    disponible: float
    cubre_emergencias: bool
    periodo_carencia_dias: int
    dias_carencia_cumplidos: bool
    deducible: float
    porcentaje_coaseguro: float          # % que paga el asegurado
    gestor_casos_nombre: str
    gestor_casos_email: str
    gestor_casos_telefono: str
    email_aseguradora: str


class PreExistencia(BaseModel):
    condicion: str
    codigo_cie10: Optional[str]
    declarada: bool
    fecha_diagnostico: Optional[str]
    excluida_de_cobertura: bool


# ── Análisis generado por el agente Claude ───────────────────────────────────
class AnalisisAgente(BaseModel):
    score_cobertura: int = Field(..., ge=0, le=100, description="0=sin riesgo, 100=exclusión total")
    estado_cobertura: EstadoCobertura
    nivel_urgencia: NivelUrgencia
    resumen_ejecutivo: str
    verifica_soat: bool
    posible_preexistencia: bool
    alertas: List[str] = []
    recomendaciones_hospital: List[str] = []
    recomendaciones_aseguradora: List[str] = []
    limite_disponible_estimado: float
    costo_estimado_emergencia: Optional[float] = None
    documentos_requeridos: List[str] = []


# ── Respuesta completa del webhook ───────────────────────────────────────────
class AlertaEmergenciaResponse(BaseModel):
    caso_id: str
    timestamp: datetime
    paciente: str
    cedula: str
    hospital: str
    estado_cobertura: EstadoCobertura
    score_cobertura: int
    nivel_urgencia: NivelUrgencia
    resumen: str
    alertas: List[str]
    limite_disponible: float
    notificaciones_enviadas: List[str]
    notion_caso_url: Optional[str] = None


# ── Evento de notificación ───────────────────────────────────────────────────
class NotificacionEvento(BaseModel):
    destinatario: str
    canal: str                           # "email" | "sms"
    asunto: Optional[str] = None
    cuerpo: str
    enviado: bool = False
    error: Optional[str] = None
