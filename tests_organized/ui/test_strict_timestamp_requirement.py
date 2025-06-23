#!/usr/bin/env python3
"""
タイムスタンプ必須要件のテスト

バックテストではtarget_timestampを必須とし、
指定がない場合はエラーとする厳格な実装のテスト
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


class TestStrictTimestampRequirement(unittest.TestCase):
    """厳格なタイムスタンプ要件のテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.analyzer = SimpleMarketContextAnalyzer()
        
        # タイムスタンプ付きテストデータ
        self.data_with_timestamp = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1, i, 0, 0) for i in range(5)],
            'open': [100 + i for i in range(5)],
            'close': [101 + i for i in range(5)],
            'high': [102 + i for i in range(5)],
            'low': [99 + i for i in range(5)],
            'volume': [1000] * 5
        })
        
        # タイムスタンプなしデータ（インデックスのみ）
        self.data_without_timestamp = pd.DataFrame({
            'open': [100 + i for i in range(5)],
            'close': [101 + i for i in range(5)],
            'high': [102 + i for i in range(5)],
            'low': [99 + i for i in range(5)],
            'volume': [1000] * 5
        }, index=range(5))
    
    def test_timestamp_required_for_backtest(self):
        """バックテストではタイムスタンプが必須"""
        target_time = datetime(2024, 1, 1, 2, 0, 0)
        
        # タイムスタンプカラムがないデータでtarget_timestamp指定
        with self.assertRaises(ValueError) as context:
            self.analyzer.analyze_market_phase(
                self.data_without_timestamp, 
                target_timestamp=target_time
            )
        
        self.assertIn("バックテスト分析ではtarget_timestampが必須", str(context.exception))
        self.assertIn("timestampカラムがなく", str(context.exception))
        
        print("✅ タイムスタンプなしデータでエラー発生を確認")
    
    def test_warning_without_timestamp(self):
        """タイムスタンプ未指定時の警告確認"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # target_timestamp未指定で呼び出し
            result = self.analyzer.analyze_market_phase(self.data_with_timestamp)
            
            # 警告が発生することを確認
            self.assertEqual(len(w), 1)
            self.assertIn("target_timestampが指定されていません", str(w[0].message))
            self.assertIn("バックテストでは正確な価格を保証できません", str(w[0].message))
            
            print("✅ タイムスタンプ未指定時の警告を確認")
            print(f"   警告メッセージ: {w[0].message}")
    
    def test_proper_usage_with_timestamp(self):
        """適切な使用方法（タイムスタンプ指定）"""
        target_time = datetime(2024, 1, 1, 2, 0, 0)
        
        # 正しい使用方法
        result = self.analyzer.analyze_market_phase(
            self.data_with_timestamp,
            target_timestamp=target_time
        )
        
        # 該当時刻のopen価格が使用されることを確認
        expected_price = self.data_with_timestamp.loc[2, 'open']  # 102
        self.assertEqual(result.current_price, expected_price)
        
        print("✅ タイムスタンプ指定時の正常動作を確認")
        print(f"   指定時刻: {target_time}")
        print(f"   使用価格: {result.current_price}")
    
    def test_scalable_analysis_integration(self):
        """scalable_analysis_systemとの統合シナリオ"""
        print("\n📊 統合シナリオテスト:")
        
        # バックテストシミュレーション
        for i in range(3):
            trade_time = self.data_with_timestamp['timestamp'].iloc[i]
            
            # 正しい使用方法：各トレード時刻を指定
            result = self.analyzer.analyze_market_phase(
                self.data_with_timestamp,
                target_timestamp=trade_time
            )
            
            print(f"   トレード{i+1}: 時刻={trade_time.strftime('%H:%M')}, "
                  f"価格={result.current_price}")
            
            # 各トレードで異なる価格が使用されることを確認
            self.assertEqual(result.current_price, self.data_with_timestamp.loc[i, 'open'])


class TestBacktestPriceDiversity(unittest.TestCase):
    """バックテストでの価格多様性テスト"""
    
    def test_price_diversity_enforcement(self):
        """価格多様性の強制確認"""
        analyzer = SimpleMarketContextAnalyzer()
        
        # 価格が変化するデータ
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1h'),
            'open': np.linspace(50000, 51000, 100),  # 50000から51000まで線形増加
            'close': np.linspace(50020, 51020, 100),
            'high': np.linspace(50100, 51100, 100),
            'low': np.linspace(49900, 50900, 100),
            'volume': [1000000] * 100
        })
        
        # タイムスタンプなしでの呼び出しを試行
        prices_without_timestamp = []
        
        # 警告を抑制して複数回実行
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            for _ in range(5):
                result = analyzer.analyze_market_phase(data)
                prices_without_timestamp.append(result.current_price)
        
        # すべて同じ価格（最新close）になることを確認
        self.assertEqual(len(set(prices_without_timestamp)), 1)
        print(f"\n⚠️ タイムスタンプなし: すべて同じ価格 {prices_without_timestamp[0]}")
        
        # タイムスタンプありでの呼び出し
        prices_with_timestamp = []
        
        for i in range(5):
            target_time = data['timestamp'].iloc[i * 20]  # 異なる時点
            result = analyzer.analyze_market_phase(data, target_timestamp=target_time)
            prices_with_timestamp.append(result.current_price)
        
        # すべて異なる価格になることを確認
        self.assertEqual(len(set(prices_with_timestamp)), 5)
        print(f"✅ タイムスタンプあり: {len(set(prices_with_timestamp))}個の異なる価格")
        print(f"   価格範囲: {min(prices_with_timestamp):.0f} - {max(prices_with_timestamp):.0f}")


def run_tests():
    """テスト実行"""
    print("🔒 厳格なタイムスタンプ要件テスト")
    print("=" * 80)
    
    # テストスイート作成
    suite = unittest.TestSuite()
    
    # テストケース追加
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestStrictTimestampRequirement))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBacktestPriceDiversity))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 テスト結果")
    print("=" * 80)
    
    if result.wasSuccessful():
        print("✅ すべてのテストが成功!")
        print("\n🎯 実装の要点:")
        print("1. タイムスタンプカラムがない場合はValueError")
        print("2. target_timestamp未指定時は警告を発生")
        print("3. バックテストでは必ずtarget_timestampを指定")
        print("4. これにより価格の多様性と正確性を保証")
    else:
        print("❌ テストに失敗があります")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)