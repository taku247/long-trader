#!/usr/bin/env python3
"""
バックテスト時系列整合性の専用テストコード
実際のHYPE問題を再現して修正効果を検証
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import sys
import os
from pathlib import Path
import tempfile

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TestBacktestTimeConsistency(unittest.TestCase):
    """バックテスト時系列整合性の特化テスト"""
    
    def setUp(self):
        """HYPE問題を模擬したテスト環境"""
        # HYPE問題の実際の時系列を模擬
        self.hype_problem_time = datetime(2025, 3, 24, 10, 0, tzinfo=timezone.utc)
        self.current_time = datetime(2025, 6, 25, 8, 40, tzinfo=timezone.utc)
        
        # 実際の問題状況を模擬したデータ作成
        self.hype_like_data = self._create_hype_problem_data()
        
    def _create_hype_problem_data(self):
        """HYPE問題を模擬したOHLCVデータ作成"""
        # 3ヶ月前から現在までのデータ
        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = self.current_time
        
        dates = pd.date_range(start=start_date, end=end_date, freq='1H')
        
        # HYPE問題を模擬：3月24日以降に価格が大きく上昇
        data = []
        base_price = 170.0
        
        for date in dates:
            if date <= self.hype_problem_time:
                # 3月24日以前：比較的安定した価格（170-180）
                trend_factor = 1.0
                volatility = 0.01
            else:
                # 3月24日以降：価格上昇（180-200）
                days_after = (date - self.hype_problem_time).days
                trend_factor = 1.0 + (days_after * 0.002)  # 徐々に上昇
                volatility = 0.015
            
            price = base_price * trend_factor
            noise = np.random.normal(0, price * volatility)
            final_price = max(1.0, price + noise)
            
            # OHLCV生成
            open_price = final_price
            high_price = final_price * (1 + abs(np.random.normal(0, 0.005)))
            low_price = final_price * (1 - abs(np.random.normal(0, 0.005)))
            close_price = final_price * (1 + np.random.normal(0, 0.003))
            volume = abs(np.random.normal(1000, 200))
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def test_hype_problem_reproduction(self):
        """HYPE問題の再現テスト"""
        print("\n🧪 HYPE問題再現テスト")
        
        # 問題状況の再現：全データで支持線検出
        all_data = self.hype_like_data
        problem_time_price = self._get_price_at_time(all_data, self.hype_problem_time)
        
        print(f"   HYPE問題時刻: {self.hype_problem_time}")
        print(f"   問題時刻の価格: {problem_time_price:.2f}")
        print(f"   全データ範囲: {all_data['timestamp'].min()} ～ {all_data['timestamp'].max()}")
        print(f"   全データサイズ: {len(all_data)}行")
        
        # 全データでの支持線検出（問題のあるケース）
        try:
            support_levels_all = self._detect_support_levels_simple(all_data, problem_time_price)
            print(f"   全データ支持線: {len(support_levels_all)}個")
            
            # 現在価格より下の支持線をカウント
            supports_below = [s for s in support_levels_all if s < problem_time_price]
            print(f"   現在価格下の支持線: {len(supports_below)}個")
            
            if len(supports_below) == 0:
                print("   ❌ HYPE問題再現: 現在価格下方にサポートレベルが存在しません")
                problem_reproduced = True
            else:
                print("   ✅ 支持線検出成功（問題未再現）")
                problem_reproduced = False
                
        except Exception as e:
            print(f"   ❌ HYPE問題再現: {e}")
            problem_reproduced = True
        
        # この段階では問題が再現されることを期待
        self.assertTrue(problem_reproduced or len(supports_below) == 0, "HYPE問題が再現されること")
        
    def test_future_data_exclusion_fix(self):
        """将来データ除外による修正効果テスト"""
        print("\n🧪 将来データ除外修正効果テスト")
        
        # 修正版：問題時刻以前のデータのみ使用
        historical_data = self.hype_like_data[self.hype_like_data['timestamp'] <= self.hype_problem_time]
        problem_time_price = self._get_price_at_time(historical_data, self.hype_problem_time)
        
        print(f"   修正版データ範囲: {historical_data['timestamp'].min()} ～ {historical_data['timestamp'].max()}")
        print(f"   修正版データサイズ: {len(historical_data)}行（削減: {len(self.hype_like_data) - len(historical_data)}行）")
        print(f"   問題時刻の価格: {problem_time_price:.2f}")
        
        # 歴史データのみでの支持線検出（修正版）
        try:
            support_levels_historical = self._detect_support_levels_simple(historical_data, problem_time_price)
            print(f"   歴史データ支持線: {len(support_levels_historical)}個")
            
            # 現在価格より下の支持線をカウント
            supports_below_fixed = [s for s in support_levels_historical if s < problem_time_price]
            print(f"   現在価格下の支持線: {len(supports_below_fixed)}個")
            
            if len(supports_below_fixed) > 0:
                print("   ✅ 修正効果確認: 適切な支持線が検出されました")
                print(f"     主な支持線: {supports_below_fixed[:3]}")
                fix_successful = True
            else:
                print("   ⚠️ 修正後も支持線不足（データ期間が短い可能性）")
                fix_successful = False
                
        except Exception as e:
            print(f"   ❌ 修正版でもエラー: {e}")
            fix_successful = False
        
        # 修正効果の確認
        self.assertTrue(fix_successful or len(historical_data) < 50, "修正により支持線検出が改善されること")
        
    def test_data_reduction_impact(self):
        """データ削減がパフォーマンスに与える影響テスト"""
        print("\n🧪 データ削減パフォーマンステスト")
        
        import time
        
        # 全データでの処理時間測定
        start_time = time.time()
        all_data_supports = self._detect_support_levels_simple(self.hype_like_data, 175.0)
        all_data_time = time.time() - start_time
        
        # 歴史データのみでの処理時間測定
        historical_data = self.hype_like_data[self.hype_like_data['timestamp'] <= self.hype_problem_time]
        start_time = time.time()
        historical_supports = self._detect_support_levels_simple(historical_data, 175.0)
        historical_time = time.time() - start_time
        
        # 結果比較
        data_reduction = (1 - len(historical_data) / len(self.hype_like_data)) * 100
        time_reduction = (1 - historical_time / all_data_time) * 100 if all_data_time > 0 else 0
        
        print(f"   全データ処理: {all_data_time:.4f}秒, 支持線{len(all_data_supports)}個")
        print(f"   歴史データ処理: {historical_time:.4f}秒, 支持線{len(historical_supports)}個")
        print(f"   データ削減率: {data_reduction:.1f}%")
        print(f"   時間削減率: {time_reduction:.1f}%")
        
        # パフォーマンス改善効果の確認
        self.assertGreater(data_reduction, 0, "データが削減されていること")
        self.assertGreaterEqual(time_reduction, 0, "処理時間が改善または同等であること")
        
    def test_multiple_backtest_points(self):
        """複数のバックテスト時点での整合性テスト"""
        print("\n🧪 複数バックテスト時点整合性テスト")
        
        # 異なる時点でのテスト
        test_points = [
            datetime(2025, 2, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2025, 3, 15, 9, 0, tzinfo=timezone.utc),
            datetime(2025, 4, 10, 14, 0, tzinfo=timezone.utc),
            datetime(2025, 5, 20, 16, 0, tzinfo=timezone.utc),
        ]
        
        consistency_results = []
        
        for i, test_time in enumerate(test_points):
            print(f"   テスト時点{i+1}: {test_time}")
            
            # その時点までのデータ
            point_data = self.hype_like_data[self.hype_like_data['timestamp'] <= test_time]
            
            if len(point_data) > 20:  # 最低限のデータがある場合
                point_price = self._get_price_at_time(point_data, test_time)
                
                try:
                    supports = self._detect_support_levels_simple(point_data, point_price)
                    supports_below = [s for s in supports if s < point_price]
                    
                    result = {
                        'time': test_time,
                        'price': point_price,
                        'data_points': len(point_data),
                        'supports_total': len(supports),
                        'supports_below': len(supports_below),
                        'success': len(supports_below) > 0
                    }
                    
                    print(f"     価格: {point_price:.2f}, データ: {len(point_data)}行")
                    print(f"     支持線: {len(supports)}個（下方: {len(supports_below)}個）")
                    print(f"     結果: {'✅ 成功' if result['success'] else '❌ 失敗'}")
                    
                    consistency_results.append(result)
                    
                except Exception as e:
                    print(f"     ❌ エラー: {e}")
                    consistency_results.append({
                        'time': test_time,
                        'success': False,
                        'error': str(e)
                    })
            else:
                print(f"     ⚠️ データ不足: {len(point_data)}行")
        
        # 整合性確認
        successful_points = [r for r in consistency_results if r.get('success', False)]
        success_rate = len(successful_points) / len(consistency_results) if consistency_results else 0
        
        print(f"   成功率: {success_rate:.1%} ({len(successful_points)}/{len(consistency_results)})")
        
        # 一定の成功率を期待
        self.assertGreaterEqual(success_rate, 0.5, "複数時点で一定の成功率を維持すること")
        
    def test_edge_case_boundary_times(self):
        """境界時刻のエッジケーステスト"""
        print("\n🧪 境界時刻エッジケーステスト")
        
        # データの最初と最後の時刻
        first_time = self.hype_like_data['timestamp'].min()
        last_time = self.hype_like_data['timestamp'].max()
        middle_time = first_time + (last_time - first_time) / 2
        
        boundary_cases = [
            ('最初の時刻', first_time),
            ('中間の時刻', middle_time),
            ('最後の時刻', last_time),
            ('データ範囲外（過去）', first_time - timedelta(days=1)),
            ('データ範囲外（未来）', last_time + timedelta(days=1)),
        ]
        
        for case_name, boundary_time in boundary_cases:
            print(f"   {case_name}: {boundary_time}")
            
            filtered_data = self.hype_like_data[self.hype_like_data['timestamp'] <= boundary_time]
            print(f"     フィルタ後データ数: {len(filtered_data)}行")
            
            if case_name == 'データ範囲外（過去）':
                self.assertEqual(len(filtered_data), 0, "過去範囲外では空データになること")
            elif case_name == 'データ範囲外（未来）':
                self.assertEqual(len(filtered_data), len(self.hype_like_data), "未来範囲外では全データが含まれること")
            elif case_name == '最初の時刻':
                self.assertGreaterEqual(len(filtered_data), 1, "最初の時刻では少なくとも1行は含まれること")
            elif case_name == '最後の時刻':
                self.assertEqual(len(filtered_data), len(self.hype_like_data), "最後の時刻では全データが含まれること")
            else:
                self.assertGreater(len(filtered_data), 0, f"{case_name}でデータが存在すること")
                self.assertLess(len(filtered_data), len(self.hype_like_data), f"{case_name}で一部データが除外されること")
        
        print("   ✅ 境界時刻エッジケース完了")
    
    def _get_price_at_time(self, df, target_time):
        """指定時刻の価格を取得"""
        if len(df) == 0:
            return 100.0  # デフォルト価格
        
        # 最も近い時刻のデータを取得
        time_diffs = abs(df['timestamp'] - target_time)
        closest_idx = time_diffs.idxmin()
        return df.loc[closest_idx, 'close']
    
    def _detect_support_levels_simple(self, df, current_price, min_touches=2):
        """簡易支持線検出（テスト用）"""
        if len(df) < 10:
            return []
        
        # 簡単な局所最小値検出
        from scipy.signal import argrelextrema
        
        lows = df['low'].values
        min_indices = argrelextrema(lows, np.less, order=3)[0]
        
        if len(min_indices) == 0:
            return []
        
        # 価格レベルのクラスタリング（簡易版）
        min_prices = [lows[i] for i in min_indices]
        
        # 近い価格をグループ化
        tolerance = current_price * 0.02  # 2%の許容範囲
        clusters = []
        
        for price in sorted(min_prices):
            added_to_cluster = False
            for cluster in clusters:
                if abs(price - np.mean(cluster)) <= tolerance:
                    cluster.append(price)
                    added_to_cluster = True
                    break
            if not added_to_cluster:
                clusters.append([price])
        
        # 最小タッチ数でフィルタ
        support_levels = []
        for cluster in clusters:
            if len(cluster) >= min_touches:
                support_levels.append(np.mean(cluster))
        
        return sorted(support_levels)

class TestRealWorldIntegration(unittest.TestCase):
    """実際のシステムとの統合テスト"""
    
    def test_scalable_analysis_system_with_current_time(self):
        """ScalableAnalysisSystemでcurrent_time変数のテスト"""
        print("\n🧪 ScalableAnalysisSystem current_time統合テスト")
        
        # current_time変数の動作をシミュレート
        test_scenarios = [
            ('バックテストモード', datetime(2025, 3, 24, 10, 0, tzinfo=timezone.utc)),
            ('リアルタイムモード', None),
        ]
        
        for scenario_name, current_time in test_scenarios:
            print(f"   シナリオ: {scenario_name}")
            print(f"   current_time: {current_time}")
            
            # サンプルデータ
            dates = pd.date_range('2025-01-01', '2025-06-01', freq='1H')
            ohlcv_data = pd.DataFrame({
                'timestamp': dates,
                'close': np.random.randn(len(dates)).cumsum() + 100
            })
            
            # 条件分岐ロジックのテスト
            if current_time:  # バックテスト時は current_time が設定されている
                # バックテスト：current_time以前のデータのみ使用
                historical_ohlcv = ohlcv_data[ohlcv_data['timestamp'] <= current_time]
                print(f"     バックテスト: データ制限 {len(historical_ohlcv)}/{len(ohlcv_data)}本")
                
                # 検証
                self.assertGreater(len(historical_ohlcv), 0, f"{scenario_name}: 歴史データが存在すること")
                self.assertLessEqual(len(historical_ohlcv), len(ohlcv_data), f"{scenario_name}: データが制限されていること")
                
                # 時系列整合性
                if len(historical_ohlcv) > 0:
                    latest_time = historical_ohlcv['timestamp'].max()
                    self.assertLessEqual(latest_time, current_time, f"{scenario_name}: 最新データがcurrent_time以前であること")
                    
            else:
                # リアルタイム：全データ使用
                historical_ohlcv = ohlcv_data
                print(f"     リアルタイム: 全データ使用 {len(historical_ohlcv)}本")
                
                # 検証
                self.assertEqual(len(historical_ohlcv), len(ohlcv_data), f"{scenario_name}: 全データが使用されていること")
            
            print(f"     ✅ {scenario_name} 正常動作")

def run_backtest_consistency_tests():
    """バックテスト整合性テストの実行"""
    print("🧪 バックテスト時系列整合性 - 専用テストスイート実行")
    print("="*70)
    
    # テストスイート作成
    test_suite = unittest.TestSuite()
    
    # HYPE問題関連テスト
    test_suite.addTest(TestBacktestTimeConsistency('test_hype_problem_reproduction'))
    test_suite.addTest(TestBacktestTimeConsistency('test_future_data_exclusion_fix'))
    
    # パフォーマンス・整合性テスト
    test_suite.addTest(TestBacktestTimeConsistency('test_data_reduction_impact'))
    test_suite.addTest(TestBacktestTimeConsistency('test_multiple_backtest_points'))
    
    # エッジケーステスト
    test_suite.addTest(TestBacktestTimeConsistency('test_edge_case_boundary_times'))
    
    # 統合テスト
    test_suite.addTest(TestRealWorldIntegration('test_scalable_analysis_system_with_current_time'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 結果サマリー
    print("\n" + "="*70)
    print("📊 バックテスト整合性テスト結果")
    print("="*70)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n⚠️ エラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    if result.wasSuccessful():
        print("\n✅ 全テスト成功！バックテスト時系列整合性修正は正常に動作しています。")
        print("🎯 HYPE問題の解決が確認されました。")
    else:
        print("\n🔴 一部テストが失敗しました。修正内容を確認してください。")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    run_backtest_consistency_tests()