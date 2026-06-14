# -*- coding: utf-8 -*-
"""
Kutu Filosu Simülasyonu (Proje 1 — Akıllı Geri Dönüşüm)

Birden çok geri dönüşüm kutusunu modeller. Her kutunun konumu (bina, kat,
koordinat) ve 4 materyal bölmesi (metal, plastik, cam, diğer) vardır. Her kutu
gün boyunca BAĞIMSIZ kendi stokastik simülasyonu ile dolar.

Çıktı: en sonda tek satır `__SIM_JSON__{...}` ile tüm filonun durumu ve kutu
başına materyal bazlı zaman serisi basılır. Web katmanı bunu okuyup
görselleştirir; bu dosyanın mantığı web tarafından değiştirilmez.

Not: dijital_ikiz.py'nin ruhu (rastgele kişi gelişi, atma olasılığı,
sınıflandırma) burada hafif/hızlı bir biçimde, çok kutu için uygulanır.
"""

import json
import random

SIM_DURATION = 28800.0        # 8 saat (sn)
SAMPLE_INTERVAL = 900.0       # zaman serisi örnekleme aralığı (15 dk)
CAPACITY_LITERS = 50.0        # her materyal bölmesinin kapasitesi (litre)

MATERIALS = ["metal", "plastic", "glass", "other"]
# Atılan atıkların materyal dağılımı (plastik en sık)
MATERIAL_WEIGHTS = [0.20, 0.40, 0.20, 0.20]


def build_fleet():
    """Kutu filosunu (konum + kimlik) üretir.

    Konumlar gerçek kampüs veritabanından alınmıştır (İstanbul Medeniyet
    Üniversitesi): 3 ana bina (Kütüphane, Yemekhane, Ana Kampüs) her biri
    0–5. kat × 2 kutu, ayrıca kantinler ve bahçe noktaları. Toplam 40 kutu.
    """
    bins = []
    port = 8081

    # Çok katlı binalar: (bina adı, enlem, N1 boylam, N2 boylam)
    # Katlar üst üste yığılır: aynı enlem/boylam, yalnızca kat farkı (dikey mesafe).
    multifloor = [
        ("Kutuphane", 40.2230, 29.01900, 29.01906),
        ("Yemekhane", 40.2250, 29.01600, 29.01606),
        ("AnaKampus", 40.2260, 29.01760, 29.01766),
    ]
    for building, base_x, y1, y2 in multifloor:
        for floor in range(6):                       # 0..5. kat
            for n, y in enumerate([y1, y2], start=1):
                bins.append({
                    "bin_id": f"BIN_{building}_K{floor}_N{n}",
                    "ip_address": f"127.0.0.1:{port}",
                    "building": building,
                    "floor": floor,
                    "x_coord": base_x,               # katlar dikey, enlem sabit
                    "y_coord": y,
                })
                port += 1

    # Tekil noktalar — kantinler ait oldukları binanın zemin katına yakın konumlanır
    extras = [
        ("BIN_Kutuphane_Kantin", "Kutuphane Kantin", 0, 40.2230, 29.01912),
        ("BIN_AnaBina_Kantin", "Ana Bina Kantin", 0, 40.2260, 29.01772),
        ("BIN_Bahce_Kuzey", "Bahce", 0, 40.2240, 29.01850),
        ("BIN_Bahce_Guney", "Bahce", 0, 40.2255, 29.01720),
    ]
    for bin_id, building, floor, x, y in extras:
        bins.append({
            "bin_id": bin_id,
            "ip_address": f"127.0.0.1:{port}",
            "building": building,
            "floor": floor,
            "x_coord": x,
            "y_coord": y,
        })
        port += 1

    return bins


def simulate_bin():
    """Tek bir kutunun gün boyunca dolumunu simüle eder.

    Returns: (timeline, fills)
      timeline: [{t, metal, plastic, glass, other}] (yüzde)
      fills: gün sonu doluluk yüzdeleri
    """
    # Kutu popülerliği: bir kısım kutu neredeyse boş kalır, bir kısmı yoğun
    if random.random() < 0.4:
        popularity = random.uniform(0.0, 0.15)     # sakin kutu
    else:
        popularity = random.uniform(0.4, 1.2)      # yoğun kutu

    expected_items = popularity * 80
    n_items = max(0, int(random.gauss(expected_items, expected_items * 0.2)))

    # Gün içinde rastgele atma olayları üret
    events = []
    for _ in range(n_items):
        t = random.uniform(0, SIM_DURATION)
        material = random.choices(MATERIALS, weights=MATERIAL_WEIGHTS)[0]
        liters = random.uniform(1.0, 3.0)
        events.append((t, material, liters))
    events.sort(key=lambda e: e[0])

    # Sabit ızgarada örnekleyerek zaman serisi çıkar
    liters_acc = {m: 0.0 for m in MATERIALS}
    timeline = []
    ei = 0
    t = 0.0
    while t <= SIM_DURATION + 1e-6:
        while ei < len(events) and events[ei][0] <= t:
            _, material, liters = events[ei]
            liters_acc[material] = min(CAPACITY_LITERS, liters_acc[material] + liters)
            ei += 1
        sample = {"t": round(t, 1)}
        for m in MATERIALS:
            sample[m] = round(liters_acc[m] / CAPACITY_LITERS * 100, 1)
        timeline.append(sample)
        t += SAMPLE_INTERVAL

    fills = {m: timeline[-1][m] for m in MATERIALS}
    return timeline, fills


def main():
    print("--- KUTU FİLOSU SİMÜLASYONU BAŞLIYOR ---\n")
    bins = build_fleet()

    for b in bins:
        timeline, fills = simulate_bin()
        b["timeline"] = timeline
        b["fills"] = fills
        max_fill = max(fills.values())
        b["fill_max"] = round(max_fill, 1)
        print(f"  {b['bin_id']:<22} (Kat {b['floor']}) -> "
              f"max %{max_fill:.0f} | metal %{fills['metal']:.0f} "
              f"plastik %{fills['plastic']:.0f} cam %{fills['glass']:.0f} "
              f"diğer %{fills['other']:.0f}")

    over = sum(1 for b in bins if b["fill_max"] >= 80.0)
    print(f"\n--- SİMÜLASYON TAMAMLANDI --- ({len(bins)} kutu, {over} tanesi %80 üstü)")

    summary = {
        "sim_duration": SIM_DURATION,
        "sample_interval": SAMPLE_INTERVAL,
        "capacity_liters": CAPACITY_LITERS,
        "materials": MATERIALS,
        "bins": bins,
    }
    print("__SIM_JSON__" + json.dumps(summary))


if __name__ == "__main__":
    main()
