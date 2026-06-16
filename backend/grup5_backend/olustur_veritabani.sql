-- olustur_veritabani.sql
-- Akıllı Sınıf Otomasyon Sistemi - Takım 5
--
-- Bu betik, SQLite veritabanı şemasını (akilli_sinif.db) oluşturur.
-- Tablo şeması, ilk çalıştırmada backend/grup5_backend/veritabani.py
-- tarafından otomatik oluşturulur; bu dosya isteğe bağlı olarak şemayı
-- manuel oluşturmak isteyenler içindir.
--
-- Kullanım (sqlite3 ile, proje kökünden):
--   sqlite3 backend/grup5_backend/akilli_sinif.db < backend/grup5_backend/olustur_veritabani.sql

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS simulasyon_oturumu (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    baslangic_zamani TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    bitis_zamani     TEXT,
    toplam_sure_sn   REAL,
    durum            TEXT DEFAULT 'CALISIYOR'
);

CREATE TABLE IF NOT EXISTS ortam_olcumleri (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    oturum_id           INTEGER REFERENCES simulasyon_oturumu(id) ON DELETE CASCADE,
    sim_zamani_sn       REAL NOT NULL,
    aktif_kisi_sayisi   INTEGER NOT NULL,
    acik_isik_adedi     INTEGER NOT NULL,
    havalandirma_durumu INTEGER NOT NULL,
    anlik_akim_a        REAL,
    sicaklik_c          REAL,
    co2_ppm             REAL,
    toplam_enerji_wh    REAL,
    kayit_zamani        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS geri_donusum_olaylari (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    oturum_id           INTEGER REFERENCES simulasyon_oturumu(id) ON DELETE CASCADE,
    sim_zamani_sn       REAL NOT NULL,
    olay_tipi           TEXT NOT NULL,
    kutudaki_atik_adedi INTEGER,
    yigin_yuksekligi_m  REAL,
    kayit_zamani        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pir_hareket_olaylari (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    oturum_id           INTEGER REFERENCES simulasyon_oturumu(id) ON DELETE CASCADE,
    sim_zamani_sn       REAL NOT NULL,
    sensor_id           TEXT NOT NULL,
    hareket_algilandi   INTEGER NOT NULL,
    oda_doluluk_tahmini INTEGER,
    kayit_zamani        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ortam_oturum ON ortam_olcumleri(oturum_id);
CREATE INDEX IF NOT EXISTS idx_geridonusum_oturum ON geri_donusum_olaylari(oturum_id);
CREATE INDEX IF NOT EXISTS idx_pir_oturum ON pir_hareket_olaylari(oturum_id);
