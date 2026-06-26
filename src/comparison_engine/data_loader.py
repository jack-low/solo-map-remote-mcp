from __future__ import annotations

import json
from pathlib import Path

from .models import LoanProduct, PluginManifest

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


def load_loan_products(path: str | Path | None = None) -> list[LoanProduct]:
    target = Path(path) if path else DATA_DIR / "loan_products.json"
    data = json.loads(target.read_text(encoding="utf-8"))
    return [LoanProduct.model_validate(item) for item in data]


def load_plugin_manifest(path: str | Path | None = None) -> PluginManifest:
    target = Path(path) if path else DATA_DIR / "plugin_manifest.json"
    return PluginManifest.model_validate_json(target.read_text(encoding="utf-8"))
