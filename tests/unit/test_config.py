from __future__ import annotations

from pathlib import Path

import pytest

from crypto_arbitrage_bot.config import ScanConfig


def test_defaults_are_sane() -> None:
    """A default config is permissive and triangle-sized."""
    cfg = ScanConfig()
    assert cfg.min_edge_pct == 0.0
    assert cfg.max_cycle_len == 3
    assert cfg.min_edge_fraction == 0.0


def test_min_edge_fraction_is_percent_over_hundred() -> None:
    """0.25% becomes the fraction 0.0025."""
    cfg = ScanConfig(min_edge_pct=0.25)
    assert cfg.min_edge_fraction == pytest.approx(0.0025)


def test_reference_notional_falls_back_to_notional() -> None:
    """When reference_notional is unset, it mirrors notional."""
    cfg = ScanConfig(notional=10_000.0)
    assert cfg.effective_reference_notional == pytest.approx(10_000.0)


def test_reference_notional_honoured_when_set() -> None:
    """An explicit reference notional overrides the fallback."""
    cfg = ScanConfig(notional=10_000.0, reference_notional=50_000.0)
    assert cfg.effective_reference_notional == pytest.approx(50_000.0)


def test_round_trips_through_json(tmp_path: Path) -> None:
    """A config survives a write/read cycle unchanged."""
    cfg = ScanConfig(min_edge_pct=0.1, notional=1_000.0, max_cycle_len=4)
    path = tmp_path / "cfg.json"
    cfg.to_json(path)
    loaded = ScanConfig.from_json(path)
    assert loaded == cfg


def test_from_json_rejects_bad_values(tmp_path: Path) -> None:
    """Validation rejects an out-of-range cycle length."""
    path = tmp_path / "bad.json"
    path.write_text('{"max_cycle_len": 1}', encoding="utf-8")
    with pytest.raises(ValueError):
        ScanConfig.from_json(path)


def test_from_json_rejects_malformed_json(tmp_path: Path) -> None:
    """Malformed JSON raises a clear ValueError, not a raw decode error."""
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        ScanConfig.from_json(path)


def test_from_json_missing_file_raises(tmp_path: Path) -> None:
    """A missing config path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        ScanConfig.from_json(tmp_path / "nope.json")
