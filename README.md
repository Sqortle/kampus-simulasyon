# Kampüs Dijital İkiz Simülasyonu

ABM-DES hibrit simülasyonunun ([simulation/dijital_ikiz.py](simulation/dijital_ikiz.py)) çıktısını
bir FastAPI backend üzerinden alıp web arayüzünde görselleştiren takım projesi.

Web katmanı simülasyonu **değiştirmez**; simülasyon kendi içinde (rastgele kişi gelişleri,
%30 çöp atma ihtimali, fizik tabanlı düşme, CO₂/enerji hesapları) çalışır, web sadece çıktısını sunar.

## Kurulum ve Çalıştırma

```bash
git clone <repo-url>
cd kampus-simulasyon

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r backend/requirements.txt

uvicorn backend.main:app --reload --port 8000
```

| URL | Açıklama |
|---|---|
| `localhost:8000` | Ana sayfa |
| `localhost:8000/docs` | Swagger API dokümantasyonu |
| `localhost:8000/frontend/grup8/` | Proje 1 referans uygulaması (geri dönüşüm) |
| `localhost:8000/frontend/ornek-proje3/` | Örnek Proje 3 demo (enerji & CO₂) |
| `localhost:8000/frontend/grup1/` | Grup 1 frontend (grup2…grup8 benzer) |
| `localhost:8000/frontend/grup5/` | Grup 5 — Akıllı Sınıf canlı kontrol paneli (SSE) |

## API Endpoint'leri

### Proje 1 — Akıllı Geri Dönüşüm (Kutu Filosu)
- `POST /api/proje1/simulate` — kutu filosunu çalıştır, gün sonu özeti
- `GET  /api/proje1/bins` — tüm kutular: konum + materyal bazlı doluluk + zaman serisi
- `GET  /api/proje1/bins/{bin_id}/timeline` — tek kutunun materyal bazlı zaman serisi
- `GET  /api/proje1/route?material=all&threshold=80` — eşiği aşan kutular için en yakın komşu toplama rotası
- `POST /api/proje1/classify-trash` — çöp sınıflandırma (placeholder — rastgele)
- `POST /api/proje1/classify-image` — yüklenen görseli Hugging Face modeliyle sınıflandırır (gerçek görüntü işleme; grup8 kamera testi)

Görüntü işleme için `transformers`, `torch`, `Pillow` gerekir (requirements.txt'te). Bunlar
kurulu değilse `classify-image` `model_used: false` döner ve site çalışmaya devam eder.
Model ([yangy50/garbage-classficition](https://huggingface.co/yangy50/garbage-classficition))
**ilk çağrıda indirilir**; ilk istek yavaş, sonrası hızlıdır.

Filo simülasyonu [simulation/kutu_filosu.py](simulation/kutu_filosu.py)'da; rota mantığı
[backend/services/route_optimizer.py](backend/services/route_optimizer.py)'da (en yakın komşu + 3B mesafe).

### Proje 3 — Enerji & CO₂ Yönetimi
- `POST /api/proje3/simulate` — 8 saatlik simülasyonu çalıştır, enerji özeti
- `GET  /api/proje3/hourly-report` — saatlik CO₂/sıcaklık/enerji/kişi listesi
- `GET  /api/proje3/energy-summary` — aydınlatma vs HVAC tüketim dağılımı
- `GET  /api/proje3/current-state` — anlık oda durumu

> **Not:** GET endpoint'leri son `simulate` koşusunun verisini döndürür (cache).
> Veriyi yenilemek için önce `simulate` çağrılır. Böylece tüm grafikler aynı koşuya ait kalır.

### Grup 5 — Akıllı Sınıf Otomasyon Sistemi
Diğer projelerden farklı olarak Grup 5 paneli **canlı** çalışır: simülasyon arka planda
sürer, ortam/geri dönüşüm/PIR olayları **SQLite**'a yazılır ve tarayıcıya Server-Sent
Events (SSE) ile anlık akar.

- `POST /api/grup5/start` — simülasyonu başlat (arka plan thread'i)
- `POST /api/grup5/stop` — çalışan simülasyonu durdur
- `GET  /api/grup5/status` — anlık durum sözlüğü (+ son loglar)
- `GET  /api/grup5/history?oturum_id=` — bir oturumun SQLite kayıtları (özet / ortam / geri dönüşüm / PIR)
- `GET  /api/grup5/events` — canlı durum + log akışı (SSE)

Tüm Grup 5 kodu [backend/grup5_backend/](backend/grup5_backend/) paketinde toplanmıştır:
- [dijital_ikiz.py](backend/grup5_backend/dijital_ikiz.py) — olay tabanlı sınıf simülasyonu (alt süreç olarak çalışır)
- [simulasyon_yoneticisi.py](backend/grup5_backend/simulasyon_yoneticisi.py) — simülasyon çıktısını parse edip PIR ağını üretir ve DB'ye yazar
- [pir_sensoru.py](backend/grup5_backend/pir_sensoru.py) — PIR hareket sensörü ağı
- [veritabani.py](backend/grup5_backend/veritabani.py) — SQLite veri katmanı (`akilli_sinif.db`, çalışma anında oluşur)
- [web_durum.py](backend/grup5_backend/web_durum.py) — canlı durum merkezi (başlat/durdur, SSE yayını, bağımlılık eksikse demo akış)
- [arayuz.py](backend/grup5_backend/arayuz.py) — opsiyonel Tkinter masaüstü paneli

Web API'si [backend/routers/grup5.py](backend/routers/grup5.py) üzerinden ana FastAPI
uygulamasına bağlıdır; ayrı bir sunucu çalıştırmaya gerek yoktur. Veritabanı dosyası
SQLite olduğu için harici bir veritabanı sunucusu (PostgreSQL vb.) kurulmasını gerektirmez.

Opsiyonel masaüstü panel (proje kökünden):

```bash
python -m backend.grup5_backend.arayuz
```

