"""Voltage-driven gate/oxide/silicon band, I-V, and C-V visualizer."""

import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from region_visuals import (draw_curves, draw_scene, mosfet_region_preset,
                            operating_region, predict_mosfet_iv_sweep)


class VoltageVisualizer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gate–Oxide–Silicon Band Visualizer")
        self.geometry("1480x960")
        self.minsize(1100, 780)
        self.device = tk.StringVar(value="MOS Capacitor")
        self.bulk = tk.StringVar(value="P-type")
        self.vg = tk.DoubleVar(value=0.0)
        self.vds = tk.DoubleVar(value=0.0)
        self.fine_step = tk.DoubleVar(value=.01)
        self.region_view = tk.StringVar(value="Follow voltage")
        self.view_elev = tk.DoubleVar(value=24.0)
        self.view_azim = tk.DoubleVar(value=-61.0)
        self.predict_step = tk.DoubleVar(value=.10)
        self.predict_points = tk.IntVar(value=5)
        self.predict_vt = tk.DoubleVar(value=.80)
        self.predict_idsat = tk.DoubleVar(value=.50)
        self.predict_specified = tk.StringVar()
        self.predict_message = tk.StringVar(value="以目前 Vgs 為第一個預測點")
        self.prediction_result = None
        self._applying_region_preset = False
        self._dragging_3d = False
        self.phase = 0.0
        self._build()
        self._device_changed()
        self._animate()

    def _build(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Region.TLabel", font=("Segoe UI", 12, "bold"), foreground="#6a1b9a")
        style.configure("Hint.TLabel", foreground="#555555")

        header = ttk.Frame(self, padding=(16, 10, 16, 5))
        header.pack(fill="x")
        title_area = ttk.Frame(header)
        title_area.pack(side="left", fill="x", expand=True)
        ttk.Label(title_area, text="Gate–Oxide–Silicon Band Visualizer", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_area, text="Voltage controls only · source and body are fixed at the same potential", style="Hint.TLabel").pack(anchor="w")
        selectors = ttk.Frame(header)
        selectors.pack(side="right")
        ttk.Label(selectors, text="Device").grid(row=0, column=0, sticky="w", padx=5)
        device_box = ttk.Combobox(selectors, textvariable=self.device, state="readonly", width=17,
                                  values=("MOS Capacitor", "MOSFET"))
        device_box.grid(row=1, column=0, padx=5)
        device_box.bind("<<ComboboxSelected>>", lambda _e: self._device_changed())
        ttk.Label(selectors, text="Bulk type").grid(row=0, column=1, sticky="w", padx=5)
        bulk_box = ttk.Combobox(selectors, textvariable=self.bulk, state="readonly", width=10,
                                values=("P-type", "N-type"))
        bulk_box.grid(row=1, column=1, padx=5)
        bulk_box.bind("<<ComboboxSelected>>", lambda _e: self._bulk_changed())

        controls = ttk.Frame(self, padding=(16, 2, 16, 5))
        controls.pack(fill="x")
        voltage_row = ttk.Frame(controls)
        voltage_row.pack(fill="x")
        self.vg_group = ttk.Frame(voltage_row)
        self.vg_group.pack(side="left")
        self.vg_label = ttk.Label(self.vg_group, width=14)
        self.vg_label.pack(side="left")
        ttk.Scale(self.vg_group, from_=-3, to=3, variable=self.vg, length=300,
                  command=lambda _v: self._voltage_changed()).pack(side="left", padx=(0, 5))
        self.vg_spin = ttk.Spinbox(self.vg_group, from_=-3, to=3, increment=.01,
                                   textvariable=self.vg, width=8, format="%.3f", command=self._voltage_changed)
        self.vg_spin.pack(side="left")
        self.vg_spin.bind("<Return>", lambda _e: self._voltage_changed())
        self.vg_spin.bind("<FocusOut>", lambda _e: self._voltage_changed())
        ttk.Button(self.vg_group, text="−", width=3, command=lambda: self._nudge(self.vg, -1)).pack(side="left", padx=(5, 1))
        ttk.Button(self.vg_group, text="+", width=3, command=lambda: self._nudge(self.vg, 1)).pack(side="left")

        self.vds_group = ttk.Frame(voltage_row)
        self.vds_group.pack(side="left", padx=(22, 0))
        self.vds_label = ttk.Label(self.vds_group, width=14)
        self.vds_label.pack(side="left")
        self.vds_scale = ttk.Scale(self.vds_group, from_=0, to=3, variable=self.vds, length=240,
                                   command=lambda _v: self._voltage_changed())
        self.vds_scale.pack(side="left", padx=(0, 5))
        self.vds_spin = ttk.Spinbox(self.vds_group, from_=-3, to=3, increment=.01,
                                    textvariable=self.vds, width=8, format="%.3f", command=self._voltage_changed)
        self.vds_spin.pack(side="left")
        self.vds_spin.bind("<Return>", lambda _e: self._voltage_changed())
        self.vds_spin.bind("<FocusOut>", lambda _e: self._voltage_changed())
        ttk.Button(self.vds_group, text="−", width=3, command=lambda: self._nudge(self.vds, -1)).pack(side="left", padx=(5, 1))
        ttk.Button(self.vds_group, text="+", width=3, command=lambda: self._nudge(self.vds, 1)).pack(side="left")

        detail_row = ttk.Frame(controls)
        detail_row.pack(fill="x", pady=(5, 0))
        ttk.Label(detail_row, text="Fine step:").pack(side="left")
        step_box = ttk.Combobox(detail_row, textvariable=self.fine_step, state="readonly", width=7,
                                values=(.001, .005, .01, .05, .1))
        step_box.pack(side="left", padx=(5, 3))
        step_box.bind("<<ComboboxSelected>>", lambda _e: self._fine_step_changed())
        ttk.Label(detail_row, text="V per −/+ click", style="Hint.TLabel").pack(side="left")
        ttk.Label(detail_row, text="Auto region:").pack(side="left", padx=(28, 6))
        self.region_text = ttk.Label(detail_row, style="Region.TLabel")
        self.region_text.pack(side="left")

        self.mosfet_view_group = ttk.LabelFrame(controls, text="MOSFET 3D view", padding=(8, 5))
        ttk.Label(self.mosfet_view_group, text="Region view").pack(side="left")
        region_box = ttk.Combobox(self.mosfet_view_group, textvariable=self.region_view,
                                  state="readonly", width=15,
                                  values=("Follow voltage", "Cutoff", "Linear", "Saturation"))
        region_box.pack(side="left", padx=(5, 18))
        region_box.bind("<<ComboboxSelected>>", lambda _e: self._region_view_changed())
        self.elev_label = ttk.Label(self.mosfet_view_group, width=18)
        self.elev_label.pack(side="left")
        ttk.Scale(self.mosfet_view_group, from_=0, to=90, variable=self.view_elev, length=145,
                  command=lambda _v: self._view_changed()).pack(side="left", padx=(0, 18))
        self.azim_label = ttk.Label(self.mosfet_view_group, width=19)
        self.azim_label.pack(side="left")
        ttk.Scale(self.mosfet_view_group, from_=-180, to=180, variable=self.view_azim, length=190,
                  command=lambda _v: self._view_changed()).pack(side="left", padx=(0, 8))
        ttk.Button(self.mosfet_view_group, text="Reset view", command=self._reset_3d_view).pack(side="left")
        self._update_view_labels()

        self.predictor_group = ttk.LabelFrame(controls, text="MOSFET Vt / Idsat prediction", padding=(8, 5))
        ttk.Label(self.predictor_group, text="錨點 Vt").pack(side="left")
        ttk.Spinbox(self.predictor_group, from_=0, to=3, increment=.01,
                    textvariable=self.predict_vt, width=6, format="%.2f").pack(side="left", padx=(4, 8))
        ttk.Label(self.predictor_group, text="錨點 Idsat").pack(side="left")
        ttk.Spinbox(self.predictor_group, from_=0.001, to=100, increment=.01,
                    textvariable=self.predict_idsat, width=7, format="%.3f").pack(side="left", padx=(4, 8))
        ttk.Label(self.predictor_group, text="step (V)").pack(side="left")
        ttk.Spinbox(self.predictor_group, from_=.01, to=1, increment=.01,
                    textvariable=self.predict_step, width=6, format="%.2f").pack(side="left", padx=(4, 10))
        ttk.Label(self.predictor_group, text="points").pack(side="left")
        ttk.Spinbox(self.predictor_group, from_=2, to=12, increment=1,
                    textvariable=self.predict_points, width=4).pack(side="left", padx=(4, 10))
        ttk.Label(self.predictor_group, text="指定 Vgs (逗號分隔)").pack(side="left")
        ttk.Entry(self.predictor_group, textvariable=self.predict_specified, width=24).pack(side="left", padx=(4, 8))
        ttk.Button(self.predictor_group, text="預測", command=self._run_prediction).pack(side="left")
        ttk.Label(self.predictor_group, textvariable=self.predict_message, style="Hint.TLabel").pack(side="left", padx=(10, 0))

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=10)
        band_tab = ttk.Frame(tabs)
        curve_tab = ttk.Frame(tabs)
        tabs.add(band_tab, text="Band & interface carriers")
        tabs.add(curve_tab, text="I-V / C-V curves")
        self.figure = Figure(figsize=(13.2, 7.2), dpi=100, constrained_layout=True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=band_tab)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.mpl_connect("button_press_event", self._plot_button_pressed)
        self.canvas.mpl_connect("button_release_event", self._plot_button_released)
        NavigationToolbar2Tk(self.canvas, band_tab, pack_toolbar=True).update()
        self.curve_figure = Figure(figsize=(13.2, 7.2), dpi=100, constrained_layout=True)
        self.curve_canvas = FigureCanvasTkAgg(self.curve_figure, master=curve_tab)
        self.curve_canvas.get_tk_widget().pack(fill="both", expand=True)
        NavigationToolbar2Tk(self.curve_canvas, curve_tab, pack_toolbar=True).update()

        footer = ttk.Frame(self, padding=(16, 3, 16, 8))
        footer.pack(fill="x")
        self.status = tk.StringVar()
        ttk.Label(footer, textvariable=self.status).pack(side="left")
        ttk.Label(footer, text="Normalized qualitative curves · no Cox/process parameters", style="Hint.TLabel").pack(side="right")

    def _device_changed(self):
        if self.device.get() == "MOSFET":
            self.vds_group.pack(side="left", padx=(22, 0))
            self.mosfet_view_group.pack(fill="x", pady=(5, 0))
            self.predictor_group.pack(fill="x", pady=(5, 0))
        else:
            self.vds_group.pack_forget()
            self.mosfet_view_group.pack_forget()
            self.predictor_group.pack_forget()
            self.region_view.set("Follow voltage")
            self.vds.set(0.0)
            self.prediction_result = None
        self._bulk_changed()

    def _run_prediction(self):
        if self.device.get() != "MOSFET":
            return
        try:
            raw = self.predict_specified.get().replace("，", ",")
            specified = [float(item.strip()) for item in raw.split(",") if item.strip()] or None
            result = predict_mosfet_iv_sweep(self.bulk.get(), self.vg.get(), self.predict_vt.get(),
                                             self.predict_idsat.get(), self.predict_step.get(),
                                             self.predict_points.get(), specified_vgs=specified)
            self.prediction_result = result
            rows = "; ".join(f"Vg={row['vg']:+.2f}, VDS,pinch-off={row['pinch_off_vds']:+.2f}, Idsat={row['idsat']:.3f}"
                             for row in result["rows"])
            self.predict_message.set(f"k={result['k']:.4f}; {rows}")
            self._redraw(update_curves=True)
        except (tk.TclError, ValueError) as exc:
            self.predict_message.set(f"輸入錯誤：{exc}")

    def _bulk_changed(self):
        if self.device.get() == "MOSFET":
            if self.bulk.get() == "P-type":
                self.vds_scale.configure(from_=0, to=3)
                self.vds_spin.configure(from_=0, to=3)
                if self.vds.get() < 0:
                    self.vds.set(0.0)
            else:
                self.vds_scale.configure(from_=0, to=-3)
                self.vds_spin.configure(from_=-3, to=0)
                if self.vds.get() > 0:
                    self.vds.set(0.0)
            if self.region_view.get() != "Follow voltage":
                self._apply_region_preset()
                return
        self._voltage_changed()

    def _region_view_changed(self):
        if self.device.get() != "MOSFET" or self.region_view.get() == "Follow voltage":
            self._redraw()
            return
        self._apply_region_preset()

    def _apply_region_preset(self):
        region = self.region_view.get()
        if region == "Follow voltage":
            return
        vgs, vds = mosfet_region_preset(self.bulk.get(), region)
        self._applying_region_preset = True
        try:
            self.vg.set(vgs)
            self.vds.set(vds)
            self._voltage_changed()
        finally:
            self._applying_region_preset = False

    def _view_changed(self):
        self._update_view_labels()
        self._redraw(update_curves=False, capture_view=False)

    def _reset_3d_view(self):
        self.view_elev.set(24.0)
        self.view_azim.set(-61.0)
        self._view_changed()

    def _update_view_labels(self):
        self.elev_label.configure(text=f"Elevation: {self.view_elev.get():.0f}°")
        self.azim_label.configure(text=f"Azimuth: {self.view_azim.get():.0f}°")

    def _plot_button_pressed(self, event):
        if event.inaxes is not None and event.inaxes.name == "3d":
            self._dragging_3d = True

    def _plot_button_released(self, event):
        if self._dragging_3d:
            self._capture_3d_view(event.inaxes if event.inaxes is not None else None)
            self._dragging_3d = False

    def _capture_3d_view(self, axis=None):
        candidates = [axis] if axis is not None else self.figure.axes
        for candidate in candidates:
            if candidate is not None and candidate.name == "3d":
                self.view_elev.set(float(candidate.elev))
                self.view_azim.set(float(candidate.azim))
                self._update_view_labels()
                return

    def _nudge(self, variable, direction):
        low, high = -3, 3
        if variable is self.vds and self.device.get() == "MOSFET":
            low, high = ((0, 3) if self.bulk.get() == "P-type" else (-3, 0))
        value = np_clip(variable.get() + direction*self.fine_step.get(), low, high)
        variable.set(round(value, 4))
        self._voltage_changed()

    def _fine_step_changed(self):
        step = self.fine_step.get()
        self.vg_spin.configure(increment=step)
        self.vds_spin.configure(increment=step)

    def _voltage_changed(self):
        try:
            vg_value = np_clip(float(self.vg.get()), -3, 3)
            vds_value = np_clip(float(self.vds.get()), -3, 3)
        except (tk.TclError, ValueError):
            return
        if self.device.get() == "MOSFET":
            vds_value = (max(0, vds_value) if self.bulk.get() == "P-type"
                         else min(0, vds_value))
        self.vg.set(vg_value)
        self.vds.set(vds_value)
        if self.device.get() == "MOSFET" and not self._applying_region_preset:
            self.region_view.set("Follow voltage")
        vg_name = "Vgs" if self.device.get() == "MOSFET" else "Vg"
        self.vg_label.configure(text=f"{vg_name} = {vg_value:+.3f} V")
        self.vds_label.configure(text=f"Vds = {vds_value:+.3f} V")
        self._redraw()

    def _redraw(self, update_curves=True, capture_view=True):
        if capture_view and self.device.get() == "MOSFET":
            self._capture_3d_view()
        region = operating_region(self.device.get(), self.bulk.get(), self.vg.get(), self.vds.get())
        self.region_text.configure(text=region)
        description = draw_scene(self.figure, self.device.get(), region, self.phase,
                                 bulk_type=self.bulk.get(), vg=self.vg.get(), vds=self.vds.get(),
                                 view_elev=self.view_elev.get(), view_azim=self.view_azim.get())
        self.status.set(description)
        self.canvas.draw_idle()
        if update_curves:
            draw_curves(self.curve_figure, self.device.get(), self.bulk.get(), self.vg.get(), self.vds.get())
            if self.device.get() == "MOSFET" and self.prediction_result:
                self._draw_prediction_curves()
            self.curve_canvas.draw_idle()

    def _draw_prediction_curves(self):
        """Overlay measured-anchor Vg sweep curves on the lower local I-V chart."""
        if not self.curve_figure.axes:
            return
        axis = self.curve_figure.axes[0]
        # Prediction mode owns the legend: hide the baseline teaching curves'
        # legend entries while retaining their faint context lines.
        for artist in (*axis.lines, *axis.collections):
            if artist.get_label() and not artist.get_label().startswith("pred Vgs="):
                artist.set_label("_nolegend_")
        colors = ("#1877c9", "#762aa5", "#d84343", "#2e7d32", "#ef8a00", "#00838f")
        for index, curve in enumerate(self.prediction_result["curves"]):
            color = colors[index % len(colors)]
            axis.plot(curve["vds"], curve["id"], lw=2.0, color=color,
                      label=f"pred Vgs={curve['vg']:+.3f} V")
            pinch_vds = curve["pinch_off_vds"]
            idsat = curve["idsat"]
            axis.scatter([pinch_vds], [idsat], s=30, color=color, zorder=6)
            axis.annotate(
                f"Vg={curve['vg']:+.3f} V\nIdsat={idsat:.4f}",
                xy=(pinch_vds, idsat),
                xytext=(8, 10 + (index % 3) * 22), textcoords="offset points",
                fontsize=7.5, color=color,
                bbox=dict(boxstyle="round,pad=.22", fc="white", ec=color, alpha=.88),
                arrowprops=dict(arrowstyle="-", color=color, lw=.8),
            )
        axis.set_title("MOSFET output I-V · measured-anchor Vg prediction", fontsize=13, weight="bold")
        axis.legend(loc="best", fontsize=7, ncol=2)

    def _animate(self):
        self.phase = (self.phase + .07) % 1.0
        if not self._dragging_3d:
            self._redraw(update_curves=False)
        self.after(280, self._animate)


def np_clip(value, low, high):
    return max(low, min(high, value))


if __name__ == "__main__":
    VoltageVisualizer().mainloop()
