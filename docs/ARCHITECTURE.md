# Architecture

## Layers

```text
AI agents / Web UI / CLI
        |
        | MCP stdio or REST
        v
FastAPI / MCP adapters
        |
        v
Domain plugin schema
        |
        v
Generic comparison engine
        |
        v
JSON product/rule/source data
```

## Why this shape

- MCP gives agent interoperability.
- FastAPI gives stable public and internal HTTP APIs.
- `AGENTS.md`, `SKILL.md`, `GEMINI.md`, `.cursor/rules`, and Claude commands let each agent read the same working rules in its native style.
- Domain data stays in JSON so non-engineers and agents can update products without touching algorithm code.

## URL convention

Public production target:

```text
https://mcp.solo-map.app/v1
```

Route families:

```text
GET  /.well-known/solo-map-plugins.json
GET  /health
GET  /v1/rules
GET  /v1/plugins
GET  /v1/plugins/{plugin_id}
POST /v1/plugins/{plugin_id}/compare
POST /v1/loan/compare
POST /v1/compare/generic
```

## Plugin contract

Every plugin should define:

- manifest
- input schema
- output schema
- eligibility rules
- scoring criteria
- source URL handling
- assumptions and warnings
- tests
- agent adapter notes
