---
name: comparison-engine
description: Build, extend, and use reusable comparison plugins for loans, products, SaaS, vendors, tools, grants, insurance, or other ranked decision workflows. Trigger when the task involves comparing options, scoring requirements, repayment simulations, or agent-callable comparison APIs.
---

# Comparison Engine Skill

Use this skill when a user asks to compare choices and produce the best option under explicit or inferred requirements.

## Workflow

1. Identify the domain: loan, SaaS, product, vendor, subsidy, insurance, infrastructure, or generic.
2. Extract requirements into structured inputs.
3. Define eligibility constraints before ranking.
4. Define weighted criteria with direction: lower is better, higher is better, match, or information-only.
5. Run the engine through FastAPI or MCP.
6. Return:
   - best option
   - ranked comparison
   - assumptions
   - warnings
   - eligibility failures
   - source URLs when known
7. Never hide uncertainty. State when a rate, price, condition, or source is stale or manually supplied.

## Finance personas

Use these extraction patterns when the user gives a natural-language finance consultation.

### Housing refinance borrower

Trigger phrases: `住宅ローン`, `借換`, `借り換え`, `見直し時期`, `金利が上がる`, `月返済を抑えたい`.

Map to `LoanCompareRequest`:

- `purpose`: `home_refinance`
- `amount`: remaining principal or planned refinance amount
- `term_months`: infer from the current payment if the user says "same term"; for 2,600万円, 0.9%, 7万円弱 and 3.25%, 9万円弱, use about 480 months unless the user gives a remaining term
- `current_annual_rate`: current mortgage rate
- `reset_annual_rate`: rate after review/reset
- `current_monthly_payment`: current monthly payment when stated
- `reset_monthly_payment`: expected payment after rate reset when stated
- `max_monthly_payment`: the user's upper monthly-payment target
- `objective`: `recommendation`
- `query`: `住宅ローン 借換`

Return both candidates and caveats. Always mention that mortgage refinance decisions need fee recovery, collateral appraisal, employment/health screening, and group-credit-life insurance comparison.

### Condition-sensitive borrower

When a product depends on mobile/utility/bank-account/WEB-contract conditions, keep it in the ranking but call out the condition. If the user has not confirmed the condition, present it as "条件が合えば有力" rather than a guaranteed best option.

### Stability-first borrower

If the user says `固定`, `安心`, `今後の上昇が怖い`, or `返済額を固定したい`, increase fixed-rate and long-term fixed scenarios in the explanation even when monthly payment is higher.

## Local commands

```bash
pytest
uvicorn comparison_engine.api:app --reload
python -m comparison_engine.mcp_server
uv --directory <local-clone-path> run solo-compare-mcp
```

## FastAPI endpoints

- `POST /v1/loan/compare`
- `POST /v1/compare/generic`
- `POST /v1/plugins/{plugin_id}/compare`
- `GET /v1/plugins`
- `GET /.well-known/solo-map-plugins.json`

## MCP tools

- `list_comparison_plugins`
- `compare_loan_repayment`
- `compare_generic_options`

## Safety

For finance, legal, medical, employment, or regulated decisions, treat the output as planning support. Do not present it as formal approval, legal advice, investment advice, or guaranteed eligibility.
