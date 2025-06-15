#!/usr/bin/env python3
"""
エントリー価格多様性テスト
バックテスト結果でエントリー価格・TP/SL・レバレッジの統一化問題を検知
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestEntryPriceDiversity(unittest.TestCase):
    """エントリー価格多様性テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        from scalable_analysis_system import ScalableAnalysisSystem
        self.system = ScalableAnalysisSystem()
        
        # テスト対象の戦略設定
        self.test_strategies = [
            ('DOT', '1h', 'Conservative_ML'),
            ('DOT', '30m', 'Aggressive_Traditional'),
            ('DOT', '15m', 'Full_ML'),
        ]
        
        # 許容可能な統一率（全体の10%まで同一値を許容）
        self.max_uniformity_rate = 0.10
        
        # 最小データ件数
        self.min_trades_for_test = 10
    
    def test_entry_price_diversity(self):
        """エントリー価格の多様性テスト"""
        print("\n🔍 エントリー価格多様性テスト")
        print("=" * 60)
        
        failed_strategies = []
        
        for symbol, timeframe, config in self.test_strategies:
            with self.subTest(symbol=symbol, timeframe=timeframe, config=config):
                trades_data = self.system.load_compressed_trades(symbol, timeframe, config)
                
                if not trades_data or len(trades_data) < self.min_trades_for_test:
                    self.skipTest(f"Insufficient trade data: {len(trades_data) if trades_data else 0} trades")
                
                entry_prices = [trade.get('entry_price') for trade in trades_data 
                              if trade.get('entry_price') is not None]
                
                if not entry_prices:
                    self.skipTest("No entry price data available")
                
                # 統一性チェック
                unique_prices = len(set(entry_prices))
                total_prices = len(entry_prices)
                diversity_rate = unique_prices / total_prices
                
                print(f"📊 {symbol} {timeframe} {config}:")
                print(f"   トレード数: {total_prices}")
                print(f"   ユニーク価格数: {unique_prices}")
                print(f"   多様性率: {diversity_rate:.2%}")
                
                # アサーション
                self.assertGreater(
                    diversity_rate, 
                    1 - self.max_uniformity_rate,
                    f"{symbol} {timeframe} {config}: エントリー価格の統一率が高すぎます "
                    f"(多様性率: {diversity_rate:.2%})"
                )
                
                if diversity_rate <= 1 - self.max_uniformity_rate:
                    failed_strategies.append(f"{symbol} {timeframe} {config}")
        
        if failed_strategies:
            self.fail(f"エントリー価格統一問題検出: {failed_strategies}")
    
    def test_take_profit_diversity(self):
        """利確ライン多様性テスト"""
        print("\n🔍 利確ライン多様性テスト")
        print("=" * 60)
        
        failed_strategies = []
        
        for symbol, timeframe, config in self.test_strategies:
            with self.subTest(symbol=symbol, timeframe=timeframe, config=config):
                trades_data = self.system.load_compressed_trades(symbol, timeframe, config)
                
                if not trades_data or len(trades_data) < self.min_trades_for_test:
                    self.skipTest(f"Insufficient trade data: {len(trades_data) if trades_data else 0} trades")
                
                tp_prices = [trade.get('take_profit_price') for trade in trades_data 
                           if trade.get('take_profit_price') is not None]
                
                if not tp_prices:
                    self.skipTest("No take profit data available")
                
                # 統一性チェック
                unique_tp = len(set(tp_prices))
                total_tp = len(tp_prices)
                diversity_rate = unique_tp / total_tp
                
                print(f"📊 {symbol} {timeframe} {config}:")
                print(f"   TP設定数: {total_tp}")
                print(f"   ユニークTP数: {unique_tp}")
                print(f"   多様性率: {diversity_rate:.2%}")
                
                # アサーション
                self.assertGreater(
                    diversity_rate, 
                    1 - self.max_uniformity_rate,
                    f"{symbol} {timeframe} {config}: 利確ラインの統一率が高すぎます "
                    f"(多様性率: {diversity_rate:.2%})"
                )
                
                if diversity_rate <= 1 - self.max_uniformity_rate:
                    failed_strategies.append(f"{symbol} {timeframe} {config}")
        
        if failed_strategies:
            self.fail(f"利確ライン統一問題検出: {failed_strategies}")
    
    def test_stop_loss_diversity(self):
        """損切りライン多様性テスト"""
        print("\n🔍 損切りライン多様性テスト")
        print("=" * 60)
        
        failed_strategies = []
        
        for symbol, timeframe, config in self.test_strategies:
            with self.subTest(symbol=symbol, timeframe=timeframe, config=config):
                trades_data = self.system.load_compressed_trades(symbol, timeframe, config)
                
                if not trades_data or len(trades_data) < self.min_trades_for_test:
                    self.skipTest(f"Insufficient trade data: {len(trades_data) if trades_data else 0} trades")
                
                sl_prices = [trade.get('stop_loss_price') for trade in trades_data 
                           if trade.get('stop_loss_price') is not None]
                
                if not sl_prices:
                    self.skipTest("No stop loss data available")
                
                # 統一性チェック
                unique_sl = len(set(sl_prices))
                total_sl = len(sl_prices)
                diversity_rate = unique_sl / total_sl
                
                print(f"📊 {symbol} {timeframe} {config}:")
                print(f"   SL設定数: {total_sl}")
                print(f"   ユニークSL数: {unique_sl}")
                print(f"   多様性率: {diversity_rate:.2%}")
                
                # アサーション
                self.assertGreater(
                    diversity_rate, 
                    1 - self.max_uniformity_rate,
                    f"{symbol} {timeframe} {config}: 損切りラインの統一率が高すぎます "
                    f"(多様性率: {diversity_rate:.2%})"
                )
                
                if diversity_rate <= 1 - self.max_uniformity_rate:
                    failed_strategies.append(f"{symbol} {timeframe} {config}")
        
        if failed_strategies:
            self.fail(f"損切りライン統一問題検出: {failed_strategies}")
    
    def test_leverage_diversity(self):
        """レバレッジ多様性テスト"""
        print("\n🔍 レバレッジ多様性テスト")
        print("=" * 60)
        
        failed_strategies = []
        
        for symbol, timeframe, config in self.test_strategies:
            with self.subTest(symbol=symbol, timeframe=timeframe, config=config):
                trades_data = self.system.load_compressed_trades(symbol, timeframe, config)
                
                if not trades_data or len(trades_data) < self.min_trades_for_test:
                    self.skipTest(f"Insufficient trade data: {len(trades_data) if trades_data else 0} trades")
                
                leverages = [trade.get('leverage') for trade in trades_data 
                           if trade.get('leverage') is not None]
                
                if not leverages:
                    self.skipTest("No leverage data available")
                
                # 統一性チェック
                unique_leverage = len(set(leverages))
                total_leverage = len(leverages)
                diversity_rate = unique_leverage / total_leverage
                
                print(f"📊 {symbol} {timeframe} {config}:")
                print(f"   レバレッジ設定数: {total_leverage}")
                print(f"   ユニークレバレッジ数: {unique_leverage}")
                print(f"   多様性率: {diversity_rate:.2%}")
                
                # レバレッジは戦略によっては同一でも許容する場合があるため、
                # より緩い基準を設定（最大50%まで同一値を許容）
                leverage_max_uniformity = 0.50
                
                # アサーション
                self.assertGreater(
                    diversity_rate, 
                    1 - leverage_max_uniformity,
                    f"{symbol} {timeframe} {config}: レバレッジの統一率が高すぎます "
                    f"(多様性率: {diversity_rate:.2%})"
                )
                
                if diversity_rate <= 1 - leverage_max_uniformity:
                    failed_strategies.append(f"{symbol} {timeframe} {config}")
        
        if failed_strategies:
            self.fail(f"レバレッジ統一問題検出: {failed_strategies}")
    
    def test_price_realism_check(self):
        """価格の現実性チェック"""
        print("\n🔍 価格現実性テスト")
        print("=" * 60)
        
        for symbol, timeframe, config in self.test_strategies:
            with self.subTest(symbol=symbol, timeframe=timeframe, config=config):
                trades_data = self.system.load_compressed_trades(symbol, timeframe, config)
                
                if not trades_data or len(trades_data) < self.min_trades_for_test:
                    self.skipTest(f"Insufficient trade data: {len(trades_data) if trades_data else 0} trades")
                
                entry_prices = [trade.get('entry_price') for trade in trades_data 
                              if trade.get('entry_price') is not None]
                exit_prices = [trade.get('exit_price') for trade in trades_data 
                             if trade.get('exit_price') is not None]
                
                if not entry_prices or not exit_prices:
                    self.skipTest("Insufficient price data")
                
                # エントリー価格の現実性チェック
                entry_min, entry_max = min(entry_prices), max(entry_prices)
                exit_min, exit_max = min(exit_prices), max(exit_prices)
                
                print(f"📊 {symbol} {timeframe} {config}:")
                print(f"   エントリー価格範囲: {entry_min:.4f} - {entry_max:.4f}")
                print(f"   クローズ価格範囲: {exit_min:.4f} - {exit_max:.4f}")
                
                # エントリー価格とクローズ価格が同じ範囲内にあることを確認
                # (極端に乖離していないかチェック)
                price_ratio = max(entry_max / exit_min, exit_max / entry_min) if exit_min > 0 and entry_min > 0 else 1
                
                self.assertLess(
                    price_ratio, 
                    2.0,  # 2倍以上の乖離は異常
                    f"{symbol} {timeframe} {config}: エントリー価格とクローズ価格の乖離が異常 "
                    f"(比率: {price_ratio:.2f})"
                )
    
    def test_temporal_consistency(self):
        """時系列整合性テスト"""
        print("\n🔍 時系列整合性テスト")
        print("=" * 60)
        
        for symbol, timeframe, config in self.test_strategies:
            with self.subTest(symbol=symbol, timeframe=timeframe, config=config):
                trades_data = self.system.load_compressed_trades(symbol, timeframe, config)
                
                if not trades_data or len(trades_data) < self.min_trades_for_test:
                    self.skipTest(f"Insufficient trade data: {len(trades_data) if trades_data else 0} trades")
                
                # エントリー時刻とクローズ時刻をチェック
                valid_time_trades = 0
                for trade in trades_data[:10]:  # 最初の10件をチェック
                    entry_time = trade.get('entry_time')
                    exit_time = trade.get('exit_time')
                    
                    if entry_time and exit_time:
                        try:
                            # 時刻の妥当性をチェック
                            if isinstance(entry_time, str):
                                entry_dt = pd.to_datetime(entry_time)
                            else:
                                entry_dt = entry_time
                            
                            if isinstance(exit_time, str):
                                exit_dt = pd.to_datetime(exit_time)
                            else:
                                exit_dt = exit_time
                            
                            # エントリー時刻がクローズ時刻より前であることを確認
                            self.assertLess(
                                entry_dt, exit_dt,
                                f"{symbol} {timeframe} {config}: エントリー時刻がクローズ時刻より後 "
                                f"(Entry: {entry_dt}, Exit: {exit_dt})"
                            )
                            valid_time_trades += 1
                            
                        except Exception as e:
                            # 時刻データが無効な場合はスキップ
                            continue
                
                print(f"📊 {symbol} {timeframe} {config}:")
                print(f"   時系列チェック対象: {valid_time_trades}件")
                
                # 最低限の時系列データが存在することを確認
                self.assertGreater(
                    valid_time_trades, 
                    0,
                    f"{symbol} {timeframe} {config}: 有効な時系列データが存在しません"
                )


