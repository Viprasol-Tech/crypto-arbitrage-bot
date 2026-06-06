from __future__ import annotations

import pytest

from crypto_arbitrage_bot.fees import FeeModel
from crypto_arbitrage_bot.scanner import VenueQuote, rank_cross, scan_cross

_ZERO = FeeModel(taker_fee=0.0)


def _board() -> list[VenueQuote]:
    return [
        VenueQuote(exchange="a", price=100.0, fees=_ZERO),
        VenueQuote(exchange="b", price=103.0, fees=_ZERO),
        VenueQuote(exchange="c", price=101.0, fees=_ZERO),
    ]


def test_scan_picks_cheapest_buy_and_dearest_sell() -> None:
    """With no fees, buy at the lowest price and sell at the highest."""
    best = scan_cross("X/USDT", _board())
    assert best.buy_exchange == "a"
    assert best.sell_exchange == "b"
    assert best.net_profit == pytest.approx(3.0)
    assert best.is_profitable is True


def test_scan_reports_correct_pair_label() -> None:
    """The pair label is threaded into the opportunity."""
    best = scan_cross("BTC/USDT", _board())
    assert best.pair == "BTC/USDT"


def test_scan_requires_two_venues() -> None:
    """A single venue cannot be crossed."""
    with pytest.raises(ValueError):
        scan_cross("X/USDT", [VenueQuote(exchange="solo", price=100.0)])


def test_rank_orders_by_net_profit_descending() -> None:
    """rank_cross returns every directed pair, best edge first."""
    ranked = rank_cross("X/USDT", _board())
    assert len(ranked) == 6  # permutations of 3 venues
    edges = [o.net_profit for o in ranked]
    assert edges == sorted(edges, reverse=True)
    assert ranked[0].buy_exchange == "a"
    assert ranked[0].sell_exchange == "b"


def test_rank_profitable_only_filters_losers() -> None:
    """profitable_only drops directed pairs that lose money."""
    ranked = rank_cross("X/USDT", _board(), profitable_only=True)
    assert all(o.is_profitable for o in ranked)
    assert len(ranked) < 6


def test_fees_can_erase_a_thin_cross_edge() -> None:
    """A 0.1% gap is wiped out by 0.1% taker fees on both venues."""
    board = [
        VenueQuote(exchange="a", price=100.0, fees=FeeModel(taker_fee=0.001)),
        VenueQuote(exchange="b", price=100.1, fees=FeeModel(taker_fee=0.001)),
    ]
    best = scan_cross("X/USDT", board)
    assert best.is_profitable is False
    assert best.net_profit < 0.0


def test_slippage_reduces_net_profit() -> None:
    """Adding slippage shrinks the net edge versus a fee-only board."""
    plain = [
        VenueQuote(exchange="a", price=100.0),
        VenueQuote(exchange="b", price=103.0),
    ]
    slipped = [
        VenueQuote(exchange="a", price=100.0, fees=FeeModel(slippage_bps=20.0)),
        VenueQuote(exchange="b", price=103.0, fees=FeeModel(slippage_bps=20.0)),
    ]
    assert scan_cross("X", slipped).net_profit < scan_cross("X", plain).net_profit
