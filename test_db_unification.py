#!/usr/bin/env python3
"""
DB統一テストスイート - テスト駆動でDBファイル参照先統一を検証
"""

import os
import sys
import sqlite3
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

class DbUnificationTest:
    """DB統一テストクラス"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dirs = []
        
    def setup_test_environment(self):
        """テスト環境のセットアップ"""
        print("🔧 DB統一テスト環境セットアップ中...")
        
        # テスト用一時ディレクトリ作成
        self.temp_dir = Path(tempfile.mkdtemp(prefix="db_unification_test_"))
        self.temp_dirs.append(self.temp_dir)
        
        # テスト用DB作成
        self.test_root_db = self.temp_dir / "execution_logs.db"
        self.test_web_db = self.temp_dir / "web_dashboard" / "execution_logs.db"
        
        # web_dashboardディレクトリ作成
        (self.temp_dir / "web_dashboard").mkdir()
        
        # 実際のDBスキーマをコピー
        self._create_test_databases()
        
        print(f"✅ テスト環境: {self.temp_dir}")
        
    def _create_test_databases(self):
        """テスト用データベースを作成"""
        # ルートDBの作成（実際のスキーマに合わせる）
        with sqlite3.connect(self.test_root_db) as conn:
            conn.execute("""
                CREATE TABLE execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    execution_type TEXT NOT NULL,
                    symbol TEXT,
                    symbols TEXT,  -- JSON array
                    timestamp_start TEXT NOT NULL,
                    timestamp_end TEXT,
                    status TEXT NOT NULL,
                    duration_seconds REAL,
                    triggered_by TEXT,
                    server_id TEXT,
                    version TEXT,
                    
                    -- 進捗情報
                    current_operation TEXT,
                    progress_percentage REAL DEFAULT 0,
                    completed_tasks TEXT,  -- JSON array
                    total_tasks INTEGER DEFAULT 0,
                    
                    -- リソース使用状況
                    cpu_usage_avg REAL,
                    memory_peak_mb INTEGER,
                    disk_io_mb INTEGER,
                    
                    -- メタデータ
                    metadata TEXT,  -- JSON
                    
                    -- エラー情報
                    errors TEXT,  -- JSON array
                    
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # テストデータ挿入（アクティブなRUNNINGプロセス含む）
            test_data = [
                ("root_exec_001", "SYMBOL_ADDITION", "BTC", None, "2025-06-21T10:00:00", None, "RUNNING", None, "TEST", None, None, None, 0, "[]", 0, None, None, None, None, "[]"),
                ("root_exec_002", "SYMBOL_ADDITION", "ETH", None, "2025-06-21T09:00:00", None, "SUCCESS", None, "TEST", None, None, None, 0, "[]", 0, None, None, None, None, "[]"),
                ("root_exec_003", "SYMBOL_ADDITION", "SOL", None, "2025-06-21T08:00:00", None, "SUCCESS", None, "TEST", None, None, None, 0, "[]", 0, None, None, None, None, "[]"),
            ]
            
            for data in test_data:
                conn.execute("""
                    INSERT INTO execution_logs 
                    (execution_id, execution_type, symbol, symbols, timestamp_start, timestamp_end, status, 
                     duration_seconds, triggered_by, server_id, version, current_operation, progress_percentage, 
                     completed_tasks, total_tasks, cpu_usage_avg, memory_peak_mb, disk_io_mb, metadata, errors)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
            conn.commit()
        
        # WebダッシュボードDBの作成（同じスキーマ）
        with sqlite3.connect(self.test_web_db) as conn:
            conn.execute("""
                CREATE TABLE execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    execution_type TEXT NOT NULL,
                    symbol TEXT,
                    symbols TEXT,  -- JSON array
                    timestamp_start TEXT NOT NULL,
                    timestamp_end TEXT,
                    status TEXT NOT NULL,
                    duration_seconds REAL,
                    triggered_by TEXT,
                    server_id TEXT,
                    version TEXT,
                    
                    -- 進捗情報
                    current_operation TEXT,
                    progress_percentage REAL DEFAULT 0,
                    completed_tasks TEXT,  -- JSON array
                    total_tasks INTEGER DEFAULT 0,
                    
                    -- リソース使用状況
                    cpu_usage_avg REAL,
                    memory_peak_mb INTEGER,
                    disk_io_mb INTEGER,
                    
                    -- メタデータ
                    metadata TEXT,  -- JSON
                    
                    -- エラー情報
                    errors TEXT,  -- JSON array
                    
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # テストデータ挿入（古いデータ、非アクティブ）
            test_data = [
                ("web_exec_001", "SYMBOL_ADDITION", "DOGE", None, "2025-06-20T15:00:00", None, "SUCCESS", None, "TEST", None, None, None, 0, "[]", 0, None, None, None, None, "[]"),
                ("web_exec_002", "SYMBOL_ADDITION", "ADA", None, "2025-06-20T14:00:00", None, "FAILED", None, "TEST", None, None, None, 0, "[]", 0, None, None, None, None, "[]"),
            ]
            
            for data in test_data:
                conn.execute("""
                    INSERT INTO execution_logs 
                    (execution_id, execution_type, symbol, symbols, timestamp_start, timestamp_end, status, 
                     duration_seconds, triggered_by, server_id, version, current_operation, progress_percentage, 
                     completed_tasks, total_tasks, cpu_usage_avg, memory_peak_mb, disk_io_mb, metadata, errors)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
            conn.commit()
    
    def test_current_db_references(self):
        """現在のDBファイル参照状況をテスト"""
        print("\n🧪 現在のDBファイル参照状況テスト")
        print("-" * 40)
        
        try:
            # execution_log_database.pyの参照先確認
            exec_db_path = Path("execution_log_database.py")
            if exec_db_path.exists():
                with open(exec_db_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # ルートディレクトリのDBを参照しているか
                if 'project_root = Path(__file__).parent' in content and 'execution_logs.db' in content:
                    print("✅ execution_log_database.py: ルートDB参照")
                else:
                    print("❌ execution_log_database.py: DB参照先不明")
                    self.test_results.append(("execution_log_database_ref", False))
                    return False
            
            # web_dashboard/app.pyの参照先確認
            app_py_path = Path("web_dashboard/app.py")
            if app_py_path.exists():
                with open(app_py_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 現在の参照先を確認
                if "exec_db_path = 'execution_logs.db'" in content:
                    print("❌ web_dashboard/app.py: ローカルDB参照（統一が必要）")
                    self.test_results.append(("web_dashboard_app_ref", False))
                    return False
                elif "exec_db_path = '../execution_logs.db'" in content:
                    print("✅ web_dashboard/app.py: ルートDB参照")
                else:
                    print("⚠️ web_dashboard/app.py: DB参照先不明")
            
            self.test_results.append(("current_db_references", True))
            return True
            
        except Exception as e:
            print(f"❌ DB参照先テストエラー: {e}")
            self.test_results.append(("current_db_references", False))
            return False
    
    def test_migration_script_functionality(self):
        """マイグレーションスクリプトの機能テスト"""
        print("\n🧪 マイグレーションスクリプト機能テスト")
        print("-" * 40)
        
        try:
            # マイグレーションスクリプトの存在確認
            migration_script = Path("db_unification_migration.py")
            if not migration_script.exists():
                print("❌ マイグレーションスクリプトが存在しません")
                self.test_results.append(("migration_script_exists", False))
                return False
            
            print("✅ マイグレーションスクリプトが存在します")
            
            # スクリプトの主要関数をテスト
            sys.path.insert(0, str(Path.cwd()))
            
            # テスト環境に移動してマイグレーション実行
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            try:
                from db_unification_migration import analyze_databases, migrate_data
                
                # データベース分析テスト
                analysis = analyze_databases()
                
                expected_root_count = 3  # テストデータ数
                expected_web_count = 2   # テストデータ数
                
                if (analysis['root_db']['count'] == expected_root_count and 
                    analysis['web_db']['count'] == expected_web_count):
                    print(f"✅ データベース分析: Root({expected_root_count}) Web({expected_web_count})")
                else:
                    print(f"❌ データベース分析: 予期しないレコード数")
                    self.test_results.append(("migration_analysis", False))
                    return False
                
                # ドライランテスト
                migrate_success = migrate_data(dry_run=True)
                if migrate_success:
                    print("✅ マイグレーション（ドライラン）成功")
                else:
                    print("❌ マイグレーション（ドライラン）失敗")
                    self.test_results.append(("migration_dry_run", False))
                    return False
                
            finally:
                os.chdir(original_cwd)
            
            self.test_results.append(("migration_script_functionality", True))
            return True
            
        except Exception as e:
            print(f"❌ マイグレーションスクリプトテストエラー: {e}")
            self.test_results.append(("migration_script_functionality", False))
            return False
    
    def test_unified_db_access(self):
        """統一後のDB参照テスト"""
        print("\n🧪 統一後のDB参照動作テスト")
        print("-" * 40)
        
        try:
            # テスト環境でのDB統一をシミュレート
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            try:
                # 統一DB作成（ルートDBにWebDBのデータを統合）
                with sqlite3.connect("execution_logs.db") as root_conn:
                    root_conn.execute("ATTACH DATABASE 'web_dashboard/execution_logs.db' AS web_db")
                    
                    # 重複チェック
                    cursor = root_conn.execute("""
                        SELECT COUNT(*) FROM web_db.execution_logs w
                        WHERE w.execution_id NOT IN (
                            SELECT execution_id FROM execution_logs
                        )
                    """)
                    new_records = cursor.fetchone()[0]
                    
                    # 新しいレコードを統合
                    root_conn.execute("""
                        INSERT OR IGNORE INTO execution_logs 
                        SELECT * FROM web_db.execution_logs 
                        WHERE execution_id NOT IN (
                            SELECT execution_id FROM execution_logs
                        )
                    """)
                    root_conn.commit()
                    
                    # 統合後の確認
                    cursor = root_conn.execute("SELECT COUNT(*) FROM execution_logs")
                    total_count = cursor.fetchone()[0]
                    
                    expected_total = 5  # 3 + 2 = 5レコード
                    if total_count == expected_total:
                        print(f"✅ DB統合成功: {total_count}レコード")
                    else:
                        print(f"❌ DB統合失敗: 予期しないレコード数 {total_count}")
                        self.test_results.append(("unified_db_access", False))
                        return False
                
                # 統一後のアクセステスト（ExecutionLogDatabaseクラス）
                sys.path.insert(0, str(Path(original_cwd)))
                from execution_log_database import ExecutionLogDatabase
                
                # 統一DBを参照
                db = ExecutionLogDatabase(db_path="execution_logs.db")
                executions = db.list_executions(limit=10)
                
                if len(executions) == expected_total:
                    print(f"✅ 統一DB経由のアクセス成功: {len(executions)}レコード")
                else:
                    print(f"❌ 統一DB経由のアクセス失敗: {len(executions)}レコード")
                    self.test_results.append(("unified_db_access", False))
                    return False
                
            finally:
                os.chdir(original_cwd)
            
            self.test_results.append(("unified_db_access", True))
            return True
            
        except Exception as e:
            print(f"❌ 統一DB参照テストエラー: {e}")
            self.test_results.append(("unified_db_access", False))
            return False
    
    def test_deletion_function_fix(self):
        """削除機能の修正テスト"""
        print("\n🧪 削除機能修正テスト")
        print("-" * 40)
        
        try:
            # app.pyの削除機能をテスト
            app_py_path = Path("web_dashboard/app.py")
            if not app_py_path.exists():
                print("❌ web_dashboard/app.py が存在しません")
                self.test_results.append(("deletion_function_fix", False))
                return False
            
            with open(app_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修正後のDB参照パスをチェック
            if "exec_db_path = '../execution_logs.db'" in content:
                print("✅ 削除機能のDB参照先が修正されています")
            elif "exec_db_path = 'execution_logs.db'" in content:
                print("❌ 削除機能のDB参照先が未修正（ローカルDB参照）")
                self.test_results.append(("deletion_function_fix", False))
                return False
            else:
                print("⚠️ 削除機能のDB参照先が不明")
                self.test_results.append(("deletion_function_fix", False))
                return False
            
            # 手動リセット機能のanalysis削除処理確認
            if "DELETE FROM analyses WHERE execution_id = ?" in content:
                print("✅ 分析結果削除処理が含まれています")
            else:
                print("❌ 分析結果削除処理が含まれていません")
                self.test_results.append(("deletion_function_fix", False))
                return False
            
            self.test_results.append(("deletion_function_fix", True))
            return True
            
        except Exception as e:
            print(f"❌ 削除機能テストエラー: {e}")
            self.test_results.append(("deletion_function_fix", False))
            return False
    
    def test_data_consistency_after_unification(self):
        """統一後のデータ整合性テスト"""
        print("\n🧪 統一後のデータ整合性テスト")
        print("-" * 40)
        
        try:
            # テスト環境での整合性チェック
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            try:
                # 統一DBの整合性チェック
                with sqlite3.connect("execution_logs.db") as conn:
                    # 重複チェック
                    cursor = conn.execute("""
                        SELECT execution_id, COUNT(*) as count 
                        FROM execution_logs 
                        GROUP BY execution_id 
                        HAVING count > 1
                    """)
                    duplicates = cursor.fetchall()
                    
                    if len(duplicates) == 0:
                        print("✅ 重複レコードなし")
                    else:
                        print(f"❌ 重複レコード検出: {len(duplicates)}件")
                        self.test_results.append(("data_consistency", False))
                        return False
                    
                    # データ型整合性チェック
                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM execution_logs 
                        WHERE execution_id IS NULL OR execution_type IS NULL
                    """)
                    null_count = cursor.fetchone()[0]
                    
                    if null_count == 0:
                        print("✅ 必須フィールドに NULL なし")
                    else:
                        print(f"❌ 必須フィールドに NULL: {null_count}件")
                        self.test_results.append(("data_consistency", False))
                        return False
                    
                    # ステータス整合性チェック
                    cursor = conn.execute("""
                        SELECT DISTINCT status FROM execution_logs
                    """)
                    statuses = [row[0] for row in cursor.fetchall()]
                    valid_statuses = ['PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELLED']
                    
                    invalid_statuses = set(statuses) - set(valid_statuses)
                    if len(invalid_statuses) == 0:
                        print("✅ ステータス値が有効")
                    else:
                        print(f"❌ 無効なステータス値: {invalid_statuses}")
                        self.test_results.append(("data_consistency", False))
                        return False
                
            finally:
                os.chdir(original_cwd)
            
            self.test_results.append(("data_consistency_after_unification", True))
            return True
            
        except Exception as e:
            print(f"❌ データ整合性テストエラー: {e}")
            self.test_results.append(("data_consistency_after_unification", False))
            return False
    
    def cleanup_test_environment(self):
        """テスト環境のクリーンアップ"""
        print("\n🧹 テスト環境クリーンアップ")
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
                print(f"✅ 削除: {temp_dir}")
            except Exception as e:
                print(f"⚠️ クリーンアップエラー: {e}")
    
    def print_test_summary(self):
        """テスト結果サマリー"""
        print("\n" + "=" * 60)
        print("📊 DB統一テスト結果")
        print("=" * 60)
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n📈 総合結果: {passed}/{total} テスト合格 ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 すべてのテストが合格しました！")
            print("✅ DB統一機能は正常に動作する準備ができています")
        else:
            print(f"\n⚠️ {total - passed}個のテストが失敗しました")
            print("❌ DB統一実装前に追加修正が必要です")
        
        return passed == total

def main():
    """メインテスト実行"""
    print("🚀 DB統一テストスイート")
    print("=" * 80)
    
    test = DbUnificationTest()
    
    try:
        # テスト環境セットアップ
        test.setup_test_environment()
        
        # テスト実行
        test.test_current_db_references()
        test.test_migration_script_functionality()
        test.test_unified_db_access()
        test.test_deletion_function_fix()
        test.test_data_consistency_after_unification()
        
        # 結果表示
        success = test.print_test_summary()
        
        return success
        
    finally:
        # クリーンアップ
        test.cleanup_test_environment()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)