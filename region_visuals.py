"""Voltage-driven qualitative MOS band and carrier scenes.

Only terminal voltages and bulk polarity are inputs.  Energy and carrier count
are schematic; no oxide capacitance, dimensions, or process parameters enter.
"""

import numpy as np
from matplotlib.patches import Rectangle, Polygon


BLUE, RED, GREEN, PURPLE, GRAY = "#1976d2", "#d84343", "#2e7d32", "#7b1fa2", "#555555"
ORANGE, OXIDE, SILICON, METAL = "#ef8a00", "#f2ca83", "#e8eef6", "#8b95a5"
REGIONS = {"MOS Capacitor": ("Accumulation", "Flat-band", "Depletion", "Inversion"),
           "MOSFET": ("Cutoff", "Linear", "Saturation")}
NORMALIZED_PHI_F = .30
NORMALIZED_VT = .80


def moscap_operating_point(bulk_type, vg):
    polarity = 1.0 if bulk_type == "P-type" else -1.0
    psi_s = .95*np.tanh(vg/1.25)
    effective_surface = polarity*psi_s
    if abs(effective_surface) <= .08:
        region = "Flat-band"
    elif effective_surface < 0:
        region = "Accumulation"
    elif effective_surface < 2*NORMALIZED_PHI_F-1e-12:
        region = "Depletion"
    else:
        region = "Inversion"
    return {"polarity": polarity, "psi_s": psi_s,
            "phi_f": polarity*NORMALIZED_PHI_F,
            "effective_surface": effective_surface, "region": region}


def mosfet_operating_point(bulk_type, vgs, vds, vt=NORMALIZED_VT, k=1.0):
    polarity = 1.0 if bulk_type == "P-type" else -1.0
    gate_drive = polarity*vgs
    drain_drive_raw = polarity*vds
    drain_polarity_valid = drain_drive_raw >= -1e-12
    drain_drive = max(drain_drive_raw, 0.0)
    overdrive = gate_drive-vt
    if overdrive <= 0:
        region, current_magnitude = "Cutoff", 0.0
    elif drain_drive < overdrive-1e-12:
        region = "Linear"
        current_magnitude = k*(overdrive*drain_drive-.5*drain_drive**2)
    else:
        region = "Saturation"
        current_magnitude = .5*k*overdrive**2
    return {"polarity": polarity, "gate_drive": gate_drive,
            "drain_drive": drain_drive, "drain_polarity_valid": drain_polarity_valid,
            "overdrive": overdrive, "region": region,
            "current_magnitude": current_magnitude,
            "current_signed": polarity*current_magnitude,
            "vgd": vgs-vds, "vt": vt, "k": k}


def operating_region(device, bulk_type, vg, vds=0.0):
    """Return the qualitative region using fixed normalized voltage boundaries."""
    if device == "MOS Capacitor":
        return moscap_operating_point(bulk_type, vg)["region"]
    return mosfet_operating_point(bulk_type, vg, vds)["region"]


def mosfet_region_preset(bulk_type, region):
    """Return representative normalized biases for a requested MOSFET region."""
    presets = {"Cutoff": (.40, .20),
               "Linear": (1.80, .30),
               "Saturation": (1.80, 1.30)}
    if region not in presets:
        raise ValueError(f"Unknown MOSFET region preset: {region}")
    polarity = 1.0 if bulk_type == "P-type" else -1.0
    vgs, vds = presets[region]
    return polarity*vgs, polarity*vds


def predict_mosfet_vt_idsat(bulk_type, anchor_vg, step=0.1, points=5,
                            specified_vgs=None, vt=NORMALIZED_VT, k=1.0):
    """Predict lower gate-drive points with the normalized square-law model.

    A single Vg cannot physically extract VT and k.  This teaching helper keeps
    VT and k explicit, then sweeps the effective gate drive toward cutoff.  For
    pMOS the signed voltages are mirrored, while the reported VT and VOV are
    magnitudes so NMOS and pMOS can be compared directly.
    """
    if bulk_type not in ("P-type", "N-type"):
        raise ValueError("bulk_type must be P-type or N-type")
    step = float(step)
    points = int(points)
    vt = float(vt)
    k = float(k)
    if step <= 0:
        raise ValueError("step must be positive")
    if points < 2 or points > 12:
        raise ValueError("points must be between 2 and 12")
    if vt < 0 or k <= 0:
        raise ValueError("vt must be non-negative and k must be positive")
    polarity = 1.0 if bulk_type == "P-type" else -1.0
    anchor_vg = float(anchor_vg)
    if specified_vgs is None:
        anchor_drive = max(polarity * anchor_vg, 0.0)
        vgs = [polarity * max(anchor_drive - i * step, 0.0)
               for i in range(points)]
        source = "step"
    else:
        vgs = [float(value) for value in specified_vgs]
        if not vgs:
            raise ValueError("specified_vgs cannot be empty")
        if len(vgs) > 12:
            raise ValueError("specified_vgs cannot contain more than 12 values")
        source = "specified"

    rows = []
    for vg in vgs:
        drive = max(polarity * vg, 0.0)
        overdrive = max(drive - vt, 0.0)
        idsat = 0.5 * k * overdrive**2 if overdrive > 0 else 0.0
        rows.append({"vg": float(vg), "gate_drive": float(drive),
                     "vt": float(vt), "overdrive": float(overdrive),
                     "idsat": float(idsat),
                     "region": "Saturation" if overdrive > 0 else "Cutoff"})
    return {"rows": rows, "source": source, "anchor_vg": anchor_vg,
            "step": step, "points": len(rows), "vt": vt, "k": k}


