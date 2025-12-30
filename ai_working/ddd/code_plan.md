# Code Implementation Plan

Generated: 2024-12-30
Based on: Phase 1 plan + Phase 2 documentation (README.md)

## Summary

引用ブロック（blockquote）に出典（citation）を追加する機能を実装する。
Markdownで `— ` (emダッシュ + スペース) で始まる行を出典として認識し、
HTML変換時に `<figcaption>` 要素に挿入する。

## Files to Change

### File: src/note_mcp/utils/markdown.py

**Current State**:
- `_convert_blockquotes_to_note_format()` 関数 (lines 120-152)
- blockquoteを `<figure>` でラップし、空の `<figcaption></figcaption>` を出力
- 出典の検出・抽出ロジックなし

**Required Changes**:
README.mdの仕様に従い、以下を実装:
- `— 出典名` → `<figcaption>出典名</figcaption>`
- `— 出典名 (URL)` → `<figcaption><a href="URL">出典名</a></figcaption>`

**Specific Modifications**:

1. **新規追加**: 正規表現パターン (module-level constants)
   ```python
   # Pattern to detect citation line: starts with em-dash + space
   _CITATION_LINE_PATTERN = re.compile(r"^—\s+(.+)$")
   # Pattern to extract URL from citation: text (URL)
   _CITATION_URL_PATTERN = re.compile(r"^(.+?)\s*\((\S+)\)\s*$")
   ```

2. **新規追加**: `_extract_citation()` ヘルパー関数
   ```python
   def _extract_citation(blockquote_content: str) -> tuple[str, str]:
       """Extract citation from blockquote content.

       Args:
           blockquote_content: HTML content inside <blockquote> tags

       Returns:
           Tuple of (modified_content, figcaption_html)
           - modified_content: blockquote content with citation line removed
           - figcaption_html: HTML for figcaption (may be empty string)
       """
   ```

   ロジック:
   - blockquote内の最後の `<p>` タグのテキストを取得
   - `— ` で始まるかチェック
   - 始まる場合:
     - 出典テキストを抽出
     - `(URL)` パターンがあればURL抽出、リンク生成
     - blockquoteから出典行を削除
   - 始まらない場合: 空のfigcaptionを返す

3. **修正**: `_convert_blockquotes_to_note_format()` 関数
   - `wrap_in_figure()` 内部関数を修正
   - `_extract_citation()` を呼び出し
   - 戻り値のfigcaption HTMLを使用

**Dependencies**: なし (既存の `re` モジュールのみ使用)

---

### File: tests/unit/test_markdown.py

**Current State**:
- blockquoteのテストあり (lines 140-226)
- figure format、multiline、formattingのテスト済み
- 出典機能のテストなし

**Required Changes**:
README.mdの仕様に基づくテストを追加

**Specific Modifications**:

新規テストケース (TDD: Red フェーズで先に作成):

1. **test_blockquote_without_citation** - 出典なしblockquoteの既存動作確認
   ```python
   def test_blockquote_without_citation(self) -> None:
       """Test that blockquotes without citation have empty figcaption."""
       result = markdown_to_html("> Just a quote")
       assert "<figcaption></figcaption>" in result
   ```

2. **test_blockquote_with_citation_text_only** - 出典テキストのみ
   ```python
   def test_blockquote_with_citation_text_only(self) -> None:
       """Test blockquote with citation text only (no URL)."""
       markdown = """> 知識は力なり
   > — フランシス・ベーコン"""
       result = markdown_to_html(markdown)
       assert "<figcaption>フランシス・ベーコン</figcaption>" in result
       assert "知識は力なり" in result
       # Citation line should NOT appear in blockquote content
       assert "—" not in result.split("<figcaption>")[0].split("<blockquote>")[1]
   ```

3. **test_blockquote_with_citation_and_url** - 出典テキスト + URL
   ```python
   def test_blockquote_with_citation_and_url(self) -> None:
       """Test blockquote with citation text and URL."""
       markdown = """> 知識は力なり
   > — フランシス・ベーコン (https://example.com)"""
       result = markdown_to_html(markdown)
       assert '<figcaption><a href="https://example.com">フランシス・ベーコン</a></figcaption>' in result
   ```

4. **test_blockquote_multiline_with_citation** - 複数行引用 + 出典
   ```python
   def test_blockquote_multiline_with_citation(self) -> None:
       """Test multiline blockquote with citation on last line."""
       markdown = """> Line 1
   > Line 2
   > — Source"""
       result = markdown_to_html(markdown)
       assert "Line 1" in result
       assert "Line 2" in result
       assert "<figcaption>Source</figcaption>" in result
   ```

5. **test_blockquote_em_dash_not_at_start** - 行頭以外のemダッシュ
   ```python
   def test_blockquote_em_dash_not_at_start(self) -> None:
       """Test that em-dash not at line start is not treated as citation."""
       result = markdown_to_html("> Text with — em-dash in middle")
       # Should NOT extract as citation
       assert "<figcaption></figcaption>" in result
       assert "em-dash" in result
   ```

