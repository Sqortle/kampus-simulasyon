# -*- coding: utf-8 -*-
"""
veritabani.py
SQLite bağlantı ve şema yönetimi.
Akıllı Sınıf Otomasyon Sistemi - Takım 5

Bu modül, dijital_ikiz.py'nin ürettiği simülasyon olaylarını bir SQLite
veritabanına yazmak için kullanılır. Projenin geri kalanıyla aynı şekilde
harici bir veritabanı sunucusu gerektirmez; veriler paket içindeki tek bir
.db dosyasında tutulur.

Not: Simülasyon arka plan thread'inden yazarken web isteği thread'inden de
okunabildiği için bağlantı `check_same_thread=False` ile açılır ve yazma/okuma
işlemleri bir kilit (Lock) ile serileştirilir.
"""

import os
import sqlite3
import threading


VARSAYILAN_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "akilli_sinif.db")


def _row_to_dict(row):
    return dict(row) if row is not None else None


class VeritabaniYoneticisi:
    """SQLite veritabanı bağlantısını ve şemasını yönetir."""

    def __init__(self, db_path=VARSAYILAN_DB):
        self.db_path = db_path
        self.conn = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # BAĞLANTI
    # ------------------------------------------------------------------
    def baglan(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        return self.conn

    def baglantiyi_kapat(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.baglan()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.baglantiyi_kapat()

    # ------------------------------------------------------------------
    # ŞEMA OLUŞTURMA
    # ------------------------------------------------------------------
    SEMA_SQL = """
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
    """

    def semayi_olustur(self):
        with self._lock:
            self.conn.executescript(self.SEMA_SQL)
            self.conn.commit()

    # ------------------------------------------------------------------
    # OTURUM İŞLEMLERİ
    # ------------------------------------------------------------------
    def oturum_baslat(self):
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO simulasyon_oturumu (durum) VALUES ('CALISIYOR');"
            )
            self.conn.commit()
            return cur.lastrowid

    def oturum_bitir(self, oturum_id, toplam_sure_sn):
        with self._lock:
            self.conn.execute(
                """UPDATE simulasyon_oturumu
                   SET bitis_zamani = CURRENT_TIMESTAMP, toplam_sure_sn = ?, durum = 'TAMAMLANDI'
                   WHERE id = ?;""",
                (toplam_sure_sn, oturum_id),
            )
            self.conn.commit()

    # ------------------------------------------------------------------
    # VERİ YAZMA
    # ------------------------------------------------------------------
    def ortam_olcumu_ekle(self, oturum_id, sim_zamani_sn, aktif_kisi_sayisi,
                           acik_isik_adedi, havalandirma_durumu, anlik_akim_a,
                           sicaklik_c, co2_ppm, toplam_enerji_wh):
        with self._lock:
            self.conn.execute(
                """INSERT INTO ortam_olcumleri
                   (oturum_id, sim_zamani_sn, aktif_kisi_sayisi, acik_isik_adedi,
                    havalandirma_durumu, anlik_akim_a, sicaklik_c, co2_ppm, toplam_enerji_wh)
                   VALUES (?,?,?,?,?,?,?,?,?);""",
                (oturum_id, sim_zamani_sn, aktif_kisi_sayisi, acik_isik_adedi,
                 int(bool(havalandirma_durumu)), anlik_akim_a, sicaklik_c, co2_ppm,
                 toplam_enerji_wh),
            )
            self.conn.commit()

    def geri_donusum_olayi_ekle(self, oturum_id, sim_zamani_sn, olay_tipi,
                                 kutudaki_atik_adedi=None, yigin_yuksekligi_m=None):
        with self._lock:
            self.conn.execute(
                """INSERT INTO geri_donusum_olaylari
                   (oturum_id, sim_zamani_sn, olay_tipi, kutudaki_atik_adedi, yigin_yuksekligi_m)
                   VALUES (?,?,?,?,?);""",
                (oturum_id, sim_zamani_sn, olay_tipi, kutudaki_atik_adedi, yigin_yuksekligi_m),
            )
            self.conn.commit()

    def pir_olayi_ekle(self, oturum_id, sim_zamani_sn, sensor_id,
                        hareket_algilandi, oda_doluluk_tahmini):
        with self._lock:
            self.conn.execute(
                """INSERT INTO pir_hareket_olaylari
                   (oturum_id, sim_zamani_sn, sensor_id, hareket_algilandi, oda_doluluk_tahmini)
                   VALUES (?,?,?,?,?);""",
                (oturum_id, sim_zamani_sn, sensor_id, int(bool(hareket_algilandi)),
                 oda_doluluk_tahmini),
            )
            self.conn.commit()

    # ------------------------------------------------------------------
    # VERİ OKUMA (Arayüz için)
    # ------------------------------------------------------------------
    def son_oturum_id(self):
        with self._lock:
            cur = self.conn.execute(
                "SELECT id FROM simulasyon_oturumu ORDER BY id DESC LIMIT 1;"
            )
            row = cur.fetchone()
            return row[0] if row else None

    def ortam_son_kayitlar(self, oturum_id, limit=200):
        with self._lock:
            cur = self.conn.execute(
                """SELECT * FROM ortam_olcumleri
                   WHERE oturum_id = ?
                   ORDER BY sim_zamani_sn DESC LIMIT ?;""",
                (oturum_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]

    def geri_donusum_son_kayitlar(self, oturum_id, limit=50):
        with self._lock:
            cur = self.conn.execute(
                """SELECT * FROM geri_donusum_olaylari
                   WHERE oturum_id = ?
                   ORDER BY sim_zamani_sn DESC LIMIT ?;""",
                (oturum_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]

    def pir_son_kayitlar(self, oturum_id, limit=50):
        with self._lock:
            cur = self.conn.execute(
                """SELECT * FROM pir_hareket_olaylari
                   WHERE oturum_id = ?
                   ORDER BY sim_zamani_sn DESC LIMIT ?;""",
                (oturum_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]

    def oturum_ozet(self, oturum_id):
        with self._lock:
            cur = self.conn.execute(
                """SELECT
                       (SELECT COUNT(*) FROM geri_donusum_olaylari
                        WHERE oturum_id=? AND olay_tipi='ATIK_DUSTU')      AS toplam_atik,
                       (SELECT COUNT(*) FROM pir_hareket_olaylari
                        WHERE oturum_id=? AND hareket_algilandi=1)         AS toplam_pir_tetik,
                       (SELECT MAX(toplam_enerji_wh) FROM ortam_olcumleri
                        WHERE oturum_id=?)                                 AS guncel_enerji_wh,
                       (SELECT MAX(aktif_kisi_sayisi) FROM ortam_olcumleri
                        WHERE oturum_id=?)                                 AS maks_kisi_sayisi
                   ;""",
                (oturum_id, oturum_id, oturum_id, oturum_id),
            )
            return _row_to_dict(cur.fetchone())


if __name__ == "__main__":
    # Basit bağlantı/şema testi
    vt = VeritabaniYoneticisi()
    vt.baglan()
    vt.semayi_olustur()
    print(f"SQLite veritabanı şeması oluşturuldu / kontrol edildi: {vt.db_path}")
    vt.baglantiyi_kapat()
