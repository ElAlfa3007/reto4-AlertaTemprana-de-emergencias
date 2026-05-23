"""
Rutas de gestión de casos para AlertaEC
"""
from fastapi import APIRouter, HTTPException
from routes.webhook import casos_activos

router = APIRouter()

@router.get("/")
async def listar_casos():
    return {"total": len(casos_activos), "casos": list(casos_activos.values())}

@router.patch("/{caso_id}/cerrar")
async def cerrar_caso(caso_id: str):
    if caso_id not in casos_activos:
        raise HTTPException(status_code=404, detail=f"Caso {caso_id} no encontrado")
    casos_activos[caso_id]["activo"] = False
    return {"mensaje": f"Caso {caso_id} cerrado", "caso": casos_activos[caso_id]}