def predict_mosfet_iv_sweep(bulk_type, anchor_vg, vt, idsat, step=0.1,
                            points=5, specified_vgs=None, samples=41):
    """Infer k from one measured pinch-off point and predict lower-Vg Id-Vds curves."""
    result = predict_mosfet_vt_idsat(bulk_type, anchor_vg, step, points,
                                     specified_vgs=specified_vgs, vt=vt, k=1.0)
    anchor_drive = max(result["rows"][0]["gate_drive"], 0.0)
    anchor_overdrive = anchor_drive - float(vt)
    idsat = float(idsat)
    if anchor_overdrive <= 0 or idsat < 0:
        raise ValueError("anchor Vg must exceed Vt and Idsat must be non-negative")
    k = 2.0 * idsat / anchor_overdrive**2
    if k <= 0:
        raise ValueError("Idsat must be positive for a pinch-off anchor")
    polarity = 1.0 if bulk_type == "P-type" else -1.0
    curves = []
    for row in result["rows"]:
        overdrive = row["overdrive"]
        vds_cutoff = max(overdrive, 0.0)
        vds_drive = np.linspace(0.0, max(1.25*vds_cutoff, .1), int(samples))
        current = np.where(vds_drive < vds_cutoff,
                           k*(overdrive*vds_drive - .5*vds_drive**2),
                           .5*k*overdrive**2)
        row["idsat"] = float(.5*k*overdrive**2)
        row["pinch_off_vds"] = float(polarity*vds_cutoff)
        curves.append({"vg": row["vg"], "vds": (polarity*vds_drive).tolist(),
                       "id": (polarity*current).tolist(),
                       "idsat": row["idsat"],
                       "pinch_off_vds": row["pinch_off_vds"]})
    return {"rows": result["rows"], "curves": curves, "source": result["source"],
            "anchor_vg": result["anchor_vg"], "anchor_vt": float(vt),
            "anchor_idsat": idsat, "step": result["step"],
            "points": len(result["rows"]), "vt": float(vt), "k": float(k)}


def _flow_dots(start, end, count, phase):
    t = (np.linspace(0, 1, count, endpoint=False) + phase) % 1.0
    return start + (end - start) * t


def _carrier(ax, x, y, kind, size=44, alpha=.92, is3d=False, z=None):
    x, y = np.broadcast_arrays(np.asarray(x), np.asarray(y))
    kwargs = dict(s=size, alpha=alpha, zorder=7)
    if kind == "electron":
        kwargs.update(c=BLUE, edgecolors="white", linewidths=.6)
    else:
        kwargs.update(facecolors="white", edgecolors=RED, linewidths=1.5)
    if is3d:
        ax.scatter(x, y, z, depthshade=False, **kwargs)
    else:
        ax.scatter(x, y, **kwargs)


def _charge_symbols(ax, x, ys, sign):
    color = RED if sign == "+" else BLUE
    for y in ys:
        ax.text(x, y, sign, color=color, fontsize=14, weight="bold", ha="center", va="center")


def draw_scene(fig, device, region=None, phase=0.0, bulk_type="P-type", vg=0.0, vds=0.0,
               view_elev=24.0, view_azim=-61.0):
    fig.clear()
    region = region or operating_region(device, bulk_type, vg, vds)
    if device == "MOS Capacitor":
        return _draw_moscap(fig, region, phase, bulk_type, vg)
    return _draw_mosfet(fig, region, phase, bulk_type, vg, vds, view_elev, view_azim)


