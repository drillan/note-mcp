---
description: GitHub issueを読み込み、ブランチを作成して実装計画を立てる
---

## User Input

```text
$ARGUMENTS
```

**Required**: issue番号（例: `141`）

## Goal

指定されたissueを読み込み、適切なブランチに切り替え、実装計画を立案する。

## Execution Steps

### Step 1: 引数の検証

`$ARGUMENTS` をパース:

1. `--force` フラグの検出と分離
2. 残りの部分がissue番号（数値）であることを確認

**パース例**:
- `141` → issue番号: 141, force: false
- `141 --force` → issue番号: 141, force: true
- `--force 141` → issue番号: 141, force: true

未指定または非数値の場合はエラーメッセージを表示して終了:

```
⚠️ issue番号が必要です

使用方法: /start-issue <issue番号> [--force]
例: /start-issue 141
例: /start-issue 141 --force（確認なしで実行）
```

### Step 2: issueの読み込み

以下のコマンドでissue情報を取得:

```bash
gh issue view $ARGUMENTS --json number,title,body,labels,state
```

取得した情報を解析:
- **title**: issueのタイトル
- **body**: issueの本文（要件詳細）
- **labels**: ラベル一覧（ブランチタイプ決定に使用）
- **state**: issueの状態（OPEN/CLOSED）

issueが見つからない場合はエラー:

```
⚠️ Issue #$ARGUMENTS が見つかりません

gh issue view $ARGUMENTS でissueを確認してください。
```

### Step 3: ブランチタイプの決定

> ブランチタイプの決定ルールは `.claude/git-conventions.md` の「Branch Type Detection」セクションを参照してください。

**決定の優先順位:**

1. **issueのラベル** → プレフィックスにマッピング
2. **タイトル・本文のキーワード** → プレフィックスにマッピング
3. **デフォルト** → `feat/`

### Step 4: ブランチ名の生成

issueタイトルからブランチ名の説明部分を生成:

1. タイトルを小文字に変換
2. 日本語・特殊文字を削除または英語に変換
3. スペースをハイフンに置換
4. 連続ハイフンを単一に
5. 先頭・末尾のハイフンを削除
6. 40文字を超える場合は切り詰め

例:
- "Add delete draft feature" → `add-delete-draft-feature`
- "下書き削除機能の追加" → `draft-delete` (簡潔な英訳)

最終的なブランチ名: `<prefix>/<issue番号>-<説明>`
例: `feat/141-add-delete-draft`

### Step 5: ブランチの作成または切り替え

既存のブランチを確認:

```bash
git branch --list "*/$ARGUMENTS-*"
```

- **既存ブランチがある場合**: そのブランチにチェックアウト
- **既存ブランチがない場合**: 新規作成してチェックアウト

```bash
# 新規作成の場合
git checkout -b <branch-name>

# 既存ブランチの場合
git checkout <existing-branch>
```

### Step 6: 実装計画の立案

**`--force`フラグがない場合**:
プランモードに移行し、ユーザーの承認を得てから実装に進む。

**`--force`フラグがある場合**:
プランモードに移行せず、計画を立案して即座に実装を開始する。
ユーザー確認はスキップする。

以下の情報を基に実装計画を立てる:

**計画に含める内容**:
1. issueの要件サマリー
2. 影響を受けるファイルの特定
3. 実装ステップの詳細
4. テスト計画
5. 検証方法

**出力形式**:

```
## Issue #$ARGUMENTS: [タイトル]

### 要件
[issueの本文から抽出した要件]

### 実装計画
1. [ステップ1]
2. [ステップ2]
...

### テスト計画
- [テスト項目1]
- [テスト項目2]

### 検証方法
[検証手順]
```

### Step 7: 計画のissueへの記録

issue-reporterスキルの「計画立案時（Plan）」形式に従い、立案した計画をissueにコメントとして投稿する。

詳細: `.claude/skills/issue-reporter/SKILL.md`

## Error Handling

| エラー | 対応 |
|--------|------|
| issue番号未指定 | 使用方法を表示 |
| issueが存在しない | エラーメッセージを表示 |
| gh未認証 | `gh auth login` を案内 |
| ブランチ作成失敗 | 原因を表示（未コミット変更等） |

## Notes

- 既存のブランチがある場合は新規作成せず、既存ブランチに切り替える
- タイトルが日本語の場合は、適切な英語のブランチ名を生成する
- `--force`なし: プランモードでの計画立案後、ユーザーの承認を得てから実装に進む
- `--force`あり: 確認なしで即座に実装を開始する
