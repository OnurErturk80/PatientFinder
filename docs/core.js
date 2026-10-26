// Python çekirdeğinin (hastagecmisi/) JavaScript karşılığı. Tarayıcıda ve Node'da çalışır.
export const TABLE = "VERİTABANI";
const MONTHS = { ocak: 1, subat: 2, mart: 3, nisan: 4, mayis: 5, haziran: 6, temmuz: 7, agustos: 8, eylul: 9, ekim: 10, kasim: 11, aralik: 12 };
const C = { row_id: "Kimlik", file_no: "DOSYA NO", last: "SOYADI", first: "ADI", spouse: "EŞİNİN ADI", birth: "DOĞUM TARİHİ",
  protocol: "TEDAVİ PROTOKOLÜ", opu: "OPU TARİHİ", oocytes: "TOPLANAN OOSİT", mii: "MATÜR (MII)", method: "FERTİLİZASYON YÖNTEMİ",
  pn2: "NORMAL FERTİLİZASYON (2PN)", stage: "EMBRİYO TRANSFER AŞAMASI", transfer_date: "TRANSFER TARİHİ",
  transfer_count: "TRANSFER EDİLEN EMBRİYO SAYISI", e1c: "EMBRİYO1 HÜCRE/AŞAMA", e1q: "EMBRİYO1 KALİTE", e2c: "EMBRİYO2 HÜCRE/AŞAMA",
  e2q: "EMBRİYO2 KALİTE", frozen: "DONDURULAN EMBRİYO SAYISI", freeze_stage: "EMBRİYO DONDURMA AŞAMASI",
  thawed: "ÇÖZDÜRÜLEN EMBRİYO SAYISI", bhcg1: "BİRİNCİ BHCG", bhcg2: "İKİNCİ BHCG", fhb: "İLK USG FHB KESE", abort: "ABORT",
  missed: "MISSED", ectopic: "EKTOPİK", live: "CANLI DOĞUM SAYISI", dead: "ÖLÜ DOĞUM SAYISI", notes: "NOTLAR", notes_conf: "NOTLAR CONFIDENTIAL" };
const TR = { "İ": "i", I: "i", "ı": "i", "Ş": "s", "ş": "s", "Ğ": "g", "ğ": "g", "Ü": "u", "ü": "u", "Ö": "o", "ö": "o", "Ç": "c", "ç": "c" };

