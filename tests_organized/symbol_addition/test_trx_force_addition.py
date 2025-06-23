#!/usr/bin/env python3
"""
TRX強制追加テスト（BaseTest使用版）
データベースの既存チェックをスキップして新規追加をテスト
"""

import sys
import os
from datetime import datetime
import sqlite3
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests_organized.base_test import BaseTest

class TRXForceAdditionTest(BaseTest):
    """TRX強制追加テスト"""
    
    def custom_setup(self):
        """テスト固有のセットアップ"""
        self.test_symbol = "TRX"
    
    def clear_trx_from_test_db(self):
        """テストDBからTRXエントリを削除"""
        print("🗑️ テストDBからTRXエントリを削除...")
        try:
            with sqlite3.connect(self.analysis_db) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM analyses WHERE symbol=?", (self.test_symbol,))
                deleted = cursor.rowcount
                conn.commit()
                print(f"✅ {deleted}件のTRXエントリを削除")
        except Exception as e:
            print(f"❌ DB削除エラー: {e}")

    def test_trx_direct_analysis(self):
        """TRXを直接分析（既存チェックなし）"""
        print("\n🔍 TRX直接分析テスト")
        print("=" * 70)
        
        try:
            from scalable_analysis_system import ScalableAnalysisSystem
            import numpy as np
            from datetime import timedelta, timezone
            
            system = ScalableAnalysisSystem()
            
            # _generate_real_analysisを直接呼び出し
            print("📊 TRXの実データ分析を実行...")
            
            timeframe = "1h"
            config = "Conservative_ML"
            
            start_time = datetime.now()
            
            # 直接実データ分析を実行（サンプル数を減らして高速化）
            trades_data = system._generate_real_analysis(self.test_symbol, timeframe, config, num_trades=10)
            
            end_time = datetime.now()
            
            print(f"\n✅ 分析完了")
            print(f"⏱️ 処理時間: {(end_time - start_time).total_seconds():.2f}秒")
            
            # 結果を検証
            self.assertIsInstance(trades_data, list, "分析結果はリスト形式である必要があります")
            
            if trades_data:
                print(f"📊 生成トレード数: {len(trades_data)}")
                
                # 最初のトレードを詳細表示
                first_trade = trades_data[0]
                print("\n最初のトレード詳細:")
                for key, value in first_trade.items():
                    if 'price' in key:
                        print(f"  {key}: ${value:.6f}")
                    else:
                        print(f"  {key}: {value}")
                
                # ハードコード値チェック
                hardcoded_values = [100.0, 105.0, 97.62, 1000.0]
                hardcoded_found = False
                
                for trade in trades_data:
                    for key in ['entry_price', 'take_profit_price', 'stop_loss_price']:
                        if key in trade:
                            value = trade[key]
                            for hv in hardcoded_values:
                                if abs(value - hv) < 0.001:
                                    print(f"\n❌ ハードコード値検出: {key} = {value}")
                                    hardcoded_found = True
                
                self.assertFalse(hardcoded_found, "ハードコードされた価格値が検出されました")
                if not hardcoded_found:
                    print("\n✅ ハードコード値なし！")
                    
                # 価格の妥当性チェック
                entry_prices = [t.get('entry_price', 0) for t in trades_data]
                if entry_prices:
                    avg_price = np.mean(entry_prices)
                    print(f"\n💰 TRX平均エントリー価格: ${avg_price:.6f}")
                    self.assertGreaterEqual(avg_price, 0.01, "TRXの価格が低すぎます")
                    self.assertLessEqual(avg_price, 1.0, "TRXの価格が高すぎます")
                    if 0.01 <= avg_price <= 1.0:
                        print("✅ TRXの妥当な価格範囲内")
                    
        except Exception as e:
            self.fail(f"TRX分析中にエラーが発生しました: {e}")
    
    def test_trx_force_addition_workflow(self):
        """TRX強制追加ワークフローテスト"""
        print("\n🚀 TRX強制追加ワークフローテスト")
        print("=" * 70)
        
        # 1. データベースクリア
        self.clear_trx_from_test_db()
        
        # 2. 直接分析テスト
        self.test_trx_direct_analysis()
        
        print("\n" + "=" * 70)
        print("✅ ワークフローテスト完了")


def run_trx_force_addition_tests():
    """TRX強制追加テスト実行"""
    import unittest
    
    # テストスイート作成
    suite = unittest.TestSuite()
    test_class = TRXForceAdditionTest
    
    # 個別テストメソッドを追加
    suite.addTest(test_class('test_trx_direct_analysis'))
    suite.addTest(test_class('test_trx_force_addition_workflow'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_trx_force_addition_tests()
    sys.exit(0 if success else 1)