#!/usr/bin/env python3
"""
Migration 001: Add strategy_configurations table

戦略カスタマイズ機能のためのstrategy_configurationsテーブル追加
"""

import sqlite3
from pathlib import Path
import json
from datetime import datetime, timezone
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config.defaults_manager import get_default_min_risk_reward

def get_migration_info():
    """マイグレーション情報を返す"""
    return {
        'id': '001',
        'name': 'add_strategy_configurations',
        'description': 'Add strategy_configurations table for strategy customization',
        'target_database': 'analysis',
        'created_at': '2025-06-23T15:48:00Z'
    }

def up(db_path):
    """マイグレーション実行 (アップ)"""
    print("🔄 Migration 001: strategy_configurationsテーブル作成中...")
    
    with sqlite3.connect(db_path) as conn:
        # strategy_configurations テーブル作成
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                base_strategy TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                parameters TEXT NOT NULL,
                description TEXT,
                created_by TEXT DEFAULT 'system',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0,
                
                UNIQUE(name, base_strategy, timeframe)
            )
        """)
        
        # インデックス作成
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_strategy_configs_base ON strategy_configurations(base_strategy)",
            "CREATE INDEX IF NOT EXISTS idx_strategy_configs_timeframe ON strategy_configurations(timeframe)",
            "CREATE INDEX IF NOT EXISTS idx_strategy_configs_active ON strategy_configurations(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_strategy_configs_default ON strategy_configurations(is_default)",
            "CREATE INDEX IF NOT EXISTS idx_strategy_configs_name ON strategy_configurations(name)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
        # デフォルト戦略設定の挿入
        default_strategies = [
            {
                'name': 'Conservative ML - 15m',
                'base_strategy': 'Conservative_ML',
                'timeframe': '15m',
                'parameters': json.dumps({
                    'risk_multiplier': 0.8,
                    'confidence_boost': 0.0,
                    'leverage_cap': 50,
                    'min_risk_reward': get_default_min_risk_reward(),
                    'stop_loss_percent': 3.5,
                    'take_profit_percent': 8.0,
                    'custom_sltp_calculator': 'ConservativeSLTPCalculator'
                }),
                'description': 'Conservative strategy optimized for 15m timeframe',
                'is_default': True
            },
            {
                'name': 'Conservative ML - 30m',
                'base_strategy': 'Conservative_ML',
                'timeframe': '30m',
                'parameters': json.dumps({
                    'risk_multiplier': 0.8,
                    'confidence_boost': 0.0,
                    'leverage_cap': 50,
                    'min_risk_reward': get_default_min_risk_reward(),
                    'stop_loss_percent': 4.0,
                    'take_profit_percent': 10.0,
                    'custom_sltp_calculator': 'ConservativeSLTPCalculator'
                }),
                'description': 'Conservative strategy optimized for 30m timeframe',
                'is_default': True
            },
            {
                'name': 'Conservative ML - 1h',
                'base_strategy': 'Conservative_ML',
                'timeframe': '1h',
                'parameters': json.dumps({
                    'risk_multiplier': 0.8,
                    'confidence_boost': 0.0,
                    'leverage_cap': 50,
                    'min_risk_reward': get_default_min_risk_reward(),
                    'stop_loss_percent': 5.0,
                    'take_profit_percent': 12.0,
                    'custom_sltp_calculator': 'ConservativeSLTPCalculator'
                }),
                'description': 'Conservative strategy optimized for 1h timeframe',
                'is_default': True
            },
            {
                'name': 'Aggressive ML - 15m',
                'base_strategy': 'Aggressive_ML',
                'timeframe': '15m',
                'parameters': json.dumps({
                    'risk_multiplier': 1.2,
                    'confidence_boost': -0.05,
                    'leverage_cap': 100,
                    'min_risk_reward': get_default_min_risk_reward(),
                    'stop_loss_percent': 3.5,
                    'take_profit_percent': 8.0,
                    'custom_sltp_calculator': 'AggressiveSLTPCalculator'
                }),
                'description': 'Aggressive strategy optimized for 15m timeframe',
                'is_default': True
            },
            {
                'name': 'Aggressive ML - 30m',
                'base_strategy': 'Aggressive_ML',
                'timeframe': '30m',
                'parameters': json.dumps({
                    'risk_multiplier': 1.2,
                    'confidence_boost': -0.05,
                    'leverage_cap': 100,
                    'min_risk_reward': get_default_min_risk_reward(),
                    'stop_loss_percent': 4.0,
                    'take_profit_percent': 10.0,
                    'custom_sltp_calculator': 'AggressiveSLTPCalculator'
                }),
                'description': 'Aggressive strategy optimized for 30m timeframe',
                'is_default': True
            },
            {
                'name': 'Aggressive ML - 1h',
                'base_strategy': 'Aggressive_ML',
                'timeframe': '1h',
                'parameters': json.dumps({
                    'risk_multiplier': 1.2,
                    'confidence_boost': -0.05,
                    'leverage_cap': 100,
                    'min_risk_reward': get_default_min_risk_reward(),
                    'stop_loss_percent': 5.0,
                    'take_profit_percent': 12.0,
                    'custom_sltp_calculator': 'AggressiveSLTPCalculator'
                }),
                'description': 'Aggressive strategy optimized for 1h timeframe',
                'is_default': True
            },
            {
                'name': 'Balanced - 30m',
                'base_strategy': 'Balanced',
                'timeframe': '30m',
                'parameters': json.dumps({
                    'risk_multiplier': 1.0,
                    'confidence_boost': 0.0,
                    'leverage_cap': 75,
                    'min_risk_reward': get_default_min_risk_reward(),
                    'stop_loss_percent': 4.0,
                    'take_profit_percent': 10.0,
                    'custom_sltp_calculator': 'DefaultSLTPCalculator'
                }),
                'description': 'Balanced strategy optimized for 30m timeframe',
                'is_default': True
            },
            {
                'name': 'Balanced - 1h',
                'base_strategy': 'Balanced',
                'timeframe': '1h',
                'parameters': json.dumps({
                    'risk_multiplier': 1.0,
                    'confidence_boost': 0.0,
                    'leverage_cap': 75,
                    'min_risk_reward': get_default_min_risk_reward(),
                    'stop_loss_percent': 5.0,
                    'take_profit_percent': 12.0,
                    'custom_sltp_calculator': 'DefaultSLTPCalculator'
                }),
                'description': 'Balanced strategy optimized for 1h timeframe',
                'is_default': True
            }
        ]
        
        # デフォルト戦略の挿入
        for strategy in default_strategies:
            try:
                conn.execute("""
                    INSERT INTO strategy_configurations 
                    (name, base_strategy, timeframe, parameters, description, is_default, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy['name'],
                    strategy['base_strategy'],
                    strategy['timeframe'],
                    strategy['parameters'],
                    strategy['description'],
                    strategy['is_default'],
                    'migration'
                ))
                print(f"  ✅ デフォルト戦略追加: {strategy['name']}")
            except sqlite3.IntegrityError:
                print(f"  ℹ️ デフォルト戦略既存: {strategy['name']} (スキップ)")
        
        conn.commit()
    
    print("✅ Migration 001 完了: strategy_configurationsテーブル作成成功")

