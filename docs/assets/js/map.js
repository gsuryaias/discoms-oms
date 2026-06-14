/* Map module — Leaflet feeder pins. OMS.map.update(rows, fit): when fit is false
   (auto-refresh) markers update in place and the viewport is left untouched, so a
   user who panned/zoomed isn't yanked back every 60s. */
window.OMS = window.OMS || {};
OMS.map = (function () {
  let map, layer;

  function init() {
    map = L.map("map", { zoomControl: true, preferCanvas: true })  // canvas: faster with many markers
      .setView([15.9, 79.9], 7);                                   // centers Andhra Pradesh
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: "© OpenStreetMap, © CARTO", subdomains: "abcd", maxZoom: 19,
    }).addTo(map);
    layer = L.layerGroup().addTo(map);
  }

  // sqrt scaling so a few huge outages don't dwarf everything else
  function radius(n) { return !n ? 6 : Math.max(6, Math.min(26, Math.sqrt(n) / 4)); }

  function popupHtml(r) {
    const approx = r.geo_precision !== "feeder" ? " <i>(approx.)</i>" : "";
    const dur = r.status === "ongoing" ? OMS.util.dur(r.outage_start) : "";
    return `<b>${r.feeder_name || "Feeder"}</b> · ${r.voltage_class || ""}${approx}<br>
      ${r.discom} — ${r.district || ""}<br>
      Status: <b>${r.status}</b>${dur ? ` · out ${dur}` : ""} · ${r.outage_type || ""}<br>
      Cause: ${r.cause || "—"}<br>
      Consumers: ${OMS.util.num(r.affected_consumers)}<br>
      Since: ${OMS.util.dt(r.outage_start)}${r.expected_restoration ? `<br>ETR: ${OMS.util.dt(r.expected_restoration)}` : ""}`;
  }

  function update(rows, fit) {
    if (!map) return;
    layer.clearLayers();
    const pts = [];
    for (const r of rows) {
      if (r.lat == null || r.lng == null) continue;
      const color = r.status === "restored" ? "#3ad29f" : "#ff5c5c";
      const precise = r.geo_precision === "feeder";
      L.circleMarker([r.lat, r.lng], {
        radius: radius(r.affected_consumers),
        color, weight: precise ? 1 : 2, fillColor: color,
        fillOpacity: precise ? 0.7 : 0.12,
        dashArray: precise ? null : "3 3",
      }).bindPopup(popupHtml(r)).addTo(layer);
      pts.push([r.lat, r.lng]);
    }
    if (fit && pts.length) map.fitBounds(pts, { padding: [40, 40], maxZoom: 11 });
  }

  return { init, update };
})();
