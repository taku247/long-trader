#!/usr/bin/env python3
"""
銘柄追加統合テストスイート

今回のDOGE追加で発生した問題の統合テスト:
1. DB分散問題 (web_dashboard側DB作成)
2. Pre-task作成機能不備
3. execution_logsスキーマ不整合
4. 'config'/'strategy'キー不一致問題
5. 分析結果保存の完全なワークフロー

エンドツーエンドでの銘柄追加プロセスをテスト
"""

import unittest
import tempfile
import shutil
import os
import sys
import sqlite3
import json
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scalable_analysis_system import ScalableAnalysisSystem
from new_symbol_addition_system import NewSymbolAdditionSystem, ExecutionMode


class TestSymbolAdditionIntegration(unittest.TestCase):
    """銘柄追加統合テスト"""

    def setUp(self):
        """テスト前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.project_root = Path(self.test_dir) / "test_project"
        self.project_root.mkdir()
        
        # テスト用DBディレクトリ作成
        self.analysis_db_dir = self.project_root / "large_scale_analysis"
        self.analysis_db_dir.mkdir()
        self.analysis_db_path = self.analysis_db_dir / "analysis.db"
        
        self.execution_logs_path = self.project_root / "execution_logs.db"
        
        # テスト用DB初期化
        self._setup_test_databases()
        
        # 環境変数設定
        os.environ['TEST_MODE'] = 'true'
        self.original_cwd = os.getcwd()

    def tearDown(self):
        """テスト後清掃"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        os.environ.pop('TEST_MODE', None)

    def _setup_test_databases(self):
        """テスト用データベース初期化"""
        # analysis.db初期化
        with sqlite3.connect(self.analysis_db_path) as conn:
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
            
            cursor.execute('''
                CREATE TABLE strategy_configurations (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    base_strategy TEXT,
                    timeframe TEXT,
                    parameters TEXT,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    is_default INTEGER DEFAULT 0
                )
            ''')
            
            # テスト用戦略設定挿入
            cursor.execute('''
                INSERT INTO strategy_configurations 
                (id, name, base_strategy, timeframe, parameters, is_active, is_default)
                VALUES (1, 'Aggressive ML - 15m', 'Aggressive_ML', '15m', '{}', 1, 1)
            ''')

        # execution_logs.db初期化（selected_strategy_idsカラム含む）
        with sqlite3.connect(self.execution_logs_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
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
                    current_operation TEXT,
                    progress_percentage REAL DEFAULT 0,
                    selected_strategy_ids TEXT,
                    metadata TEXT,
                    errors TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    def test_end_to_end_symbol_addition_workflow(self):
        """エンドツーエンド銘柄追加ワークフローテスト"""
        os.chdir(self.project_root)
        
        # 1. NewSymbolAdditionSystemの初期化（正規DB使用確認）
        with patch.object(Path, '__file__', self.project_root / "new_symbol_addition_system.py"):
            addition_system = NewSymbolAdditionSystem()
        
        # 正規DBパスを参照していることを確認
        self.assertEqual(addition_system.analysis_db, self.analysis_db_path)
        self.assertEqual(addition_system.execution_logs_db, self.execution_logs_path)
        
        # 2. AutoSymbolTrainerのモック（実際の分析処理をスキップ）
        mock_auto_trainer = MagicMock()
        mock_auto_trainer.add_symbol_with_training = AsyncMock(return_value="test_execution_id")
        addition_system.auto_trainer = mock_auto_trainer
        
        # 3. 銘柄追加実行（選択モード：Aggressive ML - 15m）
        test_symbol = "TESTCOIN"
        test_execution_id = "symbol_addition_20250624_test_001"
        selected_strategy_ids = [1]  # Aggressive ML - 15m
        
        # asyncio実行
        async def run_test():
            result = await addition_system.execute_symbol_addition(
                symbol=test_symbol,
                execution_id=test_execution_id,
                execution_mode=ExecutionMode.SELECTIVE,
                selected_strategy_ids=selected_strategy_ids
            )
            return result
        
        result = asyncio.run(run_test())
        
        # 4. 結果検証
        self.assertTrue(result, "銘柄追加が成功するべき")
        
        # AutoSymbolTrainerが正しい引数で呼び出されたことを確認
        mock_auto_trainer.add_symbol_with_training.assert_called_once()
        call_args = mock_auto_trainer.add_symbol_with_training.call_args
        
        self.assertEqual(call_args.kwargs['symbol'], test_symbol)
        self.assertEqual(call_args.kwargs['execution_id'], test_execution_id)
        self.assertIsNotNone(call_args.kwargs['selected_strategies'])
        self.assertIsNotNone(call_args.kwargs['selected_timeframes'])

    def test_pre_task_creation_with_config_strategy_key_compatibility(self):
        """'config'/'strategy'キー互換性を含むPre-task作成テスト"""
        os.chdir(self.project_root)
        
        with patch.object(Path, '__file__', self.project_root / "scalable_analysis_system.py"):
            system = ScalableAnalysisSystem(str(self.analysis_db_dir))
        
        # 'strategy'キーを使用する設定（auto_symbol_training.py形式）
        batch_configs_strategy_key = [
            {'symbol': 'TEST1', 'timeframe': '15m', 'strategy': 'Aggressive_ML'},
            {'symbol': 'TEST1', 'timeframe': '1h', 'strategy': 'Conservative_ML'}
        ]
        
        # 'config'キーを使用する設定（旧形式）
        batch_configs_config_key = [
            {'symbol': 'TEST2', 'timeframe': '30m', 'config': 'Balanced'},
        ]
        
        execution_id = "test_config_strategy_compatibility"
        
        # 両方の形式でpre-task作成
        system._create_pre_tasks(batch_configs_strategy_key, execution_id)
        system._create_pre_tasks(batch_configs_config_key, execution_id)
        
        # 結果確認
        with sqlite3.connect(system.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT symbol, timeframe, config, task_status
                FROM analyses 
                WHERE execution_id = ?
                ORDER BY symbol, timeframe
            ''', (execution_id,))
            records = cursor.fetchall()
        
        # 検証：両方の形式で正しくレコード作成
        expected_records = [
            ('TEST1', '15m', 'Aggressive_ML', 'pending'),
            ('TEST1', '1h', 'Conservative_ML', 'pending'),
            ('TEST2', '30m', 'Balanced', 'pending')
        ]
        
        self.assertEqual(len(records), 3, "3件のpre-taskレコードが作成されるべき")
        for i, (symbol, timeframe, config, task_status) in enumerate(records):
            expected = expected_records[i]
            self.assertEqual((symbol, timeframe, config, task_status), expected,
                           f"レコード{i+1}が期待値と一致するべき")

    def test_execution_logs_schema_compatibility(self):
        """execution_logsスキーマ互換性テスト"""
        os.chdir(self.project_root)
        
        with patch.object(Path, '__file__', self.project_root / "new_symbol_addition_system.py"):
            addition_system = NewSymbolAdditionSystem()
        
        # execution_logsレコード作成テスト
        test_execution_id = "test_execution_logs_schema"
        test_symbol = "SCHEMATEST"
        
        # update_execution_logs_statusメソッドテスト
        from new_symbol_addition_system import ExecutionStatus
        
        success = addition_system.update_execution_logs_status(
            execution_id=test_execution_id,
            status=ExecutionStatus.RUNNING,
            current_operation="スキーマテスト実行",
            progress_percentage=50.0
        )
        
        self.assertTrue(success, "execution_logsステータス更新が成功するべき")
        
        # レコード確認
        with sqlite3.connect(addition_system.execution_logs_db) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT execution_id, status, current_operation, progress_percentage
                FROM execution_logs
                WHERE execution_id = ?
            ''', (test_execution_id,))
            result = cursor.fetchone()
        
        self.assertIsNotNone(result, "execution_logsレコードが作成されるべき")
        exec_id, status, operation, progress = result
        self.assertEqual(exec_id, test_execution_id)
        self.assertEqual(status, ExecutionStatus.RUNNING.value)
        self.assertEqual(operation, "スキーマテスト実行")
        self.assertEqual(progress, 50.0)

    def test_web_dashboard_execution_no_db_fragmentation(self):
        """web_dashboard実行時DB分散なしテスト"""
        # web_dashboardディレクトリ作成・移動
        web_dashboard_dir = self.project_root / "web_dashboard"
        web_dashboard_dir.mkdir()
        os.chdir(web_dashboard_dir)
        
        # web_dashboard内からScalableAnalysisSystem初期化
        with patch.object(Path, '__file__', self.project_root / "scalable_analysis_system.py"):
            system = ScalableAnalysisSystem("large_scale_analysis")
        
        # 1. 正規DBパスを参照していることを確認
        expected_db_path = self.project_root / "large_scale_analysis" / "analysis.db"
        self.assertEqual(system.db_path, expected_db_path,
                        "web_dashboard実行時も正規DBを参照するべき")
        
        # 2. web_dashboard内にDBが作成されていないことを確認
        web_dashboard_db_dir = web_dashboard_dir / "large_scale_analysis"
        self.assertFalse(web_dashboard_db_dir.exists(),
                        "web_dashboard内にDBディレクトリが作成されてはいけない")
        
        # 3. 実際にpre-task作成して正規DBに保存されることを確認
        batch_configs = [{'symbol': 'WEBTEST', 'timeframe': '15m', 'strategy': 'Test_Strategy'}]
        execution_id = "web_dashboard_test_execution"
        
        system._create_pre_tasks(batch_configs, execution_id)
        
        # 正規DBにレコードが作成されていることを確認
        with sqlite3.connect(expected_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT symbol, timeframe, config FROM analyses 
                WHERE execution_id = ?
            ''', (execution_id,))
            result = cursor.fetchone()
        
        self.assertIsNotNone(result, "正規DBにpre-taskレコードが作成されるべき")
        symbol, timeframe, config = result
        self.assertEqual(symbol, 'WEBTEST')
        self.assertEqual(timeframe, '15m')
        self.assertEqual(config, 'Test_Strategy')

    def test_task_status_progression_complete_workflow(self):
        """タスクステータス完全ワークフローテスト（pending→completed）"""
        os.chdir(self.project_root)
        
        with patch.object(Path, '__file__', self.project_root / "scalable_analysis_system.py"):
            system = ScalableAnalysisSystem(str(self.analysis_db_dir))
        
        # 1. Pre-task作成（pending状態）
        batch_configs = [{'symbol': 'WORKFLOW', 'timeframe': '15m', 'strategy': 'Test_ML'}]
        execution_id = "workflow_test_execution"
        
        system._create_pre_tasks(batch_configs, execution_id)
        
        # pending状態確認
        with sqlite3.connect(system.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_status, status FROM analyses 
                WHERE symbol = 'WORKFLOW' AND execution_id = ?
            ''', (execution_id,))
            result = cursor.fetchone()
        
        self.assertEqual(result[0], 'pending', "初期状態はpendingであるべき")
        self.assertEqual(result[1], 'running', "初期ステータスはrunningであるべき")
        
        # 2. タスクステータス更新（running）
        system._update_task_status('WORKFLOW', '15m', 'Test_ML', 'running')
        
        # 3. 分析結果保存（completed）
        metrics = {
            'total_trades': 150,
            'win_rate': 0.65,
            'total_return': 0.22,
            'sharpe_ratio': 2.1,
            'max_drawdown': 0.06,
            'avg_leverage': 4.0
        }
        
        system._save_to_database('WORKFLOW', '15m', 'Test_ML', metrics,
                               '/test/chart.html', '/test/data.pkl', execution_id)
        
        # 4. 最終状態確認（completed）
        with sqlite3.connect(system.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_status, status, total_trades, sharpe_ratio, task_completed_at
                FROM analyses 
                WHERE symbol = 'WORKFLOW' AND execution_id = ?
            ''', (execution_id,))
            result = cursor.fetchone()
        
        task_status, status, total_trades, sharpe_ratio, completed_at = result
        self.assertEqual(task_status, 'completed', "最終タスクステータスはcompletedであるべき")
        self.assertEqual(status, 'completed', "最終ステータスはcompletedであるべき")
        self.assertEqual(total_trades, 150, "分析結果が正しく保存されるべき")
        self.assertEqual(sharpe_ratio, 2.1, "分析結果が正しく保存されるべき")
        self.assertIsNotNone(completed_at, "完了時刻が記録されるべき")

    def test_multiple_database_operations_consistency(self):
        """複数DB操作一貫性テスト"""
        os.chdir(self.project_root)
        
        # 複数のシステムインスタンスで同一DBアクセス
        with patch.object(Path, '__file__', self.project_root / "scalable_analysis_system.py"):
            system1 = ScalableAnalysisSystem(str(self.analysis_db_dir))
            system2 = ScalableAnalysisSystem(str(self.analysis_db_dir))
        
        # system1でpre-task作成
        batch_configs = [{'symbol': 'CONSISTENCY', 'timeframe': '1h', 'strategy': 'Consistency_Test'}]
        execution_id = "consistency_test_execution"
        
        system1._create_pre_tasks(batch_configs, execution_id)
        
        # system2で同じレコードにアクセス可能か確認
        with sqlite3.connect(system2.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT symbol, task_status FROM analyses 
                WHERE execution_id = ?
            ''', (execution_id,))
            result = cursor.fetchone()
        
        self.assertIsNotNone(result, "別のシステムインスタンスからもレコードアクセス可能であるべき")
        symbol, task_status = result
        self.assertEqual(symbol, 'CONSISTENCY')
        self.assertEqual(task_status, 'pending')
        
        # system2で分析結果保存
        metrics = {'total_trades': 75, 'win_rate': 0.55, 'total_return': 0.12,
                  'sharpe_ratio': 1.3, 'max_drawdown': 0.09, 'avg_leverage': 2.5}
        
        system2._save_to_database('CONSISTENCY', '1h', 'Consistency_Test', metrics,
                                '/test/chart2.html', '/test/data2.pkl', execution_id)
        
        # system1で更新後の状態確認
        with sqlite3.connect(system1.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_status, total_trades FROM analyses 
                WHERE execution_id = ?
            ''', (execution_id,))
            result = cursor.fetchone()
        
        task_status, total_trades = result
        self.assertEqual(task_status, 'completed', "system2の更新がsystem1でも確認できるべき")
        self.assertEqual(total_trades, 75, "system2の保存データがsystem1でも確認できるべき")


if __name__ == '__main__':
    # テストスイート実行
    unittest.main(verbosity=2)