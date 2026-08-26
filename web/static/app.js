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
    <td>${Number(row.overdrive).toFixed(3)}</td><td>${Number(row.idsat).toFixed(4)}</td>
    <td class="region-${row.region.toLowerCase()}">${row.region}</td></tr>`).join("");
  $("predictor-message").textContent = `${data.note} ${data.source === "specified" ? "使用指定 Vg 清單。" : `由 ${Number(data.anchor_vg).toFixed(3)} V 每次下降 ${Number(data.step).toFixed(3)} V。`}`;
}

async function predict() {
  const response = await fetch("/api/predict", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      anchor_vg: Number($("vg").value),
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
