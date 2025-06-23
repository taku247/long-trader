#!/usr/bin/env python3
"""
SOL APIの直接テスト（安全版）
BaseTestフレームワーク統合版
⚠️ 注意: テスト用DBを使用して本番DBへの影響を防ぐ
"""
import sqlite3
import json
import os
import unittest
import sys

# プロジェクトルートを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tests_organized.base_test import APITest


class TestSOLAPIDirect(APITest):
    """SOL API直接テストクラス"""
    
    def custom_setup(self):
        """テスト固有のセットアップ"""
        super().custom_setup()
        # SOLテストデータの作成
        self.setup_test_sol_data()
    
    def setup_test_sol_data(self):
        """テスト用SOLデータベースデータを作成"""
        # SOLテストデータの作成
        with sqlite3.connect(self.analysis_db) as conn:
            # SOLテストデータ
            strategies = ['Conservative_ML', 'Aggressive_Traditional', 'Full_ML']
            timeframes = ['30m', '1h', '4h']
            
            for i, strategy in enumerate(strategies):
                for j, tf in enumerate(timeframes):
                    execution_id = f'test_sol_{i}_{j}'
                    
                    # execution_logを作成
                    self.insert_test_execution_log(execution_id, 'SOL')
                    
                    # analysisレコードを挿入
                    conn.execute("""
                        INSERT INTO analyses 
                        (symbol, execution_id, timeframe, config, sharpe_ratio, max_drawdown, total_return)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        'SOL', 
                        execution_id,
                        tf,
                        strategy,
                        1.2 + (i * 0.1) + (j * 0.05),
                        -0.15 - (i * 0.02),
                        0.25 + (i * 0.1)
                    ))
        
        print(f"   📈 SOLテストデータ作成完了: {len(strategies) * len(timeframes)}パターン")
    
    def test_sol_api(self):
        """SOL API模擬テスト - テスト用DB使用"""
        symbol = "SOL"
        
        try:
            print(f"🧪 SOLテスト用DB使用 (本番DBへの影響なし)")
            print(f"  analysis_db: {self.analysis_db}")
            print(f"  exec_db_path: {self.execution_logs_db}")
            
            # ScalableAnalysisSystemのクエリロジック模擬
            conn = sqlite3.connect(self.analysis_db)
            cursor = conn.cursor()
            
            # execution_logs.dbアタッチ
            query = "SELECT * FROM analyses WHERE 1=1"
            params = []
            
            if os.path.exists(self.execution_logs_db):
                conn.execute(f"ATTACH DATABASE '{self.execution_logs_db}' AS exec_db")
                print("✅ execution_logs.db アタッチ成功")
                
                # manual_レコード数確認
                cursor.execute("SELECT COUNT(*) FROM analyses WHERE execution_id LIKE 'manual_%'")
                manual_count = cursor.fetchone()[0]
                print(f"📊 manual_レコード数: {manual_count}")
                
                if manual_count > 0:
                    # フォールバック: シンプルクエリ
                    query = "SELECT * FROM analyses WHERE 1=1"
                    print("🔄 シンプルクエリ使用（manual_レコード存在）")
                else:
                    # JOINクエリ
                    query = """
                        SELECT a.* FROM analyses a
                        INNER JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                        WHERE e.status = 'SUCCESS' AND a.execution_id IS NOT NULL
                    """
                    print("🔗 JOINクエリ使用")
            
            # フィルター追加
            query += " AND symbol = ?"
            params.append(symbol)
            query += " ORDER BY sharpe_ratio DESC"
            
            print(f"📋 実行クエリ: {query}")
            print(f"📋 パラメータ: {params}")
            
            cursor.execute(query, params)
            
            # カラム名取得
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            print(f"✅ {symbol}分析結果: {len(rows)}件")
            
            # 結果をディクショナリ形式に変換
            results = []
            for row in rows:
                result_dict = dict(zip(columns, row))
                results.append(result_dict)
                print(f"  {result_dict['timeframe']} {result_dict['config']}: シャープレシオ={result_dict['sharpe_ratio']}")
            
            conn.close()
            
            # APIレスポンス形式
            api_response = {
                "results": results,
                "total_count": len(results),
                "symbol": symbol
            }
            
            print(f"\n🎯 API応答例:")
            print(json.dumps(api_response, indent=2, ensure_ascii=False))
            
            # アサーション
            self.assertGreater(len(results), 0, "SOL分析結果が取得されている必要があります")
            self.assertEqual(api_response["symbol"], symbol)
            self.assertEqual(api_response["total_count"], len(results))
            
            # 各結果の必須フィールドを確認
            for result in results:
                self.assertIn('timeframe', result)
                self.assertIn('config', result)
                self.assertIn('sharpe_ratio', result)
                self.assertIn('symbol', result)
                self.assertEqual(result['symbol'], symbol)
            
            return api_response
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            self.fail(f"SOL APIテストでエラーが発生しました: {e}")
            return {"results": [], "error": str(e)}
    
    def test_sol_api_response_format(self):
        """SOL APIレスポンス形式テスト"""
        result = self.test_sol_api()
        
        # レスポンス形式の検証
        self.assertIsInstance(result, dict, "APIレスポンスは辞書形式である必要があります")
        self.assertIn("results", result, "APIレスポンスに'results'キーが必要です")
        self.assertIn("total_count", result, "APIレスポンスに'total_count'キーが必要です")
        self.assertIn("symbol", result, "APIレスポンスに'symbol'キーが必要です")
        
        # resultsの検証
        results = result["results"]
        self.assertIsInstance(results, list, "resultsはリスト形式である必要があります")
        
        if results:
            # 最初の結果の構造を確認
            first_result = results[0]
            required_fields = ['symbol', 'timeframe', 'config', 'sharpe_ratio']
            for field in required_fields:
                self.assertIn(field, first_result, f"結果に'{field}'フィールドが必要です")
        
        return result
    
    def test_complete_sol_workflow(self):
        """完全なSOL APIワークフローテスト"""
        print("=" * 60)
        print("🚀 SOL API完全ワークフローテスト")
        print("=" * 60)
        
        # データベース分離の確認
        self.assert_db_isolated()
        
        # テストデータの存在確認
        self.assert_test_data_exists("SOL", 1)
        
        # API テストの実行
        result = self.test_sol_api_response_format()
        
        print(f"\n🚀 テスト完了: {len(result.get('results', []))}件の結果")
        
        # 最終的なアサーション
        self.assertGreater(len(result.get('results', [])), 0, "SOL分析結果が取得されている必要があります")


def run_tests():
    """テストランナー関数"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()