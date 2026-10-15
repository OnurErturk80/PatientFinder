"""Yerel sunucuyu başlatır: python -m hastagecmisi KLASÖR [--port 8765] [--db yol] [--backend auto]"""
import argparse
import getpass
import socket
import os
import sys
import webbrowser

import uvicorn

from . import auth as auth_mod
from . import db
from .access_mapping import make_reader
from .app import create_app


def default_db() -> str:
    base = os.environ.get("PROGRAMDATA") or os.path.expanduser("~/.hastagecmisi")
    return os.path.join(base, "HastaGecmisi", "index.sqlite") if os.environ.get("PROGRAMDATA") else os.path.join(base, "index.sqlite")


def lan_urls(port: int) -> list[str]:
    urls = [f"http://{socket.gethostname()}:{port}"]
    try:  # UDP 'bağlantı' paket göndermez; yalnızca yerel IP'yi öğrenir
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            urls.append(f"http://{s.getsockname()[0]}:{port}")
    except OSError:
        pass
    return urls


def show_qr(text: str) -> None:
    try:
        import qrcode

        q = qrcode.QRCode(border=1)
        q.add_data(text)
        q.make()
        q.print_ascii(invert=True)
    except Exception:
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--db", default=default_db())
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--lan", action="store_true", help="Telefon erişimi: aynı ağdan, PIN ile")
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
    auth, host = None, "127.0.0.1"
    url = f"http://127.0.0.1:{a.port}"
    if a.lan:
        pin_path = os.path.join(os.path.dirname(a.db), "pin.json")
        if not auth_mod.has_pin(pin_path):
            while True:
                pin = getpass.getpass("Telefon erişimi için bir PIN belirleyin (en az 6 karakter): ")
                try:
                    auth_mod.set_pin(pin_path, pin)
                    break
                except ValueError as e:
                    print(e)
        auth, host = auth_mod.Auth(pin_path), "0.0.0.0"
        print("\nTELEFON İÇİN (aynı Wi-Fi'ye bağlı olmalı):")
        for u in lan_urls(a.port):
            print("   ", u)
            show_qr(u)
        print("Windows Güvenlik Duvarı sorarsa YALNIZCA 'Özel ağlar'ı işaretleyin.")
        print("Uyarı: bağlantı şifresizdir (HTTP); misafir Wi-Fi'de kullanmayın.\n")
    print(f"Bilgisayarda: {url}  (kapatmak için bu pencereyi kapatın)")
    webbrowser.open(url)
    uvicorn.run(create_app(conn, scan, auth), host=host, port=a.port, log_level="warning")
    return 0


sys.exit(main())
