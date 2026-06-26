from __future__ import annotations

import os
from pathlib import Path
from secrets import compare_digest
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__
from .data_loader import load_loan_products, load_plugin_manifest
from .engine import compare_generic, compare_loans, simulate_loan
from .models import GenericCompareRequest, LoanCompareRequest, LoanCompareResponse

API_PREFIX = "/v1"
DEFAULT_MAX_BODY_BYTES = 64 * 1024
STATIC_DIR = Path(__file__).resolve().parent / "static"


def allowed_origins() -> list[str]:
    raw = os.getenv("SOLO_MAP_ALLOWED_ORIGINS", "https://mcp.solo-map.app")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def max_body_bytes() -> int:
    raw = os.getenv("SOLO_MAP_MAX_BODY_BYTES")
    if not raw:
        return DEFAULT_MAX_BODY_BYTES
    try:
        return max(1024, int(raw))
    except ValueError:
        return DEFAULT_MAX_BODY_BYTES


def create_app() -> FastAPI:
    app = FastAPI(
        title="Solo Map Comparison Engine",
        description="Generic comparison engine for loans, tools, products, grants, vendors, and other decision workflows.",
        version=__version__,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @app.middleware("http")
    async def security_middleware(request: Request, call_next: Any) -> Response:
        content_length = request.headers.get("content-length")
        try:
            if content_length and int(content_length) > max_body_bytes():
                return Response("Request body too large", status_code=413)
        except ValueError:
            return Response("Invalid Content-Length", status_code=400)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; "
            "base-uri 'none'; frame-ancestors 'none'"
        )
        forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
        if request.url.scheme == "https" or forwarded_proto == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def require_token(authorization: str | None = Header(default=None)) -> None:
        expected = os.getenv("SOLO_MAP_API_TOKEN")
        if not expected or expected == "change-me":
            raise HTTPException(status_code=503, detail="API token is not configured")
        if not authorization or not compare_digest(authorization, f"Bearer {expected}"):
            raise HTTPException(status_code=401, detail="Invalid API token")

    @app.get("/", response_class=HTMLResponse)
    def root() -> str:
        return """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Solo Map MCP</title>
  <link rel="icon" type="image/png" href="/assets/solomap-mark.png">
  <style>
    :root {
      --paper: #fafaf8;
      --wash: #f0eee7;
      --ink: #111827;
      --muted: #5f6675;
      --line: #e1e5ee;
      --blue: #1558f0;
      --cyan: #10bfd0;
      --green: #0f6b52;
      --panel: #ffffff;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      color: var(--ink);
      background: var(--wash);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    a { color: inherit; }
    .shell {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      background: var(--paper);
      box-shadow: 0 24px 80px rgba(17, 24, 39, .08);
      min-height: 100vh;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      padding: 22px 48px;
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      z-index: 10;
      background: rgba(250, 250, 248, .94);
      backdrop-filter: blur(12px);
    }
    .brand {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
      font-weight: 750;
      font-size: 1.08rem;
    }
    .brand img { width: 44px; height: 44px; object-fit: contain; }
    nav { display: flex; align-items: center; gap: 18px; font-size: .93rem; font-weight: 650; }
    nav a { text-decoration: none; color: #243044; }
    .nav-cta {
      border: 1px solid #cfd7e6;
      border-radius: 999px;
      padding: 10px 16px;
      background: #fff;
    }
    .hero {
      min-height: 76vh;
      padding: 70px 48px 34px;
      display: grid;
      align-content: center;
      gap: 28px;
      border-bottom: 1px solid var(--line);
    }
    .hero-logo {
      width: min(760px, 100%);
      height: auto;
      display: block;
      margin: 0 auto 12px;
    }
    .eyebrow {
      color: var(--green);
      font-size: .78rem;
      font-weight: 800;
      letter-spacing: .14em;
      text-transform: uppercase;
      text-align: center;
    }
    h1 {
      margin: 0 auto;
      max-width: 780px;
      text-align: center;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 4.6rem;
      line-height: 1.02;
      font-weight: 500;
      letter-spacing: 0;
    }
    .lead {
      max-width: 760px;
      margin: 0 auto;
      color: var(--muted);
      text-align: center;
      font-size: 1.14rem;
      line-height: 1.85;
    }
    .hero-actions { display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; }
    .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 48px;
      padding: 0 22px;
      border-radius: 999px;
      text-decoration: none;
      font-weight: 750;
      border: 1px solid transparent;
    }
    .button.primary { background: var(--ink); color: #fff; }
    .button.secondary { background: #fff; border-color: #ccd5e3; color: #1c2b44; }
    .status-strip {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      border-top: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      background: #fff;
    }
    .status-item { padding: 22px 28px; border-right: 1px solid var(--line); }
    .status-item:last-child { border-right: 0; }
    .label {
      margin-bottom: 8px;
      color: #7a8291;
      font-size: .72rem;
      font-weight: 800;
      letter-spacing: .12em;
      text-transform: uppercase;
    }
    .value { font-size: 1.08rem; font-weight: 760; }
    section { padding: 70px 48px; border-bottom: 1px solid var(--line); }
    .section-head {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 28px;
      margin-bottom: 28px;
    }
    h2 {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 2.45rem;
      font-weight: 500;
      line-height: 1.12;
      letter-spacing: 0;
    }
    .section-copy { margin: 0; color: var(--muted); line-height: 1.75; max-width: 620px; }
    .feature-grid, .agent-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
    }
    .card h3 { margin: 0 0 10px; font-size: 1.08rem; line-height: 1.35; }
    .card p { margin: 0; color: var(--muted); line-height: 1.7; }
    .demo {
      display: grid;
      grid-template-columns: 1.05fr .95fr;
      gap: 18px;
      align-items: stretch;
    }
    .demo-result {
      background: #101827;
      color: #edf7ff;
      border-radius: 8px;
      padding: 26px;
    }
    .metric {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      padding: 14px 0;
      border-bottom: 1px solid rgba(255,255,255,.14);
    }
    .metric span:first-child { color: #aebbd3; }
    .metric strong { font-size: 1.08rem; }
    pre {
      margin: 0;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
      border: 1px solid #1f2c42;
      border-radius: 8px;
      padding: 18px;
      background: #0d1524;
      color: #dbeafe;
      font-size: .88rem;
      line-height: 1.65;
    }
    code { font-family: "Cascadia Mono", "SFMono-Regular", Consolas, monospace; }
    .agent-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .endpoint-list { border-top: 1px solid var(--line); }
    .endpoint {
      display: grid;
      grid-template-columns: 92px 220px 1fr;
      gap: 18px;
      align-items: center;
      padding: 18px 0;
      border-bottom: 1px solid var(--line);
      text-decoration: none;
    }
    .method {
      width: fit-content;
      color: var(--green);
      background: #e8f3ef;
      border: 1px solid #c7e0d8;
      border-radius: 6px;
      padding: 7px 10px;
      font-size: .75rem;
      font-weight: 800;
      letter-spacing: .06em;
    }
    .path { font-family: "Cascadia Mono", "SFMono-Regular", Consolas, monospace; font-weight: 700; }
    .note {
      background: #fff7ea;
      border: 1px solid #f0dfbd;
      color: #6d5b36;
      border-radius: 8px;
      padding: 20px 22px;
      line-height: 1.75;
    }
    footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 28px 48px;
      color: #737b8a;
      font-size: .92rem;
    }
    @media (max-width: 820px) {
      .shell { width: 100%; }
      header { padding: 18px 22px; position: static; }
      nav { display: none; }
      .hero { min-height: auto; padding: 48px 22px 30px; }
      h1 { font-size: 3rem; }
      section { padding: 46px 22px; }
      .status-strip, .feature-grid, .agent-grid, .demo { grid-template-columns: 1fr; }
      .status-item { border-right: 0; border-bottom: 1px solid var(--line); }
      .section-head { display: block; }
      h2 { font-size: 2rem; margin-bottom: 14px; }
      .endpoint { grid-template-columns: 1fr; gap: 8px; }
      footer { padding: 24px 22px; display: block; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <a class="brand" href="/" aria-label="Solo Map MCP">
        <img src="/assets/solomap-mark.png" alt="">
        <span>Solo Map MCP</span>
      </a>
      <nav aria-label="Primary">
        <a href="#features">機能</a>
        <a href="#agents">接続</a>
        <a href="#endpoints">API</a>
        <a class="nav-cta" href="/v1/docs">Docs</a>
      </nav>
    </header>

    <main>
      <section class="hero" aria-labelledby="hero-title">
        <img class="hero-logo" src="/assets/solomap-logo.png" alt="Solo Map MCP">
        <div class="eyebrow">Live Comparison Engine / Updated 2026-06-26</div>
        <h1 id="hero-title">条件から、最適な選択肢を。</h1>
        <p class="lead">金融機関、住宅ローン借換、商品、サービス、助成制度を横断比較し、候補理由・注意点・次の確認事項まで返すAI接続向け提案エンジンです。</p>
        <div class="hero-actions">
          <a class="button primary" href="/v1/docs">APIドキュメントを見る</a>
          <a class="button secondary" href="#agents">エージェントに接続する</a>
        </div>
      </section>

      <div class="status-strip" aria-label="Current status">
        <div class="status-item"><div class="label">Endpoint</div><div class="value">mcp.solo-map.app</div></div>
        <div class="status-item"><div class="label">Runtime</div><div class="value">FastAPI + stdio MCP</div></div>
        <div class="status-item"><div class="label">Latest Scenario</div><div class="value">住宅ローン借換</div></div>
        <div class="status-item"><div class="label">Auth</div><div class="value">Bearer token required</div></div>
      </div>

      <section id="features">
        <div class="section-head">
          <h2>提案に必要な比較を、構造化する。</h2>
          <p class="section-copy">自然な相談文を、条件・制約・目的に分解して比較します。結果は人が読める要約と、AIが扱いやすいJSONの両方で返せます。</p>
        </div>
        <div class="feature-grid">
          <article class="card"><h3>住宅ローン借換</h3><p>現在金利、見直し後金利、月返済上限、返済期間、Web完結、団信や優遇条件を含めて候補を比較します。</p></article>
          <article class="card"><h3>商品・サービス提案</h3><p>価格、機能、リスク、必須条件など任意の指標を重み付けし、紹介や提案に使えるランキングを生成します。</p></article>
          <article class="card"><h3>安全な公開運用</h3><p>比較実行APIはBearerトークン必須です。公開ページ、マニフェスト、導入手順に秘密情報は含めません。</p></article>
        </div>
      </section>

      <section id="demo">
        <div class="section-head">
          <h2>現在のデモ試算。</h2>
          <p class="section-copy">「2600万円の住宅ローン借換、現在0.9%、見直し後3.25%、月9万円弱を抑えたい」という相談を想定した最新データセットでのサンプルです。</p>
        </div>
        <div class="demo">
          <div class="card">
            <h3>相談内容の構造化</h3>
            <p>purpose=home_refinance、amount=26,000,000、term_months=480、reset_monthly_payment=90,000、objective=recommendation として比較します。返済期間は相談文から推定しているため、正式には残期間の確認が必要です。</p>
          </div>
          <div class="demo-result" aria-label="Sample result">
            <div class="metric"><span>候補一致</span><strong>7件</strong></div>
            <div class="metric"><span>条件適合</span><strong>5件</strong></div>
            <div class="metric"><span>最有力候補</span><strong>PayPay銀行</strong></div>
            <div class="metric"><span>月返済概算</span><strong>65,130円</strong></div>
            <div class="metric"><span>見直し後との差</span><strong>月24,870円抑制</strong></div>
          </div>
        </div>
      </section>

      <section id="agents">
        <div class="section-head">
          <h2>各エージェントに追加する。</h2>
          <p class="section-copy">GitHubリポジトリをcloneし、<code>&lt;local-clone-path&gt;</code> をclone後のローカル絶対パスに置き換えてください。GitHub URLをそのまま <code>uv --directory</code> には渡しません。</p>
        </div>
        <pre><code>git clone https://github.com/jack-low/solo-map-remote-mcp.git
cd solo-map-remote-mcp</code></pre>
        <div class="agent-grid">
          <article class="card"><h3>Claude Code</h3><pre><code>claude mcp add --scope user --transport stdio solo-map-comparison-engine -- uv --directory &lt;local-clone-path&gt; run solo-compare-mcp
claude mcp list</code></pre></article>
          <article class="card"><h3>Codex</h3><pre><code>codex mcp add solo-map-comparison-engine -- uv --directory &lt;local-clone-path&gt; run solo-compare-mcp
codex mcp list</code></pre></article>
          <article class="card"><h3>Cursor</h3><pre><code>{
  "mcpServers": {
    "solo-map-comparison-engine": {
      "command": "uv",
      "args": ["--directory", "&lt;local-clone-path&gt;", "run", "solo-compare-mcp"]
    }
  }
}</code></pre></article>
          <article class="card"><h3>Gemini CLI / Hermes</h3><pre><code>name: solo-map-comparison-engine
transport: stdio
command: uv
args: ["--directory", "&lt;local-clone-path&gt;", "run", "solo-compare-mcp"]</code></pre></article>
        </div>
      </section>

      <section>
        <div class="section-head">
          <h2>AIに接続を任せる。</h2>
          <p class="section-copy">Claude Code、Codex、CursorなどのAIエージェントに、そのまま貼り付けるための依頼文です。</p>
        </div>
        <pre><code>https://github.com/jack-low/solo-map-remote-mcp をcloneし、clone後のローカル絶対パスを &lt;local-clone-path&gt; として、このMCPを追加してください。名前は solo-map-comparison-engine、transport は stdio、command は uv、args は ["--directory", "&lt;local-clone-path&gt;", "run", "solo-compare-mcp"] です。住宅ローン借換や商品比較では compare_loan_repayment / compare_generic_options を使い、前提・注意点・候補理由を必ず返してください。</code></pre>
      </section>

      <section id="endpoints">
        <div class="section-head">
          <h2>公開エンドポイント。</h2>
          <p class="section-copy">GET系は公開、比較実行APIはBearerトークン必須です。</p>
        </div>
        <div class="endpoint-list">
          <a class="endpoint" href="/health"><span class="method">GET</span><span class="path">/health</span><span>稼働状態の確認</span></a>
          <a class="endpoint" href="/v1"><span class="method">GET</span><span class="path">/v1</span><span>API接続情報</span></a>
          <a class="endpoint" href="/v1/plugins"><span class="method">GET</span><span class="path">/v1/plugins</span><span>利用可能な比較プラグイン</span></a>
          <a class="endpoint" href="/v1/openapi.json"><span class="method">GET</span><span class="path">/v1/openapi.json</span><span>OpenAPI定義</span></a>
          <a class="endpoint" href="/v1/docs"><span class="method">GET</span><span class="path">/v1/docs</span><span>APIドキュメント</span></a>
        </div>
      </section>

      <section>
        <div class="note">返済額は概算です。審査結果、最新金利、保証料、手数料、契約条件は必ず各金融機関の公式情報を確認してください。比較結果は提案であり、契約・勧誘・金融助言ではありません。</div>
      </section>
    </main>

    <footer>
      <span>Solo Map MCP</span>
      <span>Comparison outputs are planning support, not formal approval.</span>
    </footer>
  </div>
</body>
</html>"""

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "service": "solo-map-comparison-engine", "version": __version__}

    @app.get("/.well-known/solo-map-plugins.json")
    def well_known_plugins() -> dict[str, Any]:
        manifest = load_plugin_manifest()
        return manifest.model_dump()

    @app.get(API_PREFIX)
    def api_index() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "solo-map-comparison-engine",
            "version": __version__,
            "api_base": API_PREFIX,
            "public_endpoints": [
                "/health",
                f"{API_PREFIX}",
                f"{API_PREFIX}/rules",
                f"{API_PREFIX}/plugins",
                f"{API_PREFIX}/docs",
                f"{API_PREFIX}/openapi.json",
            ],
            "protected_endpoints": [
                f"{API_PREFIX}/loan/compare",
                f"{API_PREFIX}/loan/simulate",
                f"{API_PREFIX}/compare/generic",
                f"{API_PREFIX}/plugins/{{plugin_id}}/compare",
            ],
            "auth": "Bearer token required for comparison execution endpoints.",
        }

    @app.get(f"{API_PREFIX}/rules")
    def rules() -> dict[str, Any]:
        return {
            "namespace": "mcp.solo-map.app/v1",
            "version": __version__,
            "rules": [
                "All plugins expose a manifest with id, version, inputs, outputs, and safety notes.",
                "Comparison tools must return assumptions, warnings, ranked results, and source_url when known.",
                "Decision outputs are recommendations, not official financial/legal/medical advice.",
                "Remote MCP must be deny-by-default and tool-allowlisted in production.",
                "Every plugin must include tests for at least one eligible and one ineligible case.",
            ],
        }

    @app.get(f"{API_PREFIX}/plugins")
    def list_plugins() -> dict[str, Any]:
        manifest = load_plugin_manifest()
        return {"plugins": [manifest.model_dump()]}

    @app.get(f"{API_PREFIX}/plugins/{{plugin_id}}")
    def get_plugin(plugin_id: str) -> dict[str, Any]:
        manifest = load_plugin_manifest()
        if plugin_id != manifest.id:
            raise HTTPException(status_code=404, detail="Plugin not found")
        return manifest.model_dump()

    @app.post(f"{API_PREFIX}/compare/generic")
    def compare_generic_endpoint(
        request: GenericCompareRequest, _: None = Depends(require_token)
    ) -> Any:
        return compare_generic(request)

    @app.post(f"{API_PREFIX}/loan/simulate")
    def simulate_loan_endpoint(
        request: LoanCompareRequest, _: None = Depends(require_token)
    ) -> LoanCompareResponse:
        products = load_loan_products()
        results = [simulate_loan(product, request) for product in products]
        return LoanCompareResponse(
            best=None,
            results=results,
            assumptions=["Single-product simulation mode. Use /v1/loan/compare for ranking."],
            warnings=[],
        )

    @app.post(f"{API_PREFIX}/loan/compare")
    def compare_loan_endpoint(
        request: LoanCompareRequest, _: None = Depends(require_token)
    ) -> LoanCompareResponse:
        products = load_loan_products()
        return compare_loans(products, request)

    @app.post(f"{API_PREFIX}/plugins/{{plugin_id}}/compare")
    def compare_plugin(
        plugin_id: str, payload: dict[str, Any], _: None = Depends(require_token)
    ) -> dict[str, Any]:
        if plugin_id in {"loan-repayment", "loan"}:
            loan_request = LoanCompareRequest.model_validate(payload)
            return compare_loans(load_loan_products(), loan_request).model_dump()
        if plugin_id in {"generic", "generic-comparison"}:
            generic_request = GenericCompareRequest.model_validate(payload)
            return compare_generic(generic_request).model_dump()
        raise HTTPException(status_code=404, detail="Plugin not found")

    return app


app = create_app()


def main() -> None:
    uvicorn.run("comparison_engine.api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)


if __name__ == "__main__":
    main()
