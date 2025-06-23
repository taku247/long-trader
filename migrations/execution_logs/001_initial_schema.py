#!/usr/bin/env python3
"""
execution_logs Migration: initial_schema
Version: 1
Created: 2025-06-23 14:08:00
"""
import sqlite3
from pathlib import Path
import sys

# migration_manager をインポートするためのパス設定
sys.path.append(str(Path(__file__).parent.parent.parent))
from migration_manager import Migration


class InitialSchemaMigration(Migration):
    """
    execution_logs データベースの初期スキーマ作成
    
    既存のexecution_log_database.pyと同等のテーブル構造を作成
    """
    
    def __init__(self):
        super().__init__(
            version=1,
            name="initial_schema",
            component="execution_logs"
        )
        self.description = "Create initial execution_logs and execution_steps tables with indexes"
    
    def up(self, db_path: str) -> None:
        """マイグレーション適用"""
        with sqlite3.connect(db_path) as conn:
            # execution_logs テーブル作成
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    execution_type TEXT NOT NULL,
                    symbol TEXT,
                    symbols TEXT,  -- JSON array for multiple symbols
                    timestamp_start TEXT NOT NULL,
                    timestamp_end TEXT,
                    status TEXT NOT NULL,
                    duration_seconds REAL,
                    triggered_by TEXT,
                    server_id TEXT,
                    version TEXT,
                    current_operation TEXT,
                    progress_percentage REAL DEFAULT 0.0,
                    completed_tasks TEXT,
                    total_tasks INTEGER DEFAULT 0,
                    cpu_usage_avg REAL,
                    memory_peak_mb INTEGER,
                    disk_io_mb INTEGER,
                    metadata TEXT,  -- JSON data
                    errors TEXT,    -- JSON array of errors
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # execution_steps テーブル作成
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp_start TEXT NOT NULL,
                    timestamp_end TEXT,
                    duration_seconds REAL,
                    result_data TEXT,      -- JSON data
                    error_message TEXT,
                    error_traceback TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (execution_id) REFERENCES execution_logs(execution_id) ON DELETE CASCADE
                )
            """)
            
            # インデックス作成
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_execution_logs_symbol ON execution_logs(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_execution_logs_status ON execution_logs(status)",
                "CREATE INDEX IF NOT EXISTS idx_execution_logs_type ON execution_logs(execution_type)",
                "CREATE INDEX IF NOT EXISTS idx_execution_logs_timestamp ON execution_logs(timestamp_start)",
                "CREATE INDEX IF NOT EXISTS idx_execution_steps_execution_id ON execution_steps(execution_id)",
                "CREATE INDEX IF NOT EXISTS idx_execution_steps_status ON execution_steps(status)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            # 外部キー制約を有効化
            conn.execute("PRAGMA foreign_keys = ON")
    
    def down(self, db_path: str) -> None:
        """マイグレーション巻き戻し（オプション）"""
        with sqlite3.connect(db_path) as conn:
            # 注意: 本番では実行しない
            conn.execute("DROP TABLE IF EXISTS execution_steps")
            conn.execute("DROP TABLE IF EXISTS execution_logs")
    
    def validate(self, db_path: str) -> bool:
        """マイグレーション適用後の検証"""
        with sqlite3.connect(db_path) as conn:
            # テーブル存在確認
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('execution_logs', 'execution_steps')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if len(tables) != 2:
                return False
            
            # カラム確認（execution_logs）
            cursor = conn.execute("PRAGMA table_info(execution_logs)")
            columns = [row[1] for row in cursor.fetchall()]
            required_columns = ['execution_id', 'execution_type', 'symbol', 'status', 'timestamp_start']
            
            for col in required_columns:
                if col not in columns:
                    return False
            
            # 外部キー制約確認
            cursor = conn.execute("PRAGMA foreign_key_list(execution_steps)")
            foreign_keys = cursor.fetchall()
            
            if not foreign_keys:
                return False
            
            return True


# インスタンス作成（マイグレーションマネージャーが使用）
migration = InitialSchemaMigration()