from __future__ import annotations

from dataclasses import dataclass
from math import ceil
import unicodedata
from typing import Any

from .models import (
    Criterion,
    Direction,
    GenericCompareRequest,
    GenericCompareResponse,
    LoanCompareRequest,
    LoanCompareResponse,
    LoanPayment,
    LoanProduct,
    LoanPurpose,
    Objective,
    RateType,
    RankedOption,
)


def amortized_payment(principal: float, annual_rate_percent: float, periods: int, periods_per_year: int = 12) -> float:
    """Return level payment for an amortizing loan.

    `periods_per_year=12` for monthly repayment, `2` for semiannual bonus repayment.
    """
    if periods <= 0:
        raise ValueError("periods must be positive")
    if principal <= 0:
        return 0.0
    rate = annual_rate_percent / 100.0 / periods_per_year
    if abs(rate) < 1e-12:
        return principal / periods
    return principal * rate / (1 - (1 + rate) ** (-periods))


def yen(value: float | None) -> int | None:
    if value is None:
        return None
    return int(round(value))


def annual_burden_ratio(total_annual_repayment: float, annual_income: int | None) -> float | None:
    if not annual_income:
        return None
    return round(total_annual_repayment / annual_income * 100, 2)


def normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(ch for ch in normalized if ch.isalnum())


def product_search_blob(product: LoanProduct) -> str:
    values = [
        product.id,
        product.provider,
        product.name,
        product.rate_type.value,
        product.source_url or "",
        " ".join(purpose.value for purpose in product.purposes),
        " ".join(product.condition_notes),
        " ".join(product.notes),
    ]
    return normalize_search_text(" ".join(values))


def _contains_loose(haystack: str, needle: str) -> bool:
    normalized = normalize_search_text(needle)
    return not normalized or normalized in haystack


def product_matches_request(product: LoanProduct, request: LoanCompareRequest) -> tuple[bool, list[str]]:
    filters: list[str] = []
    blob = product_search_blob(product)
    if request.query and not _contains_loose(blob, request.query):
        filters.append(f"検索語に一致しない: {request.query}")
    if request.providers:
        provider_blob = normalize_search_text(product.provider)
        if not any(_contains_loose(provider_blob, provider) for provider in request.providers):
            filters.append(f"金融機関が一致しない: {', '.join(request.providers)}")
    if request.product_ids and product.id not in set(request.product_ids):
        filters.append("指定された商品IDではない")
    if request.rate_type and product.rate_type != request.rate_type:
        filters.append(f"金利タイプが一致しない: {request.rate_type.value}")
    if request.require_web_contract is not None and product.supports_web_contract != request.require_web_contract:
        filters.append("Web完結条件が一致しない")
    if request.require_refinance is not None and product.supports_refinance != request.require_refinance:
        filters.append("借換対応条件が一致しない")
    if request.require_bonus_support is not None and product.supports_bonus != request.require_bonus_support:
        filters.append("ボーナス返済対応条件が一致しない")
    return not filters, filters


