"""
Sistema de Alerta Temprana de Ingresos a Emergencias
HackIAthon - Viamatica Ecuador
Reto 4: Webhook de emergencias con agente IA
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
from pathlib import Path

from routes.webhook import router as webhook_router
from routes.dashboard import router as dashboard_router
from routes.cases import router as cases_router

app = FastAPI(
    title="AlertaEC - Sistema de Emergencias",
    description="Agente IA para alertas tempranas en emergencias médicas - Ecuador",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/api/webhook", tags=["Webhook Admisiones"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(cases_router, prefix="/api/cases", tags=["Casos Activos"])

frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_path / "index.html"))

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "AlertaEC", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
