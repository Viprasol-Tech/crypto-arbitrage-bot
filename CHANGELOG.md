# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/).

## [0.2.0] - 2025

### Added
- **N-exchange cross scanner** (`scanner.py`): `scan_cross` finds the single best
  buy/sell venue pair for one trading pair across many venues, and `rank_cross`
  ranks every directed venue pair by net edge.
- **Triangular cycle finder over a full pair graph** (`graph.py`): `PairGraph`
  builds a directed conversion graph (two edges per market pair) and
  `find_cycles` enumerates profitable simple cycles up to a bounded length, with
  canonical-rotation deduplication so each loop is reported once.
- **Fee + slippage modelling** (`fees.py`): `FeeModel` turns a nominal quote into
  an effective fill price using a taker fee plus a transparent linear (optionally
  size-aware) slippage model; includes a round-trip break-even helper.
- **Profit / opportunity report** (`report.py`): `build_report` merges cross and
  triangular results into one ranked, threshold-filtered `Report`, and
  `render_table` formats it as a Rich table.
- **Scan configuration** (`config.py`): `ScanConfig` is a validated, JSON
  round-trippable bundle of scan parameters (min edge, notional, cycle length,
  default fees).
- **CLI subcommands**: `scan-cross` and `scan-triangular` read quote/pair boards
  from JSON, `init-config` writes a starter config, and `demo --mode scan`
  showcases the combined report.
- Public API re-exported from the package root for ergonomic imports.

### Changed
- Bumped version to 0.2.0.
- Roughly quadrupled the test suite (13 → 60 tests) with assertions covering
  fees, slippage, the scanner, the graph finder, config, reporting, and the CLI.

## [0.1.0] - 2025

### Added
- Initial release of crypto-arbitrage-bot: Cross-exchange and triangular crypto arbitrage detector.
