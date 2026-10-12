"""İsteğe bağlı değer profili (--profile). Kimlik sayılabilecek HİÇBİR değer yazılmaz:
yalnızca klinik kod sütunlarının (izinli liste) değer dağılımı, <5 kez geçen değerler gizlenir,
ve sayısal sütunlar için aralık/doluluk istatistiği. Ad, soyad, notlar, tarih değerleri yazılmaz."""
from __future__ import annotations

import os
import time
from collections import Counter, defaultdict

from .access_source import make_source

TABLE = "VERİTABANI"
CODE_COLS = ["TEDAVİ PROTOKOLÜ", "FERTİLİZASYON YÖNTEMİ", "EMBRİYO TRANSFER AŞAMASI", "EMBRİYO DONDURMA AŞAMASI",
             "ABORT", "MISSED", "EKTOPİK", "SPERM KAYNAĞI", "GENEL OOSİT KALİTESİ", "EMBRİYO1 KALİTE",
             "EMBRİYO1 HÜCRE/AŞAMA", "DENEY/KONTROL GRUBU", "BEBEK1 CİNSİYET", "KROMOZOM ANOMALİSİ"]
NUM_COLS = ["DONDURULAN EMBRİYO SAYISI", "ÇÖZDÜRÜLEN EMBRİYO SAYISI", "ÇÖZDÜRME SONRASI VİABİLİTE",
            "TRANSFER EDİLEN EMBRİYO SAYISI", "TOPLANAN OOSİT", "BİRİNCİ BHCG", "İLK USG FHB KESE",
            "CANLI DOĞUM SAYISI", "ÖLÜ DOĞUM SAYISI"]
MIN_COUNT = 5


def _norm(s):
    return " ".join(str(s).split()).lower() if s is not None else ""


def _year(v):
    for attr in ("year",):
        if hasattr(v, attr):
            return v.year
    s = str(v or "")
    for tok in s.replace("/", "-").replace(".", "-").split():
        for part in tok.split("-"):
            if len(part) == 4 and part.isdigit():
                return int(part)
    return None


def write_profile(paths: list[str], folder: str, out_path: str, backend: str = "auto") -> None:
    codes = {c: Counter() for c in CODE_COLS}
    nums = {c: {"dolu": 0, "toplam": 0, "min": None, "max": None, "sifir": 0} for c in NUM_COLS}
    per_file_years = []
    fileno_files = defaultdict(set)    # DOSYA NO -> dosya indeksleri
    fileno_names = defaultdict(set)    # DOSYA NO -> ad-soyad kümeleri (yazılmaz, yalnızca sayılır)
    skipped = []
    for i, p in enumerate(paths):
        try:
            src = make_source(p, backend)
            rows = list(src.read_table(TABLE))
            src.close()
        except Exception as e:
            skipped.append(f"{os.path.relpath(p, folder)} ({type(e).__name__})")
            continue
        years = Counter()
        for r in rows:
            for c in CODE_COLS:
                v = r.get(c)
                if v not in (None, ""):
                    codes[c][str(v).strip()] += 1
            for c in NUM_COLS:
                n = nums[c]
                n["toplam"] += 1
                v = r.get(c)
                if isinstance(v, (int, float)):
                    n["dolu"] += 1
                    n["sifir"] += v == 0
                    n["min"] = v if n["min"] is None else min(n["min"], v)
                    n["max"] = v if n["max"] is None else max(n["max"], v)
            y = _year(r.get("OPU TARİHİ")) or _year(r.get("TRANSFER TARİHİ"))
            if y:
                years[y] += 1
            no = r.get("DOSYA NO")
            if no is not None:
                fileno_files[no].add(i)
                fileno_names[no].add(_norm(r.get("ADI")) + "|" + _norm(r.get("SOYADI")))
        per_file_years.append((os.path.relpath(p, folder), dict(sorted(years.items()))))
    multi = [k for k, v in fileno_files.items() if len(v) > 1]
    same = sum(1 for k in multi if len(fileno_names[k]) == 1)
    L = ["# Değer profili (kimlik değeri içermez)", "", f"- Oluşturulma: {time.strftime('%Y-%m-%d %H:%M')}",
         f"- Okunamayan dosya: {len(skipped)}" + (": " + ", ".join(skipped) if skipped else ""), "",
         "## DOSYA NO kalıcı mı?", "",
         f"- Farklı DOSYA NO sayısı: {len(fileno_files)}",
         f"- Birden çok dosyada geçen DOSYA NO: {len(multi)}",
         f"- Bunlardan her yerde aynı ad-soyada ait olanlar: {same} (oran %{100 * same // max(len(multi), 1)})", "",
         "## Kod sütunları (≥5 kez geçen değerler)", ""]
    for c, cnt in codes.items():
        shown = [(v, n) for v, n in cnt.most_common() if n >= MIN_COUNT]
        hidden = sum(n for v, n in cnt.items() if n < MIN_COUNT)
        L += [f"### {c}", ""] + [f"- `{v}`: {n}" for v, n in shown[:40]] + \
             [f"- (diğer/nadir değerler): {hidden}" if hidden else "", ""]
    L += ["## Sayısal sütunlar", "", "| Sütun | Satır | Dolu | Sıfır | Min | Maks |", "|---|---:|---:|---:|---:|---:|"]
    for c, n in nums.items():
        L.append(f"| {c} | {n['toplam']} | {n['dolu']} | {n['sifir']} | {n['min']} | {n['max']} |")
    L += ["", "## Dosya başına işlem yılı dağılımı (OPU/transfer tarihinden; yıl: satır sayısı)", ""]
    L += [f"- {rel}: {yrs}" for rel, yrs in per_file_years]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"Değer profili yazıldı: {out_path}")
