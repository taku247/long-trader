#!/usr/bin/env python3
"""
leverage_decision_engine.pyの価格取得修正テスト

問題：current_priceが常に最新のclose価格を使用している
解決：target_timestampに基づいて適切な時点の価格を取得
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.leverage_decision_engine import SimpleMarketContextAnalyzer
from interfaces.data_types import MarketContext


class TestLeverageDecisionEngineFix(unittest.TestCase):
    """価格取得修正のテストケース"""
    
    def setUp(self):
        """テスト前準備"""
        self.analyzer = SimpleMarketContextAnalyzer()
        
        # テスト用OHLCVデータ生成（時系列で価格が変化）
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        self.test_data = pd.DataFrame({
            'timestamp': [base_time + timedelta(hours=i) for i in range(10)],
            'open': [50000 + i * 100 for i in range(10)],      # 50000, 50100, 50200, ...
            'high': [50050 + i * 100 for i in range(10)],
            'low': [49950 + i * 100 for i in range(10)],
            'close': [50020 + i * 100 for i in range(10)],     # 50020, 50120, 50220, ...
            'volume': [1000000] * 10
        })
        
        print("🧪 テスト用OHLCVデータ:")
        print(self.test_data[['timestamp', 'open', 'close']].head())
    
    def test_current_price_with_latest_data(self):
        """target_timestamp未指定時は最新close価格を使用"""
        # target_timestamp=Noneで呼び出し
        result = self.analyzer.analyze_market_phase(self.test_data)
        
        expected_price = self.test_data['close'].iloc[-1]  # 最新のclose価格
        self.assertEqual(result.current_price, expected_price)
        
        print(f"\n✅ 最新データテスト成功")
        print(f"   期待値: {expected_price}")
        print(f"   実際値: {result.current_price}")
    
    def test_current_price_with_specific_timestamp(self):
        """target_timestamp指定時は該当時刻のopen価格を使用"""
        # 5番目のローソク足の時刻を指定
        target_time = self.test_data['timestamp'].iloc[5]
        
        result = self.analyzer.analyze_market_phase(self.test_data, target_timestamp=target_time, is_realtime=False)
        
        expected_price = self.test_data['open'].iloc[5]  # 該当時刻のopen価格
        self.assertEqual(result.current_price, expected_price)
        
        print(f"\n✅ 特定時刻テスト成功")
        print(f"   指定時刻: {target_time}")
        print(f"   期待値（open）: {expected_price}")
        print(f"   実際値: {result.current_price}")
    
    def test_price_difference_between_modes(self):
        """最新価格と過去価格の違いを確認"""
        # 最新価格
        latest_result = self.analyzer.analyze_market_phase(self.test_data)
        
        # 最初のローソク足の価格
        first_time = self.test_data['timestamp'].iloc[0]
        first_result = self.analyzer.analyze_market_phase(self.test_data, target_timestamp=first_time, is_realtime=False)
        
        # 価格が異なることを確認
        self.assertNotEqual(latest_result.current_price, first_result.current_price)
        
        # 価格差を計算
        price_diff = latest_result.current_price - first_result.current_price
        expected_diff = self.test_data['close'].iloc[-1] - self.test_data['open'].iloc[0]
        
        print(f"\n✅ 価格差テスト成功")
        print(f"   最新価格: {latest_result.current_price}")
        print(f"   最初の価格: {first_result.current_price}")
        print(f"   価格差: {price_diff}")
        print(f"   期待される差: {expected_diff}")
    
    def test_without_timestamp_column(self):
        """timestampカラムがない場合の動作確認"""
        # timestampカラムをインデックスに設定
        data_with_index = self.test_data.set_index('timestamp')
        
        # target_timestamp指定で呼び出し
        target_time = data_with_index.index[3]
        result = self.analyzer.analyze_market_phase(data_with_index, target_timestamp=target_time, is_realtime=False)
        
        # timestampカラムが作成され、正しい価格が取得されることを確認
        expected_price = self.test_data['open'].iloc[3]
        self.assertEqual(result.current_price, expected_price)
        
        print(f"\n✅ インデックス形式テスト成功")
        print(f"   期待値: {expected_price}")
        print(f"   実際値: {result.current_price}")
    
    def test_backtest_scenario(self):
        """バックテストシナリオのシミュレーション"""
        print(f"\n📊 バックテストシナリオ:")
        
        prices_used = []
        
        # 各時点でのエントリーをシミュレート
        for i in range(3, 7):  # 3〜6番目のローソク足でエントリー
            target_time = self.test_data['timestamp'].iloc[i]
            result = self.analyzer.analyze_market_phase(self.test_data, target_timestamp=target_time, is_realtime=False)
            
            prices_used.append({
                'time': target_time,
                'current_price': result.current_price,
                'expected_open': self.test_data['open'].iloc[i],
                'match': result.current_price == self.test_data['open'].iloc[i]
            })
        
        # 結果を表示
        for p in prices_used:
            status = "✅" if p['match'] else "❌"
            print(f"   {status} 時刻 {p['time'].strftime('%H:%M')}: "
                  f"current_price={p['current_price']}, "
                  f"expected_open={p['expected_open']}")
        
        # すべての価格が正しいことを確認
        all_match = all(p['match'] for p in prices_used)
        self.assertTrue(all_match, "一部の価格が期待値と一致しません")
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        # 空のデータフレーム
        empty_df = pd.DataFrame()
        result = self.analyzer.analyze_market_phase(empty_df)
        self.assertEqual(result.current_price, 1000.0)  # デフォルト値
        
        # 1行のみのデータ
        single_row = self.test_data.head(1)
        result = self.analyzer.analyze_market_phase(single_row)
        self.assertEqual(result.current_price, single_row['close'].iloc[0])
        
        print("\n✅ エッジケーステスト成功")


class TestPriceConsistencyIntegration(unittest.TestCase):
    """価格整合性の統合テスト"""
    
    def test_entry_price_consistency(self):
        """entry_priceとcurrent_priceの整合性確認"""
        analyzer = SimpleMarketContextAnalyzer()
        
        # テストデータ
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        data = pd.DataFrame({
            'timestamp': [base_time + timedelta(hours=i) for i in range(5)],
            'open': [100, 102, 104, 106, 108],
            'close': [101, 103, 105, 107, 109],
            'high': [102, 104, 106, 108, 110],
            'low': [99, 101, 103, 105, 107],
            'volume': [1000] * 5
        })
        
        # 特定時刻での分析
        target_time = data['timestamp'].iloc[2]
        result = analyzer.analyze_market_phase(data, target_timestamp=target_time, is_realtime=False)
        
        # この価格がentry_priceとして使用されるべき
        expected_entry_price = data['open'].iloc[2]  # 104
        
        print(f"\n🎯 価格整合性テスト:")
        print(f"   分析時刻: {target_time}")
        print(f"   current_price: {result.current_price}")
        print(f"   期待されるentry_price: {expected_entry_price}")
        print(f"   整合性: {'✅ OK' if result.current_price == expected_entry_price else '❌ NG'}")
        
        self.assertEqual(result.current_price, expected_entry_price)


def run_tests():
    """テスト実行"""
    print("🔧 Leverage Decision Engine 価格取得修正テスト")
    print("=" * 80)
    
    # テストスイート作成
    suite = unittest.TestSuite()
    
    # テストケース追加
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLeverageDecisionEngineFix))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPriceConsistencyIntegration))
    
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
        print("\n📋 修正内容:")
        print("1. analyze_market_phase()にtarget_timestampパラメータを追加")
        print("2. target_timestamp指定時は該当時刻のopen価格を使用")
        print("3. 未指定時は従来通り最新close価格を使用（互換性維持）")
        print("4. バックテストでの価格整合性が確保される")
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