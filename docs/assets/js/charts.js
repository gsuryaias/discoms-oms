/* Charts module — ECharts donuts/bars that recompute on every filter change.
   Exposes OMS.charts.init() and OMS.charts.update(outages). */
window.OMS = window.OMS || {};
OMS.charts = (function () {
  const C = { ongoing: "#ff5c5c", restored: "#3ad29f", accent: "#4aa8ff", muted: "#8b96a5" };
  const PALETTE = ["#4aa8ff", "#3ad29f", "#f0b429", "#c77dff", "#ff8fab", "#5ad1e8"];
  let cDiscom, cCause, cVoltage;

  const base = {
    backgroundColor: "transparent",
    textStyle: { color: "#c4ccd6", fontSize: 11 },
    grid: { left: 10, right: 16, top: 24, bottom: 8, containLabel: true },
    tooltip: { trigger: "item" },
  };

  function init() {
    cDiscom = echarts.init(document.getElementById("chartDiscom"));
    cCause = echarts.init(document.getElementById("chartCause"));
    cVoltage = echarts.init(document.getElementById("chartVoltage"));
    window.addEventListener("resize", () => {
      cDiscom.resize(); cCause.resize(); cVoltage.resize();
    });
  }

  // group helper: count rows by key, split into ongoing/restored
  function tally(rows, keyFn) {
    const m = new Map();
    for (const r of rows) {
      const k = keyFn(r) || "—";
      const e = m.get(k) || { ongoing: 0, restored: 0 };
      if (r.status === "restored") e.restored++; else e.ongoing++;
      m.set(k, e);
    }
    return m;
  }

  function update(rows) {
    // --- by DISCOM: stacked bar ongoing/restored ---
    const byDiscom = tally(rows, (r) => r.discom);
    const dKeys = [...byDiscom.keys()].sort();
    cDiscom.setOption(Object.assign({}, base, {
      animationDuration: 300,
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { data: ["Ongoing", "Restored"], textStyle: { color: C.muted }, top: 0, right: 0 },
      xAxis: { type: "category", data: dKeys, axisLine: { lineStyle: { color: "#2a3240" } } },
      yAxis: { type: "value", splitLine: { lineStyle: { color: "#1c2330" } } },
      series: [
        { name: "Ongoing", type: "bar", stack: "t", color: C.ongoing,
          data: dKeys.map((k) => byDiscom.get(k).ongoing) },
        { name: "Restored", type: "bar", stack: "t", color: C.restored,
          data: dKeys.map((k) => byDiscom.get(k).restored) },
      ],
    }), true);

    // --- top causes: horizontal bar (ongoing only — what's actionable) ---
    const causeMap = new Map();
    for (const r of rows) if (r.status === "ongoing") {
      const k = r.cause || "Unknown";
      causeMap.set(k, (causeMap.get(k) || 0) + 1);
    }
    const causes = [...causeMap.entries()].sort((a, b) => a[1] - b[1]).slice(-7);
    cCause.setOption(Object.assign({}, base, {
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      xAxis: { type: "value", splitLine: { lineStyle: { color: "#1c2330" } } },
      yAxis: { type: "category", data: causes.map((c) => c[0]), axisLine: { lineStyle: { color: "#2a3240" } } },
      series: [{ type: "bar", color: C.accent, data: causes.map((c) => c[1]),
        label: { show: true, position: "right", color: C.muted } }],
    }), true);

    // --- by voltage: donut ---
    const voltMap = new Map();
    for (const r of rows) {
      const k = r.voltage_class || "—";
      voltMap.set(k, (voltMap.get(k) || 0) + 1);
    }
    cVoltage.setOption(Object.assign({}, base, {
      legend: { bottom: 0, textStyle: { color: C.muted } },
      color: PALETTE,
      series: [{
        type: "pie", radius: ["45%", "70%"], center: ["50%", "45%"],
        itemStyle: { borderColor: "#161b22", borderWidth: 2 },
        label: { color: "#c4ccd6" },
        data: [...voltMap.entries()].map(([name, value]) => ({ name, value })),
      }],
    }), true);
  }

  return { init, update };
})();
