# Contributing

Use Python 3.12 and install the package in editable mode along with notebook extras: `python -m pip install -e . -r requirements-notebooks.txt`. Run `python -m unittest discover -s tests -v` and `python -m uam_demand --verify-inputs` before proposing changes. Run `python scripts/execute_notebooks.py` when changing notebook interfaces.

For changes to `uam_demand/__main__.py`'s CLI (`--hourly`, `--reference`, `--distances`, `--zones`), also exercise `tests/test_run.py`, which covers the path where data lives outside `data/` and no reference CSV is supplied — that path has no bundled fixture to fall back on, so a regression there is easy to miss otherwise.

Keep scientific changes separate from formatting changes. For a change to a formula, parameter, weighting scheme, airport selection, or data-cleaning rule, include its rationale, input provenance, effect on numerical results, and a regression test that checks the intended scientific behavior.

Preserve the supplied `data/reference/` snapshots. For new input snapshots, document the data source, cleaning choices, and coverage; update `data/sha256.json` intentionally. Do not update checksums merely to suppress an unexplained mismatch. Use custom output directories for experiments and do not commit virtual environments, credentials, or raw trip downloads.

Report problems through GitHub Issues with the command, Python/package versions, traceback, and relevant `run_manifest.json`. Avoid uploading credentials or nonpublic individual trip data. Notebook source commits should have empty outputs and null execution counts.
