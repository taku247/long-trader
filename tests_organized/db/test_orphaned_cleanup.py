#!/usr/bin/env python3
"""
孤立データクリーンアップテストスイート
"""

import os
import sys
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

class OrphanedCleanupTest:
    """孤立データクリーンアップテストクラス"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dirs = []
        
    def setup_test_environment(self):
        """テスト環境のセットアップ"""
        print("🔧 孤立データクリーンアップテスト環境セットアップ中...")
        
        # テスト用一時ディレクトリ作成
        self.temp_dir = Path(tempfile.mkdtemp(prefix="orphaned_cleanup_test_"))
        self.temp_dirs.append(self.temp_dir)
        
        # テスト用DB作成
        self.test_execution_db = self.temp_dir / "execution_logs.db"
        self.test_analysis_db = self.temp_dir / "analysis.db"
        
        # テスト用のサブディレクトリ構造を作成
        (self.temp_dir / "web_dashboard" / "large_scale_analysis").mkdir(parents=True)
        self.test_analysis_db = self.temp_dir / "web_dashboard" / "large_scale_analysis" / "analysis.db"
        
        # テスト用データベースを作成
        self._create_test_databases()
        
        print(f"✅ テスト環境: {self.temp_dir}")
        
    def _create_test_databases(self):
        """テスト用データベースとデータを作成"""
        # execution_logs.db 作成
        with sqlite3.connect(self.test_execution_db) as conn:
            conn.execute("""
                CREATE TABLE execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    execution_type TEXT NOT NULL,
                    symbol TEXT,
                    status TEXT NOT NULL,
                    timestamp_start TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 有効なexecution_idを作成
            valid_executions = [
                ("valid_exec_001", "SYMBOL_ADDITION", "BTC", "SUCCESS", "2025-06-21T10:00:00"),
                ("valid_exec_002", "SYMBOL_ADDITION", "ETH", "SUCCESS", "2025-06-21T09:00:00"),
                ("valid_exec_003", "SYMBOL_ADDITION", "SOL", "FAILED", "2025-06-21T08:00:00"),
            ]
            
            for data in valid_executions:
                conn.execute("""
                    INSERT INTO execution_logs 
                    (execution_id, execution_type, symbol, status, timestamp_start)
                    VALUES (?, ?, ?, ?, ?)
                """, data)
            conn.commit()
        
        # analysis.db 作成（孤立データを含む）
        with sqlite3.connect(self.test_analysis_db) as conn:
            conn.execute("""
                CREATE TABLE analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    config TEXT NOT NULL,
                    total_trades INTEGER,
                    win_rate REAL,
                    total_return REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    avg_leverage REAL,
                    chart_path TEXT,
                    compressed_path TEXT,
                    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    execution_id TEXT
                )
            """)
            
            # 古い日付を計算
            old_date = (datetime.now() - timedelta(days=35)).isoformat()
            
            # 様々な状態のテストデータを作成
            test_analyses = [
                # 有効なデータ
                ("BTC", "1h", "Conservative_ML", 10, 0.6, 0.15, 1.5, -0.08, 5.2, None, None, datetime.now().isoformat(), "valid_exec_001"),
                ("ETH", "4h", "Aggressive_ML", 8, 0.75, 0.22, 1.8, -0.12, 6.1, None, None, datetime.now().isoformat(), "valid_exec_002"),
                
                # 孤立データ（無効execution_id）
                ("DOGE", "1h", "Conservative_ML", 12, 0.5, 0.08, 1.2, -0.15, 3.8, None, None, datetime.now().isoformat(), "invalid_exec_001"),
                ("ADA", "4h", "Balanced", 7, 0.57, 0.12, 1.1, -0.18, 4.2, None, None, datetime.now().isoformat(), "invalid_exec_002"),
                
                # NULL execution_id
                ("LTC", "1d", "Full_ML", 5, 0.4, -0.05, 0.8, -0.25, 4.5, None, None, datetime.now().isoformat(), None),
                ("XRP", "1h", "Conservative_ML", 15, 0.67, 0.18, 1.6, -0.10, 4.8, None, None, datetime.now().isoformat(), None),
                
                # 空文字 execution_id
                ("DOT", "4h", "Aggressive_ML", 9, 0.44, 0.02, 0.9, -0.20, 5.5, None, None, datetime.now().isoformat(), ""),
                
                # 古いNULLデータ（30日以上前）
                ("OLD1", "1h", "Legacy", 20, 0.3, -0.15, 0.5, -0.30, 3.0, None, None, old_date, None),
                ("OLD2", "4h", "Legacy", 18, 0.35, -0.10, 0.6, -0.28, 3.2, None, None, old_date, None),
            ]
            
            for data in test_analyses:
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, timeframe, config, total_trades, win_rate, total_return, 
                     sharpe_ratio, max_drawdown, avg_leverage, chart_path, compressed_path, 
                     generated_at, execution_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
            conn.commit()
    
    def test_orphaned_data_detection(self):
        """孤立データ検出テスト"""
        print("\n🧪 孤立データ検出テスト")
        print("-" * 40)
        
        try:
            # テスト環境でクリーンアップスクリプトをインポート
            sys.path.insert(0, str(Path.cwd()))
            from orphaned_data_cleanup import OrphanedDataCleanup
            
            # テスト用のクリーンアップマネージャー作成
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            try:
                cleanup = OrphanedDataCleanup()
                analysis_result = cleanup.analyze_orphaned_data()
                
                # 検出結果の検証
                expected_total = 9  # テストデータ総数
                expected_valid = 2  # 有効データ数
                expected_null = 3   # NULL execution_id (LTC, XRP, OLD1, OLD2 = 4だが、OLD1,OLD2は別カウント)
                expected_empty = 1  # 空文字 execution_id (DOT)
                expected_invalid = 2 # 無効 execution_id (DOGE, ADA)
                
                print(f"📊 検出結果:")
                print(f"   総数: {analysis_result['total_analyses']} (期待値: {expected_total})")
                print(f"   有効: {analysis_result['valid_execution_id']} (期待値: {expected_valid})")
                print(f"   NULL: {analysis_result['null_execution_id']} (期待値: 3)")
                print(f"   空文字: {analysis_result['empty_execution_id']} (期待値: {expected_empty})")
                print(f"   無効: {analysis_result['invalid_execution_id']} (期待値: {expected_invalid})")
                print(f"   古いレコード: {len(analysis_result['old_records'])} (期待値: 2)")
                
                # 検証
                success = True
                if analysis_result['total_analyses'] != expected_total:
                    print(f"❌ 総数が期待値と異なります")
                    success = False
                
                if analysis_result['valid_execution_id'] != expected_valid:
                    print(f"❌ 有効データ数が期待値と異なります")
                    success = False
                
                if analysis_result['empty_execution_id'] != expected_empty:
                    print(f"❌ 空文字データ数が期待値と異なります")
                    success = False
                
                if analysis_result['invalid_execution_id'] != expected_invalid:
                    print(f"❌ 無効データ数が期待値と異なります")
                    success = False
                
                if len(analysis_result['old_records']) != 2:
                    print(f"❌ 古いレコード数が期待値と異なります")
                    success = False
                
                if success:
                    print("✅ 孤立データ検出が正常に動作しています")
                
                self.test_results.append(("orphaned_data_detection", success))
                return analysis_result
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            print(f"❌ 孤立データ検出テストエラー: {e}")
            self.test_results.append(("orphaned_data_detection", False))
            return None
    
    def test_cleanup_execution(self, analysis_result):
        """クリーンアップ実行テスト"""
        print("\n🧪 クリーンアップ実行テスト")
        print("-" * 40)
        
        if not analysis_result:
            print("❌ 分析結果がないためテストをスキップします")
            self.test_results.append(("cleanup_execution", False))
            return None
        
        try:
            from orphaned_data_cleanup import OrphanedDataCleanup
            
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            try:
                cleanup = OrphanedDataCleanup()
                
                # 実行前のレコード数を確認
                with sqlite3.connect(self.test_analysis_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM analyses")
                    before_count = cursor.fetchone()[0]
                
                # クリーンアップ実行（実際の削除）
                cleanup_summary = cleanup.execute_cleanup(analysis_result, dry_run=False)
                
                # 実行後のレコード数を確認
                with sqlite3.connect(self.test_analysis_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM analyses")
                    after_count = cursor.fetchone()[0]
                    
                    # 残ったレコードが有効なもののみかチェック
                    cursor = conn.execute("""
                        SELECT symbol, execution_id FROM analyses 
                        WHERE execution_id IS NOT NULL AND execution_id != ''
                    """)
                    remaining_records = cursor.fetchall()
                
                print(f"📊 クリーンアップ結果:")
                print(f"   実行前レコード数: {before_count}")
                print(f"   実行後レコード数: {after_count}")
                print(f"   削除レコード数: {cleanup_summary['total_deleted']}")
                print(f"   残存レコード: {len(remaining_records)}件")
                
                # 検証
                expected_deleted = analysis_result['null_execution_id'] + analysis_result['empty_execution_id'] + analysis_result['invalid_execution_id']
                expected_remaining = analysis_result['valid_execution_id']
                
                success = True
                if cleanup_summary['total_deleted'] != expected_deleted:
                    print(f"❌ 削除数が期待値({expected_deleted})と異なります")
                    success = False
                
                if after_count != expected_remaining:
                    print(f"❌ 残存レコード数が期待値({expected_remaining})と異なります")
                    success = False
                
                # 残存レコードがすべて有効なexecution_idを持つかチェック
                valid_execution_ids = {"valid_exec_001", "valid_exec_002", "valid_exec_003"}
                for symbol, execution_id in remaining_records:
                    if execution_id not in valid_execution_ids:
                        print(f"❌ 無効なexecution_idが残存しています: {symbol} -> {execution_id}")
                        success = False
                
                if success:
                    print("✅ クリーンアップが正常に実行されました")
                
                self.test_results.append(("cleanup_execution", success))
                return cleanup_summary
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            print(f"❌ クリーンアップ実行テストエラー: {e}")
            self.test_results.append(("cleanup_execution", False))
            return None
    
    def test_backup_functionality(self):
        """バックアップ機能テスト"""
        print("\n🧪 バックアップ機能テスト")
        print("-" * 40)
        
        try:
            from orphaned_data_cleanup import OrphanedDataCleanup
            
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            try:
                cleanup = OrphanedDataCleanup()
                
                # バックアップ実行
                backup_info = cleanup.backup_databases()
                
                # バックアップファイルの存在確認
                backup_dir = Path(backup_info['backup_dir'])
                analysis_backup = Path(backup_info['backups']['analysis'])
                info_file = backup_dir / "backup_info.json"
                
                success = True
                
                if not backup_dir.exists():
                    print(f"❌ バックアップディレクトリが存在しません: {backup_dir}")
                    success = False
                
                if not analysis_backup.exists():
                    print(f"❌ バックアップファイルが存在しません: {analysis_backup}")
                    success = False
                
                if not info_file.exists():
                    print(f"❌ バックアップ情報ファイルが存在しません: {info_file}")
                    success = False
                
                # バックアップファイルの内容確認
                if analysis_backup.exists():
                    with sqlite3.connect(analysis_backup) as conn:
                        cursor = conn.execute("SELECT COUNT(*) FROM analyses")
                        backup_count = cursor.fetchone()[0]
                        print(f"📁 バックアップレコード数: {backup_count}")
                        
                        if backup_count != 9:  # テストデータ総数
                            print(f"❌ バックアップレコード数が期待値(9)と異なります")
                            success = False
                
                if success:
                    print("✅ バックアップ機能が正常に動作しています")
                    print(f"   バックアップ場所: {backup_dir}")
                
                self.test_results.append(("backup_functionality", success))
                return True
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            print(f"❌ バックアップ機能テストエラー: {e}")
            self.test_results.append(("backup_functionality", False))
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
        print("📊 孤立データクリーンアップテスト結果")
        print("=" * 60)
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n📈 総合結果: {passed}/{total} テスト合格 ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 すべてのテストが合格しました！")
            print("✅ 孤立データクリーンアップ機能は正常に動作しています")
        else:
            print(f"\n⚠️ {total - passed}個のテストが失敗しました")
            print("❌ 追加修正が必要です")
        
        return passed == total

def main():
    """メインテスト実行"""
    print("🚀 孤立データクリーンアップテストスイート")
    print("=" * 80)
    
    test = OrphanedCleanupTest()
    
    try:
        # テスト環境セットアップ
        test.setup_test_environment()
        
        # テスト実行
        test.test_backup_functionality()
        analysis_result = test.test_orphaned_data_detection()
        test.test_cleanup_execution(analysis_result)
        
        # 結果表示
        success = test.print_test_summary()
        
        return success
        
    finally:
        # クリーンアップ
        test.cleanup_test_environment()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)