"""Proje 1 (Akıllı Geri Dönüşüm — Kutu Filosu) yanıt şemaları.

Öğrenciler frontend'i bu yapılara göre yazar; alan adları değişmez.
"""

from typing import Optional

from pydantic import BaseModel


class MaterialFills(BaseModel):
    metal: float
    plastic: float
    glass: float
    other: float


class TimelineSample(BaseModel):
    t: float                  # simülasyon zamanı (sn)
    metal: float              # o andaki doluluk yüzdeleri
    plastic: float
    glass: float
    other: float


class BinState(BaseModel):
    bin_id: str
    ip_address: str
    building: str
    floor: int
    x_coord: float
    y_coord: float
    fills: MaterialFills      # gün sonu doluluk yüzdeleri
    fill_max: float           # en dolu bölme yüzdesi
    timeline: list[TimelineSample]


class BinsResponse(BaseModel):
    sim_duration: float
    sample_interval: float
    capacity_liters: float
    materials: list[str]
    bins: list[BinState]


class BinTimelineResponse(BaseModel):
    bin_id: str
    timeline: list[TimelineSample]


class SimulateResponse(BaseModel):
    total_bins: int
    bins_over_threshold: int
    threshold: float
    busiest_bin: str
    sim_duration: float


# --- Rota (route_optimizer çıktısı) ---
class ClassifyTrashResponse(BaseModel):
    category: str
    confidence: float
    bin_color: str


class ClassifyImageResponse(BaseModel):
    model_used: bool                      # model gerçekten çalıştı mı
    category: Optional[str] = None        # İngilizce etiket (plastic, glass, ...)
    category_tr: Optional[str] = None     # Türkçe ad
    confidence: Optional[float] = None    # 0-1
    bin_color: Optional[str] = None       # mavi / yeşil / gri
    thickness_cm: Optional[float] = None  # ezilmiş kalınlık (cm)
    message: Optional[str] = None         # fallback/hata mesajı


class BinCollectionDetail(BaseModel):
    bin_id: str
    building: str
    floor: int
    fill_metal_pct: float
    fill_plastic_pct: float
    fill_glass_pct: float
    fill_other_pct: float
    metal_liters: float
    plastic_liters: float
    glass_liters: float
    other_liters: float
    total_liters: float


class CollectionSummary(BaseModel):
    metal_liters: float
    plastic_liters: float
    glass_liters: float
    other_liters: float


class RouteResponse(BaseModel):
    route: list[BinCollectionDetail]
    route_order: list[str]
    total_bins_in_route: int
    total_bins_in_system: int
    threshold_used: float
    material_filter: str
    total_distance_meters: float
    total_liters: float
    collection_summary: CollectionSummary
