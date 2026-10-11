"""Hasta/çift arama ve eşleştirme. ASLA otomatik birleştirme yapmaz."""
from __future__ import annotations

from collections import defaultdict

from .normalize import norm


def couple_key(f_norm: str, m_norm: str) -> str:
    return f"{f_norm}|{m_norm}"


def search(conn, q: str, limit: int = 50) -> list[dict]:
    """Aday listesi: ad/soyad/eş adı/protokol no. Her sözcük kadın VEYA eş alanında geçmeli."""
    tokens = norm(q).split()
    if not tokens:
        return []
    groups: dict[str, dict] = {}
    for table in ("cycle", "sample_event"):
        for r in conn.execute(f"SELECT f_norm, m_norm, protocol_no, month, "
                              f"{'birth_date' if table == 'cycle' else 'NULL'} AS birth FROM {table}"):
            hay = f"{r['f_norm']} {r['m_norm']} {norm(r['protocol_no'])}"
            if all(t in hay for t in tokens):
                k = couple_key(r["f_norm"], r["m_norm"])
                g = groups.setdefault(k, {"key": k, "female": r["f_norm"], "male": r["m_norm"],
                                          "months": set(), "birth": set(), "n": 0})
                g["n"] += 1
                if r["month"]:
                    g["months"].add(r["month"])
                if r["birth"]:
                    g["birth"].add(r["birth"])
    out = []
    for g in groups.values():
        m = sorted(g["months"])
        out.append({"key": g["key"], "female": g["female"], "male": g["male"], "records": g["n"],
                    "first": m[0] if m else None, "last": m[-1] if m else None,
                    "birth": sorted(g["birth"])})
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
    """Birleştirme önerisi için benzer çiftler (aynı kadın VEYA aynı eş adı). Karar verilmemişler."""
    f, m = key.split("|", 1)
    known = decisions(conn)
    cands = {}
    for table in ("cycle", "sample_event"):
        for r in conn.execute(f"SELECT DISTINCT f_norm, m_norm FROM {table}"):
            k = couple_key(r["f_norm"], r["m_norm"])
            if k == key or frozenset((k, key)) in known:
                continue
            if (f and r["f_norm"] == f) or (m and r["m_norm"] == m):
                cands[k] = {"key": k, "female": r["f_norm"], "male": r["m_norm"]}
    return list(cands.values())


def patient_keys(conn, key: str) -> set[str]:
    return merged_keys(conn, key)
