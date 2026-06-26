from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Direction(str, Enum):
    MIN = "min"          # lower is better
    MAX = "max"          # higher is better
    MATCH = "match"      # exact/boolean match is better
    INFO = "info"        # display only, no score


class Objective(str, Enum):
    BALANCED = "balanced"
    TOTAL_PAYMENT = "total_payment"
    MONTHLY_PAYMENT = "monthly_payment"
    FIXED_RATE = "fixed_rate"
    WEB_COMPLETE = "web_complete"
    RECOMMENDATION = "recommendation"


class Criterion(BaseModel):
    key: str
    label: str
    direction: Direction = Direction.MIN
    weight: float = Field(default=1.0, ge=0.0)
    required: bool = False
    ideal: Any | None = None
    note: str | None = None


class GenericOption(BaseModel):
    id: str
    name: str
    provider: str | None = None
    metrics: dict[str, float | int | bool | str | None] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    url: str | None = None


class GenericCompareRequest(BaseModel):
    criteria: list[Criterion]
    options: list[GenericOption]
    constraints: dict[str, Any] = Field(default_factory=dict)
    top_n: int = Field(default=10, ge=1, le=100)


class RankedOption(BaseModel):
    rank: int
    id: str
    name: str
    provider: str | None = None
    score: float
    eligible: bool = True
    reasons: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    url: str | None = None


class GenericCompareResponse(BaseModel):
    best: RankedOption | None
    ranked: list[RankedOption]
    warnings: list[str] = Field(default_factory=list)


class LoanPurpose(str, Enum):
    MULTI = "multi"
    DEBT_REFINANCE = "debt_refinance"
    HOME_REFINANCE = "home_refinance"
    HOME_PURCHASE = "home_purchase"
    AUTO = "auto"
    EDUCATION = "education"
    REFORM = "reform"
    BUSINESS = "business"
    OTHER = "other"


class RateType(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"
    MANUAL = "manual"


class LoanProduct(BaseModel):
    id: str
    provider: str
    name: str
    rate_min: float | None = None
    rate_max: float | None = None
    rate_type: RateType = RateType.FIXED
    guarantee_fee_included: bool | None = None
    amount_min: int
    amount_max: int
    term_months_min: int
    term_months_max: int
    purposes: list[LoanPurpose]
    excluded_purposes: list[LoanPurpose] = Field(default_factory=list)
    supports_bonus: bool = False
    supports_web_contract: bool = False
    supports_refinance: bool = False
    membership_rate: float | None = None
    normal_rate: float | None = None
    long_term_threshold_months: int | None = None
    long_term_rate_addition: float | None = None
    upfront_fee_percent: float | None = None
    condition_notes: list[str] = Field(default_factory=list)
    manual_rate_required: bool = False
    source_url: str | None = None
    notes: list[str] = Field(default_factory=list)

    def representative_rate(self, membership: bool, manual_rates: dict[str, float] | None = None) -> float | None:
        if manual_rates and self.id in manual_rates:
            return manual_rates[self.id]
        if membership and self.membership_rate is not None:
            return self.membership_rate
        if self.normal_rate is not None:
            return self.normal_rate
        if self.rate_min is not None:
            return self.rate_min
        return None


class LoanCompareRequest(BaseModel):
    amount: int = Field(..., ge=1)
    term_months: int = Field(..., ge=1, le=600)
    annual_income: int | None = Field(default=None, ge=0)
    purpose: LoanPurpose = LoanPurpose.MULTI
    membership: bool = False
    bonus_ratio: float = Field(default=0.0, ge=0.0, le=0.5)
    objective: Objective = Objective.BALANCED
    manual_rates: dict[str, float] = Field(default_factory=dict)
    include_ineligible: bool = True
    query: str | None = Field(default=None, max_length=120)
    providers: list[str] = Field(default_factory=list, max_length=20)
    product_ids: list[str] = Field(default_factory=list, max_length=50)
    rate_type: RateType | None = None
    max_monthly_payment: int | None = Field(default=None, ge=1)
    max_total_payment: int | None = Field(default=None, ge=1)
    max_interest_total: int | None = Field(default=None, ge=0)
    require_web_contract: bool | None = None
    require_refinance: bool | None = None
    require_bonus_support: bool | None = None
    current_annual_rate: float | None = Field(default=None, ge=0.0, le=30.0)
    reset_annual_rate: float | None = Field(default=None, ge=0.0, le=30.0)
    current_monthly_payment: int | None = Field(default=None, ge=0)
    reset_monthly_payment: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_bonus_ratio(self) -> "LoanCompareRequest":
        if self.bonus_ratio and self.bonus_ratio > 0.5:
            raise ValueError("bonus_ratio must be 0.50 or less")
        return self


class LoanPayment(BaseModel):
    product_id: str
    provider: str
    name: str
    annual_rate: float | None
    rate_type: RateType
    monthly_payment: int | None
    bonus_payment: int | None
    total_payment: int | None
    interest_total: int | None
    burden_ratio_percent: float | None
    monthly_delta_vs_current: int | None = None
    monthly_savings_vs_reset: int | None = None
    eligible: bool
    rank: int | None = None
    score: float | None = None
    reasons: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    source_url: str | None = None


class LoanCompareResponse(BaseModel):
    best: LoanPayment | None
    results: list[LoanPayment]
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    filters_applied: list[str] = Field(default_factory=list)
    recommendation_summary: str | None = None
    matched_count: int = 0
    eligible_count: int = 0
    suggested_next_actions: list[str] = Field(default_factory=list)


class PluginManifest(BaseModel):
    id: str
    name: str
    version: str
    category: str
    api_base: str = "/v1"
    tools: list[dict[str, Any]] = Field(default_factory=list)
    supported_agents: list[Literal["codex", "claude-code", "gemini-cli", "cursor", "hermes-agent", "mcp"]]
    notes: list[str] = Field(default_factory=list)