export function norm(t) {
  if (t == null) return "";
  return String(t).replace(/ /g, " ").replace(/[İIıŞşĞğÜüÖöÇç]/g, (c) => TR[c]).normalize("NFKD")
    .replace(/[̀-ͯ]/g, "").toLowerCase().replace(/\s+/g, " ").trim();
}
const toInt = (v) => { if (v == null || v === "") return null; const n = Math.trunc(Number(v)); return Number.isFinite(n) ? n : null; };
const toText = (v) => { if (v == null) return null; const s = String(v).replace(/ /g, " ").trim(); return s || null; };
export function toDate(v) {
  if (v == null || v === "") return null;
  let d = null;
  if (v instanceof Date) d = v;
  else { const m = String(v).trim().match(/^(\d{4})-(\d{2})-(\d{2})/); if (m) d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])); }
  if (!d || isNaN(d)) return null;
  const y = d.getUTCFullYear();   // mdb-reader tarihleri UTC olarak verir
  return y >= 2000 && y <= 2100 ? d.toISOString().slice(0, 10) : null;
}
export function monthFromFilename(name) {
  const base = norm(name.split("/").pop().replace(/\.[^.]+$/, ""));
  for (const [k, n] of Object.entries(MONTHS)) if (base.includes(k)) return n;
  return null;
}
export function yearFromPath(path) {
  const parts = path.split("/").slice(0, -1);
  for (let i = parts.length - 1; i >= 0; i--) { const m = parts[i].match(/(?<!\d)(20\d\d)(?!\d)/); if (m) return +m[1]; }
  return null;
}
function treatmentType(r) {
  if ((toInt(r[C.thawed]) || 0) > 0) return "FET (çözdürme)";
  if (toDate(r[C.opu]) || toInt(r[C.oocytes]) != null) return toText(r[C.method]) || "OPU (yöntem belirtilmemiş)";
  if (toDate(r[C.transfer_date])) return "Transfer";
  return "İşlem bilgisi yok";
}
const fmtNum = (x) => (x == null ? "?" : typeof x === "number" ? String(Number(x.toPrecision(7))) : String(x));
function outcomeText(r) {
  const p = [], b1 = r[C.bhcg1], b2 = r[C.bhcg2];
  if (b1 != null || b2 != null) p.push("β-hCG: " + fmtNum(b1) + " / " + fmtNum(b2));
  const fhb = toInt(r[C.fhb]); if (fhb != null) p.push("USG FHB/kese: " + fhb);
  for (const [k, lab] of [["abort", "Abort"], ["missed", "Missed"], ["ectopic", "Ektopik"]]) { const t = toText(r[C[k]]); if (t) p.push(lab + ": " + t); }
  const live = toInt(r[C.live]), dead = toInt(r[C.dead]);
  if (live != null) p.push("Canlı doğum: " + live);
  if (dead) p.push("Ölü doğum: " + dead);
  return p.join("; ") || null;
}
export function mapRows(path, rows) {
  const fm = monthFromFilename(path); let year = yearFromPath(path);
  if (year == null) {
    const ys = {}; for (const r of rows) for (const d of [toDate(r[C.opu]), toDate(r[C.transfer_date])]) if (d) ys[d.slice(0, 4)] = (ys[d.slice(0, 4)] || 0) + 1;
    const top = Object.entries(ys).sort((a, b) => b[1] - a[1])[0]; year = top ? +top[0] : null;
  }
  const month = year && fm ? `${year}-${String(fm).padStart(2, "0")}` : null;
  const cycles = [], events = [];
  for (const r of rows) {
    const first = toText(r[C.first]), last = toText(r[C.last]);
    if (!(first || last)) continue;
    const opu = toDate(r[C.opu]), tdate = toDate(r[C.transfer_date]), pno = toText(r[C.file_no]);
    const keyDate = opu || tdate;
    const base = { src_ref: `Kimlik ${toText(r[C.row_id]) ?? "?"}`, month, protocol_no: pno, f_first: first, f_last: last,
      m_first: toText(r[C.spouse]), m_last: last, ident: keyDate ? `${pno}|${norm((first || "") + " " + (last || ""))}|${keyDate}` : null };
    const q = [1, 2].map((i) => { const ql = toText(r[C["e" + i + "q"]]), cl = toText(r[C["e" + i + "c"]]);
      return ql || cl ? `E${i}: ` + [ql, cl ? `(${cl})` : null].filter(Boolean).join(" ") : null; }).filter(Boolean);
    cycles.push({ ...base, cycle_date: keyDate, treatment_type: treatmentType(r), protocol: toText(r[C.protocol]),
      birth_date: toDate(r[C.birth]), oocytes: toInt(r[C.oocytes]), mii: toInt(r[C.mii]), fertilized: toInt(r[C.pn2]),
      transfer_date: tdate, transfer_day: toText(r[C.stage]), transfer_count: toInt(r[C.transfer_count]),
      transfer_quality: q.join("; ") || null, outcome: outcomeText(r), notes: toText(r[C.notes]), notes_conf: toText(r[C.notes_conf]) });
    const fz = toInt(r[C.frozen]), th = toInt(r[C.thawed]);
    if (fz) events.push({ ...base, event_date: opu || tdate, kind: "freeze", sample_type: "embryo", count: fz, day: toText(r[C.freeze_stage]) });
    if (th) events.push({ ...base, event_date: tdate || opu, kind: "thaw", sample_type: "embryo", count: th });
  }
  for (const x of cycles.concat(events)) { x.f_norm = norm(`${x.f_first || ""} ${x.f_last || ""}`); x.m_norm = norm(`${x.m_first || ""} ${x.m_last || ""}`); }
  return { cycles, events };
}

