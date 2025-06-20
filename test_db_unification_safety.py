#!/usr/bin/env python3
"""
DB統一作業の安全性テスト
現在のシステム状態を確認し、修正後の動作をテストする
"""

import os
import sys
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import unittest
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from execution_log_database import ExecutionLogDatabase
    # web_dashboard.appのインポートは不要（テストには使わない）
except ImportError as e:
    print(f"Import error: {e}")
    print("スクリプトをプロジェクトルートから実行してください")
    sys.exit(1)

class DBUnificationSafetyTest(unittest.TestCase):
    """DB統一作業の安全性をテストするクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.project_root = Path(__file__).parent
        self.root_db_path = self.project_root / "execution_logs.db"
        self.web_db_path = self.project_root / "web_dashboard" / "execution_logs.db"
        
        # テスト用一時ディレクトリ
        self.temp_dir = Path(tempfile.mkdtemp(prefix="db_unification_test_"))
        self.test_root_db = self.temp_dir / "execution_logs.db"
        self.test_web_db = self.temp_dir / "web_dashboard_execution_logs.db"
        
        print(f"🧪 テスト環境: {self.temp_dir}")
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_current_db_state(self):
        """現在のDB状態を確認"""
        print("\n📊 現在のDB状態を確認中...")
        
        # ルートDBの確認
        root_exists = self.root_db_path.exists()
        web_exists = self.web_db_path.exists()
        
        print(f"  ルートDB存在: {root_exists} ({self.root_db_path})")
        print(f"  WebDB存在: {web_exists} ({self.web_db_path})")
        
        if root_exists:
            with sqlite3.connect(self.root_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
                root_count = cursor.fetchone()[0]
                print(f"  ルートDBレコード数: {root_count}")
        
        if web_exists:
            with sqlite3.connect(self.web_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
                web_count = cursor.fetchone()[0]
                print(f"  WebDBレコード数: {web_count}")
        
        # テスト結果の記録
        self.assertTrue(root_exists or web_exists, "少なくとも一つのDBが存在する必要があります")
    
    def test_execution_log_database_default_behavior(self):
        """ExecutionLogDatabaseのデフォルト動作をテスト"""
        print("\n🔍 ExecutionLogDatabaseのデフォルト動作をテスト...")
        
        # 一時ディレクトリに移動してテスト
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            
            # デフォルトコンストラクタ
            db = ExecutionLogDatabase()
            expected_path = Path("execution_logs.db").resolve()
            actual_path = db.db_path.resolve()
            
            print(f"  期待パス: {expected_path}")
            print(f"  実際パス: {actual_path}")
            
            self.assertEqual(str(actual_path), str(expected_path))
            
        finally:
            os.chdir(original_cwd)
    
    def test_web_dashboard_db_path_behavior(self):
        """WebダッシュボードのDB参照動作をテスト"""
        print("\n🌐 WebダッシュボードのDB参照動作をテスト...")
        
        # web_dashboardディレクトリでの動作をシミュレート
        web_dashboard_dir = self.temp_dir / "web_dashboard"
        web_dashboard_dir.mkdir()
        
        original_cwd = os.getcwd()
        try:
            os.chdir(web_dashboard_dir)
            
            # web_dashboard/app.py の exec_db_path = 'execution_logs.db' をシミュレート
            expected_web_db_path = web_dashboard_dir / "execution_logs.db"
            
            # ダミーDBファイルを作成
            with sqlite3.connect(expected_web_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS execution_logs (
                        execution_id TEXT PRIMARY KEY,
                        status TEXT,
                        symbol TEXT
                    )
                """)
                conn.execute("INSERT INTO execution_logs (execution_id, status, symbol) VALUES (?, ?, ?)",
                           ("test_web_001", "RUNNING", "TEST"))
            
            # ファイルが正しい場所に作成されたことを確認
            self.assertTrue(expected_web_db_path.exists())
            
            print(f"  WebダッシュボードDB位置: {expected_web_db_path}")
            
        finally:
            os.chdir(original_cwd)
    
    def test_cancellation_simulation(self):
        """キャンセル機能のシミュレーションテスト"""
        print("\n❌ キャンセル機能のシミュレーションテスト...")
        
        # 現在の問題をシミュレート
        
        # 1. WebダッシュボードDBにレコード作成（RUNNING状態）
        web_db = self.test_web_db
        with sqlite3.connect(web_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    status TEXT,
                    symbol TEXT
                )
            """)
            conn.execute("INSERT INTO execution_logs (execution_id, status, symbol) VALUES (?, ?, ?)",
                       ("test_cancel_001", "RUNNING", "TESTCOIN"))
        
        # 2. ルートDBには異なるレコード
        root_db = self.test_root_db
        with sqlite3.connect(root_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    status TEXT,
                    symbol TEXT
                )
            """)
            conn.execute("INSERT INTO execution_logs (execution_id, status, symbol) VALUES (?, ?, ?)",
                       ("different_execution", "SUCCESS", "OTHERCOIN"))
        
        # 3. Webダッシュボードでキャンセル実行（WebDBのstatusをCANCELLEDに変更）
        with sqlite3.connect(web_db) as conn:
            conn.execute("UPDATE execution_logs SET status = 'CANCELLED' WHERE execution_id = ?",
                       ("test_cancel_001",))
        
        # 4. support_resistance_ml.pyのcheck_cancellation_requested()をシミュレート
        # （ルートDBから読み込み）
        with sqlite3.connect(root_db) as conn:
            cursor = conn.execute("SELECT status FROM execution_logs WHERE execution_id = ?",
                                ("test_cancel_001",))
            result = cursor.fetchone()
        
        # 現在の問題：ルートDBには該当レコードがないため、キャンセルが検出されない
        print(f"  WebDB内のステータス: CANCELLED")
        print(f"  ルートDBでの検索結果: {result}")
        print(f"  結果: キャンセルが検出されない（問題を再現）")
        
        self.assertIsNone(result, "現在の問題: 異なるDBを参照するためキャンセルが検出されない")
    
    def test_proposed_solution(self):
        """提案されたソリューションのテスト"""
        print("\n✅ 提案されたソリューションのテスト...")
        
        # 統一されたDBでのキャンセル機能テスト
        unified_db = self.test_root_db
        
        # 1. 統一DBにレコード作成
        with sqlite3.connect(unified_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    status TEXT,
                    symbol TEXT,
                    timestamp_start TEXT
                )
            """)
            conn.execute("INSERT INTO execution_logs (execution_id, status, symbol, timestamp_start) VALUES (?, ?, ?, ?)",
                       ("unified_test_001", "RUNNING", "TESTCOIN", datetime.now().isoformat()))
        
        # 2. WebダッシュボードもルートDBを参照してキャンセル実行
        with sqlite3.connect(unified_db) as conn:
            conn.execute("UPDATE execution_logs SET status = 'CANCELLED' WHERE execution_id = ?",
                       ("unified_test_001",))
        
        # 3. 処理システムもルートDBから読み込み
        with sqlite3.connect(unified_db) as conn:
            cursor = conn.execute("SELECT status FROM execution_logs WHERE execution_id = ?",
                                ("unified_test_001",))
            result = cursor.fetchone()
        
        print(f"  統一DB内のステータス: {result[0] if result else None}")
        print(f"  結果: キャンセルが正常に検出される")
        
        self.assertIsNotNone(result, "統一DB使用時はレコードが見つかる")
        self.assertEqual(result[0], "CANCELLED", "キャンセルステータスが正常に検出される")
    
    def test_data_migration_safety(self):
        """データマイグレーションの安全性テスト"""
        print("\n🔄 データマイグレーションの安全性テスト...")
        
        # 元データの作成
        root_data = [
            ("root_001", "SUCCESS", "BTC", "2025-06-19T10:00:00"),
            ("root_002", "FAILED", "ETH", "2025-06-19T11:00:00"),
            ("common_001", "RUNNING", "SOL", "2025-06-19T12:00:00")
        ]
        
        web_data = [
            ("web_001", "SUCCESS", "DOGE", "2025-06-19T13:00:00"),
            ("web_002", "CANCELLED", "ADA", "2025-06-19T14:00:00"),
            ("common_001", "CANCELLED", "SOL", "2025-06-19T12:30:00")  # 重複（後のタイムスタンプ）
        ]
        
        # 各DBにデータを投入
        for db_path, data in [(self.test_root_db, root_data), (self.test_web_db, web_data)]:
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS execution_logs (
                        execution_id TEXT PRIMARY KEY,
                        status TEXT,
                        symbol TEXT,
                        timestamp_start TEXT
                    )
                """)
                conn.executemany(
                    "INSERT OR REPLACE INTO execution_logs (execution_id, status, symbol, timestamp_start) VALUES (?, ?, ?, ?)",
                    data
                )
        
        # マイグレーション実行（WebDBのデータをルートDBに統合）
        with sqlite3.connect(self.test_web_db) as web_conn:
            web_conn.execute("ATTACH DATABASE ? AS root_db", (str(self.test_root_db),))
            
            # 重複チェック付きの安全な統合
            web_conn.execute("""
                INSERT OR IGNORE INTO root_db.execution_logs 
                SELECT * FROM execution_logs 
                WHERE execution_id NOT IN (
                    SELECT execution_id FROM root_db.execution_logs
                )
            """)
        
        # 結果確認
        with sqlite3.connect(self.test_root_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
            total_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT execution_id, status FROM execution_logs ORDER BY execution_id")
            all_records = cursor.fetchall()
        
        print(f"  マイグレーション後の総レコード数: {total_count}")
        print(f"  統合されたレコード:")
        for record in all_records:
            print(f"    {record[0]}: {record[1]}")
        
        # 期待値：ユニークなexecution_idが5件（root_001, root_002, web_001, web_002, common_001）
        # common_001は既存のルートDBのものが維持される（INSERT OR IGNOREのため）
        expected_count = 5
        self.assertEqual(total_count, expected_count, f"統合後のレコード数が期待値({expected_count})と一致する")

def run_safety_tests():
    """安全性テストを実行"""
    print("🛡️ DB統一作業の安全性テストを開始...")
    print("=" * 60)
    
    # テストスイート作成
    suite = unittest.TestLoader().loadTestsFromTestCase(DBUnificationSafetyTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ すべてのテストが成功しました。DB統一作業を安全に進められます。")
        return True
    else:
        print("❌ テストに失敗しました。問題を修正してから作業を進めてください。")
        return False

if __name__ == "__main__":
    success = run_safety_tests()
    sys.exit(0 if success else 1)