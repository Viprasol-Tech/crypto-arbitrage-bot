from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from crypto_arbitrage_bot import __version__
from crypto_arbitrage_bot.cli import app

runner = CliRunner()


def test_version_prints_version() -> None:
    """`version` prints the package version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_demo_both_runs_clean() -> None:
    """`demo` default mode runs both checks without error."""
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "Cross-exchange" in result.stdout
    assert "Triangular" in result.stdout


def test_demo_scan_mode_runs() -> None:
    """`demo --mode scan` renders the combined report."""
    result = runner.invoke(app, ["demo", "--mode", "scan"])
    assert result.exit_code == 0
    assert "opportunity report" in result.stdout.lower()


def test_demo_rejects_bad_mode() -> None:
    """An unknown mode exits non-zero."""
    result = runner.invoke(app, ["demo", "--mode", "nonsense"])
    assert result.exit_code == 1


def test_scan_cross_reads_json(tmp_path: Path) -> None:
    """`scan-cross` reads a quote board and finds the edge."""
    board = [
        {"exchange": "a", "price": 100.0},
        {"exchange": "b", "price": 103.0},
    ]
    path = tmp_path / "board.json"
    path.write_text(json.dumps(board), encoding="utf-8")
    result = runner.invoke(app, ["scan-cross", str(path), "--pair", "X/USDT"])
    assert result.exit_code == 0
    assert "buy@a" in result.stdout
    assert "sell@b" in result.stdout


def test_scan_cross_missing_file_exits_one() -> None:
    """A missing quotes file exits non-zero with a message."""
    result = runner.invoke(app, ["scan-cross", "does-not-exist.json"])
    assert result.exit_code == 1
    assert "not found" in result.stdout.lower()


def test_scan_triangular_finds_cycle(tmp_path: Path) -> None:
    """`scan-triangular` discovers a profitable cycle from market pairs."""
    pairs = [
        {"base": "BTC", "quote": "USDT", "price": 50000.0},
        {"base": "ETH", "quote": "BTC", "price": 0.06},
        {"base": "ETH", "quote": "USDT", "price": 3150.0},
    ]
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(pairs), encoding="utf-8")
    result = runner.invoke(app, ["scan-triangular", str(path)])
    assert result.exit_code == 0
    assert "directed edges" in result.stdout


def test_init_config_writes_and_refuses_overwrite(tmp_path: Path) -> None:
    """`init-config` writes a file once and refuses to clobber it."""
    path = tmp_path / "arb-config.json"
    first = runner.invoke(app, ["init-config", str(path)])
    assert first.exit_code == 0
    assert path.exists()
    second = runner.invoke(app, ["init-config", str(path)])
    assert second.exit_code == 1
