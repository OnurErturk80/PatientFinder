"""Şema raporu üretimi. Rapora HİÇBİR hücre değeri yazılmaz; yalnızca yapı."""
from __future__ import annotations

import os
import re
import time
import traceback
import unicodedata
from dataclasses import dataclass, field

from .access_source import AccessSource, ColumnInfo

# Sütun ADLARINA bakan sezgi (değerlere bakmaz)
_ID_HINTS = {
    "Protokol/dosya no": ("protokol", "dosya", "protocol", "file_no", "dosyano"),
    "TC kimlik": ("tc", "kimlik", "tckn", "identity"),
    "Doğum tarihi": ("dogum", "doğum", "birth", "dtarih"),
    "Barkod": ("barkod", "barcode"),
    "Ad/soyad": ("ad", "adi", "soyad", "isim", "name"),
    "Eş": ("es", "eş", "esi", "partner", "spouse"),
    "Dondurma/çözme": ("dondur", "coz", "çöz", "freez", "thaw", "straw", "tank", "kanister", "goblet"),
}


def _norm(s: str) -> str:
    s = s.replace("İ", "i").replace("I", "ı").lower()
    return unicodedata.normalize("NFKC", s).strip()


@dataclass
class TableInfo:
    name: str
    columns: list[ColumnInfo]
    rows: int | None
    error: str | None = None


@dataclass
class FileInfo:
    path: str
    size: int
    mtime: float
    backend: str = ""
    rel: str = ""
    tables: list[TableInfo] = field(default_factory=list)
    error: str | None = None


def scan_file(path: str, source: AccessSource) -> FileInfo:
    st = os.stat(path)
    fi = FileInfo(path=path, size=st.st_size, mtime=st.st_mtime, backend=source.backend_name)
    for t in source.list_tables():
        if t.lower().startswith(("msys", "~")):
            continue
        try:
            fi.tables.append(TableInfo(t, source.columns(t), source.row_count(t)))
        except Exception as e:  # tek tablo hatası tüm raporu bozmasın
            fr = traceback.extract_tb(e.__traceback__)[-1]  # mesaj yok; yalnızca tür ve kod konumu
            fi.tables.append(TableInfo(t, [], None, f"{type(e).__name__} @{os.path.basename(fr.filename)}:{fr.lineno}"))
    return fi


def find_access_files(folder: str) -> list[str]:
    out = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith((".accdb", ".mdb")) and not f.startswith("~"):
                out.append(os.path.join(root, f))
    return sorted(out)


