#!/usr/bin/env python3
"""
Migration 002: Modify analyses table for strategy configurations

analysesテーブルに戦略設定関連カラムを追加
"""

import sqlite3
from pathlib import Path

def get_migration_info():
    """マイグレーション情報を返す"""
    return {
        'id': '002',
        'name': 'modify_analyses_table',
        'description': 'Add strategy_config_id and strategy_name columns to analyses table',
        'target_database': 'analysis',
        'created_at': '2025-06-23T15:48:30Z'
    }

def up(db_path):
    """マイグレーション実行 (アップ)"""
    print("🔄 Migration 002: analyses テーブル変更中...")
    
    with sqlite3.connect(db_path) as conn:
        # 既存のテーブル構造確認
        cursor = conn.execute("PRAGMA table_info(analyses)")
        existing_columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        print(f"  📊 既存カラム数: {len(existing_columns)}")
        
        # strategy_config_id カラム追加
        if 'strategy_config_id' not in existing_columns:
            conn.execute("ALTER TABLE analyses ADD COLUMN strategy_config_id INTEGER")
            print("  ✅ strategy_config_id カラム追加")
        else:
            print("  ℹ️ strategy_config_id カラム既存")
        
        # strategy_name カラム追加
        if 'strategy_name' not in existing_columns:
            conn.execute("ALTER TABLE analyses ADD COLUMN strategy_name TEXT")
            print("  ✅ strategy_name カラム追加")
        else:
            print("  ℹ️ strategy_name カラム既存")
        
        # インデックス追加
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_analyses_strategy_config ON analyses(strategy_config_id)",
            "CREATE INDEX IF NOT EXISTS idx_analyses_strategy_name ON analyses(strategy_name)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
            index_name = index_sql.split()[-1].split('(')[0]
            print(f"  ✅ インデックス追加: {index_name}")
        
        conn.commit()
    
    print("✅ Migration 002 完了: analyses テーブル変更成功")

def down(db_path):
    """マイグレーション取り消し (ダウン)"""
    print("🔄 Migration 002 ロールバック: analyses テーブル復元中...")
    
    with sqlite3.connect(db_path) as conn:
        # SQLiteでは ALTER TABLE DROP COLUMN がサポートされていないため、
        # テーブル再作成によるロールバック
        
        # 既存データのバックアップ
        cursor = conn.execute("PRAGMA table_info(analyses)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 新しいカラムを除外
        original_columns = [col for col in columns if col not in ['strategy_config_id', 'strategy_name']]
        
        if len(original_columns) == len(columns):
            print("  ℹ️ ロールバック不要: 新しいカラムが存在しません")
            return
        
        # バックアップテーブル作成
        columns_str = ', '.join(original_columns)
        conn.execute(f"""
            CREATE TABLE analyses_backup AS 
            SELECT {columns_str} FROM analyses
        """)
        
        # 元テーブル削除
        conn.execute("DROP TABLE analyses")
        
        # 復元（元の構造で再作成）
        conn.execute("""
            CREATE TABLE analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                config TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_trades INTEGER,
                win_rate REAL,
                total_return REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                avg_leverage REAL,
                chart_path TEXT,
                compressed_path TEXT,
                status TEXT,
                execution_id TEXT
            )
        """)
        
        # データ復元
        conn.execute(f"""
            INSERT INTO analyses ({columns_str})
            SELECT {columns_str} FROM analyses_backup
        """)
        
        # バックアップテーブル削除
        conn.execute("DROP TABLE analyses_backup")
        
        # インデックス削除
        conn.execute("DROP INDEX IF EXISTS idx_analyses_strategy_config")
        conn.execute("DROP INDEX IF EXISTS idx_analyses_strategy_name")
        
        conn.commit()
    
    print("✅ Migration 002 ロールバック完了")

def verify(db_path):
    """マイグレーション検証"""
    with sqlite3.connect(db_path) as conn:
        # テーブル存在確認
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='analyses'
        """)
        
        if not cursor.fetchone():
            return False, "analysesテーブルが存在しません"
        
        # カラム確認
        cursor = conn.execute("PRAGMA table_info(analyses)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        # 新しいカラムの存在確認
        if 'strategy_config_id' not in columns:
            return False, "strategy_config_id カラムが存在しません"
        
        if 'strategy_name' not in columns:
            return False, "strategy_name カラムが存在しません"
        
        # インデックス確認
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND tbl_name='analyses'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        
        required_indexes = [
            'idx_analyses_strategy_config',
            'idx_analyses_strategy_name'
        ]
        
        for index_name in required_indexes:
            if index_name not in indexes:
                return False, f"必須インデックス {index_name} が存在しません"
        
        return True, f"検証成功: 新しいカラム追加済み (総カラム数: {len(columns)})"

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("使用方法: python 002_modify_analyses_table.py [up|down|verify] <db_path>")
        sys.exit(1)
    
    command = sys.argv[1]
    db_path = sys.argv[2]
    
    if command == "up":
        up(db_path)
    elif command == "down":
        down(db_path)
    elif command == "verify":
        success, message = verify(db_path)
        print(f"{'✅' if success else '❌'} 検証結果: {message}")
        sys.exit(0 if success else 1)
    else:
        print("❌ 無効なコマンド。up, down, verify のいずれかを指定してください。")
        sys.exit(1)