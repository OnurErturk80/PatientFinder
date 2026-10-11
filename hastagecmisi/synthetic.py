"""Tamamen uydurma hasta verisi (geliştirme/test için). Gerçek veri ASLA kullanılmaz.

Gerçek Access dosyaları yerine kanonik alanlı JSON dosyaları üretir; JsonReader
bunları okur. Access eşlemesi, şema raporundan sonra aynı Reader arayüzüyle yazılacak.
"""
from __future__ import annotations

import json
import os
import random

FEMALE = ["Ayşe", "Fatma", "Zeynep", "Elif", "Şule", "Işıl", "Gülşen", "Özlem"]
MALE = ["Mehmet", "Ali", "Çağrı", "İbrahim", "Ömer", "Uğur", "Şükrü", "Hasan"]
LAST = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Öztürk", "Aydın", "Işık"]


def make_dataset(folder: str, seed: int = 1, months: int = 12) -> list[str]:
    rnd = random.Random(seed)
    os.makedirs(folder, exist_ok=True)
    couples = [(rnd.choice(FEMALE), rnd.choice(LAST), rnd.choice(MALE)) for _ in range(15)]
    paths = []
    for i in range(months):
        y, m = 2021 + i // 12, i % 12 + 1
        month = f"{y}-{m:02d}"
        cycles, events = [], []
        for n, (fn, ln, mn) in enumerate(rnd.sample(couples, 6)):
            ref = f"{month}#{n}"
            fresh = rnd.random() < .6
            base = dict(month=month, f_first=fn, f_last=ln, m_first=mn, m_last=ln, src_ref=ref)
            if fresh:
                emb = rnd.randint(2, 8)
                cycles.append({**base, "cycle_date": f"{month}-10", "treatment_type": "ICSI",
                               "oocytes": emb + 4, "fertilized": emb, "embryos": emb,
                               "transfer_count": 1, "transfer_day": "D5"})
                events.append({**base, "event_date": f"{month}-15", "kind": "freeze",
                               "sample_type": "embryo", "count": emb - 1, "day": "D5", "quality": "4AA"})
            else:
                cycles.append({**base, "cycle_date": f"{month}-12", "treatment_type": "FET"})
                events.append({**base, "event_date": f"{month}-12", "kind": "thaw",
                               "sample_type": "embryo", "count": 1})
                events.append({**base, "event_date": f"{month}-12", "kind": "use",
                               "sample_type": "embryo", "count": 1})
        p = os.path.join(folder, f"{month}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"cycles": cycles, "events": events}, f, ensure_ascii=False)
        paths.append(p)
    return paths


def json_reader(path: str):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d["cycles"], d["events"]