def eligibility_reasons(product: LoanProduct, request: LoanCompareRequest, rate: float | None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if request.amount < product.amount_min or request.amount > product.amount_max:
        reasons.append(f"借入額が対象外: {product.amount_min:,}円〜{product.amount_max:,}円")
    if request.term_months < product.term_months_min or request.term_months > product.term_months_max:
        reasons.append(f"返済期間が対象外: {product.term_months_min}〜{product.term_months_max}か月")
    if request.purpose in product.excluded_purposes:
        reasons.append(f"用途が対象外: {request.purpose.value}")
    if request.purpose not in product.purposes and LoanPurpose.MULTI not in product.purposes:
        reasons.append(f"用途が明示対象外: {request.purpose.value}")
    if request.purpose == LoanPurpose.DEBT_REFINANCE and not product.supports_refinance:
        reasons.append("借換利用に非対応")
    if request.bonus_ratio > 0 and not product.supports_bonus:
        reasons.append("ボーナス併用返済に非対応")
    if product.manual_rate_required and rate is None:
        reasons.append("金利の手入力が必要")
    return len(reasons) == 0, reasons


def simulate_loan(product: LoanProduct, request: LoanCompareRequest) -> LoanPayment:
    rate = effective_rate(product, request)
    eligible, reasons = eligibility_reasons(product, request, rate)
    cautions: list[str] = []
    if product.rate_type == RateType.VARIABLE:
        cautions.append("変動金利のため将来返済額が変わる可能性があります")
    if product.long_term_threshold_months and product.long_term_rate_addition and request.term_months > product.long_term_threshold_months:
        cautions.append(
            f"{product.long_term_threshold_months}か月超のため年{product.long_term_rate_addition:.3f}%を上乗せして試算しています"
        )
    if product.upfront_fee_percent:
        cautions.append(f"事務手数料等の目安として借入額×{product.upfront_fee_percent:.2f}%を別途確認してください")
    cautions.extend(product.condition_notes)
    if product.manual_rate_required and product.id not in request.manual_rates:
        cautions.append("金利手入力がないため正式比較前に公式金利の確認が必要です")
    if not product.source_url:
        cautions.append("公式情報URLが未登録です")
    if rate is None:
        return LoanPayment(
            product_id=product.id,
            provider=product.provider,
            name=product.name,
            annual_rate=None,
            rate_type=product.rate_type,
            monthly_payment=None,
            bonus_payment=None,
            total_payment=None,
            interest_total=None,
            burden_ratio_percent=None,
            monthly_delta_vs_current=None,
            monthly_savings_vs_reset=None,
            eligible=False,
            reasons=reasons or ["金利が未設定のため試算不可"],
            highlights=_product_highlights(product),
            cautions=cautions,
            notes=product.notes,
            source_url=product.source_url,
        )

    monthly_principal = request.amount * (1 - request.bonus_ratio)
    bonus_principal = request.amount * request.bonus_ratio
    monthly_payment = amortized_payment(monthly_principal, rate, request.term_months, periods_per_year=12)
    bonus_periods = ceil(request.term_months / 6)
    bonus_payment = amortized_payment(bonus_principal, rate, bonus_periods, periods_per_year=2) if bonus_principal else 0.0
    total_payment = monthly_payment * request.term_months + bonus_payment * bonus_periods
    interest_total = total_payment - request.amount
    annual_payment = monthly_payment * 12 + bonus_payment * 2
    monthly_yen = yen(monthly_payment)
    reference_current = request.current_monthly_payment
    if reference_current is None and request.current_annual_rate is not None:
        reference_current = yen(
            amortized_payment(request.amount * (1 - request.bonus_ratio), request.current_annual_rate, request.term_months)
        )
    reference_reset = request.reset_monthly_payment
    if reference_reset is None and request.reset_annual_rate is not None:
        reference_reset = yen(
            amortized_payment(request.amount * (1 - request.bonus_ratio), request.reset_annual_rate, request.term_months)
        )

    return LoanPayment(
        product_id=product.id,
        provider=product.provider,
        name=product.name,
        annual_rate=round(rate, 4),
        rate_type=product.rate_type,
        monthly_payment=monthly_yen,
        bonus_payment=yen(bonus_payment) if bonus_principal else 0,
        total_payment=yen(total_payment),
        interest_total=yen(interest_total),
        burden_ratio_percent=annual_burden_ratio(annual_payment, request.annual_income),
        monthly_delta_vs_current=monthly_yen - reference_current if monthly_yen is not None and reference_current is not None else None,
        monthly_savings_vs_reset=reference_reset - monthly_yen if monthly_yen is not None and reference_reset is not None else None,
        eligible=eligible,
        reasons=reasons,
        highlights=_product_highlights(product),
        cautions=cautions,
        notes=product.notes,
        source_url=product.source_url,
    )


def effective_rate(product: LoanProduct, request: LoanCompareRequest) -> float | None:
    rate = product.representative_rate(request.membership, request.manual_rates)
    if rate is None:
        return None
    if product.long_term_threshold_months and product.long_term_rate_addition and request.term_months > product.long_term_threshold_months:
        rate += product.long_term_rate_addition
    return rate


def _product_highlights(product: LoanProduct) -> list[str]:
    highlights: list[str] = []
    if product.supports_web_contract:
        highlights.append("Web契約に対応")
    if product.supports_refinance:
        highlights.append("借換用途に対応")
    if product.supports_bonus:
        highlights.append("ボーナス併用返済に対応")
    if product.rate_type == RateType.FIXED:
        highlights.append("固定金利で返済計画を立てやすい")
    if product.upfront_fee_percent == 0:
        highlights.append("事務手数料率0%シナリオ")
    return highlights


def loan_sort_key(payment: LoanPayment, objective: Objective) -> tuple[float, float, float]:
    huge = 10**18
    if not payment.eligible:
        return (1, huge, huge)
    total = payment.total_payment if payment.total_payment is not None else huge
    monthly = payment.monthly_payment if payment.monthly_payment is not None else huge
    rate = payment.annual_rate if payment.annual_rate is not None else huge
    fixed_penalty = 0 if payment.rate_type.value == "fixed" else 1

    if objective == Objective.TOTAL_PAYMENT:
        return (0, total, monthly)
    if objective == Objective.MONTHLY_PAYMENT:
        return (0, monthly, total)
    if objective == Objective.FIXED_RATE:
        return (0, fixed_penalty, total)
    if objective == Objective.WEB_COMPLETE:
        web_penalty = 0 if "Web契約に対応" in payment.highlights else 1
        return (0, web_penalty, total)
    if objective == Objective.RECOMMENDATION:
        caution_penalty = len(payment.cautions) * 20_000
        reason_penalty = len(payment.reasons) * 100_000
        fixed_bonus = -20_000 if payment.rate_type.value == "fixed" else 0
        web_bonus = -10_000 if "Web契約に対応" in payment.highlights else 0
        return (
            0,
            total * 0.55
            + monthly * 12 * 0.25
            + rate * 10_000 * 0.2
            + caution_penalty
            + reason_penalty
            + fixed_bonus
            + web_bonus,
            total,
        )
    return (0, total * 0.7 + monthly * 12 * 0.2 + rate * 10_000 * 0.1, total)


def compare_loans(products: list[LoanProduct], request: LoanCompareRequest) -> LoanCompareResponse:
    filters_applied = describe_filters(request)
    matched_products: list[LoanProduct] = []
    filter_warnings: list[str] = []
    for product in products:
        matched, filter_reasons = product_matches_request(product, request)
        if matched:
            matched_products.append(product)
        elif request.include_ineligible:
            filter_warnings.extend(filter_reasons)

    all_results = [simulate_loan(product, request) for product in matched_products]
    for payment in all_results:
        if request.max_monthly_payment is not None and (
            payment.monthly_payment is None or payment.monthly_payment > request.max_monthly_payment
        ):
            payment.eligible = False
            payment.reasons.append(f"月返済上限を超過: {request.max_monthly_payment:,}円")
        if request.max_total_payment is not None and (
            payment.total_payment is None or payment.total_payment > request.max_total_payment
        ):
            payment.eligible = False
            payment.reasons.append(f"総支払額上限を超過: {request.max_total_payment:,}円")
        if request.max_interest_total is not None and (
            payment.interest_total is None or payment.interest_total > request.max_interest_total
        ):
            payment.eligible = False
            payment.reasons.append(f"利息総額上限を超過: {request.max_interest_total:,}円")
    visible = all_results if request.include_ineligible else [r for r in all_results if r.eligible]
    sorted_results = sorted(visible, key=lambda p: loan_sort_key(p, request.objective))
    ranked: list[LoanPayment] = []
    current_rank = 1
    for payment in sorted_results:
        if payment.eligible:
            payment.rank = current_rank
            payment.score = round(1000 / (loan_sort_key(payment, request.objective)[1] + 1) * 1_000_000, 4)
            current_rank += 1
        ranked.append(payment)

    best = next((item for item in ranked if item.eligible), None)
    enrich_rank_highlights(ranked, best)
    assumptions = [
        "返済方式は元利均等返済の概算です。",
        "ボーナス返済は年2回・6か月間隔の概算として計算します。",
        "手数料、印紙代、返済日差分、審査結果による個別金利は含みません。",
    ]
    warnings = []
    if request.bonus_ratio:
        warnings.append("ボーナス併用は金融機関ごとに上限・扱いが異なるため、正式見積で確認してください。")
    if any(p.annual_rate is None for p in ranked):
        warnings.append("一部商品は公式金利が地域・審査・店頭確認扱いのため、manual_ratesで補完してください。")
    if filters_applied and not matched_products:
        warnings.append("指定条件に一致する商品がありません。金融機関名や検索語を広げて再検索してください。")
    warnings.extend(sorted(set(filter_warnings))[:5])
    eligible_count = sum(1 for item in ranked if item.eligible)
    return LoanCompareResponse(
        best=best,
        results=ranked,
        assumptions=assumptions,
        warnings=sorted(set(warnings)),
        filters_applied=filters_applied,
        recommendation_summary=recommendation_summary(best, eligible_count),
        matched_count=len(matched_products),
        eligible_count=eligible_count,
        suggested_next_actions=suggested_next_actions(request, best),
    )


def describe_filters(request: LoanCompareRequest) -> list[str]:
    filters: list[str] = []
    if request.query:
        filters.append(f"検索語: {request.query}")
    if request.providers:
        filters.append(f"金融機関: {', '.join(request.providers)}")
    if request.product_ids:
        filters.append(f"商品ID: {', '.join(request.product_ids)}")
    if request.rate_type:
        filters.append(f"金利タイプ: {request.rate_type.value}")
    if request.max_monthly_payment:
        filters.append(f"月返済上限: {request.max_monthly_payment:,}円")
    if request.max_total_payment:
        filters.append(f"総支払額上限: {request.max_total_payment:,}円")
    if request.max_interest_total:
        filters.append(f"利息総額上限: {request.max_interest_total:,}円")
    if request.require_web_contract is not None:
        filters.append(f"Web完結: {request.require_web_contract}")
    if request.require_refinance is not None:
        filters.append(f"借換対応: {request.require_refinance}")
    if request.require_bonus_support is not None:
        filters.append(f"ボーナス対応: {request.require_bonus_support}")
    return filters


def enrich_rank_highlights(ranked: list[LoanPayment], best: LoanPayment | None) -> None:
    eligible = [item for item in ranked if item.eligible]
    if not eligible:
        return
    min_monthly = min(item.monthly_payment for item in eligible if item.monthly_payment is not None)
    min_total = min(item.total_payment for item in eligible if item.total_payment is not None)
    min_interest = min(item.interest_total for item in eligible if item.interest_total is not None)
    for item in eligible:
        if item.monthly_payment == min_monthly:
            item.highlights.append("月々返済が最小候補")
        if item.total_payment == min_total:
            item.highlights.append("総支払額が最小候補")
        if item.interest_total == min_interest:
            item.highlights.append("利息総額が最小候補")
        if item.monthly_savings_vs_reset and item.monthly_savings_vs_reset > 0:
            item.highlights.append(f"更新後想定より月{item.monthly_savings_vs_reset:,}円抑制")
        if best and item.product_id == best.product_id:
            item.highlights.append("今回条件での最有力候補")


def recommendation_summary(best: LoanPayment | None, eligible_count: int) -> str | None:
    if best is None:
        return "条件を満たす候補がありません。検索語、金融機関、返済額上限、用途を緩めて再比較してください。"
    qualifier = "条件や注意点を確認したうえで、" if best.cautions else ""
    return (
        f"{eligible_count}件の候補から、{qualifier}{best.provider}「{best.name}」を最有力候補として返しました。"
        "金利・返済額・対応用途・Web対応を総合して比較しています。"
    )


def suggested_next_actions(request: LoanCompareRequest, best: LoanPayment | None) -> list[str]:
    actions = [
        "公式ページで最新金利、保証料、手数料、申込条件を確認する",
        "同じ条件で返済期間を短縮・延長したシナリオも比較する",
    ]
    if best and best.rate_type == RateType.VARIABLE:
        actions.append("変動金利上昇時の返済額を別シナリオで確認する")
    if request.purpose == LoanPurpose.HOME_REFINANCE:
        actions.append("借換諸費用を含めた回収期間と、団信の保障差を確認する")
        actions.append("物件評価、残債、健康状態、勤務先属性で審査条件が変わるため仮審査を複数行で比較する")
    if not request.manual_rates and request.purpose != LoanPurpose.HOME_REFINANCE:
        actions.append("金利手入力枠の商品は manual_rates に公式金利を入れて再比較する")
    return actions


@dataclass(frozen=True)
class NormalizedCriterion:
    criterion: Criterion
    min_value: float | None = None
    max_value: float | None = None


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _violates_constraints(metrics: dict[str, Any], constraints: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for key, expected in constraints.items():
        actual = metrics.get(key)
        if isinstance(expected, dict):
            if "min" in expected and (actual is None or _to_number(actual) is None or _to_number(actual) < expected["min"]):
                reasons.append(f"{key} が下限未満")
            if "max" in expected and (actual is None or _to_number(actual) is None or _to_number(actual) > expected["max"]):
                reasons.append(f"{key} が上限超過")
            if "eq" in expected and actual != expected["eq"]:
                reasons.append(f"{key} が条件不一致")
        elif actual != expected:
            reasons.append(f"{key} が条件不一致")
    return reasons


def compare_generic(request: GenericCompareRequest) -> GenericCompareResponse:
    warnings: list[str] = []
    numeric_by_key: dict[str, list[float]] = {}
    for criterion in request.criteria:
        values = [_to_number(option.metrics.get(criterion.key)) for option in request.options]
        numeric_values = [value for value in values if value is not None]
        if numeric_values:
            numeric_by_key[criterion.key] = numeric_values

    ranked: list[RankedOption] = []
    for option in request.options:
        reasons = _violates_constraints(option.metrics, request.constraints)
        score = 0.0
        total_weight = 0.0
        for criterion in request.criteria:
            if criterion.direction == Direction.INFO or criterion.weight == 0:
                continue
            value = option.metrics.get(criterion.key)
            if criterion.required and value in (None, ""):
                reasons.append(f"必須項目なし: {criterion.label}")
                continue
            component = 0.0
            if criterion.direction == Direction.MATCH:
                component = 1.0 if value == criterion.ideal else 0.0
            else:
                num = _to_number(value)
                nums = numeric_by_key.get(criterion.key, [])
                if num is None or not nums:
                    warnings.append(f"{option.name}: {criterion.label} は数値化できないためスコア対象外")
                    continue
                min_v, max_v = min(nums), max(nums)
                if abs(max_v - min_v) < 1e-12:
                    component = 1.0
                elif criterion.direction == Direction.MIN:
                    component = (max_v - num) / (max_v - min_v)
                else:
                    component = (num - min_v) / (max_v - min_v)
            score += component * criterion.weight
            total_weight += criterion.weight
        normalized = round(score / total_weight * 100, 4) if total_weight else 0.0
        ranked.append(
            RankedOption(
                rank=0,
                id=option.id,
                name=option.name,
                provider=option.provider,
                score=normalized,
                eligible=not reasons,
                reasons=reasons,
                metrics=option.metrics,
                notes=option.notes,
                url=option.url,
            )
        )

    ranked.sort(key=lambda item: (not item.eligible, -item.score))
    for idx, item in enumerate(ranked[: request.top_n], start=1):
        item.rank = idx if item.eligible else 0
    visible = ranked[: request.top_n]
    best = next((item for item in visible if item.eligible), None)
    return GenericCompareResponse(best=best, ranked=visible, warnings=sorted(set(warnings)))
