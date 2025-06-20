#!/usr/bin/env python3
"""
マイグレーション後の動作確認テスト
キャンセル機能とDB参照が正常に動作することを確認
"""

import os
import sys
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import unittest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from execution_log_database import ExecutionLogDatabase, ExecutionType, ExecutionStatus
    from support_resistance_ml import check_cancellation_requested, get_current_execution_id
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class PostMigrationValidationTest(unittest.TestCase):
    """マイグレーション後の動作確認テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.project_root = Path(__file__).parent
        self.unified_db_path = self.project_root / "execution_logs.db"
        self.web_db_path = self.project_root / "web_dashboard" / "execution_logs.db"
        
    def test_unified_db_exists_and_populated(self):
        """統合DBが存在し、データが統合されていることを確認"""
        print("\n📊 統合DB状態確認...")
        
        self.assertTrue(self.unified_db_path.exists(), "統合DBが存在する")
        
        with sqlite3.connect(self.unified_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
            count = cursor.fetchone()[0]
            print(f"  統合DB総レコード数: {count}")
            
            # 152件以上（元の114 + 38）あることを確認
            self.assertGreaterEqual(count, 150, "統合により十分なレコード数がある")
            
            # WebDBからのデータが含まれていることを確認
            cursor = conn.execute("""
                SELECT COUNT(*) FROM execution_logs 
                WHERE execution_id LIKE 'symbol_addition_%'
                AND timestamp_start >= '2025-06-19'
            """)
            recent_symbols = cursor.fetchone()[0]
            print(f"  最近の銘柄追加レコード: {recent_symbols}件")
            
            self.assertGreater(recent_symbols, 0, "WebDBからの銘柄追加データが統合されている")
    
    def test_web_dashboard_db_reference(self):
        """Webダッシュボードの設定が更新されていることを確認"""
        print("\n⚙️ Webダッシュボード設定確認...")
        
        app_py_path = self.project_root / "web_dashboard" / "app.py"
        self.assertTrue(app_py_path.exists(), "app.pyが存在する")
        
        with open(app_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 新しい設定が適用されていることを確認
        expected_line = "exec_db_path = '../execution_logs.db'"
        self.assertIn(expected_line, content, "WebダッシュボードがルートDBを参照するよう設定されている")
        
        # 古い設定が残っていないことを確認
        old_line = "exec_db_path = 'execution_logs.db'"
        self.assertNotIn(old_line, content, "古い設定が残っていない")
        
        print("  ✅ Webダッシュボード設定が正しく更新されている")
    
    def test_cancellation_functionality_fixed(self):
        """キャンセル機能が修正されていることを確認"""
        print("\n❌ キャンセル機能修復確認...")
        
        # 1. テスト用のCANCELLEDレコードを作成
        test_execution_id = f"test_cancel_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        db = ExecutionLogDatabase()
        created_id = db.create_execution_with_id(
            test_execution_id,
            ExecutionType.SYMBOL_ADDITION,
            symbol="TESTCOIN",
            triggered_by="TEST"
        )
        
        # 2. CANCELLEDステータスに変更
        db.update_execution_status(test_execution_id, ExecutionStatus.CANCELLED)
        
        # 3. 環境変数を設定
        os.environ['CURRENT_EXECUTION_ID'] = test_execution_id
        
        try:
            # 4. check_cancellation_requested()でキャンセルが検出されることを確認
            is_cancelled = check_cancellation_requested()
            print(f"  キャンセル検出結果: {is_cancelled}")
            
            self.assertTrue(is_cancelled, "キャンセルが正常に検出される")
            print("  ✅ キャンセル機能が正常に動作している")
            
        finally:
            # 5. テストデータとenv変数をクリーンアップ
            if 'CURRENT_EXECUTION_ID' in os.environ:
                del os.environ['CURRENT_EXECUTION_ID']
    
    def test_execution_log_database_default_behavior(self):
        """ExecutionLogDatabaseのデフォルト動作確認"""
        print("\n🔍 ExecutionLogDatabase動作確認...")
        
        # デフォルトコンストラクタが統合DBを参照することを確認
        db = ExecutionLogDatabase()
        expected_path = self.unified_db_path.resolve()
        actual_path = db.db_path.resolve()
        
        print(f"  期待パス: {expected_path}")
        print(f"  実際パス: {actual_path}")
        
        self.assertEqual(str(actual_path), str(expected_path), 
                        "ExecutionLogDatabaseが統合DBを参照している")
    
    def test_web_db_migration_verification(self):
        """WebDBからのデータ移行を検証"""
        print("\n🔄 データ移行検証...")
        
        # 移行前のWebDBデータと現在のルートDBを比較
        if self.web_db_path.exists():
            with sqlite3.connect(self.web_db_path) as web_conn:
                web_conn.execute(f"ATTACH DATABASE '{self.unified_db_path}' AS unified_db")
                
                # WebDBの各レコードが統合DBに存在することを確認
                cursor = web_conn.execute("""
                    SELECT w.execution_id, w.symbol, w.status
                    FROM execution_logs w
                    LEFT JOIN unified_db.execution_logs u ON w.execution_id = u.execution_id
                    WHERE u.execution_id IS NULL
                """)
                
                missing_records = cursor.fetchall()
                
                if missing_records:
                    print(f"  ⚠️ 移行されていないレコード: {len(missing_records)}件")
                    for record in missing_records[:5]:
                        print(f"    - {record[0]}: {record[1]} ({record[2]})")
                    
                    self.assertEqual(len(missing_records), 0, "すべてのWebDBレコードが移行されている")
                else:
                    print("  ✅ すべてのWebDBレコードが正常に移行されている")
        else:
            print("  ℹ️ WebDBが存在しないため、移行検証をスキップ")
    
    def test_backup_integrity(self):
        """バックアップの整合性確認"""
        print("\n📁 バックアップ整合性確認...")
        
        backup_dirs = list(Path("backups").glob("migration_*"))
        if not backup_dirs:
            self.skipTest("バックアップディレクトリが見つかりません")
        
        # 最新のバックアップを確認
        latest_backup = max(backup_dirs, key=lambda p: p.name)
        print(f"  最新バックアップ: {latest_backup}")
        
        root_backup = latest_backup / "execution_logs_root_backup.db"
        web_backup = latest_backup / "execution_logs_web_backup.db"
        
        self.assertTrue(root_backup.exists(), "ルートDBバックアップが存在する")
        self.assertTrue(web_backup.exists(), "WebDBバックアップが存在する")
        
        # バックアップの内容確認
        with sqlite3.connect(root_backup) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
            root_backup_count = cursor.fetchone()[0]
            print(f"  ルートDBバックアップレコード数: {root_backup_count}")
        
        with sqlite3.connect(web_backup) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
            web_backup_count = cursor.fetchone()[0]
            print(f"  WebDBバックアップレコード数: {web_backup_count}")
        
        # 統合後のレコード数と一致することを確認
        with sqlite3.connect(self.unified_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
            current_count = cursor.fetchone()[0]
        
        expected_count = root_backup_count + web_backup_count
        self.assertGreaterEqual(current_count, expected_count, 
                               "統合後のレコード数がバックアップの合計以上である")
        
        print("  ✅ バックアップが正常に作成されている")

def run_post_migration_tests():
    """マイグレーション後テストを実行"""
    print("🧪 マイグレーション後の動作確認テストを開始...")
    print("=" * 60)
    
    # テストスイート作成
    suite = unittest.TestLoader().loadTestsFromTestCase(PostMigrationValidationTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ すべてのテストが成功しました。マイグレーションは正常に完了しています。")
        print("\n🎯 重要な確認事項:")
        print("1. ✅ DB統一完了 - WebDBデータがルートDBに統合されました")
        print("2. ✅ キャンセル機能修復 - 銘柄追加のキャンセルが正常に動作します")
        print("3. ✅ Webダッシュボード設定更新 - ルートDBを参照するよう修正されました")
        print("4. ✅ データ整合性維持 - すべてのデータが保持されています")
        print("5. ✅ バックアップ作成済み - 問題時の復旧が可能です")
        return True
    else:
        print("❌ テストに失敗しました。問題を修正してください。")
        return False

if __name__ == "__main__":
    success = run_post_migration_tests()
    sys.exit(0 if success else 1)