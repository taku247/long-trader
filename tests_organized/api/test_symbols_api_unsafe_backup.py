#!/usr/bin/env python3
"""
symbols APIのテスト
"""
import sqlite3
import os
import json

def test_symbols_api():
    """symbols API模擬テスト"""
    try:
        # Webサーバーと同じロジック
        parent_dir = "/Users/moriwakikeita/tools/long-trader"
        db_path = os.path.join(parent_dir, "large_scale_analysis", "analysis.db")
        exec_db_path = os.path.join(parent_dir, 'execution_logs.db')
        
        filter_mode = 'completed_only'
        
        print(f"🔍 pandas依存を回避してSQLアクセス")
        print(f"  db_path: {db_path}")
        print(f"  exec_db_path: {exec_db_path}")
        print(f"  filter_mode: {filter_mode}")
        
        # execution_logs.dbの存在確認
        if os.path.exists(exec_db_path):
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
        
        with sqlite3.connect(db_path) as conn:
            # execution_logs.db をアタッチ
            if os.path.exists(exec_db_path):
                conn.execute(f"ATTACH DATABASE '{exec_db_path}' AS exec_db")
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
            
            return symbols
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == '__main__':
    print("🧪 symbols API テスト実行...")
    result = test_symbols_api()
    
    print(f"\n📊 最終結果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))