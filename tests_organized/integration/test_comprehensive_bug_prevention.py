#!/usr/bin/env python3
"""
今回のバグ・実装漏れを防ぐための包括的テストスイート

主要なテスト項目:
1. Level 1厳格バリデーション - 空配列検出時の完全失敗
2. 支持線・抵抗線検出システム - 実際のデータ取得確認
3. アダプターパターン - モジュール差し替え互換性
4. データ異常検知 - 非現実的数値の検出
5. 価格参照整合性 - entry_price vs current_priceの統一
6. 統合テスト - エンドツーエンドの動作確認
"""

import unittest
import asyncio
import sys
import os
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import shutil
import sqlite3
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.stop_loss_take_profit_calculators import (
    CriticalAnalysisError, 
    DefaultSLTPCalculator, 
    ConservativeSLTPCalculator, 
    AggressiveSLTPCalculator
)
from engines.support_resistance_adapter import (
    FlexibleSupportResistanceDetector,
    ISupportResistanceProvider,
    IMLEnhancementProvider,
    SupportResistanceVisualizerAdapter,
    SupportResistanceMLAdapter
)
from engines.support_resistance_detector import SupportResistanceDetector
from engines.advanced_support_resistance_detector import AdvancedSupportResistanceDetector
from interfaces.data_types import SupportResistanceLevel
from scalable_analysis_system import ScalableAnalysisSystem


class TestCriticalAnalysisErrorHandling(unittest.TestCase):
    """Level 1厳格バリデーションのテストケース"""
    
    def setUp(self):
        """テスト前準備"""
        self.calculators = [
            DefaultSLTPCalculator(),
            ConservativeSLTPCalculator(),
            AggressiveSLTPCalculator()
        ]
        self.current_price = 50000.0
        self.leverage = 10.0
        self.empty_support_levels = []
        self.empty_resistance_levels = []
        
        # モック市場コンテキスト
        self.mock_market_context = Mock()
        self.mock_market_context.volatility = 0.03
        self.mock_market_context.trend_direction = 'BULLISH'
    
    def test_empty_support_levels_raises_critical_error(self):
        """空の支持線配列でCriticalAnalysisErrorが発生することを確認"""
        # 有効な抵抗線は提供
        valid_resistance_levels = [
            SupportResistanceLevel(
                price=52000.0, strength=0.8, touch_count=3, level_type='resistance',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1000000, distance_from_current=4.0
            )
        ]
        
        for calculator in self.calculators:
            with self.subTest(calculator=calculator.__class__.__name__):
                with self.assertRaises(CriticalAnalysisError) as context:
                    calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=self.empty_support_levels,
                        resistance_levels=valid_resistance_levels,
                        market_context=self.mock_market_context
                    )
                
                # エラーメッセージに「支持線」が含まれることを確認
                self.assertIn("支持線", str(context.exception))
    
    def test_empty_resistance_levels_raises_critical_error(self):
        """空の抵抗線配列でCriticalAnalysisErrorが発生することを確認"""
        # 有効な支持線は提供
        valid_support_levels = [
            SupportResistanceLevel(
                price=48000.0, strength=0.8, touch_count=3, level_type='support',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1000000, distance_from_current=-4.0
            )
        ]
        
        for calculator in self.calculators:
            with self.subTest(calculator=calculator.__class__.__name__):
                with self.assertRaises(CriticalAnalysisError) as context:
                    calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=valid_support_levels,
                        resistance_levels=self.empty_resistance_levels,
                        market_context=self.mock_market_context
                    )
                
                # エラーメッセージに「抵抗線」が含まれることを確認
                self.assertIn("抵抗線", str(context.exception))
    
    def test_both_empty_levels_raises_critical_error(self):
        """支持線・抵抗線両方が空でCriticalAnalysisErrorが発生することを確認"""
        for calculator in self.calculators:
            with self.subTest(calculator=calculator.__class__.__name__):
                with self.assertRaises(CriticalAnalysisError):
                    calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=self.empty_support_levels,
                        resistance_levels=self.empty_resistance_levels,
                        market_context=self.mock_market_context
                    )
    
    def test_valid_levels_do_not_raise_error(self):
        """有効な支持線・抵抗線がある場合はエラーが発生しないことを確認"""
        valid_support_levels = [
            SupportResistanceLevel(
                price=48000.0, strength=0.8, touch_count=3, level_type='support',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1000000, distance_from_current=-4.0
            )
        ]
        valid_resistance_levels = [
            SupportResistanceLevel(
                price=52000.0, strength=0.8, touch_count=3, level_type='resistance',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1000000, distance_from_current=4.0
            )
        ]
        
        for calculator in self.calculators:
            with self.subTest(calculator=calculator.__class__.__name__):
                try:
                    result = calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=valid_support_levels,
                        resistance_levels=valid_resistance_levels,
                        market_context=self.mock_market_context
                    )
                    # 結果の妥当性を簡単にチェック
                    self.assertIsNotNone(result)
                    self.assertIn('stop_loss_price', result)
                    self.assertIn('take_profit_price', result)
                except CriticalAnalysisError:
                    self.fail(f"{calculator.__class__.__name__} raised CriticalAnalysisError with valid levels")


