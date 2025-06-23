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

def setup_test_db():
    """テスト用データベースを作成"""
    test_dir = tempfile.mkdtemp(prefix="test_symbols_api_")
    
    # テスト用analysis.db作成
    analysis_dir = os.path.join(test_dir, "large_scale_analysis")
    os.makedirs(analysis_dir)
    analysis_db = os.path.join(analysis_dir, "analysis.db")
    
    # テスト用execution_logs.db作成
    exec_db = os.path.join(test_dir, "execution_logs.db")
    
    # テストデータで初期化
    with sqlite3.connect(analysis_db) as conn:
        conn.execute("""
            CREATE TABLE analyses (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                execution_id TEXT,
                sharpe_ratio REAL
            )
        """)
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
    
    with sqlite3.connect(exec_db) as conn:
        conn.execute("""
            CREATE TABLE execution_logs (
                execution_id TEXT PRIMARY KEY,
                status TEXT
            )
        """)
        # テスト実行ログ
        for symbol in ['BTC', 'ETH', 'SOL']:
            for i in range(20):
                conn.execute(
                    "INSERT INTO execution_logs (execution_id, status) VALUES (?, ?)",
                    (f"test_exec_{['1','2','3'][['BTC','ETH','SOL'].index(symbol)]}_{i}", 'SUCCESS')
                )
    
    return test_dir, analysis_db, exec_db

def test_symbols_api():
    """符号api模擬テスト - テスト用DB使用"""
    test_dir = None
    try:
        # テスト用DBのセットアップ
        test_dir, db_path, exec_db_path = setup_test_db()
        
        print(f"🧪 テスト用DB使用 (本番DBへの影響なし)")
        print(f"  test_dir: {test_dir}")
        print(f"  db_path: {db_path}")
        print(f"  exec_db_path: {exec_db_path}")
        
        filter_mode = 'completed_only'
        
        print(f"🔍 pandas依存を回避してSQLアクセス")
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
        return []
    finally:
        # テスト用DBのクリーンアップ
        if test_dir and os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"🧹 テスト用DB削除: {test_dir}")

if __name__ == "__main__":
    result = test_symbols_api()
    print(f"\n🎯 最終結果: {len(result)}件の銘柄")