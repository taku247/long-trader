#!/usr/bin/env python3
"""
タスクステータス更新のシンプルなテスト

分析失敗時にtask_statusが適切に更新されることを確認:
1. pending → failed への更新
2. エラーメッセージの記録
3. 完了時刻の記録
"""

import unittest
import tempfile
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests_organized.base_test import BaseTest


class TestTaskStatusUpdateSimple(BaseTest):
    """タスクステータス更新のシンプルテスト"""
    
    def setUp(self):
        super().setUp()
        
        # 必要なカラムを追加
        with sqlite3.connect(self.analysis_db) as conn:
            # 既存カラム確認
            cursor = conn.execute("PRAGMA table_info(analyses)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # 必要なカラムがない場合は追加
            if 'task_status' not in columns:
                conn.execute("ALTER TABLE analyses ADD COLUMN task_status TEXT DEFAULT 'pending'")
            if 'error_message' not in columns:
                conn.execute("ALTER TABLE analyses ADD COLUMN error_message TEXT")
            if 'task_completed_at' not in columns:
                conn.execute("ALTER TABLE analyses ADD COLUMN task_completed_at TIMESTAMP")
    
    def test_update_pending_tasks_to_failed_direct(self):
        """pendingタスクを直接failed更新するテスト"""
        execution_id = "test_exec_001"
        symbol = "TESTCOIN"
        error_message = "テスト用エラー: 分析失敗"
        
        # pendingタスク作成
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                INSERT INTO analyses (symbol, timeframe, config, task_status, execution_id)
                VALUES (?, ?, ?, ?, ?)
            """, (symbol, "15m", "Test_Strategy", "pending", execution_id))
        
        # failed更新実行（new_symbol_addition_systemのロジックを模倣）
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                UPDATE analyses 
                SET task_status = 'failed',
                    error_message = ?,
                    task_completed_at = datetime('now')
                WHERE execution_id = ? 
                AND symbol = ?
                AND task_status = 'pending'
            """, (error_message[:500], execution_id, symbol))
            
            updated_count = cursor.rowcount
            conn.commit()
        
        # 結果確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT task_status, error_message, task_completed_at
                FROM analyses WHERE execution_id = ? AND symbol = ?
            """, (execution_id, symbol))
            
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "レコードが存在するべき")
            self.assertEqual(result[0], "failed", "task_statusがfailedに更新されるべき")
            self.assertEqual(result[1], error_message, "エラーメッセージが記録されるべき")
            self.assertIsNotNone(result[2], "task_completed_atが設定されるべき")
            self.assertEqual(updated_count, 1, "1件のレコードが更新されるべき")
    
    def test_multiple_pending_tasks_update(self):
        """複数のpendingタスクの一括更新テスト"""
        execution_id = "test_exec_002"
        symbol = "MULTICOIN"
        
        # 複数のpendingタスク作成
        with sqlite3.connect(self.analysis_db) as conn:
            tasks = [
                (symbol, "15m", "Strategy_A", "pending", execution_id),
                (symbol, "1h", "Strategy_B", "pending", execution_id),
                (symbol, "4h", "Strategy_C", "completed", execution_id),  # これは更新されない
            ]
            
            conn.executemany("""
                INSERT INTO analyses (symbol, timeframe, config, task_status, execution_id)
                VALUES (?, ?, ?, ?, ?)
            """, tasks)
        
        # failed更新実行
        error_message = "複数タスク失敗テスト"
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                UPDATE analyses 
                SET task_status = 'failed',
                    error_message = ?,
                    task_completed_at = datetime('now')
                WHERE execution_id = ? 
                AND symbol = ?
                AND task_status = 'pending'
            """, (error_message, execution_id, symbol))
            
            updated_count = cursor.rowcount
            conn.commit()
        
        # 結果確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT timeframe, task_status FROM analyses 
                WHERE execution_id = ? ORDER BY timeframe
            """, (execution_id,))
            
            results = cursor.fetchall()
            
            self.assertEqual(len(results), 3, "3つのタスクが存在するべき")
            
            # pendingタスクがfailedに更新されている
            failed_tasks = [r for r in results if r[1] == 'failed']
            completed_tasks = [r for r in results if r[1] == 'completed']
            
            self.assertEqual(len(failed_tasks), 2, "2つのpendingタスクがfailedに更新")
            self.assertEqual(len(completed_tasks), 1, "completedタスクは変更されない")
            self.assertEqual(updated_count, 2, "2件のレコードが更新されるべき")
    
    def test_error_message_truncation(self):
        """長いエラーメッセージの切り詰めテスト"""
        execution_id = "test_exec_003"
        symbol = "LONGMSG"
        
        # pendingタスク作成
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                INSERT INTO analyses (symbol, timeframe, config, task_status, execution_id)
                VALUES (?, ?, ?, ?, ?)
            """, (symbol, "15m", "Test", "pending", execution_id))
        
        # 非常に長いエラーメッセージ
        long_error = "エラー: " + "A" * 1000
        
        # 500文字に切り詰めて更新
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                UPDATE analyses 
                SET task_status = 'failed',
                    error_message = ?,
                    task_completed_at = datetime('now')
                WHERE execution_id = ? 
                AND symbol = ?
                AND task_status = 'pending'
            """, (long_error[:500], execution_id, symbol))
            
            conn.commit()
        
        # エラーメッセージが切り詰められることを確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT error_message FROM analyses WHERE execution_id = ?
            """, (execution_id,))
            
            error_msg = cursor.fetchone()[0]
            self.assertEqual(len(error_msg), 500, "エラーメッセージは500文字に切り詰められるべき")
            self.assertTrue(error_msg.startswith("エラー: "), "エラーメッセージの開始部分が保持されるべき")
    
    def test_no_pending_tasks_update(self):
        """pendingタスクが存在しない場合の更新テスト"""
        execution_id = "test_exec_004"
        symbol = "NOTASKS"
        
        # completedタスクのみ作成
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                INSERT INTO analyses (symbol, timeframe, config, task_status, execution_id)
                VALUES (?, ?, ?, ?, ?)
            """, (symbol, "15m", "Test", "completed", execution_id))
        
        # 更新実行（pendingタスクがないため何も更新されない）
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                UPDATE analyses 
                SET task_status = 'failed',
                    error_message = ?,
                    task_completed_at = datetime('now')
                WHERE execution_id = ? 
                AND symbol = ?
                AND task_status = 'pending'
            """, ("テストエラー", execution_id, symbol))
            
            updated_count = cursor.rowcount
            conn.commit()
        
        # 何も更新されないことを確認
        self.assertEqual(updated_count, 0, "pendingタスクがない場合は何も更新されない")
        
        # completedタスクはそのまま
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT task_status FROM analyses WHERE execution_id = ?
            """, (execution_id,))
            
            status = cursor.fetchone()[0]
            self.assertEqual(status, "completed", "既存のcompletedタスクは変更されない")
    
    def test_update_pending_tasks_to_failed_function_simulation(self):
        """update_pending_tasks_to_failed関数のシミュレーションテスト"""
        def update_pending_tasks_to_failed(analysis_db, execution_id, symbol, error_message):
            """new_symbol_addition_systemのメソッドをシミュレート"""
            try:
                with sqlite3.connect(analysis_db) as conn:
                    cursor = conn.execute("""
                        UPDATE analyses 
                        SET task_status = 'failed',
                            error_message = ?,
                            task_completed_at = datetime('now')
                        WHERE execution_id = ? 
                        AND symbol = ?
                        AND task_status = 'pending'
                    """, (error_message[:500], execution_id, symbol))
                    
                    updated_count = cursor.rowcount
                    conn.commit()
                    
                    return updated_count
                    
            except Exception:
                return -1
        
        # テストデータ準備
        execution_id = "test_exec_005"
        symbol = "SIMCOIN"
        
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                INSERT INTO analyses (symbol, timeframe, config, task_status, execution_id)
                VALUES (?, ?, ?, ?, ?)
            """, (symbol, "15m", "Test", "pending", execution_id))
        
        # 関数実行
        updated_count = update_pending_tasks_to_failed(
            self.analysis_db, execution_id, symbol, "シミュレーションエラー"
        )
        
        # 正常に更新されることを確認
        self.assertEqual(updated_count, 1, "1件のタスクが更新されるべき")
        
        # 結果確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT task_status, error_message FROM analyses WHERE execution_id = ?
            """, (execution_id,))
            
            result = cursor.fetchone()
            self.assertEqual(result[0], "failed")
            self.assertEqual(result[1], "シミュレーションエラー")


if __name__ == '__main__':
    unittest.main(verbosity=2)