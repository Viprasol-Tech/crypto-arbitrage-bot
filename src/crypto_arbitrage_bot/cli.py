"""Command-line interface for Crypto Arbitrage Bot.

``crypto-arbitrage-bot demo`` runs both a cross-exchange and a triangular
arbitrage check on illustrative quotes — no API keys, no risk.

Part of Crypto Arbitrage Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from crypto_arbitrage_bot import __version__
from crypto_arbitrage_bot.cross import ExchangeQuote, cross_exchange_profit
from crypto_arbitrage_bot.triangular import TriangularLeg, triangular_edge

app = typer.Typer(add_completion=False, help="Crypto Arbitrage Bot — by Viprasol Tech.")
console = Console()


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


@app.command()
def demo(mode: str = typer.Option("both", help="cross | triangular | both")) -> None:
    """Run an arbitrage check on illustrative quotes."""
    if mode in ("cross", "both"):
        _run_cross()
    if mode in ("triangular", "both"):
        _run_triangular()
    if mode not in ("cross", "triangular", "both"):
        console.print("[red]mode must be 'cross', 'triangular', or 'both'[/]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
