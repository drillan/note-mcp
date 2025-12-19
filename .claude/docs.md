# Documentation Guidelines

このファイルは、プロジェクトのドキュメンテーションガイドラインを提供します。

## Documentation System

プロジェクトで使用するドキュメンテーションシステムを記載してください。

**例: Sphinx + MyST-Parser**

Documentation is built with **Sphinx** + **MyST-Parser** (Markdown support) + **Mermaid** diagrams.

### Building Docs

例: Sphinxを使用する場合
```bash
cd docs
make html
# Output: docs/_build/html/index.html

# または直接実行
sphinx-build -M html docs docs/_build
```

他のドキュメンテーションシステムを使用する場合は、適切なビルドコマンドを記載してください。

## Writing Guidelines

### Markup Syntax

使用するマークアップ構文とその拡張機能を記載してください。

**例: MyST (Markdown for Sphinx)**

Write all documentation in [MyST](https://mystmd.org/guide) format (Markdown for Sphinx).

**Supported extensions**:
- `colon_fence` - Directive syntax using `:::`
- `substitution` - Variable substitution
- `tasklist` - Task lists with `[ ]` and `[x]`
- `attrs_inline` - Inline attributes
- `deflist` - Definition lists

**Common patterns**:

````markdown
# Table of contents
```{contents}
:depth: 2
:local:
```

# Admonitions
```{note}
This is a note.
```

# Code blocks with line numbers
```{code-block} python
:linenos:
def example():
    pass
```
````

### Tone and Style

プロフェッショナルで簡潔な技術文書を心がけてください。

**Avoid**:
- ❌ 誇張表現: "革命的"、"画期的"、"amazing"
- ❌ マーケティング用語: "best-in-class"、"cutting-edge"、"next-generation"
- ❌ 絶対的な表現: "完全サポート"、"必ず"、"絶対"
- ❌ 感嘆符: "！" for professional tone
- ❌ 内部用語: "Phase 1"、"Milestone 3" (代わりに "v0.2+" を使用)
- ❌ 内部参照: "Article 3"、"Article 8" (代わりに概念を直接参照)
- ❌ 過度な太字使用: 文中で`**`を多用すると可読性が低下します

**Prefer**:
- ✅ 事実に基づく記述: "supports"、"provides"、"enables"
- ✅ 限定的な表現: "多くの場合"、"通常"、"一般的に"
- ✅ バージョン表記: "v0.2+"、"since v0.3"、"as of v0.2"
- ✅ 明確で簡潔な技術的記述

### Emphasis

太字（`**bold**`）は本当に必要な場合のみ使用してください。過度な修飾はドキュメントの可読性を損ない、プロフェッショナルな印象を損ないます。

**使用が許可される場合:**
- セクション見出し（自動）
- 重要な警告や要件
- 初出の重要用語

**重要**: 通常の説明文では太字を使用せず、平文で記述してください。

**Avoid over-emphasis**:
```markdown
# ❌ 太字が多すぎる
**このライブラリ**は**すべての機能**に**優れたサポート**を提供します。

# ✅ 適切な太字使用
このライブラリはカスタムツールをサポートします。**注意**: APIキーが必要です。
```

### Code Block Highlighting

構文ハイライターエラーを避けるため、以下に注意してください。

**Common pitfalls**:

#### TOML
```toml
# ❌ TOMLでnullを使用しない
key = null

# ✅ 代わりにコメントを使用
# key = (not set)
```

#### JSON
```json
// ❌ 省略記号を使用しない
{
  "items": [...]
}

// ✅ 完全な構造を示すかコメントを使用
{
  "items": ["item1", "item2"]
}
```

#### Unknown lexers
````text
# ❌ サポートされていないlexerを使用しない
```unknownlang
code here
```

# ✅ 'text'または'bash'を使用
```text
code here
```
````

#### Special characters
```python
# ❌ コードブロック内で矢印記号を避ける
result → value  # ハイライトエラーの原因となる可能性

# ✅ 標準的なASCIIを使用
result = value
```

#### Nested code blocks

コードブロック内にさらにコードブロックを記載する場合（例: Markdown構文の例を示す場合）は、ネスト構文を使用します。

**ネストの方法:**

外側のコードブロックのバッククォートの数を増やします：
- 通常のコードブロック: 3つのバッククォート（```）
- 1段階ネスト: 4つのバッククォート（````）
- 2段階ネスト: 5つのバッククォート（`````）

**例:**

`````markdown
# ❌ 正しくレンダリングされない
```markdown
# MyST構文の例
```{note}
This is a note.
```
```

# ✅ 正しいネスト構文
````markdown
# MyST構文の例
```{note}
This is a note.
```
````
`````

**使用例:**

このファイル内でもネスト構文を使用しています：
- Markup Syntax セクション（46-64行）: MyST構文の例
- Unknown lexers セクション（134-144行）: コードブロックの例

**参考:**
- [MyST Parser - Nesting Directives](https://myst-parser.readthedocs.io/en/v0.15.1/syntax/syntax.html#nesting-directives)

## Structure Guidelines

### File Organization

プロジェクトのドキュメント構造を記載してください。

例:
```
docs/
├── index.md              # Main landing page
├── user-guide.md         # Getting started guide
├── features.md           # Feature-specific docs
├── how-it-works.md       # Technical details
├── architecture.md       # System design
└── conf.py              # Documentation config (e.g., Sphinx)
```

### Document Sections

機能ドキュメントの標準セクション:

1. **Overview** - 簡潔な紹介（2-3文）
2. **Quick Start** - 最小限の動作例
3. **Features** - 詳細な機能リスト
4. **Limitations** - 既知の制約
5. **Troubleshooting** - よくある問題と解決策
6. **FAQ** - よくある質問
7. **Examples** - サンプルコードへのリンク

### Cross-References

クロスリファレンスの構文を記載してください。

例: MyST
```markdown
# 別のドキュメントへのリンク
[Features](features.md)

# セクションへのリンク
[Installation](#installation)

# カスタムテキストでリンク
See the [features guide](features.md) for details.
```

## Version Documentation

### Feature Status Labels

機能の成熟度を示すラベル:

- **v0.2+** - バージョン0.2以降で利用可能
- **Experimental** - 動作するが変更される可能性がある
- **Deprecated** - 将来削除される予定
- **Planned** - まだ実装されていない

**Example**:
```markdown
## Custom Tools (v0.2+)

### Basic Tools
Dependency-free tools are supported (v0.2+).

### Advanced Features (Experimental)
Advanced dependency injection is supported as an experimental feature.
```

### Version-Specific Notes

バージョン固有の動作を記載する場合:

```markdown
**Version Support**:
- v0.1: Basic support only
- v0.2+: Enhanced features
- v0.2+ (Experimental): Experimental features
```

## Common Warnings to Avoid

ドキュメントビルド時の一般的な警告を避けるため:

1. **Missing cross-references**
   ```markdown
   # ❌ 壊れたリンク
   [Non-existent file](missing.md)

   # ✅ 有効なリンク
   [Existing file](user-guide.md)
   ```

2. **Empty sections before transitions**
   ```markdown
   # ❌ 空のセクション
   ### Section Title

   ---

   # ✅ コンテンツを追加
   ### Section Title

   Content here.

   ---
   ```

3. **Missing toctree entries** (Sphinx)
   - すべてのドキュメントファイルを`index.md`のtoctreeに含める
   - ビルド出力で "document isn't included in any toctree" をチェック

4. **Heading level skips**
   ```markdown
   # ❌ 見出しレベルをスキップ
   # Heading 1
   ### Heading 3  # Skipped level 2

   # ✅ 連続したレベル
   # Heading 1
   ## Heading 2
   ### Heading 3
   ```

## Build Verification

### Before Committing

コミット前にドキュメントをビルドしてください:

例: Sphinx
```bash
sphinx-build -M html docs docs/_build
```

**Check for**:
- ❌ Errors (must fix)
- ⚠️ Warnings (should fix)
- ✅ Success message

### Clean Build

キャッシュなしでクリーンビルド:

例: Sphinx
```bash
rm -rf docs/_build
sphinx-build -M html docs docs/_build
```

## Configuration

### Documentation System Configuration

ドキュメンテーションシステムの設定を記載してください。

**例: Sphinx Configuration (`docs/conf.py`)**

```python
# Project info
project = '{{PROJECT_NAME}}'
language = 'ja'  # または 'en'

# Extensions
extensions = [
    'myst_parser',           # Markdown support
    'sphinx.ext.autodoc',    # Auto-generate docs from docstrings
    'sphinx.ext.napoleon',   # Google-style docstrings
    'sphinxcontrib.mermaid', # Mermaid diagrams
]

# MyST configuration
myst_enable_extensions = [
    'colon_fence',
    'substitution',
    'tasklist',
    'attrs_inline',
    'deflist',
]
```

## References

ドキュメンテーションシステムの参考資料を記載してください。

例: Sphinx + MyST
- [MyST Parser Documentation](https://mystmd.org/guide)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Mermaid Diagram Syntax](https://mermaid.js.org/)
- [Claude Code Memory System](https://docs.claude.com/ja/docs/claude-code/memory)
