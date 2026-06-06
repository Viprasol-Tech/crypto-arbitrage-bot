"""Scan configuration loaded from JSON.

A scan needs more than quotes: it needs the minimum edge worth reporting, the
notional size to assume for slippage, default fees for venues that do not
override them, and the maximum cycle length for the triangular finder. Bundling
these into a validated :class:`ScanConfig` keeps the CLI and library calls
consistent and lets users drive a scan from a single JSON file.

Part of Crypto Arbitrage Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from crypto_arbitrage_bot.fees import FeeModel


class ScanConfig(BaseModel):
    """Tunable parameters that govern a scan.

    Args:
        min_edge_pct: Minimum net edge, as a percentage, for an opportunity to be
            flagged in a report (e.g. ``0.1`` for 0.1%).
        notional: Assumed per-leg notional in quote currency, fed to slippage.
        reference_notional: Reference notional that size-aware slippage is scaled
            against. Defaults to ``notional`` when left at zero.
        max_cycle_len: Maximum number of legs for the triangular cycle finder.
        default_fees: Fee model applied to venues/pairs that omit their own.
    """

    min_edge_pct: float = Field(default=0.0, ge=0.0)
    notional: float = Field(default=0.0, ge=0.0)
    reference_notional: float = Field(default=0.0, ge=0.0)
    max_cycle_len: int = Field(default=3, ge=2)
    default_fees: FeeModel = Field(default_factory=FeeModel)

    @property
    def effective_reference_notional(self) -> float:
        """The reference notional, falling back to ``notional`` when unset."""
        return self.reference_notional if self.reference_notional > 0.0 else self.notional

    @property
    def min_edge_fraction(self) -> float:
        """``min_edge_pct`` expressed as a plain fraction."""
        return self.min_edge_pct / 100.0

    @classmethod
    def from_json(cls, path: str | Path) -> ScanConfig:
        """Load a config from a JSON file.

        Args:
            path: Path to a JSON document with config fields.

        Returns:
            The validated :class:`ScanConfig`.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            ValueError: If the JSON is malformed or fails validation.
        """
        text = Path(path).read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:  # pragma: no cover - thin wrapper
            raise ValueError(f"invalid JSON in {path}: {exc}") from exc
        return cls.model_validate(data)

    def to_json(self, path: str | Path) -> None:
        """Write this config to a JSON file (pretty-printed, UTF-8).

        Args:
            path: Destination path.
        """
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")
