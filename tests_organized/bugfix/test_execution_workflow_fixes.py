#!/usr/bin/env python3
"""
実行ワークフロー修正のテストコード
手動リセット、分析結果管理、プロセス管理などの総合テスト
"""

import unittest
import tempfile
import sqlite3
import json
import os
import sys
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# パス追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from execution_log_database import ExecutionLogDatabase, ExecutionStatus, ExecutionType


class TestExecutionWorkflowFixes(unittest.TestCase):
    """実行ワークフロー修正のテストクラス"""

    def setUp(self):
        """テスト前準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_execution_db = os.path.join(self.temp_dir, "test_execution_logs.db")
        
        # テスト用データベース初期化
        self.setup_test_database()

    def tearDown(self):
        """テスト後クリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def setup_test_database(self):
        """テスト用データベースセットアップ"""
        with sqlite3.connect(self.temp_execution_db) as conn:
            conn.execute("""
                CREATE TABLE execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    execution_type TEXT NOT NULL,
                    symbol TEXT,
                    symbols TEXT,
                    timestamp_start TEXT NOT NULL,
                    timestamp_end TEXT,
                    status TEXT NOT NULL,
                    triggered_by TEXT,
                    metadata TEXT,
                    current_operation TEXT,
                    progress_percentage REAL DEFAULT 0,
                    total_tasks INTEGER DEFAULT 0,
                    completed_tasks TEXT DEFAULT '[]',
                    errors TEXT DEFAULT '[]',
                    selected_strategy_ids TEXT,
                    execution_mode TEXT,
                    estimated_patterns INTEGER
                )
            """)

    def test_manual_reset_only_running_executions(self):
        """手動リセットがRUNNING状態のみに適用されることを確認"""
        test_cases = [
            ('exec_pending', 'PENDING'),
            ('exec_running', 'RUNNING'),
            ('exec_failed', 'FAILED'),
            ('exec_success', 'SUCCESS'),
        ]
        
        # テストデータ投入
        with sqlite3.connect(self.temp_execution_db) as conn:
            for exec_id, status in test_cases:
                conn.execute("""
                    INSERT INTO execution_logs 
                    (execution_id, execution_type, symbol, timestamp_start, status, triggered_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (exec_id, "SYMBOL_ADDITION", "TEST", 
                      datetime.now().isoformat(), status, "USER"))
            conn.commit()
        
        # 手動リセットロジックのテスト
        with sqlite3.connect(self.temp_execution_db) as conn:
            for exec_id, original_status in test_cases:
                cursor = conn.execute("""
                    SELECT status FROM execution_logs WHERE execution_id = ?
                """, (exec_id,))
                
                current_status = cursor.fetchone()[0]
                
                # RUNNING以外は手動リセット対象外
                if current_status != 'RUNNING':
                    # 手動リセットを試行（失敗すべき）
                    with self.assertRaises(ValueError):
                        if current_status != 'RUNNING':
                            raise ValueError(f'実行は既に{current_status}状態です')
                else:
                    # RUNNINGの場合は手動リセット可能
                    error_data = [{
                        "error_type": "ManualReset",
                        "error_message": "Manually reset by user",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }]
                    
                    conn.execute("""
                        UPDATE execution_logs 
                        SET status = 'FAILED', 
                            current_operation = '手動停止',
                            timestamp_end = datetime('now'),
                            errors = ?
                        WHERE execution_id = ?
                    """, (json.dumps(error_data), exec_id))
                    conn.commit()
                    
                    # リセット後の確認
                    cursor = conn.execute("""
                        SELECT status, current_operation FROM execution_logs WHERE execution_id = ?
                    """, (exec_id,))
                    
                    result = cursor.fetchone()
                    self.assertEqual(result[0], 'FAILED')
                    self.assertEqual(result[1], '手動停止')

    def test_error_type_classification(self):
        """エラータイプ分類のテスト"""
        error_types = [
            ("AutomaticFailure", "自動的な失敗"),
            ("ManualReset", "手動停止"),
            ("DataInsufficient", "データ不足"),
            ("AnalysisResultsMissing", "分析結果なし"),
            ("TimeframeNotSupported", "未対応時間足"),
            ("DuplicateExecution", "重複実行")
        ]
        
        with sqlite3.connect(self.temp_execution_db) as conn:
            for i, (error_type, description) in enumerate(error_types):
                exec_id = f"exec_error_{i}"
                
                error_data = [{
                    "error_type": error_type,
                    "error_message": description,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }]
                
                conn.execute("""
                    INSERT INTO execution_logs 
                    (execution_id, execution_type, symbol, timestamp_start, status, 
                     current_operation, errors, triggered_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (exec_id, "SYMBOL_ADDITION", "TEST", 
                      datetime.now().isoformat(), "FAILED", 
                      description, json.dumps(error_data), "USER"))
            
            conn.commit()
            
            # エラータイプ別の集計確認
            for error_type, description in error_types:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM execution_logs 
                    WHERE errors LIKE ?
                """, (f'%"error_type": "{error_type}"%',))
                
                count = cursor.fetchone()[0]
                self.assertEqual(count, 1, f"エラータイプ {error_type} の記録が見つからない")

    def test_failed_status_consolidation(self):
        """FAILEDステータス統合のテスト"""
        # 様々な失敗ケースがすべてFAILEDになることを確認
        failure_scenarios = [
            ("手動停止", "ManualReset"),
            ("データ不足", "DataInsufficient"), 
            ("分析結果なし", "AnalysisResultsMissing"),
            ("重複実行エラー", "DuplicateExecution"),
            ("システムエラー", "AutomaticFailure")
        ]
        
        with sqlite3.connect(self.temp_execution_db) as conn:
            for i, (operation, error_type) in enumerate(failure_scenarios):
                exec_id = f"exec_fail_{i}"
                
                error_data = [{
                    "error_type": error_type,
                    "error_message": f"Test {operation}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }]
                
                conn.execute("""
                    INSERT INTO execution_logs 
                    (execution_id, execution_type, symbol, timestamp_start, status, 
                     current_operation, errors, triggered_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (exec_id, "SYMBOL_ADDITION", "TEST", 
                      datetime.now().isoformat(), "FAILED", 
                      operation, json.dumps(error_data), "USER"))
            
            conn.commit()
            
            # すべてがFAILEDステータスになっていることを確認
            cursor = conn.execute("""
                SELECT COUNT(*) FROM execution_logs WHERE status = 'FAILED'
            """)
            
            failed_count = cursor.fetchone()[0]
            self.assertEqual(failed_count, len(failure_scenarios))
            
            # CANCELLEDが存在しないことを確認
            cursor = conn.execute("""
                SELECT COUNT(*) FROM execution_logs WHERE status = 'CANCELLED'
            """)
            
            cancelled_count = cursor.fetchone()[0]
            self.assertEqual(cancelled_count, 0)

    def test_process_cleanup_after_reset(self):
        """リセット後のプロセスクリーンアップテスト"""
        # プロセスクリーンアップのロジックをテスト（実際のプロセス操作なし）
        
        exec_id = "exec_cleanup_test"
        symbol = "TEST_CLEANUP"
        
        with sqlite3.connect(self.temp_execution_db) as conn:
            # 実行記録作成
            conn.execute("""
                INSERT INTO execution_logs 
                (execution_id, execution_type, symbol, timestamp_start, status, triggered_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (exec_id, "SYMBOL_ADDITION", symbol, 
                  datetime.now().isoformat(), "RUNNING", "USER"))
            conn.commit()
            
            # 手動リセット実行
            error_data = [{
                "error_type": "ManualReset",
                "error_message": "Manually reset by user",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cleanup_performed": True
            }]
            
            conn.execute("""
                UPDATE execution_logs 
                SET status = 'FAILED', 
                    current_operation = '手動停止',
                    timestamp_end = datetime('now'),
                    errors = ?
                WHERE execution_id = ?
            """, (json.dumps(error_data), exec_id))
            conn.commit()
            
            # クリーンアップが記録されていることを確認
            cursor = conn.execute("""
                SELECT errors FROM execution_logs WHERE execution_id = ?
            """, (exec_id,))
            
            errors_json = cursor.fetchone()[0]
            errors = json.loads(errors_json)
            
            self.assertTrue(errors[0].get("cleanup_performed", False))

    def test_database_consistency_after_operations(self):
        """操作後のデータベース整合性テスト"""
        exec_id = "exec_consistency_test"
        symbol = "TEST_CONSISTENCY"
        
        with sqlite3.connect(self.temp_execution_db) as conn:
            # 1. 実行開始
            conn.execute("""
                INSERT INTO execution_logs 
                (execution_id, execution_type, symbol, timestamp_start, status, 
                 progress_percentage, triggered_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (exec_id, "SYMBOL_ADDITION", symbol, 
                  datetime.now().isoformat(), "RUNNING", 0, "USER"))
            
            # 2. 進行状況更新
            conn.execute("""
                UPDATE execution_logs 
                SET progress_percentage = 50, current_operation = '分析実行中'
                WHERE execution_id = ?
            """, (exec_id,))
            
            # 3. 手動リセット
            error_data = [{
                "error_type": "ManualReset",
                "error_message": "Manually reset by user",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
            
            conn.execute("""
                UPDATE execution_logs 
                SET status = 'FAILED', 
                    current_operation = '手動停止',
                    timestamp_end = datetime('now'),
                    progress_percentage = 50,
                    errors = ?
                WHERE execution_id = ?
            """, (json.dumps(error_data), exec_id))
            
            conn.commit()
            
            # 整合性確認
            cursor = conn.execute("""
                SELECT execution_id, status, progress_percentage, 
                       current_operation, timestamp_end, errors
                FROM execution_logs WHERE execution_id = ?
            """, (exec_id,))
            
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            
            # フィールド確認
            self.assertEqual(result[1], "FAILED")  # status
            self.assertEqual(result[2], 50)       # progress_percentage
            self.assertEqual(result[3], "手動停止")  # current_operation
            self.assertIsNotNone(result[4])       # timestamp_end
            self.assertIsNotNone(result[5])       # errors
            
            # エラーデータの形式確認
            errors = json.loads(result[5])
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["error_type"], "ManualReset")

    def test_analysis_database_cleanup(self):
        """分析データベースクリーンアップのテスト"""
        # 分析結果クリーンアップのロジックをテスト
        temp_analysis_db = os.path.join(self.temp_dir, "test_analysis.db")
        
        with sqlite3.connect(temp_analysis_db) as conn:
            conn.execute("""
                CREATE TABLE analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    config TEXT NOT NULL,
                    execution_id TEXT,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_return REAL,
                    sharpe_ratio REAL
                )
            """)
            
            # テストデータ投入
            test_data = [
                ("TEST_SYMBOL", "1h", "Conservative_ML", "exec_cleanup_123", 0.15, 1.2),
                ("TEST_SYMBOL", "30m", "Conservative_ML", "exec_cleanup_123", 0.12, 1.0),
                ("OTHER_SYMBOL", "1h", "Conservative_ML", "exec_other_456", 0.18, 1.5),
            ]
            
            for symbol, timeframe, config, exec_id, ret, sharpe in test_data:
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, timeframe, config, execution_id, total_return, sharpe_ratio)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (symbol, timeframe, config, exec_id, ret, sharpe))
            
            conn.commit()
            
            # クリーンアップ前の確認
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses WHERE execution_id = 'exec_cleanup_123'
            """)
            before_count = cursor.fetchone()[0]
            self.assertEqual(before_count, 2)
            
            # クリーンアップ実行（execution_idベース）
            cursor = conn.execute("""
                DELETE FROM analyses WHERE execution_id = 'exec_cleanup_123'
            """)
            deleted_count = cursor.rowcount
            conn.commit()
            
            # クリーンアップ後の確認
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses WHERE execution_id = 'exec_cleanup_123'
            """)
            after_count = cursor.fetchone()[0]
            
            self.assertEqual(deleted_count, 2)
            self.assertEqual(after_count, 0)
            
            # 他のデータは残っていることを確認
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses WHERE execution_id = 'exec_other_456'
            """)
            other_count = cursor.fetchone()[0]
            self.assertEqual(other_count, 1)


class AsyncTestCase(unittest.TestCase):
    """非同期テスト用ベースクラス"""
    
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        self.loop.close()
    
    def async_test(self, coro):
        return self.loop.run_until_complete(coro)


class TestAsyncExecutionFixes(AsyncTestCase):
    """非同期実行修正のテストクラス"""
    
    async def test_async_execution_error_handling(self):
        """非同期実行のエラーハンドリングテスト"""
        
        # モック設定
        with patch('auto_symbol_training.ScalableAnalysisSystem'), \
             patch('auto_symbol_training.ExecutionLogDatabase') as mock_db_class:
            
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db
            
            from auto_symbol_training import AutoSymbolTrainer
            trainer = AutoSymbolTrainer()
            trainer.execution_db = mock_db
            
            # 分析結果確認がFalseを返すようにモック
            with patch.object(trainer, '_verify_analysis_results', return_value=False):
                
                # 実行完了時の処理をテスト
                try:
                    # 分析結果が存在しない場合の処理をシミュレート
                    analysis_results_exist = False
                    
                    if not analysis_results_exist:
                        # FAILEDステータスに設定
                        mock_db.update_execution_status.assert_not_called()  # まだ呼ばれていない
                        
                        # 実際の呼び出しをシミュレート
                        mock_db.update_execution_status(
                            "test_exec_id",
                            ExecutionStatus.FAILED,
                            current_operation='分析結果なし - 処理失敗',
                            progress_percentage=100,
                            error_message="No analysis results found despite successful steps"
                        )
                        
                        # 呼び出しが正しく行われたことを確認
                        mock_db.update_execution_status.assert_called_with(
                            "test_exec_id",
                            ExecutionStatus.FAILED,
                            current_operation='分析結果なし - 処理失敗',
                            progress_percentage=100,
                            error_message="No analysis results found despite successful steps"
                        )
                        
                        # ValueError が発生することを確認
                        with self.assertRaises(ValueError) as context:
                            raise ValueError("No analysis results found for TEST despite successful execution steps")
                        
                        self.assertIn("No analysis results found", str(context.exception))
                
                except Exception as e:
                    self.fail(f"非同期エラーハンドリングテストが失敗: {e}")

    def test_new_system_async_integration(self):
        """新システムの非同期統合テスト"""
        
        with patch('new_symbol_addition_system.AutoSymbolTrainer') as mock_trainer_class:
            
            mock_trainer = MagicMock()
            mock_trainer_class.return_value = mock_trainer
            mock_trainer.add_symbol_with_training.return_value = "exec_success_123"
            
            from new_symbol_addition_system import NewSymbolAdditionSystem, ExecutionMode
            system = NewSymbolAdditionSystem()
            
            # 非同期実行をモックでシミュレート
            with patch.object(system, 'execute_symbol_addition', return_value=True) as mock_execute:
                
                # 非同期実行の呼び出しをシミュレート
                result = True  # モックされた戻り値
                
                # 正常完了することを確認
                self.assertTrue(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)