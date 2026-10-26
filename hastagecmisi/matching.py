"""Hasta/çift arama ve eşleştirme. ASLA otomatik birleştirme yapmaz."""
from __future__ import annotations

from collections import Counter, defaultdict

from .normalize import norm
from .query import in_range, parse_query


def couple_key(f_norm: str, m_norm: str) -> str:
    return f"{f_norm}|{m_norm}"


def row_key(r) -> str:
    """DOSYA NO kalıcı hasta numarasıdır: varsa anahtar odur (yazım hatalarına dayanıklı).
    Yoksa ad+eş adı. Anahtar her zaman '|' içerir."""
    no = (r["protocol_no"] or "").strip()
    return f"#{no}|" if no else couple_key(r["f_norm"], r["m_norm"])


def search(conn, q: str, limit: int = 50) -> list[dict]:
    """Ad/soyad/eş adı/protokol no ve/veya tarih (bkz. query.py). Her ad sözcüğü kadın VEYA eş alanında geçmeli."""
    protocols = {str(r[0]).strip() for t in ("cycle", "sample_event") for r in conn.execute(f"SELECT DISTINCT protocol_no FROM {t}") if r[0]}
    tokens, rng = parse_query(q, protocols)
    if not tokens and not rng:
        return []
    groups: dict[str, dict] = {}
    for table in ("cycle", "sample_event"):
        cols = "cycle_date AS d1, transfer_date AS d2, birth_date AS birth" if table == "cycle" else "event_date AS d1, NULL AS d2, NULL AS birth"
        for r in conn.execute(f"SELECT f_norm, m_norm, protocol_no, month, {cols} FROM {table}"):
            hay = f"{r['f_norm']} {r['m_norm']} {norm(r['protocol_no'])}"
            if not all(t in hay for t in tokens):
                continue
            hit = None
            if rng:
                hit = in_range((r["d1"], r["d2"]), r["month"], rng)
                if not hit:
                    continue
            g = groups.setdefault(row_key(r), {"f": Counter(), "m": Counter(), "months": set(), "birth": set(),
                                               "n": 0, "no": r["protocol_no"], "hits": set()})
            g["n"] += 1
            g["f"][r["f_norm"]] += 1
            g["m"][r["m_norm"]] += 1
            if hit:
                g["hits"].add(hit)
            if r["month"]:
                g["months"].add(r["month"])
            if r["birth"]:
                g["birth"].add(r["birth"])
    out = []
    for k, g in groups.items():
        m = sorted(g["months"])
        out.append({"key": k, "female": g["f"].most_common(1)[0][0], "male": g["m"].most_common(1)[0][0],
                    "protocol_no": g["no"], "records": g["n"], "first": m[0] if m else None,
                    "last": m[-1] if m else None, "birth": sorted(g["birth"]), "match_dates": sorted(g["hits"])[:3]})
    if rng and not tokens:  # yalnızca tarih: en erken eşleşen tarihe göre; daha uzun liste
        out.sort(key=lambda x: (x["match_dates"][0] if x["match_dates"] else "", x["female"]))
        return out[:max(limit, 200)]
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
