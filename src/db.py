"""SQLite şeması ve veri erişimi.

Vektörler BLOB olarak saklanır (numpy float32). FTS5 sanal tablosu hibrit
aramanın lexical yarısını sağlar ve tetikleyicilerle chunks tablosuyla senkron
tutulur — aksi halde external-content FTS tablosu boş kalır.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY,
    vendor      TEXT NOT NULL,
    model       TEXT NOT NULL,
    source_file TEXT NOT NULL UNIQUE,
    version     TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    id         INTEGER PRIMARY KEY,
    doc_id     INTEGER NOT NULL REFERENCES documents(id),
    fault_code TEXT,              -- üreticinin kendi kodu: F30002 | 2310 | 29
    severity   TEXT,              -- fault | alarm | both  (aciliyet ayrımı)
    section    TEXT,
    page       INTEGER NOT NULL,  -- kaynak atfı için zorunlu
    content    TEXT NOT NULL,
    embedding  BLOB
);

CREATE INDEX IF NOT EXISTS idx_chunks_fault_code ON chunks(fault_code);
CREATE INDEX IF NOT EXISTS idx_chunks_doc        ON chunks(doc_id);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content, content='chunks', content_rowid='id'
);

-- FTS tablosunu chunks ile senkron tut
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.id, old.content);
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
END;
"""


@dataclass
class Chunk:
    """Veritabanına yazılmaya hazır tek bir parça."""
    fault_code: str | None
    severity: str | None
    section: str
    page: int
    content: str


def connect(path: Path | str) -> sqlite3.Connection:
    """Veritabanı bağlantısı açar.

    check_same_thread=False ZORUNLU: Streamlit bağlantıyı @st.cache_resource
    içinde bir thread'de oluşturur, ardından her etkileşimi başka bir thread'de
    çalıştırır. Varsayılan davranışta sqlite bağlantıyı oluşturan thread'e
    kilitler ve ikinci sorguda ProgrammingError fırlatır.

    Güvenli, çünkü uygulama yolunda yalnızca OKUMA var (eşzamanlı okuma sqlite'ta
    sorunsuz); tek yazan yer ingest ve o tek thread'de çalışıyor.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_document(conn, vendor: str, model: str, source_file: str,
                    version: str | None = None) -> int:
    """Dokümanı kaydeder; zaten varsa eski chunk'larını siler ve id'sini döner."""
    row = conn.execute(
        "SELECT id FROM documents WHERE source_file = ?", (source_file,)
    ).fetchone()
    if row:
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (row["id"],))
        conn.commit()
        return row["id"]

    cur = conn.execute(
        "INSERT INTO documents (vendor, model, source_file, version) VALUES (?,?,?,?)",
        (vendor, model, source_file, version),
    )
    conn.commit()
    return cur.lastrowid


def insert_chunks(conn, doc_id: int, chunks: list[Chunk]) -> int:
    conn.executemany(
        "INSERT INTO chunks (doc_id, fault_code, severity, section, page, content) "
        "VALUES (?,?,?,?,?,?)",
        [(doc_id, c.fault_code, c.severity, c.section, c.page, c.content)
         for c in chunks],
    )
    conn.commit()
    return len(chunks)


def set_embeddings(conn, ids: list[int], vectors: np.ndarray) -> None:
    """Embedding'leri toplu yazar. vectors: (n, dim) float32."""
    v = np.asarray(vectors, dtype=np.float32)
    conn.executemany(
        "UPDATE chunks SET embedding = ? WHERE id = ?",
        [(v[i].tobytes(), ids[i]) for i in range(len(ids))],
    )
    conn.commit()


def load_embeddings(conn) -> tuple[list[int], np.ndarray]:
    """Tüm vektörleri belleğe alır — 1.500 chunk için ~6 MB, tek seferlik."""
    rows = conn.execute(
        "SELECT id, embedding FROM chunks WHERE embedding IS NOT NULL ORDER BY id"
    ).fetchall()
    if not rows:
        return [], np.empty((0, 0), dtype=np.float32)
    ids = [r["id"] for r in rows]
    mat = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
    return ids, mat


def known_fault_codes(conn) -> dict[str, set[str]]:
    """Marka -> var olan kodlar. Hibrit aramada regex adaylarını doğrulamak için.

    Regex tek başına yetersiz (ABB'nin onaltılık biçimi '2024' gibi dizileri de
    yakalıyor); karar bu kümeye bakılarak veriliyor.
    """
    rows = conn.execute(
        "SELECT d.vendor, c.fault_code FROM chunks c "
        "JOIN documents d ON d.id = c.doc_id WHERE c.fault_code IS NOT NULL"
    ).fetchall()
    out: dict[str, set[str]] = {}
    for r in rows:
        out.setdefault(r["vendor"], set()).add(r["fault_code"])
    return out
