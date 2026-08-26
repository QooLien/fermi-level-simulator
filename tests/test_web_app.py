import unittest

from web_app import STATE, app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original = dict(STATE)

    def tearDown(self):
        STATE.update(self.original)

    def test_index_and_state_endpoint_render(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Fermi Level Simulator", page.get_data(as_text=True))
        response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("band_svg", payload)
        self.assertIn("curve_svg", payload)
        self.assertIn("MOS Capacitor", payload["status"])

    def test_region_preset_and_bulk_mirror_update(self):
        response = self.client.post("/api/state", json={"device": "MOSFET", "region_view": "Saturation"})
        self.assertEqual(response.get_json()["region"], "Saturation")
        mirrored = self.client.post("/api/state", json={"bulk": "N-type"}).get_json()
        self.assertEqual(mirrored["state"]["region_view"], "Saturation")
        self.assertEqual(mirrored["state"]["vg"], -1.8)
        self.assertEqual(mirrored["state"]["vds"], -1.3)
        self.assertEqual(mirrored["region"], "Saturation")

    def test_manual_voltage_returns_to_follow_voltage(self):
        self.client.post("/api/state", json={"device": "MOSFET", "region_view": "Linear"})
        payload = self.client.post("/api/state", json={"vg": 1.8, "vds": 1.3}).get_json()
        self.assertEqual(payload["state"]["region_view"], "Follow voltage")
        self.assertEqual(payload["region"], "Saturation")

    def test_vt_idsat_prediction_endpoint_supports_step_and_specified_values(self):
        self.client.post("/api/state", json={"device": "MOSFET", "bulk": "P-type", "vg": 1.8})
        response = self.client.post("/api/predict", json={"step": .2, "points": 4})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["rows"]), 4)
        self.assertAlmostEqual(payload["rows"][1]["vg"], 1.6)
        specified = self.client.post("/api/predict", json={"specified_vgs": "1.0, 0.8, 0.6"})
        self.assertEqual(specified.status_code, 200)
        self.assertEqual([row["region"] for row in specified.get_json()["rows"]],
                         ["Saturation", "Cutoff", "Cutoff"])

    def test_vt_idsat_prediction_rejects_mos_capacitor(self):
        response = self.client.post("/api/predict", json={})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
