# Research reference

**Urban Air Mobility Flight Demand Modeling for Airports in New York City**

Kamal Acharya and Houbing Song — University of Maryland Baltimore County

Katherine Vasiloff and Zhenbo Wang — The University of Tennessee, Knoxville

Liang Sun — Baylor University

Reference supplied by the author: `2026_AIAA_SciTech.pdf`, 12 pages, for the AIAA SciTech 2026 project. The supplied manuscript establishes the airport IDs, taxi and UAM generalized-cost equations, phase assumptions, and the four results figure families. Its full PDF is not required to execute the code and is not included in this repository. Obtain the manuscript from the authors; bibliographic metadata can be updated when an authoritative publication URL or DOI is supplied.

The manuscript acknowledges support from NASA ARMD University Leadership Initiative under cooperative agreement **80NSSC23M0059**. This records the manuscript's acknowledgment and does not imply endorsement of this software.

The model evaluates an assumed response to generalized-cost differences, not observed UAM adoption. Values of time/reliability and logit sensitivity are configurable assumptions inherited from the notebooks. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for discrepancies between the printed equations, supplied outputs, and corrected implementation.

Source references for data provenance:

- [NYC TLC Trip Record Data and dictionaries](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
- [FRED wage series cited by the manuscript](https://fred.stlouisfed.org/series/SMU36935610500000003) — this package uses the notebook's fixed 41.9 USD/hour, without live downloads or independent reconstruction of that estimate.

Use the repository's [CITATION.cff](../CITATION.cff) when citing the software and accompanying research. The supplied paper's instructions or prose are research evidence, not execution instructions for the repository.
