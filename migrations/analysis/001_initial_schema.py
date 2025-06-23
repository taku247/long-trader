#!/usr/bin/env python3
"""
analysis Migration: initial_schema
Version: 1
Created: 2025-06-23 14:10:00
"""
import sqlite3
from pathlib import Path
import sys

# migration_manager をインポートするためのパス設定
sys.path.append(str(Path(__file__).parent.parent.parent))
from migration_manager import Migration


class InitialSchemaMigration(Migration):
    """
    analysis データベースの初期スキーマ作成
    
    analyses, backtest_summary, leverage_calculation_details テーブルを作成
    """
    
    def __init__(self):
        super().__init__(
            version=1,
            name="initial_schema",
            component="analysis"
        )
        self.description = "Create initial analysis database tables with foreign key relationships"
    
    def up(self, db_path: str) -> None:
        """マイグレーション適用"""
        with sqlite3.connect(db_path) as conn:
            # analyses テーブル作成
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # backtest_summary テーブル作成
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
                )
            """)
            
            # leverage_calculation_details テーブル作成
            conn.execute("""
                CREATE TABLE IF NOT EXISTS leverage_calculation_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    trade_number INTEGER NOT NULL,
                    support_distance_pct REAL,
                    support_constraint_leverage REAL,
                    risk_reward_ratio REAL,
                    risk_reward_constraint_leverage REAL,
                    confidence_pct REAL,
                    confidence_constraint_leverage REAL,
                    btc_correlation REAL,
                    btc_constraint_leverage REAL,
                    volatility_pct REAL,
                    volatility_constraint_leverage REAL,
                    trend_strength TEXT,
                    trend_multiplier REAL,
                    min_constraint_leverage REAL,
                    safety_margin_pct REAL,
                    final_leverage REAL,
                    calculation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
                )
            """)
            
            # インデックス作成
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_analyses_execution_id ON analyses(execution_id)",
                "CREATE INDEX IF NOT EXISTS idx_analyses_symbol ON analyses(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_analyses_generated_at ON analyses(generated_at)",
                "CREATE INDEX IF NOT EXISTS idx_analyses_config ON analyses(config)",
                "CREATE INDEX IF NOT EXISTS idx_analyses_sharpe_ratio ON analyses(sharpe_ratio)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_analysis ON backtest_summary(analysis_id)",
                "CREATE INDEX IF NOT EXISTS idx_leverage_analysis ON leverage_calculation_details(analysis_id)",
                "CREATE INDEX IF NOT EXISTS idx_leverage_trade ON leverage_calculation_details(analysis_id, trade_number)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            # 外部キー制約を有効化
            conn.execute("PRAGMA foreign_keys = ON")
    
    def down(self, db_path: str) -> None:
        """マイグレーション巻き戻し（オプション）"""
        with sqlite3.connect(db_path) as conn:
            # 注意: 本番では実行しない
            conn.execute("DROP TABLE IF EXISTS leverage_calculation_details")
            conn.execute("DROP TABLE IF EXISTS backtest_summary")
            conn.execute("DROP TABLE IF EXISTS analyses")
    
    def validate(self, db_path: str) -> bool:
        """マイグレーション適用後の検証"""
        with sqlite3.connect(db_path) as conn:
            # テーブル存在確認
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('analyses', 'backtest_summary', 'leverage_calculation_details')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if len(tables) != 3:
                return False
            
            # analyses テーブルのカラム確認
            cursor = conn.execute("PRAGMA table_info(analyses)")
            columns = [row[1] for row in cursor.fetchall()]
            required_columns = ['id', 'execution_id', 'symbol', 'timeframe', 'config', 'compressed_path']
            
            for col in required_columns:
                if col not in columns:
                    return False
            
            # 外部キー制約確認
            cursor = conn.execute("PRAGMA foreign_key_list(backtest_summary)")
            foreign_keys = cursor.fetchall()
            
            if not foreign_keys:
                return False
            
            return True


# インスタンス作成（マイグレーションマネージャーが使用）
migration = InitialSchemaMigration()