def _draw_moscap(fig, region, phase, bulk_type, vg):
    grid = fig.add_gridspec(2, 2, height_ratios=(4.8, 1.45))
    ax_band = fig.add_subplot(grid[0, 0])
    ax_device = fig.add_subplot(grid[0, 1])
    ax_formula = fig.add_subplot(grid[1, :])
    point = moscap_operating_point(bulk_type, vg)
    region = point["region"]
    p_bulk = bulk_type == "P-type"
    majority = "hole" if p_bulk else "electron"
    minority = "electron" if p_bulk else "hole"
    polarity = 1.0 if p_bulk else -1.0

    # Gate Fermi energy moves by -qVg relative to body EF=0.  Positive Vg bends
    # the silicon bands downward; negative Vg bends them upward.
    ef_gate = -vg
    bend = -point["psi_s"]
    si_x = np.linspace(0, 1.2, 260)
    ei_bulk = NORMALIZED_PHI_F if p_bulk else -NORMALIZED_PHI_F
    ei_si = ei_bulk + bend * np.exp(-si_x/.24)
    ec_si, ev_si, evac_si = ei_si + .56, ei_si - .56, ei_si + 1.42
    ox_x = np.linspace(-.55, 0, 50)
    # With the idealized equal-work-function reference, oxide bands are flat at
    # Vg=0 and tilt only with the applied gate-to-body potential.
    ec_ox = np.linspace(ef_gate + 1.90, 1.90, len(ox_x))
    ev_ox, evac_ox = ec_ox - 3.15, ec_ox + .42
    gate_x = np.array([-.95, -.55])

    ax_band.axvspan(-.95, -.55, color=METAL, alpha=.18)
    ax_band.axvspan(-.55, 0, color=OXIDE, alpha=.25)
    ax_band.axvspan(0, 1.2, color=SILICON, alpha=.38)
    ax_band.plot(gate_x, [ef_gate, ef_gate], color=PURPLE, lw=2.5, label="gate Ef")
    ax_band.plot(gate_x, [ef_gate+.78, ef_gate+.78], color=GRAY, lw=1.7, label="Evac")
    ax_band.plot(ox_x, ec_ox, color=BLUE, lw=2.0, label="oxide Ec")
    ax_band.plot(ox_x, ev_ox, color=RED, lw=2.0, label="oxide Ev")
    ax_band.plot(ox_x, evac_ox, color=GRAY, lw=1.4)
    ax_band.plot(si_x, ec_si, color=BLUE, lw=2.5, label="silicon Ec")
    ax_band.plot(si_x, ei_si, color=GREEN, lw=1.8, ls="--", label="silicon Ei")
    ax_band.plot(si_x, ev_si, color=RED, lw=2.5, label="silicon Ev")
    ax_band.plot(si_x, evac_si, color=GRAY, lw=1.5)
    ax_band.plot(si_x, np.zeros_like(si_x), color=PURPLE, lw=2.2, label="body Ef")
    ax_band.plot([-.55, 0], [ef_gate, 0], color=ORANGE, lw=1.5, ls=":", label="electrostatic drop")
    ax_band.axvline(-.55, color="#8b6d30", lw=1.1)
    ax_band.axvline(0, color="#444444", lw=1.5)
    ax_band.text(-.75, .96, "METAL GATE", transform=ax_band.get_xaxis_transform(), ha="center", weight="bold", fontsize=9)
    ax_band.text(-.275, .96, "OXIDE", transform=ax_band.get_xaxis_transform(), ha="center", weight="bold", fontsize=9)
    ax_band.text(.60, .96, f"{bulk_type.upper()} SILICON", transform=ax_band.get_xaxis_transform(), ha="center", weight="bold", fontsize=9)
    if abs(vg) < .04:
        ax_band.text(-.34, .08, "gate Ef aligned with body Ef", color=PURPLE, fontsize=9)
    else:
        mid_y = .5 * ef_gate
        ax_band.annotate(f"qVg = {vg:+.2f} eV", xy=(-.32, 0), xytext=(-.32, ef_gate),
                         arrowprops=dict(arrowstyle="<->", color=ORANGE, lw=1.7), color=ORANGE,
                         ha="center", va="center")
        ax_band.text(-.27, mid_y, "Ef shift", color=ORANGE, fontsize=8, va="center")
    band_note = "flat silicon bands" if region == "Flat-band" else "silicon band bending"
    note_y = ei_bulk + (.34 if region == "Flat-band" else .72*np.sign(bend))
    ax_band.annotate(band_note, xy=(.06, ei_si[12]), xytext=(.45, note_y),
                     arrowprops=dict(arrowstyle="->", color=GREEN), color=GREEN, fontsize=9)
    ax_band.set_title(f"Gate / oxide / silicon bands — {region}", fontsize=13, weight="bold")
    ax_band.set_xlabel("Position through stack")
    ax_band.set_ylabel("Normalized electron energy")
    ax_band.set_xticks([-.75, -.275, .6], ["gate", "oxide", "silicon bulk"])
    ax_band.grid(alpha=.13)
    handles, labels = ax_band.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax_band.legend(unique.values(), unique.keys(), fontsize=8, ncol=3, loc="best")

    # Cross-section and carrier motion.
    ax_device.set_xlim(0, 10); ax_device.set_ylim(0, 7); ax_device.set_aspect("equal")
    ax_device.add_patch(Rectangle((.65, 1), 1.6, 5, facecolor=METAL, edgecolor="#4b5563"))
    ax_device.add_patch(Rectangle((2.25, 1), .85, 5, facecolor=OXIDE, edgecolor="#a46f18"))
    ax_device.add_patch(Rectangle((3.1, 1), 6.25, 5, facecolor=SILICON, edgecolor="#7890aa"))
    ax_device.text(1.45, 6.28, f"Gate  Vg={vg:+.2f} V", ha="center", weight="bold")
    ax_device.text(2.68, .65, "oxide", ha="center")
    ax_device.text(6.2, .65, f"{bulk_type} bulk · body=0 V", ha="center")
    charge_count = max(3, min(10, 3 + int(abs(vg)*2.4)))
    charge_ys = np.linspace(1.45, 5.5, charge_count)
    gate_sign = "+" if vg > .04 else "−" if vg < -.04 else "0"
    if gate_sign != "0":
        _charge_symbols(ax_device, 2.05, charge_ys, gate_sign)
    else:
        ax_device.text(2.05, 3.5, "neutral", rotation=90, ha="center", color=GRAY)

    ys = np.linspace(1.4, 5.5, 8)
    if region == "Flat-band":
        bulk_x = np.linspace(3.45, 8.8, 18)
        bulk_y = 1.45 + 3.9*((np.arange(18)*7) % 17)/16
        _carrier(ax_device, bulk_x, bulk_y, majority, 42, .72)
        ax_device.text(6.2, 5.72, "no net interface redistribution", ha="center", color=GRAY)
        detail = "gate Ef aligns with body Ef and the silicon bands are flat"
    elif region == "Accumulation":
        strength = max(1, min(4, 1 + int(abs(vg)*1.4)))
        for layer in range(strength):
            _carrier(ax_device, np.full(len(ys), 3.25 + .20*layer), ys, majority, 52)
        moving = _flow_dots(7.5, 3.3, 6, phase)
        _carrier(ax_device, moving, 5.68 + .06*np.sin(moving*4), majority, 48)
        color = RED if majority == "hole" else BLUE
        ax_device.annotate(f"{majority}s → interface", xy=(3.25,5.75), xytext=(7.25,5.75),
                           arrowprops=dict(arrowstyle="-|>", color=color, lw=2.2), color=color, ha="center")
        detail = f"majority {majority}s accumulate at the interface"
    elif region == "Depletion":
        width = .55 + 1.25*min(abs(vg), .9)/.9
        ax_device.add_patch(Rectangle((3.1,1), width,5, facecolor="#fff3c4", edgecolor="none", alpha=.82))
        fixed_sign = "−" if p_bulk else "+"
        _charge_symbols(ax_device, 3.35 + width*.35, np.linspace(1.55,5.35,6), fixed_sign)
        if abs(vg) > .05:
            moving = _flow_dots(3.35, 7.3, 6, phase)
            _carrier(ax_device, moving, 5.68 + .06*np.sin(moving*4), majority, 46)
            color = RED if majority == "hole" else BLUE
            ax_device.annotate(f"{majority}s repelled", xy=(7.3,5.75), xytext=(3.4,5.75),
                               arrowprops=dict(arrowstyle="-|>", color=color, lw=2.2), color=color)
        ax_device.text(3.2+width/2, 3.4, "depletion\nfixed bulk charge", ha="center", color="#806000")
        detail = "majority carriers leave the surface and expose fixed bulk charge"
    else:
        width = 1.25
        ax_device.add_patch(Rectangle((3.1,1), width,5, facecolor="#fff3c4", edgecolor="none", alpha=.65))
        for layer in range(2 + min(2, int((abs(vg)-.9)*1.2))):
            _carrier(ax_device, np.full(len(ys), 3.22 + .19*layer), ys, minority, 54)
        moving = _flow_dots(7.5, 3.25, 6, phase)
        _carrier(ax_device, moving, 5.68 + .06*np.sin(moving*4), minority, 48)
        color = BLUE if minority == "electron" else RED
        ax_device.annotate(f"{minority}s → inversion interface", xy=(3.22,5.75), xytext=(7.2,5.75),
                           arrowprops=dict(arrowstyle="-|>", color=color, lw=2.2), color=color, ha="center")
        detail = f"minority {minority}s form the inversion layer"
    ax_device.set_title("Gate charge and interface carriers", fontsize=13, weight="bold")
    ax_device.axis("off")
    _draw_moscap_formula(ax_formula, bulk_type, vg, region)
    fig.suptitle(f"{bulk_type} MOS capacitor · Vg={vg:+.2f} V · {region}", fontsize=14)
    return f"{region}: gate Ef={ef_gate:+.2f} eV relative to body Ef; {detail}."


