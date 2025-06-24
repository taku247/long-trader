#!/usr/bin/env python3
"""
DB分散問題防止テストスイート

今回発生したバグ:
1. web_dashboard側にDB作成される問題
2. pre-task作成が機能しない問題
3. execution_logsスキーマ不整合問題
4. 複数DBで参照先が分散する問題

このテストスイートで防止・検出する。
"""

import unittest
import tempfile
import shutil
import os
import sys
import sqlite3
from pathlib import Path
import json
from unittest.mock import patch, MagicMock

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scalable_analysis_system import ScalableAnalysisSystem
from auto_symbol_training import AutoSymbolTrainer
from new_symbol_addition_system import NewSymbolAdditionSystem


class TestDBFragmentationPrevention(unittest.TestCase):
    """DB分散問題防止テスト"""

    def setUp(self):
        """テスト前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        
        # テスト用プロジェクト構造作成
        self.project_root = Path(self.test_dir) / "test_project"
        self.project_root.mkdir()
        self.web_dashboard_dir = self.project_root / "web_dashboard"
        self.web_dashboard_dir.mkdir()
        
        # テスト環境変数設定
        os.environ['TEST_MODE'] = 'true'
        os.environ.pop('FORCE_ROOT_ANALYSIS_DB', None)

    def tearDown(self):
        """テスト後清掃"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        os.environ.pop('TEST_MODE', None)
        os.environ.pop('FORCE_ROOT_ANALYSIS_DB', None)

    def test_web_dashboard_db_creation_prevention(self):
        """web_dashboard側DB作成阻止テスト"""
        # web_dashboardディレクトリに移動してScalableAnalysisSystem初期化
        os.chdir(self.web_dashboard_dir)
        
        # ScalableAnalysisSystemを初期化（環境変数で強制）
        os.environ['FORCE_ROOT_ANALYSIS_DB'] = 'true'
        try:
            system = ScalableAnalysisSystem("large_scale_analysis")
            
            # 1. web_dashboard内にDBが作成されていないことを確認
            web_dashboard_db = self.web_dashboard_dir / "large_scale_analysis"
            self.assertFalse(web_dashboard_db.exists(), 
                            "web_dashboard内にlarge_scale_analysisディレクトリが作成されてはいけない")
            
            # 2. 正規の場所（プロジェクトルート）にDBが作成されていることを確認
            expected_db_path = self.project_root / "large_scale_analysis" / "analysis.db"
            self.assertTrue(expected_db_path.parent.exists(), 
                           "正規のlarge_scale_analysisディレクトリが作成されるべき")
            
            # 3. システムのDB参照先が正規パスであることを確認
            self.assertEqual(system.db_path, expected_db_path,
                            "ScalableAnalysisSystemのDB参照先が正規パスでなければならない")
        finally:
            os.environ.pop('FORCE_ROOT_ANALYSIS_DB', None)

    def test_force_root_analysis_db_environment_variable(self):
        """FORCE_ROOT_ANALYSIS_DB環境変数テスト"""
        os.environ['FORCE_ROOT_ANALYSIS_DB'] = 'true'
        os.chdir(self.web_dashboard_dir)
        
        with patch.object(Path, '__file__', self.project_root / "scalable_analysis_system.py"):
            system = ScalableAnalysisSystem("large_scale_analysis")
        
        # 環境変数が設定されている場合は必ず正規DBを使用
        expected_db_path = self.project_root / "large_scale_analysis" / "analysis.db"
        self.assertEqual(system.db_path, expected_db_path,
                        "FORCE_ROOT_ANALYSIS_DB=trueで正規DB強制使用されるべき")

    def test_web_dashboard_path_detection_in_db_path(self):
        """DBパス内のweb_dashboard検出テスト"""
        os.chdir(self.project_root)
        
        # 意図的にweb_dashboardを含むパスを指定
        with patch.object(Path, '__file__', self.project_root / "scalable_analysis_system.py"):
            system = ScalableAnalysisSystem("web_dashboard/large_scale_analysis")
        
        # web_dashboardパスが検出され、正規パスにリダイレクトされることを確認
        expected_db_path = self.project_root / "large_scale_analysis" / "analysis.db"
        self.assertEqual(system.db_path, expected_db_path,
                        "web_dashboardパス検出時に正規DBパスにリダイレクトされるべき")


