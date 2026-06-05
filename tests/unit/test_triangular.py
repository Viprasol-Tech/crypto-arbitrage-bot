from __future__ import annotations

import pytest

from crypto_arbitrage_bot.triangular import TriangularLeg, triangular_edge


def _consistent_cycle() -> list[TriangularLeg]:
    """A perfectly consistent USDT -> BTC -> ETH -> USDT cycle (no edge)."""
    return [
        TriangularLeg(pair="BTC/USDT", rate=1.0 / 50_000.0),
        TriangularLeg(pair="ETH/BTC", rate=50_000.0 / 3_000.0),
        TriangularLeg(pair="ETH/USDT", rate=3_000.0),
    ]


def test_consistent_cycle_has_no_edge_without_fees() -> None:
    """A consistent cycle returns exactly the starting balance."""
    result = triangular_edge(_consistent_cycle(), fee_rate=0.0)
    assert result.gross_product == pytest.approx(1.0)
    assert result.edge == pytest.approx(0.0, abs=1e-12)
    assert result.is_profitable is False


def test_fees_make_a_consistent_cycle_unprofitable() -> None:
    """With fees, a break-even cycle becomes a small loss."""
    result = triangular_edge(_consistent_cycle(), fee_rate=0.001)
    # net = 1 * (0.999 ** 3) ~= 0.997002999 -> edge ~= -0.003.
    assert result.net_product == pytest.approx(0.999**3)
    assert result.edge < 0.0
    assert result.is_profitable is False


def test_mispriced_cycle_yields_positive_edge() -> None:
    """A deliberate mispricing on the last leg creates a real edge."""
    legs = [
        TriangularLeg(pair="BTC/USDT", rate=1.0 / 50_000.0),
        TriangularLeg(pair="ETH/BTC", rate=50_000.0 / 3_000.0),
        TriangularLeg(pair="ETH/USDT", rate=3_150.0),  # ETH dear vs implied 3000
    ]
    result = triangular_edge(legs, fee_rate=0.0)
    # gross = 3150 / 3000 = 1.05 -> 5% edge.
    assert result.gross_product == pytest.approx(1.05)
    assert result.edge == pytest.approx(0.05)
    assert result.is_profitable is True


def test_mispriced_cycle_survives_small_fees() -> None:
    """A 5% mispricing remains profitable after 0.1% per-leg fees."""
    legs = [
        TriangularLeg(pair="BTC/USDT", rate=1.0 / 50_000.0),
        TriangularLeg(pair="ETH/BTC", rate=50_000.0 / 3_000.0),
        TriangularLeg(pair="ETH/USDT", rate=3_150.0),
    ]
    result = triangular_edge(legs, fee_rate=0.001)
    assert result.net_product == pytest.approx(1.05 * (0.999**3))
    assert result.is_profitable is True


def test_requires_at_least_two_legs() -> None:
    """A single leg is not a cycle."""
    with pytest.raises(ValueError):
        triangular_edge([TriangularLeg(pair="BTC/USDT", rate=1.0)])


def test_rejects_out_of_range_fee() -> None:
    """Fee rates must live in [0, 1)."""
    with pytest.raises(ValueError):
        triangular_edge(_consistent_cycle(), fee_rate=1.0)
    with pytest.raises(ValueError):
        triangular_edge(_consistent_cycle(), fee_rate=-0.01)
