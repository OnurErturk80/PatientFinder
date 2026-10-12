"""Yerel sunucuyu başlatır: python -m hastagecmisi KLASÖR [--port 8765] [--db yol] [--backend auto]"""
import argparse
import os
import sys
import webbrowser

import uvicorn

from . import db
from .access_mapping import make_reader
from .app import create_app


def default_db() -> str:
    base = os.environ.get("PROGRAMDATA") or os.path.expanduser("~/.hastagecmisi")
    return os.path.join(base, "HastaGecmisi", "index.sqlite") if os.environ.get("PROGRAMDATA") else os.path.join(base, "index.sqlite")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--db", default=default_db())
    ap.add_argument("--backend", default="auto")
    a = ap.parse_args(argv)
    conn = db.connect(a.db)
    reader = make_reader(a.backend)

    def scan():
        res = db.scan_folder(conn, a.folder, reader)
        out = {"imported": 0, "skipped": 0, "failed": []}
        for p, st in res.items():
            if st.startswith("failed"):
                out["failed"].append(f"{os.path.relpath(p, a.folder)}: {st}")
            else:
                out[st] += 1
        return out

    print("Access dosyaları taranıyor (salt okunur)...")
    r = scan()
    print(f"Tamam: {r['imported']} yeni, {r['skipped']} değişmemiş, {len(r['failed'])} okunamadı.")
    for f in r["failed"]:
        print("  OKUNAMADI:", f)
    url = f"http://127.0.0.1:{a.port}"
    print(f"Arayüz: {url}  (kapatmak için bu pencereyi kapatın)")
    webbrowser.open(url)
    uvicorn.run(create_app(conn, scan), host="127.0.0.1", port=a.port, log_level="warning")
    return 0


sys.exit(main())