6. **test_blockquote_citation_empty_text** - 空の出典（`— ` のみ）
   ```python
   def test_blockquote_citation_empty_text(self) -> None:
       """Test blockquote with only em-dash (no citation text)."""
       markdown = """> Quote
   > — """
       result = markdown_to_html(markdown)
       # Empty citation should result in empty figcaption
       assert "<figcaption></figcaption>" in result
   ```

**Dependencies**: markdown.py の実装

---

## Implementation Chunks

### Chunk 1: Unit Tests (TDD Red Phase)

**Files**: tests/unit/test_markdown.py
**Description**: 出典機能の全テストケースを先に追加
**Why first**: TDD原則 - テストが失敗することを確認してから実装
**Test strategy**: `uv run pytest tests/unit/test_markdown.py -v` で全テスト失敗を確認
**Dependencies**: None
**Commit point**: テスト追加後（失敗状態でコミット不要）

### Chunk 2: Core Implementation (TDD Green Phase)

**Files**: src/note_mcp/utils/markdown.py
**Description**: 出典抽出・変換ロジックの実装
**Why second**: テストをパスさせる最小限の実装
**Test strategy**: `uv run pytest tests/unit/test_markdown.py -v` で全テストパス
**Dependencies**: Chunk 1 (tests exist)
**Commit point**: 全テストパス後

### Chunk 3: Quality & Integration (TDD Refactor Phase)

**Files**: Both files
**Description**: 品質チェック、リファクタリング（必要なら）
**Why third**: Green後のリファクタリングフェーズ
**Test strategy**:
- `uv run ruff check --fix .`
- `uv run ruff format .`
- `uv run mypy .`
- `uv run pytest`
**Dependencies**: Chunk 2
**Commit point**: 全品質チェックパス後

---

## Testing Strategy

### Unit Tests to Add

**File: tests/unit/test_markdown.py**

| テスト名 | 検証内容 |
|----------|----------|
| `test_blockquote_without_citation` | 出典なし→空figcaption |
| `test_blockquote_with_citation_text_only` | 出典テキストのみ |
| `test_blockquote_with_citation_and_url` | 出典 + URLリンク |
| `test_blockquote_multiline_with_citation` | 複数行 + 出典 |
| `test_blockquote_em_dash_not_at_start` | 誤検出防止 |
| `test_blockquote_citation_empty_text` | 空出典のエッジケース |

### User Testing Plan

**Commands to run**:
```bash
# MCP経由で出典付き記事を作成
# Claude Desktopまたはnote-mcpツールで:
note_create_draft(
    title="出典テスト",
    body="""
> 知識は力なり
> — フランシス・ベーコン (https://ja.wikipedia.org/wiki/知識は力なり)
"""
)
```

**Expected behavior**:
- note.comのプレビューで出典が表示される
- 出典がリンクとしてクリック可能

---

## Philosophy Compliance

### Ruthless Simplicity

- **1ファイル、1関数の修正**: `_convert_blockquotes_to_note_format()` のみ
- **新規追加は最小限**: ヘルパー関数1つ、正規表現2つ
- **YAGNI**: Playwright対応は将来必要になってから

### Modular Design

- **Brick**: markdown変換ユーティリティは独立
- **Stud**: `markdown_to_html()` シグネチャ変更なし
- **Regeneratable**: 仕様から再実装可能

---

## Commit Strategy

**Commit 1**: (Chunk 2 + Chunk 3 完了後)
```
feat: Add citation support for blockquotes

- Add _extract_citation() helper for em-dash citation detection
- Support citation text only: `— Source`
- Support citation with URL: `— Source (URL)`
- URL citations rendered as links in figcaption
- Existing blockquotes without citations unchanged
- All tests passing, quality checks pass
```

---

## Risk Assessment

**Low Risk Changes**:
- 既存の空figcaption動作は維持される
- 出典なしblockquoteは影響なし

**Edge Cases to Handle**:
- emダッシュ (`—`) vs ハイフン (`-`) の区別
- 空の出典テキスト
- URLの括弧内にスペースがある場合

---

## Success Criteria

Code is ready when:

- [x] README.mdの仕様を理解
- [ ] 全テストケース作成済み
- [ ] `_extract_citation()` 実装済み
- [ ] `_convert_blockquotes_to_note_format()` 修正済み
- [ ] `uv run pytest` パス
- [ ] `uv run ruff check --fix .` パス
- [ ] `uv run ruff format .` パス
- [ ] `uv run mypy .` パス
- [ ] note.comでプレビュー確認済み

---

## Next Steps

✅ Code plan complete and detailed
➡️ Get user approval
➡️ When approved, run: `/ddd:4-code`
