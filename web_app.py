"""Responsive browser interface for the MOS band and carrier visualizer.

Run this file on the computer hosting the simulator, then open the computer's
LAN address from a phone on the same network.
"""

import io
import os
import threading

import matplotlib

matplotlib.use("Agg")
from flask import Flask, jsonify, render_template, request
from matplotlib.figure import Figure

from region_visuals import (draw_curves, draw_scene, mosfet_region_preset,
                            operating_region, predict_mosfet_iv_sweep)


app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
STATE_LOCK = threading.RLock()
STATE = {
    "device": "MOS Capacitor",
    "bulk": "P-type",
    "vg": 0.0,
    "vds": 0.0,
    "region_view": "Follow voltage",
    "view_elev": 24.0,
    "view_azim": -61.0,
}


def _clip(value, low, high):
    return max(low, min(high, float(value)))


def _apply_payload(payload):
    if not isinstance(payload, dict):
        return
    if payload.get("device") in ("MOS Capacitor", "MOSFET"):
        STATE["device"] = payload["device"]
    if payload.get("bulk") in ("P-type", "N-type"):
        STATE["bulk"] = payload["bulk"]

    preset = payload.get("region_view")
    if (STATE["device"] == "MOSFET" and payload.get("bulk") is not None
            and preset is None and STATE["region_view"] != "Follow voltage"):
        preset = STATE["region_view"]
    if STATE["device"] == "MOSFET" and preset in ("Cutoff", "Linear", "Saturation"):
        STATE["region_view"] = preset
        STATE["vg"], STATE["vds"] = mosfet_region_preset(STATE["bulk"], preset)
    else:
        if preset == "Follow voltage" or STATE["device"] == "MOS Capacitor":
            STATE["region_view"] = "Follow voltage"
        manual_voltage = "vg" in payload or "vds" in payload
        if manual_voltage and STATE["device"] == "MOSFET":
            STATE["region_view"] = "Follow voltage"
        if "vg" in payload:
            STATE["vg"] = _clip(payload["vg"], -3, 3)
        if "vds" in payload:
            STATE["vds"] = _clip(payload["vds"], -3, 3)

    if STATE["device"] == "MOS Capacitor":
        STATE["vds"] = 0.0
    elif STATE["bulk"] == "P-type":
        STATE["vds"] = _clip(STATE["vds"], 0, 3)
    else:
        STATE["vds"] = _clip(STATE["vds"], -3, 0)
    STATE["view_elev"] = _clip(payload.get("view_elev", STATE["view_elev"]), 0, 90)
    STATE["view_azim"] = _clip(payload.get("view_azim", STATE["view_azim"]), -180, 180)


def _svg_for(kind):
    figure = Figure(figsize=(12, 7), dpi=100, constrained_layout=True)
    if kind == "band":
        draw_scene(figure, STATE["device"], phase=0.0, bulk_type=STATE["bulk"],
                   vg=STATE["vg"], vds=STATE["vds"], view_elev=STATE["view_elev"],
                   view_azim=STATE["view_azim"])
    else:
        draw_curves(figure, STATE["device"], STATE["bulk"], STATE["vg"], STATE["vds"])
    output = io.StringIO()
    figure.savefig(output, format="svg", metadata={"Creator": "Fermi Level Simulator"})
    figure.clear()
    return output.getvalue()


def _snapshot():
    region = operating_region(STATE["device"], STATE["bulk"], STATE["vg"], STATE["vds"])
    return {
        "state": dict(STATE),
        "region": region,
        "status": f"{region} · {STATE['device']} · {STATE['bulk']} bulk",
        "band_svg": _svg_for("band"),
        "curve_svg": _svg_for("curve"),
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.route("/api/state", methods=["GET", "POST"])
def state():
    with STATE_LOCK:
        if request.method == "POST":
            _apply_payload(request.get_json(silent=True) or {})
        return jsonify(_snapshot())


def _parse_vg_list(raw):
    if raw is None or not str(raw).strip():
        return None
    values = []
    for token in str(raw).replace("，", ",").replace(";", ",").split(","):
        token = token.strip()
        if token:
            values.append(float(token))
    return values


@app.post("/api/predict")
def predict():
    payload = request.get_json(silent=True) or {}
    with STATE_LOCK:
        if STATE["device"] != "MOSFET":
            return jsonify({"error": "Vt / Idsat 預測器僅適用於 MOSFET。"}), 400
        try:
            anchor = float(payload.get("anchor_vg", STATE["vg"]))
            vt = float(payload.get("vt", 0.8))
            idsat = float(payload.get("idsat", 0.5))
            step = float(payload.get("step", 0.1))
            points = int(payload.get("points", 5))
            specified = _parse_vg_list(payload.get("specified_vgs", ""))
            result = predict_mosfet_iv_sweep(STATE["bulk"], anchor, vt, idsat, step, points,
                                             specified_vgs=specified)
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
        result["bulk"] = STATE["bulk"]
        result["note"] = ("以輸入 pinch-off 錨點反推 k = 2Idsat/VOV²；"
                           "各 Vg 的 pinch-off 發生於 |VDS|=VOV。")
        return jsonify(result)


if __name__ == "__main__":
    app.run(host=os.environ.get("FERMI_HOST", "0.0.0.0"),
            port=int(os.environ.get("FERMI_PORT", "5000")),
            debug=False, threaded=True)
