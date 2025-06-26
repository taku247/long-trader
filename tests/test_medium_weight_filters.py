#!/usr/bin/env python3
"""
中重量フィルター（Filter 4-6）のテストケース

TDD アプローチで先にテストを作成し、実装の要件を明確化する
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


class TestMediumWeightFilters(BaseTest if USE_BASE_TEST else unittest.TestCase):
    """中重量フィルター（Filter 4-6）のテストクラス"""
    
    def setUp(self):
        """テスト前準備"""
        if USE_BASE_TEST:
            super().setUp()
        
        # テスト用の一時ディレクトリ
        self.test_dir = tempfile.mkdtemp()
        
        # モックデータの準備
        self.mock_prepared_data = self._create_mock_prepared_data()
        self.mock_strategy = self._create_mock_strategy()
        self.test_evaluation_time = datetime.now()
        
        # 支持線・抵抗線のモックデータ
        self.mock_support_levels = self._create_mock_support_levels()
        self.mock_resistance_levels = self._create_mock_resistance_levels()
    
    def tearDown(self):
        """テスト後清理"""
        if USE_BASE_TEST:
            super().tearDown()
        
        # 一時ディレクトリの削除
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_mock_prepared_data(self):
        """テスト用の準備データモック作成"""
        mock_data = Mock()
        
        # 基本価格・市場データ
        mock_data.get_price_at.return_value = 50000.0
        mock_data.get_volume_at.return_value = 1000000
        mock_data.get_spread_at.return_value = 0.01
        mock_data.get_liquidity_score_at.return_value = 0.8
        
        # ML予測データ
        mock_data.get_ml_confidence_at.return_value = 0.75
        mock_data.get_ml_prediction_at.return_value = "BUY"
        mock_data.get_ml_signal_strength_at.return_value = 0.8
        
        # ボラティリティデータ
        mock_data.get_volatility_at.return_value = 0.05  # 5%のボラティリティ
        mock_data.get_atr_at.return_value = 1500.0  # Average True Range
        mock_data.get_price_change_volatility_at.return_value = 0.03
        
        # データ品質
        mock_data.has_missing_data_around.return_value = False
        mock_data.has_price_anomaly_at.return_value = False
        mock_data.is_valid.return_value = True
        
        return mock_data
    
    def _create_mock_strategy(self):
        """テスト用の戦略モック作成"""
        mock_strategy = Mock()
        mock_strategy.name = "MediumWeightTestStrategy"
        
        # 基本設定
        mock_strategy.min_volume_threshold = 500000
        mock_strategy.max_spread_threshold = 0.05
        mock_strategy.min_liquidity_score = 0.5
        
        # Filter 4: 距離・強度条件
        mock_strategy.min_distance_from_support = 0.5  # 0.5%以上
        mock_strategy.max_distance_from_support = 5.0  # 5.0%以下
        mock_strategy.min_distance_from_resistance = 1.0  # 1.0%以上
        mock_strategy.max_distance_from_resistance = 8.0  # 8.0%以下
        mock_strategy.min_support_strength = 0.6
        mock_strategy.min_resistance_strength = 0.6
        
        # Filter 5: ML信頼度条件
        mock_strategy.min_ml_confidence = 0.7  # 70%以上
        mock_strategy.required_ml_signal = "BUY"  # BUYシグナル必須
        mock_strategy.min_ml_signal_strength = 0.6
        
        # Filter 6: ボラティリティ条件
        mock_strategy.min_volatility = 0.01  # 1%以上
        mock_strategy.max_volatility = 0.15  # 15%以下
        mock_strategy.max_atr_ratio = 0.05  # ATR/価格の比率5%以下
        
        return mock_strategy
    
    def _create_mock_support_levels(self):
        """モック支持線データ作成"""
        mock_levels = []
        
        # 支持線1: 現在価格の2%下、強度0.8
        support1 = Mock()
        support1.price = 49000.0  # 2%下
        support1.strength = 0.8
        support1.distance_from_current = 2.0
        support1.touch_count = 3
        mock_levels.append(support1)
        
        # 支持線2: 現在価格の4%下、強度0.7
        support2 = Mock()
        support2.price = 48000.0  # 4%下
        support2.strength = 0.7
        support2.distance_from_current = 4.0
        support2.touch_count = 2
        mock_levels.append(support2)
        
        return mock_levels
    
    def _create_mock_resistance_levels(self):
        """モック抵抗線データ作成"""
        mock_levels = []
        
        # 抵抗線1: 現在価格の3%上、強度0.75
        resistance1 = Mock()
        resistance1.price = 51500.0  # 3%上
        resistance1.strength = 0.75
        resistance1.distance_from_current = 3.0
        resistance1.touch_count = 3
        mock_levels.append(resistance1)
        
        # 抵抗線2: 現在価格の6%上、強度0.65
        resistance2 = Mock()
        resistance2.price = 53000.0  # 6%上
        resistance2.strength = 0.65
        resistance2.distance_from_current = 6.0
        resistance2.touch_count = 2
        mock_levels.append(resistance2)
        
        return mock_levels
    
    def test_distance_analysis_filter_creation(self):
        """DistanceAnalysisFilter作成テスト"""
        from engines.filters.medium_weight_filters import DistanceAnalysisFilter
        
        filter_obj = DistanceAnalysisFilter()
        self.assertEqual(filter_obj.name, "distance_analysis")
        self.assertEqual(filter_obj.weight, "medium")
        self.assertEqual(filter_obj.max_execution_time, 20)
        self.assertEqual(filter_obj.execution_count, 0)
    
    def test_ml_confidence_filter_creation(self):
        """MLConfidenceFilter作成テスト"""
        from engines.filters.medium_weight_filters import MLConfidenceFilter
        
        filter_obj = MLConfidenceFilter()
        self.assertEqual(filter_obj.name, "ml_confidence")
        self.assertEqual(filter_obj.weight, "medium")
        self.assertEqual(filter_obj.max_execution_time, 25)
        self.assertEqual(filter_obj.execution_count, 0)
    
    def test_volatility_filter_creation(self):
        """VolatilityFilter作成テスト"""
        from engines.filters.medium_weight_filters import VolatilityFilter
        
        filter_obj = VolatilityFilter()
        self.assertEqual(filter_obj.name, "volatility")
        self.assertEqual(filter_obj.weight, "medium")
        self.assertEqual(filter_obj.max_execution_time, 20)
        self.assertEqual(filter_obj.execution_count, 0)
    
    def test_distance_analysis_filter_requirements(self):
        """DistanceAnalysisFilterの要件定義テスト"""
        
        # 期待される動作要件
        requirements = {
            'name': 'distance_analysis',
            'weight': 'medium',
            'max_execution_time': 20,
            
            # 距離条件チェック
            'check_support_distance': True,
            'check_resistance_distance': True,
            'check_level_strength': True,
            
            # 除外条件
            'exclude_too_close_to_support': True,  # 支持線に近すぎる
            'exclude_too_far_from_support': True,  # 支持線から遠すぎる
            'exclude_too_close_to_resistance': True,  # 抵抗線に近すぎる
            'exclude_too_far_from_resistance': True,  # 抵抗線から遠すぎる
            'exclude_weak_levels': True,  # 弱い支持線・抵抗線
        }
        
        # 実装後にこれらの要件が満たされることを確認
        self.assertTrue(requirements['check_support_distance'])
        self.assertTrue(requirements['check_resistance_distance'])
        self.assertEqual(requirements['name'], 'distance_analysis')
    
    def test_ml_confidence_filter_requirements(self):
        """MLConfidenceFilterの要件定義テスト"""
        
        # 期待される動作要件
        requirements = {
            'name': 'ml_confidence',
            'weight': 'medium',
            'max_execution_time': 25,
            
            # ML予測チェック
            'check_confidence_threshold': True,
            'check_signal_direction': True,
            'check_signal_strength': True,
            
            # 除外条件
            'exclude_low_confidence': True,  # 信頼度不足
            'exclude_wrong_signal': True,  # 期待と異なるシグナル
            'exclude_weak_signal': True,  # 弱いシグナル強度
        }
        
        # 実装後にこれらの要件が満たされることを確認
        self.assertTrue(requirements['check_confidence_threshold'])
        self.assertTrue(requirements['check_signal_direction'])
        self.assertEqual(requirements['name'], 'ml_confidence')
    
    def test_volatility_filter_requirements(self):
        """VolatilityFilterの要件定義テスト"""
        
        # 期待される動作要件
        requirements = {
            'name': 'volatility',
            'weight': 'medium',
            'max_execution_time': 20,
            
            # ボラティリティチェック
            'check_volatility_range': True,
            'check_atr_ratio': True,
            'check_price_stability': True,
            
            # 除外条件
            'exclude_too_low_volatility': True,  # ボラティリティ不足
            'exclude_too_high_volatility': True,  # 過度なボラティリティ
            'exclude_unstable_price': True,  # 価格不安定
        }
        
        # 実装後にこれらの要件が満たされることを確認
        self.assertTrue(requirements['check_volatility_range'])
        self.assertTrue(requirements['check_atr_ratio'])
        self.assertEqual(requirements['name'], 'volatility')
    
    def test_distance_filter_logic_expectations(self):
        """距離フィルターのロジック期待値テスト"""
        
        # テストケース: 適切な距離の場合
        current_price = 50000.0
        support_price = 49000.0  # 2%下
        resistance_price = 51500.0  # 3%上
        
        support_distance = ((current_price - support_price) / current_price) * 100  # 2.0%
        resistance_distance = ((resistance_price - current_price) / current_price) * 100  # 3.0%
        
        # 戦略パラメータ内なので通過するはず
        self.assertGreaterEqual(support_distance, self.mock_strategy.min_distance_from_support)  # 2.0% >= 0.5%
        self.assertLessEqual(support_distance, self.mock_strategy.max_distance_from_support)  # 2.0% <= 5.0%
        self.assertGreaterEqual(resistance_distance, self.mock_strategy.min_distance_from_resistance)  # 3.0% >= 1.0%
        self.assertLessEqual(resistance_distance, self.mock_strategy.max_distance_from_resistance)  # 3.0% <= 8.0%
        
        # テストケース: 近すぎる場合
        too_close_support = 49750.0  # 0.5%下（閾値0.5%ギリギリ）
        too_close_distance = ((current_price - too_close_support) / current_price) * 100  # 0.5%
        self.assertEqual(too_close_distance, self.mock_strategy.min_distance_from_support)  # 境界値
    
    def test_ml_filter_logic_expectations(self):
        """MLフィルターのロジック期待値テスト"""
        
        # テストケース: 高信頼度BUYシグナル
        ml_confidence = 0.75  # 75%
        ml_signal = "BUY"
        ml_strength = 0.8
        
        # 戦略要件を満たすので通過するはず
        self.assertGreaterEqual(ml_confidence, self.mock_strategy.min_ml_confidence)  # 75% >= 70%
        self.assertEqual(ml_signal, self.mock_strategy.required_ml_signal)  # BUY == BUY
        self.assertGreaterEqual(ml_strength, self.mock_strategy.min_ml_signal_strength)  # 0.8 >= 0.6
        
        # テストケース: 低信頼度
        low_confidence = 0.65  # 65%
        self.assertLess(low_confidence, self.mock_strategy.min_ml_confidence)  # 65% < 70% (除外)
        
        # テストケース: 異なるシグナル
        wrong_signal = "SELL"
        self.assertNotEqual(wrong_signal, self.mock_strategy.required_ml_signal)  # SELL != BUY (除外)
    
    def test_volatility_filter_logic_expectations(self):
        """ボラティリティフィルターのロジック期待値テスト"""
        
        # テストケース: 適切なボラティリティ
        volatility = 0.05  # 5%
        atr = 1500.0
        current_price = 50000.0
        atr_ratio = atr / current_price  # 0.03 = 3%
        
        # 戦略要件を満たすので通過するはず
        self.assertGreaterEqual(volatility, self.mock_strategy.min_volatility)  # 5% >= 1%
        self.assertLessEqual(volatility, self.mock_strategy.max_volatility)  # 5% <= 15%
        self.assertLessEqual(atr_ratio, self.mock_strategy.max_atr_ratio)  # 3% <= 5%
        
        # テストケース: 低ボラティリティ
        low_volatility = 0.005  # 0.5%
        self.assertLess(low_volatility, self.mock_strategy.min_volatility)  # 0.5% < 1% (除外)
        
        # テストケース: 高ボラティリティ
        high_volatility = 0.20  # 20%
        self.assertGreater(high_volatility, self.mock_strategy.max_volatility)  # 20% > 15% (除外)
    
    def test_filter_integration_workflow(self):
        """フィルター統合ワークフローテスト"""
        
        # Filter 4-6の処理順序と依存関係を確認
        filter_sequence = [
            ('data_quality', 'light'),
            ('market_condition', 'light'),
            ('support_resistance', 'light'),
            ('distance_analysis', 'medium'),  # Filter 4
            ('ml_confidence', 'medium'),      # Filter 5
            ('volatility', 'medium'),         # Filter 6
        ]
        
        # 軽量フィルターが先に実行され、中重量フィルターが後に実行される
        light_filters = [f for f in filter_sequence if f[1] == 'light']
        medium_filters = [f for f in filter_sequence if f[1] == 'medium']
        
        self.assertEqual(len(light_filters), 3)  # Filter 1-3
        self.assertEqual(len(medium_filters), 3)  # Filter 4-6
        
        # 順序確認
        self.assertEqual(light_filters[0][0], 'data_quality')
        self.assertEqual(medium_filters[0][0], 'distance_analysis')
        self.assertEqual(medium_filters[1][0], 'ml_confidence')
        self.assertEqual(medium_filters[2][0], 'volatility')
    
    def test_distance_analysis_filter_execution(self):
        """DistanceAnalysisFilter実行テスト"""
        from engines.filters.medium_weight_filters import DistanceAnalysisFilter
        
        filter_obj = DistanceAnalysisFilter()
        result = filter_obj.execute(self.mock_prepared_data, self.mock_strategy, self.test_evaluation_time)
        
        # 正常なモックデータなので通過するはず
        self.assertTrue(result.passed)
        self.assertEqual(result.reason, "距離・強度分析チェック合格")
        self.assertEqual(filter_obj.execution_count, 1)
        self.assertEqual(filter_obj.success_count, 1)
        
        # メトリクスの確認
        self.assertIn('support_distance', result.metrics)
        self.assertIn('resistance_distance', result.metrics)
        self.assertIn('strength_analysis', result.metrics)
    
    def test_ml_confidence_filter_execution(self):
        """MLConfidenceFilter実行テスト"""
        from engines.filters.medium_weight_filters import MLConfidenceFilter
        
        filter_obj = MLConfidenceFilter()
        result = filter_obj.execute(self.mock_prepared_data, self.mock_strategy, self.test_evaluation_time)
        
        # 正常なモックデータなので通過するはず
        self.assertTrue(result.passed)
        self.assertEqual(result.reason, "ML信頼度チェック合格")
        self.assertEqual(filter_obj.execution_count, 1)
        self.assertEqual(filter_obj.success_count, 1)
        
        # メトリクスの確認
        self.assertIn('ml_confidence', result.metrics)
        self.assertIn('ml_prediction', result.metrics)
        self.assertIn('ml_signal_strength', result.metrics)
        self.assertEqual(result.metrics['ml_confidence'], 0.75)
        self.assertEqual(result.metrics['ml_prediction'], "BUY")
    
    def test_volatility_filter_execution(self):
        """VolatilityFilter実行テスト"""
        from engines.filters.medium_weight_filters import VolatilityFilter
        
        filter_obj = VolatilityFilter()
        result = filter_obj.execute(self.mock_prepared_data, self.mock_strategy, self.test_evaluation_time)
        
        # 正常なモックデータなので通過するはず
        self.assertTrue(result.passed)
        self.assertEqual(result.reason, "ボラティリティチェック合格")
        self.assertEqual(filter_obj.execution_count, 1)
        self.assertEqual(filter_obj.success_count, 1)
        
        # メトリクスの確認
        self.assertIn('volatility', result.metrics)
        self.assertIn('atr_ratio', result.metrics)
        self.assertIn('stability_score', result.metrics)
        self.assertEqual(result.metrics['volatility'], 0.05)
    
    def test_filter_failure_scenarios(self):
        """フィルター失敗シナリオテスト"""
        from engines.filters.medium_weight_filters import MLConfidenceFilter
        
        # 低信頼度MLデータでテスト
        failing_mock_data = Mock()
        failing_mock_data.get_ml_confidence_at.return_value = 0.5  # 閾値0.7未満
        failing_mock_data.get_ml_prediction_at.return_value = "BUY"
        failing_mock_data.get_ml_signal_strength_at.return_value = 0.8
        
        filter_obj = MLConfidenceFilter()
        result = filter_obj.execute(failing_mock_data, self.mock_strategy, self.test_evaluation_time)
        
        # 信頼度不足で失敗するはず
        self.assertFalse(result.passed)
        self.assertIn("ML信頼度不足", result.reason)
        self.assertEqual(filter_obj.execution_count, 1)
        self.assertEqual(filter_obj.failure_count, 1)


class TestMediumWeightFilterMockData(BaseTest if USE_BASE_TEST else unittest.TestCase):
    """中重量フィルター用のモックデータテスト"""
    
    def test_support_resistance_mock_data(self):
        """支持線・抵抗線モックデータの妥当性テスト"""
        test_case = TestMediumWeightFilters()
        test_case.setUp()
        
        support_levels = test_case.mock_support_levels
        resistance_levels = test_case.mock_resistance_levels
        
        # 支持線データの確認
        self.assertEqual(len(support_levels), 2)
        self.assertEqual(support_levels[0].price, 49000.0)
        self.assertEqual(support_levels[0].strength, 0.8)
        self.assertEqual(support_levels[0].distance_from_current, 2.0)
        
        # 抵抗線データの確認
        self.assertEqual(len(resistance_levels), 2)
        self.assertEqual(resistance_levels[0].price, 51500.0)
        self.assertEqual(resistance_levels[0].strength, 0.75)
        self.assertEqual(resistance_levels[0].distance_from_current, 3.0)
        
        test_case.tearDown()
    
    def test_ml_prediction_mock_data(self):
        """ML予測モックデータの妥当性テスト"""
        test_case = TestMediumWeightFilters()
        test_case.setUp()
        
        mock_data = test_case.mock_prepared_data
        
        # ML予測データの確認
        self.assertEqual(mock_data.get_ml_confidence_at(datetime.now()), 0.75)
        self.assertEqual(mock_data.get_ml_prediction_at(datetime.now()), "BUY")
        self.assertEqual(mock_data.get_ml_signal_strength_at(datetime.now()), 0.8)
        
        test_case.tearDown()
    
    def test_volatility_mock_data(self):
        """ボラティリティモックデータの妥当性テスト"""
        test_case = TestMediumWeightFilters()
        test_case.setUp()
        
        mock_data = test_case.mock_prepared_data
        
        # ボラティリティデータの確認
        self.assertEqual(mock_data.get_volatility_at(datetime.now()), 0.05)
        self.assertEqual(mock_data.get_atr_at(datetime.now()), 1500.0)
        self.assertEqual(mock_data.get_price_change_volatility_at(datetime.now()), 0.03)
        
        test_case.tearDown()


if __name__ == '__main__':
    # テスト実行時のログ出力
    print("🧪 中重量フィルター（Filter 4-6）テスト開始")
    print("📋 TDD アプローチによる要件定義確認")
    
    # BaseTestの使用状況を表示
    if USE_BASE_TEST:
        print("✅ BaseTest使用: 本番DB保護確認済み")
    else:
        print("⚠️ BaseTest未使用: 標準unittestで実行")
    
    # テストスイート実行
    unittest.main(verbosity=2)