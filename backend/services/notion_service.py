"""
Servicio de integración con Notion
Gestiona pólizas, casos activos y pre-existencias
"""

import httpx
import asyncio
from datetime import datetime
from typing import Optional
from models.schemas import DatosPoliza, PreExistencia
from config import NOTION_TOKEN, NOTION_POLIZAS_DB, NOTION_CASOS_DB, NOTION_PREEXISTENCIAS_DB

NOTION_BASE = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# ── Datos de demo para desarrollo sin Notion real ────────────────────────────
POLIZAS_DEMO = {
    "1723456784": DatosPoliza(
        numero_poliza="POL-2024-001",
        aseguradora="Aseguradora del Sur",
        plan="Plan Salud Premium",
        vigente=True,
        fecha_inicio="2024-01-01",
        fecha_fin="2024-12-31",
        limite_anual=50000.0,
        consumido_anual=8500.0,
        disponible=41500.0,
        cubre_emergencias=True,
        periodo_carencia_dias=30,
        dias_carencia_cumplidos=True,
        deducible=200.0,
        porcentaje_coaseguro=20.0,
        gestor_casos_nombre="Dra. María Vásquez",
        gestor_casos_email="mvasquez@aseguradoradelsur.ec",
        gestor_casos_telefono="+593 98 765 4321",
        email_aseguradora="casos@aseguradoradelsur.ec",
    ),
    "0912345675": DatosPoliza(
        numero_poliza="POL-2024-002",
        aseguradora="Seguros Sucre",
        plan="Plan Básico",
        vigente=True,
        fecha_inicio="2024-06-01",
        fecha_fin="2025-05-31",
        limite_anual=20000.0,
        consumido_anual=19200.0,
        disponible=800.0,
        cubre_emergencias=True,
        periodo_carencia_dias=90,
        dias_carencia_cumplidos=True,
        deducible=500.0,
        porcentaje_coaseguro=30.0,
        gestor_casos_nombre="Ing. Carlos Rueda",
        gestor_casos_email="crueda@segurossucre.com.ec",
        gestor_casos_telefono="+593 99 111 2233",
        email_aseguradora="emergencias@segurossucre.com.ec",
    ),
    "1700000001": DatosPoliza(
        numero_poliza="N/A",
        aseguradora="N/A",
        plan="N/A",
        vigente=False,
        fecha_inicio="2023-01-01",
        fecha_fin="2023-12-31",
        limite_anual=0.0,
        consumido_anual=0.0,
        disponible=0.0,
        cubre_emergencias=False,
        periodo_carencia_dias=0,
        dias_carencia_cumplidos=False,
        deducible=0.0,
        porcentaje_coaseguro=100.0,
        gestor_casos_nombre="N/A",
        gestor_casos_email="",
        gestor_casos_telefono="",
        email_aseguradora="",
    ),
}

PREEXISTENCIAS_DEMO = {
    "1723456784": [
        PreExistencia(
            condicion="Hipertensión arterial",
            codigo_cie10="I10",
            declarada=True,
            fecha_diagnostico="2020-03-15",
            excluida_de_cobertura=False,
        )
    ],
    "0912345675": [],
    "1700000001": [],
}


