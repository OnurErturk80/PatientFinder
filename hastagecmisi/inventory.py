"""Kalan dondurulmuş örnek hesabı. Klinik karar vermez, kayıtları derler.

kalan = dondurulan − (max(çözülen, kullanılan+atılan) + devredilen)
Çelişki veya eksiklikte sonuç 'Doğrulanmalı' ile işaretlenir.
"""
from __future__ import annotations

from .matching import patient_keys

SAMPLE_TR = {"embryo": "embriyo", "oocyte": "oosit", "sperm": "sperm"}
OUT_KINDS = ("thaw", "use", "discard", "transfer_out")


def events_for(conn, keys: set[str]) -> list[dict]:
    rows = []
    for r in conn.execute("SELECT e.*, f.path FROM sample_event e JOIN source_file f ON f.id=e.file_id "
                          "ORDER BY COALESCE(e.event_date, e.month), e.id"):
        if f"{r['f_norm']}|{r['m_norm']}" in keys:
            rows.append(dict(r))
    return rows


def compute(events: list[dict]) -> dict:
    out = {}
    for st in SAMPLE_TR:
        evs = [e for e in events if e["sample_type"] == st]
        if not evs:
            continue
        frozen = sum(e["count"] or 0 for e in evs if e["kind"] == "freeze")
        outs = {k: sum(e["count"] or 0 for e in evs if e["kind"] == k) for k in OUT_KINDS}
        # Çözülen bir örnek sonra kullanılır/atılır: aynı örneği iki kez düşmemek için
        # çözme ile (kullanım+atılma) arasında büyük olan alınır; devredilen ayrıca düşer.
        used = outs["use"] + outs["discard"]
        consumed = max(outs["thaw"], used) + outs["transfer_out"]
        remaining = frozen - consumed
        warnings = []
        if any(e["count"] is None for e in evs):
            warnings.append("Bazı kayıtlarda adet boş.")
        if not any(e["kind"] == "freeze" for e in evs):
            warnings.append("Dondurma kaydı yok, yalnızca çözme/kullanım kaydı var.")
        if remaining < 0:
            warnings.append("Çözülen/kullanılan sayısı dondurulandan fazla.")
        if outs["thaw"] and not used:
            warnings.append("Çözme var ama kullanım/atılma kaydı yok.")
        if outs["thaw"] and used and outs["thaw"] != used:
            warnings.append("Çözülen sayısı ile kullanılan+atılan sayısı tutmuyor.")
        out[st] = {"type": st, "type_tr": SAMPLE_TR[st], "frozen": frozen, **outs,
                   "remaining": max(remaining, 0) if not warnings else remaining,
                   "verify": bool(warnings), "warnings": warnings,
                   "sources": [{"id": e["id"], "file": e["path"], "ref": e["src_ref"], "kind": e["kind"],
                                "count": e["count"], "date": e["event_date"] or e["month"]} for e in evs]}
    return out


def summary_text(inv: dict) -> list[str]:
    lines = []
    for st, d in inv.items():
        if d["verify"]:
            lines.append(f"Doğrulanmalı ({d['type_tr']}): " + " ".join(d["warnings"]))
        elif d["remaining"] > 0:
            lines.append(f"Kayıtlara göre {d['remaining']} {d['type_tr']} kalmış görünüyor.")
        else:
            lines.append(f"Kayıtlara göre kalan {d['type_tr']} yok.")
    return lines or ["Dondurma kaydı bulunamadı."]


def for_patient(conn, key: str) -> dict:
    keys = patient_keys(conn, key)
    ev = events_for(conn, keys)
    inv = compute(ev)
    return {"inventory": inv, "lines": summary_text(inv),
            "note": "Fiziksel doğrulama için tank haritasına bakın."}
