#!/usr/bin/env python3
"""
未定義戦略エラーテスト

フォールバック除去により、未定義戦略が適切にエラーになることをテスト
"""

import sys
import os
import unittest
from unittest.mock import patch
import tempfile
import json

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.unified_config_manager import UnifiedConfigManager


class TestUndefinedStrategyError(unittest.TestCase):
    """未定義戦略エラーのテストクラス"""
    
    def setUp(self):
        """テスト前準備"""
        # シングルトンをリセット
        UnifiedConfigManager._instance = None
        UnifiedConfigManager._initialized = False
        
        # テスト用設定ファイルを作成
        self.test_config = {
            "description": "テスト用設定",
            "strategy_configs": {
                "Conservative_ML": {
                    "description": "保守的ML戦略",
                    "sltp_calculator": "ConservativeSLTPCalculator",
                    "risk_multiplier": 0.8,
                    "confidence_boost": 0.0,
                    "leverage_cap": 50
                },
                "Aggressive_ML": {
                    "description": "積極的ML戦略", 
                    "sltp_calculator": "AggressiveSLTPCalculator",
                    "risk_multiplier": 1.2,
                    "confidence_boost": -0.05,
                    "leverage_cap": 100
                },
                "Balanced": {
                    "description": "バランス戦略",
                    "sltp_calculator": "DefaultSLTPCalculator",
                    "risk_multiplier": 1.0,
                    "confidence_boost": 0.0,
                    "leverage_cap": 75
                }
            }
        }
        
        # 一時設定ファイル作成
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_config, self.temp_file, indent=2)
        self.temp_file.close()
        
    def tearDown(self):
        """テスト後クリーンアップ"""
        # 一時ファイル削除
        os.unlink(self.temp_file.name)
        
        # シングルトンをリセット
        UnifiedConfigManager._instance = None
        UnifiedConfigManager._initialized = False
    
    def test_valid_strategy_success(self):
        """✅ 有効な戦略で正常動作することをテスト"""
        config_manager = UnifiedConfigManager(trading_config_file=self.temp_file.name)
        
        # 定義済み戦略は正常に取得できる
        conservative_config = config_manager.get_strategy_config("Conservative_ML")
        self.assertEqual(conservative_config["risk_multiplier"], 0.8)
        self.assertEqual(conservative_config["leverage_cap"], 50)
        
        aggressive_config = config_manager.get_strategy_config("Aggressive_ML")
        self.assertEqual(aggressive_config["risk_multiplier"], 1.2)
        self.assertEqual(aggressive_config["leverage_cap"], 100)
        
        balanced_config = config_manager.get_strategy_config("Balanced")
        self.assertEqual(balanced_config["risk_multiplier"], 1.0)
        self.assertEqual(balanced_config["leverage_cap"], 75)
        
        print("✅ 有効戦略テスト: 全ての定義済み戦略が正常に取得できました")
    
    def test_undefined_strategy_error(self):
        """❌ 未定義戦略でValueErrorが発生することをテスト"""
        config_manager = UnifiedConfigManager(trading_config_file=self.temp_file.name)
        
        # 未定義戦略のテストケース
        undefined_strategies = [
            "Aggressive_Traditional",
            "Full_ML", 
            "NonExistentStrategy",
            "InvalidConfig"
        ]
        
        for strategy in undefined_strategies:
            with self.subTest(strategy=strategy):
                with self.assertRaises(ValueError) as context:
                    config_manager.get_strategy_config(strategy)
                
                # エラーメッセージの内容を検証
                error_msg = str(context.exception)
                self.assertIn(f"未定義の戦略: '{strategy}'", error_msg)
                self.assertIn("利用可能な戦略:", error_msg)
                self.assertIn("Conservative_ML", error_msg)
                self.assertIn("Aggressive_ML", error_msg)
                self.assertIn("Balanced", error_msg)
                
                print(f"✅ 未定義戦略エラーテスト: '{strategy}' → 適切にValueError発生")
    
    def test_error_message_format(self):
        """📝 エラーメッセージの形式をテスト"""
        config_manager = UnifiedConfigManager(trading_config_file=self.temp_file.name)
        
        with self.assertRaises(ValueError) as context:
            config_manager.get_strategy_config("Aggressive_Traditional")
        
        error_msg = str(context.exception)
        
        # メッセージ形式の検証
        self.assertTrue(error_msg.startswith("未定義の戦略: 'Aggressive_Traditional'"))
        self.assertIn("利用可能な戦略: ['Conservative_ML', 'Aggressive_ML', 'Balanced']", error_msg)
        
        print(f"✅ エラーメッセージ形式テスト: {error_msg}")
    
    @patch('builtins.print')
    def test_error_logging(self, mock_print):
        """🖨️ エラーログ出力をテスト"""
        config_manager = UnifiedConfigManager(trading_config_file=self.temp_file.name)
        
        with self.assertRaises(ValueError):
            config_manager.get_strategy_config("Full_ML")
        
        # print関数が呼ばれたことを確認
        mock_print.assert_called()
        
        # 最後のprint呼び出しがエラーメッセージか確認
        last_call = mock_print.call_args_list[-1][0][0]
        self.assertIn("❌ 未定義の戦略: 'Full_ML'", last_call)
        self.assertIn("利用可能な戦略:", last_call)
        
        print("✅ エラーログ出力テスト: エラーメッセージが正しく出力されています")
    
    def test_empty_strategy_configs(self):
        """🗂️ 空の戦略設定でのエラーをテスト"""
        # 空の戦略設定
        empty_config = {
            "description": "空設定テスト",
            "strategy_configs": {}
        }
        
        temp_empty_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(empty_config, temp_empty_file, indent=2)
        temp_empty_file.close()
        
        try:
            config_manager = UnifiedConfigManager(trading_config_file=temp_empty_file.name)
            
            with self.assertRaises(ValueError) as context:
                config_manager.get_strategy_config("Conservative_ML")
            
            error_msg = str(context.exception)
            self.assertIn("利用可能な戦略: []", error_msg)
            
            print("✅ 空戦略設定テスト: 空リストが適切に表示されています")
            
        finally:
            os.unlink(temp_empty_file.name)
    
    def test_case_sensitivity(self):
        """🔤 戦略名の大文字小文字区別をテスト"""
        config_manager = UnifiedConfigManager(trading_config_file=self.temp_file.name)
        
        # 大文字小文字が異なる戦略名でエラーテスト
        case_variations = [
            "conservative_ml",  # 小文字
            "CONSERVATIVE_ML",  # 大文字
            "Conservative_ml",  # 混在
            "aggressive_ML"     # 混在
        ]
        
        for strategy in case_variations:
            with self.subTest(strategy=strategy):
                with self.assertRaises(ValueError) as context:
                    config_manager.get_strategy_config(strategy)
                
                error_msg = str(context.exception)
                self.assertIn(f"未定義の戦略: '{strategy}'", error_msg)
                
                print(f"✅ 大文字小文字区別テスト: '{strategy}' → 適切にエラー")


def run_comprehensive_test():
    """包括的テスト実行"""
    print("=" * 70)
    print("🧪 未定義戦略エラーテスト開始")
    print("=" * 70)
    
    # テストスイート作成
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestUndefinedStrategyError)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("\n" + "=" * 70)
    print("📊 テスト結果サマリー")
    print("=" * 70)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, trace in result.failures:
            print(f"  - {test}: {trace.splitlines()[-1]}")
    
    if result.errors:
        print("\n💥 エラーが発生したテスト:")
        for test, trace in result.errors:
            print(f"  - {test}: {trace.splitlines()[-1]}")
    
    if result.wasSuccessful():
        print("\n🎉 全てのテストが成功しました！")
        print("✅ 未定義戦略は適切にエラーで検出されます")
        print("✅ フォールバック機能は完全に除去されました")
    else:
        print("\n⚠️ いくつかのテストが失敗しました")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)