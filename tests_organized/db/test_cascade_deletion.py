#!/usr/bin/env python3
"""
カスケード削除システムテストスイート
"""

import os
import sys
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))
from tests_organized.base_test import BaseTest

class CascadeDeletionTest(BaseTest):
    """カスケード削除テストクラス"""
    
    def custom_setup(self):
        """カスケード削除テスト固有のセットアップ"""
        self.test_results = []
        
        # テスト用ファイルアーティファクト用ディレクトリ
        self.charts_dir = Path(self.temp_dir) / "charts"
        self.compressed_dir = Path(self.temp_dir) / "compressed"
        self.charts_dir.mkdir(exist_ok=True)
        self.compressed_dir.mkdir(exist_ok=True)
        
        print(f"✅ カスケード削除テスト環境: {self.temp_dir}")
        
    def setup_test_environment(self):
        """BaseTestのセットアップを利用"""
        # BaseTestが既にセットアップを行っているので、追加のセットアップのみ実行
        self.custom_setup()
        
    def _create_test_databases(self):
        """テスト用データベースとデータを作成"""
        # execution_logs.db 作成 (BaseTestのDBを使用)
        with sqlite3.connect(self.execution_logs_db) as conn:
            conn.execute("""
                CREATE TABLE execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    execution_type TEXT NOT NULL,
                    symbol TEXT,
                    status TEXT NOT NULL,
                    timestamp_start TEXT NOT NULL,
                    timestamp_end TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # テスト用のexecution_logsデータ
            test_executions = [
                ("target_exec_001", "SYMBOL_ADDITION", "BTC", "SUCCESS", "2025-06-21T10:00:00", "2025-06-21T10:30:00"),
                ("target_exec_002", "SYMBOL_ADDITION", "ETH", "SUCCESS", "2025-06-21T09:00:00", "2025-06-21T09:45:00"),
                ("keep_exec_001", "SYMBOL_ADDITION", "SOL", "SUCCESS", "2025-06-21T08:00:00", "2025-06-21T08:30:00"),
                ("target_exec_003", "SYMBOL_ADDITION", "DOGE", "FAILED", "2025-06-21T07:00:00", "2025-06-21T07:15:00"),
            ]
            
            for data in test_executions:
                conn.execute("""
                    INSERT INTO execution_logs 
                    (execution_id, execution_type, symbol, status, timestamp_start, timestamp_end)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, data)
            conn.commit()
        
        # analysis.db 作成（関連分析結果を含む） (BaseTestのDBを使用)
        with sqlite3.connect(self.analysis_db) as conn:
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
                    execution_id TEXT NOT NULL
                )
            """)
            
            # テスト用ファイル作成
            chart1 = self.charts_dir / "btc_1h_chart.html"
            chart2 = self.charts_dir / "eth_4h_chart.html"
            compressed1 = self.compressed_dir / "btc_1h_data.gz"
            compressed2 = self.compressed_dir / "eth_4h_data.gz"
            
            # テストファイル作成
            chart1.write_text("<html>BTC Chart</html>")
            chart2.write_text("<html>ETH Chart</html>")
            compressed1.write_bytes(b"BTC compressed data")
            compressed2.write_bytes(b"ETH compressed data")
            
            # テスト用の分析結果データ
            test_analyses = [
                # target_exec_001 関連（削除対象）
                ("BTC", "1h", "Conservative_ML", 10, 0.6, 0.15, 1.5, -0.08, 5.2, str(chart1), str(compressed1), datetime.now().isoformat(), "target_exec_001"),
                ("BTC", "4h", "Aggressive_ML", 8, 0.75, 0.22, 1.8, -0.12, 6.1, None, None, datetime.now().isoformat(), "target_exec_001"),
                
                # target_exec_002 関連（削除対象）
                ("ETH", "1h", "Conservative_ML", 12, 0.5, 0.08, 1.2, -0.15, 3.8, str(chart2), str(compressed2), datetime.now().isoformat(), "target_exec_002"),
                ("ETH", "1d", "Full_ML", 5, 0.4, -0.05, 0.8, -0.25, 4.5, None, None, datetime.now().isoformat(), "target_exec_002"),
                
                # keep_exec_001 関連（保持対象）
                ("SOL", "1h", "Conservative_ML", 15, 0.67, 0.18, 1.6, -0.10, 4.8, None, None, datetime.now().isoformat(), "keep_exec_001"),
                ("SOL", "4h", "Balanced", 7, 0.57, 0.12, 1.1, -0.18, 4.2, None, None, datetime.now().isoformat(), "keep_exec_001"),
                
                # target_exec_003 関連（削除対象、失敗したexecution）
                ("DOGE", "1h", "Aggressive_ML", 3, 0.33, -0.20, 0.5, -0.35, 2.5, None, None, datetime.now().isoformat(), "target_exec_003"),
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
    
    def test_impact_analysis(self):
        """削除影響範囲分析テスト"""
        print("\n🧪 削除影響範囲分析テスト")
        print("-" * 40)
        
        try:
            # テスト環境でカスケード削除システムをインポート
            sys.path.insert(0, str(Path.cwd()))
            from cascade_deletion_system import CascadeDeletionSystem
            
            # テスト用のシステム作成
            original_cwd = os.getcwd()
            os.chdir(Path(self.temp_dir))
            
            try:
                cascade_system = CascadeDeletionSystem()
                
                # 削除対象のexecution_idを指定
                target_execution_ids = ["target_exec_001", "target_exec_002", "target_exec_003"]
                
                # 影響範囲分析実行
                impact_analysis = cascade_system.analyze_deletion_impact(target_execution_ids)
                
                # 検証
                expected_exec_logs = 3  # target_exec_001, target_exec_002, target_exec_003
                expected_analyses = 5   # BTC:2件 + ETH:2件 + DOGE:1件 = 5件
                expected_files = 4      # chart1, chart2, compressed1, compressed2
                
                print(f"📊 分析結果:")
                print(f"   実行ログ: {impact_analysis['execution_logs']['total_found']} (期待値: {expected_exec_logs})")
                print(f"   分析結果: {impact_analysis['analyses']['total_affected']} (期待値: {expected_analyses})")
                
                file_count = (len(impact_analysis['file_artifacts']['chart_files']) + 
                            len(impact_analysis['file_artifacts']['compressed_files']))
                print(f"   ファイル: {file_count} (期待値: {expected_files})")
                
                # 検証
                success = True
                if impact_analysis['execution_logs']['total_found'] != expected_exec_logs:
                    print(f"❌ 実行ログ数が期待値と異なります")
                    success = False
                
                if impact_analysis['analyses']['total_affected'] != expected_analyses:
                    print(f"❌ 分析結果数が期待値と異なります")
                    success = False
                
                if file_count != expected_files:
                    print(f"❌ ファイル数が期待値と異なります")
                    success = False
                
                # 銘柄別統計の確認
                expected_symbols = {"BTC": 2, "ETH": 2, "DOGE": 1}
                if impact_analysis['analyses']['by_symbol'] != expected_symbols:
                    print(f"❌ 銘柄別統計が期待値と異なります")
                    print(f"   実際: {impact_analysis['analyses']['by_symbol']}")
                    print(f"   期待: {expected_symbols}")
                    success = False
                
                if success:
                    print("✅ 削除影響範囲分析が正常に動作しています")
                
                self.test_results.append(("impact_analysis", success))
                return impact_analysis
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            print(f"❌ 削除影響範囲分析テストエラー: {e}")
            self.test_results.append(("impact_analysis", False))
            return None
    
    def test_cascade_deletion_dry_run(self, impact_analysis):
        """カスケード削除ドライランテスト"""
        print("\n🧪 カスケード削除ドライランテスト")
        print("-" * 40)
        
        if not impact_analysis:
            print("❌ 影響分析結果がないためテストをスキップします")
            self.test_results.append(("cascade_deletion_dry_run", False))
            return None
        
        try:
            from cascade_deletion_system import CascadeDeletionSystem
            
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            try:
                cascade_system = CascadeDeletionSystem()
                
                # ドライラン実行
                target_execution_ids = ["target_exec_001", "target_exec_002", "target_exec_003"]
                success = cascade_system.safe_cascade_delete(
                    execution_ids=target_execution_ids,
                    dry_run=True,
                    delete_files=True,
                    skip_backup=True
                )
                
                # ドライラン後のデータ確認（変更されていないことを確認）
                with sqlite3.connect(self.execution_logs_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
                    exec_count_after = cursor.fetchone()[0]
                
                with sqlite3.connect(self.analysis_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM analyses")
                    analysis_count_after = cursor.fetchone()[0]
                
                # ファイルが削除されていないことを確認
                chart1 = self.charts_dir / "btc_1h_chart.html"
                chart2 = self.charts_dir / "eth_4h_chart.html"
                files_exist = chart1.exists() and chart2.exists()
                
                print(f"📊 ドライラン結果:")
                print(f"   実行ログ数: {exec_count_after} (期待値: 4)")
                print(f"   分析結果数: {analysis_count_after} (期待値: 7)")
                print(f"   ファイル保持: {'Yes' if files_exist else 'No'}")
                
                # 検証
                test_success = True
                if exec_count_after != 4:  # 元の数
                    print(f"❌ ドライランで実行ログが変更されました")
                    test_success = False
                
                if analysis_count_after != 7:  # 元の数
                    print(f"❌ ドライランで分析結果が変更されました")
                    test_success = False
                
                if not files_exist:
                    print(f"❌ ドライランでファイルが削除されました")
                    test_success = False
                
                if not success:
                    print(f"❌ ドライラン実行でエラーが発生しました")
                    test_success = False
                
                if test_success:
                    print("✅ ドライランが正常に動作しています")
                
                self.test_results.append(("cascade_deletion_dry_run", test_success))
                return True
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            print(f"❌ カスケード削除ドライランテストエラー: {e}")
            self.test_results.append(("cascade_deletion_dry_run", False))
            return False
    
    def test_actual_cascade_deletion(self):
        """実際のカスケード削除テスト"""
        print("\n🧪 実際のカスケード削除テスト")
        print("-" * 40)
        
        try:
            from cascade_deletion_system import CascadeDeletionSystem
            
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            try:
                cascade_system = CascadeDeletionSystem()
                
                # 削除前の状況確認
                with sqlite3.connect(self.execution_logs_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
                    exec_count_before = cursor.fetchone()[0]
                
                with sqlite3.connect(self.analysis_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM analyses")
                    analysis_count_before = cursor.fetchone()[0]
                
                # 実際のカスケード削除実行
                target_execution_ids = ["target_exec_001", "target_exec_002"]  # 2件のみ削除
                success = cascade_system.safe_cascade_delete(
                    execution_ids=target_execution_ids,
                    dry_run=False,
                    delete_files=True,
                    skip_backup=True
                )
                
                # 削除後の状況確認
                with sqlite3.connect(self.execution_logs_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
                    exec_count_after = cursor.fetchone()[0]
                    
                    # 残っているexecution_idを確認
                    cursor = conn.execute("SELECT execution_id FROM execution_logs ORDER BY execution_id")
                    remaining_exec_ids = [row[0] for row in cursor.fetchall()]
                
                with sqlite3.connect(self.analysis_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM analyses")
                    analysis_count_after = cursor.fetchone()[0]
                    
                    # 残っているanalysesのexecution_idを確認
                    cursor = conn.execute("SELECT DISTINCT execution_id FROM analyses ORDER BY execution_id")
                    remaining_analysis_exec_ids = [row[0] for row in cursor.fetchall()]
                
                # ファイル削除の確認
                chart1 = self.charts_dir / "btc_1h_chart.html"
                chart2 = self.charts_dir / "eth_4h_chart.html"
                files_deleted = not chart1.exists() and not chart2.exists()
                
                print(f"📊 削除結果:")
                print(f"   実行ログ数: {exec_count_before} → {exec_count_after}")
                print(f"   分析結果数: {analysis_count_before} → {analysis_count_after}")
                print(f"   残存実行ID: {remaining_exec_ids}")
                print(f"   残存分析ID: {remaining_analysis_exec_ids}")
                print(f"   ファイル削除: {'Yes' if files_deleted else 'No'}")
                
                # 検証
                expected_exec_after = 2  # keep_exec_001, target_exec_003 が残る
                expected_analysis_after = 3  # SOL:2件 + DOGE:1件 = 3件
                expected_remaining_ids = ["keep_exec_001", "target_exec_003"]
                
                test_success = True
                if exec_count_after != expected_exec_after:
                    print(f"❌ 実行ログ削除数が期待値と異なります")
                    test_success = False
                
                if analysis_count_after != expected_analysis_after:
                    print(f"❌ 分析結果削除数が期待値と異なります")
                    test_success = False
                
                if set(remaining_exec_ids) != set(expected_remaining_ids):
                    print(f"❌ 残存実行IDが期待値と異なります")
                    test_success = False
                
                if not files_deleted:
                    print(f"❌ 関連ファイルが削除されていません")
                    test_success = False
                
                if not success:
                    print(f"❌ カスケード削除実行でエラーが発生しました")
                    test_success = False
                
                if test_success:
                    print("✅ カスケード削除が正常に実行されました")
                
                self.test_results.append(("actual_cascade_deletion", test_success))
                return True
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            print(f"❌ 実際のカスケード削除テストエラー: {e}")
            self.test_results.append(("actual_cascade_deletion", False))
            return False
    
    def test_backup_functionality(self):
        """バックアップ機能テスト"""
        print("\n🧪 バックアップ機能テスト")
        print("-" * 40)
        
        try:
            from cascade_deletion_system import CascadeDeletionSystem
            
            original_cwd = os.getcwd()
            os.chdir(Path(self.temp_dir))
            
            try:
                cascade_system = CascadeDeletionSystem()
                
                # バックアップ実行
                target_execution_ids = ["target_exec_003"]
                backup_info = cascade_system.backup_before_deletion(target_execution_ids)
                
                # バックアップファイルの存在確認
                backup_dir = Path(backup_info['backup_dir'])
                exec_backup = Path(backup_info['backups']['execution'])
                analysis_backup = Path(backup_info['backups']['analysis'])
                info_file = backup_dir / "backup_info.json"
                
                success = True
                
                if not backup_dir.exists():
                    print(f"❌ バックアップディレクトリが存在しません: {backup_dir}")
                    success = False
                
                if not exec_backup.exists():
                    print(f"❌ 実行ログバックアップが存在しません: {exec_backup}")
                    success = False
                
                if not analysis_backup.exists():
                    print(f"❌ 分析結果バックアップが存在しません: {analysis_backup}")
                    success = False
                
                if not info_file.exists():
                    print(f"❌ バックアップ情報ファイルが存在しません: {info_file}")
                    success = False
                
                # バックアップファイルの内容確認
                if exec_backup.exists():
                    with sqlite3.connect(exec_backup) as conn:
                        cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
                        backup_exec_count = cursor.fetchone()[0]
                        
                        if backup_exec_count != 4:  # 元のテストデータ数
                            print(f"❌ 実行ログバックアップのレコード数が不正: {backup_exec_count}")
                            success = False
                
                if analysis_backup.exists():
                    with sqlite3.connect(analysis_backup) as conn:
                        cursor = conn.execute("SELECT COUNT(*) FROM analyses")
                        backup_analysis_count = cursor.fetchone()[0]
                        
                        if backup_analysis_count < 3:  # 残りのレコード数
                            print(f"❌ 分析結果バックアップのレコード数が不正: {backup_analysis_count}")
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
        # BaseTestが自動的にクリーンアップを行うため、追加処理のみ
        print("✅ BaseTestによる自動クリーンアップ完了")
    
    def print_test_summary(self):
        """テスト結果サマリー"""
        print("\n" + "=" * 60)
        print("📊 カスケード削除テスト結果")
        print("=" * 60)
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n📈 総合結果: {passed}/{total} テスト合格 ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 すべてのテストが合格しました！")
            print("✅ カスケード削除システムは正常に動作しています")
        else:
            print(f"\n⚠️ {total - passed}個のテストが失敗しました")
            print("❌ 追加修正が必要です")
        
        return passed == total

    def test_cascade_deletion_workflow(self):
        """カスケード削除ワークフローテスト"""
        print("🚀 カスケード削除テストスイート")
        print("=" * 80)
        
        # テスト環境セットアップ
        self.setup_test_environment()
        
        # テスト実行
        self.test_backup_functionality()
        impact_analysis = self.test_impact_analysis()
        self.test_cascade_deletion_dry_run(impact_analysis)
        self.test_actual_cascade_deletion()
        
        # 結果表示
        success = self.print_test_summary()
        self.assertTrue(success, "カスケード削除テストが失敗しました")

def run_cascade_deletion_tests():
    """カスケード削除テスト実行"""
    import unittest
    
    # テストスイート作成
    suite = unittest.TestSuite()
    test_class = CascadeDeletionTest
    
    # テストメソッドを追加
    suite.addTest(test_class('test_cascade_deletion_workflow'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    import sys
    success = run_cascade_deletion_tests()
    sys.exit(0 if success else 1)