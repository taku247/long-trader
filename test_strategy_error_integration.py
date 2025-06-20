#!/usr/bin/env python3
"""
未定義戦略エラーの統合テスト

実際の銘柄追加フローで未定義戦略エラーが適切に処理されることを検証
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import json

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.unified_config_manager import UnifiedConfigManager
from auto_symbol_training import AutoSymbolTrainer
from scalable_analysis_system import ScalableAnalysisSystem


class TestStrategyErrorIntegration(unittest.TestCase):
    """未定義戦略エラーの統合テストクラス"""
    
    def setUp(self):
        """テスト前準備"""
        # シングルトンをリセット
        UnifiedConfigManager._instance = None
        UnifiedConfigManager._initialized = False
        
    def tearDown(self):
        """テスト後クリーンアップ"""
        # シングルトンをリセット
        UnifiedConfigManager._instance = None
        UnifiedConfigManager._initialized = False
    
    def test_scalable_analysis_system_error_handling(self):
        """🔍 ScalableAnalysisSystemでの未定義戦略エラー処理をテスト"""
        system = ScalableAnalysisSystem()
        
        # 未定義戦略での分析を試行
        with self.assertRaises(ValueError) as context:
            result = system.run_single_analysis("TEST", "1h", "Aggressive_Traditional")
        
        error_msg = str(context.exception)
        self.assertIn("未定義の戦略: 'Aggressive_Traditional'", error_msg)
        self.assertIn("利用可能な戦略:", error_msg)
        
        print("✅ ScalableAnalysisSystem: 未定義戦略で適切にValueError発生")
        print(f"   エラーメッセージ: {error_msg}")
    
    @patch('auto_symbol_training.AutoSymbolTrainer._run_comprehensive_backtest')
    @patch('auto_symbol_training.AutoSymbolTrainer._fetch_and_validate_data')
    def test_auto_symbol_trainer_error_handling(self, mock_fetch, mock_backtest):
        """🚀 AutoSymbolTrainerでの未定義戦略エラー処理をテスト"""
        
        # モックデータ設定
        mock_fetch.return_value = {"status": "success", "data_points": 2000}
        mock_backtest.side_effect = ValueError("未定義の戦略: 'Aggressive_Traditional'. 利用可能な戦略: ['Conservative_ML', 'Aggressive_ML', 'Balanced']")
        
        trainer = AutoSymbolTrainer()
        
        # 未定義戦略使用時のエラーをテスト
        with self.assertRaises(ValueError) as context:
            # 非同期関数を同期的に実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(trainer.add_symbol_with_training("TEST"))
            finally:
                loop.close()
        
        error_msg = str(context.exception)
        self.assertIn("未定義の戦略", error_msg)
        
        print("✅ AutoSymbolTrainer: 未定義戦略使用時に適切にエラー伝播")
        print(f"   エラーメッセージ: {error_msg}")
    
    def test_strategy_list_accuracy(self):
        """📋 利用可能戦略リストの正確性をテスト"""
        config_manager = UnifiedConfigManager()
        
        with self.assertRaises(ValueError) as context:
            config_manager.get_strategy_config("InvalidStrategy")
        
        error_msg = str(context.exception)
        
        # 実際の設定ファイルから戦略リストを取得
        expected_strategies = list(config_manager.trading_config.get('strategy_configs', {}).keys())
        
        for strategy in expected_strategies:
            self.assertIn(strategy, error_msg)
        
        print(f"✅ 戦略リスト正確性: 利用可能戦略 {expected_strategies} が正しく表示")
    
    def test_error_message_user_friendliness(self):
        """👥 エラーメッセージのユーザーフレンドリー性をテスト"""
        config_manager = UnifiedConfigManager()
        
        test_cases = [
            "Aggressive_Traditional",
            "Full_ML",
            "RandomStrategy"
        ]
        
        for strategy in test_cases:
            with self.subTest(strategy=strategy):
                with self.assertRaises(ValueError) as context:
                    config_manager.get_strategy_config(strategy)
                
                error_msg = str(context.exception)
                
                # ユーザーフレンドリー要素をチェック
                self.assertIn(f"未定義の戦略: '{strategy}'", error_msg)  # 明確な問題特定
                self.assertIn("利用可能な戦略:", error_msg)  # 解決策提示
                self.assertIn("Conservative_ML", error_msg)  # 具体的選択肢
                self.assertIn("Aggressive_ML", error_msg)
                self.assertIn("Balanced", error_msg)
                
                print(f"✅ ユーザーフレンドリー性: '{strategy}' のエラーメッセージは明確")
    
    @patch('builtins.print')
    def test_console_output_format(self, mock_print):
        """🖥️ コンソール出力の形式をテスト"""
        config_manager = UnifiedConfigManager()
        
        with self.assertRaises(ValueError):
            config_manager.get_strategy_config("Aggressive_Traditional")
        
        # print呼び出しを確認
        print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
        
        # エラーメッセージがコンソールに出力されているかチェック
        error_output = None
        for call in print_calls:
            if "❌ 未定義の戦略" in call:
                error_output = call
                break
        
        self.assertIsNotNone(error_output, "エラーメッセージがコンソールに出力されていません")
        self.assertIn("❌", error_output)  # 視覚的なエラーアイコン
        self.assertIn("Aggressive_Traditional", error_output)
        
        print(f"✅ コンソール出力: エラーメッセージが適切に表示")
        print(f"   出力内容: {error_output}")


def run_integration_test():
    """統合テスト実行"""
    print("=" * 70)
    print("🔄 未定義戦略エラー統合テスト開始")
    print("=" * 70)
    
    # テストスイート作成
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestStrategyErrorIntegration)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("\n" + "=" * 70)
    print("📊 統合テスト結果サマリー")
    print("=" * 70)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, trace in result.failures:
            print(f"  - {test}")
            trace_lines = trace.split('\n')
            print(f"    {trace_lines[-2] if len(trace_lines) > 1 else trace}")
    
    if result.errors:
        print("\n💥 エラーが発生したテスト:")
        for test, trace in result.errors:
            print(f"  - {test}")
            error_lines = trace.split('\n')
            print(f"    {error_lines[-2] if len(error_lines) > 1 else trace}")
    
    if result.wasSuccessful():
        print("\n🎉 全ての統合テストが成功しました！")
        print("✅ 未定義戦略エラーは適切にシステム全体で処理されます")
        print("✅ エラーメッセージはユーザーフレンドリーです")
        print("✅ 銘柄追加プロセスで適切にエラーが検出されます")
    else:
        print("\n⚠️ いくつかの統合テストが失敗しました")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)