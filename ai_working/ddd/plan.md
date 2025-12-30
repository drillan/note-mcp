# DDD Plan: 引用（blockquote）の出典入力機能

**Issue**: #14
**Branch**: `feature/014-blockquote-citation`
**Date**: 2024-12-30

## Problem Statement

note.comのMarkdown引用（blockquote）に「出典」を追加する機能を実装する。

### ユーザー価値

- 引用の正確性・信頼性向上（出典を明示）
- note.comの引用機能を完全にMCPでサポート
- 手動でUIを操作せずに出典付き引用を作成可能

### 現状

- 引用ブロック自体は #12 で対応済み
- `<figcaption></figcaption>` と空のまま
- 出典入力は未対応

## Proposed Solution

### アプローチ: Markdown拡張 + API経由

Markdownで出典を表現し、`markdown_to_html()` で `<figcaption>` に変換する。

### Markdown構文

```markdown
> 引用テキスト
> — 出典名
```

出典URL付き:

```markdown
> 引用テキスト
> — 出典名 (https://example.com)
```

### 変換結果

```html
<figure name="UUID" id="UUID">
  <blockquote>
    <p name="UUID" id="UUID">引用テキスト</p>
  </blockquote>
  <figcaption>出典名</figcaption>
</figure>
```

URL付きの場合:

```html
<figure name="UUID" id="UUID">
  <blockquote>
    <p name="UUID" id="UUID">引用テキスト</p>
  </blockquote>
  <figcaption><a href="https://example.com">出典名</a></figcaption>
</figure>
```

## Alternatives Considered

### Option B: Playwright経由でUI操作

- ❌ ブラウザ操作が複雑化
- ❌ DOM構造に依存（変更に弱い）
- ❌ API経由の記事作成/更新で使えない

### Option C: 両方をサポート

- ❌ 実装コスト高
- ❌ メンテナンスコスト高
- 将来必要になれば追加可能

**選択理由**: Option Aは既存の画像captionパターンと同様で、最小限の変更で実装可能。

## Architecture & Design

### Key Interfaces

変更なし。`markdown_to_html(content: str) -> str` のシグネチャは維持。

### Module Boundaries

```
src/note_mcp/utils/markdown.py
  └── _convert_blockquotes_to_note_format()  # 修正対象
      └── _extract_citation()  # 新規追加（内部ヘルパー）
```

### Data Flow

```
Markdown入力
    ↓
markdown_to_html()
    ↓
_convert_blockquotes_to_note_format()
    ↓ 出典行を検出
_extract_citation()
    ↓
<figcaption>に出典を挿入
    ↓
HTML出力
```

### 出典抽出ロジック

1. blockquote内の最終 `<p>` タグを取得
2. `— ` (emダッシュ + スペース) で始まるかチェック
3. 始まる場合:
   - その行を出典テキストとして抽出
   - `(URL)` パターンがあればURL抽出
   - blockquoteから出典行を削除
   - figcaptionに出典を挿入

## Files to Change

### Non-Code Files (Phase 2)

- [ ] `docs/usage.md` - 出典付きblockquoteの使用方法を追加
- [ ] `README.md` - 機能一覧に出典機能を追加（必要に応じて）

### Code Files (Phase 4)

- [ ] `src/note_mcp/utils/markdown.py` - 出典抽出・変換ロジック追加
- [ ] `tests/unit/test_markdown.py` - 出典機能のテスト追加

## Philosophy Alignment

### Ruthless Simplicity

- **Start minimal**: 1ファイルの1関数を修正
- **Avoid future-proofing**: Playwright対応は将来必要になってから
- **Clear over clever**: 既存の画像captionパターンを踏襲

### Modular Design

- **Bricks**: markdown変換は独立したユーティリティ
- **Studs**: `markdown_to_html()` シグネチャ変更なし
- **Regeneratable**: 仕様から再実装可能なシンプルさ

## Test Strategy

### Unit Tests

1. **出典なしblockquote** - 既存動作の維持確認
2. **出典テキストのみ** - `— 出典名` パターン
3. **出典テキスト + URL** - `— 出典名 (URL)` パターン
4. **複数行blockquote + 出典** - 改行 + 出典の組み合わせ
5. **emダッシュなしの行** - 誤検出しないことを確認
6. **空の出典** - `— ` のみの場合

### Integration Tests

- API経由で出典付き記事を作成し、出典が保存されることを確認

### User Testing

1. MCPツールで出典付きblockquoteを含む記事を作成
2. note.comのプレビューで出典が表示されることを確認

## Implementation Approach

### Phase 2 (Docs)

1. `docs/usage.md` に出典付きblockquoteの使用方法を追加
   - Markdown構文の説明
   - 使用例

### Phase 3 (Code Plan)

コード実装の詳細計画を作成

### Phase 4 (Code)

1. **テスト作成** (TDD: Red)
   - `test_markdown.py` に出典機能のテストを追加
   - テストが失敗することを確認

2. **実装** (TDD: Green)
   - `_extract_citation()` ヘルパー関数を追加
   - `_convert_blockquotes_to_note_format()` を修正
   - テストが通ることを確認

3. **リファクタリング** (TDD: Refactor)
   - 必要に応じてコード整理

### Phase 5 (Cleanup)

1. 品質チェック実行 (`make check`)
2. 全テスト実行 (`make test`)
3. git status確認
4. コミット

## Success Criteria

- [ ] 出典付きblockquoteがHTMLに正しく変換される
- [ ] 出典URLがリンクとして変換される
- [ ] 既存のblockquote機能が壊れていない
- [ ] 全テストがパス
- [ ] `make check` がパス
- [ ] note.comでプレビュー確認済み

## Next Steps

✅ Plan complete and approved
➡️ Ready for `/ddd:2-docs`
