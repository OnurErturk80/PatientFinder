"""SQLite indeksi (türetilmiş kopya) ve artımlı içe aktarma çerçevesi.

Kaynak doğruluk Access dosyalarıdır. Bu veritabanı silinirse yeniden üretilebilir.
Eşleme katmanı (Access sütunu -> kanonik alan) şema raporundan sonra yazılacak
bir 'okuyucu' (reader) işlevidir; bu modül ondan bağımsızdır.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from typing import Callable, Iterable

from .normalize import full_name

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_file(
  id INTEGER PRIMARY KEY, path TEXT UNIQUE, size INTEGER, mtime REAL,
  sha256 TEXT, imported_at REAL);
-- Tedavi döngüsü. Kayıtta olmayan alan NULL kalır (uydurulmaz).
CREATE TABLE IF NOT EXISTS cycle(
  id INTEGER PRIMARY KEY, file_id INTEGER REFERENCES source_file(id) ON DELETE CASCADE,
  src_ref TEXT, ident TEXT, month TEXT, cycle_date TEXT, treatment_type TEXT, protocol TEXT,
  protocol_no TEXT, f_first TEXT, f_last TEXT, m_first TEXT, m_last TEXT, birth_date TEXT,
  f_norm TEXT, m_norm TEXT,
  oocytes INTEGER, mii INTEGER, fertilized INTEGER, embryos INTEGER, embryo_quality TEXT,
  transfer_date TEXT, transfer_day TEXT, transfer_count INTEGER, transfer_quality TEXT,
  outcome TEXT);
-- Dondurma / çözme / kullanım / atılma olayları.
CREATE TABLE IF NOT EXISTS sample_event(
  id INTEGER PRIMARY KEY, file_id INTEGER REFERENCES source_file(id) ON DELETE CASCADE,
  src_ref TEXT, ident TEXT, month TEXT, event_date TEXT,
  kind TEXT CHECK(kind IN ('freeze','thaw','use','discard','transfer_out')),
  sample_type TEXT CHECK(sample_type IN ('embryo','oocyte','sperm')),
  count INTEGER, quality TEXT, day TEXT, location TEXT, cycle_ref TEXT,
  protocol_no TEXT, f_first TEXT, f_last TEXT, m_first TEXT, m_last TEXT,
  f_norm TEXT, m_norm TEXT);
-- Kullanıcı kararları: iki kişi/çift anahtarı birleştirilsin mi? (geri alınabilir)
CREATE TABLE IF NOT EXISTS decision(
  key_a TEXT, key_b TEXT, verdict TEXT CHECK(verdict IN ('merge','separate')),
  decided_at REAL, PRIMARY KEY(key_a, key_b));
CREATE INDEX IF NOT EXISTS ix_cycle_f ON cycle(f_norm); CREATE INDEX IF NOT EXISTS ix_cycle_m ON cycle(m_norm);
CREATE INDEX IF NOT EXISTS ix_ev_f ON sample_event(f_norm); CREATE INDEX IF NOT EXISTS ix_ev_m ON sample_event(m_norm);
"""

CYCLE_FIELDS = ["src_ref", "ident", "month", "cycle_date", "treatment_type", "protocol", "protocol_no", "f_first",
                "f_last", "m_first", "m_last", "birth_date", "oocytes", "mii", "fertilized", "embryos",
                "embryo_quality", "transfer_date", "transfer_day", "transfer_count", "transfer_quality", "outcome"]
EVENT_FIELDS = ["src_ref", "ident", "month", "event_date", "kind", "sample_type", "count", "quality", "day",
                "location", "cycle_ref", "protocol_no", "f_first", "f_last", "m_first", "m_last"]

# Okuyucu: dosya yolu -> (döngü sözlükleri, olay sözlükleri)
Reader = Callable[[str], tuple[Iterable[dict], Iterable[dict]]]


def connect(path: str = ":memory:") -> sqlite3.Connection:
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:  # yalnızca okuma
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _insert(conn, table, fields, file_id, row):
    d = {k: row.get(k) for k in fields}
    d["f_norm"] = full_name(d["f_first"], d["f_last"])
    d["m_norm"] = full_name(d["m_first"], d["m_last"])
    cols = ["file_id"] + fields + ["f_norm", "m_norm"]
    conn.execute(f"INSERT INTO {table}({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                 [file_id] + [d[k] for k in fields] + [d["f_norm"], d["m_norm"]])


def import_file(conn, path: str, reader: Reader) -> str:
    """'imported' | 'skipped' | 'failed:<hata türü>'. Dosya başına tek transaction."""
    st = os.stat(path)
    sha = _sha256(path)
    row = conn.execute("SELECT id, sha256 FROM source_file WHERE path=?", (path,)).fetchone()
    if row and row["sha256"] == sha:
        return "skipped"
    try:
        with conn:  # hata olursa bu dosyanın tüm değişiklikleri geri alınır
            if row:
                conn.execute("DELETE FROM source_file WHERE id=?", (row["id"],))
            cur = conn.execute("INSERT INTO source_file(path,size,mtime,sha256,imported_at) VALUES(?,?,?,?,?)",
                               (path, st.st_size, st.st_mtime, sha, time.time()))
            fid = cur.lastrowid
            cycles, events = reader(path)
            for c in cycles:
                _insert(conn, "cycle", CYCLE_FIELDS, fid, c)
            for e in events:
                _insert(conn, "sample_event", EVENT_FIELDS, fid, e)
        return "imported"
    except Exception as ex:  # hata iletisine kayıt içeriği girmesin
        return f"failed:{type(ex).__name__}"


def scan_folder(conn, folder: str, reader: Reader, exts=(".accdb", ".mdb")) -> dict[str, str]:
    result = {}
    for root, _, files in os.walk(folder):
        for f in sorted(files):
            if f.lower().endswith(exts) and not f.startswith("~"):
                p = os.path.join(root, f)
                result[p] = import_file(conn, p, reader)
    return result