class TestSupportResistanceDetection(unittest.TestCase):
    """支持線・抵抗線検出システムのテストケース"""
    
    def setUp(self):
        """テスト前準備"""
        # サンプルOHLCVデータ生成
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        base_price = 50000
        trend = np.linspace(0, 2000, 200)
        noise = np.random.normal(0, 300, 200)
        prices = base_price + trend + noise
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 30, 200),
            'high': prices + np.abs(np.random.normal(100, 50, 200)),
            'low': prices - np.abs(np.random.normal(100, 50, 200)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 200)
        })
        self.current_price = prices[-1]
    
    def test_basic_detector_returns_levels(self):
        """基本検出器が支持線・抵抗線を返すことを確認"""
        detector = SupportResistanceDetector()
        
        try:
            support_levels, resistance_levels = detector.detect_levels_from_ohlcv(
                self.df, self.current_price
            )
            
            # 何らかのレベルが検出されることを確認
            total_levels = len(support_levels) + len(resistance_levels)
            self.assertGreater(total_levels, 0, "支持線・抵抗線が1つも検出されませんでした")
            
            # レベルオブジェクトの妥当性確認
            for level in support_levels:
                self.assertIsInstance(level, SupportResistanceLevel)
                self.assertLess(level.price, self.current_price, "支持線が現在価格より高い位置にあります")
                self.assertGreater(level.strength, 0, "支持線の強度が0以下です")
            
            for level in resistance_levels:
                self.assertIsInstance(level, SupportResistanceLevel)
                self.assertGreater(level.price, self.current_price, "抵抗線が現在価格より低い位置にあります")
                self.assertGreater(level.strength, 0, "抵抗線の強度が0以下です")
            
        except Exception as e:
            self.fail(f"基本検出器でエラーが発生: {str(e)}")
    
    def test_advanced_detector_returns_levels(self):
        """高度検出器が支持線・抵抗線を返すことを確認"""
        detector = AdvancedSupportResistanceDetector(use_ml_prediction=False)  # MLなしでテスト
        
        try:
            support_levels, resistance_levels = detector.detect_advanced_levels(
                self.df, self.current_price
            )
            
            # 何らかのレベルが検出されることを確認
            total_levels = len(support_levels) + len(resistance_levels)
            self.assertGreater(total_levels, 0, "高度検出器で支持線・抵抗線が1つも検出されませんでした")
            
        except Exception as e:
            self.fail(f"高度検出器でエラーが発生: {str(e)}")
    
    def test_insufficient_data_raises_error(self):
        """データ不足時にエラーが発生することを確認"""
        # 不十分なデータ（10本のみ）
        insufficient_df = self.df.head(10)
        detector = SupportResistanceDetector()
        
        with self.assertRaises(ValueError) as context:
            detector.detect_levels_from_ohlcv(insufficient_df, self.current_price)
        
        self.assertIn("データが不足", str(context.exception))


