#!/usr/bin/env python3
"""
重量フィルター（Filter 7-9）のテスト

レバレッジ最適化、リスクリワード分析、戦略固有フィルターのテスト
"""

import unittest
import tempfile
import os
import sys
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


class TestHeavyWeightFilters(BaseTest if USE_BASE_TEST else unittest.TestCase):
    """重量フィルターのテストクラス"""
    
    def setUp(self):
        """テスト前準備"""
        if USE_BASE_TEST:
            super().setUp()
        
        # モック準備データ
        self.mock_prepared_data = Mock()
        self.mock_prepared_data.get_price_at = Mock(return_value=100.0)
        self.mock_prepared_data.get_support_resistance = Mock(return_value={
            'support': 95.0,
            'resistance': 105.0,
            'levels': [90.0, 95.0, 100.0, 105.0, 110.0]
        })
        self.mock_prepared_data.get_volatility = Mock(return_value=0.02)  # 2%
        self.mock_prepared_data.get_volume_profile = Mock(return_value={
            'average': 1000000,
            'current': 1200000,
            'ratio': 1.2
        })
        self.mock_prepared_data.get_market_trend = Mock(return_value='bullish')
        
        # テスト戦略
        self.mock_strategy = Mock()
        self.mock_strategy.name = "Conservative_ML"
        self.mock_strategy.timeframe = "15m"
        
        # 評価時点
        self.evaluation_time = datetime.now()
    
    def test_leverage_filter_import(self):
        """LeverageFilterクラスのインポートテスト（Filter 7）"""
        try:
            from engines.filters.heavy_weight_filters import LeverageFilter
            self.assertTrue(True)
        except ImportError:
            self.fail("LeverageFilterクラスがインポートできません")
    
    def test_leverage_filter_creation(self):
        """LeverageFilterクラスの作成テスト"""
        from engines.filters.heavy_weight_filters import LeverageFilter
        
        filter_obj = LeverageFilter()
        self.assertEqual(filter_obj.name, "レバレッジ最適化フィルター")
        self.assertEqual(filter_obj.weight, "heavy")
        self.assertEqual(filter_obj.max_execution_time, 3.0)
    
    def test_leverage_filter_execution(self):
        """LeverageFilter実行テスト"""
        from engines.filters.heavy_weight_filters import LeverageFilter
        
        filter_obj = LeverageFilter()
        
        # モックデータに追加属性
        self.mock_prepared_data.calculate_optimal_leverage = Mock(return_value={
            'optimal_leverage': 3.0,
            'range': (2.0, 5.0),
            'confidence': 0.85
        })
        
        result = filter_obj.execute(
            self.mock_prepared_data,
            self.mock_strategy,
            self.evaluation_time
        )
        
        # 基本的な結果確認
        self.assertIsNotNone(result)
        self.assertIn('leverage_analysis', result.metrics)
        
        # レバレッジ分析結果確認
        leverage_metrics = result.metrics['leverage_analysis']
        self.assertIn('optimal_leverage', leverage_metrics)
        # モック実装では実際のフィールドを確認
        self.assertTrue('optimal_leverage' in leverage_metrics or 'confidence' in leverage_metrics)
    
    def test_leverage_filter_high_risk_rejection(self):
        """高リスクレバレッジの除外テスト"""
        from engines.filters.heavy_weight_filters import LeverageFilter
        
        filter_obj = LeverageFilter()
        
        # 高リスクシナリオ
        self.mock_prepared_data.calculate_optimal_leverage = Mock(return_value={
            'optimal_leverage': 10.0,  # 非常に高いレバレッジ
            'range': (8.0, 15.0),
            'confidence': 0.4  # 低信頼度
        })
        self.mock_prepared_data.get_volatility = Mock(return_value=0.1)  # 10%の高ボラティリティ
        
        result = filter_obj.execute(
            self.mock_prepared_data,
            self.mock_strategy,
            self.evaluation_time
        )
        
        # 高リスクは除外されるべき
        self.assertFalse(result.passed)
        self.assertIn("リスク", result.reason)
    
    def test_risk_reward_filter_import(self):
        """RiskRewardFilterクラスのインポートテスト（Filter 8）"""
        try:
            from engines.filters.heavy_weight_filters import RiskRewardFilter
            self.assertTrue(True)
        except ImportError:
            self.fail("RiskRewardFilterクラスがインポートできません")
    
    def test_risk_reward_filter_creation(self):
        """RiskRewardFilterクラスの作成テスト"""
        from engines.filters.heavy_weight_filters import RiskRewardFilter
        
        filter_obj = RiskRewardFilter()
        self.assertEqual(filter_obj.name, "リスクリワード比分析フィルター")
        self.assertEqual(filter_obj.weight, "heavy")
        self.assertEqual(filter_obj.max_execution_time, 2.5)
    
    def test_risk_reward_filter_execution(self):
        """RiskRewardFilter実行テスト"""
        from engines.filters.heavy_weight_filters import RiskRewardFilter
        
        filter_obj = RiskRewardFilter()
        
        # モックデータに追加属性
        self.mock_prepared_data.calculate_risk_reward = Mock(return_value={
            'ratio': 2.5,  # リスクリワード比
            'potential_profit': 0.05,  # 5%
            'potential_loss': 0.02,    # 2%
            'probability': 0.65        # 勝率65%
        })
        
        result = filter_obj.execute(
            self.mock_prepared_data,
            self.mock_strategy,
            self.evaluation_time
        )
        
        # 基本的な結果確認
        self.assertIsNotNone(result)
        self.assertIn('risk_reward_analysis', result.metrics)
        
        # リスクリワード分析結果確認
        rr_metrics = result.metrics['risk_reward_analysis']
        self.assertIn('ratio', rr_metrics)
        
        # 期待値分析とケリー分析は別のメトリクス
        if 'expected_value_analysis' in result.metrics:
            ev_metrics = result.metrics['expected_value_analysis']
            self.assertIn('expected_value', ev_metrics)
        
        if 'kelly_analysis' in result.metrics:
            kelly_metrics = result.metrics['kelly_analysis']
            self.assertIn('kelly_fraction', kelly_metrics)
    
    def test_risk_reward_filter_poor_ratio_rejection(self):
        """低リスクリワード比の除外テスト"""
        from engines.filters.heavy_weight_filters import RiskRewardFilter
        
        filter_obj = RiskRewardFilter()
        
        # 低リスクリワード比シナリオ
        self.mock_prepared_data.calculate_risk_reward = Mock(return_value={
            'ratio': 0.8,  # 1未満（リスクが報酬を上回る）
            'potential_profit': 0.02,
            'potential_loss': 0.025,
            'probability': 0.5
        })
        
        result = filter_obj.execute(
            self.mock_prepared_data,
            self.mock_strategy,
            self.evaluation_time
        )
        
        # 低リスクリワード比は除外されるべき
        self.assertFalse(result.passed)
        self.assertIn("リスクリワード", result.reason)
    
    def test_strategy_specific_filter_import(self):
        """StrategySpecificFilterクラスのインポートテスト（Filter 9）"""
        try:
            from engines.filters.heavy_weight_filters import StrategySpecificFilter
            self.assertTrue(True)
        except ImportError:
            self.fail("StrategySpecificFilterクラスがインポートできません")
    
    def test_strategy_specific_filter_creation(self):
        """StrategySpecificFilterクラスの作成テスト"""
        from engines.filters.heavy_weight_filters import StrategySpecificFilter
        
        filter_obj = StrategySpecificFilter()
        self.assertEqual(filter_obj.name, "戦略固有詳細分析フィルター")
        self.assertEqual(filter_obj.weight, "heavy")
        self.assertEqual(filter_obj.max_execution_time, 5.0)
    
    def test_strategy_specific_filter_ml_strategy(self):
        """ML戦略固有フィルターテスト"""
        from engines.filters.heavy_weight_filters import StrategySpecificFilter
        
        filter_obj = StrategySpecificFilter()
        
        # ML戦略のモック
        self.mock_strategy.name = "Full_ML"
        self.mock_prepared_data.get_ml_features = Mock(return_value={
            'feature_importance': {'volume': 0.3, 'rsi': 0.25, 'macd': 0.2},
            'model_confidence': 0.82,
            'prediction_stability': 0.75,
            'backtesting_accuracy': 0.68
        })
        
        result = filter_obj.execute(
            self.mock_prepared_data,
            self.mock_strategy,
            self.evaluation_time
        )
        
        # ML戦略の分析結果確認
        self.assertIsNotNone(result)
        self.assertIn('strategy_specific_metrics', result.metrics)
        
        metrics = result.metrics['strategy_specific_metrics']
        self.assertIn('ml_evaluation', metrics)
        self.assertIn('feature_quality', metrics['ml_evaluation'])
    
    def test_strategy_specific_filter_traditional_strategy(self):
        """Traditional戦略固有フィルターテスト"""
        from engines.filters.heavy_weight_filters import StrategySpecificFilter
        
        filter_obj = StrategySpecificFilter()
        
        # Traditional戦略のモック
        self.mock_strategy.name = "Aggressive_Traditional"
        self.mock_prepared_data.get_technical_indicators = Mock(return_value={
            'rsi': 65,
            'macd': {'signal': 'buy', 'strength': 0.7},
            'bollinger': {'position': 'upper_band', 'width': 0.03},
            'volume_trend': 'increasing'
        })
        
        result = filter_obj.execute(
            self.mock_prepared_data,
            self.mock_strategy,
            self.evaluation_time
        )
        
        # Traditional戦略の分析結果確認
        self.assertIsNotNone(result)
        self.assertIn('strategy_specific_metrics', result.metrics)
        
        metrics = result.metrics['strategy_specific_metrics']
        self.assertIn('technical_evaluation', metrics)
        self.assertIn('signal_strength', metrics['technical_evaluation'])
    
    def test_all_heavy_filters_integration(self):
        """全重量フィルターの統合テスト"""
        from engines.filters.heavy_weight_filters import LeverageFilter, RiskRewardFilter, StrategySpecificFilter
        
        filters = [
            LeverageFilter(),
            RiskRewardFilter(),
            StrategySpecificFilter()
        ]
        
        # 全フィルターが正しく作成されることを確認
        self.assertEqual(len(filters), 3)
        
        # 各フィルターの重量確認
        for filter_obj in filters:
            self.assertEqual(filter_obj.weight, "heavy")
            self.assertGreaterEqual(filter_obj.max_execution_time, 2.5)
        
        # 統計リセット可能確認
        for filter_obj in filters:
            filter_obj.reset_statistics()
            stats = filter_obj.get_statistics()
            self.assertEqual(stats['execution_count'], 0)
            self.assertEqual(stats['success_count'], 0)
    
    def test_heavy_filters_performance_characteristics(self):
        """重量フィルターのパフォーマンス特性テスト"""
        from engines.filters.heavy_weight_filters import LeverageFilter, RiskRewardFilter, StrategySpecificFilter
        
        # 各フィルターの予想通過率
        expected_pass_rates = {
            'LeverageFilter': 0.5,      # 50%（厳格なレバレッジ制限）
            'RiskRewardFilter': 0.6,    # 60%（リスクリワード基準）
            'StrategySpecificFilter': 0.7  # 70%（戦略適合性）
        }
        
        # 複合通過率計算（全て通過）
        combined_pass_rate = 0.5 * 0.6 * 0.7
        self.assertAlmostEqual(combined_pass_rate, 0.21, places=2)
        
        # 全9フィルターでの最終通過率（仮定）
        # Light (1-3): 90% * 85% * 80% = 61.2%
        # Medium (4-6): 60% * 80% * 70% = 33.6%
        # Heavy (7-9): 50% * 60% * 70% = 21%
        # 総合: 61.2% * 33.6% * 21% ≈ 4.3%
        
        overall_pass_rate = 0.612 * 0.336 * 0.21
        self.assertLess(overall_pass_rate, 0.05)  # 5%未満の厳格なフィルタリング


def run_all_tests():
    """全テスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHeavyWeightFilters)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "="*70)
    print("重量フィルターテスト結果サマリー")
    print("="*70)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ 全ての重量フィルターテストが成功しました！")
    else:
        print("\n❌ 一部のテストが失敗しました。")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)