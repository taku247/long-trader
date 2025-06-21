#!/usr/bin/env python3
"""
execution_id統合テスト - 実際の銘柄追加フローをテスト
"""

import asyncio
import sqlite3
import os
import sys
import json
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class ExecutionIdIntegrationTest:
    """execution_id統合テストクラス"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dirs = []
        
    def setup_test_environment(self):
        """テスト環境のセットアップ"""
        print("🔧 テスト環境セットアップ中...")
        
        # テスト用一時ディレクトリ作成
        self.temp_dir = Path(tempfile.mkdtemp(prefix="execution_id_test_"))
        self.temp_dirs.append(self.temp_dir)
        
        # テスト用DB作成
        self.test_execution_db = self.temp_dir / "execution_logs.db"
        self.test_analysis_db = self.temp_dir / "analysis.db"
        
        # 実際のDBからスキーマをコピー
        self._copy_db_schema()
        
        print(f"✅ テスト環境: {self.temp_dir}")
        
    def _copy_db_schema(self):
        """実際のDBスキーマをテスト用DBにコピー"""
        # execution_logs.db スキーマ
        real_execution_db = Path("web_dashboard/execution_logs.db")
        if real_execution_db.exists():
            shutil.copy2(real_execution_db, self.test_execution_db)
            # テストデータをクリア
            with sqlite3.connect(self.test_execution_db) as conn:
                conn.execute("DELETE FROM execution_logs")
                conn.execute("DELETE FROM execution_steps")
                conn.commit()
        
        # analysis.db スキーマ
        real_analysis_db = Path("web_dashboard/large_scale_analysis/analysis.db")
        if real_analysis_db.exists():
            shutil.copy2(real_analysis_db, self.test_analysis_db)
            # テストデータをクリア
            with sqlite3.connect(self.test_analysis_db) as conn:
                conn.execute("DELETE FROM analyses")
                conn.execute("DELETE FROM backtest_summary")
                conn.commit()
    
    def test_execution_log_creation(self):
        """実行ログ作成テスト"""
        print("\n🧪 実行ログ作成テスト")
        print("-" * 40)
        
        try:
            from execution_log_database import ExecutionLogDatabase, ExecutionType
            
            # テスト用DBパスを設定
            db = ExecutionLogDatabase(db_path=str(self.test_execution_db))
            
            # 実行ログ作成（ExecutionType.SYMBOL_ADDITIONを使用）
            execution_id = db.create_execution(
                execution_type=ExecutionType.SYMBOL_ADDITION,
                symbol="TESTCOIN",
                triggered_by="INTEGRATION_TEST",
                metadata={"test": True, "auto_training": True}
            )
            
            print(f"✅ 実行ID生成: {execution_id}")
            
            # 作成されたログを確認
            with sqlite3.connect(self.test_execution_db) as conn:
                cursor = conn.execute(
                    "SELECT execution_id, symbol, status FROM execution_logs WHERE execution_id = ?",
                    (execution_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    print(f"✅ ログ確認: {row[0]} | {row[1]} | {row[2]}")
                    self.test_results.append(("execution_log_creation", True))
                    return execution_id
                else:
                    print("❌ 実行ログが作成されていません")
                    self.test_results.append(("execution_log_creation", False))
                    return None
                    
        except Exception as e:
            print(f"❌ 実行ログ作成エラー: {e}")
            self.test_results.append(("execution_log_creation", False))
            return None
    
    def test_scalable_analysis_with_execution_id(self, execution_id):
        """ScalableAnalysisSystemでのexecution_id記録テスト"""
        print("\n🧪 ScalableAnalysisSystem execution_id記録テスト")
        print("-" * 40)
        
        try:
            # 環境変数にexecution_idを設定
            os.environ['CURRENT_EXECUTION_ID'] = execution_id
            
            from scalable_analysis_system import ScalableAnalysisSystem
            
            # テスト用のScalableAnalysisSystemを作成
            system = ScalableAnalysisSystem(base_dir=str(self.temp_dir))
            
            # テスト用メトリクス
            test_metrics = {
                'total_trades': 10,
                'win_rate': 0.6,
                'total_return': 0.15,
                'sharpe_ratio': 1.5,
                'max_drawdown': -0.08,
                'avg_leverage': 5.2
            }
            
            # _save_to_databaseを直接テスト
            system._save_to_database(
                symbol="TESTCOIN",
                timeframe="1h", 
                config="Conservative_ML",
                metrics=test_metrics,
                chart_path=None,
                compressed_path=None,
                execution_id=execution_id
            )
            
            # 保存されたデータを確認
            with sqlite3.connect(self.test_analysis_db) as conn:
                cursor = conn.execute("""
                    SELECT symbol, timeframe, config, execution_id 
                    FROM analyses 
                    WHERE symbol = 'TESTCOIN'
                """)
                row = cursor.fetchone()
                
                if row and row[3] == execution_id:
                    print(f"✅ 分析結果保存: {row[0]} | {row[1]} | {row[2]} | {row[3]}")
                    self.test_results.append(("scalable_analysis_execution_id", True))
                    return True
                else:
                    print(f"❌ execution_idが正しく保存されていません: {row}")
                    self.test_results.append(("scalable_analysis_execution_id", False))
                    return False
                    
        except Exception as e:
            print(f"❌ ScalableAnalysisSystem テストエラー: {e}")
            self.test_results.append(("scalable_analysis_execution_id", False))
            return False
        finally:
            # 環境変数をクリア
            if 'CURRENT_EXECUTION_ID' in os.environ:
                del os.environ['CURRENT_EXECUTION_ID']
    
    def test_manual_reset_cleanup(self, execution_id):
        """手動リセット時のクリーンアップテスト"""
        print("\n🧪 手動リセット分析結果クリーンアップテスト")
        print("-" * 40)
        
        try:
            # 手動リセット処理のシミュレーション
            with sqlite3.connect(self.test_execution_db) as exec_conn:
                # 実行ログをCANCELLEDに更新
                exec_conn.execute("""
                    UPDATE execution_logs 
                    SET status = 'CANCELLED'
                    WHERE execution_id = ?
                """, (execution_id,))
                exec_conn.commit()
            
            # 分析結果削除（手動リセット機能の模擬）
            with sqlite3.connect(self.test_analysis_db) as analysis_conn:
                cursor = analysis_conn.execute("""
                    DELETE FROM analyses WHERE execution_id = ?
                """, (execution_id,))
                deleted_count = cursor.rowcount
                analysis_conn.commit()
            
            print(f"✅ 削除された分析結果: {deleted_count}件")
            
            # 削除確認
            with sqlite3.connect(self.test_analysis_db) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM analyses WHERE execution_id = ?
                """, (execution_id,))
                remaining_count = cursor.fetchone()[0]
                
                if remaining_count == 0:
                    print("✅ 分析結果が正しく削除されました")
                    self.test_results.append(("manual_reset_cleanup", True))
                    return True
                else:
                    print(f"❌ 分析結果が残っています: {remaining_count}件")
                    self.test_results.append(("manual_reset_cleanup", False))
                    return False
                    
        except Exception as e:
            print(f"❌ 手動リセットテストエラー: {e}")
            self.test_results.append(("manual_reset_cleanup", False))
            return False
    
    def test_data_integrity(self):
        """データ整合性テスト"""
        print("\n🧪 データ整合性テスト")
        print("-" * 40)
        
        try:
            # execution_logsとanalysesの関連性チェック
            with sqlite3.connect(self.test_execution_db) as exec_conn:
                exec_cursor = exec_conn.execute("SELECT execution_id FROM execution_logs")
                execution_ids = [row[0] for row in exec_cursor.fetchall()]
            
            with sqlite3.connect(self.test_analysis_db) as analysis_conn:
                analysis_cursor = analysis_conn.execute("""
                    SELECT DISTINCT execution_id FROM analyses WHERE execution_id IS NOT NULL
                """)
                analysis_execution_ids = [row[0] for row in analysis_cursor.fetchall()]
            
            # 孤立した分析結果がないかチェック
            orphaned = set(analysis_execution_ids) - set(execution_ids)
            
            if len(orphaned) == 0:
                print("✅ 孤立した分析結果はありません")
                self.test_results.append(("data_integrity", True))
                return True
            else:
                print(f"❌ 孤立した分析結果: {orphaned}")
                self.test_results.append(("data_integrity", False))
                return False
                
        except Exception as e:
            print(f"❌ データ整合性テストエラー: {e}")
            self.test_results.append(("data_integrity", False))
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
        print("📊 execution_id統合テスト結果")
        print("=" * 60)
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n📈 総合結果: {passed}/{total} テスト合格 ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 すべてのテストが合格しました！")
            print("✅ execution_id統合機能は正常に動作しています")
        else:
            print(f"\n⚠️ {total - passed}個のテストが失敗しました")
            print("❌ 追加修正が必要です")
        
        return passed == total

def main():
    """メインテスト実行"""
    print("🚀 execution_id統合テストスイート")
    print("=" * 80)
    
    test = ExecutionIdIntegrationTest()
    
    try:
        # テスト環境セットアップ
        test.setup_test_environment()
        
        # テスト実行
        execution_id = test.test_execution_log_creation()
        if execution_id:
            test.test_scalable_analysis_with_execution_id(execution_id)
            test.test_manual_reset_cleanup(execution_id)
        
        test.test_data_integrity()
        
        # 結果表示
        success = test.print_test_summary()
        
        return success
        
    finally:
        # クリーンアップ
        test.cleanup_test_environment()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)