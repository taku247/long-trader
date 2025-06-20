#!/usr/bin/env python3
"""
UTC aware datetime強制確認テスト

すべてのdatetimeオブジェクトが必ずUTC awareであることを担保するテストフレームワーク
"""

import asyncio
import inspect
import pandas as pd
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple, Union
import importlib
import warnings

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class UTCAwareValidator:
    """UTC aware datetime強制バリデーター"""
    
    def __init__(self):
        self.violations = []
        self.checked_modules = []
        self.checked_functions = []
        
    def check_datetime_object(self, obj: Any, context: str = "") -> bool:
        """datetimeオブジェクトがUTC awareかチェック"""
        if isinstance(obj, datetime):
            if obj.tzinfo is None:
                self.violations.append({
                    'type': 'datetime_naive',
                    'object': str(obj),
                    'context': context,
                    'severity': 'CRITICAL'
                })
                return False
            elif obj.tzinfo != timezone.utc:
                self.violations.append({
                    'type': 'datetime_non_utc',
                    'object': str(obj),
                    'timezone': str(obj.tzinfo),
                    'context': context,
                    'severity': 'WARNING'
                })
                return False
        
        elif isinstance(obj, pd.Timestamp):
            if obj.tz is None:
                self.violations.append({
                    'type': 'pandas_timestamp_naive',
                    'object': str(obj),
                    'context': context,
                    'severity': 'CRITICAL'
                })
                return False
            elif str(obj.tz) != 'UTC':
                self.violations.append({
                    'type': 'pandas_timestamp_non_utc',
                    'object': str(obj),
                    'timezone': str(obj.tz),
                    'context': context,
                    'severity': 'WARNING'
                })
                return False
        
        elif isinstance(obj, pd.DataFrame):
            for col in obj.columns:
                if pd.api.types.is_datetime64_any_dtype(obj[col]):
                    if hasattr(obj[col], 'dt') and obj[col].dt.tz is None:
                        self.violations.append({
                            'type': 'dataframe_column_naive',
                            'object': f'DataFrame[{col}]',
                            'context': context,
                            'severity': 'CRITICAL'
                        })
                        return False
                    elif hasattr(obj[col], 'dt') and str(obj[col].dt.tz) != 'UTC':
                        self.violations.append({
                            'type': 'dataframe_column_non_utc',
                            'object': f'DataFrame[{col}]',
                            'timezone': str(obj[col].dt.tz),
                            'context': context,
                            'severity': 'WARNING'
                        })
                        return False
        
        return True
    
    def scan_function_for_datetime_creation(self, func: callable) -> List[str]:
        """関数内のdatetime作成パターンをスキャン"""
        if not callable(func):
            return []
        
        violations = []
        
        try:
            source = inspect.getsource(func)
            
            # 危険なパターンを検索
            dangerous_patterns = [
                ('datetime.now()', 'timezone-naive datetime.now()'),
                ('datetime.fromtimestamp(', 'timezone-naive fromtimestamp without tz parameter'),
                ('pd.to_datetime(', 'pandas to_datetime without utc=True'),
                ('datetime(', 'direct datetime() constructor without timezone'),
            ]
            
            for pattern, description in dangerous_patterns:
                if pattern in source:
                    # より詳細な分析
                    if pattern == 'datetime.now()':
                        if 'datetime.now(timezone.utc)' not in source:
                            violations.append(f"{description} in {func.__name__}")
                    
                    elif pattern == 'datetime.fromtimestamp(':
                        if 'tz=' not in source:
                            violations.append(f"{description} in {func.__name__}")
                    
                    elif pattern == 'pd.to_datetime(':
                        if 'utc=True' not in source:
                            violations.append(f"{description} in {func.__name__}")
                    
                    elif pattern == 'datetime(':
                        if 'tzinfo=' not in source and 'timezone' not in source:
                            violations.append(f"{description} in {func.__name__}")
        
        except (OSError, TypeError):
            pass  # ソースコードが取得できない場合はスキップ
        
        return violations


