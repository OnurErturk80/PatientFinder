"""Aynı kaydın birden çok dosyada bulunması (yedek, yeniden kaydedilmiş ay) durumunda
yalnızca en son değiştirilen dosyadaki kopyayı tutar; böylece dondurulan embriyo iki kez sayılmaz."""
from __future__ import annotations


def latest_per_ident(rows: list[dict], key_fn, compare: tuple[str, ...] = ()) -> list[dict]:
    """key_fn(row) -> kimlik (None ise kopya aranmaz). compare: kopyalar bu alanlarda
    farklıysa tutulan kayda conflict=True işareti konur. Kopya sayısı 'copies' alanındadır."""
    best: dict = {}
    order: list = []
    groups: dict = {}
    for r in rows:
        k = key_fn(r)
        if k is None:
            order.append(("row", id(r)))
            best[("row", id(r))] = r
            groups[("row", id(r))] = [r]
            continue
        groups.setdefault(k, []).append(r)
        cur = best.get(k)
        if cur is None:
            order.append(k)
            best[k] = r
        elif (r.get("mtime") or 0, r.get("file_id") or 0) > (cur.get("mtime") or 0, cur.get("file_id") or 0):
            best[k] = r
    out = []
    for k in order:
        r = dict(best[k])
        g = groups[k]
        r["copies"] = len(g)
        r["conflict"] = any(len({x.get(f) for x in g}) > 1 for f in compare) if len(g) > 1 else False
        out.append(r)
    return out
