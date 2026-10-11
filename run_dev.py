"""Geliştirme: sentetik veriyle arayüzü aç (http://127.0.0.1:8765). Gerçek veri kullanmaz."""
import tempfile

import uvicorn

from hastagecmisi import db
from hastagecmisi.app import create_app
from hastagecmisi.synthetic import json_reader, make_dataset

folder = tempfile.mkdtemp()
make_dataset(folder)
conn = db.connect()
db.scan_folder(conn, folder, json_reader, exts=(".json",))
uvicorn.run(create_app(conn), host="127.0.0.1", port=8765)
