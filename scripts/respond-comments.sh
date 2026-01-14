#!/bin/bash
# respond-comments.sh - PRのレビューコメントに対応
#
# Usage: ./scripts/respond-comments.sh [-v|--verbose]
#
# Options:
#   -v, --verbose  途中経過を表示（ツール呼び出しを含む）
#
# worktreeディレクトリ内で実行してください。
# 現在のブランチに紐づくPRを自動検出します。

set -euo pipefail

# オプション解析
VERBOSE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "⚠️ 不明なオプション: $1"
            exit 1
            ;;
    esac
done

echo "🔍 現在のブランチからPRを検出中..."

PR_NUM=$(gh pr view --json number --jq '.number' 2>/dev/null || true)

if [[ -z "$PR_NUM" ]]; then
    echo "⚠️ 現在のブランチに紐づくPRが見つかりません"
    echo ""
    echo "先に complete-issue.sh を実行してPRを作成してください。"
    exit 1
fi

echo "📍 PRを検出: #$PR_NUM"
echo ""
echo "💬 review-pr-comments を実行中..."
echo ""

PROMPT="/review-pr-comments $PR_NUM"

if [[ "$VERBOSE" == "true" ]]; then
    claude -p "$PROMPT" --dangerously-skip-permissions --output-format stream-json --verbose 2>&1 | \
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
    exec claude -p "$PROMPT" --dangerously-skip-permissions
fi
