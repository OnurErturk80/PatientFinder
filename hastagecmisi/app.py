"""Yerel web sunucusu (FastAPI). Varsayılan: yalnızca 127.0.0.1."""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from . import db as dbmod
from .matching import decide, search
from .patient import patient_view

WEB = os.path.join(os.path.dirname(__file__), "web")


class Login(BaseModel):
    pin: str


class Decision(BaseModel):
    key_a: str
    key_b: str
    verdict: str | None  # 'merge' | 'separate' | null (geri al)


def create_app(conn=None, scan=None, auth=None) -> FastAPI:
    """scan: () -> {dosya: durum} (Access klasörünü içe aktaran işlev)."""
    conn = conn or dbmod.connect()
    app = FastAPI(title="Hasta Geçmişi", docs_url=None, redoc_url=None)

    COOKIE = "hg_session"

    @app.middleware("http")
    async def require_login(request: Request, call_next):
        open_paths = ("/login", "/api/login", "/manifest.webmanifest")
        if auth and request.url.path not in open_paths and not auth.valid(request.cookies.get(COOKIE)):
            if request.url.path.startswith("/api/"):
                return JSONResponse({"detail": "Giriş gerekli."}, status_code=401)
            return RedirectResponse("/login")
        resp = await call_next(request)
        resp.headers["Cache-Control"] = "no-store"  # hasta verisi tarayıcı önbelleğinde kalmasın
        return resp

    @app.get("/login")
    def login_page():
        return FileResponse(os.path.join(WEB, "login.html"))

    @app.post("/api/login")
    def api_login(body: Login, request: Request):
        ip = request.client.host if request.client else "?"
        if auth.locked(ip):
            return JSONResponse({"detail": "Çok fazla hatalı deneme. 5 dakika sonra tekrar deneyin."}, status_code=429)
        tok = auth.login(ip, body.pin)
        if not tok:
            return JSONResponse({"detail": "PIN hatalı."}, status_code=401)
        r = JSONResponse({"ok": True})
        r.set_cookie(COOKIE, tok, httponly=True, samesite="strict", max_age=None)
        return r

    @app.get("/manifest.webmanifest")
    def manifest():
        return JSONResponse({"name": "Hasta Geçmişi", "short_name": "Hasta", "start_url": "/",
                             "display": "standalone", "background_color": "#12151b", "theme_color": "#12151b"},
                            media_type="application/manifest+json")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(WEB, "index.html"))

    @app.get("/api/search")
    def api_search(q: str = ""):
        return search(conn, q)

    @app.get("/api/patient")
    def api_patient(key: str):
        if "|" not in key:
            raise HTTPException(400, "Geçersiz hasta anahtarı.")
        return patient_view(conn, key)

    @app.post("/api/decision")
    def api_decision(d: Decision):
        if d.verdict not in ("merge", "separate", None):
            raise HTTPException(400, "Geçersiz karar.")
        decide(conn, d.key_a, d.key_b, d.verdict)
        return {"ok": True}

    @app.post("/api/scan")
    def api_scan():
        if scan is None:
            raise HTTPException(400, "Access klasörü ayarlanmamış.")
        return scan()

    return app
