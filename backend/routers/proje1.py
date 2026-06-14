"""Proje 1 — Akıllı Geri Dönüşüm (Kutu Filosu) endpoint'leri.

simulate                  : filoyu çalıştır, gün sonu özetini döndür
bins                      : tüm kutular (konum + doluluk + zaman serisi)
bins/{bin_id}/timeline    : tek kutunun materyal bazlı zaman serisi
route                     : eşiği aşan kutular için toplama rotası
classify-trash            : çöp sınıflandırma (öğrenci modeli ekleyecek — placeholder)
"""

import random
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from backend import runner
from backend.services import route_optimizer, waste_classifier
from backend.models.proje1_models import (
    BinsResponse,
    BinTimelineResponse,
    ClassifyImageResponse,
    ClassifyTrashResponse,
    RouteResponse,
    SimulateResponse,
)

router = APIRouter()

DEFAULT_THRESHOLD = 80.0


def _fleet():
    data = runner.ensure_fleet()
    if "error" in data:
        raise HTTPException(status_code=500, detail=data)
    return data


@router.post("/simulate", response_model=SimulateResponse)
def simulate():
    """Filoyu baştan çalıştırır ve gün sonu özetini döndürür."""
    data = runner.run_fleet()
    if "error" in data:
        raise HTTPException(status_code=500, detail=data)

    bins = data["bins"]
    over = [b for b in bins if b["fill_max"] >= DEFAULT_THRESHOLD]
    busiest = max(bins, key=lambda b: b["fill_max"]) if bins else None
    return SimulateResponse(
        total_bins=len(bins),
        bins_over_threshold=len(over),
        threshold=DEFAULT_THRESHOLD,
        busiest_bin=busiest["bin_id"] if busiest else "",
        sim_duration=data["sim_duration"],
    )


@router.get("/bins", response_model=BinsResponse)
def bins():
    """Tüm kutuların konum, doluluk ve zaman serisi bilgisini döndürür."""
    return _fleet()


@router.get("/bins/{bin_id}/timeline", response_model=BinTimelineResponse)
def bin_timeline(bin_id: str):
    """Tek bir kutunun materyal bazlı zaman serisini döndürür."""
    data = _fleet()
    for b in data["bins"]:
        if b["bin_id"] == bin_id:
            return BinTimelineResponse(bin_id=bin_id, timeline=b["timeline"])
    raise HTTPException(status_code=404, detail=f"Kutu bulunamadı: {bin_id}")


@router.get("/route", response_model=RouteResponse)
def route(
    material: str = Query("all", description="all | metal | plastic | glass | other"),
    threshold: float = Query(DEFAULT_THRESHOLD, ge=0, le=100),
    at: Optional[float] = Query(
        None, ge=0,
        description="Simülasyon zamanı (sn). Verilirse rota o ana ait dolulukla "
                    "hesaplanır; verilmezse gün sonu durumu kullanılır.",
    ),
):
    """Eşiği aşan kutular için en yakın komşu toplama rotasını hesaplar.

    `at` verildiğinde her kutunun zaman serisinden o ana karşılık gelen örnek
    alınır; böylece playback'i duraklattığın anla rota tutarlı olur.
    """
    data = _fleet()
    bins = data["bins"]

    if at is not None:
        interval = data["sample_interval"]
        snapshot = []
        for b in bins:
            n = len(b["timeline"])
            idx = min(n - 1, max(0, int(at // interval)))
            s = b["timeline"][idx]
            snapshot.append({
                **b,
                "fills": {m: s[m] for m in ("metal", "plastic", "glass", "other")},
            })
        bins = snapshot

    return route_optimizer.optimize(bins, material=material, threshold=threshold)


@router.post("/classify-trash", response_model=ClassifyTrashResponse)
async def classify_trash():
    """PLACEHOLDER — öğrenci görüntü sınıflandırma modelini buraya bağlayacak."""
    categories = ["plastik", "kağıt", "cam", "metal", "organik"]
    bin_map = {
        "plastik": "mavi", "kağıt": "mavi", "cam": "yeşil",
        "metal": "gri", "organik": "kahve",
    }
    cat = random.choice(categories)
    return ClassifyTrashResponse(
        category=cat,
        confidence=round(random.uniform(0.70, 0.99), 2),
        bin_color=bin_map[cat],
    )


@router.post("/classify-image", response_model=ClassifyImageResponse)
def classify_image(file: UploadFile = File(...)):
    """Yüklenen görseli Hugging Face modeliyle sınıflandırır (gerçek görüntü işleme).

    Model kurulu değilse model_used=False ve açıklayıcı bir mesaj döner.
    """
    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Boş dosya.")
    return waste_classifier.classify_image(contents)
