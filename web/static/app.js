const $ = (id) => document.getElementById(id);
let updateTimer = null;
let pending = {};

function formatVoltage(value) {
  return `${Number(value).toFixed(3)} V`;
}

function syncControls(data) {
  const state = data.state;
  $("device").value = state.device;
  $("bulk").value = state.bulk;
  $("region-view").value = state.region_view;
  $("vg").value = state.vg;
  $("vds").value = state.vds;
  $("view-elev").value = state.view_elev;
  $("view-azim").value = state.view_azim;
  $("vg-label").textContent = state.device === "MOSFET" ? "Vgs" : "Vg";
  $("vds-label").textContent = "Vds";
  $("vg-value").textContent = formatVoltage(state.vg);
  $("vds-value").textContent = formatVoltage(state.vds);
  $("elev-value").textContent = `${Math.round(state.view_elev)}°`;
  $("azim-value").textContent = `${Math.round(state.view_azim)}°`;
  $("vds-control").hidden = state.device !== "MOSFET";
  $("view-controls").hidden = state.device !== "MOSFET";
  $("region-view").disabled = state.device !== "MOSFET";
  $("predictor-panel").hidden = state.device !== "MOSFET";
  $("region").textContent = data.region;
  $("status").textContent = data.status;
}

function renderPrediction(data) {
  const body = $("prediction-body");
  body.innerHTML = data.rows.map((row) => `
    <tr><td>${Number(row.vg).toFixed(3)}</td><td>${Number(row.vt).toFixed(3)}</td>
    <td>${Number(row.overdrive).toFixed(3)}</td><td>${Number(row.pinch_off_vds).toFixed(3)}</td><td>${Number(row.idsat).toFixed(4)}</td>
    <td class="region-${row.region.toLowerCase()}">${row.region}</td></tr>`).join("");
  $("predictor-message").textContent = `${data.note} 反推 k=${Number(data.k).toFixed(4)}；${data.source === "specified" ? "使用指定 Vg 清單。" : `由 ${Number(data.anchor_vg).toFixed(3)} V 每次下降 ${Number(data.step).toFixed(3)} V。`}`;
  const width = 720, height = 250, pad = 42;
  const allVds = data.curves.flatMap(c => c.vds), allId = data.curves.flatMap(c => c.id);
  const xmax = Math.max(...allVds.map(Math.abs), .1), ymax = Math.max(...allId.map(Math.abs), .01);
  const x = v => pad + (Math.abs(v) / xmax) * (width - pad - 12);
  const y = v => height - pad - (Math.abs(v) / ymax) * (height - pad - 12);
  const colors = ["#1877c9", "#762aa5", "#d84343", "#2e7d32", "#ef8a00", "#00838f", "#6d4c41", "#455a64"];
  const paths = data.curves.map((curve, i) => {
    const points = curve.vds.map((v, j) => `${x(v).toFixed(1)},${y(curve.id[j]).toFixed(1)}`).join(" L");
    return `<path d="M${points}" fill="none" stroke="${colors[i % colors.length]}" stroke-width="2"/><text x="${width - 118}" y="${25 + i*18}" fill="${colors[i % colors.length]}">Vg=${Number(curve.vg).toFixed(2)} V</text>`;
  }).join("");
  $("predictor-plot").innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img"><line x1="${pad}" y1="${height-pad}" x2="${width-10}" y2="${height-pad}" stroke="#63758a"/><line x1="${pad}" y1="10" x2="${pad}" y2="${height-pad}" stroke="#63758a"/><text x="${width/2}" y="${height-8}" text-anchor="middle">|VDS| (V)</text><text x="12" y="${height/2}" transform="rotate(-90 12 ${height/2})" text-anchor="middle">|ID|</text>${paths}</svg>`;
}

async function predict() {
  const response = await fetch("/api/predict", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      anchor_vg: Number($("vg").value),
      vt: Number($("predict-vt").value),
      idsat: Number($("predict-idsat").value),
      step: Number($("predict-step").value),
      points: Number($("predict-points").value),
      specified_vgs: $("predict-specified").value,
    }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  renderPrediction(data);
}

function render(data) {
  syncControls(data);
  $("band-panel").innerHTML = data.band_svg;
  $("curve-panel").innerHTML = data.curve_svg;
}

async function update(extra = {}) {
  const response = await fetch("/api/state", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(extra),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  render(await response.json());
}

function queueUpdate(extra) {
  pending = { ...pending, ...extra };
  clearTimeout(updateTimer);
  updateTimer = setTimeout(async () => {
    const payload = pending;
    pending = {};
    try { await update(payload); }
    catch (error) { $("status").textContent = `連線錯誤：${error.message}`; }
  }, 70);
}

$("device").addEventListener("change", (event) => queueUpdate({ device: event.target.value }));
$("bulk").addEventListener("change", (event) => queueUpdate({ bulk: event.target.value }));
$("region-view").addEventListener("change", (event) => queueUpdate({ region_view: event.target.value }));
$("vg").addEventListener("input", (event) => {
  $("vg-value").textContent = formatVoltage(event.target.value);
  queueUpdate({ vg: Number(event.target.value) });
});
$("vds").addEventListener("input", (event) => {
  $("vds-value").textContent = formatVoltage(event.target.value);
  queueUpdate({ vds: Number(event.target.value) });
});
$("view-elev").addEventListener("input", (event) => {
  $("elev-value").textContent = `${event.target.value}°`;
  queueUpdate({ view_elev: Number(event.target.value) });
});
$("view-azim").addEventListener("input", (event) => {
  $("azim-value").textContent = `${event.target.value}°`;
  queueUpdate({ view_azim: Number(event.target.value) });
});
$("reset-view").addEventListener("click", () => queueUpdate({ view_elev: 24, view_azim: -61 }));
$("predict-button").addEventListener("click", async () => {
  $("predictor-message").textContent = "正在計算…";
  try { await predict(); }
  catch (error) { $("predictor-message").textContent = `預測失敗：${error.message}`; }
});

document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("active", item === tab));
  document.querySelectorAll(".plot").forEach((plot) => plot.classList.toggle("active", plot.id === `${tab.dataset.tab}-panel`));
}));

fetch("/api/state").then((response) => response.json()).then(render).catch((error) => {
  $("status").textContent = `無法連線：${error.message}`;
});