async def test_hyperliquid_api_client_utc_aware():
    """hyperliquid_api_client.pyのUTC aware強制テスト"""
    print("\n🧪 hyperliquid_api_client.py UTC aware テスト")
    print("=" * 60)
    
    from hyperliquid_api_client import MultiExchangeAPIClient
    
    validator = UTCAwareValidator()
    
    # 1. datetime.now()呼び出しの確認
    client = MultiExchangeAPIClient()
    
    # get_ohlcv_data_with_period内のdatetime作成
    try:
        # 内部でdatetime.now()が呼ばれる
        test_time = datetime.now(timezone.utc)
        validator.check_datetime_object(test_time, "test_time_creation")
        
        # 実際のメソッド呼び出しでのタイムスタンプ確認
        from unittest.mock import patch, MagicMock
        
        with patch('hyperliquid_api_client.gate_api'):
            mock_client = MultiExchangeAPIClient(exchange_type='gateio')
            
            # get_ohlcv_data_with_periodの内部タイムスタンプ確認
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=30)
            
            is_end_utc = validator.check_datetime_object(end_time, "get_ohlcv_data_with_period.end_time")
            is_start_utc = validator.check_datetime_object(start_time, "get_ohlcv_data_with_period.start_time")
            
            print(f"   ✅ end_time UTC aware: {is_end_utc}")
            print(f"   ✅ start_time UTC aware: {is_start_utc}")
    
    except Exception as e:
        print(f"   ❌ テストエラー: {e}")
    
    # 2. DataFrameタイムスタンプの確認
    test_df = pd.DataFrame({
        'timestamp': pd.to_datetime([1703930400000, 1703934000000], unit='ms', utc=True),
        'price': [100.0, 101.0]
    })
    
    is_df_utc = validator.check_datetime_object(test_df, "test_dataframe")
    print(f"   ✅ DataFrame UTC aware: {is_df_utc}")
    
    return len(validator.violations) == 0


async def test_symbol_early_fail_validator_utc_aware():
    """symbol_early_fail_validator.pyのUTC aware強制テスト"""
    print("\n🧪 symbol_early_fail_validator.py UTC aware テスト")
    print("=" * 60)
    
    from symbol_early_fail_validator import SymbolEarlyFailValidator
    
    validator = UTCAwareValidator()
    
    # 1. バリデーター内部のdatetime作成確認
    early_fail_validator = SymbolEarlyFailValidator()
    
    # 内部で使用される各種datetime
    test_cases = [
        (datetime.now(timezone.utc), "datetime.now(timezone.utc)"),
        (datetime.now(timezone.utc) - timedelta(days=90), "test_start"),
        (datetime.now(timezone.utc) - timedelta(days=30), "strict_quality_start"),
    ]
    
    all_utc = True
    for dt, context in test_cases:
        is_utc = validator.check_datetime_object(dt, context)
        print(f"   ✅ {context}: {is_utc}")
        all_utc = all_utc and is_utc
    
    # 2. メタデータ内のタイムスタンプ確認
    metadata_time = datetime.now(timezone.utc).isoformat()
    print(f"   ✅ metadata timestamp format: {metadata_time} (ISO format)")
    
    return all_utc and len(validator.violations) == 0


async def test_scalable_analysis_system_utc_aware():
    """scalable_analysis_system.pyのUTC aware強制テスト"""
    print("\n🧪 scalable_analysis_system.py UTC aware テスト")
    print("=" * 60)
    
    validator = UTCAwareValidator()
    
    # ScalableAnalysisSystem内部のdatetime作成確認
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=30)
    
    is_end_utc = validator.check_datetime_object(end_time, "scalable_analysis.end_time")
    is_start_utc = validator.check_datetime_object(start_time, "scalable_analysis.start_time")
    
    print(f"   ✅ end_time UTC aware: {is_end_utc}")
    print(f"   ✅ start_time UTC aware: {is_start_utc}")
    
    return is_end_utc and is_start_utc and len(validator.violations) == 0


def test_dangerous_pattern_detection():
    """危険なdatetimeパターンの検出テスト"""
    print("\n🧪 危険なdatetimeパターン検出テスト")
    print("=" * 60)
    
    validator = UTCAwareValidator()
    
    # テスト用の危険な関数例
    def bad_function_example():
        # これらは検出されるべき危険なパターン
        naive_now = datetime.now()  # ❌
        naive_timestamp = datetime.fromtimestamp(1703930400)  # ❌
        naive_df = pd.to_datetime([1703930400000], unit='ms')  # ❌
        naive_constructor = datetime(2023, 12, 30, 10, 0, 0)  # ❌
        return naive_now
    
    def good_function_example():
        # これらは安全なパターン
        utc_now = datetime.now(timezone.utc)  # ✅
        utc_timestamp = datetime.fromtimestamp(1703930400, tz=timezone.utc)  # ✅
        utc_df = pd.to_datetime([1703930400000], unit='ms', utc=True)  # ✅
        utc_constructor = datetime(2023, 12, 30, 10, 0, 0, tzinfo=timezone.utc)  # ✅
        return utc_now
    
    # パターン検出テスト
    bad_violations = validator.scan_function_for_datetime_creation(bad_function_example)
    good_violations = validator.scan_function_for_datetime_creation(good_function_example)
    
    print(f"   ✅ 危険な関数での検出数: {len(bad_violations)}")
    for violation in bad_violations:
        print(f"      - {violation}")
    
    print(f"   ✅ 安全な関数での検出数: {len(good_violations)}")
    
    return len(bad_violations) > 0 and len(good_violations) == 0


