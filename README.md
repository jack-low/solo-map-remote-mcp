# Solo Map Comparison Engine Kit

AIエージェント対応の汎用比較エンジンです。最初の実装はローン返済シミュレーションですが、設計上は SaaS 選定、PC/ガジェット比較、補助金比較、保険、ベンダー選定、制度比較などに転用できます。

## できること

- FastAPI で `mcp.solo-map.app/v1` 風のREST APIを提供
- MCPサーバーとして Codex / Claude Code / Gemini CLI / Cursor / Hermes-Agent から呼び出し可能
- Codex Skill / Claude Skill / Gemini command / Cursor rules / Hermes profile の雛形を同梱
- ローン以外にも使える generic weighted comparison を提供
- 金融機関名・商品名・用途メモの曖昧検索、月返済上限、Web完結、固定/変動金利などの絞り込みに対応
- 候補ごとの提案理由、注意点、次の確認アクションを返却
- GitHub OSS 化しやすい MIT License / CI / Docker / tests 付き

## 開発環境構築手順

```bash
git clone https://github.com/jack-low/solo-map-remote-mcp.git
cd solo-map-remote-mcp
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
pytest
```

API起動:

```bash
uvicorn comparison_engine.api:app --reload --host 0.0.0.0 --port 8000
```

確認:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/plugins
```

比較実行 API は `SOLO_MAP_API_TOKEN` による Bearer 認証が必要です。

MCP stdio起動:

```bash
python -m comparison_engine.mcp_server
```

uv でのMCP起動:

```bash
uv --directory "$PWD" run solo-compare-mcp
```

`uv --directory` に渡す値は GitHub URL ではなく、clone 後のローカルディレクトリです。
Windows 例: `uv --directory C:\Work\solo-map-remote-mcp run solo-compare-mcp`

## Docker

```bash
docker compose up --build
```

## API例

```bash
curl -X POST http://localhost:8000/v1/loan/compare \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SOLO_MAP_API_TOKEN" \
  -d '{
    "amount": 1000000,
    "term_months": 120,
    "annual_income": 4000000,
    "purpose": "multi",
    "membership": true,
    "bonus_ratio": 0,
    "objective": "recommendation",
    "providers": ["北洋", "ろうきん"],
    "query": "web",
    "require_web_contract": true,
    "max_monthly_payment": 15000
  }'
```

## 汎用比較API例

```bash
curl -X POST http://localhost:8000/v1/compare/generic \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SOLO_MAP_API_TOKEN" \
  -d @examples/generic_saas_compare.json
```

## 住宅ローン借換の相談例

```bash
curl -X POST http://localhost:8000/v1/loan/compare \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SOLO_MAP_API_TOKEN" \
  -d @examples/housing_refinance_compare.json
```

自然文の例:

> 住宅ローンを借換したい。借換予定額は2,600万円、現在0.9%で月7万円弱、見直し後3.25%で月9万円弱になりそうなので抑えたい。

この場合は `purpose=home_refinance`、`amount=26000000`、`term_months=480`、`reset_monthly_payment=90000`、`max_monthly_payment=90000` を目安に比較します。返済期間が不明な場合は、必ず推定として扱います。

## 公開運用のセキュリティ設定

- `SOLO_MAP_API_TOKEN`: 比較実行 API の Bearer トークン。未設定または `change-me` の場合は比較 API を拒否します。
- `SOLO_MAP_ALLOWED_ORIGINS`: CORS 許可オリジン。未設定時は `https://mcp.solo-map.app` のみ許可します。
- `SOLO_MAP_MAX_BODY_BYTES`: 受信ボディ上限。未設定時は 64KiB です。
- レスポンスには `X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy`、`Content-Security-Policy` を付与します。

## エージェント対応

| Agent | 入口 | 同梱ファイル |
|---|---|---|
| Codex | `AGENTS.md`, Skill, MCP | `AGENTS.md`, `skills/comparison-engine/SKILL.md`, `.mcp.json` |
| Claude Code | MCP, Skill/command | `configs/claude/.claude/...` |
| Gemini CLI | `GEMINI.md`, custom command, MCP | `configs/gemini/...` |
| Cursor | Rules, MCP | `configs/cursor/.cursor/...` |
| Hermes-Agent | profile + MCP | `configs/hermes/...` |

### Claude Code

```bash
claude mcp add --scope user --transport stdio solo-map-comparison-engine \
  -- uv --directory <local-clone-path> run solo-compare-mcp
claude mcp list
```

### Codex

```bash
codex mcp add solo-map-comparison-engine \
  -- uv --directory <local-clone-path> run solo-compare-mcp
codex mcp list
```

### Cursor

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "solo-map-comparison-engine": {
      "command": "uv",
      "args": ["--directory", "<local-clone-path>", "run", "solo-compare-mcp"]
    }
  }
}
```

### AIに接続を頼む文面

```text
https://github.com/jack-low/solo-map-remote-mcp を clone し、clone 後のローカル絶対パスを <local-clone-path> として、このMCPを追加してください。名前は solo-map-comparison-engine、transport は stdio、command は uv、args は ["--directory", "<local-clone-path>", "run", "solo-compare-mcp"] です。住宅ローン借換や商品比較では compare_loan_repayment / compare_generic_options を使い、前提・注意点・候補理由を必ず返してください。
```

## GitHub

Repository: <https://github.com/jack-low/solo-map-remote-mcp>

## 注意

金融商品の返済額は概算です。手数料、印紙代、審査結果、返済日、金利改定、保証会社条件により正式見積と差が出ます。
