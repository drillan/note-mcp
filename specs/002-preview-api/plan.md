# Implementation Plan: プレビューAPI対応

**Branch**: `002-preview-api` | **Date**: 2025-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-preview-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

note.com MCP Serverのプレビュー機能を拡張し、API経由で`preview_access_token`を取得して直接プレビューURLにアクセスすることで高速化・安定化を図る。以下の2つの利用モードを提供：

1. **人間確認用モード（`note_show_preview`改善）**: API経由でトークン取得後、ブラウザで直接プレビューURLを開く
2. **プログラム用モード（`note_get_preview_html`新規追加）**: API経由でプレビューHTMLを取得

## Technical Context

**Language/Version**: Python 3.11+ (pyproject.toml: requires-python = ">=3.11")
**Primary Dependencies**:
- FastMCP 2.0.0+ (MCP server framework)
- Playwright 1.40.0+ (browser automation for login/preview display)
- httpx 0.27.0+ (HTTP client for API requests)
- Pydantic 2.0.0+ (data validation)

**Storage**: keyring (OS secure storage for session cookies)
**Testing**: pytest 8.4.1+, pytest-asyncio 0.23.0+
**Target Platform**: Linux server (also compatible with macOS)
**Project Type**: Single project (MCP server)
**Performance Goals**:
- プレビュー表示: 3秒以内（現行エディター経由より大幅改善）
- HTML取得: 5秒以内
- E2Eテスト高速化: 80%以上

**Constraints**:
- note.com APIの形式に依存（`POST /api/v2/notes/{article_key}/access_tokens`）
- プレビューURL形式: `https://note.com/preview/{article_key}?prev_access_key={token}`
- 認証済みセッション必須

**Scale/Scope**: Single user (personal MCP server), 低頻度操作

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Requirement | Status | Notes |
|---------|-------------|--------|-------|
| Article 1: Test-First Imperative | TDDに従う | ✅ PASS | ユニットテスト作成 → 承認 → 実装 |
| Article 2: Documentation Integrity | 仕様との整合性 | ✅ PASS | spec.mdに基づいて実装 |
| Article 3: MCP Protocol Compliance | MCPプロトコル準拠 | ✅ PASS | FastMCPフレームワーク使用、Pydanticで入力検証 |
| Article 4: Simplicity | 最小構造 | ✅ PASS | 既存構造への追加のみ、新規プロジェクト不要 |
| Article 5: Code Quality Standards | 品質基準遵守 | ✅ PASS | ruff, mypy, pytest実行必須 |
| Article 6: Data Accuracy Mandate | データ正確性 | ✅ PASS | APIからトークン取得、推測禁止 |
| Article 7: DRY Principle | 重複禁止 | ✅ PASS | 既存NoteAPIClient再利用 |
| Article 9: Python Type Safety | 型安全性 | ✅ PASS | 全関数に型注釈必須 |
| Article 11: SpecKit Naming | 命名規則 | ✅ PASS | 002-preview-api形式 |

**Pre-Design Gate**: ✅ PASS - No violations detected

**Post-Design Gate**: ✅ PASS - Design artifacts comply with constitution
- research.md: 技術調査完了、既存パターン踏襲
- data-model.md: Pydanticモデル定義済み、型安全性確保
- contracts/: API契約・MCPツール契約定義済み
- quickstart.md: 実装手順・テスト手順明確化

## Project Structure

### Documentation (this feature)

```text
specs/002-preview-api/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/note_mcp/
├── api/
│   ├── client.py        # NoteAPIClient (既存、再利用)
│   ├── articles.py      # 記事API (既存)
│   └── preview.py       # NEW: プレビューAPI (access_token取得)
├── browser/
│   ├── manager.py       # BrowserManager (既存)
│   └── preview.py       # 既存、API経由に改修
├── models.py            # Pydanticモデル (PreviewAccessToken追加)
└── server.py            # MCPツール定義 (note_get_preview_html追加)

tests/
├── unit/
│   └── test_preview_api.py  # NEW: プレビューAPI単体テスト
└── integration/
    └── test_preview_e2e.py  # NEW: E2E統合テスト
```

**Structure Decision**: 既存のsrc/note_mcp構造に追加。api/preview.pyを新規作成し、browser/preview.pyを改修。

## Complexity Tracking

> **No Constitution violations requiring justification**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