def _draw_moscap_formula(ax, bulk_type, vg, region):
    point = moscap_operating_point(bulk_type, vg)
    p_bulk = bulk_type == "P-type"
    polarity = point["polarity"]
    psi_s = point["psi_s"]
    psi_eff = point["effective_surface"]
    phi_f = point["phi_f"]
    region = point["region"]
    ef_shift = -vg
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.set_title("Live mathematical derivation (normalized teaching model)", loc="left", fontsize=11, weight="bold")
    left_1 = (r"$\phi_F^{*}=" + (r"+" if p_bulk else r"-")
              + r"\frac{kT}{q}\ln\!\left(\frac{N_{\mathrm{sub}}}{n_i}\right)="
              + f"{phi_f:+.3f}" + r"\ \mathrm{V},\qquad 2|\phi_F^{*}|="
              + f"{2*NORMALIZED_PHI_F:.3f}" + r"\ \mathrm{V}$")
    left_2 = (r"$\psi_s^{*}=0.95\tanh\!\left(\frac{V_G}{1.25\ \mathrm{V}}\right)="
              + f"{psi_s:+.3f}" + r"\ \mathrm{V},\qquad "
              + r"\Delta E_{c,i,v}(0)=-q\psi_s^{*}=" + f"{-psi_s:+.3f}" + r"\ \mathrm{eV}$")
    left_3 = (r"$E_F^{G}-E_F^{B}=-qV_G=" + f"{ef_shift:+.3f}" + r"\ \mathrm{eV},\qquad "
              + r"\frac{n_s}{n_0}=e^{\psi_s^{*}/V_T},\quad\frac{p_s}{p_0}=e^{-\psi_s^{*}/V_T}$")
    if p_bulk:
        cases = (r"$\psi_s<0:\ \mathrm{Accumulation};\quad \psi_s=0:\ \mathrm{Flat\!\!-\!\!band};\quad "
                 r"0<\psi_s<2\phi_F:\ \mathrm{Depletion};\quad \psi_s\geq2\phi_F:\ \mathrm{Strong\ inversion}$")
    else:
        cases = (r"$\psi_s>0:\ \mathrm{Accumulation};\quad \psi_s=0:\ \mathrm{Flat\!\!-\!\!band};\quad "
                 r"-2|\phi_F|<\psi_s<0:\ \mathrm{Depletion};\quad \psi_s\leq-2|\phi_F|:\ \mathrm{Strong\ inversion}$")
    region_math = region.replace("-", r"\!-\!").replace(" ", r"\ ")
    live = (r"$\psi_{\mathrm{eff}}=" + (r"+\psi_s" if p_bulk else r"-\psi_s")
            + f"={psi_eff:+.3f}" + r"\ \mathrm{V}\ \Longrightarrow\ \mathbf{\mathrm{" + region_math + r"}}$")
    ax.text(.01, .73, left_1, fontsize=10.5, va="center")
    ax.text(.01, .43, left_2, fontsize=10.5, va="center")
    ax.text(.01, .13, left_3, fontsize=10.5, va="center")
    ax.text(.54, .58, cases, fontsize=10.0, va="center")
    ax.text(.67, .18, live, fontsize=11.0, va="center", color=PURPLE)