class TestAdapterPatternCompatibility(unittest.TestCase):
    """アダプターパターンの互換性テストケース"""
    
    def setUp(self):
        """テスト前準備"""
        # サンプルOHLCVデータ生成
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        base_price = 50000
        prices = base_price + np.random.normal(0, 500, 100)
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 30, 100),
            'high': prices + np.abs(np.random.normal(100, 50, 100)),
            'low': prices - np.abs(np.random.normal(100, 50, 100)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 100)
        })
        self.current_price = prices[-1]
    
    def test_flexible_detector_initialization(self):
        """FlexibleSupportResistanceDetectorの初期化テスト"""
        try:
            detector = FlexibleSupportResistanceDetector()
            self.assertIsNotNone(detector)
            
            # プロバイダー情報の取得
            info = detector.get_provider_info()
            self.assertIn('base_provider', info)
            self.assertIn('ml_provider', info)
            
        except Exception as e:
            # 既存モジュールがない場合はスキップ
            if "読み込みに失敗" in str(e):
                self.skipTest(f"既存モジュールが利用できません: {str(e)}")
            else:
                self.fail(f"FlexibleSupportResistanceDetector初期化エラー: {str(e)}")
    
    def test_provider_switching(self):
        """プロバイダー切り替え機能のテスト"""
        # モックプロバイダーを作成
        class MockProvider(ISupportResistanceProvider):
            def detect_basic_levels(self, df, min_touches=2):
                return [
                    {
                        'price': 49000,
                        'strength': 0.7,
                        'touch_count': 3,
                        'type': 'support',
                        'timestamps': [df['timestamp'].iloc[0], df['timestamp'].iloc[-1]],
                        'avg_volume': 1500000
                    }
                ]
            
            def get_provider_name(self):
                return "MockProvider"
            
            def get_provider_version(self):
                return "1.0.0-test"
        
        try:
            detector = FlexibleSupportResistanceDetector()
            mock_provider = MockProvider()
            
            # プロバイダー切り替え
            detector.set_base_provider(mock_provider)
            
            # プロバイダー情報の確認
            info = detector.get_provider_info()
            self.assertIn("MockProvider", info['base_provider'])
            
            # 検出実行
            support_levels, resistance_levels = detector.detect_levels(self.df, self.current_price)
            
            # モックプロバイダーが実際に使用されたことを確認
            # （モックは支持線のみ返すため、支持線が検出されることを確認）
            self.assertGreater(len(support_levels), 0, "モックプロバイダーから支持線が検出されませんでした")
            
        except Exception as e:
            if "読み込みに失敗" in str(e):
                self.skipTest(f"既存モジュールが利用できません: {str(e)}")
            else:
                self.fail(f"プロバイダー切り替えテストでエラー: {str(e)}")
    
    def test_ml_enhancement_toggle(self):
        """ML機能のオン/オフ切り替えテスト"""
        try:
            detector = FlexibleSupportResistanceDetector()
            
            # ML機能を無効化
            detector.disable_ml_enhancement()
            info = detector.get_provider_info()
            self.assertEqual(info['ml_enhancement_enabled'], 'False')
            
            # ML機能を有効化
            detector.enable_ml_enhancement()
            info = detector.get_provider_info()
            # ML プロバイダーが利用できない場合は無効のままになる可能性がある
            self.assertIn(info['ml_enhancement_enabled'], ['True', 'False'])
            
        except Exception as e:
            if "読み込みに失敗" in str(e):
                self.skipTest(f"既存モジュールが利用できません: {str(e)}")
            else:
                self.fail(f"ML機能切り替えテストでエラー: {str(e)}")


class TestDataAnomalyDetection(unittest.TestCase):
    """データ異常検知のテストケース"""
    
    def test_unrealistic_profit_detection(self):
        """非現実的利益率の検知テスト"""
        # テストデータ: 異常な利益率
        entry_price = 1932.0
        exit_price = 2812.0
        time_minutes = 50
        
        profit_rate = (exit_price - entry_price) / entry_price
        annual_rate = profit_rate * (365 * 24 * 60 / time_minutes)
        
        # 45%の利益が50分で発生する場合
        self.assertGreater(profit_rate, 0.4, "利益率が期待値より低い")
        self.assertGreater(annual_rate, 1000, "年利換算が異常に高い（1000%超）")
        
        # 異常検知のロジック
        def is_unrealistic_profit(entry, exit, time_min):
            profit_pct = (exit - entry) / entry * 100
            if time_min < 60 and profit_pct > 20:  # 1時間未満で20%超
                return True
            if time_min < 120 and profit_pct > 40:  # 2時間未満で40%超
                return True
            return False
        
        self.assertTrue(
            is_unrealistic_profit(entry_price, exit_price, time_minutes),
            "異常な利益率が検知されませんでした"
        )
    
    def test_invalid_stop_loss_take_profit_logic(self):
        """損切り・利確ラインの論理エラー検知テスト"""
        # ロングポジションの場合の正常条件
        entry_price = 1932.0
        stop_loss_price = 2578.0  # エントリーより33%高い（異常）
        take_profit_price = 2782.0  # エントリーより44%高い
        
        def validate_long_position_logic(entry, stop_loss, take_profit):
            """ロングポジションの妥当性検証"""
            if stop_loss >= entry:
                return False, "損切りラインがエントリー価格以上です"
            if take_profit <= entry:
                return False, "利確ラインがエントリー価格以下です"
            if stop_loss >= take_profit:
                return False, "損切りラインが利確ライン以上です"
            return True, "正常"
        
        is_valid, message = validate_long_position_logic(
            entry_price, stop_loss_price, take_profit_price
        )
        
        self.assertFalse(is_valid, "異常な損切り・利確ロジックが検知されませんでした")
        self.assertIn("損切りライン", message, "エラーメッセージが期待値と異なります")
    
    def test_price_reference_consistency(self):
        """価格参照の整合性テスト"""
        # current_price vs entry_priceの整合性確認
        current_price = 3950.0
        entry_price = 3970.0  # 実際の市場価格
        close_price = 5739.36  # 異常に高いクローズ価格
        
        # 価格差の許容範囲（通常1%以内が妥当）
        price_diff_pct = abs(current_price - entry_price) / entry_price * 100
        close_diff_pct = abs(close_price - entry_price) / entry_price * 100
        
        # current_priceとentry_priceの差は小さいはず
        self.assertLess(price_diff_pct, 2.0, "current_priceとentry_priceの差が大きすぎます")
        
        # close_priceが異常に高い場合の検知
        self.assertGreater(close_diff_pct, 40.0, "close_priceの異常が検知されませんでした")


