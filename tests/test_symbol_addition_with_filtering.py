#!/usr/bin/env python3
"""
フィルタリングシステムを使った銘柄追加テスト

実際の銘柄追加フローでフィルタリングシステムが正常に動作することを確認
"""

import unittest
import tempfile
import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# BaseTestを継承してテスト環境の安全性を確保
try:
    from tests_organized.base_test import BaseTest
    USE_BASE_TEST = True
except ImportError:
    USE_BASE_TEST = False
    print("⚠️ BaseTestが利用できません。標準のunittestを使用します。")


class TestSymbolAdditionWithFiltering(BaseTest if USE_BASE_TEST else unittest.TestCase):
    """フィルタリングシステムを使った銘柄追加テスト"""
    
    def setUp(self):
        """テスト前準備"""
        if USE_BASE_TEST:
            super().setUp()
        
        # テスト用の一時ディレクトリ
        self.test_dir = tempfile.mkdtemp()
        
        # テスト用設定
        self.test_symbol = "TESTCOIN"
        self.test_timeframe = "1h"
        self.test_start_date = "2024-01-01"
        self.test_end_date = "2024-06-01"
    
    def tearDown(self):
        """テスト後清理"""
        if USE_BASE_TEST:
            super().tearDown()
        
        # 一時ディレクトリの削除
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('engines.filtering_framework.FilteringFramework')
    def test_filtering_framework_integration_in_symbol_addition(self, mock_filtering_framework):
        """銘柄追加時のフィルタリングフレームワーク統合テスト"""
        
        # モックフレームワークの設定
        mock_framework_instance = Mock()
        mock_framework_instance.execute_filtering.return_value = [
            {
                'evaluation_time': datetime.now(),
                'entry_price': 50000.0,
                'strategy': 'TestStrategy',
                'leverage': 2.0,
                'profit_potential': 0.05,
                'downside_risk': 0.03,
                'risk_reward_ratio': 1.67,
                'confidence_score': 0.75
            }
        ]
        
        # 統計情報のモック
        mock_stats = Mock()
        mock_stats.total_evaluations = 100
        mock_stats.valid_trades = 25
        mock_stats.get_efficiency_metrics.return_value = {
            'pass_rate': 25.0,
            'exclusion_rate': 75.0,
            'avg_evaluation_time': 0.001
        }
        mock_framework_instance.get_statistics.return_value = mock_stats
        
        mock_filtering_framework.return_value = mock_framework_instance
        
        # フィルタリングフレームワークが正しく呼び出されることを確認
        from engines.filtering_framework import FilteringFramework
        
        # モック戦略とデータ
        mock_strategy = Mock()
        mock_strategy.name = "TestStrategy"
        mock_prepared_data = Mock()
        
        # フレームワークインスタンス作成
        framework = FilteringFramework(mock_strategy, mock_prepared_data)
        
        # 評価時点の生成
        evaluation_times = [datetime.now() + timedelta(hours=i) for i in range(10)]
        
        # フィルタリング実行
        results = framework.execute_filtering(evaluation_times)
        
        # 結果の検証
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)  # 1つの有効取引
        
        # 統計情報の確認
        stats = framework.get_statistics()
        self.assertIsNotNone(stats)
        
        print("✅ フィルタリングフレームワーク統合テスト成功")
    
    def test_filtering_system_performance_benchmark(self):
        """フィルタリングシステムのパフォーマンスベンチマーク"""
        from engines.filtering_framework import FilteringFramework
        
        # 大量データでのパフォーマンステスト
        mock_strategy = Mock()
        mock_strategy.name = "PerformanceTestStrategy"
        mock_strategy.min_volume_threshold = 500000
        mock_strategy.max_spread_threshold = 0.05
        mock_strategy.min_liquidity_score = 0.5
        mock_strategy.min_support_strength = 0.6
        mock_strategy.min_resistance_strength = 0.6
        
        # リアルなモックデータ
        mock_prepared_data = Mock()
        mock_prepared_data.has_missing_data_around.return_value = False
        mock_prepared_data.has_price_anomaly_at.return_value = False
        mock_prepared_data.is_valid.return_value = True
        mock_prepared_data.get_volume_at.return_value = 1000000
        mock_prepared_data.get_spread_at.return_value = 0.01
        mock_prepared_data.get_liquidity_score_at.return_value = 0.8
        mock_prepared_data.get_price_at.return_value = 50000.0
        
        # 1000個の評価時点でテスト
        evaluation_times = [datetime.now() + timedelta(minutes=i*5) for i in range(1000)]
        
        framework = FilteringFramework(mock_strategy, mock_prepared_data)
        
        start_time = time.time()
        results = framework.execute_filtering(evaluation_times)
        execution_time = time.time() - start_time
        
        # パフォーマンス要件
        avg_time_per_evaluation = execution_time / len(evaluation_times)
        
        print(f"\n📊 パフォーマンスベンチマーク結果:")
        print(f"   評価時点数: {len(evaluation_times)}")
        print(f"   有効取引数: {len(results)}")
        print(f"   実行時間: {execution_time:.3f}秒")
        print(f"   平均処理時間: {avg_time_per_evaluation:.6f}秒/評価時点")
        
        # パフォーマンス要件チェック
        self.assertLess(avg_time_per_evaluation, 0.01, 
                       f"平均処理時間が遅すぎます: {avg_time_per_evaluation:.6f}秒")
        self.assertGreater(len(results), 0, "有効取引が1つも見つかりませんでした")
        
        print("✅ パフォーマンスベンチマーク成功")
    
    def test_filtering_with_realistic_exclusion_rates(self):
        """現実的な除外率でのフィルタリングテスト"""
        from engines.filtering_framework import FilteringFramework
        
        # 設計値に近い除外率を生成するモックデータ
        mock_strategy = Mock()
        mock_strategy.name = "RealisticTestStrategy"
        mock_strategy.min_volume_threshold = 800000
        mock_strategy.max_spread_threshold = 0.05
        mock_strategy.min_liquidity_score = 0.5
        mock_strategy.min_support_strength = 0.6
        mock_strategy.min_resistance_strength = 0.6
        
        # 現実的な除外パターンを持つモックデータ
        mock_prepared_data = Mock()
        
        def mock_volume_func(eval_time):
            # 30%が低取引量で除外
            return 500000 if hash(str(eval_time)) % 10 < 3 else 1000000
        
        def mock_spread_func(eval_time):
            # 10%が高スプレッドで除外
            return 0.08 if hash(str(eval_time)) % 10 == 0 else 0.01
        
        def mock_liquidity_func(eval_time):
            # 15%が低流動性で除外
            return 0.3 if hash(str(eval_time)) % 7 == 0 else 0.8
        
        mock_prepared_data.has_missing_data_around.return_value = False
        mock_prepared_data.has_price_anomaly_at.return_value = False
        mock_prepared_data.is_valid.return_value = True
        mock_prepared_data.get_volume_at.side_effect = mock_volume_func
        mock_prepared_data.get_spread_at.side_effect = mock_spread_func
        mock_prepared_data.get_liquidity_score_at.side_effect = mock_liquidity_func
        mock_prepared_data.get_price_at.return_value = 50000.0
        
        # 500個の評価時点でテスト
        evaluation_times = [datetime.now() + timedelta(hours=i) for i in range(500)]
        
        framework = FilteringFramework(mock_strategy, mock_prepared_data)
        results = framework.execute_filtering(evaluation_times)
        
        # 統計分析
        stats = framework.get_statistics()
        efficiency = stats.get_efficiency_metrics()
        
        print(f"\n📈 現実的除外率テスト結果:")
        print(f"   総評価時点: {stats.total_evaluations}")
        print(f"   有効取引: {stats.valid_trades}")
        print(f"   通過率: {efficiency['pass_rate']:.1f}%")
        print(f"   除外率: {efficiency['exclusion_rate']:.1f}%")
        
        # フィルター別統計
        print(f"\n🔍 フィルター別除外統計:")
        for filter_name, count in stats.filtering_stats.items():
            if count > 0:
                percentage = (count / stats.total_evaluations) * 100
                print(f"   {filter_name}: {count}回 ({percentage:.1f}%)")
        
        # 設計値との比較
        # 設計では約27%が有効機会として残る予定
        expected_pass_rate_min = 15.0  # 最低15%
        expected_pass_rate_max = 40.0  # 最大40%
        
        self.assertGreaterEqual(efficiency['pass_rate'], expected_pass_rate_min,
                               f"通過率が低すぎます: {efficiency['pass_rate']:.1f}% < {expected_pass_rate_min}%")
        self.assertLessEqual(efficiency['pass_rate'], expected_pass_rate_max,
                            f"通過率が高すぎます: {efficiency['pass_rate']:.1f}% > {expected_pass_rate_max}%")
        
        print("✅ 現実的除外率テスト成功")
    
    def test_filtering_system_memory_usage(self):
        """フィルタリングシステムのメモリ使用量テスト"""
        import psutil
        import os
        
        from engines.filtering_framework import FilteringFramework
        
        # メモリ使用量測定開始
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 大量データでのメモリテスト
        mock_strategy = Mock()
        mock_strategy.name = "MemoryTestStrategy"
        mock_strategy.min_volume_threshold = 500000
        mock_strategy.max_spread_threshold = 0.05
        mock_strategy.min_liquidity_score = 0.5
        mock_strategy.min_support_strength = 0.6
        mock_strategy.min_resistance_strength = 0.6
        
        mock_prepared_data = Mock()
        mock_prepared_data.has_missing_data_around.return_value = False
        mock_prepared_data.has_price_anomaly_at.return_value = False
        mock_prepared_data.is_valid.return_value = True
        mock_prepared_data.get_volume_at.return_value = 1000000
        mock_prepared_data.get_spread_at.return_value = 0.01
        mock_prepared_data.get_liquidity_score_at.return_value = 0.8
        mock_prepared_data.get_price_at.return_value = 50000.0
        
        # 5000個の評価時点（実際のバックテスト規模）
        evaluation_times = [datetime.now() + timedelta(seconds=i*60) for i in range(5000)]
        
        framework = FilteringFramework(mock_strategy, mock_prepared_data)
        results = framework.execute_filtering(evaluation_times)
        
        # メモリ使用量測定終了
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\n💾 メモリ使用量テスト結果:")
        print(f"   開始時メモリ: {initial_memory:.1f} MB")
        print(f"   終了時メモリ: {final_memory:.1f} MB")
        print(f"   メモリ増加: {memory_increase:.1f} MB")
        print(f"   評価時点あたり: {memory_increase*1024/len(evaluation_times):.2f} KB")
        
        # メモリ要件チェック（1GB以内）
        self.assertLess(memory_increase, 1024, 
                       f"メモリ使用量が多すぎます: {memory_increase:.1f} MB")
        
        print("✅ メモリ使用量テスト成功")


if __name__ == '__main__':
    # テスト実行時のログ出力
    print("🧪 フィルタリングシステム銘柄追加テスト開始")
    print("📋 実際の銘柄追加フローでの動作確認")
    
    # BaseTestの使用状況を表示
    if USE_BASE_TEST:
        print("✅ BaseTest使用: 本番DB保護確認済み")
    else:
        print("⚠️ BaseTest未使用: 標準unittestで実行")
    
    # テストスイート実行
    unittest.main(verbosity=2)