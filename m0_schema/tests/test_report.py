import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hastagecmisi_m0.access_source import AccessSource, ColumnInfo
from hastagecmisi_m0.cli import run
from hastagecmisi_m0.report import find_access_files, render, scan_file


class FakeSource(AccessSource):
    backend_name = "fake"

    def __init__(self, tables):
        self.t = tables

    def list_tables(self):
        return list(self.t) + ["MSysObjects"]

    def columns(self, table):
        return [ColumnInfo(n, ty) for n, ty in self.t[table]]

    def row_count(self, table):
        return 5

    def read_table(self, table):
        raise AssertionError("Şema taramasında satır verisi okunmamalı")


OLD = {"Hasta": [("ProtokolNo", "Text"), ("Ad", "Text"), ("DogumTarihi", "Date/Time")]}
NEW = {"Hasta": [("ProtokolNo", "Text"), ("Ad", "Text"), ("TC", "Text")], "Dondurma": [("Tank", "Text")]}


def _mk(tmp_path, name):
    p = tmp_path / name
    p.write_bytes(b"x" * 2048)
    return str(p)


def test_report_has_diff_and_no_values(tmp_path):
    a, b = _mk(tmp_path, "2017-01.mdb"), _mk(tmp_path, "2024-03.accdb")
    files = [scan_file(a, FakeSource(OLD)), scan_file(b, FakeSource(NEW))]
    md = render(files)
    assert "Farklı şema sayısı: **2**" in md
    assert "Hasta.TC (+)" in md and "Hasta.DogumTarihi (−)" in md
    assert "Dondurma" in md and "MSysObjects" not in md
    assert "Protokol/dosya no" in md and "Barkod" not in md


def test_find_files_skips_lock_and_temp(tmp_path):
    _mk(tmp_path, "a.accdb"), _mk(tmp_path, "~b.accdb"), _mk(tmp_path, "c.txt")
    assert [os.path.basename(p) for p in find_access_files(str(tmp_path))] == ["a.accdb"]


def test_run_never_modifies_input(tmp_path, monkeypatch):
    p = _mk(tmp_path, "a.mdb")
    before = os.stat(p).st_mtime_ns
    monkeypatch.setattr("hastagecmisi_m0.cli.make_source", lambda path, backend: FakeSource(OLD))
    out = tmp_path / "r.md"
    assert run(str(tmp_path), str(out)) == 0
    assert os.stat(p).st_mtime_ns == before and out.exists()
