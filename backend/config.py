"""
Configuración central del sistema AlertaEC
Variables de entorno y constantes del dominio ecuatoriano
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Anthropic ────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# ── Notion ───────────────────────────────────────────────────────────────────
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_POLIZAS_DB = os.getenv("NOTION_POLIZAS_DB", "")        # DB de pólizas
NOTION_CASOS_DB = os.getenv("NOTION_CASOS_DB", "")            # DB de casos activos
NOTION_PREEXISTENCIAS_DB = os.getenv("NOTION_PREEXISTENCIAS_DB", "")

# ── Notificaciones ───────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_FROM = os.getenv("TWILIO_PHONE_FROM", "")         # Número Twilio
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "alertas@alertaec.com")

# ── Sistema ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# ── Umbrales de decisión ─────────────────────────────────────────────────────
SCORE_AUTO_APROBAR = 30         # Score <= 30: cobertura confirmada automáticamente
SCORE_REVISION_HUMANA = 70      # Score 31-70: requiere revisión del gestor
SCORE_ALERTA_CRITICA = 71       # Score >= 71: alerta crítica, posible exclusión

# ── Constantes Ecuador ───────────────────────────────────────────────────────
COBERTURA_SOAT_ACCIDENTE = True  # Verificar SOAT en accidentes de tránsito
MONEDA = "USD"                   # Ecuador usa dólares
ZONA_HORARIA = "America/Guayaquil"

# ── Tipos de emergencia (CIE-10 grupos frecuentes Ecuador) ───────────────────
TIPOS_EMERGENCIA = {
    "TRAUMA": "Traumatismos y lesiones (S00-T98)",
    "CARDIOVASCULAR": "Enfermedades cardiovasculares (I00-I99)",
    "RESPIRATORIO": "Enfermedades respiratorias (J00-J99)",
    "DIGESTIVO": "Enfermedades digestivas (K00-K93)",
    "NEUROLOGICO": "Enfermedades neurológicas (G00-G99)",
    "OBSTETRICO": "Complicaciones obstétricas (O00-O99)",
    "PEDIATRICO": "Condiciones pediátricas",
    "OTRO": "Otra causa de emergencia",
}

# ── Hospitales de la red (demo) ──────────────────────────────────────────────
HOSPITALES_RED = [
    {"id": "H001", "nombre": "Clínica Kennedy - Guayaquil", "ciudad": "Guayaquil"},
    {"id": "H002", "nombre": "Hospital Metropolitano - Quito", "ciudad": "Quito"},
    {"id": "H003", "nombre": "Clínica Pichincha - Quito", "ciudad": "Quito"},
    {"id": "H004", "nombre": "Hospital Voz Andes - Quito", "ciudad": "Quito"},
    {"id": "H005", "nombre": "Clínica Santa Inés - Cuenca", "ciudad": "Cuenca"},
]
