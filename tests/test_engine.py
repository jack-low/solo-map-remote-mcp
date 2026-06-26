from comparison_engine.data_loader import load_loan_products
from comparison_engine.engine import amortized_payment, compare_generic, compare_loans
from comparison_engine.models import GenericCompareRequest, LoanCompareRequest


def test_amortized_payment_positive():
    payment = amortized_payment(1_000_000, 1.8, 120)
    assert 9000 < payment < 9300


def test_compare_loans_hokuoh_can_rank_first_for_member():
    request = LoanCompareRequest(amount=1_000_000, term_months=120, purpose="multi", membership=True)
    response = compare_loans(load_loan_products(), request)
    assert response.best is not None
    assert response.best.product_id == "hokuoh-katikoti-purpose"
    assert response.best.eligible is True


def test_compare_loans_reject_auto_for_hokuoh():
    request = LoanCompareRequest(amount=1_000_000, term_months=60, purpose="auto", membership=True)
    response = compare_loans(load_loan_products(), request)
    hokuoh = [r for r in response.results if r.product_id == "hokuoh-katikoti-purpose"][0]
    assert hokuoh.eligible is False
    assert any("用途" in reason for reason in hokuoh.reasons)


def test_compare_loans_filters_by_fuzzy_provider():
    request = LoanCompareRequest(
        amount=1_000_000,
        term_months=120,
        purpose="multi",
        providers=["北洋"],
    )
    response = compare_loans(load_loan_products(), request)
    assert response.matched_count == 2
    assert all(result.provider == "北洋銀行" for result in response.results)
    assert "金融機関: 北洋" in response.filters_applied


def test_compare_loans_filters_by_query_and_web_contract():
    request = LoanCompareRequest(
        amount=1_000_000,
        term_months=120,
        purpose="multi",
        query="web",
        require_web_contract=True,
        include_ineligible=False,
    )
    response = compare_loans(load_loan_products(), request)
    assert response.best is not None
    assert all("Web契約に対応" in result.highlights for result in response.results)
    assert response.eligible_count == len(response.results)


def test_compare_loans_monthly_cap_marks_ineligible():
    request = LoanCompareRequest(
        amount=1_000_000,
        term_months=12,
        purpose="multi",
        max_monthly_payment=10_000,
    )
    response = compare_loans(load_loan_products(), request)
    assert response.best is None
    assert response.eligible_count == 0
    assert any("月返済上限" in reason for result in response.results for reason in result.reasons)


def test_housing_refinance_persona_gets_mortgage_candidates():
    request = LoanCompareRequest(
        amount=26_000_000,
        term_months=480,
        purpose="home_refinance",
        objective="recommendation",
        query="住宅ローン 借換",
        max_monthly_payment=90_000,
        current_annual_rate=0.9,
        reset_annual_rate=3.25,
        current_monthly_payment=70_000,
        reset_monthly_payment=90_000,
        include_ineligible=False,
    )
    response = compare_loans(load_loan_products(), request)
    assert response.best is not None
    assert response.best.monthly_payment is not None
    assert response.best.monthly_payment < 90_000
    assert response.best.monthly_savings_vs_reset is not None
    assert response.best.monthly_savings_vs_reset > 0
    assert response.eligible_count >= 3
    assert any("借換諸費用" in action for action in response.suggested_next_actions)


def test_generic_compare_constraints():
    request = GenericCompareRequest.model_validate(
        {
            "criteria": [
                {"key": "price", "label": "価格", "direction": "min", "weight": 2},
                {"key": "api", "label": "API", "direction": "match", "ideal": True, "required": True},
            ],
            "constraints": {"api": True},
            "options": [
                {"id": "a", "name": "A", "metrics": {"price": 100, "api": True}},
                {"id": "b", "name": "B", "metrics": {"price": 50, "api": False}},
            ],
        }
    )
    response = compare_generic(request)
    assert response.best is not None
    assert response.best.id == "a"
    assert response.ranked[1].eligible is False
