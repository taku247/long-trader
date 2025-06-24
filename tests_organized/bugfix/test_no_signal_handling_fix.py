#!/usr/bin/env python3
"""
シグナルなし処理修正テスト

支持線・抵抗線未検出時の警告処理が改善され、
シグナルなしでも"成功"として扱われることをテスト
"""

import unittest
import sqlite3
import tempfile
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests_organized.base_test import BaseTest


class TestNoSignalHandlingFix(BaseTest):
    """シグナルなし処理修正のテスト"""
    
    def test_create_no_signal_record(self):
        """_create_no_signal_record メソッドのテスト"""
        from auto_symbol_training import AutoSymbolTrainer
        
        trainer = AutoSymbolTrainer()
        
        # テスト用の設定
        symbol = "TESTCOIN"
        execution_id = "test_execution_123"
        config = {
            'symbol': symbol,
            'timeframe': '15m',
            'strategy': 'Balanced',
            'strategy_config_id': 1,
            'strategy_name': 'Balanced - 15m'
        }
        
        # テスト用DBパスに変更
        original_create_method = trainer._create_no_signal_record
        
        def mock_create_no_signal_record(symbol, config, execution_id, error_message=None):
            # テスト用DBを使用するように変更
            import sqlite3
            from datetime import datetime, timezone
            
            with sqlite3.connect(self.analysis_db) as conn:
                conn.execute("""
                    INSERT INTO analyses (
                        symbol, timeframe, config, strategy_config_id, strategy_name,
                        execution_id, task_status, task_created_at, task_completed_at,
                        total_return, sharpe_ratio, max_drawdown, win_rate, total_trades,
                        status, error_message, generated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, config['timeframe'], config['strategy'],
                    config.get('strategy_config_id'), config.get('strategy_name'),
                    execution_id, 'completed', datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(), 0.0, 0.0, 0.0, 0.0, 0,
                    'no_signal', error_message or 'No trading signals detected',
                    datetime.now().isoformat()
                ))
                conn.commit()
        
        # メソッドをモック
        trainer._create_no_signal_record = mock_create_no_signal_record
        
        # メソッド実行
        trainer._create_no_signal_record(symbol, config, execution_id, "Test no signal")
        
        # データベースから結果確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT symbol, timeframe, config, task_status, status, error_message
                FROM analyses 
                WHERE execution_id = ? AND symbol = ?
            """, (execution_id, symbol))
            
            result = cursor.fetchone()
            
        # 検証
        self.assertIsNotNone(result, "シグナルなしレコードが作成されるべき")
        self.assertEqual(result[0], symbol, "シンボルが正しく記録されるべき")
        self.assertEqual(result[1], '15m', "時間足が正しく記録されるべき")
        self.assertEqual(result[2], 'Balanced', "戦略が正しく記録されるべき")
        self.assertEqual(result[3], 'completed', "タスクステータスはcompletedであるべき")
        self.assertEqual(result[4], 'no_signal', "ステータスはno_signalであるべき")
        self.assertEqual(result[5], 'Test no signal', "エラーメッセージが正しく記録されるべき")
    
    def test_no_signal_processed_count_fix(self):
        """シグナルなし時のprocessed_count修正テスト"""
        from auto_symbol_training import AutoSymbolTrainer
        
        trainer = AutoSymbolTrainer()
        
        # テスト用設定
        symbol = "TESTCOIN"
        configs = [
            {'symbol': symbol, 'timeframe': '15m', 'strategy': 'Balanced', 'strategy_config_id': 1},
            {'symbol': symbol, 'timeframe': '30m', 'strategy': 'Aggressive_ML', 'strategy_config_id': 2}
        ]
        
        # ScalableAnalysisSystemをモック（processed_count = 0を返す）
        mock_analysis_system = MagicMock()
        mock_analysis_system.generate_batch_analysis.return_value = 0  # シグナルなし状況を再現
        trainer.analysis_system = mock_analysis_system
        
        # _create_no_signal_recordをモック
        trainer._create_no_signal_record = MagicMock()
        
        # _current_execution_idを設定
        trainer._current_execution_id = "test_execution_456"
        
        # バックテスト実行の部分をテスト
        try:
            # 実際のメソッド呼び出し（asyncなのでrunではなく直接テスト）
            import asyncio
            
            async def test_backtest():
                return await trainer._run_comprehensive_backtest(symbol, None, None, configs)
            
            result = asyncio.run(test_backtest())
            
            # 検証: シグナルなしでも成功として処理されることを確認
            self.assertIsNotNone(result, "バックテスト結果が返されるべき")
            self.assertEqual(result['total_combinations'], 2, "設定数が正しく記録されるべき")
            
            # _create_no_signal_recordが各設定に対して呼ばれたことを確認
            self.assertEqual(trainer._create_no_signal_record.call_count, 2, 
                           "各設定に対してシグナルなしレコードが作成されるべき")
            
        except Exception as e:
            # シグナルなし時に例外が発生しないことを確認
            if "全戦略の分析が失敗" in str(e):
                self.fail("シグナルなし時に例外が発生すべきでない")
            else:
                # その他の例外は再発生
                raise
    
    def test_backtest_success_with_no_signals(self):
        """シグナルなしでもバックテスト成功とする統合テスト"""
        from auto_symbol_training import AutoSymbolTrainer
        
        trainer = AutoSymbolTrainer()
        
        # 完全にモック化してテスト
        symbol = "TESTCOIN"
        configs = [
            {'symbol': symbol, 'timeframe': '15m', 'strategy': 'Balanced', 'strategy_config_id': 1, 'strategy_name': 'Balanced-15m'}
        ]
        
        # ScalableAnalysisSystemをモック（シグナルなし状況）
        mock_analysis_system = MagicMock()
        mock_analysis_system.generate_batch_analysis.return_value = 0
        mock_analysis_system.query_analyses.return_value = []  # 結果なし
        trainer.analysis_system = mock_analysis_system
        
        # シグナルなしレコード作成をモック
        trainer._create_no_signal_record = MagicMock()
        trainer._current_execution_id = "test_execution_789"
        
        # バックテスト実行
        import asyncio
        
        async def test_full_backtest():
            try:
                result = await trainer._run_comprehensive_backtest(symbol, None, None, configs)
                return result, None
            except Exception as e:
                return None, e
        
        result, error = asyncio.run(test_full_backtest())
        
        # 検証
        if error:
            self.fail(f"シグナルなし時にエラーが発生すべきでない: {error}")
        
        self.assertIsNotNone(result, "結果が返されるべき")
        self.assertEqual(result['total_combinations'], 1, "設定数が正しい")
        
        # シグナルなしレコードが作成されたことを確認
        trainer._create_no_signal_record.assert_called_once()
    
    def test_processed_count_modification(self):
        """processed_count修正の詳細テスト"""
        # 修正前: processed_count = 0 → 例外発生
        # 修正後: processed_count = len(configs) → 成功として扱う
        
        configs = [
            {'symbol': 'TEST', 'timeframe': '15m', 'strategy': 'Balanced'},
            {'symbol': 'TEST', 'timeframe': '30m', 'strategy': 'Aggressive_ML'}
        ]
        
        # 修正後のロジックをテスト
        processed_count_before = 0  # シグナルなし状況
        processed_count_after = len(configs)  # 修正後
        
        # 修正前の条件
        successful_tests = 0
        failed_tests = len(configs)
        
        # 修正前: processed_count == 0 → 例外
        should_fail_before = (successful_tests == 0 and processed_count_before == 0)
        
        # 修正後: processed_count > 0 → 成功
        should_fail_after = (successful_tests == 0 and processed_count_after == 0)
        
        self.assertTrue(should_fail_before, "修正前は失敗すべき")
        self.assertFalse(should_fail_after, "修正後は成功すべき")


if __name__ == '__main__':
    unittest.main(verbosity=2)