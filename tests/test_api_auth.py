from fastapi.testclient import TestClient

from comparison_engine.api import create_app


def test_compare_requires_configured_token(monkeypatch):
    monkeypatch.delenv("SOLO_MAP_API_TOKEN", raising=False)
    client = TestClient(create_app())
    response = client.post(
        "/v1/loan/compare",
        json={"amount": 1000000, "term_months": 120, "purpose": "multi"},
    )
    assert response.status_code == 503


def test_compare_rejects_invalid_token(monkeypatch):
    monkeypatch.setenv("SOLO_MAP_API_TOKEN", "test-token-123456789012345")
    client = TestClient(create_app())
    response = client.post(
        "/v1/loan/compare",
        json={"amount": 1000000, "term_months": 120, "purpose": "multi"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401


def test_compare_accepts_valid_token(monkeypatch):
    token = "test-token-123456789012345"
    monkeypatch.setenv("SOLO_MAP_API_TOKEN", token)
    client = TestClient(create_app())
    response = client.post(
        "/v1/loan/compare",
        json={"amount": 1000000, "term_months": 120, "purpose": "multi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["best"] is not None


def test_root_page_and_security_headers(monkeypatch):
    monkeypatch.setenv("SOLO_MAP_API_TOKEN", "test-token-123456789012345")
    client = TestClient(create_app())
    response = client.get("/", headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 200
    assert "Solo Map MCP" in response.text
    assert "/assets/solomap-logo.png" in response.text
    assert "PayPay銀行" in response.text
    assert "claude mcp add" in response.text
    assert "codex mcp add" in response.text
    assert "Cursor" in response.text
    assert "/v1" in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert "script-src" not in response.headers["content-security-policy"]


def test_docs_page_allows_swagger_assets(monkeypatch):
    monkeypatch.setenv("SOLO_MAP_API_TOKEN", "test-token-123456789012345")
    client = TestClient(create_app())
    response = client.get("/v1/docs", headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 200
    assert "Swagger UI" in response.text
    csp = response.headers["content-security-policy"]
    assert "script-src" in csp
    assert "style-src" in csp
    assert "https://cdn.jsdelivr.net" in csp
    assert "connect-src 'self'" in csp
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


def test_v1_index(monkeypatch):
    monkeypatch.setenv("SOLO_MAP_API_TOKEN", "test-token-123456789012345")
    client = TestClient(create_app())
    response = client.get("/v1")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["api_base"] == "/v1"
    assert "/v1/docs" in body["public_endpoints"]
    assert "/v1/loan/compare" in body["protected_endpoints"]


def test_logo_asset_is_served(monkeypatch):
    monkeypatch.setenv("SOLO_MAP_API_TOKEN", "test-token-123456789012345")
    client = TestClient(create_app())
    response = client.get("/assets/solomap-logo.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_rejects_large_request_body(monkeypatch):
    token = "test-token-123456789012345"
    monkeypatch.setenv("SOLO_MAP_API_TOKEN", token)
    monkeypatch.setenv("SOLO_MAP_MAX_BODY_BYTES", "1024")
    client = TestClient(create_app())
    response = client.post(
        "/v1/loan/compare",
        content=b"{" + b'"x":' + b'"' + (b"a" * 2048) + b'"}',
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert response.status_code == 413