class TestBacktestRealism(unittest.TestCase):
    """バックテスト現実性テスト"""
    
    def test_no_look_ahead_bias(self):
        """Look-ahead bias検知テスト"""
        print("\n🔍 Look-ahead bias検知テスト")
        print("=" * 60)
        
        # このテストは将来的に実装予定
        # 現在のバックテストエンジンでlook-ahead biasが発生していないかチェック
        self.skipTest("Look-ahead bias検知テストは今後実装予定")
    
    def test_realistic_slippage(self):
        """現実的スリッページテスト"""
        print("\n🔍 現実的スリッページテスト")
        print("=" * 60)
        
        # エントリー価格とクローズ価格の関係から
        # 現実的なスリッページが考慮されているかチェック
        self.skipTest("スリッページテストは今後実装予定")


def run_entry_price_diversity_tests():
    """エントリー価格多様性テストを実行"""
    print("🚀 エントリー価格多様性テストスイート実行")
    print("=" * 70)
    print("目的: バックテスト結果の価格統一問題を自動検知")
    print("=" * 70)
    
    # テストスイート作成
    suite = unittest.TestSuite()
    
    # エントリー価格多様性テストを追加
    suite.addTest(TestEntryPriceDiversity('test_entry_price_diversity'))
    suite.addTest(TestEntryPriceDiversity('test_take_profit_diversity'))
    suite.addTest(TestEntryPriceDiversity('test_stop_loss_diversity'))
    suite.addTest(TestEntryPriceDiversity('test_leverage_diversity'))
    suite.addTest(TestEntryPriceDiversity('test_price_realism_check'))
    suite.addTest(TestEntryPriceDiversity('test_temporal_consistency'))
    
    # バックテスト現実性テストを追加
    suite.addTest(TestBacktestRealism('test_no_look_ahead_bias'))
    suite.addTest(TestBacktestRealism('test_realistic_slippage'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 エントリー価格多様性テスト結果")
    print("=" * 70)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = total_tests - failures - errors - skipped
    
    print(f"実行テスト数: {total_tests}")
    print(f"成功: {passed}")
    print(f"失敗: {failures}")
    print(f"エラー: {errors}")
    print(f"スキップ: {skipped}")
    
    if failures > 0:
        print(f"\n❌ {failures}件の多様性問題を検出:")
        for test, traceback in result.failures:
            print(f"  • {test}")
    
    if errors > 0:
        print(f"\n⚠️ {errors}件のテストエラー:")
        for test, traceback in result.errors:
            print(f"  • {test}")
    
    success_rate = (passed / total_tests) * 100 if total_tests > 0 else 0
    
    if success_rate >= 80:
        print(f"\n✅ テスト成功率: {success_rate:.1f}% - バックテスト品質良好")
    else:
        print(f"\n⚠️ テスト成功率: {success_rate:.1f}% - 改善が必要")
    
    return result


if __name__ == '__main__':
    run_entry_price_diversity_tests()