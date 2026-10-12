"""Komut satırı / çift tıkla giriş noktası."""
from __future__ import annotations

import os
import sys
import traceback

from .access_source import make_source
from .report import FileInfo, find_access_files, render, scan_file


def _ask_folder() -> str | None:
    try:
        import tkinter
        from tkinter import filedialog

        root = tkinter.Tk()
        root.withdraw()
        return filedialog.askdirectory(title="Access dosyalarının klasörünü seçin") or None
    except Exception:
        return None


def run(folder: str, out_path: str, backend: str = "auto") -> int:
    paths = find_access_files(folder)
    if not paths:
        print("Bu klasörde .accdb/.mdb dosyası bulunamadı.")
        return 1
    print(f"{len(paths)} dosya bulundu. Salt okunur taranıyor...")
    results: list[FileInfo] = []
    for p in paths:
        before = os.stat(p).st_mtime_ns
        try:
            src = make_source(p, backend)
            try:
                fi = scan_file(p, src)
                fi.rel = os.path.relpath(p, folder)
            finally:
                src.close()
        except Exception as e:  # hata mesajına dosya içeriği girmez
            st = os.stat(p)
            fr = traceback.extract_tb(e.__traceback__)[-1]  # yalnızca hata türü ve kod konumu, mesaj yok
            fi = FileInfo(p, st.st_size, st.st_mtime, error=f"{type(e).__name__} @{os.path.basename(fr.filename)}:{fr.lineno}",
                          rel=os.path.relpath(p, folder))
        if os.stat(p).st_mtime_ns != before:
            print(f"UYARI: {os.path.basename(p)} değiştirilme zamanı değişti!")
        results.append(fi)
        print(f"  {os.path.basename(p)}: {'HATA' if fi.error else str(len(fi.tables)) + ' tablo'}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render(results, os.path.basename(os.path.abspath(folder))))
    print(f"\nRapor yazıldı: {out_path}\nBu dosya hasta verisi içermez; Claude sohbetine yapıştırabilirsiniz.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    backend = "auto"
    if "--backend" in argv:
        i = argv.index("--backend")
        backend = argv[i + 1]
        del argv[i:i + 2]
    profile = "--profile" in argv
    argv = [a for a in argv if a != "--profile"]
    folder = argv[0] if argv else _ask_folder()
    if not folder:
        print("Klasör seçilmedi.")
        return 1
    out = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])) if getattr(sys, "frozen", False) else os.getcwd(), "schema_report.md")
    code = run(folder, out, backend)
    if profile and code == 0:
        from .profile import write_profile

        write_profile(find_access_files(folder), folder, os.path.join(os.path.dirname(out), "value_profile.md"), backend)
    if getattr(sys, "frozen", False):
        input("\nKapatmak için Enter'a basın...")
    return code
