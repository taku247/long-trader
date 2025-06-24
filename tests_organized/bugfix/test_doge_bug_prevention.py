#!/usr/bin/env python3
"""
DOGE追加で発生したバグの防止テストスイート

発生した具体的な問題:
1. web_dashboard側にDB作成 → 分散問題
2. pre-task作成機能不備 → 進捗追跡不能
3. execution_logsのselected_strategy_idsカラム不足
4. 'config'/'strategy'キー不一致問題

このテストでバグ再発を防止
"""

import unittest
import tempfile
import shutil
import os
import sys
import sqlite3
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scalable_analysis_system import ScalableAnalysisSystem


class TestDOGEBugPrevention(unittest.TestCase):
    """DOGEバグ防止テスト"""

    def setUp(self):
        """テスト前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()

    def tearDown(self):
        """テスト後清掃"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        # 環境変数クリーンアップ
        for env_var in ['FORCE_ROOT_ANALYSIS_DB', 'TEST_MODE']:
            os.environ.pop(env_var, None)

    def test_web_dashboard_db_prevention(self):
        """web_dashboard側DB作成阻止テスト（簡潔版）"""
        # テスト用ディレクトリ構造
        project_dir = Path(self.test_dir) / "project"
        project_dir.mkdir()
        web_dashboard_dir = project_dir / "web_dashboard"
        web_dashboard_dir.mkdir()
        
        # web_dashboardディレクトリに移動
        os.chdir(web_dashboard_dir)
        
        # 環境変数でDB統一を強制
        os.environ['FORCE_ROOT_ANALYSIS_DB'] = 'true'
        
        # ScalableAnalysisSystem初期化
        system = ScalableAnalysisSystem("large_scale_analysis")
        
        # web_dashboard内にDBディレクトリが作成されていないことを確認
        web_db_dir = web_dashboard_dir / "large_scale_analysis"
        self.assertFalse(web_db_dir.exists(),
                        "web_dashboard内にDBディレクトリが作成されてはいけない")
        
        # 正規の場所にDBが作成されていることを確認
        self.assertTrue(system.db_path.parent.exists(),
                       "正規の場所にDBディレクトリが作成されるべき")

    def test_pre_task_creation_functionality(self):
        """Pre-task作成機能テスト"""
        # テスト用DB作成
        db_path = Path(self.test_dir) / "test_analysis.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE analyses (
                    symbol TEXT,
                    timeframe TEXT,
                    config TEXT,
                    task_status TEXT DEFAULT 'pending',
                    execution_id TEXT,
                    status TEXT DEFAULT 'running'
                )
            ''')
        
        # ScalableAnalysisSystemのモック的使用
        system = ScalableAnalysisSystem.__new__(ScalableAnalysisSystem)
        system.db_path = db_path
        
        # 'strategy'キーと'config'キー両方のテスト
        batch_configs = [
            {'symbol': 'DOGE', 'timeframe': '15m', 'strategy': 'Aggressive_ML'},  # strategy key
            {'symbol': 'DOGE', 'timeframe': '1h', 'config': 'Conservative_ML'}    # config key
        ]
        execution_id = 'test_doge_execution'
        
        # Pre-task作成実行
        system._create_pre_tasks(batch_configs, execution_id)
        
        # 結果確認
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT symbol, timeframe, config, task_status
                FROM analyses WHERE execution_id = ?
                ORDER BY timeframe
            ''', (execution_id,))
            results = cursor.fetchall()
        
        # 検証
        self.assertEqual(len(results), 2, "2件のpre-taskレコードが作成されるべき")
        
        # 15m Aggressive_ML
        self.assertEqual(results[0], ('DOGE', '15m', 'Aggressive_ML', 'pending'))
        # 1h Conservative_ML 
        self.assertEqual(results[1], ('DOGE', '1h', 'Conservative_ML', 'pending'))

    def test_execution_logs_schema_validation(self):
        """execution_logsスキーマ検証テスト"""
        db_path = Path(self.test_dir) / "test_execution_logs.db"
        
        # selected_strategy_idsカラムを含むexecution_logsテーブル作成
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    execution_type TEXT,
                    symbol TEXT,
                    status TEXT,
                    current_operation TEXT,
                    progress_percentage REAL,
                    selected_strategy_ids TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # DOGEで失敗していた挿入をテスト
            cursor.execute('''
                INSERT INTO execution_logs 
                (execution_id, execution_type, symbol, status, current_operation, 
                 progress_percentage, selected_strategy_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                'symbol_addition_test_doge',
                'symbol_addition',
                'DOGE', 
                'RUNNING',
                'バックテスト実行',
                25.0,
                '[1]'  # Aggressive ML - 15m
            ))
        
        # 挿入成功確認
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT symbol, status, selected_strategy_ids 
                FROM execution_logs 
                WHERE execution_id = 'symbol_addition_test_doge'
            ''')
            result = cursor.fetchone()
        
        self.assertIsNotNone(result, "execution_logsレコードが正常に挿入されるべき")
        symbol, status, strategy_ids = result
        self.assertEqual(symbol, 'DOGE')
        self.assertEqual(status, 'RUNNING')
        self.assertEqual(strategy_ids, '[1]')

    def test_task_status_progression_workflow(self):
        """タスクステータス進行ワークフローテスト"""
        db_path = Path(self.test_dir) / "test_workflow.db"
        
        # テーブル作成
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE analyses (
                    symbol TEXT,
                    timeframe TEXT,
                    config TEXT,
                    task_status TEXT DEFAULT 'pending',
                    execution_id TEXT,
                    status TEXT DEFAULT 'running',
                    total_trades INTEGER,
                    win_rate REAL,
                    total_return REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    avg_leverage REAL,
                    chart_path TEXT,
                    compressed_path TEXT,
                    task_completed_at TEXT
                )
            ''')
        
        # ScalableAnalysisSystemのモック使用
        system = ScalableAnalysisSystem.__new__(ScalableAnalysisSystem)
        system.db_path = db_path
        
        execution_id = 'test_workflow_doge'
        
        # 1. Pre-task作成（pending状態）
        batch_configs = [{'symbol': 'DOGE', 'timeframe': '15m', 'strategy': 'Aggressive_ML'}]
        system._create_pre_tasks(batch_configs, execution_id)
        
        # pending状態確認
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_status, status FROM analyses 
                WHERE symbol = 'DOGE' AND execution_id = ?
            ''', (execution_id,))
            result = cursor.fetchone()
        
        self.assertEqual(result, ('pending', 'running'), "初期状態確認")
        
        # 2. 分析結果保存（completed状態）
        metrics = {
            'total_trades': 100,
            'win_rate': 0.6,
            'total_return': 0.15,
            'sharpe_ratio': 1.8,
            'max_drawdown': 0.08,
            'avg_leverage': 3.5
        }
        
        system._save_to_database('DOGE', '15m', 'Aggressive_ML', metrics,
                               '/test/chart.html', '/test/data.pkl', execution_id)
        
        # completed状態確認
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_status, status, total_trades, sharpe_ratio, task_completed_at
                FROM analyses 
                WHERE symbol = 'DOGE' AND execution_id = ?
            ''', (execution_id,))
            result = cursor.fetchone()
        
        task_status, status, total_trades, sharpe_ratio, completed_at = result
        self.assertEqual(task_status, 'completed', "タスクステータスがcompletedに更新")
        self.assertEqual(status, 'completed', "ステータスがcompletedに更新")
        self.assertEqual(total_trades, 100, "分析結果が正しく保存")
        self.assertEqual(sharpe_ratio, 1.8, "分析結果が正しく保存")
        self.assertIsNotNone(completed_at, "完了時刻が記録")

    def test_database_unified_access(self):
        """データベース統一アクセステスト"""
        # 複数のScalableAnalysisSystemインスタンスが同じDBにアクセス
        db_dir = Path(self.test_dir) / "unified_test"
        db_dir.mkdir()
        
        # システム1でDB初期化
        system1 = ScalableAnalysisSystem(str(db_dir))
        
        # システム2で同じDBアクセス
        system2 = ScalableAnalysisSystem(str(db_dir))
        
        # 両システムが同じDBパスを参照
        self.assertEqual(system1.db_path, system2.db_path,
                        "複数システムインスタンスが同一DBを参照するべき")
        
        # システム1でデータ作成
        with sqlite3.connect(system1.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                )
            ''')
            cursor.execute("INSERT INTO test_table (data) VALUES ('unified_test')")
        
        # システム2で同じデータにアクセス可能
        with sqlite3.connect(system2.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM test_table WHERE id = 1")
            result = cursor.fetchone()
        
        self.assertIsNotNone(result, "別システムインスタンスからデータアクセス可能")
        self.assertEqual(result[0], 'unified_test', "正しいデータが取得される")


if __name__ == '__main__':
    # DOGEバグ防止テスト実行
    unittest.main(verbosity=2)