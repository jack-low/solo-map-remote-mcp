# Solo Map Comparison Engine Context

This project provides a generic comparison engine with FastAPI and MCP adapters.

When a user asks for repayment simulation, product comparison, SaaS/vendor selection, or ranked decision support:

1. Convert the request into structured constraints and weighted criteria.
2. Use MCP tool `compare_loan_repayment` for loans or `compare_generic_options` for generic comparisons.
3. If MCP is not available, use the REST API under `/v1`.
4. Always include assumptions, warnings, and eligibility reasons.
5. Do not present approximate financial simulations as official approval or advice.

## MCP setup

Use this stdio MCP server configuration when Gemini CLI supports MCP:

First clone the repository. Use the local clone path, not the GitHub URL, for `--directory`.

```bash
git clone https://github.com/jack-low/solo-map-remote-mcp.git
```

```yaml
name: solo-map-comparison-engine
transport: stdio
command: uv
args:
  - --directory
  - <local-clone-path>
  - run
  - solo-compare-mcp
```

If MCP is not available, use the authenticated REST API at `https://mcp.solo-map.app/v1`.
