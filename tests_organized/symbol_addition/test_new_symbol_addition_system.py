#!/usr/bin/env python3
"""
新銘柄追加システムのテストケース
統一戦略管理 + 事前タスク作成 + 詳細進捗追跡システム
"""
import unittest
import sqlite3
import json
import tempfile
import sys
import os
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))
from tests_organized.base_test import BaseTest

class NewSymbolAdditionSystemTest(BaseTest):
    """新銘柄追加システムテスト"""
    
    def custom_setup(self):
        """テスト固有のセットアップ"""
        self.test_symbol = "TEST"
        self.test_execution_id = "symbol_addition_20250623_test_abc123"
        
        # テスト用戦略設定
        self.test_strategies = [
            {
                "name": "Conservative ML - 1h",
                "base_strategy": "Conservative_ML",
                "timeframe": "1h",
                "parameters": json.dumps({"risk_multiplier": 0.8, "confidence_threshold": 0.7}),
                "description": "保守的なML戦略 1時間足",
                "is_default": True,
                "is_active": True
            },
            {
                "name": "Aggressive ML - 4h", 
                "base_strategy": "Aggressive_ML",
                "timeframe": "4h",
                "parameters": json.dumps({"risk_multiplier": 1.2, "confidence_threshold": 0.6}),
                "description": "積極的なML戦略 4時間足",
                "is_default": True,
                "is_active": True
            },
            {
                "name": "カスタム戦略テスト",
                "base_strategy": "Balanced",
                "timeframe": "30m", 
                "parameters": json.dumps({"custom_param": "test_value"}),
                "description": "テスト用カスタム戦略",
                "is_default": False,
                "is_active": True,
                "created_by": "test_user"
            }
        ]
        
        self.setup_strategy_configurations()
        self.setup_database_schema()
    
    def setup_strategy_configurations(self):
        """strategy_configurationsテーブル作成・データ投入"""
        with sqlite3.connect(self.analysis_db) as conn:
            # テーブル作成
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
            
            # テストデータ投入
            for strategy in self.test_strategies:
                conn.execute("""
                    INSERT INTO strategy_configurations 
                    (name, base_strategy, timeframe, parameters, description, is_default, is_active, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy["name"], strategy["base_strategy"], strategy["timeframe"],
                    strategy["parameters"], strategy["description"], 
                    strategy["is_default"], strategy["is_active"],
                    strategy.get("created_by", "system")
                ))
    
    def setup_database_schema(self):
        """拡張データベーススキーマ作成"""
        # execution_logs拡張
        with sqlite3.connect(self.execution_logs_db) as conn:
            try:
                conn.execute("ALTER TABLE execution_logs ADD COLUMN selected_strategy_ids TEXT")
            except sqlite3.OperationalError:
                pass  # カラムが既に存在
            try:
                conn.execute("ALTER TABLE execution_logs ADD COLUMN execution_mode TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE execution_logs ADD COLUMN estimated_patterns INTEGER")
            except sqlite3.OperationalError:
                pass
        
        # analyses拡張  
        with sqlite3.connect(self.analysis_db) as conn:
            try:
                conn.execute("ALTER TABLE analyses ADD COLUMN strategy_config_id INTEGER")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE analyses ADD COLUMN strategy_name TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE analyses ADD COLUMN task_status TEXT DEFAULT 'pending'")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE analyses ADD COLUMN task_created_at TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE analyses ADD COLUMN task_started_at TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE analyses ADD COLUMN task_completed_at TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE analyses ADD COLUMN error_message TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE analyses ADD COLUMN retry_count INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

class TestStrategyConfigurationsManagement(NewSymbolAdditionSystemTest):
    """戦略設定管理テスト"""
    
    def test_strategy_configurations_creation(self):
        """戦略設定テーブル作成・データ投入テスト"""
        with sqlite3.connect(self.analysis_db) as conn:
            # データ確認
            cursor = conn.execute("SELECT COUNT(*) FROM strategy_configurations")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 3, "3つの戦略設定が作成されている")
            
            # デフォルト戦略確認
            cursor = conn.execute("SELECT COUNT(*) FROM strategy_configurations WHERE is_default=1")
            default_count = cursor.fetchone()[0]
            self.assertEqual(default_count, 2, "2つのデフォルト戦略がある")
            
            # カスタム戦略確認
            cursor = conn.execute("SELECT name, created_by FROM strategy_configurations WHERE is_default=0")
            custom = cursor.fetchone()
            self.assertEqual(custom[0], "カスタム戦略テスト")
            self.assertEqual(custom[1], "test_user")
    
    def test_strategy_selection_query(self):
        """戦略選択クエリテスト"""
        with sqlite3.connect(self.analysis_db) as conn:
            # アクティブなデフォルト戦略取得
            cursor = conn.execute("""
                SELECT id, name, base_strategy, timeframe 
                FROM strategy_configurations 
                WHERE is_default=1 AND is_active=1
                ORDER BY base_strategy, timeframe
            """)
            default_strategies = cursor.fetchall()
            
            self.assertEqual(len(default_strategies), 2)
            self.assertEqual(default_strategies[0][1], "Aggressive ML - 4h")
            self.assertEqual(default_strategies[1][1], "Conservative ML - 1h")
    
    def test_strategy_parameters_json(self):
        """戦略パラメータJSON処理テスト"""
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT parameters FROM strategy_configurations 
                WHERE name='Conservative ML - 1h'
            """)
            params_json = cursor.fetchone()[0]
            params = json.loads(params_json)
            
            self.assertEqual(params["risk_multiplier"], 0.8)
            self.assertEqual(params["confidence_threshold"], 0.7)

