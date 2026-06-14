"""Toplama rotası optimizasyonu.

Filo simülasyonunun ürettiği kutu sözlükleri üzerinde çalışır. Eşiği aşan
kutuları filtreler ve "en yakın komşu" (nearest neighbor) ile bir toplama
sırası kurar. Mesafe 3 boyutludur: yatay (haversine) + dikey (kat farkı).

Kutu sözlüğü beklenen yapı:
    {bin_id, building, floor, x_coord, y_coord, fills: {metal, plastic, glass, other}}
"""

from __future__ import annotations

import math

CAPACITY_LITERS = 50.0          # materyal bölmesi kapasitesi (litre)
FLOOR_HEIGHT_METERS = 3.0       # bir kat = kaç metre dikey


def _fill_for_material(b: dict, material: str) -> float:
    fills = b["fills"]
    if material == "all":
        return max(fills.values())
    return fills.get(material, 0.0)


def get_bins_to_collect(bins: list[dict], threshold: float, material: str) -> list[dict]:
    """Belirtilen materyalin doluluğu eşiği geçen kutuları döndürür."""
    return [b for b in bins if _fill_for_material(b, material) >= threshold]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """İki GPS koordinatı arası yüzey mesafesi (metre)."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _distance(b1: dict, b2: dict) -> float:
    """İki kutu arası 3B mesafe (metre): yatay haversine + dikey kat farkı."""
    horizontal = _haversine(b1["x_coord"], b1["y_coord"], b2["x_coord"], b2["y_coord"])
    vertical = abs(b1["floor"] - b2["floor"]) * FLOOR_HEIGHT_METERS
    return math.sqrt(horizontal ** 2 + vertical ** 2)


def nearest_neighbor_route(bins: list[dict], material: str) -> list[dict]:
    """En dolu kutudan başlayıp her adımda en yakın komşuya giden sıra."""
    if not bins:
        return []
    unvisited = list(bins)
    current = max(unvisited, key=lambda b: _fill_for_material(b, material))
    route = []
    while unvisited:
        route.append(current)
        unvisited.remove(current)
        if not unvisited:
            break
        current = min(unvisited, key=lambda b: _distance(route[-1], b))
    return route


def _total_distance(ordered: list[dict]) -> float:
    total = sum(_distance(ordered[i], ordered[i + 1]) for i in range(len(ordered) - 1))
    return round(total, 1)


def _detail(b: dict) -> dict:
    fills = b["fills"]
    liters = {m: round(CAPACITY_LITERS * fills[m] / 100.0, 1) for m in fills}
    return {
        "bin_id": b["bin_id"],
        "building": b["building"],
        "floor": b["floor"],
        "fill_metal_pct": round(fills["metal"], 1),
        "fill_plastic_pct": round(fills["plastic"], 1),
        "fill_glass_pct": round(fills["glass"], 1),
        "fill_other_pct": round(fills["other"], 1),
        "metal_liters": liters["metal"],
        "plastic_liters": liters["plastic"],
        "glass_liters": liters["glass"],
        "other_liters": liters["other"],
        "total_liters": round(sum(liters.values()), 1),
    }


def optimize(bins: list[dict], material: str = "all", threshold: float = 80.0) -> dict:
    """Filtrele → rota kur → mesafe + hacim hesapla → zengin sonuç döndür."""
    full = get_bins_to_collect(bins, threshold, material)
    ordered = nearest_neighbor_route(full, material)
    details = [_detail(b) for b in ordered]
    summary = {
        "metal_liters": round(sum(d["metal_liters"] for d in details), 1),
        "plastic_liters": round(sum(d["plastic_liters"] for d in details), 1),
        "glass_liters": round(sum(d["glass_liters"] for d in details), 1),
        "other_liters": round(sum(d["other_liters"] for d in details), 1),
    }
    return {
        "route": details,
        "route_order": [b["bin_id"] for b in ordered],
        "total_bins_in_route": len(ordered),
        "total_bins_in_system": len(bins),
        "threshold_used": threshold,
        "material_filter": material,
        "total_distance_meters": _total_distance(ordered),
        "total_liters": round(sum(d["total_liters"] for d in details), 1),
        "collection_summary": summary,
    }
