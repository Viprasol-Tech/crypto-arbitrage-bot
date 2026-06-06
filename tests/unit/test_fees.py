from __future__ import annotations

import pytest

from crypto_arbitrage_bot.fees import FeeModel, Side


def test_buy_price_is_marked_up_by_fee() -> None:
    """A buy with only a taker fee pays price * (1 + fee)."""
    model = FeeModel(taker_fee=0.001)
    assert model.effective_price(100.0, Side.BUY) == pytest.approx(100.1)


def test_sell_price_is_marked_down_by_fee() -> None:
    """A sell with only a taker fee receives price * (1 - fee)."""
    model = FeeModel(taker_fee=0.001)
    assert model.effective_price(100.0, Side.SELL) == pytest.approx(99.9)


def test_flat_slippage_widens_both_sides() -> None:
    """Flat slippage pushes buys up and sells down on top of fees."""
    model = FeeModel(taker_fee=0.0, slippage_bps=10.0)  # 0.10%
    assert model.effective_price(100.0, Side.BUY) == pytest.approx(100.0 * 1.001)
    assert model.effective_price(100.0, Side.SELL) == pytest.approx(100.0 * 0.999)


def test_size_aware_slippage_scales_with_notional() -> None:
    """impact_per_notional_bps adds impact proportional to size/reference."""
    model = FeeModel(taker_fee=0.0, slippage_bps=0.0, impact_per_notional_bps=20.0)
    # size == reference => full 20 bps of impact.
    frac = model.slippage_fraction(size=10_000.0, reference_notional=10_000.0)
    assert frac == pytest.approx(20.0 / 10_000.0)
    # half the reference => half the impact.
    half = model.slippage_fraction(size=5_000.0, reference_notional=10_000.0)
    assert half == pytest.approx(10.0 / 10_000.0)


def test_size_aware_slippage_ignored_without_reference() -> None:
    """Without a positive reference notional, only flat slippage applies."""
    model = FeeModel(slippage_bps=5.0, impact_per_notional_bps=50.0)
    frac = model.slippage_fraction(size=10_000.0, reference_notional=0.0)
    assert frac == pytest.approx(5.0 / 10_000.0)


def test_round_trip_cost_combines_fees_and_slippage() -> None:
    """Round-trip cost equals the gap between an effective buy and sell of 1.0."""
    model = FeeModel(taker_fee=0.001, slippage_bps=10.0)
    cost = model.round_trip_cost_fraction()
    buy = model.effective_price(1.0, Side.BUY)
    sell = model.effective_price(1.0, Side.SELL)
    assert cost == pytest.approx(buy - sell)
    assert cost > 0.0


def test_rejects_non_positive_price() -> None:
    """A non-positive price is invalid for effective_price."""
    model = FeeModel()
    with pytest.raises(ValueError):
        model.effective_price(0.0, Side.BUY)


def test_rejects_out_of_range_fee() -> None:
    """Taker fee must live in [0, 1)."""
    with pytest.raises(ValueError):
        FeeModel(taker_fee=1.0)
    with pytest.raises(ValueError):
        FeeModel(taker_fee=-0.1)
