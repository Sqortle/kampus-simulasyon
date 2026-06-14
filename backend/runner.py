"""Simülasyonları alt süreç (subprocess) olarak çalıştırıp yapılandırılmış
çıktılarını döndürür.

İki simülasyon vardır:
  - `simulation/dijital_ikiz.py`  -> Proje 3 (enerji & CO2, tek oda)
  - `simulation/kutu_filosu.py`   -> Proje 1 (çok kutulu geri dönüşüm filosu)

Her ikisi de en sonda tek satır halinde `__SIM_JSON__{...}` basar. Buradaki tek
iş o satırı bulup parse etmektir; geri kalan konsol çıktısına dokunulmaz.
Sonuçlar bellekte cache'lenir, böylece GET endpoint'leri aynı koşunun verisini
okur (her tıklamada yeniden koşmaz).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

# backend/ -> proje kökü
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SIM_PATH = os.path.join(_PROJECT_ROOT, "simulation", "dijital_ikiz.py")
_FLEET_PATH = os.path.join(_PROJECT_ROOT, "simulation", "kutu_filosu.py")
_JSON_PREFIX = "__SIM_JSON__"

_last_result: dict | None = None      # Proje 3 (dijital_ikiz)
_last_fleet: dict | None = None       # Proje 1 (kutu_filosu)


def _run_script(path: str, timeout: int) -> dict:
    """Verilen simülasyon betiğini çalıştırır, __SIM_JSON__ satırını parse eder."""
    try:
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=_PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Simülasyon {timeout} sn içinde tamamlanamadı (timeout)."}

    if result.returncode != 0:
        stderr_tail = (result.stderr or "").strip().splitlines()[-5:]
        return {"error": "Simülasyon hata ile sonlandı.", "detail": "\n".join(stderr_tail)}

    for line in result.stdout.splitlines():
        if line.startswith(_JSON_PREFIX):
            try:
                return json.loads(line[len(_JSON_PREFIX):])
            except json.JSONDecodeError as exc:
                return {"error": f"Simülasyon çıktısı JSON olarak ayrıştırılamadı: {exc}"}

    return {"error": "Simülasyon çıktısında __SIM_JSON__ satırı bulunamadı."}


# --- Proje 3: dijital_ikiz ---
def run_simulation(timeout: int = 120) -> dict:
    global _last_result
    data = _run_script(_SIM_PATH, timeout)
    if "error" not in data:
        _last_result = data
    return data


def ensure_result() -> dict:
    if _last_result is None:
        return run_simulation()
    return _last_result


# --- Proje 1: kutu_filosu ---
def run_fleet(timeout: int = 120) -> dict:
    global _last_fleet
    data = _run_script(_FLEET_PATH, timeout)
    if "error" not in data:
        _last_fleet = data
    return data


def ensure_fleet() -> dict:
    if _last_fleet is None:
        return run_fleet()
    return _last_fleet
