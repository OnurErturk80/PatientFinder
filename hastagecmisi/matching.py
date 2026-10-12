"""Hasta/çift arama ve eşleştirme. ASLA otomatik birleştirme yapmaz."""
from __future__ import annotations

from collections import Counter, defaultdict

from .normalize import norm


def couple_key(f_norm: str, m_norm: str) -> str:
    return f"{f_norm}|{m_norm}"


def row_key(r) -> str:
    """DOSYA NO kalıcı hasta numarasıdır: varsa anahtar odur (yazım hatalarına dayanıklı).
    Yoksa ad+eş adı. Anahtar her zaman '|' içerir."""
    no = (r["protocol_no"] or "").strip()
    return f"#{no}|" if no else couple_key(r["f_norm"], r["m_norm"])


def search(conn, q: str, limit: int = 50) -> list[dict]:
    """Aday listesi: ad/soyad/eş adı/protokol no. Her sözcük kadın VEYA eş alanında geçmeli."""
    tokens = norm(q).split()
    if not tokens:
        return []
    groups: dict[str, dict] = {}
    for table in ("cycle", "sample_event"):
        birth = "birth_date" if table == "cycle" else "NULL"
        for r in conn.execute(f"SELECT f_norm, m_norm, protocol_no, month, {birth} AS birth FROM {table}"):
            hay = f"{r['f_norm']} {r['m_norm']} {norm(r['protocol_no'])}"
            if all(t in hay for t in tokens):
                g = groups.setdefault(row_key(r), {"f": Counter(), "m": Counter(), "months": set(),
                                                   "birth": set(), "n": 0, "no": r["protocol_no"]})
                g["n"] += 1
                g["f"][r["f_norm"]] += 1
                g["m"][r["m_norm"]] += 1
                if r["month"]:
                    g["months"].add(r["month"])
                if r["birth"]:
                    g["birth"].add(r["birth"])
    out = []
    for k, g in groups.items():
        m = sorted(g["months"])
        out.append({"key": k, "female": g["f"].most_common(1)[0][0], "male": g["m"].most_common(1)[0][0],
                    "protocol_no": g["no"], "records": g["n"], "first": m[0] if m else None,
                    "last": m[-1] if m else None, "birth": sorted(g["birth"])})
    out.sort(key=lambda x: (-x["records"], x["female"]))
    return out[:limit]


def decisions(conn) -> dict[frozenset, str]:
    return {frozenset((r["key_a"], r["key_b"])): r["verdict"]
            for r in conn.execute("SELECT * FROM decision")}


def decide(conn, key_a: str, key_b: str, verdict: str | None) -> None:
    """verdict=None kararı geri alır."""
    a, b = sorted((key_a, key_b))
    with conn:
        conn.execute("DELETE FROM decision WHERE key_a=? AND key_b=?", (a, b))
        if verdict:
            conn.execute("INSERT INTO decision VALUES(?,?,?,strftime('%s','now'))", (a, b, verdict))


def merged_keys(conn, key: str) -> set[str]:
    """Kullanıcının 'birleştir' dediği anahtarların bağlantılı kümesi (yalnızca açık kararlar)."""
    adj = defaultdict(set)
    for pair, v in decisions(conn).items():
        if v == "merge":
            a, b = tuple(pair)
            adj[a].add(b)
            adj[b].add(a)
    seen, stack = {key}, [key]
    while stack:
        for n in adj[stack.pop()] - seen:
            seen.add(n)
            stack.append(n)
    return seen


def similar_candidates(conn, key: str) -> list[dict]:
    """Birleştirme önerisi: aynı kadın VEYA aynı eş adı taşıyan, karar verilmemiş diğer anahtarlar."""
    known = decisions(conn)
    names: dict[str, dict] = {}
    for table in ("cycle", "sample_event"):
        for r in conn.execute(f"SELECT DISTINCT f_norm, m_norm, protocol_no FROM {table}"):
            g = names.setdefault(row_key(r), {"f": set(), "m": set()})
            g["f"].add(r["f_norm"])
            g["m"].add(r["m_norm"])
    me = names.get(key)
    if not me:
        return []
    out = []
    for k, g in names.items():
        if k == key or frozenset((k, key)) in known:
            continue
        if (me["f"] & g["f"] - {""}) or (me["m"] & g["m"] - {""}):
            out.append({"key": k, "female": sorted(g["f"])[0], "male": sorted(g["m"])[0]})
    return out


def patient_keys(conn, key: str) -> set[str]:
    return merged_keys(conn, key)
