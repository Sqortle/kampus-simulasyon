"""Proje 3 — Enerji & CO2 Yönetimi endpoint'leri.

simulate        : 8 saatlik simülasyonu çalıştırır, enerji özetini döndürür
hourly-report   : saatlik CO2 / sıcaklık / enerji / kişi listesi (grafik için)
energy-summary  : aydınlatma vs HVAC tüketim dağılımı
current-state   : son ölçülen anlık oda durumu
"""

from fastapi import APIRouter, HTTPException

from backend import runner
from backend.models.proje3_models import (
    CurrentStateResponse,
    EnergySummaryResponse,
    HourlyReportResponse,
    SimulateResponse,
)

router = APIRouter()


def _get_data() -> dict:
    data = runner.ensure_result()
    if "error" in data:
        raise HTTPException(status_code=500, detail=data)
    return data


@router.post("/simulate", response_model=SimulateResponse)
def simulate():
    """8 saatlik simülasyonu baştan çalıştırır ve enerji özetini döndürür."""
    data = runner.run_simulation()
    if "error" in data:
        raise HTTPException(status_code=500, detail=data)

    return SimulateResponse(
        total_energy_wh=data["total_energy_wh"],
        lighting_energy_wh=data["lighting_energy_wh"],
        vent_energy_wh=data["vent_energy_wh"],
        max_co2=data["max_co2"],
        hours=len(data["hourly"]),
    )


@router.get("/hourly-report", response_model=HourlyReportResponse)
def hourly_report():
    """Saatlik ölçümleri döndürür (CO2/sıcaklık/enerji/akım/kişi grafikleri için)."""
    data = _get_data()
    return HourlyReportResponse(hourly=data["hourly"])


@router.get("/energy-summary", response_model=EnergySummaryResponse)
def energy_summary():
    """Aydınlatma ve HVAC tüketim dağılımını yüzde olarak döndürür."""
    data = _get_data()
    lighting = data["lighting_energy_wh"]
    vent = data["vent_energy_wh"]
    total = lighting + vent
    if total <= 0:
        lighting_pct = vent_pct = 0.0
    else:
        lighting_pct = round(lighting / total * 100.0, 1)
        vent_pct = round(vent / total * 100.0, 1)

    return EnergySummaryResponse(
        lighting_energy_wh=lighting,
        vent_energy_wh=vent,
        total_energy_wh=round(total, 2),
        lighting_percent=lighting_pct,
        vent_percent=vent_pct,
    )


@router.get("/current-state", response_model=CurrentStateResponse)
def current_state():
    """En son saatlik kayda göre anlık oda durumunu döndürür."""
    data = _get_data()
    hourly = data["hourly"]
    if not hourly:
        raise HTTPException(status_code=404, detail="Henüz saatlik veri yok.")

    last = hourly[-1]
    return CurrentStateResponse(
        people=last["people"],
        co2=last["co2"],
        temp=last["temp"],
        vent_on=last["vent_on"],
        lights_on=last["lights_on"],
        current_a=last["current_a"],
        co2_critical=last["co2"] >= data["critical_co2"],
    )
