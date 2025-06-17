#!/usr/bin/env python3
"""
フラグベース分析の包括テスト

リアルタイム分析かバックテスト分析かを is_realtime フラグで明示的に指定し、
それぞれの場合で適切な価格取得が行われることを確認する。
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.leverage_decision_engine import SimpleMarketContextAnalyzer


class TestFlagBasedAnalysis(unittest.TestCase):
    """フラグベース分析テスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.analyzer = SimpleMarketContextAnalyzer()
        
        # 価格が時系列で変化するテストデータ
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        self.test_data = pd.DataFrame({
            'timestamp': [base_time + timedelta(hours=i) for i in range(10)],
            'open': [1000 + i * 10 for i in range(10)],       # 1000, 1010, 1020, ...
            'close': [1005 + i * 10 for i in range(10)],      # 1005, 1015, 1025, ...
            'high': [1008 + i * 10 for i in range(10)],
            'low': [998 + i * 10 for i in range(10)],
            'volume': [10000] * 10
        })
        
        print(f"\n🧪 テストデータ準備完了:")
        print(f"   データ範囲: {len(self.test_data)}件")
        print(f"   価格範囲: open {self.test_data['open'].min()}-{self.test_data['open'].max()}")
        print(f"   価格範囲: close {self.test_data['close'].min()}-{self.test_data['close'].max()}")
    
    def test_realtime_analysis_flag(self):
        """リアルタイム分析フラグのテスト"""
        print(f"\n🔴 リアルタイム分析テスト:")
        
        # is_realtime=True で実行
        result = self.analyzer.analyze_market_phase(
            self.test_data, 
            is_realtime=True
        )
        
        # 最新のclose価格が使用されることを確認
        expected_price = self.test_data['close'].iloc[-1]  # 1095
        self.assertEqual(result.current_price, expected_price)
        
        print(f"   ✅ リアルタイム分析: current_price={result.current_price}")
        print(f"   ✅ 期待値: {expected_price}")
        print(f"   ✅ 一致: {result.current_price == expected_price}")
    
    def test_backtest_analysis_flag(self):
        """バックテスト分析フラグのテスト"""
        print(f"\n🔵 バックテスト分析テスト:")
        
        # 特定の時刻を指定
        target_time = self.test_data['timestamp'].iloc[5]  # 5番目のローソク足
        
        # is_realtime=False で実行
        result = self.analyzer.analyze_market_phase(
            self.test_data, 
            target_timestamp=target_time,
            is_realtime=False
        )
        
        # 該当時刻のopen価格が使用されることを確認
        expected_price = self.test_data['open'].iloc[5]  # 1050
        self.assertEqual(result.current_price, expected_price)
        
        print(f"   ✅ バックテスト分析: current_price={result.current_price}")
        print(f"   ✅ 期待値: {expected_price}")
        print(f"   ✅ 一致: {result.current_price == expected_price}")
    
    def test_backtest_without_timestamp_error(self):
        """バックテストでのタイムスタンプ必須エラー"""
        print(f"\n⚠️ バックテストタイムスタンプ必須テスト:")
        
        # is_realtime=False でtarget_timestampなし
        with self.assertRaises(ValueError) as context:
            self.analyzer.analyze_market_phase(
                self.test_data, 
                is_realtime=False  # target_timestampなし
            )
        
        # エラーメッセージの確認
        error_msg = str(context.exception)
        self.assertIn("バックテスト分析ではtarget_timestampが必須", error_msg)
        
        print(f"   ✅ エラー発生確認: {error_msg}")
    
    def test_price_difference_between_modes(self):
        """リアルタイムとバックテストの価格差確認"""
        print(f"\n🔄 価格差比較テスト:")
        
        # リアルタイム分析
        realtime_result = self.analyzer.analyze_market_phase(
            self.test_data, 
            is_realtime=True
        )
        
        # バックテスト分析（最初の時刻）
        first_time = self.test_data['timestamp'].iloc[0]
        backtest_result = self.analyzer.analyze_market_phase(
            self.test_data, 
            target_timestamp=first_time,
            is_realtime=False
        )
        
        # 価格が異なることを確認
        self.assertNotEqual(realtime_result.current_price, backtest_result.current_price)
        
        price_diff = realtime_result.current_price - backtest_result.current_price
        
        print(f"   ✅ リアルタイム価格: {realtime_result.current_price}")
        print(f"   ✅ バックテスト価格: {backtest_result.current_price}")
        print(f"   ✅ 価格差: {price_diff}")
        print(f"   ✅ 価格差は期待通り: {price_diff == 95}")  # 1095 - 1000 = 95
    
    def test_multiple_backtest_timestamps(self):
        """複数のバックテスト時刻での価格多様性確認"""
        print(f"\n📊 複数時刻バックテストテスト:")
        
        prices = []
        for i in range(0, 5):
            target_time = self.test_data['timestamp'].iloc[i]
            result = self.analyzer.analyze_market_phase(
                self.test_data, 
                target_timestamp=target_time,
                is_realtime=False
            )
            prices.append(result.current_price)
            print(f"   時刻{i}: {target_time.strftime('%H:%M')} -> 価格: {result.current_price}")
        
        # すべて異なる価格になることを確認
        unique_prices = len(set(prices))
        self.assertEqual(unique_prices, 5)
        
        print(f"   ✅ ユニーク価格数: {unique_prices}")
        print(f"   ✅ 価格範囲: {min(prices)} - {max(prices)}")
    
    def test_default_behavior_compatibility(self):
        """デフォルト動作の互換性確認"""
        print(f"\n🔄 互換性テスト:")
        
        # パラメータなしでの呼び出し（従来の動作）
        result_default = self.analyzer.analyze_market_phase(self.test_data)
        
        # is_realtime=True での呼び出し
        result_explicit = self.analyzer.analyze_market_phase(
            self.test_data, 
            is_realtime=True
        )
        
        # 同じ結果になることを確認
        self.assertEqual(result_default.current_price, result_explicit.current_price)
        
        print(f"   ✅ デフォルト動作: {result_default.current_price}")
        print(f"   ✅ 明示的リアルタイム: {result_explicit.current_price}")
        print(f"   ✅ 互換性: {result_default.current_price == result_explicit.current_price}")