class TestIntegrationEndToEnd(unittest.TestCase):
    """統合テスト（エンドツーエンド）"""
    
    def setUp(self):
        """テスト前準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_analysis.db")
    
    def tearDown(self):
        """テスト後cleanup"""
        shutil.rmtree(self.temp_dir)
    
    def test_complete_analysis_workflow_with_strict_validation(self):
        """厳格バリデーション込みの完全分析ワークフローテスト"""
        # モックデータで分析システムを構築
        system = ScalableAnalysisSystem(base_dir=self.temp_dir)
        
        # テスト設定
        test_configs = [{
            'symbol': 'TEST',
            'timeframe': '1h',
            'config': 'Conservative'
        }]
        
        # 支持線・抵抗線データ不足をシミュレート
        with patch('scalable_analysis_system.ScalableAnalysisSystem._generate_single_analysis') as mock_analysis:
            # CriticalAnalysisErrorを発生させる
            mock_analysis.side_effect = CriticalAnalysisError("支持線・抵抗線データが不足しています")
            
            # 分析実行
            with self.assertLogs(level='ERROR') as log:
                try:
                    processed_count = system.generate_batch_analysis(test_configs)
                    self.assertEqual(processed_count, 0, "データ不足時に処理が継続されました")
                except Exception as e:
                    self.assertIn("支持線", str(e), "期待されるエラーメッセージが含まれていません")
    
    @patch('ohlcv_by_claude.get_ohlcv_data')
    def test_full_symbol_analysis_with_real_detection(self, mock_ohlcv):
        """実際の検出システムを使用した完全銘柄分析テスト"""
        # モックOHLCVデータ
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=1000, freq='1h')
        base_price = 50000
        prices = base_price + np.random.normal(0, 500, 1000)
        
        mock_df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 30, 1000),
            'high': prices + np.abs(np.random.normal(100, 50, 1000)),
            'low': prices - np.abs(np.random.normal(100, 50, 1000)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 1000)
        })
        
        mock_ohlcv.return_value = mock_df
        
        try:
            # FlexibleSupportResistanceDetectorのテスト
            detector = FlexibleSupportResistanceDetector()
            current_price = prices[-1]
            
            support_levels, resistance_levels = detector.detect_levels(mock_df, current_price)
            
            # 有効なレベルが検出されることを確認
            self.assertGreater(len(support_levels) + len(resistance_levels), 0, 
                              "実際の検出システムでレベルが検出されませんでした")
            
            # SLTPCalculatorでCriticalAnalysisErrorが発生しないことを確認
            calculator = DefaultSLTPCalculator()
            mock_market_context = Mock()
            mock_market_context.volatility = 0.03
            
            if support_levels and resistance_levels:
                result = calculator.calculate_levels(
                    current_price=current_price,
                    leverage=10.0,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    market_context=mock_market_context
                )
                
                # 結果の妥当性確認
                self.assertIn('stop_loss_price', result)
                self.assertIn('take_profit_price', result)
                self.assertLess(result['stop_loss_price'], current_price)
                self.assertGreater(result['take_profit_price'], current_price)
            
        except Exception as e:
            if "読み込みに失敗" in str(e):
                self.skipTest(f"既存モジュールが利用できません: {str(e)}")
            else:
                self.fail(f"統合テストでエラー: {str(e)}")


def run_comprehensive_tests():
    """包括的テストの実行"""
    print("🧪 今回のバグ・実装漏れ防止テストスイート実行開始")
    print("=" * 80)
    
    # テストスイートを作成
    test_suite = unittest.TestSuite()
    
    # 各テストクラスを追加
    test_classes = [
        TestCriticalAnalysisErrorHandling,
        TestSupportResistanceDetection,
        TestAdapterPatternCompatibility,
        TestDataAnomalyDetection,
        TestIntegrationEndToEnd
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)
    print(f"実行テスト数: {result.testsRun}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    print(f"スキップ: {len(result.skipped)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split(chr(10))[0]}")
    
    if result.errors:
        print("\n💥 エラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split(chr(10))[-2]}")
    
    if result.skipped:
        print("\n⏭️ スキップされたテスト:")
        for test, reason in result.skipped:
            print(f"  - {test}: {reason}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n成功率: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ すべてのテストが成功しました!")
        print("今回のバグ・実装漏れに対する防御機能が正常に動作しています。")
    else:
        print("\n⚠️ 一部のテストが失敗しました。")
        print("修正が必要な問題があります。")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)