import tempfile
from pathlib import Path
import unittest

import pandas as pd

from uam_demand.__main__ import run

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.json"

HOURLY_ROW = {
    "PULocationID": 10, "DOLocationID": 1, "pickup_hour": 8, "num_trips": 3,
    "avg_trip_time": 1.0, "std_trip_time": 0.1, "avg_fare_amount": 50.0,
    "std_trip_miles": 2.0, "avg_speed_mph": 20.0,
}


class IndependentDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp_context = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_context.name)
        self.addCleanup(self.tmp_context.cleanup)
        self.hourly_path = self.tmp / "my_ewr_hourly.csv"
        pd.DataFrame([HOURLY_ROW]).to_csv(self.hourly_path, index=False)
        self.distances_path = self.tmp / "my_distances.csv"
        pd.DataFrame({"LocationID": [10], "D_EWR_miles": [10.0]}).to_csv(self.distances_path, index=False)
        self.zones_path = self.tmp / "my_zones.csv"
        pd.DataFrame({"LocationID": [10], "borough": ["Queens"]}).to_csv(self.zones_path, index=False)

    def test_custom_hourly_distances_and_zones_outside_root_skip_audit_without_a_reference(self):
        output = self.tmp / "out"
        report = run(ROOT, output, CONFIG, ["EWR"], plots=False,
                     hourly={"EWR": self.hourly_path}, distances=self.distances_path, zones=self.zones_path)
        self.assertIsNone(report["audit"]["EWR"]["max_abs_cost_difference_from_reference"])
        self.assertEqual(report["audit"]["EWR"]["valid_hourly_rows"], 1)
        costs = pd.read_csv(output / "EWR" / "Final_EWR_UAM_GCT.csv")
        self.assertEqual(costs.loc[0, "GCT_Taxi"], 98.60)  # 50 + 41.9 + 33.52 * (.1 + 2/20)
        self.assertAlmostEqual(costs.loc[0, "GCT_UAM_Early"], 153.352)
        self.assertIn(str(self.hourly_path), report["input_sha256"])

    def test_custom_hourly_with_explicit_reference_runs_audit(self):
        reference_path = self.tmp / "my_ewr_reference.csv"
        pd.DataFrame([{
            "PULocationID": 10, "DOLocationID": 1, "pickup_hour": 8, "num_trips": 3,
            "GCT_Taxi": 98.60, "GCT_UAM_Early": 153.352,
            "GCT_UAM_Mid": 102.401333, "GCT_UAM_Mature": 52.394286,
        }]).to_csv(reference_path, index=False)
        output = self.tmp / "out"
        report = run(ROOT, output, CONFIG, ["EWR"], plots=False,
                     hourly={"EWR": self.hourly_path}, reference={"EWR": reference_path},
                     distances=self.distances_path, zones=self.zones_path)
        diff = report["audit"]["EWR"]["max_abs_cost_difference_from_reference"]
        self.assertIsNotNone(diff)
        self.assertLess(diff["GCT_Taxi"], 1e-6)

    def test_archived_mode_requires_an_existing_reference_csv(self):
        missing_reference = self.tmp / "does_not_exist.csv"
        with self.assertRaisesRegex(ValueError, "Archived mode requires a reference CSV"):
            run(ROOT, self.tmp / "out", CONFIG, ["EWR"], mode="archived", plots=False,
                reference={"EWR": missing_reference})


if __name__ == "__main__":
    unittest.main()
