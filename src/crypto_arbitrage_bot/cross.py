"""Cross-exchange arbitrage detection.

Given the same trading pair quoted on two exchanges (each with its own taker
fee), buy on the cheaper venue and sell on the dearer one. This module computes
the realistic *net* profit per unit after both fees and tells you whether the
opportunity clears.

Part of Crypto Arbitrage Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExchangeQuote(BaseModel):
    """A price quote for one pair on one exchange.

    Args:
        exchange: Human-readable venue name (e.g. ``"binance"``).
        price: The quote (mid/last) price of the pair on this exchange.
        fee_rate: Taker fee as a fraction (e.g. ``0.001`` for 0.1%).
    """

    exchange: str = Field(min_length=1)
    price: float = Field(gt=0.0)
    fee_rate: float = Field(ge=0.0, lt=1.0)


class CrossArbResult(BaseModel):
    """Outcome of a cross-exchange arbitrage check.

    Attributes:
        buy_exchange: Venue to buy on (the cheaper one after fees).
        sell_exchange: Venue to sell on (the dearer one after fees).
        buy_cost: Cash paid per unit on the buy side, including its fee.
        sell_proceeds: Cash received per unit on the sell side, net of its fee.
        net_profit: ``sell_proceeds - buy_cost`` per unit (may be negative).
        net_profit_pct: ``net_profit`` as a fraction of ``buy_cost``.
        is_profitable: ``True`` when ``net_profit`` is strictly positive.
    """

    buy_exchange: str
    sell_exchange: str
    buy_cost: float
    sell_proceeds: float
    net_profit: float
    net_profit_pct: float
    is_profitable: bool


def cross_exchange_profit(a: ExchangeQuote, b: ExchangeQuote) -> CrossArbResult:
    """Compute net per-unit profit of buying on one exchange and selling on the other.

    The cheaper venue (after adding its taker fee) is used as the buy side and
    the other as the sell side. You pay ``price * (1 + fee_rate)`` to acquire one
    unit and receive ``price * (1 - fee_rate)`` when you dispose of it.

    Args:
        a: Quote on the first exchange.
        b: Quote on the second exchange.

    Returns:
        A :class:`CrossArbResult` describing direction, costs, and net profit.

    Example:
        >>> r = cross_exchange_profit(
        ...     ExchangeQuote(exchange="x", price=100.0, fee_rate=0.0),
        ...     ExchangeQuote(exchange="y", price=110.0, fee_rate=0.0),
        ... )
        >>> round(r.net_profit, 2)
        10.0
        >>> r.is_profitable
        True
    """
    cost_a = a.price * (1.0 + a.fee_rate)
    cost_b = b.price * (1.0 + b.fee_rate)

    if cost_a <= cost_b:
        buy, sell = a, b
    else:
        buy, sell = b, a

    buy_cost = buy.price * (1.0 + buy.fee_rate)
    sell_proceeds = sell.price * (1.0 - sell.fee_rate)
    net_profit = sell_proceeds - buy_cost
    net_profit_pct = net_profit / buy_cost

    return CrossArbResult(
        buy_exchange=buy.exchange,
        sell_exchange=sell.exchange,
        buy_cost=buy_cost,
        sell_proceeds=sell_proceeds,
        net_profit=net_profit,
        net_profit_pct=net_profit_pct,
        is_profitable=net_profit > 0.0,
    )
