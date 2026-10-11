"""Access okuma arayüzü. Tüm arka uçlar SALT OKUNUR çalışır; yazma kodu yoktur."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator

# access-parser'ın sayısal tip kodları -> okunur ad
_TYPE_NAMES = {
    1: "Yes/No", 2: "Byte", 3: "Integer", 4: "Long Integer", 5: "Currency",
    6: "Single", 7: "Double", 8: "Date/Time", 9: "Binary", 10: "Text",
    11: "OLE", 12: "Memo", 15: "GUID", 16: "Decimal", 18: "Complex",
}


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type_name: str


class AccessSource(ABC):
    """Tek bir .accdb/.mdb dosyasına salt okunur erişim."""

    backend_name = "?"

    @abstractmethod
    def list_tables(self) -> list[str]: ...

    @abstractmethod
    def columns(self, table: str) -> list[ColumnInfo]: ...

    @abstractmethod
    def row_count(self, table: str) -> int: ...

    @abstractmethod
    def read_table(self, table: str) -> Iterator[dict]: ...

    def close(self) -> None:  # pragma: no cover - isteğe bağlı
        pass


class AccessParserSource(AccessSource):
    """Saf Python arka uç (access-parser). Sürücü kurulumu gerektirmez."""

    backend_name = "access-parser"

    def __init__(self, path: str):
        from access_parser import AccessParser  # gecikmeli içe aktarma

        self._db = AccessParser(path)  # dosyayı yalnızca 'rb' ile okur
        self._cache: dict[str, object] = {}

    def _table(self, name: str):
        if name not in self._cache:
            self._cache[name] = self._db.get_table(name)
        return self._cache[name]

    def list_tables(self) -> list[str]:
        return sorted(self._db.catalog.keys())

    def columns(self, table: str) -> list[ColumnInfo]:
        t = self._table(table)
        cols = getattr(t, "columns", None) or {}
        out = []
        for idx in sorted(cols):
            c = cols[idx]
            name = getattr(c, "col_name_str", None) or getattr(c, "name", str(idx))
            ctype = getattr(c, "type", None)
            out.append(ColumnInfo(name, _TYPE_NAMES.get(ctype, f"Bilinmeyen({ctype})")))
        return out

    def read_table(self, table: str) -> Iterator[dict]:
        data = self._db.parse_table(table) or {}
        if not data:
            return
        names = list(data.keys())
        for i in range(len(data[names[0]])):
            yield {n: data[n][i] for n in names}

    def row_count(self, table: str) -> int:
        data = self._db.parse_table(table) or {}
        if not data:
            return 0
        return len(next(iter(data.values())))


class PyodbcSource(AccessSource):
    """Windows arka ucu: Microsoft Access Database Engine (ACE) + pyodbc."""

    backend_name = "pyodbc+ACE"

    def __init__(self, path: str):
        import pyodbc

        drivers = [d for d in pyodbc.drivers() if "Access Driver" in d]
        if not drivers:
            raise RuntimeError(
                "Microsoft Access Database Engine sürücüsü bulunamadı. "
                "Python ile aynı bit sürümünü (32/64) kurun."
            )
        self._conn = pyodbc.connect(
            f"DRIVER={{{drivers[0]}}};DBQ={path};ReadOnly=1;", readonly=True
        )
        self._cur = self._conn.cursor()

    def list_tables(self) -> list[str]:
        return sorted(r.table_name for r in self._cur.tables(tableType="TABLE"))

    def columns(self, table: str) -> list[ColumnInfo]:
        return [ColumnInfo(r.column_name, r.type_name) for r in self._cur.columns(table=table)]

    def row_count(self, table: str) -> int:
        cur = self._conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM [{table.replace(']', '')}]")
        return int(cur.fetchone()[0])

    def read_table(self, table: str) -> Iterator[dict]:
        cur = self._conn.cursor()
        cur.execute(f"SELECT * FROM [{table.replace(']', '')}]")
        names = [d[0] for d in cur.description]
        for row in cur:
            yield dict(zip(names, row))

    def close(self) -> None:
        self._conn.close()


def make_source(path: str, backend: str = "auto") -> AccessSource:
    """backend: 'auto' (önce pyodbc, olmazsa access-parser), 'pyodbc', 'access-parser'."""
    if backend == "access-parser":
        return AccessParserSource(path)
    if backend == "pyodbc":
        return PyodbcSource(path)
    try:
        return PyodbcSource(path)
    except Exception:
        return AccessParserSource(path)
