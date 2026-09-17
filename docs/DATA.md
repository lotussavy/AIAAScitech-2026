# Data dictionary and provenance

The bundled analysis inputs were copied from the author's local project on 2026-09-12, except the corrected borough lookup fetched from TLC that day. They are sufficient to run this repository offline after Python dependencies are installed. The input hashes are recorded in `data/sha256.json`. Use `python -m uam_demand --verify-inputs` to validate them.

The schemas below also govern data you supply yourself: see [Using your own data](../README.md#using-your-own-data) for the `--hourly`/`--distances`/`--zones`/`--config` CLI flags. CSV and JSON inputs may be UTF-8 or UTF-8 with a byte-order mark (the default when saving from Notepad or PowerShell's `Set-Content -Encoding utf8` on Windows); both are read correctly.

## Inputs

| Repository path | Source project path | Rows |
|---|---|---:|
| `data/hourly/EWR-hourly.csv` | `Data/Combined/EWR-hourly.csv` | 5,370 |
| `data/hourly/LGA-hourly.csv` | `Data/Combined/LGA-hourly.csv` | 11,654 |
| `data/hourly/JFK-hourly.csv` | `Data/Combined/JFK-hourly.csv` | 12,118 |
| `data/taxi_zones.csv` | Official TLC lookup, normalized to IDs 1–263 | 263 |
| `data/reference/taxi_zones_original.csv` | Original `Data/TaxiZone/taxi_zones.csv` (duplicates retained for audit) | 263 |
| `data/taxi_zone_airport_distances.csv` | `Data/TaxiZone/taxi_zone_airport_distances.csv` | 263 |
| `data/reference/Final_EWR_UAM_GCT.csv` | `Data/TaxiZone/Final_EWR_UAM_GCT.csv` | 5,370 |
| `data/reference/Final_LGA_UAM_GCT.csv` | `Data/TaxiZone/Final_LGA_UAM_GCT.csv` | 11,654 |
| `data/reference/Final_JFK_UAM_GCT.csv` | `Data/TaxiZone/Final_JFK_UAM_GCT.csv` | 12,118 |

The paper identifies the underlying observations as January–December 2023 NYC TLC Yellow Taxi, Green Taxi, and high-volume for-hire vehicle trips. The summaries contain no date, month, or vehicle-category column, so those original coverage claims cannot be independently verified from these files alone. No individual trip records, credentials, or local Python environment are bundled.

## Hourly summary schema

One row represents an origin, destination, and pickup-hour group aggregated over the source observation period. The original notebook groups the combined observations directly, rather than averaging monthly means. Do not sum standard deviations or average monthly averages without accounting for their counts and between-group variance.

| Column | Meaning / unit |
|---|---|
| `PULocationID` | Integer pickup taxi zone ID |
| `DOLocationID` | Integer dropoff taxi zone ID |
| `pickup_hour` | Hour extracted from pickup timestamp, 0–23, local NYC wall time |
| `num_trips` | Number of trips in the group; weight for all aggregate results |
| `avg_trip_time` | Mean trip duration, **hours** (already converted; do not divide by 3600 again) |
| `std_trip_time` | Sample standard deviation of trip duration, hours |
| `avg_fare_amount` | Mean recorded base fare, USD |
| `avg_trip_miles` | Mean driving distance, miles; retained but not directly used in GCT |
| `std_trip_miles` | Sample standard deviation of driving distance, miles |
| `avg_speed_mph` | Mean of per-trip speeds, mph; not mean distance / mean duration |
| `std_speed_mph` | Sample standard deviation of speed, mph; retained but not used in GCT |

The original pandas aggregation uses sample standard deviations (`ddof=1`). Its subsequent `dropna()` removes singleton groups with undefined sample standard deviations. This package starts after that step; removed groups cannot be recovered. Group IDs must be unique, weights and mean speeds must be positive, and required model values must be finite.

## Spatial inputs

`taxi_zones.csv` contains `LocationID` and `borough`. It contains 263 unique spatial IDs and names for the five NYC boroughs plus EWR. The supplied original lookup repeated ID 56 twice and ID 103 three times, omitted 57, 104, and 105, and could multiply observations on merge. This repository uses the official TLC lookup normalized to IDs 1–263 and preserves the original in `data/reference/taxi_zones_original.csv`. Download provenance and its original SHA-256 are in `data/lookup_provenance.json`. Existing shared IDs have identical borough labels.

The pipeline excludes 264 and 265 in either endpoint. In the retrieved TLC lookup, 264 has borough `Unknown` and 265 has zone `Outside of NYC`; they are not distinct pickup-only and dropoff-only flags.

`taxi_zone_airport_distances.csv` contains `LocationID`, `D_EWR_miles`, `D_LGA_miles`, and `D_JFK_miles`. The paper describes great-circle distances. The source coordinates, centroid choices, Earth-radius constant, projection workflow, and generator are not present in the supplied project; distances are therefore treated as fixed supplied inputs, not independently regenerated geometry.

Airport zone IDs: EWR = 1, JFK = 132, LGA = 138. Airport GCT uses the distance column for that airport and the other trip endpoint. Inter-airport trips can appear in more than one airport-specific input; do not sum airport totals as if they were mutually exclusive demand samples. Borough comparisons include only the five NYC boroughs, while zone rankings can include any mapped pickup zone with airport-bound trips.

## Historical reference CSVs

The reference files use `PULocationID`, `DOLocationID`, `pickup_hour`, `num_trips`, `GCT_Taxi`, `GCT_UAM_Early`, `GCT_UAM_Mid`, and `GCT_UAM_Mature`. These are input snapshots for regression checks, not regenerated truth. EWR's UAM columns match **LGA distances**, as established by the included regression test. Corrected EWR values intentionally differ.

## Acquiring raw observations for a new study

The official [NYC TLC Trip Record Data page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) provides monthly Parquet downloads, category-specific data dictionaries, taxi zone lookup data, and geometry. To undertake a new raw-data study:

1. Download and record hashes for all intended 2023 Yellow, Green, and HVFHV monthly files.
2. Normalize each category's timestamps, zone IDs, distance, and base-fare columns using its data dictionary. HVFHV uses different fields from Yellow/Green. Ordinary FHV records do not provide the same cost/distance fields and are not interchangeable with HVFHV.
3. Exclude invalid endpoints, missing critical fields, invalid durations/speeds, and clearly specified outliers; explicitly record every threshold and per-file rejection count.
4. Compute per-trip duration in hours and speed in mph; select trips involving airport IDs and aggregate all retained observations by OD and local pickup hour using the schema above.
5. Document singleton treatment, full-year coverage, time-zone assumptions, and fare conventions before replacing the supplied summaries.

The paper describes outlier exclusion qualitatively but does not supply numerical cleaning thresholds. This repository does not invent them or claim that downloading today's TLC files recovers the exact original sample. The raw workflow above is a specification for new work, not a validated exact-reproduction script. Full raw-trip replication additionally needs the original cleaning settings and distance-generation inputs from the authors.
