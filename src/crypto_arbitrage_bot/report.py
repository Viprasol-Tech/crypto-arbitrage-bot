"""Profit / opportunity reporting.

The scanners and the graph finder return rich opportunity objects; a report turns
a heap of them into a ranked, threshold-filtered summary a human (or an alert
bot) can act on. A :class:`Report` is itself a pydantic model so it serialises
cleanly to JSON, and :func:`render_table` formats it as a Rich table for the CLI.

Part of Crypto Arbitrage Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from rich.table import Table

from crypto_arbitrage_bot.graph import Cycle
from crypto_arbitrage_bot.scanner import CrossOpportunity


class ReportRow(BaseModel):
    """A single line of an opportunity report.

    Attributes:
        kind: ``"cross"`` or ``"triangular"``.
        route: Human-readable path (``"buy@a -> sell@b"`` or asset loop).
        edge_pct: Net edge as a percentage.
        detail: Extra context (pair label or cycle assets).
        is_profitable: Whether the row cleared its profitability check.
    """

    kind: str
    route: str
    edge_pct: float
    detail: str
    is_profitable: bool


class Report(BaseModel):
    """A ranked, threshold-filtered set of opportunities.

    Attributes:
        rows: Opportunity rows, sorted by edge descending.
        min_edge_pct: The threshold used to filter rows.
    """

    rows: list[ReportRow] = Field(default_factory=list)
    min_edge_pct: float = 0.0

    @property
    def best_edge_pct(self) -> float:
        """The largest edge in the report, or ``0.0`` when empty."""
        return self.rows[0].edge_pct if self.rows else 0.0

    @property
    def profitable_count(self) -> int:
        """How many rows are flagged profitable."""
        return sum(1 for r in self.rows if r.is_profitable)


def _cross_row(opp: CrossOpportunity) -> ReportRow:
    return ReportRow(
        kind="cross",
        route=f"buy@{opp.buy_exchange} -> sell@{opp.sell_exchange}",
        edge_pct=opp.net_profit_pct * 100.0,
        detail=opp.pair,
        is_profitable=opp.is_profitable,
    )


def _cycle_row(cycle: Cycle) -> ReportRow:
    return ReportRow(
        kind="triangular",
        route=" -> ".join(cycle.assets),
        edge_pct=cycle.edge * 100.0,
        detail=" | ".join(leg.pair for leg in cycle.legs),
        is_profitable=cycle.is_profitable,
    )


def build_report(
    *,
    cross: list[CrossOpportunity] | None = None,
    cycles: list[Cycle] | None = None,
    min_edge_pct: float = 0.0,
) -> Report:
    """Combine cross and triangular results into one ranked, filtered report.

    Args:
        cross: Cross-venue opportunities to include.
        cycles: Triangular cycles to include.
        min_edge_pct: Drop any opportunity whose edge percentage is below this.

    Returns:
        A :class:`Report` sorted by edge descending.
    """
    rows: list[ReportRow] = []
    rows.extend(_cross_row(o) for o in (cross or []))
    rows.extend(_cycle_row(c) for c in (cycles or []))
    rows = [r for r in rows if r.edge_pct >= min_edge_pct]
    rows.sort(key=lambda r: r.edge_pct, reverse=True)
    return Report(rows=rows, min_edge_pct=min_edge_pct)


def render_table(report: Report, title: str = "Arbitrage opportunities") -> Table:
    """Render a report as a Rich table for terminal display.

    Args:
        report: The report to render.
        title: Table title.

    Returns:
        A populated :class:`rich.table.Table` (rendering is left to the caller).
    """
    table = Table(title=title)
    table.add_column("Kind")
    table.add_column("Route")
    table.add_column("Detail")
    table.add_column("Edge", justify="right")
    table.add_column("Verdict", justify="center")
    for row in report.rows:
        verdict = "[bold green]EDGE[/]" if row.is_profitable else "[red]none[/]"
        table.add_row(row.kind, row.route, row.detail, f"{row.edge_pct:.4f}%", verdict)
    if not report.rows:
        table.add_row("-", "no opportunities above threshold", "-", "-", "-")
    return table
