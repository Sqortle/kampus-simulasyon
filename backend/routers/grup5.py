"""Grup 5 — Akıllı Sınıf Otomasyon Sistemi endpoint'leri.

Web paneli (frontend/grup5) bu router üzerinden tek FastAPI sunucusuna bağlanır.
Eskiden bağımsız bir http.server (app.py, port 5000) idi; artık
`uvicorn backend.main:app` ile aynı süreçte servis edilir.

start    : simülasyonu başlat (SimulasyonYoneticisi, arka plan thread)
stop     : çalışan simülasyonu durdur
status   : anlık durum sözlüğü (+ son loglar)
history  : SQLite'taki son oturumun özeti / ortam / geri dönüşüm / PIR kayıtları
events   : Server-Sent Events ile canlı durum + log akışı
"""

from __future__ import annotations

import json
import queue
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from backend.grup5_backend.web_durum import merkez
from backend.grup5_backend.veritabani import VeritabaniYoneticisi

router = APIRouter()


@router.post("/start")
def start():
    """Simülasyonu başlatır (zaten çalışıyorsa ok=False döner)."""
    basarili, mesaj = merkez.baslat()
    return {"ok": basarili, "message": mesaj, "status": merkez.anlik()}


@router.post("/stop")
def stop():
    """Çalışan simülasyonu durdurur."""
    basarili, mesaj = merkez.durdur()
    return {"ok": basarili, "message": mesaj, "status": merkez.anlik()}


@router.get("/status")
def status():
    """Anlık durum sözlüğünü (son loglar dahil) döndürür."""
    return merkez.anlik()


@router.get("/history")
def history(oturum_id: Optional[int] = Query(None, description="Belirli bir oturum; verilmezse son oturum")):
    """SQLite'taki bir oturumun özet + zaman serisi kayıtlarını döndürür."""
    vt = VeritabaniYoneticisi()
    vt.baglan()
    try:
        vt.semayi_olustur()
        aktif_oturum = oturum_id or vt.son_oturum_id()
        if aktif_oturum is None:
            return {"ok": True, "data": {
                "oturum_id": None, "ozet": {}, "ortam": [],
                "geri_donusum": [], "pir": [],
            }}
        return {"ok": True, "data": {
            "oturum_id": aktif_oturum,
            "ozet": vt.oturum_ozet(aktif_oturum) or {},
            "ortam": vt.ortam_son_kayitlar(aktif_oturum, limit=80),
            "geri_donusum": vt.geri_donusum_son_kayitlar(aktif_oturum, limit=80),
            "pir": vt.pir_son_kayitlar(aktif_oturum, limit=80),
        }}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
    finally:
        vt.baglantiyi_kapat()


@router.get("/events")
def events():
    """Canlı durum/log akışını Server-Sent Events olarak yayınlar."""

    def akis():
        q = merkez.abone_ekle()

        def paketle(event: str, payload) -> str:
            return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        try:
            yield paketle("status", merkez.anlik())
            while True:
                try:
                    mesaj = q.get(timeout=15)
                    yield paketle(mesaj["event"], mesaj["payload"])
                except queue.Empty:
                    yield paketle("ping", {})
        finally:
            merkez.abone_sil(q)

    return StreamingResponse(
        akis(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
