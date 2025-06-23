#!/usr/bin/env python3
"""
symbols APIのテスト（安全版）
⚠️ 注意: テスト用DBを使用して本番DBへの影響を防ぐ
"""
import sqlite3
import os
import json
import tempfile
import shutil
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))
from tests_organized.base_test import BaseTest

class SymbolsAPITest(BaseTest):
    """symbols APIテストクラス"""
    
    def custom_setup(self):
        """テスト固有のセットアップ"""
        self.setup_test_data()
    
    def setup_test_data(self):
        """テスト用データベースにデータを作成"""
        # BaseTestのデータベースを使用してテストデータを初期化
        with sqlite3.connect(self.analysis_db) as conn:
            # テストデータの挿入
            test_data = [
                ('BTC', 'test_exec_1', 1.5),
                ('ETH', 'test_exec_2', 1.2),
                ('SOL', 'test_exec_3', 0.8)
            ]
            for symbol, exec_id, sharpe in test_data:
                for i in range(20):  # 20パターンで満たす
                    conn.execute(
                        "INSERT INTO analyses (symbol, execution_id, sharpe_ratio) VALUES (?, ?, ?)",
                        (symbol, f"{exec_id}_{i}", sharpe + (i * 0.1))
                    )
        
        with sqlite3.connect(self.execution_logs_db) as conn:
            # テスト実行ログ
            for symbol in ['BTC', 'ETH', 'SOL']:
                for i in range(20):
                    conn.execute(
                        "INSERT INTO execution_logs (execution_id, status) VALUES (?, ?)",
                        (f"test_exec_{['1','2','3'][['BTC','ETH','SOL'].index(symbol)]}_{i}", 'SUCCESS')
                    )

    def test_symbols_api(self):
        """符号api模擬テスト - テスト用DB使用"""
        print(f"🧪 テスト用DB使用 (本番DBへの影響なし)")
        print(f"  analysis_db: {self.analysis_db}")
        print(f"  execution_logs_db: {self.execution_logs_db}")
        
        filter_mode = 'completed_only'
        
        print(f"🔍 pandas依存を回避してSQLアクセス")
        print(f"  filter_mode: {filter_mode}")
        
        # execution_logs.dbの存在確認
        if os.path.exists(self.execution_logs_db):
            print("✅ execution_logs.db存在")
            # JOINクエリ
            query = """
                SELECT a.symbol, COUNT(*) as pattern_count, AVG(a.sharpe_ratio) as avg_sharpe
                FROM analyses a
                INNER JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                WHERE e.status = 'SUCCESS'
                GROUP BY a.symbol 
                HAVING pattern_count >= 18
                ORDER BY pattern_count DESC, avg_sharpe DESC
            """
        else:
            print("❌ execution_logs.db不存在")
            # シンプルクエリ
            query = """
                SELECT symbol, COUNT(*) as pattern_count, AVG(sharpe_ratio) as avg_sharpe
                FROM analyses
                WHERE symbol IS NOT NULL
                GROUP BY symbol
                HAVING pattern_count >= 8
                ORDER BY pattern_count DESC, avg_sharpe DESC
            """
        
        print(f"📊 実行クエリ:")
        print(f"  {query}")
        
        with sqlite3.connect(self.analysis_db) as conn:
            # execution_logs.db をアタッチ
            if os.path.exists(self.execution_logs_db):
                conn.execute(f"ATTACH DATABASE '{self.execution_logs_db}' AS exec_db")
                print("✅ execution_logs.db アタッチ成功")
            
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            print(f"📋 クエリ結果: {len(results)}件")
            
            symbols = []
            for row in results:
                symbol_data = {
                    'symbol': row[0],
                    'pattern_count': row[1] if row[1] is not None else 0,
                    'avg_sharpe': round(row[2], 2) if row[2] else 0
                }
                
                if filter_mode == 'completed_only':
                    symbol_data['completion_rate'] = round((row[1] / 18.0) * 100, 1)
                
                symbols.append(symbol_data)
                print(f"  {symbol_data}")
            
            # テスト検証
            self.assertGreater(len(symbols), 0, "シンボルが取得できませんでした")
            print(f"\n✅ テスト成功: {len(symbols)}件の銘柄取得")

def run_symbols_api_tests():
    """symbols APIテスト実行"""
    import unittest
    
    # テストスイート作成
    suite = unittest.TestSuite()
    test_class = SymbolsAPITest
    
    # テストメソッドを追加
    suite.addTest(test_class('test_symbols_api'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    import sys
    success = run_symbols_api_tests()
    sys.exit(0 if success else 1)