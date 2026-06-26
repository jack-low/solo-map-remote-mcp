# Agent Operating Guide

This repository implements a reusable comparison engine.

## Mission
Build plugins that accept structured requirements, rank options, expose assumptions, and return decision-ready comparisons for humans and AI agents.

## Rules
- Keep the scoring engine domain-neutral. Domain-specific rules belong in plugin data, schema, or adapter files.
- Always return `assumptions`, `warnings`, `source_url`, and eligibility reasons when possible.
- Do not hardcode secrets, official rates, or private customer data in source code.
- Treat financial output as an approximate simulation, not formal financial advice.
- Add or update tests whenever product data, scoring rules, API schemas, or MCP tools change.
- Prefer simple Pydantic schemas over clever dynamic schemas.

## Local commands
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
pytest
uvicorn comparison_engine.api:app --reload
python -m comparison_engine.mcp_server
```

## Public route convention
Use these route families under `https://mcp.solo-map.app/v1`:

- `/v1/plugins` - list available plugins
- `/v1/plugins/{plugin_id}` - plugin manifest
- `/v1/plugins/{plugin_id}/compare` - canonical comparison endpoint
- `/v1/compare/generic` - generic weighted comparison
- `/v1/loan/compare` - loan comparison plugin
- `/.well-known/solo-map-plugins.json` - discovery manifest
