# Codex guidance for Solo Map Comparison Engine

- Use this repository as an OSS-grade plugin and MCP foundation.
- Keep reusable logic in `src/comparison_engine/engine.py`.
- Keep domain data in `data/*.json`.
- Add new domains as plugins, not one-off scripts.
- Run `pytest` before proposing changes.
- For agent distribution, update `skills/comparison-engine/SKILL.md`, `.mcp.json`, and README together.
