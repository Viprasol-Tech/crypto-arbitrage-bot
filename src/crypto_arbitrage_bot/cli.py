"""Command-line interface for Crypto Arbitrage Bot.

Subcommands:

* ``version`` — print the installed version.
* ``demo`` — run cross and/or triangular checks on illustrative quotes.
* ``scan-cross`` — scan an N-venue quote board (JSON) for the best cross edge.
* ``scan-triangular`` — find profitable cycles in a pair graph (JSON).
* ``init-config`` — write a starter ``ScanConfig`` JSON file.

No API keys, no live orders — everything operates on data you provide.

Part of Crypto Arbitrage Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from crypto_arbitrage_bot import __version__
from crypto_arbitrage_bot.config import ScanConfig
from crypto_arbitrage_bot.cross import ExchangeQuote, cross_exchange_profit
from crypto_arbitrage_bot.graph import MarketPair, PairGraph
from crypto_arbitrage_bot.report import build_report, render_table
from crypto_arbitrage_bot.scanner import VenueQuote, rank_cross
from crypto_arbitrage_bot.triangular import TriangularLeg, triangular_edge

app = typer.Typer(add_completion=False, help="Crypto Arbitrage Bot - by Viprasol Tech.")
console = Console()


def _load_json(path: Path) -> object:
    if not path.exists():
        console.print(f"[red]file not found:[/] {path}")
        raise typer.Exit(code=1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        console.print(f"[red]invalid JSON in {path}:[/] {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"crypto-arbitrage-bot [bold cyan]{__version__}[/] - by Viprasol Tech")


def _run_cross() -> None:
    """Demo the cross-exchange detector with a mispriced BTC/USDT quote."""
    a = ExchangeQuote(exchange="binance", price=50_000.0, fee_rate=0.001)
    b = ExchangeQuote(exchange="kraken", price=50_300.0, fee_rate=0.001)
    result = cross_exchange_profit(a, b)

    table = Table(title="Cross-exchange arbitrage (BTC/USDT)")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Buy on", result.buy_exchange)
    table.add_row("Sell on", result.sell_exchange)
    table.add_row("Buy cost / unit", f"${result.buy_cost:,.2f}")
    table.add_row("Sell proceeds / unit", f"${result.sell_proceeds:,.2f}")
    table.add_row("Net profit / unit", f"${result.net_profit:,.2f}")
    table.add_row("Net profit %", f"{result.net_profit_pct * 100:.3f}%")
    verdict = "[bold green]PROFITABLE[/]" if result.is_profitable else "[red]no edge[/]"
    table.add_row("Verdict", verdict)
    console.print(table)


def _run_triangular() -> None:
    """Demo the triangular detector with a deliberately mispriced cycle."""
    legs = [
        TriangularLeg(pair="BTC/USDT", rate=1.0 / 50_000.0),
        TriangularLeg(pair="ETH/BTC", rate=50_000.0 / 3_000.0),
        TriangularLeg(pair="ETH/USDT", rate=3_030.0),
    ]
    result = triangular_edge(legs, fee_rate=0.001)

    table = Table(title="Triangular arbitrage (USDT -> BTC -> ETH -> USDT)")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Gross cycle product", f"{result.gross_product:.6f}")
    table.add_row("Net cycle product", f"{result.net_product:.6f}")
    table.add_row("Edge", f"{result.edge * 100:.4f}%")
    verdict = "[bold green]PROFITABLE[/]" if result.is_profitable else "[red]no edge[/]"
    table.add_row("Verdict", verdict)
    console.print(table)


def _run_scan_demo() -> None:
    """Demo the N-venue scanner + graph finder, rendered as one report."""
    board = [
        VenueQuote(exchange="binance", price=50_000.0),
        VenueQuote(exchange="kraken", price=50_300.0),
        VenueQuote(exchange="coinbase", price=49_950.0),
    ]
    cross = rank_cross("BTC/USDT", board, profitable_only=True)

    graph = PairGraph(
        [
            MarketPair(base="BTC", quote="USDT", price=50_000.0),
            MarketPair(base="ETH", quote="BTC", price=3_000.0 / 50_000.0),
            MarketPair(base="ETH", quote="USDT", price=3_150.0),
        ]
    )
    cycles = graph.find_cycles(max_len=3, profitable_only=True)
    report = build_report(cross=cross, cycles=cycles, min_edge_pct=0.0)
    console.print(render_table(report, title="Combined opportunity report (demo)"))


@app.command()
def demo(mode: str = typer.Option("both", help="cross | triangular | scan | both")) -> None:
    """Run an arbitrage check on illustrative quotes."""
    if mode not in ("cross", "triangular", "scan", "both"):
        console.print("[red]mode must be 'cross', 'triangular', 'scan', or 'both'[/]")
        raise typer.Exit(code=1)
    if mode in ("cross", "both"):
        _run_cross()
    if mode in ("triangular", "both"):
        _run_triangular()
    if mode == "scan":
        _run_scan_demo()


@app.command(name="scan-cross")
def scan_cross_cmd(
    quotes: Path = typer.Argument(..., help="JSON file: a quote board for one pair."),
    pair: str = typer.Option("PAIR", help="Label for the trading pair."),
    min_edge_pct: float = typer.Option(0.0, help="Minimum edge %% to report."),
    size: float = typer.Option(0.0, help="Per-leg notional for slippage."),
) -> None:
    """Scan an N-venue quote board for the best cross-exchange edges.

    The JSON file must be a list of ``{"exchange", "price", "fees"?}`` objects.
    """
    raw = _load_json(quotes)
    if not isinstance(raw, list):
        console.print("[red]quotes file must contain a JSON list of venue quotes[/]")
        raise typer.Exit(code=1)
    board = [VenueQuote.model_validate(item) for item in raw]
    ranked = rank_cross(pair, board, size=size, reference_notional=size, profitable_only=False)
    report = build_report(cross=ranked, min_edge_pct=min_edge_pct)
    console.print(render_table(report, title=f"Cross-exchange scan: {pair}"))
    if report.profitable_count == 0:
        console.print("[yellow]No profitable cross opportunities above threshold.[/]")


@app.command(name="scan-triangular")
def scan_triangular_cmd(
    pairs: Path = typer.Argument(..., help="JSON file: a list of market pairs."),
    max_len: int = typer.Option(3, help="Maximum cycle length (legs)."),
    min_edge_pct: float = typer.Option(0.0, help="Minimum edge %% to report."),
    start: str = typer.Option("", help="Optional start asset for cycles."),
) -> None:
    """Find profitable cycles in a pair graph built from market pairs.

    The JSON file must be a list of ``{"base", "quote", "price", "fees"?}``.
    """
    raw = _load_json(pairs)
    if not isinstance(raw, list):
        console.print("[red]pairs file must contain a JSON list of market pairs[/]")
        raise typer.Exit(code=1)
    market = [MarketPair.model_validate(item) for item in raw]
    graph = PairGraph(market)
    cycles = graph.find_cycles(start=start or None, max_len=max_len, profitable_only=False)
    report = build_report(cycles=cycles, min_edge_pct=min_edge_pct)
    console.print(render_table(report, title="Triangular scan"))
    console.print(f"[dim]graph: {len(graph.assets)} assets, {graph.edge_count()} directed edges[/]")
    if report.profitable_count == 0:
        console.print("[yellow]No profitable cycles above threshold.[/]")


@app.command(name="init-config")
def init_config_cmd(
    path: Path = typer.Argument(Path("arb-config.json"), help="Where to write the config."),
) -> None:
    """Write a starter scan-config JSON file you can edit."""
    if path.exists():
        console.print(f"[red]refusing to overwrite existing file:[/] {path}")
        raise typer.Exit(code=1)
    ScanConfig(min_edge_pct=0.1, notional=10_000.0, max_cycle_len=3).to_json(path)
    console.print(f"[green]wrote starter config to[/] {path}")


if __name__ == "__main__":
    app()
