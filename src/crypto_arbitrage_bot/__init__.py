"""Crypto Arbitrage Bot — cross-exchange and triangular arbitrage detector by Viprasol Tech."""

from __future__ import annotations

from crypto_arbitrage_bot.config import ScanConfig
from crypto_arbitrage_bot.cross import (
    CrossArbResult,
    ExchangeQuote,
    cross_exchange_profit,
)
from crypto_arbitrage_bot.fees import FeeModel, Side
from crypto_arbitrage_bot.graph import Cycle, CycleLeg, MarketPair, PairGraph
from crypto_arbitrage_bot.report import Report, ReportRow, build_report, render_table
from crypto_arbitrage_bot.scanner import (
    CrossOpportunity,
    VenueQuote,
    rank_cross,
    scan_cross,
)
from crypto_arbitrage_bot.triangular import (
    TriangularLeg,
    TriangularResult,
    triangular_edge,
)

__version__ = "0.2.0"
__author__ = "Viprasol Tech Private Limited"
__all__ = [  # noqa: RUF022 - grouped by domain for readability
    "__version__",
    # config
    "ScanConfig",
    # fees
    "FeeModel",
    "Side",
    # cross (pairwise)
    "ExchangeQuote",
    "CrossArbResult",
    "cross_exchange_profit",
    # cross (N-venue scanner)
    "VenueQuote",
    "CrossOpportunity",
    "scan_cross",
    "rank_cross",
    # triangular (single cycle)
    "TriangularLeg",
    "TriangularResult",
    "triangular_edge",
    # triangular (graph)
    "MarketPair",
    "PairGraph",
    "Cycle",
    "CycleLeg",
    # reporting
    "Report",
    "ReportRow",
    "build_report",
    "render_table",
]
