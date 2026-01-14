---
description: PRのCIが完了するのを待ってからマージする
---

## User Input

```text
$ARGUMENTS
```

**Required**: PR番号（例: `45`）

## Goal

指定されたPRのCIチェックが完了するまで待機し、すべてのチェックがパスしたらsquash mergeを実行する。

## Execution Steps

### Step 1: 引数の検証

`$ARGUMENTS` をパース:

1. PR番号が数値であることを確認
2. オプションフラグの検出（`--merge`, `--rebase`）

**パース例**:
- `45` → PR番号: 45, マージ方法: squash（デフォルト）
- `45 --merge` → PR番号: 45, マージ方法: merge
- `45 --rebase` → PR番号: 45, マージ方法: rebase

未指定または非数値の場合はエラーメッセージを表示して終了:

```
⚠️ PR番号が必要です

使用方法: /merge-pr <PR番号> [--merge|--rebase]
例: /merge-pr 45
例: /merge-pr 45 --merge（マージコミットを作成）
例: /merge-pr 45 --rebase（リベースマージ）
```

### Step 2: PR情報の取得・検証

以下のコマンドでPR情報を取得:

```bash
gh pr view <PR番号> --json number,title,state,mergeable,baseRefName,headRefName
```

取得した情報を検証:
- **state**: `OPEN`であること（`MERGED`や`CLOSED`でないこと）
- **mergeable**: `MERGEABLE`であること（コンフリクトがないこと）

**エラー時の対応**:

| 状態 | 対応 |
|------|------|
| PRが存在しない | `⚠️ PR #<PR番号> が見つかりません` |
| stateがMERGED | `ℹ️ PR #<PR番号> は既にマージ済みです` |
| stateがCLOSED | `⚠️ PR #<PR番号> はクローズされています` |
| mergeableがCONFLICTING | `⚠️ PR #<PR番号> にコンフリクトがあります。解消してから再実行してください` |

### Step 3: CIチェックの待機

CIチェックの状態を確認し、完了まで待機:

```bash
gh pr checks <PR番号> --watch
```

このコマンドは:
- すべてのチェックが完了するまでリアルタイムで状態を表示
- 完了後に終了コードを返す（全成功: 0, 失敗あり: 非0）

**出力例（待機中）**:
```
Some checks are still pending
NAME                    STATUS   DESCRIPTION
test                    pending  Waiting for status to be reported
lint                    pass     All checks passed
```

**チェック失敗時**:

```bash
# 失敗したチェックの詳細を確認
gh pr checks <PR番号> --json name,state,conclusion --jq '.[] | select(.conclusion == "failure" or .conclusion == "cancelled")'
```

失敗がある場合は処理を中断:

```
❌ CIチェックが失敗しました

失敗したチェック:
- test: failure
- lint: cancelled

修正してから再実行してください。
```

### Step 4: マージ可能性の最終確認

CIチェック完了後、再度PRの状態を確認:

```bash
gh pr view <PR番号> --json mergeable,mergeStateStatus
```

- **mergeStateStatus**: `CLEAN`であること

`BLOCKED`の場合はブロック理由を表示:

```
⚠️ マージがブロックされています

理由: レビュー承認が必要です

PRの要件を確認してください。
```

### Step 5: マージの実行

すべての条件を満たしたらマージを実行:

```bash
# デフォルト: squash merge
gh pr merge <PR番号> --squash --delete-branch

# --merge フラグ指定時
gh pr merge <PR番号> --merge --delete-branch

# --rebase フラグ指定時
gh pr merge <PR番号> --rebase --delete-branch
```

成功時の出力:

```
✅ PR #<PR番号> をマージしました

マージ方法: squash
ベースブランチ: main
リモートブランチ: 削除済み
```

### Step 6: 後処理

**重要**: worktreeディレクトリ内で`git worktree remove`を実行するとカレントディレクトリが削除され、その後のgitコマンドが失敗する。必ず**メインリポジトリに移動してから**後処理を行う。

#### 6.1 現在の作業ディレクトリを確認

```bash
# 現在のディレクトリがworktreeかどうかを確認
git rev-parse --git-common-dir
```

- メインリポジトリ: `.git` を返す
- worktree: メインリポジトリの`.git`への絶対パスを返す（例: `/home/user/repo/note-mcp/.git`）

#### 6.2 メインリポジトリに移動

worktreeで作業している場合は、まずメインリポジトリに移動:

```bash
# メインリポジトリのパスを取得
MAIN_REPO=$(git rev-parse --git-common-dir | sed 's/\/.git$//')

# メインリポジトリに移動
cd "$MAIN_REPO"
```

#### 6.3 mainブランチに切り替え

```bash
# mainブランチに切り替え
git checkout main

# リモートの更新を取得
git pull origin main
```

#### 6.4 worktreeの削除

マージしたブランチに対応するworktreeがある場合は削除:

```bash
# worktree一覧を取得
git worktree list

# 対応するworktreeがあるか確認（ブランチ名で検索）
# 例: feat/123-add-feature → ../note-mcp-feat-123-add-feature

# worktreeがあれば削除（メインリポジトリから実行）
git worktree remove <worktree-path>

# staleなworktree参照をクリーンアップ
git worktree prune
```

成功時:

```
🧹 worktreeを削除しました: ../note-mcp-feat-123-add-feature
```

#### 6.5 ローカルブランチの削除

worktree削除後にブランチを削除:

```bash
# マージ済みブランチを削除
git branch -d <headRefName>
```

**注意**: worktreeを先に削除しないと、ブランチが「チェックアウト中」とみなされて削除できない。

## Error Handling

| エラー | 対応 |
|--------|------|
| PR番号未指定 | 使用方法を表示 |
| PRが存在しない | エラーメッセージを表示 |
| PRがマージ済み/クローズ済み | 状態を表示して終了 |
| コンフリクトあり | 解消方法を案内 |
| CIが失敗 | 失敗したチェックを表示 |
| マージがブロック | ブロック理由を表示 |
| gh未認証 | `gh auth login`を案内 |
| worktree削除失敗 | 警告を表示するが続行 |

## Notes

- デフォルトのマージ方法は`--squash`（コミットを1つにまとめる）
- `--delete-branch`により、マージ後にリモートブランチは自動削除される
- worktreeの自動削除は`.claude/git-conventions.md`の命名規則に基づいて検出する
- CIが進行中の場合、`gh pr checks --watch`により完了まで待機する
- すべてのチェックがパスしないとマージは実行されない
- **後処理の順序が重要**: メインリポジトリに移動 → mainにチェックアウト → worktree削除 → ブランチ削除
