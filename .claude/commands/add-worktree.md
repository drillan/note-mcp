---
description: issue番号を指定してgit worktreeを新規作成する
---

## User Input

```text
$ARGUMENTS
```

**Required**: issue番号（例: `141`）

## Goal

指定されたissue番号からブランチ名を自動生成し、新規ワークツリーを作成する。

## Naming Convention

> ブランチ・ワークツリーの命名規則は `.claude/git-conventions.md` を参照してください。

## Execution Steps

### Step 1: 引数の検証

`$ARGUMENTS` がissue番号（数値）であることを確認。
未指定または非数値の場合はエラーメッセージを表示して終了:

```
⚠️ issue番号が必要です

使用方法: /add-worktree <issue番号>
例: /add-worktree 141
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

### Step 5: ワークツリーディレクトリ名の生成

ブランチ名からワークツリーディレクトリ名を生成:

1. ブランチ名を取得（例: `feat/141-add-delete-draft`）
2. `/` を `-` に置換（例: `feat-141-add-delete-draft`）
3. プロジェクト名をプレフィックスに追加
4. 親ディレクトリに配置

**結果**: `../note-mcp-feat-141-add-delete-draft`

### Step 6: 既存ワークツリーの確認

```bash
git worktree list
```

同じブランチのワークツリーが既に存在する場合はエラー:

```
⚠️ このブランチのワークツリーは既に存在します

既存のワークツリー: ../note-mcp-feat-141-add-delete-draft

既存のワークツリーを使用するか、削除してから再実行してください:
  git worktree remove ../note-mcp-feat-141-add-delete-draft
```

### Step 7: ワークツリーの作成

`-b` オプションを使用して新規ブランチとワークツリーを同時作成:

```bash
git worktree add -b <ブランチ名> <ワークツリーディレクトリ>
```

例:
```bash
git worktree add -b feat/141-add-delete-draft ../note-mcp-feat-141-add-delete-draft
```

### Step 8: 結果の報告

成功時:

```
✅ ワークツリーを作成しました

Issue: #141 - [issueタイトル]
ブランチ: feat/141-add-delete-draft
ディレクトリ: ../note-mcp-feat-141-add-delete-draft

作業を開始するには:
  cd ../note-mcp-feat-141-add-delete-draft
```

## Error Handling

| エラー | 対応 |
|--------|------|
| issue番号未指定 | 使用方法を表示 |
| issueが存在しない | エラーメッセージを表示 |
| gh未認証 | `gh auth login` を案内 |
| ワークツリーが既存 | 既存パスを表示 |
| ディレクトリ作成失敗 | 原因を表示 |

## start-issueとの違い

| 項目 | start-issue | add-worktree |
|------|-------------|--------------|
| ブランチ作成 | メインリポジトリに作成 | ワークツリーに作成 |
| 作業ディレクトリ | メインリポジトリ | 新規ワークツリー |
| プランモード | 移行する | 移行しない |
| issue報告 | あり | なし |

## Notes

- ワークツリー内では通常のgit操作が可能
- 作業完了後は `git worktree remove` で削除可能
- メインリポジトリと並行して作業が可能
