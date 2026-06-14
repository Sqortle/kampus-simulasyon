"""Atık görseli sınıflandırma servisi.

Hugging Face `image-classification` pipeline'ı (model: yangy50/garbage-classficition)
ile yüklenen bir görseldeki atık türünü tahmin eder. Model lazy (ilk istekte)
yüklenir; transformers/torch kurulu değilse veya model indirilemezse FALLBACK
moduna düşülür ve sunucu çalışmaya devam eder.

Bu servis yalnızca görüntü işleme yapar — simülasyona bağlı değildir.
"""

from __future__ import annotations

import io

_classifier = None  # None: denenmedi | "FALLBACK": kullanılamıyor | pipeline: hazır

# Atık türü -> ezilmiş kalınlık (metre). Arkadaşımızın modelindeki değerlerle aynı.
WASTE_PROPERTIES = {
    "cardboard": 0.05,
    "glass": 0.03,
    "metal": 0.02,
    "paper": 0.01,
    "plastic": 0.025,
    "trash": 0.02,
}

# İngilizce model etiketi -> Türkçe görünen ad
LABEL_TR = {
    "cardboard": "Karton",
    "glass": "Cam",
    "metal": "Metal",
    "paper": "Kâğıt",
    "plastic": "Plastik",
    "trash": "Diğer",
}

# Atık türü -> atılması gereken kutu rengi
BIN_COLOR = {
    "cardboard": "mavi",
    "paper": "mavi",
    "plastic": "mavi",
    "glass": "yeşil",
    "metal": "gri",
    "trash": "gri",
}


def get_classifier():
    """Sınıflandırma pipeline'ını lazy yükler (singleton). Hata olursa 'FALLBACK'."""
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline
            print("[SİSTEM] Hugging Face sınıflandırma modeli yükleniyor...")
            _classifier = pipeline(
                "image-classification",
                model="yangy50/garbage-classification",
            )
        except Exception as exc:  # transformers/torch yok ya da indirme hatası
            print(f"[UYARI] Sınıflandırma modeli yüklenemedi: {exc}")
            _classifier = "FALLBACK"
    return _classifier


def classify_image(image_bytes: bytes) -> dict:
    """Görsel baytlarını alır, atık türünü döndürür.

    Model yoksa {'model_used': False, 'message': ...} döner (rastgele tahmin üretmez).
    """
    model = get_classifier()
    if model == "FALLBACK" or model is None:
        return {
            "model_used": False,
            "message": "Sınıflandırma modeli yüklü değil "
                       "(transformers/torch kurulu değil veya model indirilemedi).",
        }

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        predictions = model(img)
        top = predictions[0]
        label = str(top["label"]).lower()
        return {
            "model_used": True,
            "category": label,
            "category_tr": LABEL_TR.get(label, label.capitalize()),
            "confidence": round(float(top["score"]), 3),
            "bin_color": BIN_COLOR.get(label, "gri"),
            "thickness_cm": round(WASTE_PROPERTIES.get(label, 0.02) * 100, 1),
        }
    except Exception as exc:
        return {"model_used": False, "message": f"Görsel işlenemedi: {exc}"}
