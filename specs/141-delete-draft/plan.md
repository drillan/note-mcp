# Implementation Plan: 下書き記事の削除機能

**Branch**: `141-delete-draft` | **Date**: 2026-01-13 | **Spec**: [141-delete-draft/spec.md](./spec.md)
**Input**: Feature specification from `/specs/141-delete-draft/spec.md`

## Summary

note.com MCPサーバーに下書き記事の削除機能を追加する。ユーザーがAIアシスタント経由で不要になった下書き記事を削除できるようにする。2つのMCPツール（`note_delete_draft`と`note_delete_all_drafts`）を提供し、確認フラグによる誤操作防止機能を実装する。親仕様（001-note-mcp）で定義された認証・セッション管理・API通信パターンを活用する。

## Technical Context

**Language/Version**: Python 3.11+ (pyproject.toml: requires-python = ">=3.11")
**Primary Dependencies**: mcp>=1.9.2, pydantic>=2.0, playwright, httpx (via NoteAPIClient)
**Storage**: keyring (OS secure storage for session cookies)
**Testing**: pytest >= 8.4.1, pytest-asyncio
**Target Platform**: Linux/macOS/Windows (desktop environments with browser support)
**Project Type**: Single project (MCP server)
**Performance Goals**: 削除操作は10秒以内、一括削除の確認フェーズは5秒以内、実行フェーズは30秒以内
**Constraints**: 下書きのみ削除可能、公開済み記事は削除拒否、レート制限10req/min
**Scale/Scope**: 個人ユーザー向け、1セッション1ユーザー

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Status | Notes |
|---------|--------|-------|
| **Article 1: Test-First Imperative** | ⏳ Pending | TDDに従い、ユニットテストを先に作成する |
| **Article 2: Documentation Integrity** | ✅ Pass | spec.mdで仕様定義済み、実装前に確認完了 |
| **Article 3: MCP Protocol Compliance** | ⏳ Pending | Pydanticモデルによる入力検証、適切なエラー形式を実装予定 |
| **Article 4: Simplicity** | ✅ Pass | 既存のNoteAPIClient、Session管理を再利用 |
| **Article 5: Code Quality Standards** | ⏳ Pending | コミット前にruff/mypy品質チェックを実行 |
| **Article 6: Data Accuracy Mandate** | ✅ Pass | ハードコード禁止、APIレスポンスを使用 |
| **Article 7: DRY Principle** | ✅ Pass | 既存のarticles.py、models.py、client.pyを活用 |
| **Article 8: Refactoring Policy** | ✅ Pass | 新規追加、既存コードへの破壊的変更なし |
| **Article 9: Python Type Safety** | ⏳ Pending | 全関数に型注釈、mypyチェック必須 |
| **Article 10: Python Docstring** | ⏳ Pending | Google-style docstringを記述 |
| **Article 11: SpecKit Naming** | ✅ Pass | ブランチ名・ディレクトリ名は規則準拠 |

**Gate Result**: ✅ PASS - 既存アーキテクチャとの整合性確認済み、実装に進む

## Project Structure

### Documentation (this feature)

```text
specs/141-delete-draft/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── delete-api.yaml  # OpenAPI specification for delete endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/note_mcp/
├── models.py           # 既存: DeleteResult追加
├── server.py           # 既存: note_delete_draft, note_delete_all_drafts ツール追加
├── api/
│   ├── articles.py     # 既存: delete_draft, delete_all_drafts関数追加
│   ├── client.py       # 既存: delete()メソッド既に実装済み
│   └── __init__.py     # 既存: 新関数をエクスポート

tests/
├── unit/
│   └── test_delete_draft.py    # 新規: ユニットテスト
├── integration/
│   └── test_delete_integration.py  # 新規: 統合テスト
└── contract/                   # 将来の契約テスト用
```

**Structure Decision**: 単一プロジェクト構造を維持。既存のapi/articles.pyに削除関数を追加し、server.pyにMCPツールを登録する。新規ファイル作成は不要で、既存ファイルへの追加のみ。

## Complexity Tracking

> Constitution Check has no violations requiring justification.

N/A - すべての設計は既存アーキテクチャに沿っており、憲法違反なし。

## Constitution Check (Post-Design)

*Phase 1完了後の再評価*

| Article | Status | Notes |
|---------|--------|-------|
| **Article 1: Test-First Imperative** | ⏳ Implementation | TDDに従い実装時にテストを先に作成 |
| **Article 2: Documentation Integrity** | ✅ Pass | spec.md, plan.md, research.md, data-model.md, quickstart.md完成 |
| **Article 3: MCP Protocol Compliance** | ✅ Pass | data-model.mdでPydanticモデル設計、contracts/で入出力スキーマ定義済み |
| **Article 4: Simplicity** | ✅ Pass | 既存クライアント再利用、新規ラッパー不要 |
| **Article 5: Code Quality Standards** | ⏳ Implementation | 実装時にruff/mypy品質チェックを実行 |
| **Article 6: Data Accuracy Mandate** | ✅ Pass | 設計でハードコード禁止を確認、APIレスポンスを使用 |
| **Article 7: DRY Principle** | ✅ Pass | 既存のlist_articles, get_article, NoteAPIClient.delete()を再利用 |
| **Article 8: Refactoring Policy** | ✅ Pass | 既存コードへの破壊的変更なし、追加のみ |
| **Article 9: Python Type Safety** | ✅ Pass | data-model.mdですべてのモデルに型注釈定義済み |
| **Article 10: Python Docstring** | ⏳ Implementation | 実装時にGoogle-style docstringを記述 |
| **Article 11: SpecKit Naming** | ✅ Pass | ブランチ名・ディレクトリ名は規則準拠 |

**Post-Design Gate Result**: ✅ PASS - 設計完了、実装フェーズに進む準備完了

## Generated Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| research.md | specs/141-delete-draft/research.md | 技術調査結果 |
| data-model.md | specs/141-delete-draft/data-model.md | データモデル設計 |
| delete-api.yaml | specs/141-delete-draft/contracts/delete-api.yaml | OpenAPI契約 |
| quickstart.md | specs/141-delete-draft/quickstart.md | 使用方法ガイド |

## Next Steps

1. `/speckit.tasks` コマンドで tasks.md を生成
2. TDDに従いテストを先に作成
3. 実装フェーズに進む
