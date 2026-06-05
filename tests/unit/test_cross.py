from __future__ import annotations

import pytest

from crypto_arbitrage_bot.cross import ExchangeQuote, cross_exchange_profit


def test_buys_cheap_sells_dear() -> None:
    """The cheaper venue is always chosen as the buy side."""
    a = ExchangeQuote(exchange="cheap", price=100.0, fee_rate=0.0)
    b = ExchangeQuote(exchange="dear", price=110.0, fee_rate=0.0)
    result = cross_exchange_profit(a, b)
    assert result.buy_exchange == "cheap"
    assert result.sell_exchange == "dear"


def test_direction_is_independent_of_argument_order() -> None:
    """Swapping the arguments yields the same direction and profit."""
    a = ExchangeQuote(exchange="cheap", price=100.0, fee_rate=0.0)
    b = ExchangeQuote(exchange="dear", price=110.0, fee_rate=0.0)
    r1 = cross_exchange_profit(a, b)
    r2 = cross_exchange_profit(b, a)
    assert r1.buy_exchange == r2.buy_exchange
    assert r1.net_profit == pytest.approx(r2.net_profit)


def test_profit_magnitude_no_fees() -> None:
    """With zero fees the profit is exactly the price gap."""
    a = ExchangeQuote(exchange="x", price=100.0, fee_rate=0.0)
    b = ExchangeQuote(exchange="y", price=110.0, fee_rate=0.0)
    result = cross_exchange_profit(a, b)
    assert result.net_profit == pytest.approx(10.0)
    assert result.net_profit_pct == pytest.approx(0.10)
    assert result.is_profitable is True


def test_equal_prices_no_profit_after_fees() -> None:
    """Equal prices with positive fees cannot be profitable."""
    a = ExchangeQuote(exchange="x", price=100.0, fee_rate=0.001)
    b = ExchangeQuote(exchange="y", price=100.0, fee_rate=0.001)
    result = cross_exchange_profit(a, b)
    # buy 100*(1.001)=100.1, sell 100*(0.999)=99.9 -> -0.2 per unit.
    assert result.net_profit == pytest.approx(-0.2)
    assert result.is_profitable is False


def test_fees_can_erase_a_small_gap() -> None:
    """A 0.1% price gap is wiped out by 0.1% taker fees on both sides."""
    a = ExchangeQuote(exchange="x", price=100.0, fee_rate=0.001)
    b = ExchangeQuote(exchange="y", price=100.1, fee_rate=0.001)
    result = cross_exchange_profit(a, b)
    assert result.is_profitable is False
    assert result.net_profit < 0.0


def test_large_gap_survives_fees() -> None:
    """A wide gap remains profitable after realistic fees."""
    a = ExchangeQuote(exchange="x", price=100.0, fee_rate=0.001)
    b = ExchangeQuote(exchange="y", price=105.0, fee_rate=0.001)
    result = cross_exchange_profit(a, b)
    buy_cost = 100.0 * 1.001
    sell_proceeds = 105.0 * 0.999
    assert result.net_profit == pytest.approx(sell_proceeds - buy_cost)
    assert result.is_profitable is True


def test_rejects_invalid_quotes() -> None:
    """Non-positive prices and out-of-range fees are rejected."""
    with pytest.raises(ValueError):
        ExchangeQuote(exchange="x", price=0.0, fee_rate=0.0)
    with pytest.raises(ValueError):
        ExchangeQuote(exchange="x", price=100.0, fee_rate=1.0)
