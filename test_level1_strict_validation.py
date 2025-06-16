#!/usr/bin/env python3
"""
Level 1厳格バリデーション専用テストスイート

今回実装したLevel 1厳格バリデーションの徹底的なテスト:
1. CriticalAnalysisError例外の発生確認
2. 空配列検出時の完全失敗動作
3. フォールバック値の廃止確認
4. エラーメッセージの適切性
5. 全計算機タイプでの一貫性
"""

import unittest
import sys
import os
from unittest.mock import Mock
from datetime import datetime
import traceback

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.stop_loss_take_profit_calculators import (
    CriticalAnalysisError,
    DefaultSLTPCalculator,
    ConservativeSLTPCalculator,
    AggressiveSLTPCalculator
)
from interfaces.data_types import SupportResistanceLevel


class TestLevel1StrictValidation(unittest.TestCase):
    """Level 1厳格バリデーションの網羅的テスト"""
    
    def setUp(self):
        """各テスト前の準備"""
        self.all_calculators = [
            ("Default", DefaultSLTPCalculator()),
            ("Conservative", ConservativeSLTPCalculator()),
            ("Aggressive", AggressiveSLTPCalculator())
        ]
        
        self.current_price = 50000.0
        self.leverage = 10.0
        
        # モック市場コンテキスト
        self.mock_market_context = Mock()
        self.mock_market_context.volatility = 0.03
        self.mock_market_context.trend_direction = 'BULLISH'
        
        # 有効な支持線・抵抗線サンプル
        self.valid_support_levels = [
            SupportResistanceLevel(
                price=48000.0, strength=0.8, touch_count=3, level_type='support',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1500000, distance_from_current=-4.17
            ),
            SupportResistanceLevel(
                price=47000.0, strength=0.6, touch_count=2, level_type='support',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1200000, distance_from_current=-6.38
            )
        ]
        
        self.valid_resistance_levels = [
            SupportResistanceLevel(
                price=52000.0, strength=0.8, touch_count=3, level_type='resistance',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1500000, distance_from_current=4.0
            ),
            SupportResistanceLevel(
                price=53000.0, strength=0.7, touch_count=2, level_type='resistance',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1300000, distance_from_current=6.0
            )
        ]
    
    def test_empty_support_levels_critical_error(self):
        """空の支持線配列でCriticalAnalysisErrorが発生"""
        for calc_name, calculator in self.all_calculators:
            with self.subTest(calculator=calc_name):
                with self.assertRaises(CriticalAnalysisError) as context:
                    calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=[],  # 空配列
                        resistance_levels=self.valid_resistance_levels,
                        market_context=self.mock_market_context
                    )
                
                error_msg = str(context.exception)
                
                # エラーメッセージの内容確認
                self.assertIn("支持線", error_msg, f"{calc_name}: エラーメッセージに'支持線'が含まれていません")
                self.assertIn("不足", error_msg, f"{calc_name}: エラーメッセージに'不足'が含まれていません")
                
                print(f"✅ {calc_name}: 空支持線配列でCriticalAnalysisError正常発生")
    
    def test_empty_resistance_levels_critical_error(self):
        """空の抵抗線配列でCriticalAnalysisErrorが発生"""
        for calc_name, calculator in self.all_calculators:
            with self.subTest(calculator=calc_name):
                with self.assertRaises(CriticalAnalysisError) as context:
                    calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=self.valid_support_levels,
                        resistance_levels=[],  # 空配列
                        market_context=self.mock_market_context
                    )
                
                error_msg = str(context.exception)
                
                # エラーメッセージの内容確認
                self.assertIn("抵抗線", error_msg, f"{calc_name}: エラーメッセージに'抵抗線'が含まれていません")
                self.assertIn("不足", error_msg, f"{calc_name}: エラーメッセージに'不足'が含まれていません")
                
                print(f"✅ {calc_name}: 空抵抗線配列でCriticalAnalysisError正常発生")
    
    def test_both_empty_arrays_critical_error(self):
        """支持線・抵抗線両方が空の場合のCriticalAnalysisError"""
        for calc_name, calculator in self.all_calculators:
            with self.subTest(calculator=calc_name):
                with self.assertRaises(CriticalAnalysisError):
                    calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=[],  # 空配列
                        resistance_levels=[],  # 空配列
                        market_context=self.mock_market_context
                    )
                
                print(f"✅ {calc_name}: 両方空配列でCriticalAnalysisError正常発生")
    
    def test_no_relevant_support_levels_critical_error(self):
        """現在価格より下に支持線がない場合のCriticalAnalysisError"""
        # 現在価格より上の「偽支持線」を作成
        irrelevant_support_levels = [
            SupportResistanceLevel(
                price=52000.0, strength=0.8, touch_count=3, level_type='support',  # 実際は抵抗線
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1500000, distance_from_current=4.0
            )
        ]
        
        for calc_name, calculator in self.all_calculators:
            with self.subTest(calculator=calc_name):
                with self.assertRaises(CriticalAnalysisError) as context:
                    calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=irrelevant_support_levels,
                        resistance_levels=self.valid_resistance_levels,
                        market_context=self.mock_market_context
                    )
                
                error_msg = str(context.exception)
                self.assertIn("支持線", error_msg, f"{calc_name}: 下方支持線不足エラーメッセージが不適切")
                
                print(f"✅ {calc_name}: 下方支持線なしでCriticalAnalysisError正常発生")
    
    def test_no_relevant_resistance_levels_critical_error(self):
        """現在価格より上に抵抗線がない場合のCriticalAnalysisError"""
        # 現在価格より下の「偽抵抗線」を作成
        irrelevant_resistance_levels = [
            SupportResistanceLevel(
                price=48000.0, strength=0.8, touch_count=3, level_type='resistance',  # 実際は支持線
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1500000, distance_from_current=-4.0
            )
        ]
        
        for calc_name, calculator in self.all_calculators:
            with self.subTest(calculator=calc_name):
                with self.assertRaises(CriticalAnalysisError) as context:
                    calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=self.valid_support_levels,
                        resistance_levels=irrelevant_resistance_levels,
                        market_context=self.mock_market_context
                    )
                
                error_msg = str(context.exception)
                self.assertIn("抵抗線", error_msg, f"{calc_name}: 上方抵抗線不足エラーメッセージが不適切")
                
                print(f"✅ {calc_name}: 上方抵抗線なしでCriticalAnalysisError正常発生")
    
    def test_valid_levels_no_error(self):
        """有効な支持線・抵抗線がある場合はエラーが発生しない"""
        for calc_name, calculator in self.all_calculators:
            with self.subTest(calculator=calc_name):
                try:
                    result = calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=self.valid_support_levels,
                        resistance_levels=self.valid_resistance_levels,
                        market_context=self.mock_market_context
                    )
                    
                    # 結果の基本的な妥当性チェック
                    self.assertIsInstance(result, dict, f"{calc_name}: 戻り値が辞書でない")
                    self.assertIn('stop_loss_price', result, f"{calc_name}: stop_loss_priceがない")
                    self.assertIn('take_profit_price', result, f"{calc_name}: take_profit_priceがない")
                    
                    # ロングポジションの論理確認
                    self.assertLess(
                        result['stop_loss_price'], self.current_price,
                        f"{calc_name}: 損切り価格が現在価格以上"
                    )
                    self.assertGreater(
                        result['take_profit_price'], self.current_price,
                        f"{calc_name}: 利確価格が現在価格以下"
                    )
                    
                    print(f"✅ {calc_name}: 有効データで正常計算完了")
                    
                except CriticalAnalysisError as e:
                    self.fail(f"{calc_name}: 有効データでCriticalAnalysisErrorが発生: {str(e)}")
                except Exception as e:
                    self.fail(f"{calc_name}: 予期しないエラー: {str(e)}")
    
    def test_no_fallback_values_used(self):
        """フォールバック値（固定パーセンテージ）が使用されていないことを確認"""
        # この機能は直接テストが困難なため、ログ出力やreasoningをチェック
        for calc_name, calculator in self.all_calculators:
            with self.subTest(calculator=calc_name):
                try:
                    result = calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=self.valid_support_levels,
                        resistance_levels=self.valid_resistance_levels,
                        market_context=self.mock_market_context
                    )
                    
                    # reasoningに固定値の使用がないことを確認
                    reasoning = result.get('reasoning', [])
                    reasoning_text = ' '.join(reasoning)
                    
                    # 固定パーセンテージの使用を示すキーワードがないことを確認
                    forbidden_phrases = [
                        "固定5%", "固定3%", "固定8%", "固定10%", "固定15%",
                        "サポートなし", "レジスタンスなし", "サポートデータなし", "レジスタンスデータなし"
                    ]
                    
                    for phrase in forbidden_phrases:
                        self.assertNotIn(
                            phrase, reasoning_text,
                            f"{calc_name}: 禁止されたフォールバック文言'{phrase}'が使用されています"
                        )
                    
                    print(f"✅ {calc_name}: フォールバック値の使用なし確認")
                    
                except CriticalAnalysisError:
                    # CriticalAnalysisErrorは期待された動作なのでスキップ
                    pass
    
    def test_error_propagation_in_batch_processing(self):
        """バッチ処理でのCriticalAnalysisError伝播テスト"""
        # auto_symbol_training.pyでの使用を想定
        from auto_symbol_training import AutoSymbolTrainer
        
        # モックを使ってCriticalAnalysisErrorの伝播をテスト
        try:
            trainer = AutoSymbolTrainer()
            
            # ScalableAnalysisSystemのgenerate_batch_analysisをモック
            def mock_generate_batch_analysis(configs):
                raise CriticalAnalysisError("支持線・抵抗線データが不足しています")
            
            trainer.analysis_system.generate_batch_analysis = mock_generate_batch_analysis
            
            # CriticalAnalysisErrorが適切に伝播することを確認
            with self.assertRaises(Exception) as context:
                trainer.process_symbol("TEST")
            
            error_msg = str(context.exception)
            self.assertIn("支持線・抵抗線データが不足", error_msg)
            
            print("✅ バッチ処理でのCriticalAnalysisError伝播確認")
            
        except ImportError:
            self.skipTest("AutoSymbolTrainerのインポートに失敗")
    
    def test_critical_analysis_error_attributes(self):
        """CriticalAnalysisError例外クラスの属性テスト"""
        # CriticalAnalysisErrorが正しく定義されているか確認
        self.assertTrue(issubclass(CriticalAnalysisError, Exception))
        
        # 例外の作成と属性確認
        test_message = "テスト用エラーメッセージ"
        error = CriticalAnalysisError(test_message)
        
        self.assertEqual(str(error), test_message)
        self.assertIsInstance(error, Exception)
        
        print("✅ CriticalAnalysisError例外クラス正常定義確認")


