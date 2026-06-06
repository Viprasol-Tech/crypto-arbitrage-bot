from __future__ import annotations

import pytest

from crypto_arbitrage_bot.fees import FeeModel
from crypto_arbitrage_bot.graph import MarketPair, PairGraph

_ZERO = FeeModel(taker_fee=0.0)


def _consistent_pairs() -> list[MarketPair]:
    """BTC/USDT, ETH/BTC, ETH/USDT priced perfectly consistently (no edge)."""
    return [
        MarketPair(base="BTC", quote="USDT", price=50_000.0, fees=_ZERO),
        MarketPair(base="ETH", quote="BTC", price=3_000.0 / 50_000.0, fees=_ZERO),
        MarketPair(base="ETH", quote="USDT", price=3_000.0, fees=_ZERO),
    ]


def _mispriced_pairs() -> list[MarketPair]:
    """ETH dear on the ETH/USDT leg creates a real cross-cycle edge (fee-free)."""
    return [
        MarketPair(base="BTC", quote="USDT", price=50_000.0, fees=_ZERO),
        MarketPair(base="ETH", quote="BTC", price=3_000.0 / 50_000.0, fees=_ZERO),
        MarketPair(base="ETH", quote="USDT", price=3_150.0, fees=_ZERO),
    ]


def test_graph_builds_both_directions_per_pair() -> None:
    """Each pair adds two directed edges and registers both assets."""
    graph = PairGraph([MarketPair(base="BTC", quote="USDT", price=50_000.0)])
    assert graph.assets == ["BTC", "USDT"]
    assert graph.edge_count() == 2


def test_consistent_graph_has_no_profitable_cycle() -> None:
    """A perfectly consistent triangle yields no profitable cycle."""
    graph = PairGraph(_consistent_pairs())
    assert graph.find_cycles(max_len=3, profitable_only=True) == []


def test_mispriced_graph_finds_a_triangle() -> None:
    """The 5% mispricing surfaces as a profitable triangle."""
    graph = PairGraph(_mispriced_pairs())
    cycles = graph.find_cycles(max_len=3, profitable_only=True)
    assert cycles
    best = cycles[0]
    assert best.is_profitable is True
    assert best.edge == pytest.approx(0.05, abs=1e-9)
    assert len(best.legs) == 3
    # Cycle is closed: starts and ends on the same asset.
    assert best.assets[0] == best.assets[-1]


def test_each_cycle_reported_once_when_scanning_all_seeds() -> None:
    """Canonical rotation keeps each undirected loop from duplicating per seed."""
    graph = PairGraph(_mispriced_pairs())
    cycles = graph.find_cycles(max_len=3, profitable_only=False)
    by_len = {2: 0, 3: 0}
    for c in cycles:
        by_len[len(c.legs)] += 1
    # Three pairs => three 2-leg round trips, and one triangle traversed in two
    # directions. Without canonical dedup each of the three seeds would re-emit
    # the triangle, so this asserts the dedup logic works.
    assert by_len == {2: 3, 3: 2}


def test_opposite_direction_loses_when_one_direction_wins() -> None:
    """If one rotation is profitable, the reverse rotation is not."""
    graph = PairGraph(_mispriced_pairs())
    all_cycles = graph.find_cycles(max_len=3, profitable_only=False)
    profitable = [c for c in all_cycles if c.is_profitable]
    assert len(profitable) == 1


def test_fees_can_erase_a_thin_cycle_edge() -> None:
    """A tiny mispricing dies once a per-leg fee is charged."""
    pairs = [
        MarketPair(base="BTC", quote="USDT", price=50_000.0, fees=FeeModel(taker_fee=0.001)),
        MarketPair(
            base="ETH", quote="BTC", price=3_000.0 / 50_000.0, fees=FeeModel(taker_fee=0.001)
        ),
        MarketPair(base="ETH", quote="USDT", price=3_002.0, fees=FeeModel(taker_fee=0.001)),
    ]
    graph = PairGraph(pairs)
    # ~0.067% gross edge cannot survive three legs of 0.1% taker fee (~0.3%).
    assert graph.find_cycles(max_len=3, profitable_only=True) == []


def test_start_filters_to_one_asset() -> None:
    """A start asset restricts cycles to those beginning there."""
    graph = PairGraph(_mispriced_pairs())
    cycles = graph.find_cycles(start="USDT", max_len=3, profitable_only=False)
    assert cycles
    assert all(c.assets[0] == "USDT" for c in cycles)


def test_unknown_start_raises() -> None:
    """Starting from an asset not in the graph is an error."""
    graph = PairGraph(_mispriced_pairs())
    with pytest.raises(ValueError):
        graph.find_cycles(start="DOGE")


def test_max_len_below_two_raises() -> None:
    """A cycle needs at least two legs."""
    graph = PairGraph(_mispriced_pairs())
    with pytest.raises(ValueError):
        graph.find_cycles(max_len=1)
