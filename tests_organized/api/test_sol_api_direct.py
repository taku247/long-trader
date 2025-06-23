#!/usr/bin/env python3
"""
SOL APIの直接テスト（安全版）
⚠️ 注意: テスト用DBを使用して本番DBへの影響を防ぐ
"""
import sqlite3
import json
import os
import tempfile
import shutil

def setup_test_sol_db():
    """テスト用SOLデータベースを作成"""
    test_dir = tempfile.mkdtemp(prefix="test_sol_api_")
    
    # テスト用analysis.db作成
    analysis_dir = os.path.join(test_dir, "large_scale_analysis")
    os.makedirs(analysis_dir)
    analysis_db = os.path.join(analysis_dir, "analysis.db")
    
    # テスト用execution_logs.db作成
    exec_db = os.path.join(test_dir, "execution_logs.db")
    
    # SOLテストデータの作成
    with sqlite3.connect(analysis_db) as conn:
        conn.execute("""
            CREATE TABLE analyses (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                execution_id TEXT,
                timeframe TEXT,
                config TEXT,
                sharpe_ratio REAL,
                max_drawdown REAL,
                total_return REAL
            )
        """)
        
        # SOLテストデータ
        strategies = ['Conservative_ML', 'Aggressive_Traditional', 'Full_ML']
        timeframes = ['30m', '1h', '4h']
        
        for i, strategy in enumerate(strategies):
            for j, tf in enumerate(timeframes):
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, execution_id, timeframe, config, sharpe_ratio, max_drawdown, total_return)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    'SOL', 
                    f'test_sol_{i}_{j}',
                    tf,
                    strategy,
                    1.2 + (i * 0.1) + (j * 0.05),
                    -0.15 - (i * 0.02),
                    0.25 + (i * 0.1)
                ))
    
    with sqlite3.connect(exec_db) as conn:
        conn.execute("""
            CREATE TABLE execution_logs (
                execution_id TEXT PRIMARY KEY,
                status TEXT,
                symbol TEXT
            )
        """)
        
        # SOL実行ログ
        for i in range(3):
            for j in range(3):
                conn.execute(
                    "INSERT INTO execution_logs (execution_id, status, symbol) VALUES (?, ?, ?)",
                    (f'test_sol_{i}_{j}', 'SUCCESS', 'SOL')
                )
    
    return test_dir, analysis_db, exec_db

def test_sol_api():
    """SOL API模擬テスト - テスト用DB使用"""
    test_dir = None
    symbol = "SOL"
    
    try:
        # テスト用DBセットアップ
        test_dir, analysis_db, exec_db_path = setup_test_sol_db()
        
        print(f"🧪 SOLテスト用DB使用 (本番DBへの影響なし)")
        print(f"  test_dir: {test_dir}")
        print(f"  analysis_db: {analysis_db}")
        print(f"  exec_db_path: {exec_db_path}")
        
        # ScalableAnalysisSystemのクエリロジック模擬
        db_path = analysis_db
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # execution_logs.dbアタッチ
        query = "SELECT * FROM analyses WHERE 1=1"
        params = []
        
        if os.path.exists(exec_db_path):
            conn.execute(f"ATTACH DATABASE '{exec_db_path}' AS exec_db")
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
        
        return api_response
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return {"results": [], "error": str(e)}
    
    finally:
        # テスト用DBのクリーンアップ
        if test_dir and os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"🧹 テスト用DB削除: {test_dir}")

if __name__ == "__main__":
    result = test_sol_api()
    print(f"\n🚀 テスト完了: {len(result.get('results', []))}件の結果")