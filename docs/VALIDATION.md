# Baseline verification

Verified locally on 2026-09-12 with Python 3.12, the pinned requirements, and the bundled input checksums. All 10 unit/regression tests passed; both command-line modes rendered five PNG/PDF figure pairs each; both notebooks executed successfully in separate fresh kernels. `pip check` found no broken requirements.

| Airport | Hourly rows | Airport-bound trips | Top three pickup zones | Missing boroughs |
|---|---:|---:|---|---|
| EWR | 5,370 | 1,761,208 | 230, 68, 48 | None |
| LGA | 11,654 | 5,362,175 | 230, 161, 164 | None |
| JFK | 12,118 | 5,476,230 | 216, 230, 10 | None |

These trip counts use a unique official zone lookup, so the join does not multiply observations. The summaries were provided as 2023 data; original date/category coverage cannot be verified from the hourly-only inputs.

Taxi GCT matches every supplied reference row exactly. LGA and JFK UAM GCT differences are below 1.3e-12 USD-equivalent. Corrected EWR UAM differs from the supplied EWR reference by up to 258.167459 (Early), 173.052152 (Mid), and 88.205564 (Mature) USD-equivalent because the supplied reference uses LGA distances. Those are maximum per-OD/hour differences, not borough-average differences.

Generated `run_manifest.json` files provide full configuration, environment versions, SHA-256 hashes, and per-airport audit details. The CI workflow reruns the analysis on future changes.
