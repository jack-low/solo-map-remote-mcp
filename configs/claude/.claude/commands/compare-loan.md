---
description: Compare loan repayment options using the Solo Map comparison engine.
allowed-tools: Read, Bash
---

Use the Solo Map comparison engine to compare loan repayment plans.

Steps:
1. Extract amount, term_months, annual_income, purpose, membership, bonus_ratio, objective, manual_rates, and refinance context from the user request.
2. Prefer the MCP tool `compare_loan_repayment` when configured.
3. If MCP is unavailable, call the local API endpoint `POST /v1/loan/compare`.
4. For housing refinance, map the request to `purpose=home_refinance` and include current/reset rates and monthly payments when stated.
5. Return best option, ranked table, monthly deltas, assumptions, warnings, and eligibility failures.

Claude Code setup:

```bash
git clone https://github.com/jack-low/solo-map-remote-mcp.git
claude mcp add --scope user --transport stdio solo-map-comparison-engine \
  -- uv --directory <local-clone-path> run solo-compare-mcp
claude mcp list
```
