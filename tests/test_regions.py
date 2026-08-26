import unittest
import math
from matplotlib.figure import Figure

from region_visuals import (NORMALIZED_PHI_F, NORMALIZED_VT, REGIONS,
                            draw_curves, draw_scene, moscap_operating_point,
                            mosfet_operating_point, mosfet_region_preset,
                            operating_region, predict_mosfet_vt_idsat)


class RegionSceneTests(unittest.TestCase):
    def test_all_region_scenes_render(self):
        expected_count = {"MOS Capacitor": 4, "MOSFET": 3}
        bias = {("MOS Capacitor", "Accumulation"): (-1.0, 0),
                ("MOS Capacitor", "Flat-band"): (0.0, 0),
                ("MOS Capacitor", "Depletion"): (.5, 0),
                ("MOS Capacitor", "Inversion"): (1.5, 0),
                ("MOSFET", "Cutoff"): (.4, .2),
                ("MOSFET", "Linear"): (1.8, .3),
                ("MOSFET", "Saturation"): (1.8, 1.3)}
        for device, regions in REGIONS.items():
            self.assertEqual(len(regions), expected_count[device])
            for region in regions:
                figure = Figure(figsize=(8, 4))
                vg, vds = bias[(device, region)]
                description = draw_scene(figure, device, region, .25, vg=vg, vds=vds)
                self.assertGreaterEqual(len(figure.axes), 2)
                self.assertIn(region, description)
                self.assertGreater(len(figure.axes[-1].texts), 0)
                if device == "MOSFET":
                    self.assertEqual(figure.axes[1].name, "3d")

    def test_bulk_polarity_reverses_moscap_regions(self):
        self.assertEqual(operating_region("MOS Capacitor", "P-type", -1.0), "Accumulation")
        self.assertEqual(operating_region("MOS Capacitor", "P-type", 0.0), "Flat-band")
        self.assertEqual(operating_region("MOS Capacitor", "P-type", 1.5), "Inversion")
        self.assertEqual(operating_region("MOS Capacitor", "N-type", 1.0), "Accumulation")
        self.assertEqual(operating_region("MOS Capacitor", "N-type", -1.5), "Inversion")

    def test_mosfet_voltage_regions(self):
        self.assertEqual(operating_region("MOSFET", "P-type", .4, 0), "Cutoff")
        self.assertEqual(operating_region("MOSFET", "P-type", 1.8, .3), "Linear")
        self.assertEqual(operating_region("MOSFET", "P-type", 1.8, 1.3), "Saturation")
        self.assertEqual(operating_region("MOSFET", "N-type", -1.8, -.3), "Linear")
        figure = Figure(figsize=(8, 4))
        description = draw_scene(figure, "MOSFET", "Saturation", .25,
                                 bulk_type="N-type", vg=-1.8, vds=-1.3)
        self.assertEqual(figure.axes[1].name, "3d")
        self.assertIn("pMOS", description)

    def test_mosfet_region_presets_cover_all_views_and_mirror_pmos(self):
        for region in REGIONS["MOSFET"]:
            n_vgs, n_vds = mosfet_region_preset("P-type", region)
            p_vgs, p_vds = mosfet_region_preset("N-type", region)
            self.assertEqual(operating_region("MOSFET", "P-type", n_vgs, n_vds), region)
            self.assertEqual(operating_region("MOSFET", "N-type", p_vgs, p_vds), region)
            self.assertAlmostEqual(n_vgs, -p_vgs)
            self.assertAlmostEqual(n_vds, -p_vds)

    def test_mosfet_3d_view_angles_are_applied(self):
        figure = Figure(figsize=(8, 4))
        draw_scene(figure, "MOSFET", bulk_type="P-type", vg=1.8, vds=.3,
                   view_elev=42, view_azim=115)
        axis = figure.axes[1]
        self.assertEqual(axis.name, "3d")
        self.assertAlmostEqual(axis.elev, 42)
        self.assertAlmostEqual(axis.azim, 115)

    def test_mosfet_carrier_and_conventional_current_directions(self):
        cases = (("P-type", 1.8, .3, "electron flow", r"conventional current $I_D$", -1),
                 ("N-type", -1.8, -.3, "hole flow", r"conventional current $|I_D|$", 1))
        for bulk, vgs, vds, carrier_label, current_label, current_sign in cases:
            figure = Figure(figsize=(8, 4))
            draw_scene(figure, "MOSFET", bulk_type=bulk, vg=vgs, vds=vds)
            annotations = {text.get_text(): text for text in figure.axes[0].texts}
            carrier_arrow = annotations[carrier_label]
            current_arrow = annotations[current_label]
            self.assertGreater(carrier_arrow.xy[0], carrier_arrow.get_position()[0])
            self.assertEqual((current_arrow.xy[0] > current_arrow.get_position()[0]) -
                             (current_arrow.xy[0] < current_arrow.get_position()[0]), current_sign)

    def test_vt_idsat_prediction_sweeps_toward_cutoff_and_mirrors_pmos(self):
        result = predict_mosfet_vt_idsat("P-type", 1.8, step=.2, points=5)
        self.assertEqual([round(row["vg"], 1) for row in result["rows"]], [1.8, 1.6, 1.4, 1.2, 1.0])
        self.assertEqual([row["region"] for row in result["rows"]],
                         ["Saturation", "Saturation", "Saturation", "Saturation", "Saturation"])
        self.assertGreater(result["rows"][0]["idsat"], result["rows"][-1]["idsat"])
        pmos = predict_mosfet_vt_idsat("N-type", -1.8, step=.2, points=2)
        self.assertEqual([round(row["vg"], 1) for row in pmos["rows"]], [-1.8, -1.6])
        specified = predict_mosfet_vt_idsat("P-type", 1.0, specified_vgs=[1.0, .8, .6])
        self.assertEqual([row["region"] for row in specified["rows"]], ["Saturation", "Cutoff", "Cutoff"])

    def test_electrical_curves_render_for_both_bulk_types(self):
        for device, bulk, vg, vds in (("MOS Capacitor", "P-type", 1.2, 0),
                                      ("MOS Capacitor", "N-type", -1.2, 0),
                                      ("MOSFET", "P-type", 1.8, 1.2),
                                      ("MOSFET", "N-type", -1.8, -1.2)):
            figure = Figure(figsize=(8, 4))
            draw_curves(figure, device, bulk, vg, vds)
            self.assertEqual(len(figure.axes), 2)
            self.assertGreater(len(figure.axes[0].lines), 0)
            self.assertGreater(len(figure.axes[1].lines), 0)

    def test_moscap_high_frequency_cv_stays_at_cmin(self):
        figure = Figure(figsize=(8, 4))
        draw_curves(figure, "MOS Capacitor", "P-type", 1.5, 0)
        lines = {line.get_label(): line for line in figure.axes[1].lines}
        low = lines["low-frequency C-V"].get_ydata()
        high = lines["high-frequency C-V"].get_ydata()
        self.assertGreater(low[-1], .95)
        self.assertLess(high[-1], .37)
        self.assertAlmostEqual(high[-1], min(high), places=3)

    def test_mosfet_intrinsic_capacitance_partition_limits(self):
        figure = Figure(figsize=(8, 4))
        draw_curves(figure, "MOSFET", "P-type", 1.8, 1.2)
        lines = {line.get_label(): line for line in figure.axes[1].lines}
        cgs = lines["Cgs component"].get_ydata()
        cgd = lines["Cgd component"].get_ydata()
        self.assertLess(cgs[0], 1e-5)
        self.assertLess(cgd[0], 1e-5)
        self.assertAlmostEqual(cgs[-1], .5, delta=.02)
        self.assertAlmostEqual(cgd[-1], .5, delta=.02)

    def test_strong_inversion_boundary_and_bulk_symmetry(self):
        boundary_vg = 1.25*math.atanh((2*NORMALIZED_PHI_F)/.95)
        p_point = moscap_operating_point("P-type", boundary_vg)
        n_point = moscap_operating_point("N-type", -boundary_vg)
        self.assertAlmostEqual(p_point["psi_s"], 2*NORMALIZED_PHI_F, places=12)
        self.assertAlmostEqual(n_point["psi_s"], -2*NORMALIZED_PHI_F, places=12)
        self.assertEqual(p_point["region"], "Inversion")
        self.assertEqual(n_point["region"], "Inversion")
        self.assertAlmostEqual(p_point["effective_surface"], n_point["effective_surface"], places=12)

    def test_surface_carrier_ratios_preserve_mass_action(self):
        thermal_voltage = .02585
        for vg in (-3, -1, 0, 1, 3):
            psi = moscap_operating_point("P-type", vg)["psi_s"]
            n_ratio = math.exp(psi/thermal_voltage)
            p_ratio = math.exp(-psi/thermal_voltage)
            self.assertAlmostEqual(n_ratio*p_ratio, 1.0, places=10)

    def test_nmos_vgd_condition_matches_vds_condition(self):
        for vgs in (.9, 1.2, 1.8, 2.7):
            for vds in (0, .2, .8, 1.4, 2.8):
                point = mosfet_operating_point("P-type", vgs, vds)
                saturation_from_vds = vds >= vgs-NORMALIZED_VT
                saturation_from_vgd = point["vgd"] <= NORMALIZED_VT
                self.assertEqual(saturation_from_vds, saturation_from_vgd)

    def test_square_law_is_continuous_at_saturation_boundary(self):
        self.assertEqual(mosfet_operating_point("P-type", .8250000000000001, .025)["region"],
                         "Saturation")
        for bulk, vgs in (("P-type", 1.8), ("N-type", -1.8)):
            polarity = 1 if bulk == "P-type" else -1
            vov = abs(vgs)-NORMALIZED_VT
            below = mosfet_operating_point(bulk, vgs, polarity*(vov-1e-8))["current_magnitude"]
            boundary = mosfet_operating_point(bulk, vgs, polarity*vov)["current_magnitude"]
            expected = .5*vov**2
            self.assertAlmostEqual(below, expected, places=12)
            self.assertAlmostEqual(boundary, expected, places=12)

    def test_nmos_pmos_mirror_symmetry(self):
        n_point = mosfet_operating_point("P-type", 1.8, 1.2)
        p_point = mosfet_operating_point("N-type", -1.8, -1.2)
        self.assertEqual(n_point["region"], p_point["region"])
        self.assertAlmostEqual(n_point["current_magnitude"], p_point["current_magnitude"])
        self.assertAlmostEqual(n_point["current_signed"], -p_point["current_signed"])

    def test_band_order_and_gate_fermi_shift(self):
        figure = Figure(figsize=(8, 4))
        draw_scene(figure, "MOS Capacitor", bulk_type="P-type", vg=1.2)
        lines = {line.get_label(): line for line in figure.axes[0].lines}
        ec = lines["silicon Ec"].get_ydata()
        ei = lines["silicon Ei"].get_ydata()
        ev = lines["silicon Ev"].get_ydata()
        self.assertTrue(((ec-ei) > 0).all())
        self.assertTrue(((ei-ev) > 0).all())
        self.assertAlmostEqual(float(lines["gate Ef"].get_ydata()[0]), -1.2)
        self.assertAlmostEqual(float(lines["body Ef"].get_ydata()[0]), 0.0)


if __name__ == "__main__":
    unittest.main()
