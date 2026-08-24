"""Voltage-driven gate/oxide/silicon band, I-V, and C-V visualizer."""

import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from region_visuals import draw_curves, draw_scene, operating_region


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

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=10)
        band_tab = ttk.Frame(tabs)
        curve_tab = ttk.Frame(tabs)
        tabs.add(band_tab, text="Band & interface carriers")
        tabs.add(curve_tab, text="I-V / C-V curves")
        self.figure = Figure(figsize=(13.2, 7.2), dpi=100, constrained_layout=True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=band_tab)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
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
        else:
            self.vds_group.pack_forget()
            self.vds.set(0.0)
        self._bulk_changed()

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
        self._voltage_changed()

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
        vg_name = "Vgs" if self.device.get() == "MOSFET" else "Vg"
        self.vg_label.configure(text=f"{vg_name} = {vg_value:+.3f} V")
        self.vds_label.configure(text=f"Vds = {vds_value:+.3f} V")
        self._redraw()

    def _redraw(self, update_curves=True):
        region = operating_region(self.device.get(), self.bulk.get(), self.vg.get(), self.vds.get())
        self.region_text.configure(text=region)
        description = draw_scene(self.figure, self.device.get(), region, self.phase,
                                 bulk_type=self.bulk.get(), vg=self.vg.get(), vds=self.vds.get())
        self.status.set(description)
        self.canvas.draw_idle()
        if update_curves:
            draw_curves(self.curve_figure, self.device.get(), self.bulk.get(), self.vg.get(), self.vds.get())
            self.curve_canvas.draw_idle()

    def _animate(self):
        self.phase = (self.phase + .07) % 1.0
        self._redraw(update_curves=False)
        self.after(280, self._animate)


def np_clip(value, low, high):
    return max(low, min(high, value))


if __name__ == "__main__":
    VoltageVisualizer().mainloop()
