"""Factor Crowding Radar: offline crowding and unwind-risk analytics."""

from .core import CrowdingInputError, CrowdingReport, analyze_crowding, weighted_correlation

__all__ = [
    "CrowdingInputError",
    "CrowdingReport",
    "analyze_crowding",
    "weighted_correlation",
]

__version__ = "0.1.0"