async def obtener_poliza(cedula: str) -> Optional[DatosPoliza]:
    """
    Obtiene datos de póliza desde Notion.
    En modo demo (sin token) usa datos locales.
    """
    if not NOTION_TOKEN or NOTION_TOKEN == "":
        await asyncio.sleep(0.1)  # simular latencia
        return POLIZAS_DEMO.get(cedula)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{NOTION_BASE}/databases/{NOTION_POLIZAS_DB}/query",
                headers=HEADERS,
                json={
                    "filter": {
                        "property": "cedula_titular",
                        "rich_text": {"equals": cedula},
                    }
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                return None
            props = results[0]["properties"]
            return _mapear_poliza_notion(props)
    except Exception as e:
        print(f"[Notion] Error al obtener póliza para {cedula}: {e}")
        return POLIZAS_DEMO.get(cedula)


async def obtener_preexistencias(cedula: str) -> list[PreExistencia]:
    """Obtiene pre-existencias declaradas del asegurado."""
    if not NOTION_TOKEN or NOTION_TOKEN == "":
        await asyncio.sleep(0.05)
        return PREEXISTENCIAS_DEMO.get(cedula, [])

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{NOTION_BASE}/databases/{NOTION_PREEXISTENCIAS_DB}/query",
                headers=HEADERS,
                json={
                    "filter": {
                        "property": "cedula_paciente",
                        "rich_text": {"equals": cedula},
                    }
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return [_mapear_preexistencia(r["properties"]) for r in results]
    except Exception as e:
        print(f"[Notion] Error al obtener pre-existencias para {cedula}: {e}")
        return PREEXISTENCIAS_DEMO.get(cedula, [])


async def crear_caso_notion(
    caso_id: str,
    cedula: str,
    nombre: str,
    hospital_id: str,
    estado: str,
    score: int,
    resumen: str,
) -> Optional[str]:
    """Crea un caso activo en la base de datos de Notion. Retorna URL del registro."""
    if not NOTION_TOKEN or NOTION_TOKEN == "":
        print(f"[Notion Demo] Caso {caso_id} registrado localmente")
        return f"https://notion.so/demo/{caso_id}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{NOTION_BASE}/pages",
                headers=HEADERS,
                json={
                    "parent": {"database_id": NOTION_CASOS_DB},
                    "properties": {
                        "caso_id": {"title": [{"text": {"content": caso_id}}]},
                        "cedula_paciente": {"rich_text": [{"text": {"content": cedula}}]},
                        "nombre_paciente": {"rich_text": [{"text": {"content": nombre}}]},
                        "hospital_id": {"rich_text": [{"text": {"content": hospital_id}}]},
                        "estado_cobertura": {"select": {"name": estado}},
                        "score_riesgo": {"number": score},
                        "resumen": {"rich_text": [{"text": {"content": resumen[:2000]}}]},
                        "fecha_ingreso": {"date": {"start": datetime.now().isoformat()}},
                        "activo": {"checkbox": True},
                    },
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            page_id = resp.json().get("id", "")
            return f"https://notion.so/{page_id.replace('-', '')}"
    except Exception as e:
        print(f"[Notion] Error al crear caso: {e}")
        return None


def _mapear_poliza_notion(props: dict) -> DatosPoliza:
    """Mapea propiedades de Notion a DatosPoliza."""
    def txt(key): return props.get(key, {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
    def num(key): return props.get(key, {}).get("number", 0.0) or 0.0
    def chk(key): return props.get(key, {}).get("checkbox", False)
    def sel(key): return (props.get(key, {}).get("select") or {}).get("name", "")
    def dat(key): return (props.get(key, {}).get("date") or {}).get("start", "")

    return DatosPoliza(
        numero_poliza=txt("numero_poliza"),
        aseguradora=txt("aseguradora"),
        plan=sel("plan"),
        vigente=chk("vigente"),
        fecha_inicio=dat("fecha_inicio"),
        fecha_fin=dat("fecha_fin"),
        limite_anual=num("limite_anual"),
        consumido_anual=num("consumido_anual"),
        disponible=num("limite_anual") - num("consumido_anual"),
        cubre_emergencias=chk("cubre_emergencias"),
        periodo_carencia_dias=int(num("periodo_carencia_dias")),
        dias_carencia_cumplidos=chk("dias_carencia_cumplidos"),
        deducible=num("deducible"),
        porcentaje_coaseguro=num("porcentaje_coaseguro"),
        gestor_casos_nombre=txt("gestor_casos_nombre"),
        gestor_casos_email=txt("gestor_casos_email"),
        gestor_casos_telefono=txt("gestor_casos_telefono"),
        email_aseguradora=txt("email_aseguradora"),
    )


def _mapear_preexistencia(props: dict) -> PreExistencia:
    def txt(key): return props.get(key, {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
    def chk(key): return props.get(key, {}).get("checkbox", False)
    def dat(key): return (props.get(key, {}).get("date") or {}).get("start", None)

    return PreExistencia(
        condicion=txt("condicion"),
        codigo_cie10=txt("codigo_cie10") or None,
        declarada=chk("declarada"),
        fecha_diagnostico=dat("fecha_diagnostico"),
        excluida_de_cobertura=chk("excluida_de_cobertura"),
    )
