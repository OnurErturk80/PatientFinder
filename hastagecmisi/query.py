"""Arama sorgusunu ad sözcükleri ve tarih aralığına ayırır.

Desteklenen tarih yazımları (hepsi aynı kutuda, ad ile birlikte de yazılabilir):
  15.03.2024 · 15/03/2024 · 2024-03-15   -> o gün
  03.2024 · 03/2024 · 2024-03 · mart 2024 -> o ay
  2024                                    -> o yıl
  01.2024 - 03.2024   (iki tarih)         -> birinci tarihin başı ile ikincinin sonu arası
Dört haneli sayı bir DOSYA NO ile birebir eşleşiyorsa yıl değil dosya no sayılır.
"""
from __future__ import annotations

import calendar
import re

from .normalize import norm

_MN = "ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik"
_NUM = {m: i + 1 for i, m in enumerate(_MN.split("|"))}
_Y = r"(20\d\d)"
_PATTERNS = [  # öncelik sırası: uzun/özel biçimler önce
    ("ymd", re.compile(rf"(?<!\d){_Y}-(\d{{1,2}})-(\d{{1,2}})(?!\d)")),
    ("dmy", re.compile(rf"(?<!\d)(\d{{1,2}})[./-](\d{{1,2}})[./-]{_Y}(?!\d)")),
    ("ym", re.compile(rf"(?<!\d){_Y}-(\d{{1,2}})(?![\d-])")),
    ("my", re.compile(rf"(?<![\d./-])(\d{{1,2}})[./-]{_Y}(?!\d)")),
    ("mname", re.compile(rf"(?<![a-z])({_MN})\s+{_Y}(?!\d)")),
    ("y", re.compile(rf"(?<![\d./-]){_Y}(?![\d./-])")),
]


def _span(kind: str, g: tuple, protocols: set):
    """(başlangıç, bitiş, ayrıntı düzeyi) ya da geçersizse None."""
    if kind in ("ymd", "dmy"):
        y, m, d = (int(g[0]), int(g[1]), int(g[2])) if kind == "ymd" else (int(g[2]), int(g[1]), int(g[0]))
        if not (1 <= m <= 12 and 1 <= d <= calendar.monthrange(y, m)[1]):
            return None
        s = f"{y:04d}-{m:02d}-{d:02d}"
        return s, s, "day"
    if kind in ("ym", "my", "mname"):
        y, m = (int(g[0]), int(g[1])) if kind == "ym" else (int(g[1]), int(g[0])) if kind == "my" else (int(g[1]), _NUM[g[0]])
        if not 1 <= m <= 12:
            return None
        return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}", "month"
    if g[0] in protocols:
        return None
    return f"{g[0]}-01-01", f"{g[0]}-12-31", "year"


def parse_query(q: str, protocols: set | frozenset = frozenset()):
    """-> (ad sözcükleri, (lo, hi, gün_düzeyinde_mi) | None)."""
    s = norm(q)
    found = []
    for kind, rx in _PATTERNS:
        for m in list(rx.finditer(s)):
            sp = _span(kind, m.groups(), protocols)
            if sp:
                found.append((m.start(), sp))
                s = s[:m.start()] + " " * (m.end() - m.start()) + s[m.end():]
    tokens = [t for t in s.replace("–", " ").replace("..", " ").split() if t not in ("-", "ile")]
    if not found:
        return tokens, None
    found.sort(key=lambda x: x[0])
    lo, hi = found[0][1][0], found[-1][1][1]
    if lo > hi:
        lo, hi = found[-1][1][0], found[0][1][1]
    return tokens, (lo, hi, all(f[1][2] == "day" for f in found))


def in_range(dates, month, rng) -> str | None:
    """Kaydın tarihlerinden biri aralıktaysa o tarihi (yoksa ay dizgesini) döndürür."""
    lo, hi, day_level = rng
    for d in dates:
        if d and lo <= d <= hi:
            return d
    if month and not day_level and lo[:7] <= month <= hi[:7]:
        return month
    return None
