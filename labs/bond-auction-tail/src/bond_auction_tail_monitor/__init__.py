"""Treasury auction tail and demand stress analytics."""

from .core import AuctionReport, AuctionResult, analyze_series, load_csv

__all__ = ["AuctionReport", "AuctionResult", "analyze_series", "load_csv"]
__version__ = "0.1.0"
