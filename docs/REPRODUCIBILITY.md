# Reproducibility scope and known differences

## What is reproducible

All numeric model outputs and result-figure families can be regenerated deterministically from the nine bundled CSVs, configuration, and pinned Python packages. Tests establish agreement of calculated taxi GCT with all three supplied reference files and agreement of airport-specific UAM GCT with the supplied LGA and JFK files, within floating-point tolerance. EWR differs for the reason below. Image pixels and PDF bytes can vary with rendering libraries, fonts, operating system, and embedded metadata; numeric CSV comparisons are the regression target.

The project supports two explicitly labelled modes:

- `corrected` recomputes costs from hourly summaries and the matching airport's supplied distance column. This is the default for new analyses.
- `archived` uses the original final-cost CSV snapshots with the notebook's logit model. It preserves the documented EWR cost discrepancy so that historical cost behavior can be inspected. Both modes use the corrected borough lookup, so neither reproduces inflated trip weights caused by the original duplicate mappings. It is not proof of pixel-exact or numeric-exact agreement with the paper's published figures.

## Discrepancies and resolutions

| Issue found in supplied notebooks or paper | Repository behavior |
|---|---|
| EWR export had previously merged `Early_LGA`, `Mid_LGA`, `Mature_LGA`; the supplied EWR final CSV still reflects this | Corrected mode selects `D_EWR_miles`; archived mode retains historical EWR costs and labels every figure accordingly |
| Producer/plotter column mismatch (`GCT_Final` versus `GCT_Taxi`, and UAM variants) | One shared output schema; tests exercise downstream aggregation |
| Original borough lookup repeats IDs 56 and 103 and omits 57, 104, 105 | Both modes use the official one-row-per-ID TLC lookup to prevent multiplied trips; the original is retained for audit |
| Duplicate `plot_borough_comparison` definitions could override the five-borough list with three boroughs | One implementation; Figure 6 includes all five boroughs |
| Shared notebook variables, hardcoded airports, commented-out exports, and reused image filenames | Standalone notebooks, explicit parameters, automatic output creation, separate modes and airport directories |
| No explicit invalid-zone filtering in the original cost calculation | Exclude 264 and 265 at both endpoints; all included cleaned hourly snapshots already satisfy this rule |
| Printed paper Equation 4 uses `exp(GCT_Taxi - GCT_UAM)` | Preserve notebook `exp(lambda * (GCT_UAM - GCT_Taxi))`, so lower UAM cost increases its predicted probability |
| Paper Equation 4 omits lambda; notebooks use 0.10 | Expose lambda = 0.10 USD^-1 in config and record it in every manifest; it is an assumed sensitivity, not a calibrated estimate |
| Paper prose discusses ascent/descent time, but Equation 2 and notebooks use cruise distance/speed alone | Implement Equation 2 without undocumented fixed flight-time overhead |
| Early/mature cost comment in one notebook was reversed | Use paper's actual phase values: 15/10/5 USD per mile, 125/150/175 mph |
| Some notebook borough-switching cells included both directions | All result figures filter to airport-bound trips, matching the stated airport-access analysis |

Changing EWR to EWR-specific distances materially changes its UAM costs, switching rates, and conclusions relative to the supplied historical files. Published claims about EWR competitiveness should be reassessed using the corrected output; this package does not silently present corrected results as the original paper results.

## Aggregation decisions

- Top ten and top three pickup zones are ranked by total airport-bound trips; ties use ascending zone ID for deterministic selection.
- GCT averages use trip-count weights. Switching percentages average the per-OD/hour probabilities, not a probability evaluated at borough-average costs.
- Taxi GCT is rounded to two decimals before probability estimation, matching the original processing notebook.
- Borough GCT is shown in a fixed five-borough order for comparability rather than sorted by taxi GCT as in some original figures.
- Missing boroughs remain labelled and missing; missing hours interrupt curves. Neither becomes an invented zero-cost observation.
- The same observed taxi demand is evaluated under each phase. No endogenous demand growth, capacity ceiling, fleet optimization, boarding/access penalty, or uncertainty interval is modeled.

## Verification

```bash
python -m unittest discover -s tests -v
python -m uam_demand --verify-inputs
python -m uam_demand --mode archived --verify-inputs
```

Each `run_manifest.json` records package versions, configuration, input hashes, row counts, inbound trip counts, top-three zones, missing boroughs, and differences from historical GCT. GitHub Actions repeats tests and both full runs and uploads results as an artifact. Compare CSV values numerically, not image byte hashes.

## Remaining provenance gaps

Raw 2023 trips, exact cleaning thresholds, source-month checksums, rejected-record counts, centroid/airport coordinates, and the original spatial calculation code are absent from the provided project. The paper PDF is used as a reference but not redistributed here. No DOI or publication identifier was supplied, so citation metadata does not invent one. See [DATA.md](DATA.md) and [RESEARCH.md](RESEARCH.md).