// ---- Sorgu: ad sözcükleri + tarih aralığı (Python query.py ile aynı kurallar) ----
const MN = "ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik", MNUM = Object.fromEntries(MN.split("|").map((m, i) => [m, i + 1]));
const Y = "(20\\d\\d)", p2 = (n) => String(n).padStart(2, "0");
const PATTERNS = [
  ["ymd", new RegExp(`(?<!\\d)${Y}-(\\d{1,2})-(\\d{1,2})(?!\\d)`, "g")],
  ["dmy", new RegExp(`(?<!\\d)(\\d{1,2})[./-](\\d{1,2})[./-]${Y}(?!\\d)`, "g")],
  ["ym", new RegExp(`(?<!\\d)${Y}-(\\d{1,2})(?![\\d-])`, "g")],
  ["my", new RegExp(`(?<![\\d./-])(\\d{1,2})[./-]${Y}(?!\\d)`, "g")],
  ["mname", new RegExp(`(?<![a-z])(${MN})\\s+${Y}(?!\\d)`, "g")],
  ["y", new RegExp(`(?<![\\d./-])${Y}(?![\\d./-])`, "g")],
];
const daysIn = (y, m) => new Date(Date.UTC(y, m, 0)).getUTCDate();
function span(kind, g, protocols) {
  if (kind === "ymd" || kind === "dmy") {
    const [y, m, d] = kind === "ymd" ? [+g[0], +g[1], +g[2]] : [+g[2], +g[1], +g[0]];
    if (!(m >= 1 && m <= 12 && d >= 1 && d <= daysIn(y, m))) return null;
    const s = `${y}-${p2(m)}-${p2(d)}`; return [s, s, "day"];
  }
  if (kind === "ym" || kind === "my" || kind === "mname") {
    const [y, m] = kind === "ym" ? [+g[0], +g[1]] : kind === "my" ? [+g[1], +g[0]] : [+g[1], MNUM[g[0]]];
    if (!(m >= 1 && m <= 12)) return null;
    return [`${y}-${p2(m)}-01`, `${y}-${p2(m)}-${p2(daysIn(y, m))}`, "month"];
  }
  return protocols.has(g[0]) ? null : [`${g[0]}-01-01`, `${g[0]}-12-31`, "year"];
}
export function parseQuery(q, protocols = new Set()) {
  let s = norm(q); const found = [];
  for (const [kind, rx] of PATTERNS) {
    for (const m of [...s.matchAll(rx)]) {
      const sp = span(kind, m.slice(1), protocols); if (!sp) continue;
      found.push([m.index, sp]); s = s.slice(0, m.index) + " ".repeat(m[0].length) + s.slice(m.index + m[0].length);
    }
  }
  const tokens = s.replace(/–/g, " ").replace(/\.\./g, " ").split(/\s+/).filter((t) => t && t !== "-" && t !== "ile");
  if (!found.length) return { tokens, rng: null };
  found.sort((a, b) => a[0] - b[0]);
  let lo = found[0][1][0], hi = found.at(-1)[1][1];
  if (lo > hi) { lo = found.at(-1)[1][0]; hi = found[0][1][1]; }
  return { tokens, rng: [lo, hi, found.every((f) => f[1][2] === "day")] };
}
function inRange(dates, month, [lo, hi, dayLevel]) {
  for (const d of dates) if (d && d >= lo && d <= hi) return d;
  return month && !dayLevel && month >= lo.slice(0, 7) && month <= hi.slice(0, 7) ? month : null;
}

