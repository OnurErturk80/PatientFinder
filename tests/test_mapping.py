import datetime as dt
import os

from hastagecmisi import db, inventory
from hastagecmisi.access_mapping import (C, make_reader, map_rows, month_from_filename, to_date, treatment_type,
                                         year_from_path)
from hastagecmisi.access_source import AccessSource


def row(**kw):
    base = {C["first"]: "Ayşe", C["last"]: "Yılmaz", C["spouse"]: "Mehmet", C["file_no"]: 1234, C["row_id"]: 7}
    for k, v in kw.items():
        base[C[k]] = v
    return base


def test_filename_year_dates():
    assert month_from_filename("ŞUBATT.accdb") == 2 and month_from_filename("EYLÜL (2).accdb") == 9
    assert month_from_filename("TEMMUZ_Backup.accdb") == 7 and month_from_filename("IVFKAYIT EKİM.accdb") == 10
    assert year_from_path(os.path.join("HASTA KAYITLARI", "2023", "MART.accdb")) == 2023
    assert year_from_path("MART.accdb") is None
    assert to_date(dt.datetime(2024, 3, 5, 10)) == "2024-03-05" and to_date("1899-12-30") is None


def test_map_fresh_then_fet_inventory(tmp_path):
    fresh = row(opu=dt.datetime(2023, 3, 10), oocytes=10, mii=8, pn2=6, method="ICSI", frozen=3,
                freeze_stage="D5", transfer_date=dt.datetime(2023, 3, 15), transfer_count=1, bhcg1=250.0)
    fet = row(thawed=2, transfer_date=dt.datetime(2024, 1, 20), transfer_count=2)
    p1, p2 = tmp_path / "2023", tmp_path / "2024"
    p1.mkdir(); p2.mkdir()
    c1, e1 = map_rows(str(p1 / "MART.accdb"), [fresh, {C["first"]: None, C["last"]: None}])
    c2, e2 = map_rows(str(p2 / "OCAK.accdb"), [fet])
    assert len(c1) == 1 and c1[0]["month"] == "2023-03" and c1[0]["treatment_type"] == "ICSI"
    assert "β-hCG: 250" in c1[0]["outcome"] and c2[0]["treatment_type"] == "FET (çözdürme)"
    assert c1[0]["transfer_day"] is None and c2[0]["month"] == "2024-01"
    evs = [{**e, "id": i, "path": "x", "mtime": 0} for i, e in enumerate(e1 + e2)]
    inv = inventory.compute(evs)["embryo"]
    assert (inv["frozen"], inv["thaw"], inv["remaining"], inv["verify"]) == (3, 2, 1, False)


class FakeAccess(AccessSource):
    backend_name = "fake"

    def __init__(self, rows):
        self.rows = rows

    def list_tables(self): return ["VERİTABANI"]
    def columns(self, t): return []
    def row_count(self, t): return len(self.rows)
    def read_table(self, t): return iter(self.rows)


def test_duplicate_file_not_double_counted(tmp_path, monkeypatch):
    """Aynı ayın yedek kopyası: dondurulan embriyo iki kez sayılmamalı; farklıysa 'Doğrulanmalı'."""
    r = row(opu=dt.datetime(2023, 3, 10), frozen=3)
    for name, rows in (("MART.accdb", [r]), ("MART_Backup.accdb", [r])):
        (tmp_path / name).write_bytes(name.encode())
    monkeypatch.setattr("hastagecmisi.access_source.make_source", lambda p, b: FakeAccess([r]))
    conn = db.connect()
    res = db.scan_folder(conn, str(tmp_path), make_reader())
    assert set(res.values()) == {"imported"}
    key = "#1234|"
    inv = inventory.for_patient(conn, key)["inventory"]["embryo"]
    assert inv["frozen"] == 3 and inv["remaining"] == 3 and not inv["verify"]
    # yedekteki adet farklı olsun
    conn.execute("UPDATE sample_event SET count=2 WHERE file_id=(SELECT id FROM source_file WHERE path LIKE '%Backup%')")
    assert inventory.for_patient(conn, key)["inventory"]["embryo"]["verify"]


def test_treatment_type_fallbacks():
    assert treatment_type({}) == "İşlem bilgisi yok"
    assert treatment_type(row(opu=dt.datetime(2023, 1, 1))) == "OPU (yöntem belirtilmemiş)"


def test_dosya_no_groups_typos_together(tmp_path):
    from hastagecmisi import matching
    a = row(opu=dt.datetime(2023, 3, 10), frozen=2)
    b = {**row(thawed=1, transfer_date=dt.datetime(2024, 1, 5)), C["spouse"]: "Mehmed", C["last"]: "Yilmaz"}
    conn = db.connect()
    for name, rows in (("MART.accdb", [a]), ("OCAK.accdb", [b])):
        p = tmp_path / name
        p.write_bytes(name.encode())
        db.import_file(conn, str(p), lambda path, r=rows: map_rows(path, r))
    hits = matching.search(conn, "yilmaz")
    assert len(hits) == 1 and hits[0]["key"] == "#1234|" and hits[0]["records"] == 4
    assert inventory.for_patient(conn, "#1234|")["inventory"]["embryo"]["remaining"] == 1


def test_notes_shown_and_flag_freeze_mentions(tmp_path):
    from hastagecmisi.patient import patient_view
    r = row(opu=dt.datetime(2023, 3, 10), **{"notes": "3 embriyo donduruldu D5"})
    conn = db.connect(str(tmp_path / "i.sqlite"))
    p = tmp_path / "MART.accdb"
    p.write_bytes(b"x")
    db.import_file(conn, str(p), lambda path: map_rows(path, [r]))
    v = patient_view(conn, "#1234|")
    assert v["cycles"][0]["notes"] == "3 embriyo donduruldu D5" and v["cycles"][0]["notes_hint"]
    assert any(l.startswith("Doğrulanmalı") and "notlarında" in l for l in v["inventory_lines"])
    assert db.connect(str(tmp_path / "i.sqlite")).execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


def test_real_accdb_fixtures_end_to_end():
    """Gerçek .accdb dosyaları (uydurma veri): access-parser -> eşleme -> hasta görünümü."""
    from hastagecmisi.patient import patient_view
    folder = os.path.join(os.path.dirname(__file__), "fixtures", "sample")
    conn = db.connect()
    res = db.scan_folder(conn, folder, make_reader("access-parser"))
    assert set(res.values()) == {"imported"}
    v = patient_view(conn, "#1001|")
    assert v["header"][0].startswith("2 tedavi") and v["inventory"]["embryo"]["remaining"] == 1
    assert [c["month"] for c in v["cycles"]] == ["2023-03", "2024-01"]
    assert any("notlarında" in l for l in v["inventory_lines"])
