import pytest

from bond_auction_tail_monitor.core import AuctionResult, analyze_series


def test_tail_bp_uses_high_yield_minus_when_issued_in_basis_points():
    auction = AuctionResult(
        date="2026-06-10",
        tenor="10Y",
        high_yield=4.315,
        when_issued_yield=4.300,
        bid_to_cover=2.32,
        indirect_pct=63.0,
        direct_pct=18.0,
        dealer_pct=19.0,
    )

    assert auction.tail_bp == pytest.approx(1.5)


def test_series_flags_weak_demand_when_tail_jumps_and_bid_to_cover_falls():
    rows = [
        AuctionResult("2026-01-10", "10Y", 4.005, 4.000, 2.60, 70.0, 15.0, 15.0),
        AuctionResult("2026-02-10", "10Y", 4.106, 4.100, 2.55, 68.0, 16.0, 16.0),
        AuctionResult("2026-03-10", "10Y", 4.204, 4.200, 2.58, 69.0, 16.0, 15.0),
        AuctionResult("2026-04-10", "10Y", 4.455, 4.420, 2.05, 54.0, 14.0, 32.0),
    ]

    reports = analyze_series(rows, lookback=3)
    latest = reports[-1]

    assert latest.tail_bp == pytest.approx(3.5)
    assert latest.stress_score >= 75
    assert "large positive tail" in latest.drivers
    assert "soft bid-to-cover" in latest.drivers
    assert latest.regime == "strained"


def test_series_keeps_normal_auction_benign_against_history():
    rows = [
        AuctionResult("2026-01-10", "5Y", 4.002, 4.000, 2.45, 66.0, 17.0, 17.0),
        AuctionResult("2026-02-10", "5Y", 4.101, 4.100, 2.50, 67.0, 17.0, 16.0),
        AuctionResult("2026-03-10", "5Y", 4.201, 4.200, 2.48, 66.5, 17.0, 16.5),
        AuctionResult("2026-04-10", "5Y", 4.302, 4.300, 2.47, 66.0, 18.0, 16.0),
    ]

    latest = analyze_series(rows, lookback=3)[-1]

    assert latest.stress_score < 35
    assert latest.regime == "orderly"
    assert latest.drivers == ["near-normal auction versus tenor history"]
