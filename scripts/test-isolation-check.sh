#!/bin/bash
# テスト隔離チェックスクリプト
# 開発者のローカル環境でも実行可能

set -e

echo "🔒 Test Database Isolation Checker"
echo "=================================="

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

FAILED=0

# 1. 本番DB使用の検出
echo ""
echo "🔍 Step 1: Checking for production database usage..."

PROD_DB_FILES=$(find . -name "test_*.py" -o -path "./tests_organized/**/*.py" | xargs grep -l "large_scale_analysis/analysis.db\|execution_logs.db" 2>/dev/null || true)

if [ ! -z "$PROD_DB_FILES" ]; then
    echo "❌ FOUND: Tests using production database paths:"
    echo "$PROD_DB_FILES"
    echo ""
    echo "🔧 These files need to be migrated to use BaseTest or environment variables"
    FAILED=1
else
    echo "✅ No production database usage found"
fi

# 2. BaseTest使用チェック
echo ""
echo "🔍 Step 2: Checking BaseTest usage..."

NON_BASETEST_FILES=$(find tests_organized/ -name "test_*.py" -type f | while read file; do
    if ! grep -q "from.*base_test import BaseTest" "$file" 2>/dev/null; then
        if grep -q "class.*Test" "$file" 2>/dev/null; then
            echo "$file"
        fi
    fi
done)

if [ ! -z "$NON_BASETEST_FILES" ]; then
    echo "⚠️ FOUND: Test classes not using BaseTest:"
    echo "$NON_BASETEST_FILES"
    echo ""
    echo "💡 Consider migrating these to BaseTest for better isolation"
else
    echo "✅ All test classes use BaseTest"
fi

# 3. 隔離テスト実行
echo ""
echo "🔍 Step 3: Running isolated tests..."

if [ -f "test_strategy_api_isolated.py" ]; then
    echo "Running isolated strategy API test..."
    python test_strategy_api_isolated.py
    if [ $? -eq 0 ]; then
        echo "✅ Isolated API test passed"
    else
        echo "❌ Isolated API test failed"
        FAILED=1
    fi
else
    echo "⚠️ Isolated API test not found"
fi

# 4. BaseTest系テスト実行
echo ""
echo "Running BaseTest-based tests..."

BASETEST_DIRS="tests_organized/strategy_customization"

for dir in $BASETEST_DIRS; do
    if [ -d "$dir" ]; then
        echo "Testing directory: $dir"
        cd "$dir"
        
        for test_file in test_*.py; do
            if [ -f "$test_file" ] && grep -q "BaseTest" "$test_file" 2>/dev/null; then
                echo "  Running $test_file..."
                python "$test_file"
                if [ $? -eq 0 ]; then
                    echo "  ✅ $test_file passed"
                else
                    echo "  ❌ $test_file failed"
                    FAILED=1
                fi
            fi
        done
        
        cd "$PROJECT_ROOT"
    fi
done

# 5. 本番DB保護確認
echo ""
echo "🔍 Step 4: Verifying production database protection..."

if [ -f "large_scale_analysis/analysis.db" ]; then
    # 本番DBが存在する場合、テストデータ混入チェック
    echo "Production database exists, checking for test data contamination..."
    
    TEST_DATA_COUNT=$(sqlite3 "large_scale_analysis/analysis.db" "SELECT COUNT(*) FROM analyses WHERE symbol LIKE 'TEST%' OR symbol LIKE '%test%';" 2>/dev/null || echo "0")
    
    if [ "$TEST_DATA_COUNT" -gt 0 ]; then
        echo "⚠️ WARNING: $TEST_DATA_COUNT test records found in production database"
        echo "This suggests test isolation may have been compromised"
    else
        echo "✅ No test data contamination detected"
    fi
else
    echo "✅ No production database found (clean environment)"
fi

# 6. 結果サマリー
echo ""
echo "=================================="
echo "🎯 Test Isolation Check Results"
echo "=================================="

if [ $FAILED -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED"
    echo "Test isolation is properly maintained"
    exit 0
else
    echo "❌ SOME CHECKS FAILED"
    echo "Test isolation needs attention"
    echo ""
    echo "📋 Next steps:"
    echo "1. Review test_isolation_guide.md"
    echo "2. Use test_basetest_template.py for migrations"
    echo "3. Run this script again after fixes"
    exit 1
fi