# -*- coding: utf-8 -*-
"""
web_durum.py
Akıllı Sınıf Otomasyon Sistemi - Takım 5

Web panelinin (frontend/grup5) canlı durumunu yöneten merkez. Eskiden
`app.py` içindeki bağımsız http.server uygulamasının bir parçasıydı; artık
FastAPI router'ı (`backend/routers/grup5.py`) bu modüldeki `merkez` singleton'ını
kullanır.

Sorumlulukları:
  - Simülasyonu (SimulasyonYoneticisi) başlatıp durdurmak,
  - Anlık durum sözlüğünü ve son logları thread-safe tutmak,
  - SSE aboneleri için olay kuyruklarını beslemek (yayinla),
  - Bağımlılıklar (numpy vb.) eksikse demo akışa düşmek.
"""

from __future__ import annotations

import queue
import random
import threading
import time
from typing import Any


class WebDurumMerkezi:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.yonetici: Any | None = None
        self.istemciler: list[queue.Queue] = []
        self.loglar: list[str] = []
        self.son_hata: str | None = None
        self._web_akisi_yavaslat = False
        self._son_sim_zamani = 0.0
        self._son_gercek_zaman = time.monotonic()
        self._sim_saniye_basi_gercek_saniye = 360.0
        self.durum: dict[str, Any] = {
            "sim_zamani": 0.0,
            "aktif_kisi": 0,
            "acik_isik": 0,
            "havalandirma": False,
            "akim_a": 0.0,
            "sicaklik_c": 0.0,
            "co2_ppm": 400.0,
            "toplam_enerji_wh": 0.0,
            "kutudaki_atik": 0,
            "toplam_atik": 0,
            "pir_durum": {},
            "son_saat_raporu": 0,
            "durum_metni": "Beklemede",
            "oturum_id": None,
            "calisiyor": False,
            "mod": "Gerçek simülasyon",
        }

    def anlik(self) -> dict[str, Any]:
        with self.lock:
            durum = dict(self.durum)
            durum["loglar"] = self.loglar[-80:]
            durum["son_hata"] = self.son_hata
            if self.yonetici is not None:
                durum["calisiyor"] = bool(self.yonetici.calisiyor)
                durum["oturum_id"] = self.yonetici.oturum_id
            return durum

    def baslat(self) -> tuple[bool, str]:
        with self.lock:
            if self.yonetici is not None and self.yonetici.calisiyor:
                return False, "Simülasyon zaten çalışıyor."
            self.loglar.clear()
            self.son_hata = None
            self._web_akisi_yavaslat = False
            self._son_sim_zamani = 0.0
            self._son_gercek_zaman = time.monotonic()
            self.durum.update({
                "sim_zamani": 0.0,
                "aktif_kisi": 0,
                "acik_isik": 0,
                "havalandirma": False,
                "akim_a": 0.0,
                "sicaklik_c": 0.0,
                "co2_ppm": 400.0,
                "toplam_enerji_wh": 0.0,
                "kutudaki_atik": 0,
                "toplam_atik": 0,
                "pir_durum": {},
                "durum_metni": "Başlatılıyor",
                "calisiyor": True,
            })

        try:
            from backend.grup5_backend.simulasyon_yoneticisi import SimulasyonYoneticisi

            yonetici = SimulasyonYoneticisi(
                durum_callback=self.durum_guncelle,
                log_callback=self.log_ekle,
            )
            mod = "Gerçek simülasyon"
            uyari = None
            with self.lock:
                self._web_akisi_yavaslat = True
        except ModuleNotFoundError as exc:
            yonetici = DemoSimulasyonYoneticisi(
                durum_callback=self.durum_guncelle,
                log_callback=self.log_ekle,
            )
            mod = "Demo akış"
            uyari = (
                f"Eksik Python paketi: {exc.name}. Gerçek simülasyon için "
                "requirements.txt bağımlılıkları kurulmalı; web paneli demo akışla açıldı."
            )

        try:
            yonetici.baslat()
        except Exception as exc:
            mesaj = str(exc)
            with self.lock:
                self.son_hata = mesaj
                self.durum["durum_metni"] = "Hata"
                self.durum["calisiyor"] = False
            self.yayinla("error", {"message": mesaj})
            return False, mesaj

        with self.lock:
            self.yonetici = yonetici
            self.durum["oturum_id"] = yonetici.oturum_id
            self.durum["calisiyor"] = True
            self.durum["durum_metni"] = "Çalışıyor"
            self.durum["mod"] = mod
            self.son_hata = uyari
        if uyari:
            self.log_ekle(f"[WEB UYARI] {uyari}")
        self.yayinla("status", self.anlik())
        return True, "Simülasyon başlatıldı."

    def durdur(self) -> tuple[bool, str]:
        with self.lock:
            yonetici = self.yonetici
        if yonetici is None:
            return False, "Durdurulacak aktif simülasyon yok."
        yonetici.durdur()
        with self.lock:
            self._web_akisi_yavaslat = False
            self.durum["calisiyor"] = False
            self.durum["durum_metni"] = "Durduruldu"
        self.yayinla("status", self.anlik())
        return True, "Simülasyon durduruldu."

    def durum_guncelle(self, durum: dict[str, Any]) -> None:
        self._web_akis_hizini_uygula(durum)
        with self.lock:
            self.durum.update(durum)
            if self.yonetici is not None:
                self.durum["oturum_id"] = self.yonetici.oturum_id
                self.durum["calisiyor"] = bool(self.yonetici.calisiyor)
            else:
                self.durum["calisiyor"] = durum.get("durum_metni") == "Çalışıyor"
        self.yayinla("status", self.anlik())

    def _web_akis_hizini_uygula(self, durum: dict[str, Any]) -> None:
        sim_zamani = float(durum.get("sim_zamani") or 0.0)
        with self.lock:
            yavaslat = self._web_akisi_yavaslat
            onceki_sim = self._son_sim_zamani
            onceki_gercek = self._son_gercek_zaman
            yonetici = self.yonetici

        if not yavaslat or sim_zamani <= onceki_sim:
            with self.lock:
                self._son_sim_zamani = max(self._son_sim_zamani, sim_zamani)
                self._son_gercek_zaman = time.monotonic()
            return

        hedef_bekleme = (sim_zamani - onceki_sim) / self._sim_saniye_basi_gercek_saniye
        gecen = time.monotonic() - onceki_gercek
        kalan = min(10.0, max(0.0, hedef_bekleme - gecen))

        bitis = time.monotonic() + kalan
        while time.monotonic() < bitis:
            if yonetici is not None and not yonetici.calisiyor:
                break
            time.sleep(min(0.15, bitis - time.monotonic()))

        with self.lock:
            self._son_sim_zamani = sim_zamani
            self._son_gercek_zaman = time.monotonic()

    def log_ekle(self, satir: str) -> None:
        with self.lock:
            self.loglar.append(satir)
            self.loglar = self.loglar[-300:]
        self.yayinla("log", {"line": satir})

    def abone_ekle(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=120)
        with self.lock:
            self.istemciler.append(q)
        return q

    def abone_sil(self, q: queue.Queue) -> None:
        with self.lock:
            if q in self.istemciler:
                self.istemciler.remove(q)

    def yayinla(self, event: str, payload: dict[str, Any]) -> None:
        veri = {"event": event, "payload": payload, "ts": time.time()}
        with self.lock:
            istemciler = list(self.istemciler)
        for q in istemciler:
            try:
                q.put_nowait(veri)
            except queue.Full:
                pass


