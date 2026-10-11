"""Yerel web sunucusu (FastAPI). Varsayılan: yalnızca 127.0.0.1."""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import db as dbmod
from .matching import decide, search
from .patient import patient_view

WEB = os.path.join(os.path.dirname(__file__), "web")


class Decision(BaseModel):
    key_a: str
    key_b: str
    verdict: str | None  # 'merge' | 'separate' | null (geri al)


def create_app(conn=None, scan=None) -> FastAPI:
    """scan: () -> {dosya: durum} (Access klasörünü içe aktaran işlev)."""
    conn = conn or dbmod.connect()
    app = FastAPI(title="Hasta Geçmişi", docs_url=None, redoc_url=None)

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
