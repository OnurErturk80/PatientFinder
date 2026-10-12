"""Access (VERİTABANI tablosu) -> kanonik model eşlemesi.

Sütun adları şema raporundan alınmıştır (108 dosya, tek ana tablo, satır = bir tedavi).
Raporda olmayan bilgi (tank/kanister, oosit/sperm dondurma) Access'te yoktur; uydurulmaz.
"""
from __future__ import annotations

import datetime as dt
import os
import re
from collections import Counter

from .normalize import norm

TABLE = "VERİTABANI"
MONTHS = {"ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5, "haziran": 6, "temmuz": 7,
          "agustos": 8, "eylul": 9, "ekim": 10, "kasim": 11, "aralik": 12}

C = dict(
    row_id="Kimlik", file_no="DOSYA NO", last="SOYADI", first="ADI", spouse="EŞİNİN ADI",
    birth="DOĞUM TARİHİ", protocol="TEDAVİ PROTOKOLÜ", opu="OPU TARİHİ", oocytes="TOPLANAN OOSİT",
    mii="MATÜR (MII)", method="FERTİLİZASYON YÖNTEMİ", pn2="NORMAL FERTİLİZASYON (2PN)",
    stage="EMBRİYO TRANSFER AŞAMASI", transfer_date="TRANSFER TARİHİ",
    transfer_count="TRANSFER EDİLEN EMBRİYO SAYISI", e1c="EMBRİYO1 HÜCRE/AŞAMA", e1q="EMBRİYO1 KALİTE",
    e2c="EMBRİYO2 HÜCRE/AŞAMA", e2q="EMBRİYO2 KALİTE", frozen="DONDURULAN EMBRİYO SAYISI",
    freeze_stage="EMBRİYO DONDURMA AŞAMASI", thawed="ÇÖZDÜRÜLEN EMBRİYO SAYISI",
    bhcg1="BİRİNCİ BHCG", bhcg2="İKİNCİ BHCG", fhb="İLK USG FHB KESE", abort="ABORT", missed="MISSED",
    ectopic="EKTOPİK", live="CANLI DOĞUM SAYISI", dead="ÖLÜ DOĞUM SAYISI",
)


def to_int(v):
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def to_text(v):
    if v is None:
        return None
    s = str(v).replace("\xa0", " ").strip()
    return s or None


def to_date(v):
    """datetime/date/metin -> 'YYYY-MM-DD'. Makul olmayan yıl (2000-2100 dışı) None."""
    if v is None or v == "":
        return None
    d = None
    if isinstance(v, dt.datetime):
        d = v.date()
    elif isinstance(v, dt.date):
        d = v
    else:
        s = str(v).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y", "%m/%d/%y %H:%M:%S",
                    "%m/%d/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                d = dt.datetime.strptime(s, fmt).date()
                break
            except ValueError:
                continue
    return d.isoformat() if d and 2000 <= d.year <= 2100 else None


def month_from_filename(name: str):
    base = norm(os.path.splitext(os.path.basename(name))[0])
    for k, n in MONTHS.items():
        if k in base:
            return n
    return None


def year_from_path(path: str):
    """En yakın klasör adından 20xx yılı (ör. 'HASTA KAYITLARI/2023/MART.accdb')."""
    parts = os.path.normpath(path).split(os.sep)[:-1]
    for part in reversed(parts):
        m = re.search(r"(?<!\d)(20\d\d)(?!\d)", part)
        if m:
            return int(m.group(1))
    return None


def _label(v):
    return to_text(v)


def treatment_type(row) -> str:
    """Tedavi türü Access'te ayrı sütun değildir; TÜRETİLİR (arayüzde bu not edilir)."""
    if (to_int(row.get(C["thawed"])) or 0) > 0:
        return "FET (çözdürme)"
    if to_date(row.get(C["opu"])) or to_int(row.get(C["oocytes"])) is not None:
        return to_text(row.get(C["method"])) or "OPU (yöntem belirtilmemiş)"
    if to_date(row.get(C["transfer_date"])):
        return "Transfer"
    return "İşlem bilgisi yok"


