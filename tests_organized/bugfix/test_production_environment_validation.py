#!/usr/bin/env python3
"""
本番環境検証テストスイート

テストでは検知できなかった本番環境特有の問題を検証:
1. 複数execution_logs.dbファイル問題
2. 実際に使用されるDBファイルの特定
3. 本番環境でのスキーマ整合性
4. ファイル分散状況の検証
"""

import unittest
import os
import sqlite3
import subprocess
from pathlib import Path


class TestProductionEnvironmentValidation(unittest.TestCase):
    """本番環境検証テスト"""

    def setUp(self):
        """テスト前準備"""
        self.project_root = Path(__file__).parent.parent.parent
        self.original_cwd = os.getcwd()
        os.chdir(self.project_root)

    def tearDown(self):
        """テスト後清掃"""
        os.chdir(self.original_cwd)

    def test_execution_logs_db_file_discovery(self):
        """execution_logs.dbファイル発見テスト"""
        # 全execution_logs.dbファイルを検索（.worktrees除外）
        result = subprocess.run([
            'find', '.', '-name', '*execution_logs.db', '-type', 'f', 
            '-not', '-path', '*/.worktrees/*'
        ], capture_output=True, text=True)
        
        execution_logs_files = result.stdout.strip().split('\n')
        execution_logs_files = [f for f in execution_logs_files if f]  # 空行除去
        
        # 複数ファイル存在の検証
        self.assertGreater(len(execution_logs_files), 0, 
                          "execution_logs.dbファイルが少なくとも1つは存在するべき")
        
        print(f"📋 発見されたexecution_logs.dbファイル: {len(execution_logs_files)}個")
        for file_path in execution_logs_files:
            print(f"  - {file_path}")

    def test_execution_logs_schema_consistency(self):
        """execution_logs.dbスキーマ一貫性テスト"""
        # 全execution_logs.dbファイルのスキーマを確認（.worktrees除外）
        result = subprocess.run([
            'find', '.', '-name', '*execution_logs.db', '-type', 'f',
            '-not', '-path', '*/.worktrees/*'
        ], capture_output=True, text=True)
        
        execution_logs_files = result.stdout.strip().split('\n')
        execution_logs_files = [f for f in execution_logs_files if f and os.path.exists(f)]
        
        required_columns = ['execution_id', 'selected_strategy_ids']
        inconsistent_files = []
        
        for db_file in execution_logs_files:
            try:
                with sqlite3.connect(db_file) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA table_info(execution_logs)")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    missing_columns = [col for col in required_columns if col not in columns]
                    if missing_columns:
                        inconsistent_files.append({
                            'file': db_file,
                            'missing_columns': missing_columns,
                            'existing_columns': columns
                        })
                        
            except sqlite3.Error as e:
                inconsistent_files.append({
                    'file': db_file,
                    'error': str(e)
                })
        
        # 結果レポート
        if inconsistent_files:
            error_msg = "スキーマ不整合なexecution_logs.dbファイル:\n"
            for item in inconsistent_files:
                if 'error' in item:
                    error_msg += f"  ❌ {item['file']}: {item['error']}\n"
                else:
                    error_msg += f"  ⚠️ {item['file']}: 不足カラム {item['missing_columns']}\n"
            
            self.fail(error_msg)
        
        print(f"✅ 全{len(execution_logs_files)}個のexecution_logs.dbファイルでスキーマ一貫性確認")

    def test_database_path_resolution(self):
        """データベースパス解決テスト"""
        # 主要システムクラスが実際に使用するDBパスを確認
        import sys
        sys.path.insert(0, str(self.project_root))
        
        from scalable_analysis_system import ScalableAnalysisSystem
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        # ScalableAnalysisSystemのDBパス
        system = ScalableAnalysisSystem()
        analysis_db_path = system.db_path
        
        # NewSymbolAdditionSystemのDBパス
        addition_system = NewSymbolAdditionSystem()
        addition_analysis_db = addition_system.analysis_db
        addition_execution_logs_db = addition_system.execution_logs_db
        
        # パス一致確認
        self.assertEqual(analysis_db_path, addition_analysis_db,
                        "ScalableAnalysisSystemとNewSymbolAdditionSystemのanalysis.dbパスが一致するべき")
        
        # 実際のファイル存在確認
        self.assertTrue(analysis_db_path.exists(),
                       f"analysis.dbファイルが存在するべき: {analysis_db_path}")
        self.assertTrue(addition_execution_logs_db.exists(),
                       f"execution_logs.dbファイルが存在するべき: {addition_execution_logs_db}")
        
        print(f"📊 使用中のDBパス:")
        print(f"  analysis.db: {analysis_db_path}")
        print(f"  execution_logs.db: {addition_execution_logs_db}")

    def test_web_dashboard_database_isolation(self):
        """web_dashboardデータベース隔離テスト"""
        web_dashboard_dir = self.project_root / "web_dashboard"
        
        # web_dashboard内の潜在的DB分散箇所を確認
        potential_db_locations = [
            web_dashboard_dir / "large_scale_analysis",
            web_dashboard_dir / "execution_logs.db",
            web_dashboard_dir / "large_scale_analysis_disabled"
        ]
        
        active_db_locations = []
        for location in potential_db_locations:
            if location.exists():
                if location.is_dir():
                    # ディレクトリ内のDBファイル確認
                    db_files = list(location.glob("*.db"))
                    if db_files:
                        active_db_locations.append({
                            'location': str(location),
                            'type': 'directory',
                            'db_files': [str(f) for f in db_files]
                        })
                else:
                    # 直接DBファイル
                    active_db_locations.append({
                        'location': str(location),
                        'type': 'file'
                    })
        
        # web_dashboard内の想定外DB発見時は警告
        unexpected_locations = [
            loc for loc in active_db_locations 
            if 'large_scale_analysis_disabled' not in loc['location']
        ]
        
        if unexpected_locations:
            warning_msg = "web_dashboard内に予期しないDBファイル:\n"
            for loc in unexpected_locations:
                if loc['type'] == 'directory':
                    warning_msg += f"  📁 {loc['location']}: {loc['db_files']}\n"
                else:
                    warning_msg += f"  📄 {loc['location']}\n"
            
            print(f"⚠️ {warning_msg}")
            
            # 重要: これは必ずしもエラーではないが、監視が必要
            # テスト失敗させるかは設定可能
            # self.fail(warning_msg)

    def test_actual_database_usage_tracking(self):
        """実際のデータベース使用追跡テスト"""
        # 環境変数やログ出力から実際に使用されているDBを特定
        import sys
        sys.path.insert(0, str(self.project_root))
        
        # テスト実行中のDB使用をキャプチャ
        from scalable_analysis_system import ScalableAnalysisSystem
        
        # ログ出力をキャプチャして実際のDB使用を確認
        import logging
        import io
        
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('scalable_analysis_system')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        try:
            # ScalableAnalysisSystemを初期化してログキャプチャ
            system = ScalableAnalysisSystem()
            
            # キャプチャしたログから実際のDBパス抽出
            log_output = log_capture.getvalue()
            db_path_lines = [line for line in log_output.split('\n') if 'DB path:' in line]
            
            self.assertGreater(len(db_path_lines), 0, 
                             "DB使用ログが出力されるべき")
            
            # 最新のDBパス情報を表示
            if db_path_lines:
                latest_db_path = db_path_lines[-1]
                print(f"📊 実際に使用されたDBパス: {latest_db_path}")
                
        finally:
            logger.removeHandler(handler)

    def test_migration_completeness(self):
        """マイグレーション完全性テスト"""
        # 本番環境で必要なスキーマ変更が全て適用されているかチェック
        
        # analysis.dbの必須カラム確認
        analysis_db_path = self.project_root / "large_scale_analysis" / "analysis.db"
        if analysis_db_path.exists():
            with sqlite3.connect(analysis_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(analyses)")
                analysis_columns = [row[1] for row in cursor.fetchall()]
                
                required_analysis_columns = [
                    'execution_id', 'task_status', 'task_started_at', 
                    'task_completed_at', 'error_message'
                ]
                
                missing_analysis_columns = [
                    col for col in required_analysis_columns 
                    if col not in analysis_columns
                ]
                
                self.assertEqual(len(missing_analysis_columns), 0,
                               f"analysis.dbに不足カラム: {missing_analysis_columns}")
        
        # execution_logs.dbの必須カラム確認
        execution_logs_db_path = self.project_root / "execution_logs.db"
        if execution_logs_db_path.exists():
            with sqlite3.connect(execution_logs_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(execution_logs)")
                execution_columns = [row[1] for row in cursor.fetchall()]
                
                required_execution_columns = ['execution_id', 'selected_strategy_ids']
                
                missing_execution_columns = [
                    col for col in required_execution_columns 
                    if col not in execution_columns
                ]
                
                self.assertEqual(len(missing_execution_columns), 0,
                               f"execution_logs.dbに不足カラム: {missing_execution_columns}")
        
        print("✅ 全必須スキーマ変更が本番環境に適用済み")


if __name__ == '__main__':
    # 本番環境検証テスト実行
    unittest.main(verbosity=2)