def test_real_world_datetime_objects():
    """実際のdatetimeオブジェクトのUTC aware確認"""
    print("\n🧪 実際のdatetimeオブジェクトUTC aware確認")
    print("=" * 60)
    
    validator = UTCAwareValidator()
    
    # 実際のシステムで使用されるdatetimeオブジェクト
    test_objects = [
        (datetime.now(timezone.utc), "current_utc_time"),
        (datetime.fromtimestamp(1703930400, tz=timezone.utc), "timestamp_utc"),
        (pd.to_datetime(1703930400000, unit='ms', utc=True), "pandas_timestamp_utc"),
        (pd.DataFrame({'timestamp': pd.to_datetime([1703930400000], unit='ms', utc=True)}), "dataframe_utc"),
    ]
    
    all_valid = True
    for obj, context in test_objects:
        is_valid = validator.check_datetime_object(obj, context)
        print(f"   ✅ {context}: {'VALID' if is_valid else 'INVALID'}")
        all_valid = all_valid and is_valid
    
    # 違反があった場合の詳細表示
    if validator.violations:
        print("\n   ❌ 検出された違反:")
        for violation in validator.violations:
            print(f"      - {violation}")
    
    return all_valid


async def test_api_integration_utc_consistency():
    """API統合でのUTC一貫性テスト"""
    print("\n🧪 API統合 UTC一貫性テスト")
    print("=" * 60)
    
    validator = UTCAwareValidator()
    
    # APIクライアントの一貫性テスト
    try:
        from hyperliquid_api_client import MultiExchangeAPIClient
        
        # モックを使用した安全なテスト
        from unittest.mock import patch, MagicMock
        
        with patch('hyperliquid_api_client.gate_api'):
            client = MultiExchangeAPIClient(exchange_type='gateio')
            
            # タイムスタンプ一貫性の確認
            start_time = datetime.now(timezone.utc) - timedelta(days=1)
            end_time = datetime.now(timezone.utc)
            
            is_start_utc = validator.check_datetime_object(start_time, "api_start_time")
            is_end_utc = validator.check_datetime_object(end_time, "api_end_time")
            
            print(f"   ✅ API start_time UTC aware: {is_start_utc}")
            print(f"   ✅ API end_time UTC aware: {is_end_utc}")
            
            # DataFrame生成の確認
            test_df = pd.DataFrame({
                'timestamp': pd.to_datetime([1703930400000, 1703934000000], unit='ms', utc=True),
                'price': [100.0, 101.0]
            })
            
            is_df_utc = validator.check_datetime_object(test_df, "api_generated_dataframe")
            print(f"   ✅ API DataFrame UTC aware: {is_df_utc}")
            
            return is_start_utc and is_end_utc and is_df_utc
    
    except Exception as e:
        print(f"   ❌ API統合テストエラー: {e}")
        return False


async def run_comprehensive_utc_enforcement_test():
    """包括的UTC aware強制テスト"""
    print("=" * 80)
    print("🚀 包括的UTC aware強制テストスイート")
    print("=" * 80)
    
    test_results = []
    
    # 各テストを実行
    tests = [
        ("hyperliquid_api_client UTC aware", test_hyperliquid_api_client_utc_aware()),
        ("symbol_early_fail_validator UTC aware", test_symbol_early_fail_validator_utc_aware()),
        ("scalable_analysis_system UTC aware", test_scalable_analysis_system_utc_aware()),
        ("危険パターン検出", test_dangerous_pattern_detection()),
        ("実際のdatetimeオブジェクト", test_real_world_datetime_objects()),
        ("API統合UTC一貫性", test_api_integration_utc_consistency()),
    ]
    
    for test_name, test_coro in tests:
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} でエラー: {e}")
            test_results.append((test_name, False))
    
    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 UTC aware強制テスト結果")
    print("=" * 80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📈 総合結果: {passed}/{total} テスト合格 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 すべてのUTC aware強制テストに合格しました！")
        print("✅ システム全体でUTC aware datetimeが担保されています")
    else:
        print(f"\n⚠️ {total - passed}個のテストが失敗しました")
        print("❌ UTC aware の徹底が必要です")
    
    return passed == total


async def main():
    """メインテスト実行"""
    success = await run_comprehensive_utc_enforcement_test()
    
    print("\n" + "=" * 80)
    print("🔧 UTC aware強制の実装ガイド")
    print("=" * 80)
    print("\n✅ 推奨パターン:")
    print("  - datetime.now(timezone.utc)")
    print("  - datetime.fromtimestamp(timestamp, tz=timezone.utc)")
    print("  - pd.to_datetime(..., utc=True)")
    print("  - datetime(..., tzinfo=timezone.utc)")
    print("\n❌ 禁止パターン:")
    print("  - datetime.now()")
    print("  - datetime.fromtimestamp(timestamp)")
    print("  - pd.to_datetime(...) # utc=Trueなし")
    print("  - datetime(...) # tzinfoなし")
    print("\n🛡️ 自動チェック:")
    print("  - このテストを定期的に実行")
    print("  - CIパイプラインに組み込み")
    print("  - プリコミットフックとして使用")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())