class TestPreTaskCreationFunctionality(unittest.TestCase):
    """Pre-task作成機能テスト"""

    def setUp(self):
        """テスト前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "analysis.db"
        
        # テスト用DB初期化
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    task_started_at TEXT,
                    task_completed_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    def tearDown(self):
        """テスト後清掃"""
        shutil.rmtree(self.test_dir)

    def test_pre_task_creation(self):
        """Pre-task作成機能テスト"""
        # ScalableAnalysisSystemでpre-task作成
        with patch.object(ScalableAnalysisSystem, '__init__', lambda self, *args: None):
            system = ScalableAnalysisSystem()
            system.db_path = self.db_path
            
            # テスト用設定
            batch_configs = [
                {'symbol': 'TEST', 'timeframe': '15m', 'config': 'Aggressive_ML'},
                {'symbol': 'TEST', 'timeframe': '1h', 'config': 'Conservative_ML'}
            ]
            execution_id = 'test_execution_001'
            
            # Pre-task作成実行
            system._create_pre_tasks(batch_configs, execution_id)
        
        # 作成されたpre-taskレコード確認
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT symbol, timeframe, config, task_status, execution_id, status
                FROM analyses 
                WHERE execution_id = ?
                ORDER BY timeframe
            ''', (execution_id,))
            records = cursor.fetchall()
        
        # 検証
        self.assertEqual(len(records), 2, "Pre-taskレコードが2件作成されるべき")
        
        for i, (symbol, timeframe, config, task_status, exec_id, status) in enumerate(records):
            expected_configs = ['15m', '1h']
            self.assertEqual(symbol, 'TEST')
            self.assertEqual(timeframe, expected_configs[i])
            self.assertEqual(task_status, 'pending', "初期状態はpendingであるべき")
            self.assertEqual(exec_id, execution_id)
            self.assertEqual(status, 'running')

    def test_pre_task_duplicate_prevention(self):
        """Pre-task重複作成防止テスト"""
        with patch.object(ScalableAnalysisSystem, '__init__', lambda self, *args: None):
            system = ScalableAnalysisSystem()
            system.db_path = self.db_path
            
            batch_configs = [{'symbol': 'TEST', 'timeframe': '15m', 'config': 'Aggressive_ML'}]
            execution_id = 'test_execution_002'
            
            # 1回目のpre-task作成
            system._create_pre_tasks(batch_configs, execution_id)
            
            # 2回目のpre-task作成（重複）
            system._create_pre_tasks(batch_configs, execution_id)
        
        # 重複作成されていないことを確認
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM analyses 
                WHERE symbol = 'TEST' AND execution_id = ?
            ''', (execution_id,))
            count = cursor.fetchone()[0]
        
        self.assertEqual(count, 1, "重複作成防止により1件のみであるべき")

    def test_task_status_progression(self):
        """タスクステータス進行テスト（pending→completed）"""
        with patch.object(ScalableAnalysisSystem, '__init__', lambda self, *args: None):
            system = ScalableAnalysisSystem()
            system.db_path = self.db_path
            
            # Pre-task作成
            batch_configs = [{'symbol': 'TEST', 'timeframe': '15m', 'config': 'Aggressive_ML'}]
            execution_id = 'test_execution_003'
            system._create_pre_tasks(batch_configs, execution_id)
            
            # 分析結果保存（UPDATE処理）
            metrics = {
                'total_trades': 100,
                'win_rate': 0.6,
                'total_return': 0.15,
                'sharpe_ratio': 1.8,
                'max_drawdown': 0.08,
                'avg_leverage': 3.5
            }
            
            system._save_to_database('TEST', '15m', 'Aggressive_ML', metrics, 
                                   '/test/chart.html', '/test/data.pkl', execution_id)
        
        # ステータス進行確認
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_status, status, total_trades, sharpe_ratio, task_completed_at
                FROM analyses 
                WHERE symbol = 'TEST' AND execution_id = ?
            ''', (execution_id,))
            result = cursor.fetchone()
        
        task_status, status, total_trades, sharpe_ratio, task_completed_at = result
        self.assertEqual(task_status, 'completed', "タスクステータスがcompletedに更新されるべき")
        self.assertEqual(status, 'completed', "ステータスがcompletedに更新されるべき")
        self.assertEqual(total_trades, 100, "分析結果が正しく保存されるべき")
        self.assertEqual(sharpe_ratio, 1.8, "分析結果が正しく保存されるべき")
        self.assertIsNotNone(task_completed_at, "完了時刻が記録されるべき")


class TestExecutionLogsSchemaIntegrity(unittest.TestCase):
    """execution_logsスキーマ整合性テスト"""

    def setUp(self):
        """テスト前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.execution_logs_path = Path(self.test_dir) / "execution_logs.db"

    def tearDown(self):
        """テスト後清掃"""
        shutil.rmtree(self.test_dir)

    def create_execution_logs_table(self, include_selected_strategy_ids=True):
        """execution_logsテーブル作成"""
        with sqlite3.connect(self.execution_logs_path) as conn:
            cursor = conn.cursor()
            
            selected_strategy_ids_column = ", selected_strategy_ids TEXT" if include_selected_strategy_ids else ""
            
            cursor.execute(f'''
                CREATE TABLE execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    execution_type TEXT NOT NULL,
                    symbol TEXT,
                    symbols TEXT,
                    timestamp_start TEXT NOT NULL,
                    timestamp_end TEXT,
                    status TEXT NOT NULL,
                    duration_seconds REAL,
                    triggered_by TEXT,
                    server_id TEXT,
                    version TEXT,
                    current_operation TEXT,
                    progress_percentage REAL DEFAULT 0,
                    completed_tasks TEXT,
                    total_tasks INTEGER DEFAULT 0,
                    cpu_usage_avg REAL,
                    memory_peak_mb INTEGER,
                    disk_io_mb INTEGER,
                    metadata TEXT,
                    errors TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    {selected_strategy_ids_column}
                )
            ''')

    def test_execution_logs_required_columns_exist(self):
        """execution_logs必須カラム存在確認テスト"""
        # selected_strategy_idsカラムありでテーブル作成
        self.create_execution_logs_table(include_selected_strategy_ids=True)
        
        # 必須カラムリスト
        required_columns = [
            'execution_id', 'execution_type', 'symbol', 'status',
            'timestamp_start', 'current_operation', 'progress_percentage',
            'selected_strategy_ids'  # 今回のバグで不足していたカラム
        ]
        
        # カラム存在確認
        with sqlite3.connect(self.execution_logs_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(execution_logs)")
            columns = [row[1] for row in cursor.fetchall()]
        
        for required_column in required_columns:
            self.assertIn(required_column, columns, 
                         f"必須カラム '{required_column}' が存在しない")

    def test_execution_logs_missing_column_detection(self):
        """execution_logs不足カラム検出テスト"""
        # selected_strategy_idsカラムなしでテーブル作成
        self.create_execution_logs_table(include_selected_strategy_ids=False)
        
        # カラム不足検出
        with sqlite3.connect(self.execution_logs_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(execution_logs)")
            columns = [row[1] for row in cursor.fetchall()]
        
        self.assertNotIn('selected_strategy_ids', columns, 
                        "selected_strategy_idsカラムが意図的に作成されていない")
        
        # 不足カラム追加テスト
        with sqlite3.connect(self.execution_logs_path) as conn:
            cursor = conn.cursor()
            cursor.execute("ALTER TABLE execution_logs ADD COLUMN selected_strategy_ids TEXT")
            
            # 追加後の確認
            cursor.execute("PRAGMA table_info(execution_logs)")
            columns_after = [row[1] for row in cursor.fetchall()]
        
        self.assertIn('selected_strategy_ids', columns_after,
                     "selected_strategy_idsカラムが正しく追加された")

    def test_execution_logs_insert_with_all_columns(self):
        """execution_logs全カラム挿入テスト"""
        self.create_execution_logs_table(include_selected_strategy_ids=True)
        
        # テストデータ挿入
        test_data = {
            'execution_id': 'test_exec_001',
            'execution_type': 'symbol_addition',
            'symbol': 'TEST',
            'timestamp_start': '2025-06-24T19:00:00',
            'status': 'RUNNING',
            'current_operation': 'バックテスト実行',
            'progress_percentage': 25.0,
            'selected_strategy_ids': '[1, 2, 3]'
        }
        
        with sqlite3.connect(self.execution_logs_path) as conn:
            cursor = conn.cursor()
            
            # 今回のバグで失敗していたINSERT文をテスト
            cursor.execute('''
                INSERT INTO execution_logs 
                (execution_id, execution_type, symbol, timestamp_start, status, 
                 current_operation, progress_percentage, selected_strategy_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_data['execution_id'], test_data['execution_type'], 
                test_data['symbol'], test_data['timestamp_start'],
                test_data['status'], test_data['current_operation'],
                test_data['progress_percentage'], test_data['selected_strategy_ids']
            ))
            
            # 挿入データ確認
            cursor.execute('''
                SELECT execution_id, symbol, status, selected_strategy_ids
                FROM execution_logs WHERE execution_id = ?
            ''', (test_data['execution_id'],))
            result = cursor.fetchone()
        
        self.assertIsNotNone(result, "レコードが正しく挿入されるべき")
        exec_id, symbol, status, strategy_ids = result
        self.assertEqual(exec_id, test_data['execution_id'])
        self.assertEqual(symbol, test_data['symbol'])
        self.assertEqual(status, test_data['status'])
        self.assertEqual(strategy_ids, test_data['selected_strategy_ids'])


class TestUnifiedDatabaseReference(unittest.TestCase):
    """統一DB参照テスト"""

    def setUp(self):
        """テスト前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.project_root = Path(self.test_dir) / "test_project"
        self.project_root.mkdir()
        
        # 正規DBパス
        self.correct_db_dir = self.project_root / "large_scale_analysis"
        self.correct_db_dir.mkdir()
        self.correct_db_path = self.correct_db_dir / "analysis.db"
        
        # 正規DBにテストデータ作成
        with sqlite3.connect(self.correct_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE analyses (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT,
                    test_marker TEXT
                )
            ''')
            cursor.execute('''
                INSERT INTO analyses (symbol, test_marker)
                VALUES ('UNIFIED_TEST', 'correct_db')
            ''')

    def tearDown(self):
        """テスト後清掃"""
        shutil.rmtree(self.test_dir)

    def test_scalable_analysis_system_unified_reference(self):
        """ScalableAnalysisSystem統一DB参照テスト"""
        original_cwd = os.getcwd()
        
        try:
            # プロジェクトルートから実行
            os.chdir(self.project_root)
            
            with patch.object(Path, '__file__', self.project_root / "scalable_analysis_system.py"):
                system = ScalableAnalysisSystem("large_scale_analysis")
            
            # 正規DBを参照していることを確認
            self.assertEqual(system.db_path, self.correct_db_path,
                           "ScalableAnalysisSystemが正規DBを参照するべき")
            
            # データアクセステスト
            with sqlite3.connect(system.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT test_marker FROM analyses WHERE symbol = 'UNIFIED_TEST'")
                result = cursor.fetchone()
            
            self.assertIsNotNone(result, "正規DBのデータにアクセスできるべき")
            self.assertEqual(result[0], 'correct_db', "正規DBの正しいデータを取得できるべき")
            
        finally:
            os.chdir(original_cwd)

    def test_web_dashboard_execution_unified_reference(self):
        """web_dashboard実行時統一DB参照テスト"""
        original_cwd = os.getcwd()
        
        # web_dashboardディレクトリ作成・移動
        web_dashboard_dir = self.project_root / "web_dashboard"
        web_dashboard_dir.mkdir()
        
        try:
            os.chdir(web_dashboard_dir)
            
            with patch.object(Path, '__file__', self.project_root / "scalable_analysis_system.py"):
                system = ScalableAnalysisSystem("large_scale_analysis")
            
            # web_dashboardから実行しても正規DBを参照
            self.assertEqual(system.db_path, self.correct_db_path,
                           "web_dashboard実行時も正規DBを参照するべき")
            
            # web_dashboard内にDBが作成されていないことを確認
            web_dashboard_db = web_dashboard_dir / "large_scale_analysis"
            self.assertFalse(web_dashboard_db.exists(),
                           "web_dashboard内にDBディレクトリが作成されてはいけない")
            
        finally:
            os.chdir(original_cwd)

    def test_multiple_system_instances_same_db_reference(self):
        """複数システムインスタンス同一DB参照テスト"""
        with patch.object(Path, '__file__', self.project_root / "scalable_analysis_system.py"):
            # 複数の方法でScalableAnalysisSystemを初期化
            system1 = ScalableAnalysisSystem("large_scale_analysis")
            system2 = ScalableAnalysisSystem(str(self.correct_db_dir))
            
            # 環境変数強制モード
            os.environ['FORCE_ROOT_ANALYSIS_DB'] = 'true'
            system3 = ScalableAnalysisSystem("any_path")
            
        # 全て同じDBパスを参照することを確認
        self.assertEqual(system1.db_path, self.correct_db_path)
        self.assertEqual(system2.db_path, self.correct_db_path)
        self.assertEqual(system3.db_path, self.correct_db_path)
        
        # 全インスタンスで同じデータにアクセス可能
        for i, system in enumerate([system1, system2, system3], 1):
            with sqlite3.connect(system.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM analyses WHERE test_marker = 'correct_db'")
                count = cursor.fetchone()[0]
            
            self.assertEqual(count, 1, f"システム{i}が正規DBにアクセスできるべき")


if __name__ == '__main__':
    # テストスイート実行
    unittest.main(verbosity=2)