def _draw_mosfet(fig, region, phase, bulk_type, vgs, vds, view_elev, view_azim):
    grid = fig.add_gridspec(2, 2, height_ratios=(4.8, 1.55))
    ax_device = fig.add_subplot(grid[0, 0])
    ax_band = fig.add_subplot(grid[0, 1], projection="3d")
    ax_formula = fig.add_subplot(grid[1, :])
    point = mosfet_operating_point(bulk_type, vgs, vds)
    region = point["region"]
    p_bulk = bulk_type == "P-type"
    polarity = point["polarity"]
    device_name = "nMOS" if p_bulk else "pMOS"
    contact = "n+" if p_bulk else "p+"
    carrier = "electron" if p_bulk else "hole"
    color = BLUE if p_bulk else RED
    effective_gate = point["gate_drive"]
    control = np.clip(point["overdrive"]/1.8, 0, 1)
    effective_drain = point["drain_drive"]

    ax_device.set_xlim(0, 12); ax_device.set_ylim(0, 7.2); ax_device.set_aspect("equal")
    ax_device.add_patch(Rectangle((.5,.6),11,4.7,facecolor=SILICON,edgecolor="#7890aa"))
    contact_color = "#bad9ff" if p_bulk else "#ffd0d0"
    ax_device.add_patch(Rectangle((1,3.9),2.1,1.4,facecolor=contact_color,edgecolor=color))
    ax_device.add_patch(Rectangle((8.9,3.9),2.1,1.4,facecolor=contact_color,edgecolor=color))
    ax_device.add_patch(Rectangle((3.1,4.75),5.8,.55,facecolor=OXIDE,edgecolor="#a46f18"))
    ax_device.add_patch(Rectangle((3.4,5.3),5.2,1.0,facecolor=METAL,edgecolor="#4b5563"))
    ax_device.text(2.05,4.55,f"{contact} Source",ha="center",weight="bold")
    ax_device.text(9.95,4.55,f"{contact} Drain",ha="center",weight="bold")
    ax_device.text(6,5.78,"Gate",ha="center",color="white",weight="bold")
    ax_device.text(6,1.0,f"{bulk_type} body",ha="center")
    ax_device.text(6,6.78,f"Vgs={vgs:+.2f} V   Vds={vds:+.2f} V   Vs=Vb=0",ha="center",weight="bold")
    if abs(vgs) > .04:
        _charge_symbols(ax_device, 6, np.linspace(5.42,6.1,5), "+" if vgs > 0 else "−")
    if region == "Cutoff":
        ax_device.plot([3.1,8.9],[4.62,4.62],color="#999999",ls=":")
        ax_device.text(6,4.25,"no inversion channel",ha="center",color=GRAY)
    else:
        if region == "Linear":
            shape = Rectangle((3.05,4.38),5.9,.34,facecolor=color,edgecolor="none",alpha=.28)
            carrier_x = np.linspace(3.2,8.8,17)
        else:
            if p_bulk:
                points = [[3.05,4.38],[8.12,4.38],[8.88,4.7],[3.05,4.7]]
            else:
                points = [[3.05,4.38],[8.12,4.38],[8.88,4.7],[3.05,4.7]]
            shape = Polygon(points,closed=True,facecolor=color,edgecolor="none",alpha=.28)
            carrier_x = np.sort(3.2 + 5.1*(1-np.linspace(0,1,15)**1.8))
        ax_device.add_patch(shape)
        _carrier(ax_device,carrier_x,4.55+.03*np.sin(carrier_x*3),carrier,46)
        # The animated markers always show physical carrier transport through
        # the channel: source → drain.  For nMOS, conventional current is the
        # opposite direction because electrons carry negative charge.
        moving = _flow_dots(3.25,8.72,7,phase)
        _carrier(ax_device,moving,4.67+.04*np.sin(moving*4),carrier,56)
        ax_device.annotate(f"{carrier} flow",xy=(8.7,4.10),xytext=(3.3,4.10),
                           arrowprops=dict(arrowstyle="-|>",color=color,lw=2.3),color=color)
        current_start, current_end = ((8.7,3.38),(3.3,3.38)) if p_bulk else ((3.3,3.38),(8.7,3.38))
        current_label = r"conventional current $I_D$" if p_bulk else r"conventional current $|I_D|$"
        ax_device.annotate(current_label,xy=current_end,xytext=current_start,
                           arrowprops=dict(arrowstyle="-|>",color=PURPLE,lw=2.1),color=PURPLE,
                           ha="right" if p_bulk else "left")
        if region == "Saturation":
            ax_device.annotate("pinch-off",xy=(8.42,4.5),xytext=(9.2,3.55),
                               arrowprops=dict(arrowstyle="->",color=PURPLE),color=PURPLE)
    ax_device.set_title(f"{device_name} cross-section — {region}",fontsize=13,weight="bold")
    ax_device.axis("off")

    # Three-dimensional gate-controlled bands. Source and body share EF=0;
    # drain EF is shifted by -qVds.  Bulk polarity reverses the band response.
    x = np.linspace(0,1,46); y = np.linspace(0,1,15)
    xx, yy = np.meshgrid(x,y)
    channel = .5*(1+np.tanh((xx-.18)/.035)) * .5*(1+np.tanh((.82-xx)/.035))
    contact_ei = -NORMALIZED_PHI_F*polarity
    bulk_ei = NORMALIZED_PHI_F*polarity
    ei = contact_ei + (bulk_ei-contact_ei)*channel
    ei += -polarity*.62*control*channel - .34*vds*xx
    ei += polarity*.06*((yy-.5)/.5)**4
    if region == "Saturation":
        ei += polarity*.32*np.exp(-((xx-.79)/.085)**2)*channel
    ec, ev = ei+.56, ei-.56
    for sheet, sheet_color, label, alpha in ((ec,BLUE,"Ec",.28),(ei,GREEN,"Ei",.21),(ev,RED,"Ev",.25)):
        ax_band.plot_surface(xx,yy,sheet,color=sheet_color,alpha=alpha,linewidth=.25,
                             edgecolor=sheet_color,rstride=2,cstride=4,shade=False)
        ax_band.plot(x,np.full_like(x,1.02),sheet[-1],color=sheet_color,lw=2,label=label)
    ef_terminal = -vds*x
    active_label = "EFn" if p_bulk else "EFp"
    other_label = "EFp (body)" if p_bulk else "EFn (body)"
    ax_band.plot(x,np.full_like(x,.48),ef_terminal,color=ORANGE,lw=1.8,ls="--",label=active_label)
    ax_band.plot(x,np.full_like(x,.58),np.zeros_like(x),color=PURPLE,lw=1.5,ls="--",label=other_label)
    if region != "Cutoff":
        cx = _flow_dots(.08,.92,8,phase) if effective_drain>=0 else _flow_dots(.92,.08,8,phase)
        surface = ec[len(y)//2] if p_bulk else ev[len(y)//2]
        cz = np.interp(cx,x,surface) + (.035 if p_bulk else -.035)
        _carrier(ax_band,cx,np.full_like(cx,.5),carrier,36,is3d=True,z=cz)
        start_x, vector_x = ((.14,.64) if effective_drain>=0 else (.86,-.64))
        start_z = float(np.interp(start_x,x,surface))
        ax_band.quiver(start_x,.5,start_z,vector_x,0,-.08*vds,color=color,lw=2,arrow_length_ratio=.1)
    if region == "Saturation":
        pz = float(np.interp(.79,x,ei[len(y)//2]))
        ax_band.text(.77,.20,pz+.18*polarity,"pinch-off",color=PURPLE,fontsize=9)
    ax_band.text(.02,.08,float(ei[1,1]+.75),f"{contact} source",fontsize=9,weight="bold")
    ax_band.text(.42,.90,float(np.max(ec[:,20:26])+.08),f"{bulk_type} channel",fontsize=9,weight="bold")
    ax_band.text(.86,.08,float(ei[1,-2]+.75),f"{contact} drain",fontsize=9,weight="bold")
    ax_band.set_title(f"3D gate-controlled bands — {region}",fontsize=13,weight="bold")
    ax_band.set_xlabel("x: Source → Drain"); ax_band.set_ylabel("y: interface width"); ax_band.set_zlabel("Normalized energy")
    ax_band.set_box_aspect((1.5,.8,1))
    ax_band.view_init(elev=float(view_elev), azim=float(view_azim))
    ax_band.legend(loc="lower left",fontsize=8,ncol=2); ax_band.grid(alpha=.13)
    _draw_mosfet_formula(ax_formula, bulk_type, vgs, vds, region)
    fig.suptitle(f"{device_name} · {bulk_type} bulk · Vgs={vgs:+.2f} V · Vds={vds:+.2f} V · Vs=Vb=0",fontsize=14)
    return f"{region}: {device_name}, {carrier} channel; gate Ef={-vgs:+.2f} eV and drain EF={-vds:+.2f} eV relative to source/body."


def _draw_mosfet_formula(ax, bulk_type, vgs, vds, region):
    p_bulk = bulk_type == "P-type"
    point = mosfet_operating_point(bulk_type, vgs, vds)
    vt = point["vt"]
    region = point["region"]
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.set_title("Live mathematical derivation (normalized long-channel model, k=1)", loc="left", fontsize=11, weight="bold")
    if p_bulk:
        vov = point["overdrive"]
        vgd = point["vgd"]
        vd = point["drain_drive"]
        current = point["current_magnitude"]
        eq1 = (r"$V_S=V_B=0,\quad V_T=" + f"{vt:.3f}" + r"\ \mathrm{V},\quad V_{OV}=V_{GS}-V_T="
               + f"{vgs:+.3f}-{vt:.3f}={vov:+.3f}" + r"\ \mathrm{V}$")
        eq2 = (r"$V_{GD}=V_{GS}-V_{DS}=" + f"{vgs:+.3f}-({vds:+.3f})={vgd:+.3f}"
               + r"\ \mathrm{V};\quad V_{GD}\leq V_T\Longleftrightarrow V_{DS}\geq V_{GS}-V_T$")
        piece1 = r"$I_D=0,\qquad V_{GS}\leq V_T$"
        piece2 = r"$I_D=k\!\left[(V_{GS}-V_T)V_{DS}-\frac{V_{DS}^{2}}{2}\right],\qquad 0\leq V_{DS}<V_{OV}$"
        piece3 = r"$I_D=\frac{k}{2}(V_{GS}-V_T)^2,\qquad V_{DS}\geq V_{OV}$"
        if region == "Cutoff":
            live = rf"$I_D=0\ \Longrightarrow\ \mathbf{{\mathrm{{Cutoff}}}}$"
        elif region == "Linear":
            live = (r"$I_D=(" + f"{vov:.3f})( {vd:.3f})-({vd:.3f})^2/2={current:.4f}"
                    + r"\ \Longrightarrow\ \mathbf{\mathrm{Linear}}$")
        else:
            live = (r"$I_D=\frac{1}{2}(" + f"{vov:.3f})^2={current:.4f}"
                    + r"\ \Longrightarrow\ \mathbf{\mathrm{Saturation}}$")
    else:
        vsg, vsd = point["gate_drive"], point["drain_drive"]
        vov = point["overdrive"]
        vgd = point["vgd"]
        current = point["current_magnitude"]
        eq1 = (r"$V_S=V_B=0,\quad |V_{TP}|=" + f"{vt:.3f}" + r"\ \mathrm{V},\quad V_{OV}=V_{SG}-|V_{TP}|="
               + f"{vsg:.3f}-{vt:.3f}={vov:+.3f}" + r"\ \mathrm{V}$")
        eq2 = (r"$V_{SG}=-V_{GS}=" + f"{vsg:.3f}" + r"\ \mathrm{V},\quad V_{SD}=-V_{DS}="
               + f"{vsd:.3f}" + r"\ \mathrm{V},\quad V_{GD}=" + f"{vgd:+.3f}" + r"\ \mathrm{V}$")
        piece1 = r"$|I_D|=0,\qquad V_{SG}\leq |V_{TP}|$"
        piece2 = r"$|I_D|=k\!\left[(V_{SG}-|V_{TP}|)V_{SD}-\frac{V_{SD}^{2}}{2}\right],\qquad 0\leq V_{SD}<V_{OV}$"
        piece3 = r"$|I_D|=\frac{k}{2}(V_{SG}-|V_{TP}|)^2,\qquad V_{SD}\geq V_{OV}$"
        if region == "Cutoff":
            live = rf"$|I_D|=0\ \Longrightarrow\ \mathbf{{\mathrm{{Cutoff}}}}$"
        elif region == "Linear":
            live = (r"$|I_D|=(" + f"{vov:.3f})( {vsd:.3f})-({vsd:.3f})^2/2={current:.4f}"
                    + r"\ \Longrightarrow\ \mathbf{\mathrm{Linear}}$")
        else:
            live = (r"$|I_D|=\frac{1}{2}(" + f"{vov:.3f})^2={current:.4f}"
                    + r"\ \Longrightarrow\ \mathbf{\mathrm{Saturation}}$")
    ax.text(.01, .72, eq1, fontsize=10.5, va="center")
    ax.text(.01, .38, eq2, fontsize=10.5, va="center")
    ax.text(.52, .78, piece1, fontsize=9.8, va="center")
    ax.text(.52, .50, piece2, fontsize=9.8, va="center")
    ax.text(.52, .22, piece3, fontsize=9.8, va="center")
    ax.text(.01, .08, live, fontsize=11.0, va="center", color=PURPLE)


def _sigmoid(value):
    return 1.0 / (1.0 + np.exp(-np.clip(value, -60, 60)))


def draw_curves(fig, device, bulk_type="P-type", vg=0.0, vds=0.0):
    """Draw normalized qualitative I-V and C-V curves with live bias markers."""
    fig.clear()
    ax_iv, ax_cv = fig.subplots(1, 2)
    polarity = 1.0 if bulk_type == "P-type" else -1.0

    if device == "MOS Capacitor":
        sweep = np.linspace(-3, 3, 501)
        effective_gate = polarity*sweep
        depletion_drop = 1 - .65*_sigmoid((effective_gate + .18)/.22)
        low_frequency = np.clip(depletion_drop + .62*_sigmoid((effective_gate-.90)/.24), .25, 1.02)
        high_frequency = np.clip(depletion_drop, .25, 1.02)
        selected_lf = np.interp(vg, sweep, low_frequency)
        selected_hf = np.interp(vg, sweep, high_frequency)

        ax_iv.axhline(0, color=PURPLE, lw=2.2, label="ideal Ig")
        ax_iv.scatter([vg], [0], s=75, color=ORANGE, edgecolors="white", zorder=5,
                      label=f"Vg={vg:+.3f} V")
        ax_iv.set_ylim(-.12, .12)
        ax_iv.text(.5, .62, "Ideal oxide: DC gate current ≈ 0\n(leakage not modelled)",
                   transform=ax_iv.transAxes, ha="center", color=GRAY)
        ax_iv.set_title("MOS capacitor I-V", fontsize=13, weight="bold")
        ax_iv.set_xlabel("Gate voltage Vg (V)")
        ax_iv.set_ylabel("Normalized gate current")
        ax_iv.set_xlim(-3, 3)
        ax_iv.legend(loc="lower right", fontsize=9)

        ax_cv.plot(sweep, low_frequency, color=BLUE, lw=2.4, label="low-frequency C-V")
        ax_cv.plot(sweep, high_frequency, color=RED, lw=2.2, ls="--", label="high-frequency C-V")
        ax_cv.scatter([vg, vg], [selected_lf, selected_hf], s=70, color=ORANGE,
                      edgecolors="white", zorder=5, label="current Vg")
        ax_cv.axvline(vg, color=ORANGE, lw=1.2, ls=":")
        ax_cv.set_title(f"{bulk_type} MOS capacitor C-V", fontsize=13, weight="bold")
        ax_cv.set_xlabel("Gate voltage Vg (V)")
        ax_cv.set_ylabel("Normalized capacitance C/Cmax")
        ax_cv.set_xlim(-3, 3); ax_cv.set_ylim(.2, 1.08)
        ax_cv.text(.98, .95,
                   r"$C_{MOS}=\left(C_{ox}^{-1}+C_s^{-1}\right)^{-1}$" "\n"
                   r"$C_{LF,inv}\rightarrow C_{ox},\quad C_{HF,inv}\rightarrow C_{min}$",
                   transform=ax_cv.transAxes, ha="right", va="top", fontsize=9)
        ax_cv.legend(loc="lower left", fontsize=9)
        region = operating_region(device, bulk_type, vg, 0)
        fig.suptitle(f"Normalized electrical curves · {bulk_type} bulk · {region}", fontsize=14)
    else:
        device_name = "nMOS" if polarity > 0 else "pMOS"
        drain_eff = np.linspace(0, 3, 401)
        drain_axis = polarity*drain_eff

        def drain_current(overdrive):
            magnitude = np.where(drain_eff < overdrive,
                                 overdrive*drain_eff - .5*drain_eff**2,
                                 .5*overdrive**2)
            return polarity*np.maximum(magnitude, 0)

        for gate_eff in (1.0, 1.4, 1.8, 2.4):
            curve = drain_current(max(gate_eff-NORMALIZED_VT, 0))
            ax_iv.plot(drain_axis, curve, color=GRAY, alpha=.28, lw=1.2,
                       label=f"Vgs={polarity*gate_eff:+.1f} V")
        overdrive = max(polarity*vg-NORMALIZED_VT, 0)
        selected_curve = drain_current(overdrive)
        ax_iv.plot(drain_axis, selected_curve, color=BLUE if polarity>0 else RED, lw=2.8,
                   label=f"selected Vgs={vg:+.3f} V")
        selected_deff = np.clip(polarity*vds, 0, 3)
        point_magnitude = (overdrive*selected_deff - .5*selected_deff**2
                           if selected_deff < overdrive else .5*overdrive**2)
        selected_current = polarity*max(point_magnitude, 0)
        ax_iv.scatter([polarity*selected_deff], [selected_current], s=80, color=ORANGE,
                      edgecolors="white", zorder=6, label=f"Vds={vds:+.3f} V")
        ax_iv.axvline(polarity*selected_deff, color=ORANGE, lw=1.1, ls=":")
        ax_iv.set_title(f"{device_name} output I-V", fontsize=13, weight="bold")
        ax_iv.set_xlabel("Drain voltage Vds (V)")
        ax_iv.set_ylabel("Normalized drain current Id")
        ax_iv.legend(loc="best", fontsize=8, ncol=2)

        gate_sweep = np.linspace(-3, 3, 501)
        gate_eff = polarity*gate_sweep
        on = _sigmoid((gate_eff-NORMALIZED_VT)/.20)
        vov_sweep = np.maximum(gate_eff-NORMALIZED_VT, 0)
        effective_vds = max(polarity*vds, 0)
        saturation_weight = _sigmoid((effective_vds-vov_sweep)/.16)
        cgs = on*(.5 + (2/3-.5)*saturation_weight)
        cgd = on*.5*(1-saturation_weight)
        total = np.clip(cgs+cgd, 0, 1)
        ax_cv.plot(gate_sweep, total, color=PURPLE, lw=2.6, label="total Cg")
        ax_cv.plot(gate_sweep, cgs, color=BLUE, lw=1.8, label="Cgs component")
        ax_cv.plot(gate_sweep, cgd, color=RED, lw=1.8, ls="--", label="Cgd component")
        values = [np.interp(vg, gate_sweep, series) for series in (total, cgs, cgd)]
        ax_cv.scatter([vg]*3, values, s=65, color=ORANGE, edgecolors="white", zorder=6)
        ax_cv.axvline(vg, color=ORANGE, lw=1.1, ls=":", label=f"Vgs={vg:+.3f} V")
        ax_cv.set_title(f"{device_name} normalized gate C-V", fontsize=13, weight="bold")
        ax_cv.set_xlabel("Gate voltage Vgs (V)")
        ax_cv.set_ylabel("Normalized capacitance")
        ax_cv.set_xlim(-3, 3); ax_cv.set_ylim(0, 1.05)
        ax_cv.text(.98, .56,
                   r"$\mathrm{Linear}:\ C_{gs}=C_{gd}\approx C_0/2$" "\n"
                   r"$\mathrm{Saturation}:\ C_{gs}\approx2C_0/3,\ C_{gd}\approx0$",
                   transform=ax_cv.transAxes, ha="right", va="top", fontsize=9)
        ax_cv.legend(loc="best", fontsize=9)
        region = operating_region(device, bulk_type, vg, vds)
        fig.suptitle(f"Normalized long-channel curves · Vgs={vg:+.3f} V · Vds={vds:+.3f} V · {region}", fontsize=14)

    for axis in (ax_iv, ax_cv):
        axis.grid(alpha=.18)
        axis.spines[["top", "right"]].set_visible(False)