def down(db_path):
    """マイグレーション取り消し (ダウン)"""
    print("🔄 Migration 001 ロールバック: strategy_configurationsテーブル削除中...")
    
    with sqlite3.connect(db_path) as conn:
        # インデックス削除
        indexes_to_drop = [
            "idx_strategy_configs_base",
            "idx_strategy_configs_timeframe", 
            "idx_strategy_configs_active",
            "idx_strategy_configs_default",
            "idx_strategy_configs_name"
        ]
        
        for index_name in indexes_to_drop:
            try:
                conn.execute(f"DROP INDEX IF EXISTS {index_name}")
            except sqlite3.Error:
                pass
        
        # テーブル削除
        conn.execute("DROP TABLE IF EXISTS strategy_configurations")
        conn.commit()
    
    print("✅ Migration 001 ロールバック完了")

def verify(db_path):
    """マイグレーション検証"""
    with sqlite3.connect(db_path) as conn:
        # テーブル存在確認
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='strategy_configurations'
        """)
        
        if not cursor.fetchone():
            return False, "strategy_configurationsテーブルが存在しません"
        
        # カラム確認
        cursor = conn.execute("PRAGMA table_info(strategy_configurations)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        required_columns = {
            'id': 'INTEGER',
            'name': 'TEXT',
            'base_strategy': 'TEXT',
            'timeframe': 'TEXT',
            'parameters': 'TEXT',
            'description': 'TEXT',
            'created_by': 'TEXT',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP',
            'is_active': 'BOOLEAN',
            'is_default': 'BOOLEAN'
        }
        
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                return False, f"必須カラム {col_name} が存在しません"
        
        # デフォルトデータ確認
        cursor = conn.execute("SELECT COUNT(*) FROM strategy_configurations WHERE is_default = 1")
        default_count = cursor.fetchone()[0]
        
        if default_count == 0:
            return False, "デフォルト戦略が存在しません"
        
        # インデックス確認
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND tbl_name='strategy_configurations'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        
        required_indexes = [
            'idx_strategy_configs_base',
            'idx_strategy_configs_timeframe',
            'idx_strategy_configs_active'
        ]
        
        for index_name in required_indexes:
            if index_name not in indexes:
                return False, f"必須インデックス {index_name} が存在しません"
        
        return True, f"検証成功: {default_count}件のデフォルト戦略を含む"

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("使用方法: python 001_add_strategy_configurations.py [up|down|verify] <db_path>")
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