// ---- Dizin: dosyalardan gelen kayıtlar ----
export class Index {
  constructor(files, decisions = []) {   // files: [{path, mtime, id, cycles, events}]
    this.cycles = []; this.events = []; this.decisions = decisions;
    for (const f of files) {
      for (const c of f.cycles) this.cycles.push({ ...c, mtime: f.mtime, file: f.path });
      for (const e of f.events) this.events.push({ ...e, mtime: f.mtime, file: f.path });
    }
  }
  static rowKey(r) { const no = (r.protocol_no || "").trim(); return no ? `#${no}|` : `${r.f_norm}|${r.m_norm}`; }
  search(q, limit = 50) {
    const protocols = new Set(this.cycles.concat(this.events).map((r) => (r.protocol_no || "").trim()).filter(Boolean));
    const { tokens, rng } = parseQuery(q, protocols);
    if (!tokens.length && !rng) return [];
    const groups = new Map();
    for (const r of this.cycles.concat(this.events)) {
      const hay = `${r.f_norm} ${r.m_norm} ${norm(r.protocol_no)}`;
      if (!tokens.every((t) => hay.includes(t))) continue;
      let hit = null;
      if (rng) { hit = inRange([r.cycle_date ?? r.event_date, r.transfer_date], r.month, rng); if (!hit) continue; }
      const k = Index.rowKey(r);
      const g = groups.get(k) || { f: {}, m: {}, months: new Set(), birth: new Set(), n: 0, no: r.protocol_no, hits: new Set() };
      g.n++; g.f[r.f_norm] = (g.f[r.f_norm] || 0) + 1; g.m[r.m_norm] = (g.m[r.m_norm] || 0) + 1;
      if (hit) g.hits.add(hit);
      if (r.month) g.months.add(r.month); if (r.birth_date) g.birth.add(r.birth_date);
      groups.set(k, g);
    }
    const top = (o) => Object.entries(o).sort((a, b) => b[1] - a[1])[0][0];
    const out = [...groups].map(([key, g]) => { const m = [...g.months].sort();
      return { key, female: top(g.f), male: top(g.m), protocol_no: g.no, records: g.n, first: m[0] ?? null, last: m.at(-1) ?? null,
        birth: [...g.birth].sort(), match_dates: [...g.hits].sort().slice(0, 3) }; });
    if (rng && !tokens.length) { out.sort((a, b) => (a.match_dates[0] || "").localeCompare(b.match_dates[0] || "") || a.female.localeCompare(b.female)); return out.slice(0, Math.max(limit, 200)); }
    return out.sort((a, b) => b.records - a.records || a.female.localeCompare(b.female)).slice(0, limit);
  }
  mergedKeys(key) {
    const adj = new Map();
    for (const [a, b, v] of this.decisions) if (v === "merge") { (adj.get(a) || adj.set(a, new Set()).get(a)).add(b); (adj.get(b) || adj.set(b, new Set()).get(b)).add(a); }
    const seen = new Set([key]), st = [key];
    while (st.length) for (const n of adj.get(st.pop()) || []) if (!seen.has(n)) { seen.add(n); st.push(n); }
    return seen;
  }
  similar(key) {
    const known = new Set(this.decisions.map(([a, b]) => [a, b].sort().join("\u0001")));
    const names = new Map();
    for (const r of this.cycles.concat(this.events)) { const k = Index.rowKey(r); const g = names.get(k) || { f: new Set(), m: new Set() }; g.f.add(r.f_norm); g.m.add(r.m_norm); names.set(k, g); }
    const me = names.get(key); if (!me) return [];
    const out = [];
    for (const [k, g] of names) {
      if (k === key || known.has([k, key].sort().join("\u0001"))) continue;
      if ([...me.f].some((x) => x && g.f.has(x)) || [...me.m].some((x) => x && g.m.has(x))) out.push({ key: k, female: [...g.f].sort()[0], male: [...g.m].sort()[0] });
    }
    return out;
  }
  decide(a, b, verdict) {
    this.decisions = this.decisions.filter(([x, y]) => [x, y].sort().join("\u0001") !== [a, b].sort().join("\u0001"));
    if (verdict) this.decisions.push([a, b, verdict]);
    return this.decisions;
  }
  patient(key) {
    const keys = this.mergedKeys(key);
    const cycles = latest(this.cycles.filter((r) => keys.has(Index.rowKey(r))), (c) => c.ident, []).sort(byDate((c) => c.cycle_date || c.month));
    const evs = latest(this.events.filter((r) => keys.has(Index.rowKey(r))), (e) => (e.ident ? `${e.ident}|${e.kind}|${e.sample_type}` : null), ["count"]);
    const inventory = computeInventory(evs);
    const months = cycles.map((c) => c.month).filter(Boolean).sort();
    const lines = inventoryLines(inventory);
    const HINT = /dondur|donuk|donmu|vitrif|cryo|cozdur|cozul|embriyo|blast|straw|tank/;
    let hints = 0;
    for (const c of cycles) { c.notes_hint = HINT.test(norm(`${c.notes || ""} ${c.notes_conf || ""}`)); hints += c.notes_hint; }
    if (hints) lines.push(`Doğrulanmalı: ${hints} kaydın notlarında embriyo/dondurma ifadesi geçiyor; bu notlar envanter hesabına katılmadı, tedavi kartlarında okuyun.`);
    return { key, header: [`${cycles.length} tedavi` + (months.length ? ` · ilk kayıt ${months[0]} · son kayıt ${months.at(-1)}` : "")],
      cycles, inventory, inventory_lines: lines, note: "Fiziksel doğrulama için tank haritasına bakın.", similar: this.similar(key), na: "bilgi yok" };
  }
}
const byDate = (f) => (a, b) => String(f(a) ?? "").localeCompare(String(f(b) ?? ""));
// Aynı kayıt birden çok dosyada ise en son değiştirilen dosyadaki kopya kalır.
export function latest(rows, keyFn, compare) {
  const best = new Map(), groups = new Map(); let i = 0;
  for (const r of rows) {
    const k = keyFn(r) ?? `#row${i++}`; (groups.get(k) || groups.set(k, []).get(k)).push(r);
    const cur = best.get(k); if (!cur || String(r.mtime) > String(cur.mtime)) best.set(k, r);
  }
  return [...best].map(([k, r]) => { const g = groups.get(k);
    return { ...r, copies: g.length, conflict: g.length > 1 && compare.some((f) => new Set(g.map((x) => x[f])).size > 1) }; });
}
const SAMPLE_TR = { embryo: "embriyo", oocyte: "oosit", sperm: "sperm" };
export function computeInventory(events) {
  const out = {};
  for (const st of Object.keys(SAMPLE_TR)) {
    const evs = events.filter((e) => e.sample_type === st); if (!evs.length) continue;
    const sum = (k) => evs.filter((e) => e.kind === k).reduce((s, e) => s + (e.count || 0), 0);
    const frozen = sum("freeze"), outs = { thaw: sum("thaw"), use: sum("use"), discard: sum("discard"), transfer_out: sum("transfer_out") };
    const used = outs.use + outs.discard, remaining = frozen - (Math.max(outs.thaw, used) + outs.transfer_out), w = [];
    if (evs.some((e) => e.count == null)) w.push("Bazı kayıtlarda adet boş.");
    if (!evs.some((e) => e.kind === "freeze")) w.push("Dondurma kaydı yok, yalnızca çözme/kullanım kaydı var.");
    if (remaining < 0) w.push("Çözülen/kullanılan sayısı dondurulandan fazla.");
    if (evs.some((e) => e.conflict)) w.push("Aynı kayıt birden fazla dosyada farklı adetle geçiyor.");
    if (outs.thaw && used && outs.thaw !== used) w.push("Çözülen sayısı ile kullanılan+atılan sayısı tutmuyor.");
    out[st] = { type: st, type_tr: SAMPLE_TR[st], frozen, ...outs, remaining: w.length ? remaining : Math.max(remaining, 0), verify: w.length > 0, warnings: w,
      sources: evs.map((e) => ({ file: e.file, ref: e.src_ref, kind: e.kind, count: e.count, date: e.event_date || e.month })) };
  }
  return out;
}
export function inventoryLines(inv) {
  const l = Object.values(inv).map((d) => d.verify ? `Doğrulanmalı (${d.type_tr}): ${d.warnings.join(" ")}`
    : d.remaining > 0 ? `Kayıtlara göre ${d.remaining} ${d.type_tr} kalmış görünüyor.` : `Kayıtlara göre kalan ${d.type_tr} yok.`);
  return l.length ? l : ["Dondurma kaydı bulunamadı."];
}