def _fmt_time(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


def schema_diff(files: list[FileInfo]) -> list[str]:
    """Dosyalar arası tablo/sütun farkları (ilk başarılı dosya referans)."""
    ok = [f for f in files if not f.error]
    lines: list[str] = []
    if len(ok) < 2:
        return ["Karşılaştırılacak en az iki dosya yok."]
    sigs = {f.path: {t.name: tuple((c.name, c.type_name) for c in t.columns) for t in f.tables} for f in ok}
    groups: dict[str, list[str]] = {}
    for p, s in sigs.items():
        groups.setdefault(repr(sorted(s.items())), []).append(os.path.basename(p))
    lines.append(f"Farklı şema sayısı: **{len(groups)}** (toplam {len(ok)} dosya).")
    if len(groups) == 1:
        lines.append("Tüm dosyalar aynı tablo/sütun yapısında.")
        return lines
    ref = sigs[ok[0].path]
    lines += ["", f"Referans: `{os.path.basename(ok[0].path)}`", "",
              "| Dosya | Eklenen tablo | Kaldırılan tablo | Sütun farkı |", "|---|---|---|---|"]
    for f in ok[1:]:
        s = sigs[f.path]
        added = sorted(set(s) - set(ref))
        removed = sorted(set(ref) - set(s))
        diffs = []
        for t in sorted(set(s) & set(ref)):
            a, b = dict(ref[t]), dict(s[t])
            diffs += [f"{t}.{c} (+)" for c in sorted(set(b) - set(a))]
            diffs += [f"{t}.{c} (−)" for c in sorted(set(a) - set(b))]
            diffs += [f"{t}.{c} ({a[c]}→{b[c]})" for c in sorted(set(a) & set(b)) if a[c] != b[c]]
        if added or removed or diffs:
            lines.append(f"| {os.path.basename(f.path)} | {', '.join(added) or '-'} | "
                         f"{', '.join(removed) or '-'} | {'; '.join(diffs) or '-'} |")
    return lines


def identifier_hints(files: list[FileInfo]) -> list[str]:
    found: dict[str, set[str]] = {}
    for f in files:
        for t in f.tables:
            for c in t.columns:
                n = _norm(c.name)
                for label, keys in _ID_HINTS.items():
                    if any(n == k or re.search(rf"(^|[_\s]){re.escape(k)}", n) or (len(k) > 3 and k in n) for k in keys):
                        found.setdefault(label, set()).add(f"{t.name}.{c.name}")
    if not found:
        return ["Ad temelli ipucu bulunamadı."]
    out = ["Yalnızca sütun ADLARINA dayanır; değerlere bakılmamıştır. Kesin eşleme kullanıcı ile yapılır.", ""]
    for label, cols in sorted(found.items()):
        out.append(f"- **{label}:** " + ", ".join(f"`{c}`" for c in sorted(cols)[:15]) + (" …" if len(cols) > 15 else ""))
    return out


def render(files: list[FileInfo], folder_label: str = "(seçilen klasör)") -> str:
    L = ["# Access şema raporu", "",
         "> Bu rapor hasta verisi içermez; yalnızca dosya, tablo ve sütun yapısını gösterir.", "",
         f"- Oluşturulma: {time.strftime('%Y-%m-%d %H:%M')}",
         f"- Klasör: {folder_label}", f"- Dosya sayısı: {len(files)}", "",
         "## 1. Dosyalar", "", "| Dosya | Boyut (KB) | Değiştirilme | Arka uç | Tablo | Durum |", "|---|---:|---|---|---:|---|"]
    for f in files:
        L.append(f"| {f.rel or os.path.basename(f.path)} | {f.size // 1024} | {_fmt_time(f.mtime)} | {f.backend or '-'} | "
                 f"{len(f.tables)} | {'HATA: ' + f.error if f.error else 'tamam'} |")
    L += ["", "## 2. Yıllar arası şema farkı", ""] + schema_diff(files)
    L += ["", "## 3. Hasta ayırt edici alan ipuçları", ""] + identifier_hints(files)
    L += ["", "## 4. Tablo ve sütun ayrıntısı", ""]
    # Aynı yapıdaki dosyaları grupla; her benzersiz şemayı bir kez yaz
    seen: dict[str, list[str]] = {}
    detail: dict[str, FileInfo] = {}
    for f in files:
        if f.error:
            continue
        key = repr([(t.name, [(c.name, c.type_name) for c in t.columns]) for t in f.tables])
        seen.setdefault(key, []).append(os.path.basename(f.path))
        detail.setdefault(key, f)
    for i, (key, names) in enumerate(seen.items(), 1):
        f = detail[key]
        L += [f"### Şema {i} — {len(names)} dosya", "", "Dosyalar: " + ", ".join(names[:40]) + (" …" if len(names) > 40 else ""), ""]
        for t in f.tables:
            rows = "?" if t.rows is None else t.rows
            L += [f"**{t.name}** (örnek dosyada {rows} satır)" + (f" — okunamadı: {t.error}" if t.error else ""), "",
                  "| Sütun | Tip |", "|---|---|"] + [f"| {c.name} | {c.type_name} |" for c in t.columns] + [""]
    L += ["## 5. Satır sayıları (dosya × tablo)", ""]
    tnames = sorted({t.name for f in files for t in f.tables})
    if tnames:
        L += ["| Dosya | " + " | ".join(tnames) + " |", "|---|" + "---:|" * len(tnames)]
        for f in files:
            d = {t.name: t.rows for t in f.tables}
            L.append(f"| {os.path.basename(f.path)} | " + " | ".join("-" if d.get(n) is None else str(d[n]) for n in tnames) + " |")
    return "\n".join(L) + "\n"
