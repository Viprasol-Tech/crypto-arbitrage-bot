"""Triangular (and longer) cycle finding over a full pair graph.

The original :mod:`crypto_arbitrage_bot.triangular` evaluates *one* hand-built
cycle. On a real exchange you have dozens of pairs and want the machine to
*discover* every profitable cycle for you. Model the order book as a directed
graph whose nodes are assets and whose edges are "convert asset X into asset Y at
rate r" — one edge per side of every pair. A cycle that returns to its starting
asset with a rate product above one (after fees) is an arbitrage.

A cycle's net rate is the product of its per-leg rates after fees; a cycle is
profitable when that product exceeds one. We enumerate simple cycles up to a
bounded length (triangles by default) via depth-first search and multiply the
rates directly, which is fast and numerically exact for the small graphs typical
of a single venue's pair universe.

Part of Crypto Arbitrage Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from crypto_arbitrage_bot.fees import FeeModel


class MarketPair(BaseModel):
    """A tradable pair quoted as base/quote with a price in quote per base.

    From this single quote the graph derives *both* directions:
    converting ``quote -> base`` at ``1 / price`` and ``base -> quote`` at
    ``price``, each charged the pair's taker fee.

    Args:
        base: The base asset symbol (e.g. ``"BTC"``).
        quote: The quote asset symbol (e.g. ``"USDT"``).
        price: Price of one unit of base expressed in quote (must be positive).
        fees: Fee model applied to conversions across this pair.
    """

    base: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    price: float = Field(gt=0.0)
    fees: FeeModel = Field(default_factory=FeeModel)


class CycleLeg(BaseModel):
    """One conversion step of a discovered cycle.

    Attributes:
        frm: Asset converted from.
        to: Asset converted to.
        pair: The ``base/quote`` label of the pair used.
        rate: Gross units of ``to`` obtained per unit of ``frm`` (before fees).
    """

    frm: str
    to: str
    pair: str
    rate: float


class Cycle(BaseModel):
    """A closed conversion loop discovered on the graph.

    Attributes:
        assets: The ordered assets visited, starting and ending at the same one.
        legs: The conversion legs taken between consecutive assets.
        gross_product: Product of leg rates, ignoring fees.
        net_product: Product of leg rates after each leg's fee.
        edge: ``net_product - 1`` — fractional gain around the loop.
        is_profitable: ``True`` when ``edge`` clears a tiny tolerance.
    """

    assets: list[str]
    legs: list[CycleLeg]
    gross_product: float
    net_product: float
    edge: float
    is_profitable: bool


class _Edge:
    """Internal directed edge: convert ``frm -> to`` at ``gross_rate`` net ``keep``."""

    __slots__ = ("frm", "gross_rate", "keep", "pair", "to")

    def __init__(self, frm: str, to: str, pair: str, gross_rate: float, keep: float) -> None:
        self.frm = frm
        self.to = to
        self.pair = pair
        self.gross_rate = gross_rate
        self.keep = keep


class PairGraph:
    """A directed conversion graph built from a set of market pairs.

    Each :class:`MarketPair` contributes two edges (one per direction). Use
    :meth:`find_cycles` to enumerate profitable loops.
    """

    def __init__(self, pairs: list[MarketPair]) -> None:
        self._adj: dict[str, list[_Edge]] = {}
        for pair in pairs:
            self.add_pair(pair)

    @property
    def assets(self) -> list[str]:
        """Sorted list of every asset that appears as a node in the graph."""
        return sorted(self._adj)

    def edge_count(self) -> int:
        """Total number of directed edges in the graph."""
        return sum(len(edges) for edges in self._adj.values())

    def add_pair(self, pair: MarketPair) -> None:
        """Add both conversion directions of a market pair to the graph.

        Args:
            pair: The market pair to insert.
        """
        keep = 1.0 - pair.fees.taker_fee
        label = f"{pair.base}/{pair.quote}"
        # base -> quote: sell one base for `price` quote.
        self._adj.setdefault(pair.base, []).append(
            _Edge(pair.base, pair.quote, label, pair.price, keep)
        )
        # quote -> base: buy one base, i.e. 1/price base per quote.
        self._adj.setdefault(pair.quote, []).append(
            _Edge(pair.quote, pair.base, label, 1.0 / pair.price, keep)
        )

    def _materialise(self, path_edges: list[_Edge]) -> Cycle:
        gross = 1.0
        net = 1.0
        legs: list[CycleLeg] = []
        for e in path_edges:
            gross *= e.gross_rate
            net *= e.gross_rate * e.keep
            legs.append(CycleLeg(frm=e.frm, to=e.to, pair=e.pair, rate=e.gross_rate))
        assets = [path_edges[0].frm] + [e.to for e in path_edges]
        edge = net - 1.0
        return Cycle(
            assets=assets,
            legs=legs,
            gross_product=gross,
            net_product=net,
            edge=edge,
            is_profitable=edge > 1e-12,
        )

    def find_cycles(
        self,
        *,
        start: str | None = None,
        max_len: int = 3,
        profitable_only: bool = True,
    ) -> list[Cycle]:
        """Enumerate simple conversion cycles up to ``max_len`` legs.

        A *simple* cycle visits no intermediate asset twice. To avoid reporting
        the same loop once per rotation, only cycles whose starting asset is the
        smallest (lexicographically) asset in the loop are kept.

        Args:
            start: If given, only return cycles that begin (and end) at this
                asset. When ``None`` every asset is used as a seed.
            max_len: Maximum number of legs in a cycle (``3`` finds triangles).
                Must be at least 2.
            profitable_only: When ``True`` (default) only profitable cycles are
                returned; otherwise every discovered cycle is returned.

        Returns:
            Cycles sorted by ``edge`` descending.

        Raises:
            ValueError: If ``max_len`` is less than 2, or ``start`` is unknown.
        """
        if max_len < 2:
            raise ValueError("max_len must be at least 2")
        if start is not None and start not in self._adj:
            raise ValueError(f"unknown start asset: {start}")

        seeds = [start] if start is not None else self.assets
        results: list[Cycle] = []

        for seed in seeds:
            self._dfs(seed, seed, [], {seed}, max_len, start is None, results)

        if profitable_only:
            results = [c for c in results if c.is_profitable]
        results.sort(key=lambda c: c.edge, reverse=True)
        return results

    def _dfs(
        self,
        seed: str,
        node: str,
        path_edges: list[_Edge],
        visited: set[str],
        max_len: int,
        canonical: bool,
        out: list[Cycle],
    ) -> None:
        for edge in self._adj.get(node, []):
            nxt = edge.to
            if nxt == seed and len(path_edges) + 1 >= 2:
                # Closing the loop. Keep only the canonical rotation when scanning
                # all seeds, so each loop is reported exactly once.
                if not canonical or all(seed <= a for a in visited):
                    out.append(self._materialise([*path_edges, edge]))
                continue
            if nxt in visited or len(path_edges) + 1 >= max_len:
                continue
            visited.add(nxt)
            path_edges.append(edge)
            self._dfs(seed, nxt, path_edges, visited, max_len, canonical, out)
            path_edges.pop()
            visited.remove(nxt)
