import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from uam_demand.__main__ import verify_inputs
from uam_demand.model import (
    AIRPORTS, BOROUGHS, COSTS, KEYS, analysis_tables, compute_costs,
    switching_probability, weighted_summary,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text())


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.hourly = pd.DataFrame([{
            "PULocationID": 10, "DOLocationID": 1, "pickup_hour": 8, "num_trips": 3,
            "avg_trip_time": 1., "std_trip_time": .1, "avg_fare_amount": 50.,
            "std_trip_miles": 2., "avg_speed_mph": 20.,
        }])
        self.distances = pd.DataFrame({"LocationID": [10], "D_EWR_miles": [10.], "D_LGA_miles": [99.]})

    def test_units_and_airport_specific_distance(self):
        row = compute_costs(self.hourly, self.distances, "EWR", CONFIG).iloc[0]
        self.assertEqual(row.GCT_Taxi, 98.60)  # 50 + 41.9 + 33.52 * (.1 + 2/20)
        self.assertAlmostEqual(row.GCT_UAM_Early, 153.352)
        self.assertAlmostEqual(row.GCT_UAM_Mature, 52.394285714285715)

    def test_unknown_zones_removed_at_both_endpoints(self):
        invalid = pd.concat([self.hourly] * 2, ignore_index=True)
        invalid.loc[0, ["PULocationID", "DOLocationID"]] = [264, 1]
        invalid.loc[1, ["PULocationID", "DOLocationID"]] = [1, 265]
        combined = pd.concat([self.hourly, invalid], ignore_index=True)
        self.assertEqual(len(compute_costs(combined, self.distances, "EWR", CONFIG)), 1)

    def test_departures_use_non_airport_endpoint(self):
        self.hourly.loc[0, ["PULocationID", "DOLocationID"]] = [1, 10]
        row = compute_costs(self.hourly, self.distances, "EWR", CONFIG).iloc[0]
        self.assertAlmostEqual(row.GCT_UAM_Early, 153.352)

    def test_missing_distance_fails_instead_of_zero_cost(self):
        self.distances.loc[0, "LocationID"] = 11
        with self.assertRaisesRegex(ValueError, "Missing EWR distances"):
            compute_costs(self.hourly, self.distances, "EWR", CONFIG)

    def test_invalid_speed_and_duplicate_groups_fail(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compute_costs(pd.concat([self.hourly] * 2), self.distances, "EWR", CONFIG)
        self.hourly.loc[0, "avg_speed_mph"] = 0
        with self.assertRaisesRegex(ValueError, "positive"):
            compute_costs(self.hourly, self.distances, "EWR", CONFIG)

    def test_logit_sign_equal_costs_and_extremes(self):
        p = switching_probability([0, 50, 100, -1e6, 1e6], 50)
        self.assertGreater(p[0], p[1])
        self.assertEqual(p[1], .5)
        self.assertGreater(p[1], p[2])
        self.assertEqual(p[3], 1)
        self.assertEqual(p[4], 0)

    def test_trip_weights_not_row_average(self):
        frame = pd.DataFrame({"zone": [1, 1], "num_trips": [1, 9], "cost": [10., 100.]})
        result = weighted_summary(frame, ["zone"], ["cost"]).iloc[0]
        self.assertEqual(result.cost, 91.)
        self.assertEqual(result.total_trips, 10)

    def test_missing_borough_is_explicit_not_zero_cost(self):
        costs = compute_costs(self.hourly, self.distances, "EWR", CONFIG)
        zones = pd.DataFrame({"LocationID": [10], "borough": ["Queens"]})
        result = analysis_tables(costs, zones, "EWR", CONFIG)["borough_gct"]
        self.assertEqual(result.borough.tolist(), BOROUGHS)
        missing = result.loc[result.borough.eq("Bronx")].iloc[0]
        self.assertEqual(missing.total_trips, 0)
        self.assertTrue(pd.isna(missing.GCT_Taxi))

    def test_duplicate_borough_lookup_cannot_multiply_trips(self):
        costs = compute_costs(self.hourly, self.distances, "EWR", CONFIG)
        zones = pd.DataFrame({"LocationID": [10, 10], "borough": ["Queens", "Queens"]})
        with self.assertRaisesRegex(ValueError, "duplicate zone IDs"):
            analysis_tables(costs, zones, "EWR", CONFIG)

    def test_bundled_data_regression_and_known_ewr_discrepancy(self):
        verify_inputs(ROOT)
        distances = pd.read_csv(ROOT / "data/taxi_zone_airport_distances.csv")
        zones = pd.read_csv(ROOT / "data/taxi_zones.csv")
        for airport, zone in AIRPORTS.items():
            h = pd.read_csv(ROOT / f"data/hourly/{airport}-hourly.csv")
            actual = compute_costs(h, distances, airport, CONFIG)
            reference = pd.read_csv(ROOT / f"data/reference/Final_{airport}_UAM_GCT.csv").sort_values(KEYS).reset_index(drop=True)
            pd.testing.assert_frame_equal(actual[KEYS + ["num_trips"]], reference[KEYS + ["num_trips"]])
            np.testing.assert_allclose(actual.GCT_Taxi, reference.GCT_Taxi, atol=1e-10)
            if airport != "EWR":
                np.testing.assert_allclose(actual[COSTS], reference[COSTS], atol=1e-10)
            else:
                self.assertGreater(abs(actual.GCT_UAM_Early - reference.GCT_UAM_Early).max(), 250)
                other_zone = h.PULocationID.where(h.PULocationID.ne(zone), h.DOLocationID)
                lga = other_zone.map(distances.set_index("LocationID").D_LGA_miles) * (15 + 41.9 / 125)
                original_order = pd.read_csv(ROOT / "data/reference/Final_EWR_UAM_GCT.csv")
                np.testing.assert_allclose(lga, original_order.GCT_UAM_Early, atol=1e-10)
            tables = analysis_tables(actual, zones, airport, CONFIG)
            self.assertEqual(len(tables["borough_gct"]), 5)
            self.assertTrue(tables["borough_gct"].total_trips.gt(0).all())
            self.assertTrue(tables["airport_bound"].DOLocationID.eq(zone).all())
            self.assertTrue(actual.GCT_UAM_Early.ge(actual.GCT_UAM_Mid).all())
            self.assertTrue(actual.GCT_UAM_Mid.ge(actual.GCT_UAM_Mature).all())


if __name__ == "__main__":
    unittest.main()
