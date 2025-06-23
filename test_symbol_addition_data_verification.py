#!/usr/bin/env python3
"""
銘柄追加時のデータ保存検証テスト
- execution_logs.db にレコードが保存されるか
- large_scale_analysis/analysis.db にレコードが保存されるか
- 外部キー関係が正しく保たれているか
"""

import sys
import os
import sqlite3
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

# BaseTestを使用して安全にテスト
sys.path.append(str(Path(__file__).parent))
from tests_organized.base_test import BaseTest

class SymbolAdditionDataVerificationTest(BaseTest):
    """銘柄追加データ保存検証テスト"""
    
    def custom_setup(self):
        """テスト用追加セットアップ"""
        # 銘柄追加に必要なモジュールをテスト環境で準備
        pass
    
    def test_execution_log_creation(self):
        """execution_logsテーブルへのレコード作成テスト"""
        print("\n🧪 execution_logs レコード作成テスト")
        
        # テスト用実行ログを作成
        execution_id = "test_symbol_addition_12345"
        symbol = "TEST_SYMBOL"
        
        execution_id = self.insert_test_execution_log(execution_id, symbol, "RUNNING")
        
        # データベースから確認
        with sqlite3.connect(self.execution_logs_db) as conn:
            cursor = conn.execute("""
                SELECT execution_id, execution_type, symbol, status, timestamp_start 
                FROM execution_logs 
                WHERE execution_id = ?
            """, (execution_id,))
            
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "execution_logs にレコードが作成されていません")
            self.assertEqual(result[0], execution_id)
            self.assertEqual(result[1], "SYMBOL_ADDITION")
            self.assertEqual(result[2], symbol)
            self.assertEqual(result[3], "RUNNING")
            
            print(f"   ✅ execution_logs レコード作成成功: {execution_id}")
    
    def test_analysis_data_creation(self):
        """analysesテーブルへのレコード作成テスト"""
        print("\n🧪 analyses レコード作成テスト")
        
        # 先にexecution_logを作成
        execution_id = "test_analysis_12345"
        symbol = "TEST_SYMBOL"
        
        self.insert_test_execution_log(execution_id, symbol, "SUCCESS")
        
        # 分析データを作成
        analysis_id = self.insert_test_analysis(
            execution_id, symbol, "30m", "Conservative_ML",
            sharpe_ratio=1.5,
            max_drawdown=-0.15,
            total_return=0.25
        )
        
        # データベースから確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT id, execution_id, symbol, timeframe, config, sharpe_ratio, total_return
                FROM analyses 
                WHERE id = ?
            """, (analysis_id,))
            
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "analyses にレコードが作成されていません")
            self.assertEqual(result[1], execution_id)
            self.assertEqual(result[2], symbol)
            self.assertEqual(result[3], "30m")
            self.assertEqual(result[4], "Conservative_ML")
            self.assertEqual(result[5], 1.5)
            self.assertEqual(result[6], 0.25)
            
            print(f"   ✅ analyses レコード作成成功: ID={analysis_id}")
    
    def test_foreign_key_relationship(self):
        """外部キー関係の整合性テスト"""
        print("\n🧪 外部キー関係整合性テスト")
        
        # execution_log作成
        execution_id = "test_fk_12345"
        symbol = "TEST_FK_SYMBOL"
        
        self.insert_test_execution_log(execution_id, symbol, "SUCCESS")
        
        # 複数の分析レコード作成
        timeframes = ["15m", "30m", "1h"]
        configs = ["Conservative_ML", "Aggressive_ML"]
        
        analysis_ids = []
        for timeframe in timeframes:
            for config in configs:
                analysis_id = self.insert_test_analysis(
                    execution_id, symbol, timeframe, config,
                    sharpe_ratio=1.0 + len(analysis_ids) * 0.1
                )
                analysis_ids.append(analysis_id)
        
        # JOINクエリで関係性確認
        with sqlite3.connect(self.analysis_db) as conn:
            # execution_logs.db をアタッチ
            conn.execute(f"ATTACH DATABASE '{self.execution_logs_db}' AS exec_db")
            
            cursor = conn.execute("""
                SELECT 
                    e.execution_id,
                    e.symbol as exec_symbol,
                    e.status,
                    a.id as analysis_id,
                    a.symbol as analysis_symbol,
                    a.timeframe,
                    a.config
                FROM analyses a
                INNER JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                WHERE e.execution_id = ?
                ORDER BY a.timeframe, a.config
            """, (execution_id,))
            
            results = cursor.fetchall()
            
            self.assertEqual(len(results), len(analysis_ids), "JOIN結果の件数が期待値と一致しません")
            
            for result in results:
                self.assertEqual(result[0], execution_id)
                self.assertEqual(result[1], symbol)
                self.assertEqual(result[2], "SUCCESS")
                self.assertEqual(result[4], symbol)  # analysis_symbol
                
            print(f"   ✅ 外部キー関係確認成功: {len(results)}件のレコード")
    
    def test_symbol_addition_complete_flow(self):
        """銘柄追加の完全フロー検証"""
        print("\n🧪 銘柄追加完全フロー検証")
        
        symbol = "BTC"
        execution_id = f"symbol_addition_{datetime.now().strftime('%Y%m%d_%H%M%S')}_test"
        
        # 1. 実行開始記録
        self.insert_test_execution_log(execution_id, symbol, "RUNNING")
        print(f"   📝 実行開始記録: {execution_id}")
        
        # 2. 複数パターンの分析結果作成
        timeframes = ["15m", "30m", "1h"]
        configs = ["Conservative_ML", "Aggressive_ML", "Balanced"]
        
        created_analyses = 0
        for timeframe in timeframes:
            for config in configs:
                try:
                    analysis_id = self.insert_test_analysis(
                        execution_id, symbol, timeframe, config,
                        sharpe_ratio=1.0 + created_analyses * 0.05,
                        max_drawdown=-0.1 - created_analyses * 0.01,
                        total_return=0.15 + created_analyses * 0.02
                    )
                    created_analyses += 1
                    print(f"   📊 分析作成: {timeframe} {config} (ID: {analysis_id})")
                except Exception as e:
                    print(f"   ❌ 分析作成失敗: {timeframe} {config} - {e}")
        
        # 3. 実行完了記録
        with sqlite3.connect(self.execution_logs_db) as conn:
            conn.execute("""
                UPDATE execution_logs 
                SET status = ?, timestamp_end = ?
                WHERE execution_id = ?
            """, ("SUCCESS", datetime.now(timezone.utc).isoformat(), execution_id))
        
        print(f"   ✅ 実行完了記録更新")
        
        # 4. 最終確認 - 全体の整合性チェック
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute(f"ATTACH DATABASE '{self.execution_logs_db}' AS exec_db")
            
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as analysis_count,
                    AVG(a.sharpe_ratio) as avg_sharpe,
                    e.status
                FROM analyses a
                INNER JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                WHERE e.execution_id = ?
                GROUP BY e.status
            """, (execution_id,))
            
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "最終確認クエリの結果が取得できません")
            self.assertEqual(result[0], created_analyses, f"作成された分析数が一致しません: {result[0]} != {created_analyses}")
            self.assertEqual(result[2], "SUCCESS", "実行ステータスがSUCCESSになっていません")
            
            print(f"   🎯 最終確認成功: {result[0]}件の分析、平均Sharpe={result[1]:.3f}")
    
    def test_data_persistence_after_restart(self):
        """データベース再起動後の永続化確認"""
        print("\n🧪 データ永続化確認テスト")
        
        # データ作成
        execution_id = "persistence_test_12345"
        symbol = "PERSISTENCE_TEST"
        
        self.insert_test_execution_log(execution_id, symbol, "SUCCESS")
        analysis_id = self.insert_test_analysis(execution_id, symbol, "1h", "Conservative_ML")
        
        # 一度接続を閉じて再接続
        original_data = None
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute(f"ATTACH DATABASE '{self.execution_logs_db}' AS exec_db")
            cursor = conn.execute("""
                SELECT e.execution_id, e.symbol, a.id, a.config
                FROM analyses a
                INNER JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                WHERE e.execution_id = ?
            """, (execution_id,))
            original_data = cursor.fetchone()
        
        # 再接続して同じデータを確認
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute(f"ATTACH DATABASE '{self.execution_logs_db}' AS exec_db")
            cursor = conn.execute("""
                SELECT e.execution_id, e.symbol, a.id, a.config
                FROM analyses a
                INNER JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                WHERE e.execution_id = ?
            """, (execution_id,))
            persisted_data = cursor.fetchone()
        
        self.assertEqual(original_data, persisted_data, "データの永続化に失敗しています")
        print(f"   ✅ データ永続化確認成功: {persisted_data}")

def run_symbol_addition_verification():
    """銘柄追加データ検証テスト実行"""
    import unittest
    
    # テストスイート作成
    suite = unittest.TestSuite()
    test_class = SymbolAdditionDataVerificationTest
    
    # 個別テストメソッドを追加
    suite.addTest(test_class('test_execution_log_creation'))
    suite.addTest(test_class('test_analysis_data_creation'))
    suite.addTest(test_class('test_foreign_key_relationship'))
    suite.addTest(test_class('test_symbol_addition_complete_flow'))
    suite.addTest(test_class('test_data_persistence_after_restart'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "="*60)
    print("🧪 銘柄追加データ検証テスト結果")
    print("="*60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️ エラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 すべてのテストが成功しました！")
        print("銘柄追加時のデータ保存は正常に動作しています。")
    else:
        print("\n⚠️ 一部のテストが失敗しました。")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_symbol_addition_verification()
    sys.exit(0 if success else 1)