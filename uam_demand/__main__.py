"""Run with python -m uam_demand from the repository root."""

import argparse
import hashlib
import json
import platform
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

from . import __version__
from .model import AIRPORTS, COSTS, KEYS, analysis_tables, clean_hourly, compute_costs, validate_config
from .plots import generate_figures


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs(root):
    manifest = json.loads((root / "data/sha256.json").read_text())
    for relative, expected in manifest.items():
        path = root / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Input checksum mismatch: {relative}")
    return manifest


def run(root, output, config_path, airports, mode="corrected", plots=True):
    root, output, config_path = Path(root), Path(output), Path(config_path)
    validate_config(config := json.loads(config_path.read_text()))
    if mode == "archived" and config != json.loads((root / "config.json").read_text()):
        raise ValueError("Archived costs are fixed; use the default config or corrected mode")
    distances = pd.read_csv(root / "data/taxi_zone_airport_distances.csv")
    zones = pd.read_csv(root / "data/taxi_zones.csv")
    results, audit, inputs = {}, {}, {str(p.relative_to(root)): sha256(p) for p in [
        root / "data/taxi_zone_airport_distances.csv", root / "data/taxi_zones.csv"]}
    output.mkdir(parents=True, exist_ok=True)
    for airport in airports:
        hourly_path = root / f"data/hourly/{airport}-hourly.csv"
        reference_path = root / f"data/reference/Final_{airport}_UAM_GCT.csv"
        hourly = pd.read_csv(hourly_path)
        corrected = compute_costs(hourly, distances, airport, config)
        reference = pd.read_csv(reference_path).sort_values(KEYS).reset_index(drop=True)
        aligned = corrected.merge(reference, on=KEYS, suffixes=("_new", "_reference"),
                                  how="outer", validate="one_to_one", indicator=True)
        comparable = aligned.loc[aligned["_merge"].eq("both")]
        audit[airport] = {
            "input_hourly_rows": len(hourly), "valid_hourly_rows": len(corrected),
            "comparison_unmatched_rows": int(aligned["_merge"].ne("both").sum()),
            "max_abs_cost_difference_from_reference": {
                col: float((comparable[f"{col}_new"] - comparable[f"{col}_reference"]).abs().max())
                for col in COSTS
            },
        }
        if mode == "archived":
            # Retain only valid airport OD/hour keys while using the supplied historical costs.
            valid = clean_hourly(hourly, airport)[KEYS]
            costs = valid.merge(reference, on=KEYS, how="left", validate="one_to_one")
        else:
            costs = corrected
        tables = analysis_tables(costs, zones, airport, config)
        folder = output / airport
        folder.mkdir(exist_ok=True)
        costs.to_csv(folder / f"Final_{airport}_UAM_GCT.csv", index=False)
        for name, table in tables.items():
            table.to_csv(folder / f"{name}.csv", index=False)
        audit[airport]["airport_bound_trips"] = int(tables["airport_bound"]["num_trips"].sum())
        audit[airport]["top3_pickup_zones"] = tables["zone_gct"].head(3)["PULocationID"].astype(int).tolist()
        audit[airport]["missing_boroughs"] = tables["borough_gct"].loc[
            tables["borough_gct"]["total_trips"].eq(0), "borough"].tolist()
        results[airport] = tables
        for path in [hourly_path, reference_path]:
            inputs[str(path.relative_to(root))] = sha256(path)
    if plots:
        generate_figures(results, output / "figures", mode)
    report = {
        "version": __version__, "mode": mode, "airports": airports, "configuration": config,
        "config_sha256": sha256(config_path), "input_sha256": inputs,
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "pandas": pd.__version__, "matplotlib": matplotlib.__version__},
        "audit": audit,
    }
    (output / "run_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Generated {', '.join(airports)} results in {output.resolve()} ({mode})")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root containing data/")
    parser.add_argument("--config", type=Path, help="JSON configuration (default: ROOT/config.json)")
    parser.add_argument("--output", type=Path, help="Output directory (default: ROOT/outputs/MODE)")
    parser.add_argument("--airports", nargs="+", choices=list(AIRPORTS), default=list(AIRPORTS))
    parser.add_argument("--mode", choices=["corrected", "archived"], default="corrected")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--verify-inputs", action="store_true", help="Check bundled data against SHA-256 manifest")
    args = parser.parse_args()
    if args.verify_inputs:
        verify_inputs(args.root)
    run(args.root, args.output or args.root / "outputs" / args.mode,
        args.config or args.root / "config.json", args.airports, args.mode, not args.no_plots)


if __name__ == "__main__":
    main()
