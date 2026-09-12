"""Pure calculations, units, and input validation shared by CLI and notebooks."""

import numpy as np
import pandas as pd

AIRPORTS = {"EWR": 1, "LGA": 138, "JFK": 132}
BOROUGHS = ["Manhattan", "Queens", "Brooklyn", "Bronx", "Staten Island"]
PHASES = ["Early", "Mid", "Mature"]
KEYS = ["PULocationID", "DOLocationID", "pickup_hour"]
COSTS = ["GCT_Taxi"] + [f"GCT_UAM_{p}" for p in PHASES]
HOURLY_COLUMNS = KEYS + [
    "num_trips", "avg_trip_time", "std_trip_time", "avg_fare_amount",
    "std_trip_miles", "avg_speed_mph",
]


def require_numeric(frame, columns, label):
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label}: missing columns {missing}")
    values = frame[columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f"{label}: non-finite or missing values")


def validate_config(config):
    for name in ["value_of_time_usd_per_hour", "reliability_ratio", "logit_lambda_per_usd"]:
        value = config[name]
        if not np.isfinite(value) or value < 0:
            raise ValueError(f"Invalid configuration: {name}")
    if set(config["phases"]) != set(PHASES):
        raise ValueError("Configuration requires Early, Mid, and Mature phases")
    for phase in config["phases"].values():
        if (not np.isfinite(phase["cost_per_mile"]) or phase["cost_per_mile"] < 0
                or not np.isfinite(phase["speed_mph"]) or phase["speed_mph"] <= 0):
            raise ValueError("Phase costs must be nonnegative and speeds positive")


def clean_hourly(frame, airport):
    require_numeric(frame, HOURLY_COLUMNS, "Hourly data")
    if frame.duplicated(KEYS).any():
        raise ValueError("Hourly data contains duplicate OD/hour groups")
    for col in KEYS + ["num_trips"]:
        if (frame[col] % 1 != 0).any():
            raise ValueError(f"{col} must contain integers")
    if not frame["pickup_hour"].between(0, 23).all():
        raise ValueError("pickup_hour must be between 0 and 23")
    if (frame["num_trips"] <= 0).any() or (frame["avg_speed_mph"] <= 0).any():
        raise ValueError("Trip counts and average speeds must be positive")
    if (frame[["avg_trip_time", "std_trip_time", "avg_fare_amount", "std_trip_miles"]] < 0).any().any():
        raise ValueError("Times, variability, and fares must be nonnegative")
    # Remove these IDs at BOTH endpoints, even for already aggregated inputs.
    keep = ~frame[["PULocationID", "DOLocationID"]].isin([264, 265]).any(axis=1)
    zone = AIRPORTS[airport]
    keep &= frame["PULocationID"].eq(zone) | frame["DOLocationID"].eq(zone)
    out = frame.loc[keep].copy()
    if out.empty:
        raise ValueError(f"No valid {airport} trips")
    return out


def compute_costs(hourly, distances, airport, config):
    validate_config(config)
    h = clean_hourly(hourly, airport)
    distance_col = f"D_{airport}_miles"
    require_numeric(distances, ["LocationID", distance_col], "Distances")
    if distances["LocationID"].duplicated().any() or (distances[distance_col] < 0).any():
        raise ValueError("Distance IDs must be unique and distances nonnegative")
    non_airport = h["PULocationID"].where(h["PULocationID"].ne(AIRPORTS[airport]), h["DOLocationID"])
    distance = non_airport.map(distances.set_index("LocationID")[distance_col])
    if distance.isna().any():
        raise ValueError(f"Missing {airport} distances for zones {non_airport[distance.isna()].unique().tolist()}")
    vot = config["value_of_time_usd_per_hour"]
    vor = vot * config["reliability_ratio"]
    out = h[KEYS + ["num_trips"]].copy()
    out["GCT_Taxi"] = (
        h["avg_fare_amount"] + vot * h["avg_trip_time"]
        + vor * (h["std_trip_time"] + h["std_trip_miles"] / h["avg_speed_mph"])
    ).round(2)
    for name, phase in config["phases"].items():
        out[f"GCT_UAM_{name}"] = distance * (phase["cost_per_mile"] + vot / phase["speed_mph"])
    return out.sort_values(KEYS).reset_index(drop=True)


def switching_probability(uam_cost, taxi_cost, sensitivity=0.1):
    """Stable binary logit: equal costs -> 0.5; cheaper UAM -> higher share."""
    if not np.isfinite(sensitivity) or sensitivity < 0:
        raise ValueError("Sensitivity must be finite and nonnegative")
    delta = sensitivity * (np.asarray(uam_cost) - np.asarray(taxi_cost))
    return np.exp(-np.logaddexp(0, delta))


def weighted_summary(frame, groups, columns):
    """Weight each OD/hour mean by its trip count, never by number of rows."""
    require_numeric(frame, columns + ["num_trips"], "Weighted summary")
    if (frame["num_trips"] <= 0).any():
        raise ValueError("Weights must be positive")
    weighted = frame[groups].copy()
    weighted[columns] = frame[columns].multiply(frame["num_trips"], axis=0)
    weighted["num_trips"] = frame["num_trips"]
    sums = weighted.groupby(groups, sort=True, observed=True).sum()
    sums[columns] = sums[columns].div(sums["num_trips"], axis=0)
    return sums.rename(columns={"num_trips": "total_trips"}).reset_index()


def analysis_tables(costs, zones, airport, config):
    require_numeric(costs, KEYS + ["num_trips"] + COSTS, "Costs")
    if zones["LocationID"].duplicated().any():
        raise ValueError("Borough lookup contains duplicate zone IDs")
    # All result figures describe trips TO the airport.
    trips = costs.loc[costs["DOLocationID"].eq(AIRPORTS[airport])].copy()
    if trips.empty:
        raise ValueError(f"No airport-bound trips for {airport}")
    if trips["PULocationID"].isin([264, 265]).any():
        raise ValueError("Unlocated pickup zones remain in costs")
    trips = trips.merge(zones[["LocationID", "borough"]], left_on="PULocationID",
                        right_on="LocationID", how="left", validate="many_to_one")
    if trips["borough"].isna().any():
        raise ValueError("Missing pickup borough mapping")
    for phase in PHASES:
        trips[f"Switch_{phase}_pct"] = 100 * switching_probability(
            trips[f"GCT_UAM_{phase}"], trips["GCT_Taxi"], config["logit_lambda_per_usd"])
    switches = [f"Switch_{p}_pct" for p in PHASES]
    zone_gct = weighted_summary(trips, ["PULocationID"], COSTS).sort_values(
        ["total_trips", "PULocationID"], ascending=[False, True])
    city = trips.loc[trips["borough"].isin(BOROUGHS)]
    borough_gct = weighted_summary(city, ["borough"], COSTS).set_index("borough").reindex(BOROUGHS).reset_index()
    # A missing borough remains explicitly missing, never fabricated as zero cost.
    borough_gct["total_trips"] = borough_gct["total_trips"].fillna(0)
    return {
        "airport_bound": trips,
        "zone_gct": zone_gct,
        "borough_gct": borough_gct,
        "hourly_zone_switching": weighted_summary(trips, ["PULocationID", "pickup_hour"], switches),
        "hourly_borough_switching": weighted_summary(city, ["borough", "pickup_hour"], switches),
        "hourly_zone_gct": weighted_summary(trips, ["PULocationID", "pickup_hour"], COSTS),
    }
