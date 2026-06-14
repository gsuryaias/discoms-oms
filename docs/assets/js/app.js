/* App orchestrator — fetch data, manage filter state, render everything, and
   poll for fresh data every 60s.

   Rendering strategy (perf): the 60s poll must NOT yank the map's zoom or rebuild
   work when nothing changed. So:
     - if the new payload's generated_at matches the last one, we only refresh the
       "x min ago" stamp and return (no map/chart/DOM churn);
     - a real data refresh updates markers in place WITHOUT re-fitting bounds;
     - only user actions (filter / drill) re-fit the map. */
window.OMS = window.OMS || {};

/* ---------- shared formatting utils ---------- */
OMS.util = {
  num(n) { return n == null ? "—" : Number(n).toLocaleString("en-IN"); },
  dt(iso) { return iso ? new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—"; },
  // human outage duration from start → now
  dur(iso) {
    if (!iso) return "";
    const ms = Date.now() - new Date(iso).getTime();
    if (ms < 0) return "scheduled";
    const m = Math.floor(ms / 60000), h = Math.floor(m / 60);
    return h ? `${h}h ${m % 60}m` : `${m}m`;
  },
};

OMS.state = {
  payload: null,
  outages: [],
  discoms: new Set(),     // active DISCOM filter
  status: "all",          // all | ongoing | restored
  voltage: "all",
  type: "all",            // all | planned | unplanned
  search: "",
  sort: "ongoing",        // ongoing | consumers | name
  path: [],               // drill-down path [{field, value}, ...]
  lastGen: null,
};

const REFRESH_MS = 60_000;
const STALE_MIN = 40;
const $ = (id) => document.getElementById(id);

async function load() {
  try {
    const res = await fetch(`data/latest.json?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    const firstLoad = !OMS.state.payload;

    OMS.state.payload = payload;
    OMS.state.outages = payload.outages || [];

    if (firstLoad) {
      Object.keys(payload.discoms || {}).forEach((d) => OMS.state.discoms.add(d));
      buildFilters();
    }
    // No new data → just age the timestamp, skip all heavy rendering.
    if (!firstLoad && payload.generated_at === OMS.state.lastGen) {
      renderFreshness();
      return;
    }
    OMS.state.lastGen = payload.generated_at;
    OMS.render(firstLoad);          // re-fit map only on the very first paint
  } catch (err) {
    $("freshnessText").textContent = "Failed to load data — retrying…";
    console.error(err);
  }
}

/* ---------- filtering ---------- */
function matchesPath(o) { return OMS.state.path.every((s) => o[s.field] === s.value); }

function matchesSearch(o) {
  const q = OMS.state.search;
  if (!q) return true;
  const hay = [o.feeder_name, o.district, o.division, o.subdivision, o.section, o.cause,
    ...(o.affected_villages || [])].join(" ").toLowerCase();
  return hay.includes(q);
}

// everything EXCEPT status — KPIs use this so the ongoing/restored split shows
function scopeRows() {
  const s = OMS.state;
  return s.outages.filter((o) =>
    s.discoms.has(o.discom) &&
    matchesPath(o) &&
    (s.voltage === "all" || o.voltage_class === s.voltage) &&
    (s.type === "all" || o.outage_type === s.type) &&
    matchesSearch(o));
}
function filteredRows() {
  const s = OMS.state.status;
  return scopeRows().filter((o) => s === "all" || o.status === s);
}

/* ---------- filter controls ---------- */
function buildFilters() {
  const dc = $("discomChips");
  Object.keys(OMS.state.payload.discoms).forEach((d) =>
    dc.appendChild(chip(d, () => {
      const set = OMS.state.discoms;
      set.has(d) ? set.delete(d) : set.add(d);
      if (set.size === 0) set.add(d);     // never allow empty
      OMS.render(true);
    })));

  const sc = $("statusChips");
  [["all", "All"], ["ongoing", "Ongoing"], ["restored", "Restored"]].forEach(([v, label]) =>
    sc.appendChild(chip(label, () => { OMS.state.status = v; OMS.render(true); }, v)));

  // voltage select: always offer the standard classes (11kV/33kV) so the filter
  // is predictable even when one is momentarily empty, plus anything else seen.
  const STD = ["11kV", "33kV"];
  const found = OMS.state.outages.map((o) => o.voltage_class).filter(Boolean);
  const volts = [...new Set([...STD, ...found])].sort(
    (a, b) => (parseInt(a, 10) || 0) - (parseInt(b, 10) || 0));
  fillSelect($("voltageSelect"), [["all", "All voltages"], ...volts.map((v) => [v, v])], "voltage");
  const types = [...new Set(OMS.state.outages.map((o) => o.outage_type).filter(Boolean))].sort();
  fillSelect($("typeSelect"), [["all", "All types"], ...types.map((t) => [t, cap(t)])], "type");

  // search (debounced) + sort + reset
  let t;
  $("searchBox").addEventListener("input", (e) => {
    clearTimeout(t);
    t = setTimeout(() => { OMS.state.search = e.target.value.trim().toLowerCase(); OMS.render(true); }, 180);
  });
  $("sortSelect").addEventListener("change", (e) => { OMS.state.sort = e.target.value; OMS.render(false); });
  $("resetBtn").addEventListener("click", resetFilters);
}

function fillSelect(el, pairs, stateKey) {
  el.innerHTML = pairs.map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
  el.addEventListener("change", (e) => { OMS.state[stateKey] = e.target.value; OMS.render(true); });
}
function resetFilters() {
  const s = OMS.state;
  s.status = "all"; s.voltage = "all"; s.type = "all"; s.search = ""; s.path = [];
  Object.keys(s.payload.discoms).forEach((d) => s.discoms.add(d));
  $("searchBox").value = ""; $("voltageSelect").value = "all"; $("typeSelect").value = "all";
  OMS.render(true);
}
function chip(label, onClick, value) {
  const b = document.createElement("button");
  b.className = "chip-btn";
  b.textContent = label;
  b.dataset.value = value ?? label;
  b.addEventListener("click", onClick);
  return b;
}
function cap(s) { return s ? s[0].toUpperCase() + s.slice(1) : s; }

function syncControls() {
  document.querySelectorAll("#discomChips .chip-btn").forEach((b) =>
    b.classList.toggle("active", OMS.state.discoms.has(b.dataset.value)));
  document.querySelectorAll("#statusChips .chip-btn").forEach((b) =>
    b.classList.toggle("active", OMS.state.status === b.dataset.value));
  $("voltageSelect").value = OMS.state.voltage;
  $("typeSelect").value = OMS.state.type;
}

/* ---------- KPIs / health / freshness ---------- */
function renderKpis(scope) {
  const ongoing = scope.filter((o) => o.status === "ongoing");
  const restored = scope.filter((o) => o.status === "restored");
  const consumers = ongoing.reduce((s, o) => s + (o.affected_consumers || 0), 0);
  const reporting = Object.values(OMS.state.payload.discoms).filter((d) => d.status === "ok").length;
  const total = Object.keys(OMS.state.payload.discoms).length || 3;
  const cards = [
    { cls: "ongoing", val: OMS.util.num(ongoing.length), lbl: "Ongoing outages" },
    { cls: "restored", val: OMS.util.num(restored.length), lbl: "Restored (today)" },
    { cls: "", val: OMS.util.num(consumers), lbl: "Consumers affected" },
    { cls: "", val: `${reporting}/${total}`, lbl: "DISCOMs reporting" },
  ];
  $("kpis").innerHTML = cards.map((c) =>
    `<div class="kpi ${c.cls}"><div class="val">${c.val}</div><div class="lbl">${c.lbl}</div></div>`).join("");
}

function renderHealth() {
  $("health").innerHTML = Object.entries(OMS.state.payload.discoms).map(([name, s]) => {
    const cls = s.status === "ok" ? "ok" : "error";
    const note = s.status === "ok" ? `${s.count} feeders` : "unreachable";
    return `<div class="chip ${cls}" title="${s.status === 'ok' ? 'Scraped OK' : (s.error || 'error')}">
      <span class="s"></span><b>${name}</b><span class="meta">${note}</span></div>`;
  }).join("");
}

function renderFreshness() {
  const gen = new Date(OMS.state.payload.generated_at);
  const mins = Math.round((Date.now() - gen.getTime()) / 60000);
  const stale = mins > STALE_MIN;
  $("liveDot").className = "dot " + (stale ? "stale" : "live");
  const ago = mins <= 0 ? "just now" : `${mins} min ago`;
  $("freshnessText").textContent =
    `Updated ${ago} · source: ${OMS.state.payload.source} · auto-refresh 60s` +
    (stale ? " · ⚠ data may be stale" : "");
}

/* ---------- master render ---------- */
OMS.render = function (fit) {
  if (!OMS.state.payload) return;
  const scope = scopeRows();
  const filtered = filteredRows();
  renderFreshness();
  renderHealth();
  renderKpis(scope);
  syncControls();
  $("resultCount").textContent = `${filtered.length} of ${OMS.state.outages.length} outages`;
  OMS.drill.render(filtered);
  OMS.map.update(filtered, !!fit);
  OMS.charts.update(filtered);
};

/* ---------- boot ---------- */
window.addEventListener("DOMContentLoaded", () => {
  OMS.map.init();
  OMS.charts.init();
  load();
  setInterval(load, REFRESH_MS);
});
