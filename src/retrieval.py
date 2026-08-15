"""Hibrit arama: exact kod eşleşmesi + BM25 + vektör benzerliği.

Yönlendirme (brief §5):

    sorgu
      ├─ hata kodu içeriyor mu?  --EVET-->  indeksli SQL eşleşmesi, bitti
      └─ HAYIR --> BM25 (FTS5) + vektör kosinüs --> RRF ile birleştir

Kod tespiti regex'e TEK BAŞINA güvenmiyor. ABB'nin dört karakterlik onaltılık
biçimi "2024", "FACE" gibi alakasız dizileri de yakalar; bu yüzden regex sadece
aday üretiyor, karar ingestion sırasında kurulan gerçek kod kümesine bakılarak
veriliyor.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

import numpy as np

import config
from src import db

RRF_K = 60          # reciprocal rank fusion sabiti (standart değer)
ADAY_SAYISI = 20    # her yoldan füzyona giren aday sayısı

_KELIME = re.compile(r"[\w']+", re.UNICODE)


@dataclass
class Sonuc:
    chunk_id: int
    vendor: str
    model: str
    fault_code: str | None
    severity: str | None
    page: int
    content: str
    skor: float

    def kaynak(self) -> str:
        """Cevaba eklenecek atıf satırı. Sayfa PDF indeksi + 1 (basılı sayfa)."""
        return f"{self.vendor} {self.model}, s.{self.page + 1}"


@dataclass
class AramaSonucu:
    sonuclar: list[Sonuc]
    yol: str                  # "exact" | "hibrit"
    arama_sorgusu: str        # gerçekten aranan metin (çevrilmiş olabilir)
    cevrildi: bool
    en_iyi_benzerlik: float = 1.0   # ham kosinüs — reddetme eşiği için

    def alakali_mi(self) -> bool:
        """Bağlam soruyla gerçekten ilgili mi?

        Reddetme kararı modele BIRAKILMIYOR. Prompt'a "bilmiyorsan bilmiyorum
        de" yazmak yetersiz kaldı: format talimatı ağır basınca model alakasız
        chunk'lardan cevap uydurdu (fiyat sorusuna IGBT overload cevabı).
        Brief'te reddetme hedefi 0.95 değil 1.00 — enerjili ekipmanda emin
        tonda yanlış cevap fiziksel risk. Bu yüzden karar deterministik.
        """
        return self.yol == "exact" or self.en_iyi_benzerlik >= config.ALAKA_ESIGI


class Retriever:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        ids, M = db.load_embeddings(conn)
        self.ids = ids
        if len(ids):
            self.M = M / np.linalg.norm(M, axis=1, keepdims=True)
        else:
            self.M = M
        self.kodlar = db.known_fault_codes(conn)
        self.desenler = {
            marka: re.compile(desen, re.IGNORECASE)
            for marka, desen in config.FAULT_CODE_PATTERNS.items()
        }

    # --- 1. yol: birebir kod eşleşmesi -----------------------------------
    def kod_adaylari(self, sorgu: str) -> list[tuple[str, str]]:
        """[(marka, kod)] — regex adayları, gerçek kod kümesiyle doğrulanmış."""
        bulunan: list[tuple[str, str]] = []
        for marka, desen in self.desenler.items():
            mevcut = self.kodlar.get(marka, set())
            for m in desen.finditer(sorgu):
                aday = (m.group(1) if m.groups() else m.group(0)).upper()
                if aday in mevcut:
                    bulunan.append((marka, aday))
                elif aday.lstrip("0") in mevcut:      # Danfoss "007" -> "7"
                    bulunan.append((marka, aday.lstrip("0")))
        return bulunan

    def kod_ara(self, sorgu: str) -> list[Sonuc]:
        eslesmeler = self.kod_adaylari(sorgu)
        if not eslesmeler:
            return []
        kosullar = " OR ".join(["(d.vendor = ? AND c.fault_code = ?)"] * len(eslesmeler))
        parametreler = [x for cift in eslesmeler for x in cift]
        satirlar = self.conn.execute(
            f"SELECT c.id, d.vendor, d.model, c.fault_code, c.severity, c.page, c.content "
            f"FROM chunks c JOIN documents d ON d.id = c.doc_id WHERE {kosullar}",
            parametreler,
        ).fetchall()
        return [Sonuc(r["id"], r["vendor"], r["model"], r["fault_code"],
                      r["severity"], r["page"], r["content"], 1.0) for r in satirlar]

    # --- 2. yol: BM25 -----------------------------------------------------
    @staticmethod
    def _fts_sorgusu(sorgu: str) -> str:
        """FTS5 MATCH sözdizimi için güvenli sorgu.

        Ham kullanıcı metni doğrudan verilemez: tırnak, tire, yıldız ve iki
        nokta FTS5'te operatördür ve sözdizimi hatası fırlatır.
        """
        kelimeler = [k for k in _KELIME.findall(sorgu) if len(k) > 1]
        return " OR ".join(f'"{k}"' for k in kelimeler)

    def bm25_ara(self, sorgu: str, n: int = ADAY_SAYISI) -> list[int]:
        fts = self._fts_sorgusu(sorgu)
        if not fts:
            return []
        try:
            satirlar = self.conn.execute(
                "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? "
                "ORDER BY bm25(chunks_fts) LIMIT ?", (fts, n)
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [r["rowid"] for r in satirlar]

    # --- 3. yol: vektör ---------------------------------------------------
    def vektor_ara(self, vektor: np.ndarray,
                   n: int = ADAY_SAYISI) -> tuple[list[int], float]:
        """(sıralı chunk id'leri, en yüksek kosinüs benzerliği)."""
        if not len(self.ids):
            return [], 0.0
        q = np.asarray(vektor, dtype=np.float32)
        q = q / np.linalg.norm(q)
        skorlar = self.M @ q
        sira = np.argsort(-skorlar)[:n]
        return [self.ids[i] for i in sira], float(skorlar[sira[0]])

    # --- füzyon -----------------------------------------------------------
    @staticmethod
    def _rrf(*siralamalar: list[int]) -> dict[int, float]:
        """Reciprocal rank fusion: skorlar farklı ölçeklerde olduğu için
        değerler değil SIRALAMALAR birleştirilir."""
        skor: dict[int, float] = {}
        for sira in siralamalar:
            for konum, cid in enumerate(sira):
                skor[cid] = skor.get(cid, 0.0) + 1.0 / (RRF_K + konum + 1)
        return skor

    def _sonuclari_getir(self, ids: list[int], skorlar: dict[int, float]) -> list[Sonuc]:
        if not ids:
            return []
        yer = ",".join("?" * len(ids))
        satirlar = self.conn.execute(
            f"SELECT c.id, d.vendor, d.model, c.fault_code, c.severity, c.page, c.content "
            f"FROM chunks c JOIN documents d ON d.id = c.doc_id WHERE c.id IN ({yer})",
            ids,
        ).fetchall()
        sonuc = [Sonuc(r["id"], r["vendor"], r["model"], r["fault_code"],
                       r["severity"], r["page"], r["content"], skorlar[r["id"]])
                 for r in satirlar]
        sonuc.sort(key=lambda s: -s.skor)
        return sonuc

    # --- dış arayüz -------------------------------------------------------
    def ara(self, arama_sorgusu: str, vektor: np.ndarray | None,
            k: int = config.TOP_K, cevrildi: bool = False) -> AramaSonucu:
        exact = self.kod_ara(arama_sorgusu)
        if exact:
            return AramaSonucu(exact[:k], "exact", arama_sorgusu, cevrildi)

        bm25 = self.bm25_ara(arama_sorgusu)
        vek, benzerlik = self.vektor_ara(vektor) if vektor is not None else ([], 0.0)
        skorlar = self._rrf(bm25, vek)
        en_iyi = sorted(skorlar, key=lambda c: -skorlar[c])[:k]
        return AramaSonucu(self._sonuclari_getir(en_iyi, skorlar),
                           "hibrit", arama_sorgusu, cevrildi, benzerlik)
