from __future__ import annotations

from crypto_arbitrage_bot.graph import MarketPair, PairGraph
from crypto_arbitrage_bot.report import build_report, render_table
from crypto_arbitrage_bot.scanner import VenueQuote, rank_cross


def _cross() -> list:
    board = [
        VenueQuote(exchange="a", price=100.0),
        VenueQuote(exchange="b", price=103.0),
    ]
    return rank_cross("X/USDT", board, profitable_only=True)


def _cycles() -> list:
    graph = PairGraph(
        [
            MarketPair(base="BTC", quote="USDT", price=50_000.0),
            MarketPair(base="ETH", quote="BTC", price=3_000.0 / 50_000.0),
            MarketPair(base="ETH", quote="USDT", price=3_150.0),
        ]
    )
    return graph.find_cycles(max_len=3, profitable_only=True)


def test_report_combines_cross_and_cycles() -> None:
    """A report merges both opportunity types into one ranked list."""
    report = build_report(cross=_cross(), cycles=_cycles())
    kinds = {row.kind for row in report.rows}
    assert kinds == {"cross", "triangular"}


def test_report_sorted_by_edge_descending() -> None:
    """Rows come back best-edge first."""
    report = build_report(cross=_cross(), cycles=_cycles())
    edges = [row.edge_pct for row in report.rows]
    assert edges == sorted(edges, reverse=True)


def test_threshold_filters_low_edges() -> None:
    """A high min_edge_pct drops everything below it."""
    report = build_report(cross=_cross(), cycles=_cycles(), min_edge_pct=99.0)
    assert report.rows == []
    assert report.best_edge_pct == 0.0


def test_profitable_count_and_best_edge() -> None:
    """Summary properties reflect the rows."""
    report = build_report(cross=_cross(), cycles=_cycles())
    assert report.profitable_count == len(report.rows)
    assert report.best_edge_pct == report.rows[0].edge_pct


def test_cross_route_names_both_venues() -> None:
    """A cross row's route mentions buy and sell venues."""
    report = build_report(cross=_cross())
    route = report.rows[0].route
    assert "buy@a" in route and "sell@b" in route


def test_render_table_handles_empty_report() -> None:
    """Rendering an empty report still produces a table without raising."""
    report = build_report()
    table = render_table(report)
    assert table.row_count == 1  # the placeholder row


def test_render_table_has_a_row_per_opportunity() -> None:
    """Each opportunity becomes one table row."""
    report = build_report(cross=_cross(), cycles=_cycles())
    table = render_table(report)
    assert table.row_count == len(report.rows)
