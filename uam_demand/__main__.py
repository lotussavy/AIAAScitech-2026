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
    manifest = json.loads((root / "data/sha256.json").read_text(encoding="utf-8-sig"))
    for relative, expected in manifest.items():
        path = root / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Input checksum mismatch: {relative}")
    return manifest


def input_key(path, root):
    """Record bundled inputs by repository-relative path, external inputs by absolute path."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def run(root, output, config_path, airports, mode="corrected", plots=True,
        hourly=None, reference=None, distances=None, zones=None):
    """hourly/reference are optional {airport: path} overrides for data outside `root`.
    Airports without an override use the bundled data/ layout under `root`. A reference
    CSV is required in archived mode and otherwise only used, and audited against, when supplied.
    """
    root, output, config_path = Path(root), Path(output), Path(config_path)
    hourly, reference = dict(hourly or {}), dict(reference or {})
    validate_config(config := json.loads(config_path.read_text(encoding="utf-8-sig")))
    if mode == "archived" and config != json.loads((root / "config.json").read_text(encoding="utf-8-sig")):
        raise ValueError("Archived costs are fixed; use the default config or corrected mode")
    distances_path = Path(distances) if distances else root / "data/taxi_zone_airport_distances.csv"
    zones_path = Path(zones) if zones else root / "data/taxi_zones.csv"
    distances_df = pd.read_csv(distances_path)
    zones_df = pd.read_csv(zones_path)
    results, audit = {}, {}
    inputs = {input_key(p, root): sha256(p) for p in [distances_path, zones_path]}
    output.mkdir(parents=True, exist_ok=True)
    for airport in airports:
        hourly_path = Path(hourly[airport]) if airport in hourly else root / f"data/hourly/{airport}-hourly.csv"
        if airport in reference:
            reference_path = Path(reference[airport])
        elif mode == "archived" or airport not in hourly:
            reference_path = root / f"data/reference/Final_{airport}_UAM_GCT.csv"
        else:
            reference_path = None
        if mode == "archived" and (reference_path is None or not reference_path.is_file()):
            raise ValueError(f"Archived mode requires a reference CSV for {airport}")

        hourly_df = pd.read_csv(hourly_path)
        corrected = compute_costs(hourly_df, distances_df, airport, config)
        if reference_path is not None:
            reference_df = pd.read_csv(reference_path).sort_values(KEYS).reset_index(drop=True)
            aligned = corrected.merge(reference_df, on=KEYS, suffixes=("_new", "_reference"),
                                      how="outer", validate="one_to_one", indicator=True)
            comparable = aligned.loc[aligned["_merge"].eq("both")]
            audit[airport] = {
                "input_hourly_rows": len(hourly_df), "valid_hourly_rows": len(corrected),
                "comparison_unmatched_rows": int(aligned["_merge"].ne("both").sum()),
                "max_abs_cost_difference_from_reference": {
                    col: float((comparable[f"{col}_new"] - comparable[f"{col}_reference"]).abs().max())
                    for col in COSTS
                },
            }
        else:
            audit[airport] = {
                "input_hourly_rows": len(hourly_df), "valid_hourly_rows": len(corrected),
                "comparison_unmatched_rows": None, "max_abs_cost_difference_from_reference": None,
            }
        if mode == "archived":
            # Retain only valid airport OD/hour keys while using the supplied historical costs.
            valid = clean_hourly(hourly_df, airport)[KEYS]
            costs = valid.merge(reference_df, on=KEYS, how="left", validate="one_to_one")
        else:
            costs = corrected
        tables = analysis_tables(costs, zones_df, airport, config)
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
            if path is not None:
                inputs[input_key(path, root)] = sha256(path)
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
    parser.add_argument("--hourly", type=Path,
                        help="Hourly CSV for your own data, matching the bundled schema "
                             "(requires exactly one --airports value; overrides ROOT/data/hourly/)")
    parser.add_argument("--reference", type=Path,
                        help="Reference CSV to audit --hourly against (requires --hourly); "
                             "omit to skip the audit entirely")
    parser.add_argument("--distances", type=Path,
                        help="Zone-to-airport distances CSV (default: ROOT/data/taxi_zone_airport_distances.csv)")
    parser.add_argument("--zones", type=Path,
                        help="Zone-to-borough lookup CSV (default: ROOT/data/taxi_zones.csv)")
    args = parser.parse_args()
    if args.verify_inputs:
        verify_inputs(args.root)
    if (args.hourly or args.reference) and len(args.airports) != 1:
        parser.error("--hourly/--reference require exactly one --airports value")
    if args.reference and not args.hourly:
        parser.error("--reference requires --hourly")
    hourly = {args.airports[0]: args.hourly} if args.hourly else None
    reference = {args.airports[0]: args.reference} if args.reference else None
    run(args.root, args.output or args.root / "outputs" / args.mode,
        args.config or args.root / "config.json", args.airports, args.mode, not args.no_plots,
        hourly=hourly, reference=reference, distances=args.distances, zones=args.zones)


if __name__ == "__main__":
    main()
