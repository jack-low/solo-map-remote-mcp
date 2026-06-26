# Deployment Guide

## Local

```bash
uvicorn comparison_engine.api:app --host 0.0.0.0 --port 8000
```

## Docker

```bash
docker compose up --build
```

## Nginx reverse proxy example

```nginx
server {
    server_name mcp.solo-map.app;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## DNS

Point `mcp.solo-map.app` to the server IP with an A/AAAA record.

## TLS

Use Certbot or your preferred TLS automation:

```bash
sudo certbot --nginx -d mcp.solo-map.app
```

## Production hardening

- Enforce `SOLO_MAP_API_TOKEN`; comparison endpoints reject requests when it is missing or set to `change-me`.
- Set `SOLO_MAP_ALLOWED_ORIGINS` to the exact public origins that may call the browser API.
- Keep `SOLO_MAP_MAX_BODY_BYTES` small enough for the expected payload size.
- Keep remote MCP deny-by-default.
- Pin dependencies for production releases.
- Add rate limiting.
- Log request ids, plugin ids, and tool names, but never raw private financial data unless explicitly required and protected.