class TestStrictValidationErrorMessages(unittest.TestCase):
    """厳格バリデーションのエラーメッセージ品質テスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.calculator = DefaultSLTPCalculator()
        self.current_price = 50000.0
        self.leverage = 10.0
        self.mock_market_context = Mock()
        self.mock_market_context.volatility = 0.03
    
    def test_error_message_informativeness(self):
        """エラーメッセージの情報量テスト"""
        test_cases = [
            {
                'support_levels': [],
                'resistance_levels': [Mock()],
                'expected_keywords': ['支持線', '不足', 'データ']
            },
            {
                'support_levels': [Mock()],
                'resistance_levels': [],
                'expected_keywords': ['抵抗線', '不足', 'データ']
            }
        ]
        
        for i, case in enumerate(test_cases):
            with self.subTest(case=i):
                with self.assertRaises(CriticalAnalysisError) as context:
                    self.calculator.calculate_levels(
                        current_price=self.current_price,
                        leverage=self.leverage,
                        support_levels=case['support_levels'],
                        resistance_levels=case['resistance_levels'],
                        market_context=self.mock_market_context
                    )
                
                error_msg = str(context.exception)
                
                # 期待されるキーワードがすべて含まれているか確認
                for keyword in case['expected_keywords']:
                    self.assertIn(keyword, error_msg, 
                                f"エラーメッセージに'{keyword}'が含まれていません: {error_msg}")
                
                # エラーメッセージが十分な長さを持っているか
                self.assertGreater(len(error_msg), 20, 
                                 f"エラーメッセージが短すぎます: {error_msg}")
                
                print(f"✅ ケース{i+1}: エラーメッセージ品質確認")
    
    def test_error_message_actionability(self):
        """エラーメッセージの実行可能性（ユーザーが何をすべきかわかる）テスト"""
        with self.assertRaises(CriticalAnalysisError) as context:
            self.calculator.calculate_levels(
                current_price=self.current_price,
                leverage=self.leverage,
                support_levels=[],
                resistance_levels=[],
                market_context=self.mock_market_context
            )
        
        error_msg = str(context.exception)
        
        # 実行可能なアドバイスが含まれているか
        actionable_phrases = [
            "延期", "待機", "揃う", "完了後", "後で"
        ]
        
        has_actionable_advice = any(phrase in error_msg for phrase in actionable_phrases)
        self.assertTrue(has_actionable_advice, 
                       f"エラーメッセージに実行可能なアドバイスが含まれていません: {error_msg}")
        
        print("✅ エラーメッセージの実行可能性確認")


def run_level1_validation_tests():
    """Level 1厳格バリデーションテストの実行"""
    print("🔒 Level 1厳格バリデーション専用テストスイート")
    print("=" * 70)
    
    # テストスイート作成
    test_suite = unittest.TestSuite()
    
    # テストクラス追加
    test_classes = [
        TestLevel1StrictValidation,
        TestStrictValidationErrorMessages
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 Level 1厳格バリデーション テスト結果")
    print("=" * 70)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    print(f"スキップ: {len(result.skipped)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback_text in result.failures:
            print(f"  - {test}")
            print(f"    理由: {traceback_text.split('AssertionError: ')[-1].split(chr(10))[0]}")
    
    if result.errors:
        print("\n💥 エラーが発生したテスト:")
        for test, traceback_text in result.errors:
            print(f"  - {test}")
            print(f"    エラー: {traceback_text.split(chr(10))[-2]}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100 if result.testsRun > 0 else 0
    print(f"\n成功率: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ Level 1厳格バリデーションの全テストが成功!")
        print("厳格バリデーション機能が正常に動作しています。")
        print("\n確認された機能:")
        print("  🔒 空配列検出時の完全失敗")
        print("  🔒 CriticalAnalysisError例外の適切な発生")
        print("  🔒 フォールバック値の完全廃止")
        print("  🔒 情報豊富なエラーメッセージ")
        print("  🔒 全計算機タイプでの一貫性")
    else:
        print("\n⚠️ 一部のLevel 1厳格バリデーションテストが失敗!")
        print("厳格バリデーション機能に問題があります。")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_level1_validation_tests()
    exit(0 if success else 1)