class DemoSimulasyonYoneticisi:
    """Bağımlılıklar eksikken web panelinin canlı davranışını gösteren hafif akış."""

    def __init__(self, durum_callback, log_callback) -> None:
        self.durum_callback = durum_callback
        self.log_callback = log_callback
        self.oturum_id = "demo"
        self.calisiyor = False
        self._thread: threading.Thread | None = None
        self._durum = {
            "sim_zamani": 0.0,
            "aktif_kisi": 0,
            "acik_isik": 0,
            "havalandirma": False,
            "akim_a": 0.0,
            "sicaklik_c": 22.0,
            "co2_ppm": 400.0,
            "toplam_enerji_wh": 0.0,
            "kutudaki_atik": 0,
            "toplam_atik": 0,
            "pir_durum": {},
            "son_saat_raporu": 0,
            "durum_metni": "Beklemede",
            "oturum_id": self.oturum_id,
            "calisiyor": False,
            "mod": "Demo akış",
        }

    def baslat(self) -> None:
        self.calisiyor = True
        self._thread = threading.Thread(target=self._calistir, daemon=True)
        self._thread.start()

    def durdur(self) -> None:
        self.calisiyor = False

    def _calistir(self) -> None:
        import math

        self.log_callback("--- WEB DEMO AKIŞI BAŞLIYOR ---")
        while self.calisiyor and self._durum["sim_zamani"] < 28800:
            time.sleep(0.45)
            sim_zamani = self._durum["sim_zamani"] + 300
            dalga = (1 + math.sin(sim_zamani / 2400)) / 2
            aktif_kisi = max(0, int(4 + dalga * 32 + random.randint(-3, 3)))
            acik_isik = 0 if aktif_kisi == 0 else min(4, (aktif_kisi + 9) // 10)
            havalandirma = aktif_kisi > 22
            co2 = 420 + aktif_kisi * 18 + (80 if havalandirma else 0)
            sicaklik = 21.8 + aktif_kisi * 0.08 + random.uniform(-0.25, 0.25)
            akim = ((acik_isik * 60) + (1000 if havalandirma else 0)) / 220
            enerji = self._durum["toplam_enerji_wh"] + ((acik_isik * 60) + (1000 if havalandirma else 0)) * (300 / 3600)

            if random.random() < 0.34:
                self._durum["kutudaki_atik"] = min(40, self._durum["kutudaki_atik"] + 1)
                self._durum["toplam_atik"] += 1
                yukseklik = self._durum["kutudaki_atik"] * 0.02
                self.log_callback(
                    f"   [{sim_zamani:.1f} sn] -> Çöp atıldı. Yığın Yüksekliği: "
                    f"{yukseklik:.2f}m (Kutudaki: {self._durum['kutudaki_atik']}/40)"
                )

            if self._durum["kutudaki_atik"] >= 40:
                self.log_callback(f"   [{sim_zamani:.1f} sn] -> [GERİ DÖNÜŞÜM GÖREVLİSİ] Kutu boşaltıldı!")
                self._durum["kutudaki_atik"] = 0

            pir = {f"PIR_{i}": (aktif_kisi > 0 and random.random() < 0.82) for i in range(1, 4)}

            self._durum.update({
                "sim_zamani": sim_zamani,
                "aktif_kisi": aktif_kisi,
                "acik_isik": acik_isik,
                "havalandirma": havalandirma,
                "akim_a": akim,
                "sicaklik_c": sicaklik,
                "co2_ppm": co2,
                "toplam_enerji_wh": enerji,
                "pir_durum": pir,
                "durum_metni": "Çalışıyor",
                "calisiyor": True,
            })

            if sim_zamani % 3600 == 0:
                saat = int(sim_zamani // 3600)
                self.log_callback(f"[{saat}. SAAT RAPORU | Zaman: {sim_zamani:.0f}s] ---")

            self.durum_callback(dict(self._durum))

        self.calisiyor = False
        self._durum["durum_metni"] = "Tamamlandı"
        self._durum["calisiyor"] = False
        self.durum_callback(dict(self._durum))
        self.log_callback("--- WEB DEMO AKIŞI TAMAMLANDI ---")


# FastAPI router'ının paylaştığı tek durum merkezi (singleton)
merkez = WebDurumMerkezi()
