"""Triangular arbitrage detection on a single exchange.

Three pairs that share three assets form a cycle, e.g. start with USDT, buy BTC
(BTC/USDT), use BTC to buy ETH (ETH/BTC), then sell ETH back to USDT (ETH/USDT).
If the product of the conversion rates around the cycle exceeds one (after fees),
you end with more of the starting asset than you began with — a triangular edge.

Part of Crypto Arbitrage Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TriangularLeg(BaseModel):
    """One conversion step in a triangular cycle.

    Args:
        pair: Label for the pair being traded on this leg (e.g. ``"BTC/USDT"``).
        rate: Units of the *output* asset obtained per unit of the *input* asset
            on this leg, quoted *before* fees. For a "buy BTC with USDT" step
            where BTC costs 50,000 USDT, the rate is ``1 / 50000``.
    """

    pair: str = Field(min_length=1)
    rate: float = Field(gt=0.0)


class TriangularResult(BaseModel):
    """Outcome of a triangular arbitrage check.

    Attributes:
        gross_product: Product of the leg rates, ignoring fees.
        net_product: Product of the leg rates after applying the per-leg fee.
        edge: ``net_product - 1`` — the fractional gain around the cycle.
        is_profitable: ``True`` when ``edge`` is strictly positive.
    """

    gross_product: float
    net_product: float
    edge: float
    is_profitable: bool


def triangular_edge(legs: list[TriangularLeg], fee_rate: float = 0.0) -> TriangularResult:
    """Compute the net edge of completing a triangular conversion cycle.

    Each leg multiplies the running balance by its ``rate``; a taker fee of
    ``fee_rate`` is charged on every leg, so each leg effectively contributes
    ``rate * (1 - fee_rate)``. The ``edge`` is the product of all legs minus one:
    positive means the cycle returns more of the starting asset than was put in.

    Args:
        legs: The ordered legs of the cycle. Must contain at least two legs;
            a genuine triangle has three.
        fee_rate: Taker fee per leg as a fraction (e.g. ``0.001`` for 0.1%).

    A tiny tolerance (``1e-12``) guards the profitability flag against
    floating-point noise, so an exactly consistent cycle reads as *no edge*
    rather than a spurious sub-picopercent "profit".

    Returns:
        A :class:`TriangularResult` with gross/net products and the net edge.

    Raises:
        ValueError: If fewer than two legs are supplied or ``fee_rate`` is not
            in the half-open interval ``[0, 1)``.

    Example:
        >>> legs = [
        ...     TriangularLeg(pair="BTC/USDT", rate=1 / 50000),
        ...     TriangularLeg(pair="ETH/BTC", rate=50000 / 3000),
        ...     TriangularLeg(pair="ETH/USDT", rate=3000),
        ... ]
        >>> round(triangular_edge(legs).edge, 6)
        0.0
    """
    if len(legs) < 2:
        raise ValueError("a triangular cycle needs at least two legs")
    if not 0.0 <= fee_rate < 1.0:
        raise ValueError("fee_rate must be in [0, 1)")

    keep = 1.0 - fee_rate
    gross_product = 1.0
    net_product = 1.0
    for leg in legs:
        gross_product *= leg.rate
        net_product *= leg.rate * keep

    edge = net_product - 1.0
    return TriangularResult(
        gross_product=gross_product,
        net_product=net_product,
        edge=edge,
        is_profitable=edge > 1e-12,
    )
