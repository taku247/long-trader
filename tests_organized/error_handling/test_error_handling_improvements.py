#!/usr/bin/env python3
"""
エラーハンドリング改善のテスト

2025-06-28のエラーハンドリング改善が適切に機能することを検証：
1. ブレイクアウト予測: エラー1回でも例外発生
2. BTC相関分析: データ不足も例外発生
3. エラーメッセージの詳細化
4. カスタムエラータイプの適切な使用
"""

import unittest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import tempfile
import shutil

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# BaseTestクラスをインポート
try:
    from tests_organized.base_test import BaseTest, TestResult
except ImportError:
    class BaseTest(unittest.TestCase):
        def setUp(self):
            self.temp_dir = tempfile.mkdtemp()
        def tearDown(self):
            if hasattr(self, 'temp_dir'):
                shutil.rmtree(self.temp_dir)

from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
from engines.leverage_decision_engine import (
    InsufficientMarketDataError, 
    InsufficientConfigurationError, 
    LeverageAnalysisError
)

class TestErrorHandlingImprovements(BaseTest):
    """エラーハンドリング改善テスト"""
    
    def setUp(self):
        """テスト前準備"""
        super().setUp()
        self.orchestrator = HighLeverageBotOrchestrator()
        
        # テスト用のダミーデータ
        self.test_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H'),
            'open': [100.0 + i for i in range(100)],
            'high': [101.0 + i for i in range(100)],
            'low': [99.0 + i for i in range(100)],
            'close': [100.5 + i for i in range(100)],
            'volume': [1000.0] * 100
        })
        
        # テスト用のサポレジレベル
        self.mock_support_level = Mock()
        self.mock_support_level.price = 100.0
        self.mock_support_level.strength = 0.5
        self.mock_support_level.touch_count = 3
        
        self.mock_resistance_level = Mock()
        self.mock_resistance_level.price = 110.0
        self.mock_resistance_level.strength = 0.6
        self.mock_resistance_level.touch_count = 4
    
    def test_breakout_prediction_fail_fast_single_error(self):
        """ブレイクアウト予測: 1つのレベルでエラーが発生したら即座に例外発生"""
        print("🧪 ブレイクアウト予測 Fail-Fast テスト（単一エラー）")
        
        # モックブレイクアウト予測器を設定
        mock_predictor = Mock()
        mock_predictor.is_trained = True
        
        # 1つ目のレベルで例外、2つ目は成功する設定
        mock_predictor.predict_breakout.side_effect = [
            Exception("Mock prediction error"), 
            Mock()  # 2つ目は成功するはずだが、1つ目でFailするべき
        ]
        
        self.orchestrator.breakout_predictor = mock_predictor
        
        # レベルリスト（2つ）
        levels = [self.mock_support_level, self.mock_resistance_level]
        
        # 1つでもエラーがあれば例外発生することを確認
        with self.assertRaises(Exception) as context:
            self.orchestrator._predict_breakouts(self.test_data, levels)
        
        # エラーメッセージに詳細情報が含まれることを確認
        error_message = str(context.exception)
        self.assertIn("ML予測でエラーが発生", error_message)
        self.assertIn("1/2", error_message)  # 1つのエラー / 2つのレベル
        self.assertIn("100.0: Exception", error_message)  # レベル価格とエラータイプ
        
        print(f"   ✅ 期待通りに例外発生: {error_message}")
    
    def test_breakout_prediction_model_training_failure(self):
        """ブレイクアウト予測: MLモデル訓練失敗時の例外発生"""
        print("🧪 MLモデル訓練失敗テスト")
        
        # モックブレイクアウト予測器を設定（未訓練状態）
        mock_predictor = Mock()
        mock_predictor.is_trained = False
        mock_predictor.train_model.side_effect = Exception("Mock training failure")
        
        self.orchestrator.breakout_predictor = mock_predictor
        
        # 訓練失敗で例外発生することを確認
        with self.assertRaises(Exception) as context:
            self.orchestrator._predict_breakouts(self.test_data, [self.mock_support_level])
        
        error_message = str(context.exception)
        self.assertIn("MLモデル訓練に失敗", error_message)
        self.assertIn("予測システムが利用できません", error_message)
        
        print(f"   ✅ 期待通りに例外発生: {error_message}")
    
    def test_btc_correlation_data_insufficient_fails(self):
        """BTC相関分析: データ不足エラーも例外発生"""
        print("🧪 BTC相関分析 データ不足例外テスト")
        
        # モックBTC相関分析器を設定（データ不足エラーを発生）
        mock_analyzer = Mock()
        mock_analyzer.predict_altcoin_impact.side_effect = Exception("Insufficient data for correlation analysis")
        
        self.orchestrator.btc_correlation_analyzer = mock_analyzer
        
        # データ不足エラーでも例外発生することを確認
        with self.assertRaises(Exception) as context:
            self.orchestrator._analyze_btc_correlation("TEST")
        
        error_message = str(context.exception)
        self.assertIn("BTC相関分析でデータ不足エラー", error_message)
        self.assertIn("Insufficient data", error_message)
        self.assertIn("銘柄: TEST", error_message)
        
        print(f"   ✅ 期待通りに例外発生: {error_message}")
    
    def test_btc_correlation_other_errors_fail(self):
        """BTC相関分析: その他のエラーも例外発生"""
        print("🧪 BTC相関分析 その他エラー例外テスト")
        
        # モックBTC相関分析器を設定（その他のエラーを発生）
        mock_analyzer = Mock()
        mock_analyzer.predict_altcoin_impact.side_effect = Exception("Network connection failed")
        
        self.orchestrator.btc_correlation_analyzer = mock_analyzer
        
        # その他のエラーでも例外発生することを確認
        with self.assertRaises(Exception) as context:
            self.orchestrator._analyze_btc_correlation("TEST")
        
        error_message = str(context.exception)
        self.assertIn("BTC相関分析で致命的エラー", error_message)
        self.assertIn("Network connection failed", error_message)
        self.assertIn("銘柄: TEST", error_message)
        
        print(f"   ✅ 期待通りに例外発生: {error_message}")
    
    def test_insufficient_market_data_error_propagation(self):
        """InsufficientMarketDataErrorの適切な伝播"""
        print("🧪 InsufficientMarketDataError 伝播テスト")
        
        from engines.leverage_decision_engine import CoreLeverageDecisionEngine
        
        # レバレッジエンジンを作成
        engine = CoreLeverageDecisionEngine()
        
        # 空のサポートレベルでInsufficientMarketDataErrorが発生することを確認
        with self.assertRaises(InsufficientMarketDataError) as context:
            engine._analyze_downside_risk(100.0, [], [], [])
        
        error = context.exception
        self.assertEqual(error.error_type, "support_detection_failed")
        self.assertEqual(error.missing_data, "support_levels")
        self.assertIn("サポートレベルが検出できませんでした", str(error))
        
        print(f"   ✅ InsufficientMarketDataError適切に発生: {error.error_type}")
    
    def test_error_message_format_with_error_type(self):
        """エラーメッセージがエラータイプ情報を含むことを確認"""
        print("🧪 エラーメッセージフォーマットテスト")
        
        # カスタムエラーを作成
        test_error = InsufficientMarketDataError(
            message="テストエラーメッセージ",
            error_type="test_error_type",
            missing_data="test_data"
        )
        
        # エラータイプの確認
        self.assertEqual(test_error.error_type, "test_error_type")
        self.assertEqual(test_error.missing_data, "test_data")
        self.assertEqual(str(test_error), "テストエラーメッセージ")
        
        # type().__name__ でエラータイプが取得できることを確認
        error_type_name = type(test_error).__name__
        self.assertEqual(error_type_name, "InsufficientMarketDataError")
        
        # フォーマット例: [InsufficientMarketDataError] メッセージ
        formatted_error = f"[{error_type_name}] {str(test_error)}"
        expected = "[InsufficientMarketDataError] テストエラーメッセージ"
        self.assertEqual(formatted_error, expected)
        
        print(f"   ✅ エラーフォーマット確認: {formatted_error}")
    
    def test_custom_error_types_exist(self):
        """カスタムエラータイプが適切に定義されていることを確認"""
        print("🧪 カスタムエラータイプ存在確認テスト")
        
        # 各エラータイプのインスタンス作成テスト
        error1 = InsufficientMarketDataError("test", "test_type", "test_data")
        error2 = InsufficientConfigurationError("test", "test_type", "test_config")
        error3 = LeverageAnalysisError("test", "test_type", "test_stage")
        
        # 属性の確認
        self.assertEqual(error1.error_type, "test_type")
        self.assertEqual(error1.missing_data, "test_data")
        
        self.assertEqual(error2.error_type, "test_type")
        self.assertEqual(error2.missing_config, "test_config")
        
        self.assertEqual(error3.error_type, "test_type")
        self.assertEqual(error3.analysis_stage, "test_stage")
        
        # 継承関係の確認
        self.assertIsInstance(error1, Exception)
        self.assertIsInstance(error2, Exception)
        self.assertIsInstance(error3, Exception)
        
        print("   ✅ 全カスタムエラータイプが適切に定義されています")
    
    def test_no_error_hiding_in_breakout_prediction(self):
        """ブレイクアウト予測でエラーが隠蔽されないことを確認"""
        print("🧪 ブレイクアウト予測エラー隠蔽防止テスト")
        
        # モックブレイクアウト予測器を設定
        mock_predictor = Mock()
        mock_predictor.is_trained = True
        mock_predictor.predict_breakout.side_effect = Exception("Test prediction error")
        
        self.orchestrator.breakout_predictor = mock_predictor
        
        # エラーが隠蔽されずに例外が発生することを確認
        with self.assertRaises(Exception) as context:
            self.orchestrator._predict_breakouts(self.test_data, [self.mock_support_level])
        
        # エラーが隠蔽されずに適切に例外が発生することを確認
        error_message = str(context.exception)
        # エラーメッセージに関連情報が含まれていることを確認
        self.assertIn("ML予測でエラーが発生", error_message)
        self.assertIn("Exception", error_message)  # エラータイプが含まれる
        self.assertNotEqual(len(error_message), 0)  # エラーメッセージが空でない
        
        print(f"   ✅ エラー隠蔽されずに適切に例外発生: {error_message[:100]}")

if __name__ == '__main__':
    unittest.main()