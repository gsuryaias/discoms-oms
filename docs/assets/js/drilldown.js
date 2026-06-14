/* Drill-down — DISTRICT → DIVISION → SUBDIVISION → SECTION → FEEDER.
   Breadcrumb + aggregated table (sortable, with a mini load bar); the deepest
   level lists individual outages with live duration + ETR. */
window.OMS = window.OMS || {};
OMS.drill = (function () {
  const LEVELS = [
    { field: "district", label: "District / Circle" },
    { field: "division", label: "Division" },
    { field: "subdivision", label: "Subdivision" },
    { field: "section", label: "Section" },
    { field: "feeder_name", label: "Feeder" },
  ];
  const U = () => OMS.util;

  function setPath(path) { OMS.state.path = path; OMS.render(true); }

  function breadcrumb() {
    const el = document.getElementById("breadcrumb");
    const path = OMS.state.path;
    let html = `<a data-i="0">All AP</a>`;
    path.forEach((step, i) => {
      html += ` <span class="sep">›</span> `;
      html += i === path.length - 1 ? `<span class="cur">${step.value}</span>`
        : `<a data-i="${i + 1}">${step.value}</a>`;
    });
    el.innerHTML = html;
    el.querySelectorAll("a").forEach((a) =>
      a.addEventListener("click", () => setPath(OMS.state.path.slice(0, +a.dataset.i))));
  }

  function sortGroups(entries) {
    const by = OMS.state.sort;
    if (by === "name") return entries.sort((a, b) => a[0].localeCompare(b[0]));
    if (by === "consumers") return entries.sort((a, b) => b[1].consumers - a[1].consumers);
    return entries.sort((a, b) => b[1].ongoing - a[1].ongoing || b[1].consumers - a[1].consumers);
  }

  // rows are already filtered by discom + status + path + voltage/type/search
  function render(rows) {
    breadcrumb();
    const depth = OMS.state.path.length;
    const table = document.getElementById("drillTable");
    if (depth >= LEVELS.length) return renderLeaves(rows, table);

    const level = LEVELS[depth];
    const groups = new Map();
    for (const r of rows) {
      const k = r[level.field] || "—";
      const g = groups.get(k) || { ongoing: 0, restored: 0, consumers: 0 };
      if (r.status === "restored") g.restored++;
      else { g.ongoing++; g.consumers += r.affected_consumers || 0; }
      groups.set(k, g);
    }
    const sorted = sortGroups([...groups.entries()]);
    const maxOng = Math.max(1, ...sorted.map(([, g]) => g.ongoing));

    table.innerHTML = `<thead><tr>
        <th>${level.label}</th><th class="num">Ongoing</th>
        <th class="num">Restored</th><th class="num">Consumers</th><th></th>
      </tr></thead><tbody>${
      sorted.map(([name, g]) => `<tr class="clickable" data-v="${encodeURIComponent(name)}">
        <td class="name">${name}<div class="minibar"><i style="width:${(g.ongoing / maxOng) * 100}%"></i></div></td>
        <td class="num"><span class="badge ongoing">${g.ongoing}</span></td>
        <td class="num"><span class="badge restored">${g.restored}</span></td>
        <td class="num">${U().num(g.consumers)}</td>
        <td class="chev"></td></tr>`).join("")
      }</tbody>`;

    table.querySelectorAll("tr.clickable").forEach((tr) =>
      tr.addEventListener("click", () =>
        setPath([...OMS.state.path, { field: level.field, value: decodeURIComponent(tr.dataset.v) }])));
  }

  function renderLeaves(rows, table) {
    const sorted = [...rows].sort((a, b) => (b.affected_consumers || 0) - (a.affected_consumers || 0));
    table.innerHTML = `<thead><tr><th>${rows.length} outage(s) on this feeder</th></tr></thead>`;
    const body = document.createElement("tbody");
    if (!sorted.length) {
      body.innerHTML = `<tr><td class="meta" style="padding:14px">No outages match the current filters.</td></tr>`;
    }
    for (const r of sorted) {
      const dur = r.status === "ongoing" ? U().dur(r.outage_start) : "";
      const tr = document.createElement("tr");
      tr.innerHTML = `<td><div class="outage-card">
        <div class="row1">
          <span class="feeder">${r.feeder_name || "Feeder"} · ${r.voltage_class || ""}</span>
          <span class="badge ${r.status}">${r.status}${dur ? " · " + dur : ""}</span>
        </div>
        <div class="meta">
          ${r.discom} · ${r.outage_type || ""} · Cause: ${r.cause || "—"}<br>
          ${r.affected_consumers != null ? U().num(r.affected_consumers) + " consumers · " : ""}Since ${U().dt(r.outage_start)}
          ${r.expected_restoration ? "<br>ETR: " + U().dt(r.expected_restoration) : ""}
          ${r.affected_villages && r.affected_villages.length ? "<br>Areas: " + r.affected_villages.join(", ") : ""}
        </div></div></td>`;
      body.appendChild(tr);
    }
    table.appendChild(body);
  }

  return { render, setPath, LEVELS };
})();
