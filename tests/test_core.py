import os
import shutil

from fastapi.testclient import TestClient

from hastagecmisi import db, inventory, matching
from hastagecmisi.app import create_app
from hastagecmisi.normalize import norm
from hastagecmisi.synthetic import json_reader, make_dataset


def ev(kind, count, st="embryo"):
    return {"kind": kind, "count": count, "sample_type": st, "id": 1, "path": "x", "src_ref": "r",
            "event_date": "2024-01-01", "month": "2024-01"}


def test_norm_turkish():
    assert norm("  YILMAZ\xa0Şükrü ") == "yilmaz sukru"
    assert norm("İbrahim ILGAZ") == "ibrahim ilgaz" and norm(None) == ""


def test_inventory_clean_and_conflicts():
    ok = inventory.compute([ev("freeze", 5), ev("thaw", 2), ev("use", 2)])["embryo"]
    assert ok["remaining"] == 3 and not ok["verify"]
    assert inventory.compute([ev("freeze", 1), ev("thaw", 3)])["embryo"]["verify"]
    assert inventory.compute([ev("thaw", 1)])["embryo"]["verify"]
    r = inventory.compute([ev("freeze", 4), ev("thaw", 1)])["embryo"]  # Access'te yalnızca freeze/thaw tutulur
    assert r["remaining"] == 3 and not r["verify"]
    assert inventory.compute([{**ev("freeze", 2), "conflict": True}])["embryo"]["verify"]
    assert inventory.compute([ev("freeze", None)])["embryo"]["verify"]


def _loaded(tmp_path):
    folder = str(tmp_path / "d")
    make_dataset(folder)
    conn = db.connect()
    return conn, folder, db.scan_folder(conn, folder, json_reader, exts=(".json",))


def test_incremental_import(tmp_path):
    conn, folder, first = _loaded(tmp_path)
    assert set(first.values()) == {"imported"}
    assert set(db.scan_folder(conn, folder, json_reader, exts=(".json",)).values()) == {"skipped"}
    p = os.path.join(folder, "2021-01.json")
    open(p, "a").write(" ")
    assert db.scan_folder(conn, folder, json_reader, exts=(".json",))[p] == "imported"
    n = conn.execute("SELECT COUNT(*) FROM cycle").fetchone()[0]
    assert n == 72  # yeniden aktarım kopya üretmedi


def test_failed_file_rolls_back(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{}")
    conn = db.connect()
    assert db.import_file(conn, str(p), json_reader).startswith("failed:")
    assert conn.execute("SELECT COUNT(*) FROM source_file").fetchone()[0] == 0


def test_search_couple_and_spouse(tmp_path):
    conn, *_ = _loaded(tmp_path)
    r = matching.search(conn, "yilmaz")
    assert r and all("yilmaz" in x["female"] + x["male"] for x in r)
    c = r[0]
    assert matching.search(conn, c["male"].split()[0] + " " + c["female"].split()[0])


def test_merge_decision_is_explicit_and_reversible(tmp_path):
    conn, *_ = _loaded(tmp_path)
    a, b = "ayse yilmaz|ali yilmaz", "ayse yilmaz|ali kaya"
    assert matching.merged_keys(conn, a) == {a}
    matching.decide(conn, a, b, "merge")
    assert matching.merged_keys(conn, a) == {a, b}
    matching.decide(conn, a, b, None)
    assert matching.merged_keys(conn, a) == {a}


def test_api_end_to_end(tmp_path):
    conn, *_ = _loaded(tmp_path)
    c = TestClient(create_app(conn))
    hit = c.get("/api/search", params={"q": "yilmaz"}).json()[0]
    p = c.get("/api/patient", params={"key": hit["key"]}).json()
    assert p["cycles"] and "inventory_lines" in p and p["note"]
    assert all(cy["source"]["file"] for cy in p["cycles"])
    assert c.get("/").status_code == 200
    assert c.get("/api/patient", params={"key": "x"}).status_code == 400
