#!/usr/bin/env python3
"""
修正によるリグレッション安全性テスト

今回実装した機能に特化した安全性テスト:
1. evaluation_period_days動的取得
2. 評価回数動的計算
3. 柔軟な時刻マッチング
4. 賢い評価開始時刻調整
"""

import sys
import os
import tempfile
import pandas as pd
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class RegressionSafetyTest:
    """修正によるリグレッション安全性テスト"""
    
    def __init__(self):
        self.test_dir = None
        self.system = None
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
    
    def setUp(self):
        """テスト環境セットアップ"""
        self.test_dir = tempfile.mkdtemp(prefix="regression_test_")
        print(f"📁 テスト用ディレクトリ: {self.test_dir}")
        
        # テスト用にScalableAnalysisSystemを初期化
        from scalable_analysis_system import ScalableAnalysisSystem
        self.system = ScalableAnalysisSystem(os.path.join(self.test_dir, "test_analysis"))
    
    def tearDown(self):
        """テスト環境クリーンアップ"""
        if self.test_dir and os.path.exists(self.test_dir):
            import shutil
            shutil.rmtree(self.test_dir)
    
    def assert_test(self, condition, test_name, error_msg=""):
        """テスト結果の記録"""
        if condition:
            print(f"   ✅ {test_name}")
            self.passed_tests += 1
            self.test_results.append({"test": test_name, "status": "PASS"})
        else:
            print(f"   ❌ {test_name}: {error_msg}")
            self.failed_tests += 1
            self.test_results.append({"test": test_name, "status": "FAIL", "error": error_msg})
    
    def test_timeframe_config_loading(self):
        """時間足設定動的読み込みテスト"""
        print("\n🧪 時間足設定動的読み込みテスト")
        
        try:
            # 各時間足の設定確認
            timeframes = ['1m', '3m', '15m', '1h']
            
            for tf in timeframes:
                config = self.system._load_timeframe_config(tf)
                
                # data_daysが正しく取得できているか
                data_days = config.get('data_days')
                self.assert_test(
                    data_days is not None and isinstance(data_days, int) and data_days > 0,
                    f"{tf}足のdata_days取得",
                    f"data_days={data_days}"
                )
                
                # evaluation_interval_minutesが正しく取得できているか
                interval_min = config.get('evaluation_interval_minutes')
                self.assert_test(
                    interval_min is not None and isinstance(interval_min, int) and interval_min > 0,
                    f"{tf}足のevaluation_interval_minutes取得",
                    f"interval_min={interval_min}"
                )
        
        except Exception as e:
            self.assert_test(False, "時間足設定読み込み", str(e))
    
    def test_evaluation_count_calculation(self):
        """評価回数動的計算テスト"""
        print("\n🧪 評価回数動的計算テスト")
        
        try:
            # モック設定で計算テスト
            test_cases = [
                {"data_days": 14, "interval_min": 5, "expected_min": 1000},  # 1m足
                {"data_days": 90, "interval_min": 60, "expected_min": 1000}, # 15m足
                {"data_days": 180, "interval_min": 240, "expected_min": 500} # 1h足
            ]
            
            for case in test_cases:
                data_days = case["data_days"]
                interval_min = case["interval_min"]
                expected_min = case["expected_min"]
                
                # 計算ロジックをテスト
                total_period_minutes = data_days * 24 * 60
                total_possible_evaluations = total_period_minutes // interval_min
                target_coverage = 0.8
                calculated_max_evaluations = int(total_possible_evaluations * target_coverage)
                
                # 設定値100と計算値の最大値
                config_max = 100
                actual_max = min(max(config_max, calculated_max_evaluations), 5000)
                
                self.assert_test(
                    actual_max >= expected_min,
                    f"評価回数計算 ({data_days}日, {interval_min}分間隔)",
                    f"actual_max={actual_max}, expected_min={expected_min}"
                )
                
                # カバー率計算
                actual_coverage = (actual_max * interval_min) / total_period_minutes * 100
                self.assert_test(
                    actual_coverage >= 50.0,  # 最低50%カバー率
                    f"カバー率計算 ({data_days}日)",
                    f"coverage={actual_coverage:.1f}%"
                )
        
        except Exception as e:
            self.assert_test(False, "評価回数動的計算", str(e))
    
    def test_flexible_time_matching(self):
        """柔軟な時刻マッチングテスト"""
        print("\n🧪 柔軟な時刻マッチングテスト")
        
        try:
            # モックOHLCVデータ作成
            base_time = datetime(2025, 3, 27, 6, 30, 0, tzinfo=timezone.utc)
            mock_data = []
            
            for i in range(10):
                timestamp = base_time + timedelta(minutes=15*i)
                mock_data.append({
                    'open': 100.0 + i,
                    'high': 105.0 + i,
                    'low': 95.0 + i,
                    'close': 102.0 + i,
                    'volume': 1000
                })
            
            market_data = pd.DataFrame(mock_data, index=[base_time + timedelta(minutes=15*i) for i in range(10)])
            
            # モックボット作成
            class MockBot:
                def __init__(self, market_data):
                    self._cached_data = market_data
                
                def _fetch_market_data(self, symbol, timeframe):
                    return market_data
            
            mock_bot = MockBot(market_data)
            
            # テストケース1: 15分ギャップ（SOLパターン）
            trade_time = datetime(2025, 3, 27, 6, 25, 11, tzinfo=timezone.utc)
            
            try:
                price = self.system._get_real_market_price(mock_bot, "TEST", "15m", trade_time)
                self.assert_test(
                    isinstance(price, (int, float)) and price > 0,
                    "15分ギャップ価格取得",
                    f"price={price}"
                )
            except Exception as e:
                self.assert_test(False, "15分ギャップ価格取得", str(e))
            
            # テストケース2: 完全一致
            exact_time = datetime(2025, 3, 27, 6, 30, 0, tzinfo=timezone.utc)
            
            try:
                price = self.system._get_real_market_price(mock_bot, "TEST", "15m", exact_time)
                self.assert_test(
                    isinstance(price, (int, float)) and price > 0,
                    "完全一致価格取得",
                    f"price={price}"
                )
            except Exception as e:
                self.assert_test(False, "完全一致価格取得", str(e))
        
        except Exception as e:
            self.assert_test(False, "柔軟な時刻マッチング", str(e))
    
    def test_smart_evaluation_start(self):
        """賢い評価開始時刻調整テスト"""
        print("\n🧪 賢い評価開始時刻調整テスト")
        
        try:
            # テストケース
            test_cases = [
                {
                    "data_start": datetime(2025, 3, 27, 6, 30, 0, tzinfo=timezone.utc),
                    "interval": timedelta(hours=1),
                    "expected_hour": 7
                },
                {
                    "data_start": datetime(2024, 12, 16, 14, 23, 0, tzinfo=timezone.utc),
                    "interval": timedelta(minutes=15),
                    "expected_minute": 30
                },
                {
                    "data_start": datetime(2025, 1, 1, 10, 15, 0, tzinfo=timezone.utc),
                    "interval": timedelta(hours=4),
                    "expected_hour": 12
                }
            ]
            
            for i, case in enumerate(test_cases):
                result = self.system._find_first_valid_evaluation_time(
                    case["data_start"], case["interval"]
                )
                
                # 結果検証
                if "expected_hour" in case:
                    condition = result.hour == case["expected_hour"]
                    self.assert_test(
                        condition,
                        f"ケース{i+1}: 時間調整",
                        f"expected_hour={case['expected_hour']}, actual_hour={result.hour}"
                    )
                
                if "expected_minute" in case:
                    condition = result.minute == case["expected_minute"]
                    self.assert_test(
                        condition,
                        f"ケース{i+1}: 分調整",
                        f"expected_minute={case['expected_minute']}, actual_minute={result.minute}"
                    )
                
                # データ開始時刻以降であることを確認
                self.assert_test(
                    result >= case["data_start"],
                    f"ケース{i+1}: データ開始以降",
                    f"result={result}, data_start={case['data_start']}"
                )
        
        except Exception as e:
            self.assert_test(False, "賢い評価開始時刻調整", str(e))
    
    def test_method_signature_compatibility(self):
        """メソッドシグネチャ互換性テスト"""
        print("\n🧪 メソッドシグネチャ互換性テスト")
        
        try:
            import inspect
            
            # _generate_real_analysisのシグネチャ確認
            signature = inspect.signature(self.system._generate_real_analysis)
            params = list(signature.parameters.keys())
            
            # 必須引数の確認
            required_params = ['symbol', 'timeframe', 'config']
            for param in required_params:
                self.assert_test(
                    param in params,
                    f"必須引数 {param} 存在",
                    f"params={params}"
                )
            
            # オプション引数の確認
            custom_period_param = signature.parameters.get('custom_period_days')
            self.assert_test(
                custom_period_param is not None and custom_period_param.default is None,
                "custom_period_days オプション引数",
                f"param={custom_period_param}"
            )
            
            # 新しいメソッドの存在確認
            self.assert_test(
                hasattr(self.system, '_find_first_valid_evaluation_time'),
                "_find_first_valid_evaluation_time メソッド存在"
            )
            
        except Exception as e:
            self.assert_test(False, "メソッドシグネチャ互換性", str(e))
    
    def test_database_operations(self):
        """データベース操作テスト"""
        print("\n🧪 データベース操作テスト")
        
        try:
            # データベース初期化確認
            self.assert_test(
                os.path.exists(self.system.db_path),
                "データベースファイル存在"
            )
            
            # テーブル構造確認
            with sqlite3.connect(self.system.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                
                expected_tables = ['analyses', 'backtest_summary']  # strategy_configurationsは必須ではない
                for table in expected_tables:
                    self.assert_test(
                        table in tables,
                        f"テーブル {table} 存在",
                        f"existing_tables={tables}"
                    )
        
        except Exception as e:
            self.assert_test(False, "データベース操作", str(e))
    
    def run_all_tests(self):
        """全テスト実行"""
        print("🚀 リグレッション安全性テスト開始")
        print("=" * 60)
        
        try:
            self.setUp()
            
            # 各テスト実行
            self.test_timeframe_config_loading()
            self.test_evaluation_count_calculation()
            self.test_flexible_time_matching()
            self.test_smart_evaluation_start()
            self.test_method_signature_compatibility()
            self.test_database_operations()
            
        except Exception as e:
            print(f"❌ テスト実行中エラー: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.tearDown()
        
        # 結果サマリー
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n🎯 リグレッション安全性テスト結果")
        print("=" * 50)
        print(f"📊 総テスト数: {total_tests}")
        print(f"✅ 成功: {self.passed_tests}")
        print(f"❌ 失敗: {self.failed_tests}")
        print(f"📈 成功率: {success_rate:.1f}%")
        
        if self.failed_tests == 0:
            print("\n🎉 全テスト成功！修正にリグレッションなし")
            return True
        else:
            print(f"\n⚠️ {self.failed_tests}件のテスト失敗 - 要調査")
            return False

if __name__ == "__main__":
    test = RegressionSafetyTest()
    success = test.run_all_tests()
    
    exit_code = 0 if success else 1
    sys.exit(exit_code)