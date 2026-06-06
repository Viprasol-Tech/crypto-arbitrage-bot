"""N-exchange cross-venue arbitrage scanner.

The pairwise :func:`crypto_arbitrage_bot.cross.cross_exchange_profit` answers
"which of these two venues is cheaper?". A real desk watches the same pair on
many venues at once and wants the single best buy/sell pair ranked against every
other candidate. This module does exactly that: given a board of quotes for one
pair across N exchanges, it finds the cheapest place to buy and the dearest
place to sell *after* fee and slippage costs, and can rank every directed venue
pair by net edge.

It reuses :class:`crypto_arbitrage_bot.fees.FeeModel` so the same cost
assumptions drive both the cross scanner and the triangular finder.

Part of Crypto Arbitrage Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from itertools import permutations

from pydantic import BaseModel, Field

from crypto_arbitrage_bot.fees import FeeModel, Side


class VenueQuote(BaseModel):
    """A price quote for one pair on one venue, with its own cost model.

    Args:
        exchange: Human-readable venue name (e.g. ``"binance"``).
        price: The quote (mid/last) price of the pair on this venue.
        fees: The fee and slippage model for fills on this venue.
    """

    exchange: str = Field(min_length=1)
    price: float = Field(gt=0.0)
    fees: FeeModel = Field(default_factory=FeeModel)


class CrossOpportunity(BaseModel):
    """A directed buy-here / sell-there opportunity for one pair.

    Attributes:
        pair: The trading pair this opportunity is for.
        buy_exchange: Venue to buy on.
        sell_exchange: Venue to sell on.
        buy_cost: Effective cash paid per unit on the buy side, after costs.
        sell_proceeds: Effective cash received per unit, after costs.
        net_profit: ``sell_proceeds - buy_cost`` per unit (may be negative).
        net_profit_pct: ``net_profit`` as a fraction of ``buy_cost``.
        is_profitable: ``True`` when ``net_profit`` clears a tiny tolerance.
    """

    pair: str
    buy_exchange: str
    sell_exchange: str
    buy_cost: float
    sell_proceeds: float
    net_profit: float
    net_profit_pct: float
    is_profitable: bool


def _directed_opportunity(
    pair: str,
    buy: VenueQuote,
    sell: VenueQuote,
    size: float,
    reference_notional: float,
) -> CrossOpportunity:
    buy_cost = buy.fees.effective_price(
        buy.price, Side.BUY, size=size, reference_notional=reference_notional
    )
    sell_proceeds = sell.fees.effective_price(
        sell.price, Side.SELL, size=size, reference_notional=reference_notional
    )
    net_profit = sell_proceeds - buy_cost
    return CrossOpportunity(
        pair=pair,
        buy_exchange=buy.exchange,
        sell_exchange=sell.exchange,
        buy_cost=buy_cost,
        sell_proceeds=sell_proceeds,
        net_profit=net_profit,
        net_profit_pct=net_profit / buy_cost,
        is_profitable=net_profit > 1e-12,
    )


def scan_cross(
    pair: str,
    quotes: list[VenueQuote],
    *,
    size: float = 0.0,
    reference_notional: float = 0.0,
) -> CrossOpportunity:
    """Find the single best buy/sell venue pair for one trading pair.

    Buys at the venue with the lowest effective buy price and sells at the venue
    with the highest effective sell proceeds. The two need not be distinct venues
    in degenerate inputs, but with at least two venues the function never returns
    a same-venue trade unless that is genuinely the only pairing.

    Args:
        pair: Label for the trading pair (e.g. ``"BTC/USDT"``).
        quotes: Quotes for the pair across two or more venues.
        size: Notional per leg, forwarded to each venue's slippage model.
        reference_notional: Reference notional for size-aware slippage.

    Returns:
        The best :class:`CrossOpportunity`, by net profit per unit.

    Raises:
        ValueError: If fewer than two venues are supplied.

    Example:
        >>> board = [
        ...     VenueQuote(exchange="a", price=100.0),
        ...     VenueQuote(exchange="b", price=103.0),
        ...     VenueQuote(exchange="c", price=101.0),
        ... ]
        >>> best = scan_cross("X/USDT", board)
        >>> best.buy_exchange, best.sell_exchange
        ('a', 'b')
    """
    if len(quotes) < 2:
        raise ValueError("need at least two venues to cross")

    best: CrossOpportunity | None = None
    for buy, sell in permutations(quotes, 2):
        opp = _directed_opportunity(pair, buy, sell, size, reference_notional)
        if best is None or opp.net_profit > best.net_profit:
            best = opp
    assert best is not None  # permutations of >=2 items is non-empty
    return best


def rank_cross(
    pair: str,
    quotes: list[VenueQuote],
    *,
    size: float = 0.0,
    reference_notional: float = 0.0,
    profitable_only: bool = False,
) -> list[CrossOpportunity]:
    """Rank every directed venue pair for one trading pair by net edge.

    Args:
        pair: Label for the trading pair.
        quotes: Quotes for the pair across two or more venues.
        size: Notional per leg, forwarded to each venue's slippage model.
        reference_notional: Reference notional for size-aware slippage.
        profitable_only: When ``True``, drop non-profitable directed pairs.

    Returns:
        Opportunities sorted by ``net_profit`` descending.

    Raises:
        ValueError: If fewer than two venues are supplied.
    """
    if len(quotes) < 2:
        raise ValueError("need at least two venues to cross")

    opps = [
        _directed_opportunity(pair, buy, sell, size, reference_notional)
        for buy, sell in permutations(quotes, 2)
    ]
    if profitable_only:
        opps = [o for o in opps if o.is_profitable]
    opps.sort(key=lambda o: o.net_profit, reverse=True)
    return opps
