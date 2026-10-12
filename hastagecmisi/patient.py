"""Hasta sayfası verisi: özet kartı, zaman çizelgesi, envanter."""
from __future__ import annotations

from .dedupe import latest_per_ident
from .inventory import for_patient
from .matching import patient_keys, row_key, similar_candidates

NA = "bilgi yok"


def timeline(conn, keys: set[str]) -> list[dict]:
    rows = []
    for r in conn.execute("SELECT c.*, f.path, f.mtime FROM cycle c JOIN source_file f ON f.id=c.file_id "
                          "ORDER BY COALESCE(c.cycle_date, c.month), c.id"):
        if row_key(r) in keys:
            d = dict(r)
            d["source"] = {"file": d.pop("path"), "ref": d["src_ref"]}
            rows.append(d)
    rows = latest_per_ident(rows, lambda c: c["ident"] or None, compare=())
    return [{k: (v if v not in (None, "") else None) for k, v in d.items()} for d in rows]


def patient_view(conn, key: str) -> dict:
    keys = patient_keys(conn, key)
    cycles = timeline(conn, keys)
    months = sorted(c["month"] for c in cycles if c["month"])
    inv = for_patient(conn, key)
    header = [f"{len(cycles)} tedavi" + (f" · ilk kayıt {months[0]} · son kayıt {months[-1]}" if months else "")]
    return {"key": key, "merged_keys": sorted(keys), "header": header, "cycles": cycles,
            "inventory": inv["inventory"], "inventory_lines": inv["lines"], "note": inv["note"],
            "similar": similar_candidates(conn, key), "na": NA}
