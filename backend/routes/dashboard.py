"""
Rutas del dashboard y casos activos para AlertaEC
"""
from fastapi import APIRouter
from routes.webhook import casos_activos

router = APIRouter()

@router.get("/stats")
async def estadisticas_dashboard():
    """Estadísticas generales para el panel de control."""
    total = len(casos_activos)
    if total == 0:
        return {"total_casos": 0, "confirmados": 0, "en_revision": 0, "alertas_criticas": 0, "sin_cobertura": 0}

    estados = [c["estado_cobertura"] for c in casos_activos.values()]
    return {
        "total_casos": total,
        "confirmados": estados.count("CONFIRMADA"),
        "en_revision": estados.count("EN_REVISION"),
        "alertas_criticas": estados.count("ALERTA_CRITICA"),
        "sin_cobertura": estados.count("SIN_COBERTURA"),
        "casos_soat": sum(1 for c in casos_activos.values() if c.get("verifica_soat")),
    }
