#!/usr/bin/env python3
"""
フィルタリングシステム統合テスト

実際のデータを使った統合テストとパフォーマンステスト
"""

import unittest
import tempfile
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# BaseTestを継承してテスト環境の安全性を確保
try:
    from tests_organized.base_test import BaseTest
    USE_BASE_TEST = True
except ImportError:
    USE_BASE_TEST = False
    print("⚠️ BaseTestが利用できません。標準のunittestを使用します。")


class TestFilteringIntegration(BaseTest if USE_BASE_TEST else unittest.TestCase):
    """フィルタリングシステム統合テスト"""
    
    def setUp(self):
        """テスト前準備"""
        if USE_BASE_TEST:
            super().setUp()
        
        # テスト用の一時ディレクトリ
        self.test_dir = tempfile.mkdtemp()
        
        # 統合テスト用のモックデータ
        self.mock_prepared_data = self._create_realistic_mock_data()
        self.mock_strategy = self._create_test_strategy()
        
        # 評価時点の生成（100個）
        self.evaluation_times = self._generate_evaluation_times(100)
    
    def tearDown(self):
        """テスト後清理"""
        if USE_BASE_TEST:
            super().tearDown()
        
        # 一時ディレクトリの削除
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_realistic_mock_data(self):
        """より現実的なモックデータを作成"""
        mock_data = Mock()
        
        # データ品質に変化を持たせる
        def mock_has_missing_data(eval_time):
            # 評価時点の時間に基づいて、1%の確率でデータ欠損
            return hash(str(eval_time)) % 100 == 0
        
        def mock_has_price_anomaly(eval_time):
            # 2%の確率で価格異常
            return hash(str(eval_time)) % 50 == 0
        
        def mock_get_volume(eval_time):
            # 30%が低取引量
            base_volume = 1000000
            if hash(str(eval_time)) % 10 < 3:
                return base_volume * 0.3  # 低取引量
            return base_volume
        
        def mock_get_spread(eval_time):
            # 20%が高スプレッド
            if hash(str(eval_time)) % 5 == 0:
                return 0.08  # 高スプレッド
            return 0.01  # 正常スプレッド
        
        def mock_get_liquidity_score(eval_time):
            # 15%が低流動性
            if hash(str(eval_time)) % 7 == 0:
                return 0.3  # 低流動性
            return 0.8  # 正常流動性
        
        # モック関数を設定
        mock_data.has_missing_data_around.side_effect = mock_has_missing_data
        mock_data.has_price_anomaly_at.side_effect = mock_has_price_anomaly
        mock_data.get_volume_at.side_effect = mock_get_volume
        mock_data.get_spread_at.side_effect = mock_get_spread
        mock_data.get_liquidity_score_at.side_effect = mock_get_liquidity_score
        mock_data.get_price_at.return_value = 50000.0
        mock_data.is_valid.return_value = True
        
        return mock_data
    
    def _create_test_strategy(self):
        """テスト戦略を作成"""
        mock_strategy = Mock()
        mock_strategy.name = "IntegrationTestStrategy"
        mock_strategy.min_volume_threshold = 800000
        mock_strategy.max_spread_threshold = 0.05
        mock_strategy.min_liquidity_score = 0.5
        mock_strategy.min_support_strength = 0.6
        mock_strategy.min_resistance_strength = 0.6
        return mock_strategy
    
    def _generate_evaluation_times(self, count: int):
        """評価時点リストを生成"""
        base_time = datetime.now()
        return [base_time + timedelta(hours=i) for i in range(count)]
    
    def test_filtering_framework_integration(self):
        """フィルタリングフレームワーク統合テスト"""
        from engines.filtering_framework import FilteringFramework
        
        # 進捗コールバックのモック
        progress_updates = []
        def progress_callback(update):
            progress_updates.append(update)
        
        # フィルタリングフレームワークを初期化
        framework = FilteringFramework(
            strategy=self.mock_strategy,
            prepared_data=self.mock_prepared_data,
            progress_callback=progress_callback
        )
        
        # フィルターチェーンが構築されていることを確認
        self.assertGreater(len(framework.filter_chain), 0)
        self.assertEqual(framework.filter_chain[0].name, "data_quality")
        
        # フィルタリング実行
        valid_trades = framework.execute_filtering(self.evaluation_times)
        
        # 結果の検証
        self.assertIsInstance(valid_trades, list)
        
        # 統計情報の確認
        stats = framework.get_statistics()
        self.assertEqual(stats.total_evaluations, len(self.evaluation_times))
        self.assertGreaterEqual(stats.valid_trades, 0)
        self.assertLessEqual(stats.valid_trades, len(self.evaluation_times))
        
        # 進捗更新が呼ばれたことを確認
        self.assertGreater(len(progress_updates), 0)
        
        # 効率指標の確認
        efficiency = stats.get_efficiency_metrics()
        self.assertIn('pass_rate', efficiency)
        self.assertIn('exclusion_rate', efficiency)
        self.assertGreaterEqual(efficiency['pass_rate'], 0)
        self.assertLessEqual(efficiency['pass_rate'], 100)
    
    def test_filter_chain_early_termination(self):
        """フィルターチェーンの早期終了テスト"""
        from engines.filtering_framework import FilteringFramework
        
        # データ品質で必ず失敗するモックデータ
        failing_mock_data = Mock()
        failing_mock_data.has_missing_data_around.return_value = True  # 常にデータ欠損
        failing_mock_data.has_price_anomaly_at.return_value = False
        failing_mock_data.is_valid.return_value = True
        
        framework = FilteringFramework(
            strategy=self.mock_strategy,
            prepared_data=failing_mock_data
        )
        
        # 単一評価時点でテスト
        single_evaluation = [datetime.now()]
        valid_trades = framework.execute_filtering(single_evaluation)
        
        # 全て除外されるはず
        self.assertEqual(len(valid_trades), 0)
        
        # Filter 1で除外されたことを確認
        stats = framework.get_statistics()
        self.assertEqual(stats.filtering_stats['filter_1'], 1)
        self.assertEqual(stats.filtering_stats['filter_2'], 0)  # Filter 2には到達しない
    
    def test_performance_measurement(self):
        """パフォーマンス測定テスト"""
        from engines.filtering_framework import FilteringFramework
        import time
        
        # 大量の評価時点でテスト
        large_evaluation_times = self._generate_evaluation_times(500)
        
        framework = FilteringFramework(
            strategy=self.mock_strategy,
            prepared_data=self.mock_prepared_data
        )
        
        start_time = time.time()
        valid_trades = framework.execute_filtering(large_evaluation_times)
        execution_time = time.time() - start_time
        
        # パフォーマンス要件のチェック
        avg_time_per_evaluation = execution_time / len(large_evaluation_times)
        self.assertLess(avg_time_per_evaluation, 0.1, 
                       f"評価時点あたりの処理時間が遅すぎます: {avg_time_per_evaluation:.4f}秒")
        
        # 統計情報の確認
        stats = framework.get_statistics()
        efficiency = stats.get_efficiency_metrics()
        
        print(f"\n📊 パフォーマンステスト結果:")
        print(f"   総評価時点: {len(large_evaluation_times)}")
        print(f"   有効取引: {len(valid_trades)}")
        print(f"   通過率: {efficiency['pass_rate']:.1f}%")
        print(f"   実行時間: {execution_time:.2f}秒")
        print(f"   平均処理時間: {avg_time_per_evaluation:.4f}秒/評価時点")
    
    def test_filter_statistics_accuracy(self):
        """フィルター統計の正確性テスト"""
        from engines.filtering_framework import FilteringFramework
        
        framework = FilteringFramework(
            strategy=self.mock_strategy,
            prepared_data=self.mock_prepared_data
        )
        
        # 少数の評価時点で詳細確認
        test_evaluation_times = self._generate_evaluation_times(20)
        valid_trades = framework.execute_filtering(test_evaluation_times)
        
        stats = framework.get_statistics()
        
        # 統計の整合性チェック
        total_excluded = sum(stats.filtering_stats.values())
        total_passed = stats.valid_trades
        
        self.assertEqual(total_excluded + total_passed, len(test_evaluation_times),
                        "除外数 + 通過数 = 総評価数でない")
        
        # 個別フィルターの統計確認
        for filter_obj in framework.filter_chain:
            filter_stats = filter_obj.get_statistics()
            self.assertGreaterEqual(filter_stats['execution_count'], 0)
            self.assertEqual(
                filter_stats['success_count'] + filter_stats['failure_count'],
                filter_stats['execution_count'],
                f"Filter {filter_obj.name} の統計に不整合"
            )
    
    def test_error_handling_robustness(self):
        """エラーハンドリングの堅牢性テスト"""
        from engines.filtering_framework import FilteringFramework
        
        # エラーを発生させるモックデータ
        error_mock_data = Mock()
        error_mock_data.has_missing_data_around.side_effect = Exception("テスト例外")
        error_mock_data.has_price_anomaly_at.return_value = False
        error_mock_data.is_valid.return_value = True
        
        framework = FilteringFramework(
            strategy=self.mock_strategy,
            prepared_data=error_mock_data
        )
        
        # エラーが発生しても処理が継続することを確認
        test_evaluation_times = [datetime.now()]
        valid_trades = framework.execute_filtering(test_evaluation_times)
        
        # エラーにより除外されるはず
        self.assertEqual(len(valid_trades), 0)
        
        # エラー統計の確認
        stats = framework.get_statistics()
        self.assertEqual(stats.filtering_stats['filter_1'], 1)


if __name__ == '__main__':
    # テスト実行時のログ出力
    print("🧪 フィルタリングシステム統合テスト開始")
    print("📋 実際のデータフローを使った統合検証")
    
    # BaseTestの使用状況を表示
    if USE_BASE_TEST:
        print("✅ BaseTest使用: 本番DB保護確認済み")
    else:
        print("⚠️ BaseTest未使用: 標準unittestで実行")
    
    # テストスイート実行
    unittest.main(verbosity=2)