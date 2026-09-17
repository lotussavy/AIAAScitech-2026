"""Airport UAM generalized-cost and demand analysis."""

__version__ = "1.0.0"

from .model import (
    AIRPORTS, BOROUGHS, COSTS, HOURLY_COLUMNS, KEYS, PHASES,
    analysis_tables, clean_hourly, compute_costs, require_numeric,
    switching_probability, validate_config, weighted_summary,
)
from .plots import generate_figures

__all__ = [
    "AIRPORTS", "BOROUGHS", "COSTS", "HOURLY_COLUMNS", "KEYS", "PHASES",
    "analysis_tables", "clean_hourly", "compute_costs", "require_numeric",
    "switching_probability", "validate_config", "weighted_summary",
    "generate_figures",
]
