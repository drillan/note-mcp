# Data Model: E2Eテスト - ネイティブHTML変換検証

**Feature**: `001-e2e-native-html-validation`
**Date**: 2026-01-01
**Phase**: 1 - Design

## 1. テストケースモデル

### 1.1 MarkdownTestCase

テスト対象のMarkdown記法と期待されるHTML変換結果を定義。

```python
from dataclasses import dataclass
from enum import Enum


class TriggerType(Enum):
    """ProseMirror変換トリガータイプ。"""
    SPACE = " "      # スペースでトリガー
    ENTER = "\n"     # Enterでトリガー（変換されない）
    NONE = ""        # トリガーなし


class MarkdownCategory(Enum):
    """Markdown記法カテゴリ。"""
    HEADING = "heading"
    STRIKETHROUGH = "strikethrough"
    CODE_BLOCK = "code_block"
    ALIGNMENT = "alignment"


@dataclass(frozen=True)
class MarkdownTestCase:
    """テストケース定義。

    Attributes:
        category: Markdown記法のカテゴリ
        input_pattern: エディタに入力するパターン（例: "## 見出し"）
        trigger: 変換をトリガーする入力
        expected_tag: 期待されるHTML要素（例: "h2"）
        expected_text: 期待されるテキスト内容
        expected_style: 期待されるスタイル属性（オプション）
        description: テストケースの説明
    """
    category: MarkdownCategory
    input_pattern: str
    trigger: TriggerType
    expected_tag: str
    expected_text: str
    expected_style: str | None = None
    description: str = ""
```

### 1.2 定義済みテストケース

```python
# P1テストケース（優先度1）
P1_TEST_CASES: list[MarkdownTestCase] = [
    MarkdownTestCase(
        category=MarkdownCategory.HEADING,
        input_pattern="## テスト見出し2",
        trigger=TriggerType.SPACE,
        expected_tag="h2",
        expected_text="テスト見出し2",
        description="H2見出し変換",
    ),
    MarkdownTestCase(
        category=MarkdownCategory.HEADING,
        input_pattern="### テスト見出し3",
        trigger=TriggerType.SPACE,
        expected_tag="h3",
        expected_text="テスト見出し3",
        description="H3見出し変換",
    ),
    MarkdownTestCase(
        category=MarkdownCategory.STRIKETHROUGH,
        input_pattern="~~打消しテキスト~~",
        trigger=TriggerType.SPACE,
        expected_tag="s",
        expected_text="打消しテキスト",
        description="打消し線変換",
    ),
]

# P2テストケース（優先度2）
P2_TEST_CASES: list[MarkdownTestCase] = [
    MarkdownTestCase(
        category=MarkdownCategory.CODE_BLOCK,
        input_pattern="```",  # 開始フェンス
        trigger=TriggerType.SPACE,
        expected_tag="pre code",
        expected_text="console.log('test')",
        description="コードブロック変換",
    ),
    MarkdownTestCase(
        category=MarkdownCategory.ALIGNMENT,
        input_pattern="->中央揃えテキスト<-",
        trigger=TriggerType.NONE,  # プレースホルダー経由
        expected_tag="p",
        expected_text="中央揃えテキスト",
        expected_style="text-align: center",
        description="中央揃え変換",
    ),
    MarkdownTestCase(
        category=MarkdownCategory.ALIGNMENT,
        input_pattern="->右揃えテキスト",
        trigger=TriggerType.NONE,
        expected_tag="p",
        expected_text="右揃えテキスト",
        expected_style="text-align: right",
        description="右揃え変換",
    ),
]
```

## 2. 検証結果モデル

### 2.1 NativeHTMLValidationResult

既存の`ValidationResult`を拡張し、ネイティブHTML検証に特化。

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NativeHTMLValidationResult:
    """ネイティブHTML検証結果。

    Attributes:
        success: 検証成功かどうか
        test_case: 検証対象のテストケース
        expected_html: 期待されるHTML構造
        actual_html: 実際に取得したHTML
        message: 詳細メッセージ
        timestamp: 検証実行時刻
        source: HTMLソース（"native" = note.com生成, "api" = markdown_to_html()生成）
    """
    success: bool
    test_case: MarkdownTestCase
    expected_html: str
    actual_html: str | None
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "native"  # "native" or "api"

    @property
    def is_tautology_free(self) -> bool:
        """トートロジーではないことを確認。"""
        return self.source == "native"
```

### 2.2 TestSuiteResult

テストスイート全体の結果を集約。

```python
@dataclass
class TestSuiteResult:
    """テストスイート結果。

    Attributes:
        results: 個別の検証結果リスト
        total_count: 総テスト数
        passed_count: 成功数
        failed_count: 失敗数
        duration_seconds: 実行時間（秒）
    """
    results: list[NativeHTMLValidationResult]
    duration_seconds: float = 0.0

    @property
    def total_count(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed_count(self) -> int:
        return self.total_count - self.passed_count

    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.passed_count / self.total_count * 100

    def to_report(self) -> str:
        """テスト結果レポートを生成。"""
        lines = [
            "# ネイティブHTML変換検証レポート",
            "",
            f"- 総テスト数: {self.total_count}",
            f"- 成功: {self.passed_count}",
            f"- 失敗: {self.failed_count}",
            f"- 成功率: {self.success_rate:.1f}%",
            f"- 実行時間: {self.duration_seconds:.2f}秒",
            "",
        ]

        if self.failed_count > 0:
            lines.append("## 失敗したテスト")
            lines.append("")
            for result in self.results:
                if not result.success:
                    lines.append(f"### {result.test_case.description}")
                    lines.append(f"- 期待: `{result.expected_html}`")
                    lines.append(f"- 実際: `{result.actual_html}`")
                    lines.append(f"- メッセージ: {result.message}")
                    lines.append("")

        return "\n".join(lines)
```

## 3. エディタ状態モデル

### 3.1 EditorState

エディタの状態を追跡。

```python
@dataclass
class EditorState:
    """ProseMirrorエディタの状態。

    Attributes:
        is_focused: エディタにフォーカスがあるか
        cursor_position: カーソル位置（行, 列）
        content_html: 現在のHTMLコンテンツ
    """
    is_focused: bool = False
    cursor_position: tuple[int, int] = (0, 0)
    content_html: str = ""
```

## 4. データフロー

```
┌─────────────────────────────────────────────────────────────────┐
│                         テスト実行フロー                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MarkdownTestCase                                               │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐                                           │
│  │   editor_page   │  ← Playwright Page                        │
│  │   (fixture)     │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ type_markdown_  │  ← キーボード入力                          │
│  │ pattern()       │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │   ProseMirror   │  ← note.comエディタ（ネイティブ変換）        │
│  │   Conversion    │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │  preview_page   │  ← プレビューページ                        │
│  │  (fixture)      │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │PreviewValidator │  ← 既存ヘルパー                            │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  NativeHTMLValidationResult                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 5. 既存モデルとの関係

| 新規モデル | 既存モデル | 関係 |
|-----------|-----------|------|
| `MarkdownTestCase` | - | 新規 |
| `NativeHTMLValidationResult` | `ValidationResult` | 拡張 |
| `TestSuiteResult` | - | 新規 |
| `EditorState` | - | 新規（オプション） |

## 6. 型安全性（Constitution Article 9）

すべてのモデルは以下を満たす：

- `dataclass` または Pydantic モデルで定義
- すべてのフィールドに型アノテーション
- `mypy --strict` で検証可能
- `None` 可能なフィールドは `| None` で明示
