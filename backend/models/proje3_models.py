"""Proje 3 (Enerji & CO2 Yönetimi) yanıt şemaları."""

from pydantic import BaseModel


class HourlyRecord(BaseModel):
    hour: int
    people: int
    lights_on: int
    vent_on: bool
    current_a: float
    energy_wh: float
    temp: float
    co2: int


class SimulateResponse(BaseModel):
    total_energy_wh: float
    lighting_energy_wh: float
    vent_energy_wh: float
    max_co2: int
    hours: int               # kaç saatlik kayıt var


class HourlyReportResponse(BaseModel):
    hourly: list[HourlyRecord]


class EnergySummaryResponse(BaseModel):
    lighting_energy_wh: float
    vent_energy_wh: float
    total_energy_wh: float
    lighting_percent: float
    vent_percent: float


class CurrentStateResponse(BaseModel):
    people: int
    co2: int
    temp: float
    vent_on: bool
    lights_on: int
    current_a: float
    co2_critical: bool       # CO2 kritik eşiği aştı mı (uyarı banner'ı için)
