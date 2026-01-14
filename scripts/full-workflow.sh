#!/bin/bash
# full-workflow.sh - issue対応の全ワークフローを自動実行
#
# Usage: ./scripts/full-workflow.sh [-v|--verbose] <issue番号>
# Example: ./scripts/full-workflow.sh 199
# Example: ./scripts/full-workflow.sh -v 199
#
# Options:
#   -v, --verbose  途中経過を表示（ツール呼び出しを含む）
#
# 以下を順次実行します:
# 1. worktree作成 + start-issue（計画立案・実装）
# 2. complete-issue（commit + push + PR作成）
# 3. review-pr（PRレビュー + コメント投稿）
# 4. respond-comments（レビューコメントに対応）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_NAME="note-mcp"

# オプション解析
VERBOSE=false
ISSUE_NUM=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            if [[ -z "$ISSUE_NUM" ]]; then
                ISSUE_NUM="$1"
            else
                echo "⚠️ 不明なオプション: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$ISSUE_NUM" ]]; then
    echo "⚠️ issue番号が必要です"
    echo ""
    echo "使用方法: $0 [-v|--verbose] <issue番号>"
    echo "例: $0 199"
    echo "例: $0 -v 199"
    exit 1
fi

# 数値チェック
if ! [[ "$ISSUE_NUM" =~ ^[0-9]+$ ]]; then
    echo "⚠️ issue番号は数値で指定してください: $ISSUE_NUM"
    exit 1
fi

# claude実行関数（verboseモード対応）
run_claude() {
    local prompt="$1"
    if [[ "$VERBOSE" == "true" ]]; then
        claude -p "$prompt" --dangerously-skip-permissions --output-format stream-json --verbose 2>&1 | \
            jq -r --unbuffered '
                if .type == "assistant" and .message.content then
                    .message.content[] |
                    if .type == "tool_use" then
                        "● \(.name)(\(.input | tostring | .[0:60])...)"
                    elif .type == "text" then
                        empty
                    else
                        empty
                    end
                elif .type == "result" then
                    "\n" + .result
                else
                    empty
                end
            ' 2>/dev/null
    else
        claude -p "$prompt" --dangerously-skip-permissions
    fi
}

echo "═══════════════════════════════════════════════════════════════"
echo "🚀 Full Workflow: issue #${ISSUE_NUM}"
if [[ "$VERBOSE" == "true" ]]; then
    echo "   (verbose mode)"
fi
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: worktree作成または検出
echo "📦 Step 1/4: worktree準備"
echo "───────────────────────────────────────────────────────────────"

EXISTING_DIR=$(ls "$(dirname "$PROJECT_ROOT")" 2>/dev/null | grep -E "^${PROJECT_NAME}-.*${ISSUE_NUM}.*" | head -1 || true)

if [[ -n "$EXISTING_DIR" ]]; then
    WORKTREE_PATH="$(dirname "$PROJECT_ROOT")/$EXISTING_DIR"
    echo "📁 既存のワークツリーを検出: $WORKTREE_PATH"
else
    echo "🔧 ワークツリーを作成中..."
    "$SCRIPT_DIR/add-worktree.sh" "$ISSUE_NUM"

    EXISTING_DIR=$(ls "$(dirname "$PROJECT_ROOT")" 2>/dev/null | grep -E "^${PROJECT_NAME}-.*${ISSUE_NUM}.*" | head -1 || true)

    if [[ -z "$EXISTING_DIR" ]]; then
        echo "⚠️ ワークツリーディレクトリが見つかりません"
        exit 1
    fi

    WORKTREE_PATH="$(dirname "$PROJECT_ROOT")/$EXISTING_DIR"
    echo "✅ ワークツリー作成完了: $WORKTREE_PATH"
fi

cd "$WORKTREE_PATH"
echo ""

# Step 2: start-issue（計画立案・実装）
echo "📝 Step 2/4: start-issue（計画立案・実装）"
echo "───────────────────────────────────────────────────────────────"

START_ISSUE_FILE="$WORKTREE_PATH/.claude/commands/start-issue.md"

if [[ ! -f "$START_ISSUE_FILE" ]]; then
    echo "⚠️ start-issue.md が見つかりません: $START_ISSUE_FILE"
    exit 1
fi

CONTENT="$(awk 'BEGIN{skip=0} /^---$/{skip++; next} skip>=2{print}' "$START_ISSUE_FILE")"
CONTENT_REPLACED="$(echo "$CONTENT" | sed "s/\\\$ARGUMENTS/$ISSUE_NUM --force/g")"

PROMPT_START="以下の指示に従って、issue #${ISSUE_NUM} の作業を開始してください。引数は既に ${ISSUE_NUM} --force として渡されています（プランモードをスキップ）。

${CONTENT_REPLACED}"

run_claude "$PROMPT_START"

echo ""
echo "✅ start-issue 完了"
echo ""

# Step 3: complete-issue（commit + push + PR作成）
echo "📤 Step 3/4: complete-issue（commit + push + PR作成）"
echo "───────────────────────────────────────────────────────────────"

PROMPT_COMPLETE="以下のスキルを実行してください:

/commit-commands:commit-push-pr

実装された変更をコミットし、リモートにプッシュして、プルリクエストを作成してください。"

run_claude "$PROMPT_COMPLETE"

echo ""
echo "✅ complete-issue 完了"
echo ""

# Step 4: review-pr（PRレビュー + コメント投稿）
echo "🔍 Step 4/4: review-pr（PRレビュー + コメント投稿）"
echo "───────────────────────────────────────────────────────────────"

PR_NUM=$(gh pr view --json number --jq '.number' 2>/dev/null || true)

if [[ -z "$PR_NUM" ]]; then
    echo "⚠️ PRが見つかりません。review-prをスキップします。"
else
    echo "📍 PRを検出: #$PR_NUM"

    PROMPT_REVIEW="/pr-review-toolkit:review-pr $PR_NUM PRにコメントしてください"
    run_claude "$PROMPT_REVIEW"

    echo ""
    echo "✅ review-pr 完了"
    echo ""

    # Step 5: respond-comments（レビューコメントに対応）
    echo "💬 Step 5/4: respond-comments（レビューコメントに対応）"
    echo "───────────────────────────────────────────────────────────────"

    PROMPT_RESPOND="/review-pr-comments $PR_NUM"
    run_claude "$PROMPT_RESPOND"

    echo ""
    echo "✅ respond-comments 完了"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "🎉 Full Workflow 完了: issue #${ISSUE_NUM}"
echo "═══════════════════════════════════════════════════════════════"
