#!/bin/bash
# complete-issue.sh - 実装完了後にcommit, push, PR作成を実行
#
# Usage: ./scripts/complete-issue.sh [-v|--verbose]
#
# Options:
#   -v, --verbose  途中経過を表示（ツール呼び出しを含む）
#
# worktreeディレクトリ内で実行してください。

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

echo "🚀 commit-push-pr を実行中..."
echo ""

PROMPT="以下のスキルを実行してください:

/commit-commands:commit-push-pr

実装された変更をコミットし、リモートにプッシュして、プルリクエストを作成してください。"

if [[ "$VERBOSE" == "true" ]]; then
    # stream-jsonで途中経過を表示しながら、最終結果も表示
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
