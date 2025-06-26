#!/usr/bin/env python3
"""
フィルタリングシステム統合テスト

auto_symbol_training.pyとFilteringFrameworkの統合動作を確認
"""

import unittest
import tempfile
import os
import sys
import asyncio
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


class TestFilteringSystemIntegration(BaseTest if USE_BASE_TEST else unittest.TestCase):
    """フィルタリングシステム統合テスト"""
    
    def setUp(self):
        """テスト前準備"""
        if USE_BASE_TEST:
            super().setUp()
        
        # テスト用の一時ディレクトリ
        self.test_dir = tempfile.mkdtemp()
        
        # モックデータの準備
        self.test_symbol = "TESTCOIN"
        self.test_execution_id = "test-exec-001"
    
    def tearDown(self):
        """テスト後清理"""
        if USE_BASE_TEST:
            super().tearDown()
        
        # 一時ディレクトリの削除
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('auto_symbol_training.ScalableAnalysisSystem')
    @patch('auto_symbol_training.ExecutionLogDatabase')
    def test_auto_symbol_trainer_initialization(self, mock_db, mock_analysis):
        """AutoSymbolTrainerの初期化テスト"""
        from auto_symbol_training import AutoSymbolTrainer
        
        trainer = AutoSymbolTrainer()
        
        # フィルタリングシステムが初期化されていることを確認
        self.assertIsNotNone(trainer.early_fail_validator)
        self.assertIsNotNone(trainer.analysis_system)
        self.assertIsNotNone(trainer.execution_db)
    
    @patch('auto_symbol_training.ScalableAnalysisSystem')
    @patch('auto_symbol_training.ExecutionLogDatabase')
    async def test_early_fail_validation_integration(self, mock_db, mock_analysis):
        """Early Fail検証統合テスト"""
        from auto_symbol_training import AutoSymbolTrainer
        
        trainer = AutoSymbolTrainer()
        
        # Early Fail検証をモック
        mock_validator = Mock()
        mock_result = Mock()
        mock_result.passed = True
        mock_result.metadata = {'test': 'data'}
        mock_validator.validate_symbol.return_value = mock_result
        trainer.early_fail_validator = mock_validator
        
        # 非同期Early Fail検証実行
        result = await trainer._run_early_fail_validation(self.test_symbol)
        
        # 結果の確認
        self.assertTrue(result.passed)
        mock_validator.validate_symbol.assert_called_once_with(self.test_symbol)
    
    @patch('auto_symbol_training.ScalableAnalysisSystem')
    @patch('auto_symbol_training.ExecutionLogDatabase')
    async def test_early_fail_validation_failure(self, mock_db, mock_analysis):
        """Early Fail検証失敗テスト"""
        from auto_symbol_training import AutoSymbolTrainer
        from symbol_early_fail_validator import FailReason
        
        trainer = AutoSymbolTrainer()
        
        # 失敗するEarly Fail検証をモック
        mock_validator = Mock()
        mock_result = Mock()
        mock_result.passed = False
        mock_result.fail_reason = FailReason.SYMBOL_NOT_FOUND
        mock_result.error_message = "Symbol not found"
        mock_result.suggestion = "Check symbol name"
        mock_validator.validate_symbol.return_value = mock_result
        trainer.early_fail_validator = mock_validator
        
        # 非同期Early Fail検証実行
        result = await trainer._run_early_fail_validation(self.test_symbol)
        
        # 失敗結果の確認
        self.assertFalse(result.passed)
        self.assertEqual(result.fail_reason, FailReason.SYMBOL_NOT_FOUND)
    
    @patch('auto_symbol_training.ScalableAnalysisSystem')
    @patch('auto_symbol_training.ExecutionLogDatabase')
    async def test_filtering_framework_integration(self, mock_db, mock_analysis):
        """FilteringFramework統合テスト"""
        from auto_symbol_training import AutoSymbolTrainer
        
        trainer = AutoSymbolTrainer()
        
        # テスト用設定データ
        test_configs = [
            {'symbol': self.test_symbol, 'timeframe': '1m', 'strategy': 'Conservative_ML'},
            {'symbol': self.test_symbol, 'timeframe': '5m', 'strategy': 'Conservative_ML'},
            {'symbol': self.test_symbol, 'timeframe': '1h', 'strategy': 'Aggressive_Traditional'},
            {'symbol': self.test_symbol, 'timeframe': '15m', 'strategy': 'Full_ML'},
        ]
        
        # FilteringFramework事前検証実行
        filtered_configs = await trainer._apply_filtering_framework(
            test_configs, self.test_symbol, self.test_execution_id
        )
        
        # フィルタリング結果の確認
        self.assertIsInstance(filtered_configs, list)
        self.assertLessEqual(len(filtered_configs), len(test_configs))
        
        # 期待される除外: Conservative_ML + 1m (短期間足)
        conservative_1m_filtered = not any(
            config['strategy'] == 'Conservative_ML' and config['timeframe'] == '1m' 
            for config in filtered_configs
        )
        self.assertTrue(conservative_1m_filtered, "Conservative_ML + 1mは除外されるべき")
        
        # 期待される除外: Aggressive_Traditional + 1h (長期間足)
        aggressive_1h_filtered = not any(
            config['strategy'] == 'Aggressive_Traditional' and config['timeframe'] == '1h'
            for config in filtered_configs
        )
        self.assertTrue(aggressive_1h_filtered, "Aggressive_Traditional + 1hは除外されるべき")
    
    async def test_config_viability_evaluation(self):
        """個別設定実行可能性評価テスト"""
        from auto_symbol_training import AutoSymbolTrainer
        
        trainer = AutoSymbolTrainer.__new__(AutoSymbolTrainer)  # __init__をスキップ
        
        # 有効な設定
        valid_config = {
            'symbol': self.test_symbol, 
            'timeframe': '5m', 
            'strategy': 'Conservative_ML'
        }
        result = await trainer._evaluate_config_viability(valid_config, self.test_symbol)
        self.assertTrue(result)
        
        # 無効な設定（必須フィールド不足）
        invalid_config = {'symbol': self.test_symbol}
        result = await trainer._evaluate_config_viability(invalid_config, self.test_symbol)
        self.assertFalse(result)
        
        # 除外される組み合わせ（Conservative_ML + 1m）
        filtered_config = {
            'symbol': self.test_symbol, 
            'timeframe': '1m', 
            'strategy': 'Conservative_ML'
        }
        result = await trainer._evaluate_config_viability(filtered_config, self.test_symbol)
        self.assertFalse(result)
    
    @patch('auto_symbol_training.ScalableAnalysisSystem')
    @patch('auto_symbol_training.ExecutionLogDatabase')
    async def test_filtering_statistics_recording(self, mock_db, mock_analysis):
        """フィルタリング統計記録テスト"""
        from auto_symbol_training import AutoSymbolTrainer
        
        trainer = AutoSymbolTrainer()
        
        # モックExecutionLogDatabase
        mock_db_instance = Mock()
        trainer.execution_db = mock_db_instance
        
        # フィルタリング統計記録
        await trainer._record_filtering_statistics(
            self.test_execution_id, 
            total_configs=10, 
            passed_configs=7, 
            filtered_configs=3
        )
        
        # execution_logにステップが追加されたことを確認
        mock_db_instance.add_execution_step.assert_called_once()
        
        call_args = mock_db_instance.add_execution_step.call_args
        self.assertEqual(call_args[0][0], self.test_execution_id)  # execution_id
        self.assertEqual(call_args[0][1], "filtering_framework_precheck")  # step
        
        # メタデータの確認
        metadata = call_args[1]['metadata']
        self.assertIn('filtering_statistics', metadata)
        stats = metadata['filtering_statistics']
        self.assertEqual(stats['total_configurations'], 10)
        self.assertEqual(stats['passed_configurations'], 7)
        self.assertEqual(stats['filtered_configurations'], 3)
        self.assertEqual(stats['filter_rate_percent'], 30.0)
    
    @patch('auto_symbol_training.ScalableAnalysisSystem')
    @patch('auto_symbol_training.ExecutionLogDatabase')
    @patch('symbol_early_fail_validator.SymbolEarlyFailValidator')
    async def test_end_to_end_integration(self, mock_validator_class, mock_db, mock_analysis):
        """End-to-End統合テスト"""
        from auto_symbol_training import AutoSymbolTrainer
        
        # Early Fail検証をモック
        mock_validator = Mock()
        mock_result = Mock()
        mock_result.passed = True
        mock_result.metadata = {}
        mock_validator.validate_symbol.return_value = mock_result
        mock_validator_class.return_value = mock_validator
        
        # ExecutionLogDatabaseをモック
        mock_db_instance = Mock()
        mock_db_instance.create_execution.return_value = self.test_execution_id
        mock_db.return_value = mock_db_instance
        
        trainer = AutoSymbolTrainer()
        
        # データ取得・検証をモック
        with patch.object(trainer, '_fetch_and_validate_data') as mock_fetch:
            mock_fetch.return_value = {'status': 'success'}
            
            # バックテスト実行をモック
            with patch.object(trainer, '_execute_strategies_independently') as mock_execute:
                mock_execute.return_value = 5  # 処理された設定数
                
                # 統合テスト実行
                try:
                    execution_id = await trainer.add_symbol_with_training(
                        symbol=self.test_symbol,
                        selected_strategies=['Conservative_ML', 'Full_ML'],
                        selected_timeframes=['5m', '15m', '1h']
                    )
                    
                    # 実行IDが返されることを確認
                    self.assertEqual(execution_id, self.test_execution_id)
                    
                    # Early Fail検証が呼ばれたことを確認
                    mock_validator.validate_symbol.assert_called_once_with(self.test_symbol)
                    
                    # データ取得・検証が呼ばれたことを確認
                    mock_fetch.assert_called_once()
                    
                    print("✅ End-to-End統合テスト成功")
                    
                except Exception as e:
                    self.fail(f"End-to-End統合テストでエラー: {str(e)}")


def run_async_test():
    """非同期テストの実行"""
    
    async def run_all_tests():
        test_instance = TestFilteringSystemIntegration()
        test_instance.setUp()
        
        try:
            print("🧪 フィルタリングシステム統合テスト開始")
            
            # Early Fail検証テスト
            await test_instance.test_early_fail_validation_integration()
            print("✅ Early Fail検証統合テスト成功")
            
            # FilteringFramework統合テスト
            await test_instance.test_filtering_framework_integration()
            print("✅ FilteringFramework統合テスト成功")
            
            # 設定評価テスト
            await test_instance.test_config_viability_evaluation()
            print("✅ 設定評価テスト成功")
            
            # 統計記録テスト
            await test_instance.test_filtering_statistics_recording()
            print("✅ 統計記録テスト成功")
            
            # End-to-End統合テスト
            await test_instance.test_end_to_end_integration()
            print("✅ End-to-End統合テスト成功")
            
            print("🎉 全ての非同期統合テスト成功！")
            
        finally:
            test_instance.tearDown()
    
    asyncio.run(run_all_tests())


if __name__ == '__main__':
    # 非同期テストの実行
    run_async_test()
    
    # 通常のunittestも実行
    unittest.main(verbosity=2)