def outcome_text(row):
    """Yorumlamadan, kayıttaki ham değerleri gösterir (kod anlamları bilinmediği için)."""
    parts = []
    b1, b2 = row.get(C["bhcg1"]), row.get(C["bhcg2"])
    if b1 is not None or b2 is not None:
        parts.append("β-hCG: " + " / ".join("?" if x is None else f"{x:g}" if isinstance(x, (int, float)) else str(x)
                                            for x in (b1, b2)))
    fhb = to_int(row.get(C["fhb"]))
    if fhb is not None:
        parts.append(f"USG FHB/kese: {fhb}")
    for key, lab in (("abort", "Abort"), ("missed", "Missed"), ("ectopic", "Ektopik")):
        t = _label(row.get(C[key]))
        if t:
            parts.append(f"{lab}: {t}")
    live, dead = to_int(row.get(C["live"])), to_int(row.get(C["dead"]))
    if live is not None:
        parts.append(f"Canlı doğum: {live}")
    if dead:
        parts.append(f"Ölü doğum: {dead}")
    return "; ".join(parts) or None


def map_rows(path: str, rows: list[dict]):
    """-> (döngüler, olaylar). Adı ve soyadı boş satırlar atlanır."""
    fm = month_from_filename(path)
    year = year_from_path(path)
    if year is None:  # klasörde yıl yoksa satırlardaki tarihlerin en sık yılı
        ys = Counter(int(d[:4]) for r in rows for d in (to_date(r.get(C["opu"])), to_date(r.get(C["transfer_date"]))) if d)
        year = ys.most_common(1)[0][0] if ys else None
    month = f"{year}-{fm:02d}" if year and fm else None
    cycles, events = [], []
    for r in rows:
        first, last = to_text(r.get(C["first"])), to_text(r.get(C["last"]))
        if not (first or last):
            continue
        opu, tdate = to_date(r.get(C["opu"])), to_date(r.get(C["transfer_date"]))
        pno = to_text(r.get(C["file_no"]))
        ref = f"Kimlik {to_text(r.get(C['row_id'])) or '?'}"
        base = dict(src_ref=ref, month=month, protocol_no=pno, f_first=first, f_last=last,
                    m_first=to_text(r.get(C["spouse"])), m_last=last)
        key_date = opu or tdate
        ident = f"{pno}|{norm((first or '') + ' ' + (last or ''))}|{key_date}" if key_date else None
        base["ident"] = ident
        q = [f"E{i}: " + " ".join(x for x in (to_text(r.get(C[f"e{i}q"])), f"({to_text(r.get(C[f'e{i}c']))})"
                                              if to_text(r.get(C[f"e{i}c"])) else None) if x)
             for i in (1, 2) if to_text(r.get(C[f"e{i}q"])) or to_text(r.get(C[f"e{i}c"]))]
        cycles.append({**base, "cycle_date": key_date, "treatment_type": treatment_type(r),
                       "protocol": to_text(r.get(C["protocol"])), "birth_date": to_date(r.get(C["birth"])),
                       "oocytes": to_int(r.get(C["oocytes"])), "mii": to_int(r.get(C["mii"])),
                       "fertilized": to_int(r.get(C["pn2"])), "transfer_date": tdate,
                       "transfer_day": to_text(r.get(C["stage"])),
                       "transfer_count": to_int(r.get(C["transfer_count"])),
                       "transfer_quality": "; ".join(q) or None, "outcome": outcome_text(r)})
        fz, th = to_int(r.get(C["frozen"])), to_int(r.get(C["thawed"]))
        if fz:
            events.append({**base, "event_date": opu or tdate, "kind": "freeze", "sample_type": "embryo",
                           "count": fz, "day": to_text(r.get(C["freeze_stage"]))})
        if th:
            events.append({**base, "event_date": tdate or opu, "kind": "thaw", "sample_type": "embryo", "count": th})
    return cycles, events


def make_reader(backend: str = "auto"):
    from .access_source import make_source  # m0 ile aynı salt okunur arka uçlar

    def reader(path: str):
        src = make_source(path, backend)
        try:
            return map_rows(path, list(src.read_table(TABLE)))
        finally:
            src.close()

    return reader
