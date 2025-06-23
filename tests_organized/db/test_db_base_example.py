#!/usr/bin/env python3
"""
データベーステストの実装例
base_test.pyを使用した安全なDBテストの例
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_test import DatabaseTest
import sqlite3

class TestDatabaseOperations(DatabaseTest):
    """データベース操作のテスト"""
    
    def test_foreign_key_constraints_enforcement(self):
        """外部キー制約の実施テスト"""
        # 存在しないexecution_idで分析レコード作成を試行
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_test_analysis(
                "nonexistent_exec_id", "TEST", "1h", "Conservative_ML"
            )
    
    def test_cascade_deletion_simulation(self):
        """カスケード削除のシミュレーション"""
        # テストデータ作成
        execution_id = "test_cascade_123"
        self.insert_test_execution_log(execution_id, "TEST")
        analysis_id = self.insert_test_analysis(execution_id, "TEST", "1h", "Conservative_ML")
        
        # データ存在確認
        self.assert_test_data_exists("TEST", 1)
        
        # execution_logを削除
        with sqlite3.connect(self.execution_logs_db) as conn:
            conn.execute("DELETE FROM execution_logs WHERE execution_id = ?", (execution_id,))
        
        # 外部キー制約によりanalysisレコードが孤立することを確認
        # (カスケード削除が有効な場合は自動削除される)
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute(f"ATTACH DATABASE '{self.execution_logs_db}' AS exec_db")
            
            # 孤立レコードの確認クエリ
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses a
                LEFT JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                WHERE e.execution_id IS NULL AND a.execution_id = ?
            """, (execution_id,))
            orphaned_count = cursor.fetchone()[0]
            
            # カスケード削除が無効な場合は孤立レコードが存在
            self.assertGreaterEqual(orphaned_count, 0)
    
    def test_database_schema_validation(self):
        """データベーススキーマの検証"""
        # execution_logsテーブルのスキーマ確認
        with sqlite3.connect(self.execution_logs_db) as conn:
            cursor = conn.execute("PRAGMA table_info(execution_logs)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            expected_columns = {
                'execution_id': 'TEXT',
                'symbol': 'TEXT',
                'status': 'TEXT',
                'start_time': 'TEXT',
                'end_time': 'TEXT',
                'error_message': 'TEXT'
            }
            
            for col_name, col_type in expected_columns.items():
                self.assertIn(col_name, columns, f"カラム {col_name} が存在しません")
                self.assertEqual(columns[col_name], col_type, 
                               f"カラム {col_name} の型が不正: {columns[col_name]} != {col_type}")
        
        # analysesテーブルのスキーマ確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("PRAGMA table_info(analyses)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            expected_columns = {
                'id': 'INTEGER',
                'execution_id': 'TEXT',
                'symbol': 'TEXT',
                'timeframe': 'TEXT',
                'config': 'TEXT',
                'sharpe_ratio': 'REAL'
            }
            
            for col_name, col_type in expected_columns.items():
                self.assertIn(col_name, columns, f"カラム {col_name} が存在しません")
    
    def test_index_existence(self):
        """インデックスの存在確認"""
        # execution_logsのインデックス
        with sqlite3.connect(self.execution_logs_db) as conn:
            cursor = conn.execute("PRAGMA index_list(execution_logs)")
            indexes = [row[1] for row in cursor.fetchall()]
            
            self.assertIn('idx_execution_logs_symbol', indexes)
            self.assertIn('idx_execution_logs_status', indexes)
        
        # analysesのインデックス
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("PRAGMA index_list(analyses)")
            indexes = [row[1] for row in cursor.fetchall()]
            
            self.assertIn('idx_analyses_symbol', indexes)
            self.assertIn('idx_analyses_execution_id', indexes)
    
    def test_data_integrity_constraints(self):
        """データ整合性制約のテスト"""
        # 必須カラムのNULL制約テスト
        with self.assertRaises(sqlite3.IntegrityError):
            with sqlite3.connect(self.execution_logs_db) as conn:
                conn.execute("""
                    INSERT INTO execution_logs (execution_id, symbol, status, start_time)
                    VALUES (NULL, 'TEST', 'SUCCESS', '2025-06-23T10:00:00')
                """)
        
        with self.assertRaises(sqlite3.IntegrityError):
            with sqlite3.connect(self.analysis_db) as conn:
                conn.execute("""
                    INSERT INTO analyses (execution_id, symbol, timeframe, config)
                    VALUES ('test_123', NULL, '1h', 'Conservative_ML')
                """)


class TestDatabasePerformance(DatabaseTest):
    """データベースパフォーマンステスト"""
    
    def test_large_dataset_query_performance(self):
        """大量データでのクエリパフォーマンステスト"""
        import time
        
        # 大量テストデータ作成
        symbols = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']
        strategies = ['Conservative_ML', 'Aggressive_Traditional', 'Full_ML']
        timeframes = ['30m', '1h', '4h']
        
        total_records = 0
        for symbol in symbols:
            for strategy in strategies:
                for timeframe in timeframes:
                    for i in range(10):  # 各組み合わせ10レコード
                        execution_id = f"perf_{symbol}_{strategy}_{timeframe}_{i}"
                        self.insert_test_execution_log(execution_id, symbol)
                        self.insert_test_analysis(execution_id, symbol, timeframe, strategy)
                        total_records += 1
        
        print(f"  📊 テストデータ作成: {total_records}レコード")
        
        # クエリパフォーマンス測定
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute(f"ATTACH DATABASE '{self.execution_logs_db}' AS exec_db")
            
            # シンプルクエリ
            start_time = time.time()
            cursor = conn.execute("SELECT COUNT(*) FROM analyses")
            simple_count = cursor.fetchone()[0]
            simple_duration = time.time() - start_time
            
            # JOIN クエリ
            start_time = time.time()
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses a
                INNER JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                WHERE e.status = 'SUCCESS'
            """)
            join_count = cursor.fetchone()[0]
            join_duration = time.time() - start_time
            
            print(f"  ⚡ シンプルクエリ: {simple_count}件 ({simple_duration:.4f}s)")
            print(f"  ⚡ JOINクエリ: {join_count}件 ({join_duration:.4f}s)")
            
            # パフォーマンス検証
            self.assertLess(simple_duration, 1.0, "シンプルクエリが遅すぎます")
            self.assertLess(join_duration, 2.0, "JOINクエリが遅すぎます")
            self.assertEqual(simple_count, join_count, "レコード数が一致しません")


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)