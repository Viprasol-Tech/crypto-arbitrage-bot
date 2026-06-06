"""Fee and slippage modelling for arbitrage estimates.

Top-of-book prices flatter every arbitrage estimate: they assume infinite depth
at the best quote and zero cost beyond the taker fee. Real fills pay a taker fee
*and* walk the book, so the effective buy price is higher and the effective sell
price lower than the headline quote. This module turns a nominal price into an
*effective* price once a linear slippage model and the taker fee are applied.

The slippage model is intentionally simple and transparent: the price impact is
``slippage_bps / 10_000`` of the quote, scaled linearly by how much of a
reference notional the trade consumes. It is a first-order correction, not a
microstructure simulator — but it is enough to stop a 0.05% top-of-book "edge"
from masquerading as profit once realistic costs are subtracted.

Part of Crypto Arbitrage Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

BPS = 10_000.0


class Side(str, Enum):
    """Which way a fill goes."""

    BUY = "buy"
    SELL = "sell"


class FeeModel(BaseModel):
    """Trading-cost assumptions applied to a single fill.

    Args:
        taker_fee: Taker fee as a fraction (e.g. ``0.001`` for 0.1%).
        slippage_bps: Baseline price impact in basis points charged on every
            fill, before any notional scaling.
        impact_per_notional_bps: Extra basis points of impact per unit of
            ``size / reference_notional``. With the default of ``0`` the model is
            a flat slippage charge; raise it to make larger orders cost more.
    """

    taker_fee: float = Field(default=0.001, ge=0.0, lt=1.0)
    slippage_bps: float = Field(default=0.0, ge=0.0)
    impact_per_notional_bps: float = Field(default=0.0, ge=0.0)

    def slippage_fraction(self, size: float = 0.0, reference_notional: float = 0.0) -> float:
        """Return the fractional price impact for a fill of ``size``.

        Args:
            size: Notional value of this fill in quote currency. Only matters
                when ``impact_per_notional_bps`` is non-zero.
            reference_notional: Notional that ``impact_per_notional_bps`` is
                expressed against. Ignored when non-positive.

        Returns:
            The fractional price impact (e.g. ``0.0005`` for 5 bps).
        """
        impact_bps = self.slippage_bps
        if self.impact_per_notional_bps > 0.0 and reference_notional > 0.0:
            impact_bps += self.impact_per_notional_bps * (size / reference_notional)
        return impact_bps / BPS

    def effective_price(
        self,
        price: float,
        side: Side,
        size: float = 0.0,
        reference_notional: float = 0.0,
    ) -> float:
        """Adjust a quote for fee and slippage in the direction of the trade.

        A buy fills *above* the quote (you pay the fee and cross the spread); a
        sell fills *below* it. The fee and slippage compound multiplicatively.

        Args:
            price: The nominal quote price (must be positive).
            side: Whether you are buying or selling at this price.
            size: Notional of the fill, passed through to the slippage model.
            reference_notional: Reference notional for size-aware slippage.

        Returns:
            The effective fill price after costs.

        Raises:
            ValueError: If ``price`` is not strictly positive.
        """
        if price <= 0.0:
            raise ValueError("price must be positive")
        slip = self.slippage_fraction(size=size, reference_notional=reference_notional)
        if side is Side.BUY:
            return price * (1.0 + self.taker_fee) * (1.0 + slip)
        return price * (1.0 - self.taker_fee) * (1.0 - slip)

    def round_trip_cost_fraction(self, size: float = 0.0, reference_notional: float = 0.0) -> float:
        """Approximate the total fractional cost of a buy-then-sell round trip.

        This is the fraction of notional eaten by two taker fees and two
        slippage charges, useful as a quick break-even threshold.

        Args:
            size: Notional of each leg.
            reference_notional: Reference notional for size-aware slippage.

        Returns:
            The combined round-trip cost as a fraction of notional.
        """
        slip = self.slippage_fraction(size=size, reference_notional=reference_notional)
        buy = (1.0 + self.taker_fee) * (1.0 + slip)
        sell = (1.0 - self.taker_fee) * (1.0 - slip)
        return buy - sell
