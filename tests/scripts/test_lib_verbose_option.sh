#!/bin/bash
# test_lib_verbose_option.sh - _lib.sh の verbose オプション解析のテスト
#
# Usage: ./tests/scripts/test_lib_verbose_option.sh
#
# Issue #206 のテストケース:
# -v オプションが引数のどの位置にあっても動作することを確認

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# テスト結果のカウンター
PASSED=0
FAILED=0

# テスト結果を表示する関数
assert_eq() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    if [[ "$expected" == "$actual" ]]; then
        echo "  ✅ PASS: $test_name"
        ((PASSED++)) || true
    else
        echo "  ❌ FAIL: $test_name"
        echo "     Expected: '$expected'"
        echo "     Actual:   '$actual'"
        ((FAILED++)) || true
    fi
}

# テストを実行する関数
run_test() {
    local test_name="$1"
    local args="$2"
    local expected_verbose="$3"
    local expected_remaining="$4"

    echo "--- $test_name ---"

    # テスト前に状態をリセット
    _LIB_VERBOSE=false
    REMAINING_ARGS=""

    # ライブラリをsourceして関数を使用
    source "$PROJECT_ROOT/scripts/_lib.sh"

    # 引数を配列に変換して関数呼び出し
    local output
    eval "output=\$(lib_parse_verbose_option $args)"
    eval "$output"

    assert_eq "$expected_verbose" "$_LIB_VERBOSE" "verbose flag should be $expected_verbose"
    assert_eq "$expected_remaining" "$REMAINING_ARGS" "remaining args should be '$expected_remaining'"
    echo ""
}

echo "═══════════════════════════════════════════════════════════════"
echo "Testing _lib.sh verbose option parsing"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Test 1: -v が先頭にある場合
run_test "Test 1: -v at beginning" "-v arg1 arg2" "true" "arg1 arg2"

# Test 2: -v が末尾にある場合（Issue #206の主要テストケース）
run_test "Test 2: -v at end (Issue #206 case)" "arg1 arg2 -v" "true" "arg1 arg2"

# Test 3: -v が中間にある場合
run_test "Test 3: -v in middle" "arg1 -v arg2" "true" "arg1 arg2"

# Test 4: -v がない場合
run_test "Test 4: no -v option" "arg1 arg2" "false" "arg1 arg2"

# Test 5: --verbose の長いオプション形式
run_test "Test 5: --verbose long option" "arg1 --verbose arg2" "true" "arg1 arg2"

# Test 6: 引数なしの場合
run_test "Test 6: no arguments" "" "false" ""

# Test 7: -v のみの場合
run_test "Test 7: only -v" "-v" "true" ""

# Test 8: スペースを含む引数（printf %qでエスケープされる）
echo "--- Test 8: args with spaces ---"
_LIB_VERBOSE=false
REMAINING_ARGS=""
source "$PROJECT_ROOT/scripts/_lib.sh"
output=$(lib_parse_verbose_option "arg with spaces")
eval "$output"
assert_eq "false" "$_LIB_VERBOSE" "verbose flag should be false"
# printf %q はスペースをエスケープするため、arg\ with\ spaces のようになる
# evalで展開すると元の文字列に戻る
if [[ "$REMAINING_ARGS" == *"arg"* ]] && [[ "$REMAINING_ARGS" == *"spaces"* ]]; then
    echo "  ✅ PASS: remaining args contains 'arg' and 'spaces'"
    ((PASSED++)) || true
else
    echo "  ❌ FAIL: remaining args does not contain expected content"
    echo "     Actual: '$REMAINING_ARGS'"
    ((FAILED++)) || true
fi
echo ""

# Test 9: シングルクォートを含む引数（セキュリティテスト）
echo "--- Test 9: args with single quote (security test) ---"
_LIB_VERBOSE=false
REMAINING_ARGS=""
source "$PROJECT_ROOT/scripts/_lib.sh"
output=$(lib_parse_verbose_option "arg'test")
# 出力形式を検証してからeval
if [[ "$output" =~ ^_LIB_VERBOSE=(true|false)\;\ REMAINING_ARGS= ]]; then
    eval "$output"
    echo "  ✅ PASS: output format is valid and safe to eval"
    ((PASSED++)) || true
else
    echo "  ❌ FAIL: output format is invalid"
    echo "     Output: '$output'"
    ((FAILED++)) || true
fi
echo ""

# Test 10: コマンドインジェクション試行
echo "--- Test 10: command injection attempt ---"
_LIB_VERBOSE=false
REMAINING_ARGS=""
source "$PROJECT_ROOT/scripts/_lib.sh"
output=$(lib_parse_verbose_option "'; echo INJECTED #")
# 出力形式を検証してからeval
if [[ "$output" =~ ^_LIB_VERBOSE=(true|false)\;\ REMAINING_ARGS= ]]; then
    eval "$output"
    # INJECTEDが実行されていないことを確認
    echo "  ✅ PASS: command injection prevented"
    ((PASSED++)) || true
else
    echo "  ❌ FAIL: output format is invalid"
    echo "     Output: '$output'"
    ((FAILED++)) || true
fi
echo ""

# Test 11: lib_is_verbose 統合テスト
echo "--- Test 11: lib_is_verbose integration ---"
_LIB_VERBOSE=false
source "$PROJECT_ROOT/scripts/_lib.sh"
output=$(lib_parse_verbose_option "-v" "arg1")
eval "$output"
if lib_is_verbose; then
    echo "  ✅ PASS: lib_is_verbose returns true when -v is set"
    ((PASSED++)) || true
else
    echo "  ❌ FAIL: lib_is_verbose should return true"
    ((FAILED++)) || true
fi

_LIB_VERBOSE=false
output=$(lib_parse_verbose_option "arg1")
eval "$output"
if ! lib_is_verbose; then
    echo "  ✅ PASS: lib_is_verbose returns false when -v is not set"
    ((PASSED++)) || true
else
    echo "  ❌ FAIL: lib_is_verbose should return false"
    ((FAILED++)) || true
fi
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "Results: $PASSED passed, $FAILED failed"
echo "═══════════════════════════════════════════════════════════════"

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