class TestFlagBasedSystemIntegration(unittest.TestCase):
    """システム統合テスト"""
    
    def test_scalable_analysis_system_integration(self):
        """scalable_analysis_systemとの統合シナリオ"""
        print(f"\n🔗 システム統合テスト:")
        
        analyzer = SimpleMarketContextAnalyzer()
        
        # バックテストシナリオのシミュレーション
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        data = pd.DataFrame({
            'timestamp': [base_time + timedelta(hours=i) for i in range(5)],
            'open': [2000 + i * 50 for i in range(5)],
            'close': [2020 + i * 50 for i in range(5)],
            'high': [2030 + i * 50 for i in range(5)],
            'low': [1990 + i * 50 for i in range(5)],
            'volume': [50000] * 5
        })
        
        # 各トレード時刻での価格取得
        trade_results = []
        for i in range(5):
            trade_time = data['timestamp'].iloc[i]
            
            # バックテストモードで分析
            result = analyzer.analyze_market_phase(
                data, 
                target_timestamp=trade_time,
                is_realtime=False
            )
            
            trade_results.append({
                'time': trade_time,
                'current_price': result.current_price,
                'expected_open': data['open'].iloc[i]
            })
            
            print(f"   トレード{i+1}: {trade_time.strftime('%H:%M')} -> 価格: {result.current_price}")
        
        # すべての価格が正しく取得されることを確認
        all_correct = all(
            tr['current_price'] == tr['expected_open'] 
            for tr in trade_results
        )
        self.assertTrue(all_correct)
        
        print(f"   ✅ 全トレード価格正確性: {all_correct}")
    
    def test_error_handling_scenarios(self):
        """エラーハンドリングシナリオ"""
        print(f"\n⚠️ エラーハンドリングテスト:")
        
        analyzer = SimpleMarketContextAnalyzer()
        
        # データにtimestampカラムがない場合
        data_no_timestamp = pd.DataFrame({
            'open': [100, 110, 120],
            'close': [105, 115, 125],
            'high': [108, 118, 128],
            'low': [98, 108, 118],
            'volume': [1000, 1100, 1200]
        })
        
        # バックテストでtimestampなしデータ
        with self.assertRaises(ValueError) as context:
            analyzer.analyze_market_phase(
                data_no_timestamp, 
                target_timestamp=datetime.now(),
                is_realtime=False
            )
        
        error_msg = str(context.exception)
        self.assertIn("timestampカラムが必要", error_msg)
        
        print(f"   ✅ timestampなしエラー: {error_msg}")
        
        # 空のデータフレーム
        empty_data = pd.DataFrame()
        result = analyzer.analyze_market_phase(empty_data, is_realtime=True)
        self.assertEqual(result.current_price, 1000.0)  # デフォルト値
        
        print(f"   ✅ 空データ処理: デフォルト価格 {result.current_price}")


def run_tests():
    """テスト実行"""
    print("🏁 フラグベース分析システム包括テスト")
    print("=" * 80)
    
    # テストスイート作成
    suite = unittest.TestSuite()
    
    # テストケース追加
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFlagBasedAnalysis))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFlagBasedSystemIntegration))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ すべてのテストが成功!")
        print("\n🎯 実装の要点:")
        print("1. is_realtime=True: 最新close価格を使用（リアルタイム分析）")
        print("2. is_realtime=False: target_timestampが必須（バックテスト分析）")
        print("3. バックテストでは該当時刻のopen価格を使用")
        print("4. 明示的なフラグにより事故を防止")
        print("5. 価格の多様性と正確性を保証")
        print("\n🔧 次のステップ:")
        print("1. 実際のAPIからのリアルタイム価格取得実装")
        print("2. high_leverage_bot_orchestratorでの適切なフラグ設定")
        print("3. scalable_analysis_systemでの統合テスト")
    else:
        print("\n❌ テストに失敗があります")
        if result.failures:
            print("\n失敗したテスト:")
            for test, traceback in result.failures:
                print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)