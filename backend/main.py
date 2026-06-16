"""Kampüs Simülasyon API — FastAPI uygulaması.

Çalıştırma (proje kökünden):
    uvicorn backend.main:app --reload --port 8000
"""

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.routers import proje1, proje3, grup5

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FRONTEND_DIR = os.path.join(_PROJECT_ROOT, "frontend")

app = FastAPI(title="Kampüs Simülasyon API")

app.include_router(proje1.router, prefix="/api/proje1", tags=["Proje 1 - Geri Dönüşüm"])
app.include_router(proje3.router, prefix="/api/proje3", tags=["Proje 3 - Enerji/CO2"])
app.include_router(grup5.router, prefix="/api/grup5", tags=["Grup 5 - Akıllı Sınıf"])

# Statik frontend: /frontend/... altında servis edilir
app.mount("/frontend", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")


@app.get("/")
def root():
    return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))
