"""PDF → chunk → embedding → SQLite.

Çalıştırma:
    .venv/bin/python -m src.ingest              # ayrıştır + embed
    .venv/bin/python -m src.ingest --no-embed   # yalnızca ayrıştır (hızlı)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src import db
from src.parsers import parse_abb, parse_danfoss, parse_siemens

# (ayrıştırıcı, marka, model, dosya, sürüm)
MANUELLER = [
    (parse_danfoss, "Danfoss", "VLT AutomationDrive FC 302",
     "danfoss_fc302_programming_guide.pdf", "MG33MO02"),
    (parse_siemens, "Siemens", "SINAMICS G120C",
     "siemens_g120c_list_manual.pdf", "LH13 04/2014"),
    (parse_abb, "ABB", "ACS580",
     "abb_acs580_firmware_manual.pdf", "EN_ACS580_FW_J"),
]

BATCH = 32


def _embedding_istemcisi():
    from foundry_local_sdk import Configuration, FoundryLocalManager

    FoundryLocalManager.initialize(Configuration(
        app_name=config.APP_NAME,
        model_cache_dir=str(config.MODEL_CACHE_DIR),
    ))
    model = FoundryLocalManager.instance.catalog.get_model(config.EMBEDDING_MODEL)
    if model is None:
        raise SystemExit(f"embedding modeli bulunamadı: {config.EMBEDDING_MODEL}")
    model.load()
    return model.get_embedding_client()


def ayristir(conn, manuals_dir: Path) -> dict[str, int]:
    """Üç manueli ayrıştırıp veritabanına yazar. Marka -> chunk sayısı."""
    ozet: dict[str, int] = {}
    for parser, marka, model, dosya, surum in MANUELLER:
        yol = manuals_dir / dosya
        if not yol.exists():
            print(f"  ATLANDI {marka}: {dosya} bulunamadı")
            continue

        t = time.perf_counter()
        chunks = parser(yol)
        doc_id = db.upsert_document(conn, marka, model, dosya, surum)
        n = db.insert_chunks(conn, doc_id, chunks)
        ozet[marka] = n
        print(f"  {marka:8s} {n:4d} chunk  ({time.perf_counter()-t:.1f} sn)")
    return ozet


def embedle(conn, istemci) -> int:
    """Embedding'i olmayan chunk'lar için vektör üretir."""
    satirlar = conn.execute(
        "SELECT id, content FROM chunks WHERE embedding IS NULL ORDER BY id"
    ).fetchall()
    if not satirlar:
        print("  tüm chunk'ların embedding'i mevcut")
        return 0

    toplam = len(satirlar)
    print(f"  {toplam} chunk embed ediliyor ({BATCH}'lik gruplar)...")
    t = time.perf_counter()

    for bas in range(0, toplam, BATCH):
        grup = satirlar[bas:bas + BATCH]
        yanit = istemci.generate_embeddings([r["content"] for r in grup])
        vektorler = np.array([d.embedding for d in yanit.data], dtype=np.float32)
        db.set_embeddings(conn, [r["id"] for r in grup], vektorler)
        print(f"    {min(bas+BATCH, toplam):4d}/{toplam}", end="\r", flush=True)

    sure = time.perf_counter() - t
    print(f"\n  tamam — {sure:.1f} sn ({toplam/sure:.1f} chunk/sn)")
    return toplam


def main() -> None:
    ap = argparse.ArgumentParser(description="USTA bilgi tabanı kurulumu")
    ap.add_argument("--manuals", type=Path, default=config.MANUALS_DIR)
    ap.add_argument("--db", type=Path, default=config.DB_PATH)
    ap.add_argument("--no-embed", action="store_true", help="yalnızca ayrıştır")
    a = ap.parse_args()

    conn = db.connect(a.db)
    db.init_schema(conn)

    print(f"\nAyrıştırma — {a.manuals}")
    ozet = ayristir(conn, a.manuals)

    if not a.no_embed:
        print("\nEmbedding")
        embedle(conn, _embedding_istemcisi())

    kodlar = db.known_fault_codes(conn)
    toplam = conn.execute("SELECT count(*) c FROM chunks").fetchone()["c"]
    print(f"\nBilgi tabanı hazır: {a.db}")
    print(f"  chunk      : {toplam}")
    print(f"  hata kodu  : { {k: len(v) for k, v in kodlar.items()} }")
    conn.close()


if __name__ == "__main__":
    main()
