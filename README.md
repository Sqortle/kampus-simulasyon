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

## Öğrencilere Kurallar

- Yalnızca kendi `frontend/grupN/` klasörünüze dokunun. `index.html` ve `style.css` serbesttir;
  ek JS/görsel dosya ekleyebilirsiniz. CSS tamamen serbesttir, ortak stylesheet yoktur.
- `simulation/dijital_ikiz.py` içindeki prosedür gövdeleri doldurulur;
  **yeni fonksiyon veya event sınıfı eklenmez**.
- API adresleri ve döndürdükleri JSON yapısı değiştirilmez; frontend `fetch('/api/...')` ile çağırır.
- Yeni endpoint ihtiyacı olursa proje yöneticisine iletilir.
