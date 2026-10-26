"""Telefon uygulaması uçtan uca testi (Chromium). Google ve Drive taklit edilir; .accdb dosyaları gerçektir.
Kullanım: python tests/e2e_phone.py ÖRNEK_KLASÖR   (içinde 2023/MART.accdb, 2024/OCAK.accdb)"""
import functools
import http.server
import json
import os
import sys
import threading

from playwright.sync_api import sync_playwright

SAMPLE = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/index.html"

FILES = {"fMART": ("MART.accdb", "2023/MART.accdb", "y23"), "fOCAK": ("OCAK.accdb", "2024/OCAK.accdb", "y24")}
TREE = {"ROOTFOLDER1234567": [{"id": "y23", "name": "2023", "mimeType": "application/vnd.google-apps.folder"},
                              {"id": "y24", "name": "2024", "mimeType": "application/vnd.google-apps.folder"}],
        "y23": [{"id": "fMART", "name": "MART.accdb", "mimeType": "x", "modifiedTime": "2025-01-01T00:00:00Z", "md5Checksum": "a"}],
        "y24": [{"id": "fOCAK", "name": "OCAK.accdb", "mimeType": "x", "modifiedTime": "2025-02-01T00:00:00Z", "md5Checksum": "b"}]}
downloads, auth_seen = [], []

GSI = "window.google={accounts:{oauth2:{initTokenClient:c=>({requestAccessToken:()=>c.callback({access_token:'tok123'})}),revoke:()=>{}}}};"


def drive(route):
    req = route.request
    auth_seen.append(req.headers.get("authorization"))
    u = req.url
    if "alt=media" in u:
        fid = u.split("/files/")[1].split("?")[0]
        downloads.append(fid)
        return route.fulfill(status=200, body=open(os.path.join(SAMPLE, FILES[fid][1]), "rb").read(),
                             headers={"access-control-allow-origin": "*"})
    q = u.split("q=")[1].split("&")[0]
    parent = q.replace("%27", "'").split("'")[1]
    route.fulfill(status=200, content_type="application/json", headers={"access-control-allow-origin": "*"},
                  body=json.dumps({"files": TREE[parent]}))


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
    ctx = b.new_context()
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    ext = []
    console = []
    page.on("console", lambda m: console.append(m.text))
    page.on("request", lambda r: ext.append(r.url) if not r.url.startswith(("http://127.0.0.1", "data:")) else None)
    ctx.route("https://accounts.google.com/gsi/client", lambda r: r.fulfill(body=GSI, content_type="text/javascript"))
    ctx.route("https://www.googleapis.com/**", drive)
    page.goto(URL)
    page.fill("#cid", "test.apps.googleusercontent.com")
    page.fill("#fol", "https://drive.google.com/drive/folders/ROOTFOLDER1234567?usp=sharing")
    page.click("#save")
    page.click("#dosync")
    try:
        page.wait_for_selector("#q:not(.hide)", timeout=20000)
    except Exception:
        print("SYNC:", page.inner_text("#syncinfo"), "| ERR:", page.inner_text("#errs"), "| JS:", errors, "| CONSOLE:", console)
        raise
    assert not errors, errors
    page.fill("#q", "yilmaz")
    page.wait_for_selector(".row")
    assert "dosya 1001" in page.inner_text(".row") and page.locator(".row").count() == 1
    for q, want in (("10.03.2023", 1), ("03.2023", 2), ("2024", 1), ("2022", 0), ("01.2023 - 06.2024", 2), ("ayse 2024", 1), ("isil 2024", 0)):
        page.fill("#q", q)
        page.wait_for_timeout(450)
        assert page.locator(".row").count() == want, (q, want, page.locator(".row").count())
    page.fill("#q", "15.03.2023")
    page.wait_for_selector(".row")
    assert "eşleşen tarih: 2023-03-15" in page.inner_text(".row")
    page.fill("#q", "yilmaz")
    page.wait_for_selector(".row")
    page.click(".row")
    txt = page.inner_text("#view")
    assert "2 tedavi" in txt and "Kayıtlara göre 1 embriyo kalmış görünüyor." in txt, txt
    full = page.text_content("#view")  # kapalı <details> içeriği dahil
    assert "notlarında embriyo/dondurma" in txt and "2 embriyo da notta yazıyor" in full
    assert "dondurulan 3, çözülen 2" in txt
    assert set(downloads) == {"fMART", "fOCAK"} and set(auth_seen) == {"Bearer tok123"}
    # ikinci eşitleme: dosyalar değişmediği için yeniden indirilmemeli
    downloads.clear()
    page.click("#dosync")
    page.wait_for_function("document.querySelector('#dosync').disabled === false")
    assert downloads == [], downloads
    # sayfa yenilenince veri yerel depodan gelir (Drive çağrısı yok)
    page.reload()
    page.wait_for_selector("#q:not(.hide)")
    page.fill("#q", "sahin")
    page.wait_for_selector(".row")
    # verileri sil
    page.once("dialog", lambda d: d.accept())
    page.click("#wipe")
    page.wait_for_selector("#setup:not(.hide)")
    assert page.locator("#q.hide").count() == 1
    # hiçbir istek Google dışına / Drive dışına gitmedi
    bad = [u for u in ext if not u.startswith(("https://accounts.google.com/", "https://www.googleapis.com/"))]
    assert not bad, bad
    print("E2E TAMAM: indirme", sorted(set(FILES)), "| dış istek yalnızca Google:", sorted({u.split('/')[2] for u in ext}))
    b.close()
