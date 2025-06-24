#!/usr/bin/env python3
"""
execution_logs と analyses テーブル拡張マイグレーション
新銘柄追加システム対応のカラム追加
"""
import sqlite3
from pathlib import Path

def extend_execution_logs_table(db_path):
    """execution_logsテーブル拡張"""
    with sqlite3.connect(db_path) as conn:
        # 新カラム追加
        try:
            conn.execute("ALTER TABLE execution_logs ADD COLUMN selected_strategy_ids TEXT")
            print("✅ selected_strategy_ids カラム追加")
        except sqlite3.OperationalError:
            print("ℹ️ selected_strategy_ids カラムは既に存在")
        
        try:
            conn.execute("ALTER TABLE execution_logs ADD COLUMN execution_mode TEXT")
            print("✅ execution_mode カラム追加")
        except sqlite3.OperationalError:
            print("ℹ️ execution_mode カラムは既に存在")
        
        try:
            conn.execute("ALTER TABLE execution_logs ADD COLUMN estimated_patterns INTEGER")
            print("✅ estimated_patterns カラム追加")
        except sqlite3.OperationalError:
            print("ℹ️ estimated_patterns カラムは既に存在")

def extend_analyses_table(db_path):
    """analysesテーブル拡張"""
    with sqlite3.connect(db_path) as conn:
        # タスク管理カラム追加
        try:
            conn.execute("ALTER TABLE analyses ADD COLUMN task_status TEXT DEFAULT 'pending'")
            print("✅ task_status カラム追加")
        except sqlite3.OperationalError:
            print("ℹ️ task_status カラムは既に存在")
        
        try:
            conn.execute("ALTER TABLE analyses ADD COLUMN task_created_at TIMESTAMP")
            print("✅ task_created_at カラム追加")
        except sqlite3.OperationalError:
            print("ℹ️ task_created_at カラムは既に存在")
        
        try:
            conn.execute("ALTER TABLE analyses ADD COLUMN task_started_at TIMESTAMP")
            print("✅ task_started_at カラム追加")
        except sqlite3.OperationalError:
            print("ℹ️ task_started_at カラムは既に存在")
        
        try:
            conn.execute("ALTER TABLE analyses ADD COLUMN task_completed_at TIMESTAMP")
            print("✅ task_completed_at カラム追加")
        except sqlite3.OperationalError:
            print("ℹ️ task_completed_at カラムは既に存在")
        
        try:
            conn.execute("ALTER TABLE analyses ADD COLUMN error_message TEXT")
            print("✅ error_message カラム追加")
        except sqlite3.OperationalError:
            print("ℹ️ error_message カラムは既に存在")
        
        try:
            conn.execute("ALTER TABLE analyses ADD COLUMN retry_count INTEGER DEFAULT 0")
            print("✅ retry_count カラム追加")
        except sqlite3.OperationalError:
            print("ℹ️ retry_count カラムは既に存在")
        
        # 新しいインデックス作成
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_task_status ON analyses(task_status)")
            print("✅ task_status インデックス作成")
        except sqlite3.OperationalError:
            print("ℹ️ task_status インデックスは既に存在")
        
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_execution_task ON analyses(execution_id, task_status)")
            print("✅ execution_id+task_status インデックス作成")
        except sqlite3.OperationalError:
            print("ℹ️ execution_id+task_status インデックスは既に存在")

def run_migration():
    """マイグレーション実行"""
    project_root = Path(__file__).parent.parent
    execution_logs_db_path = project_root / "execution_logs.db"
    analysis_db_path = project_root / "large_scale_analysis" / "analysis.db"
    
    print("🔧 テーブル拡張マイグレーション開始")
    
    # execution_logs拡張
    print("\n📊 execution_logs テーブル拡張中...")
    print(f"対象DB: {execution_logs_db_path}")
    extend_execution_logs_table(execution_logs_db_path)
    
    # analyses拡張
    print("\n📊 analyses テーブル拡張中...")
    print(f"対象DB: {analysis_db_path}")
    extend_analyses_table(analysis_db_path)
    
    # 確認
    print("\n📋 拡張後テーブル構造確認:")
    
    # execution_logs確認
    with sqlite3.connect(execution_logs_db_path) as conn:
        cursor = conn.execute("PRAGMA table_info(execution_logs)")
        columns = [row[1] for row in cursor.fetchall()]
        new_columns = [col for col in ["selected_strategy_ids", "execution_mode", "estimated_patterns"] if col in columns]
        print(f"execution_logs 新カラム: {new_columns}")
    
    # analyses確認
    with sqlite3.connect(analysis_db_path) as conn:
        cursor = conn.execute("PRAGMA table_info(analyses)")
        columns = [row[1] for row in cursor.fetchall()]
        new_columns = [col for col in ["task_status", "task_created_at", "task_started_at", "task_completed_at", "error_message", "retry_count"] if col in columns]
        print(f"analyses 新カラム: {new_columns}")
    
    print("\n🎉 テーブル拡張マイグレーション完了")

if __name__ == "__main__":
    run_migration()