class TestPreTaskCreation(NewSymbolAdditionSystemTest):
    """事前タスク作成テスト"""
    
    def test_execution_log_with_strategy_selection(self):
        """戦略選択付き実行ログ作成テスト"""
        selected_strategy_ids = [1, 2]  # Conservative ML - 1h, Aggressive ML - 4h
        
        with sqlite3.connect(self.execution_logs_db) as conn:
            conn.execute("""
                INSERT INTO execution_logs 
                (execution_id, execution_type, symbol, status, timestamp_start, selected_strategy_ids, execution_mode, estimated_patterns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.test_execution_id, "symbol_addition", self.test_symbol, "PENDING",
                datetime.now().isoformat(), json.dumps(selected_strategy_ids), "selective", len(selected_strategy_ids)
            ))
            
            # 確認
            cursor = conn.execute("""
                SELECT selected_strategy_ids, execution_mode, estimated_patterns 
                FROM execution_logs WHERE execution_id=?
            """, (self.test_execution_id,))
            result = cursor.fetchone()
            
            self.assertEqual(json.loads(result[0]), selected_strategy_ids)
            self.assertEqual(result[1], "selective")
            self.assertEqual(result[2], 2)
    
    def test_pre_task_creation(self):
        """事前タスク作成テスト"""
        selected_strategy_ids = [1, 2, 3]
        
        # 戦略情報取得
        with sqlite3.connect(self.analysis_db) as conn:
            strategies = []
            for strategy_id in selected_strategy_ids:
                cursor = conn.execute("""
                    SELECT id, name, base_strategy, timeframe 
                    FROM strategy_configurations WHERE id=?
                """, (strategy_id,))
                strategies.append(cursor.fetchone())
            
            # 事前タスク作成
            for strategy in strategies:
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, timeframe, config, strategy_config_id, strategy_name, execution_id, 
                     task_status, task_created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    self.test_symbol, strategy[3], strategy[2], strategy[0], 
                    strategy[1], self.test_execution_id, "pending"
                ))
            
            # 確認
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses 
                WHERE execution_id=? AND task_status='pending'
            """, (self.test_execution_id,))
            pending_count = cursor.fetchone()[0]
            
            self.assertEqual(pending_count, 3, "3つの事前タスクが作成された")

