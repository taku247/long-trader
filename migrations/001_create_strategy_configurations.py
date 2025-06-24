#!/usr/bin/env python3
"""
Strategy Configurations テーブル作成マイグレーション
統一戦略管理のためのテーブル作成とデフォルトデータ投入
"""
import sqlite3
import json
from pathlib import Path

def create_strategy_configurations_table(db_path):
    """strategy_configurationsテーブル作成"""
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                base_strategy TEXT NOT NULL,
                timeframe TEXT NOT NULL, 
                parameters TEXT NOT NULL,
                description TEXT,
                is_default BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_by TEXT DEFAULT 'system',
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(name, base_strategy, timeframe)
            )
        """)
        
        # インデックス作成
        conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_configs_base ON strategy_configurations(base_strategy)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_configs_timeframe ON strategy_configurations(timeframe)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_configs_active ON strategy_configurations(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_configs_default ON strategy_configurations(is_default)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_configs_name ON strategy_configurations(name)")

def insert_default_strategies(db_path):
    """デフォルト戦略設定投入"""
    default_strategies = [
        # Conservative ML 戦略
        {
            "name": "Conservative ML - 15m",
            "base_strategy": "Conservative_ML",
            "timeframe": "15m",
            "parameters": {
                "risk_multiplier": 0.7,
                "confidence_threshold": 0.8,
                "max_leverage": 10,
                "stop_loss_threshold": 0.05,
                "take_profit_threshold": 0.10
            },
            "description": "保守的なML戦略 - 15分足。低リスク・安定志向",
            "is_default": True
        },
        {
            "name": "Conservative ML - 30m", 
            "base_strategy": "Conservative_ML",
            "timeframe": "30m",
            "parameters": {
                "risk_multiplier": 0.8,
                "confidence_threshold": 0.75,
                "max_leverage": 12,
                "stop_loss_threshold": 0.06,
                "take_profit_threshold": 0.12
            },
            "description": "保守的なML戦略 - 30分足。安定性重視",
            "is_default": True
        },
        {
            "name": "Conservative ML - 1h",
            "base_strategy": "Conservative_ML", 
            "timeframe": "1h",
            "parameters": {
                "risk_multiplier": 0.9,
                "confidence_threshold": 0.7,
                "max_leverage": 15,
                "stop_loss_threshold": 0.08,
                "take_profit_threshold": 0.15
            },
            "description": "保守的なML戦略 - 1時間足。バランス重視",
            "is_default": True
        },
        {
            "name": "Conservative ML - 4h",
            "base_strategy": "Conservative_ML",
            "timeframe": "4h", 
            "parameters": {
                "risk_multiplier": 1.0,
                "confidence_threshold": 0.65,
                "max_leverage": 18,
                "stop_loss_threshold": 0.10,
                "take_profit_threshold": 0.20
            },
            "description": "保守的なML戦略 - 4時間足。中期トレンド対応",
            "is_default": True
        },
        {
            "name": "Conservative ML - 1d",
            "base_strategy": "Conservative_ML",
            "timeframe": "1d",
            "parameters": {
                "risk_multiplier": 1.1,
                "confidence_threshold": 0.6,
                "max_leverage": 20,
                "stop_loss_threshold": 0.12,
                "take_profit_threshold": 0.25
            },
            "description": "保守的なML戦略 - 日足。長期トレンド重視",
            "is_default": True
        },
        {
            "name": "Conservative ML - 1w",
            "base_strategy": "Conservative_ML",
            "timeframe": "1w",
            "parameters": {
                "risk_multiplier": 1.2,
                "confidence_threshold": 0.55,
                "max_leverage": 25,
                "stop_loss_threshold": 0.15,
                "take_profit_threshold": 0.30
            },
            "description": "保守的なML戦略 - 週足。超長期トレンド",
            "is_default": True
        },
        
        # Aggressive ML 戦略
        {
            "name": "Aggressive ML - 15m",
            "base_strategy": "Aggressive_ML",
            "timeframe": "15m",
            "parameters": {
                "risk_multiplier": 1.3,
                "confidence_threshold": 0.6,
                "max_leverage": 30,
                "stop_loss_threshold": 0.08,
                "take_profit_threshold": 0.25
            },
            "description": "積極的なML戦略 - 15分足。高リターン追求",
            "is_default": True
        },
        {
            "name": "Aggressive ML - 30m",
            "base_strategy": "Aggressive_ML", 
            "timeframe": "30m",
            "parameters": {
                "risk_multiplier": 1.4,
                "confidence_threshold": 0.55,
                "max_leverage": 35,
                "stop_loss_threshold": 0.10,
                "take_profit_threshold": 0.30
            },
            "description": "積極的なML戦略 - 30分足。攻撃的運用",
            "is_default": True
        },
        {
            "name": "Aggressive ML - 1h",
            "base_strategy": "Aggressive_ML",
            "timeframe": "1h",
            "parameters": {
                "risk_multiplier": 1.5,
                "confidence_threshold": 0.5,
                "max_leverage": 40,
                "stop_loss_threshold": 0.12,
                "take_profit_threshold": 0.35
            },
            "description": "積極的なML戦略 - 1時間足。最大リターン狙い",
            "is_default": True
        },
        {
            "name": "Aggressive ML - 4h",
            "base_strategy": "Aggressive_ML",
            "timeframe": "4h",
            "parameters": {
                "risk_multiplier": 1.6,
                "confidence_threshold": 0.45,
                "max_leverage": 45,
                "stop_loss_threshold": 0.15,
                "take_profit_threshold": 0.40
            },
            "description": "積極的なML戦略 - 4時間足。ハイリスク・ハイリターン",
            "is_default": True
        },
        {
            "name": "Aggressive ML - 1d",
            "base_strategy": "Aggressive_ML",
            "timeframe": "1d", 
            "parameters": {
                "risk_multiplier": 1.7,
                "confidence_threshold": 0.4,
                "max_leverage": 50,
                "stop_loss_threshold": 0.18,
                "take_profit_threshold": 0.45
            },
            "description": "積極的なML戦略 - 日足。大胆なポジション取り",
            "is_default": True
        },
        {
            "name": "Aggressive ML - 1w",
            "base_strategy": "Aggressive_ML",
            "timeframe": "1w",
            "parameters": {
                "risk_multiplier": 1.8,
                "confidence_threshold": 0.35,
                "max_leverage": 55,
                "stop_loss_threshold": 0.20,
                "take_profit_threshold": 0.50
            },
            "description": "積極的なML戦略 - 週足。最大攻撃性",
            "is_default": True
        },
        
        # Balanced 戦略
        {
            "name": "Balanced - 15m",
            "base_strategy": "Balanced",
            "timeframe": "15m",
            "parameters": {
                "risk_multiplier": 1.0,
                "confidence_threshold": 0.65,
                "max_leverage": 20,
                "stop_loss_threshold": 0.06,
                "take_profit_threshold": 0.15
            },
            "description": "バランス戦略 - 15分足。リスクとリターンの調和",
            "is_default": True
        },
        {
            "name": "Balanced - 30m",
            "base_strategy": "Balanced",
            "timeframe": "30m",
            "parameters": {
                "risk_multiplier": 1.1,
                "confidence_threshold": 0.6,
                "max_leverage": 25,
                "stop_loss_threshold": 0.08,
                "take_profit_threshold": 0.18
            },
            "description": "バランス戦略 - 30分足。適度なリスクテイク",
            "is_default": True
        },
        {
            "name": "Balanced - 1h",
            "base_strategy": "Balanced",
            "timeframe": "1h",
            "parameters": {
                "risk_multiplier": 1.2,
                "confidence_threshold": 0.55,
                "max_leverage": 30,
                "stop_loss_threshold": 0.10,
                "take_profit_threshold": 0.20
            },
            "description": "バランス戦略 - 1時間足。標準的な運用",
            "is_default": True
        },
        {
            "name": "Balanced - 4h",
            "base_strategy": "Balanced",
            "timeframe": "4h",
            "parameters": {
                "risk_multiplier": 1.3,
                "confidence_threshold": 0.5,
                "max_leverage": 35,
                "stop_loss_threshold": 0.12,
                "take_profit_threshold": 0.25
            },
            "description": "バランス戦略 - 4時間足。中期バランス運用",
            "is_default": True
        },
        {
            "name": "Balanced - 1d",
            "base_strategy": "Balanced",
            "timeframe": "1d",
            "parameters": {
                "risk_multiplier": 1.4,
                "confidence_threshold": 0.45,
                "max_leverage": 40,
                "stop_loss_threshold": 0.15,
                "take_profit_threshold": 0.30
            },
            "description": "バランス戦略 - 日足。長期バランス運用",
            "is_default": True
        },
        {
            "name": "Balanced - 1w", 
            "base_strategy": "Balanced",
            "timeframe": "1w",
            "parameters": {
                "risk_multiplier": 1.5,
                "confidence_threshold": 0.4,
                "max_leverage": 45,
                "stop_loss_threshold": 0.18,
                "take_profit_threshold": 0.35
            },
            "description": "バランス戦略 - 週足。超長期バランス運用",
            "is_default": True
        }
    ]
    
    with sqlite3.connect(db_path) as conn:
        for strategy in default_strategies:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO strategy_configurations 
                    (name, base_strategy, timeframe, parameters, description, is_default, is_active, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy["name"],
                    strategy["base_strategy"], 
                    strategy["timeframe"],
                    json.dumps(strategy["parameters"]),
                    strategy["description"],
                    strategy["is_default"],
                    True,  # is_active
                    "system"
                ))
            except Exception as e:
                print(f"Warning: Failed to insert strategy {strategy['name']}: {e}")

def run_migration():
    """マイグレーション実行"""
    # プロジェクトルート取得
    project_root = Path(__file__).parent.parent
    analysis_db_path = project_root / "large_scale_analysis" / "analysis.db"
    
    print("🔧 Strategy Configurations マイグレーション開始")
    print(f"📊 対象DB: {analysis_db_path}")
    
    # テーブル作成
    print("1. テーブル作成中...")
    create_strategy_configurations_table(analysis_db_path)
    print("✅ strategy_configurations テーブル作成完了")
    
    # デフォルトデータ投入
    print("2. デフォルト戦略投入中...")
    insert_default_strategies(analysis_db_path)
    
    # 確認
    with sqlite3.connect(analysis_db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM strategy_configurations")
        total_count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM strategy_configurations WHERE is_default=1")
        default_count = cursor.fetchone()[0]
        
    print(f"✅ デフォルト戦略投入完了: {default_count}個のデフォルト戦略 (総数: {total_count})")
    print("🎉 マイグレーション完了")

if __name__ == "__main__":
    run_migration()