from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import __version__
from .data_loader import load_loan_products, load_plugin_manifest
from .engine import compare_generic, compare_loans
from .models import GenericCompareRequest, LoanCompareRequest

mcp = FastMCP("solo-map-comparison-engine")


@mcp.tool()
def list_comparison_plugins() -> dict[str, Any]:
    """List available Solo Map comparison plugins and supported agent surfaces."""
    return {"version": __version__, "plugins": [load_plugin_manifest().model_dump()]}


@mcp.tool()
def compare_loan_repayment(
    amount: int,
    term_months: int,
    purpose: str = "multi",
    annual_income: int | None = None,
    membership: bool = False,
    bonus_ratio: float = 0.0,
    objective: str = "balanced",
    manual_rates_json: str = "{}",
    query: str | None = None,
    providers_json: str = "[]",
    rate_type: str | None = None,
    max_monthly_payment: int | None = None,
    require_web_contract: bool | None = None,
    include_ineligible: bool = True,
    current_annual_rate: float | None = None,
    reset_annual_rate: float | None = None,
    current_monthly_payment: int | None = None,
    reset_monthly_payment: int | None = None,
) -> dict[str, Any]:
    """Compare loan repayment plans and return ranked options with assumptions and warnings.

    Use this for personal loans, refinance checks, purpose loans, and repayment planning.
    `manual_rates_json` is a JSON object keyed by product id, e.g. {"hokkaido-bank-best-free": 7.8}.
    """
    try:
        manual_rates = json.loads(manual_rates_json or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"manual_rates_json is not valid JSON: {exc}") from exc
    try:
        providers = json.loads(providers_json or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"providers_json is not valid JSON: {exc}") from exc
    request = LoanCompareRequest.model_validate(
        {
            "amount": amount,
            "term_months": term_months,
            "purpose": purpose,
            "annual_income": annual_income,
            "membership": membership,
            "bonus_ratio": bonus_ratio,
            "objective": objective,
            "manual_rates": manual_rates,
            "query": query,
            "providers": providers,
            "rate_type": rate_type,
            "max_monthly_payment": max_monthly_payment,
            "require_web_contract": require_web_contract,
            "include_ineligible": include_ineligible,
            "current_annual_rate": current_annual_rate,
            "reset_annual_rate": reset_annual_rate,
            "current_monthly_payment": current_monthly_payment,
            "reset_monthly_payment": reset_monthly_payment,
        }
    )
    return compare_loans(load_loan_products(), request).model_dump()


@mcp.tool()
def compare_generic_options(payload_json: str) -> dict[str, Any]:
    """Run a generic weighted comparison.

    The payload must match GenericCompareRequest:
    {"criteria": [...], "options": [...], "constraints": {...}}
    Use this for products, SaaS, vendors, grants, insurance, devices, tools, schools, or any ranked decision.
    """
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"payload_json is not valid JSON: {exc}") from exc
    request = GenericCompareRequest.model_validate(payload)
    return compare_generic(request).model_dump()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