class TestTaskProgressTracking(NewSymbolAdditionSystemTest):
    """タスク進捗追跡テスト"""
    
    def setUp(self):
        super().setUp()
        # 事前タスクを作成
        self.create_sample_tasks()
    
    def create_sample_tasks(self):
        """サンプルタスク作成"""
        with sqlite3.connect(self.analysis_db) as conn:
            tasks = [
                (1, "Conservative ML - 1h", "pending"),
                (2, "Aggressive ML - 4h", "running"), 
                (3, "カスタム戦略テスト", "completed")
            ]
            
            for strategy_id, strategy_name, status in tasks:
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, timeframe, config, strategy_config_id, strategy_name, execution_id,
                     task_status, task_created_at, total_return, sharpe_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
                """, (
                    self.test_symbol, "1h", "test_config", strategy_id, strategy_name,
                    self.test_execution_id, status, 0.15, 1.2
                ))
    
    def test_task_status_update(self):
        """タスクステータス更新テスト"""
        with sqlite3.connect(self.analysis_db) as conn:
            # pending → running
            conn.execute("""
                UPDATE analyses SET 
                task_status='running', task_started_at=datetime('now')
                WHERE execution_id=? AND strategy_config_id=1
            """, (self.test_execution_id,))
            
            # running → completed
            conn.execute("""
                UPDATE analyses SET 
                task_status='completed', task_completed_at=datetime('now'),
                total_return=0.25, sharpe_ratio=1.8
                WHERE execution_id=? AND strategy_config_id=2
            """, (self.test_execution_id,))
            
            # 確認
            cursor = conn.execute("""
                SELECT task_status, strategy_name FROM analyses 
                WHERE execution_id=? ORDER BY strategy_config_id
            """, (self.test_execution_id,))
            results = cursor.fetchall()
            
            self.assertEqual(results[0][0], "running")   # strategy_id=1
            self.assertEqual(results[1][0], "completed") # strategy_id=2
            self.assertEqual(results[2][0], "completed") # strategy_id=3
    
    def test_progress_calculation(self):
        """進捗計算テスト"""
        with sqlite3.connect(self.analysis_db) as conn:
            # 全体進捗
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN task_status='completed' THEN 1 ELSE 0 END) as completed
                FROM analyses WHERE execution_id=?
            """, (self.test_execution_id,))
            total, completed = cursor.fetchone()
            
            progress = (completed / total) * 100 if total > 0 else 0
            self.assertEqual(total, 3)
            self.assertEqual(completed, 1)  # 初期状態で1つcompleted
            self.assertEqual(progress, 33.33333333333333)
    
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        with sqlite3.connect(self.analysis_db) as conn:
            # エラー発生をシミュレート
            error_message = "API接続エラー: タイムアウト"
            conn.execute("""
                UPDATE analyses SET 
                task_status='failed', error_message=?, retry_count=1
                WHERE execution_id=? AND strategy_config_id=1
            """, (error_message, self.test_execution_id))
            
            # 確認
            cursor = conn.execute("""
                SELECT task_status, error_message, retry_count 
                FROM analyses WHERE execution_id=? AND strategy_config_id=1
            """, (self.test_execution_id,))
            result = cursor.fetchone()
            
            self.assertEqual(result[0], "failed")
            self.assertEqual(result[1], error_message)
            self.assertEqual(result[2], 1)

class TestExecutionModeVariations(NewSymbolAdditionSystemTest):
    """実行モード別テスト"""
    
    def test_default_execution_mode(self):
        """デフォルト実行モードテスト"""
        with sqlite3.connect(self.analysis_db) as conn:
            # 全デフォルト戦略取得
            cursor = conn.execute("""
                SELECT id FROM strategy_configurations 
                WHERE is_default=1 AND is_active=1
            """)
            default_strategy_ids = [row[0] for row in cursor.fetchall()]
            
            # デフォルト実行ログ作成
            execution_id = "symbol_addition_default_test"
            with sqlite3.connect(self.execution_logs_db) as conn2:
                conn2.execute("""
                    INSERT INTO execution_logs 
                    (execution_id, execution_type, symbol, status, timestamp_start, selected_strategy_ids, execution_mode, estimated_patterns)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id, "symbol_addition", "BTC", "PENDING", 
                    datetime.now().isoformat(), json.dumps(default_strategy_ids), "default", len(default_strategy_ids)
                ))
            
            self.assertEqual(len(default_strategy_ids), 2)
    
    def test_selective_execution_mode(self):
        """選択実行モードテスト"""
        selected_ids = [1, 3]  # Conservative ML + カスタム戦略
        
        execution_id = "symbol_addition_selective_test"
        with sqlite3.connect(self.execution_logs_db) as conn:
            conn.execute("""
                INSERT INTO execution_logs 
                (execution_id, execution_type, symbol, status, timestamp_start, selected_strategy_ids, execution_mode, estimated_patterns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id, "symbol_addition", "ETH", "PENDING", 
                datetime.now().isoformat(), json.dumps(selected_ids), "selective", len(selected_ids)
            ))
            
            # 確認
            cursor = conn.execute("""
                SELECT estimated_patterns FROM execution_logs WHERE execution_id=?
            """, (execution_id,))
            patterns = cursor.fetchone()[0]
            
            self.assertEqual(patterns, 2)
    
    def test_custom_execution_mode(self):
        """カスタム実行モードテスト"""
        # カスタム戦略のみ
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT id FROM strategy_configurations 
                WHERE is_default=0 AND is_active=1
            """)
            custom_strategy_ids = [row[0] for row in cursor.fetchall()]
        
        execution_id = "symbol_addition_custom_test"
        with sqlite3.connect(self.execution_logs_db) as conn:
            conn.execute("""
                INSERT INTO execution_logs 
                (execution_id, execution_type, symbol, status, timestamp_start, selected_strategy_ids, execution_mode, estimated_patterns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id, "symbol_addition", "SOL", "PENDING", 
                datetime.now().isoformat(), json.dumps(custom_strategy_ids), "custom", len(custom_strategy_ids)
            ))
        
        self.assertEqual(len(custom_strategy_ids), 1)

if __name__ == '__main__':
    unittest.main()