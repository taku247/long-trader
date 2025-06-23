#!/usr/bin/env python3
"""
SOL APIの直接テスト（依存関係なし）
"""
import sqlite3
import json
import os

def test_sol_api():
    """SOL API模擬テスト"""
    symbol = "SOL"
    
    try:
        # ScalableAnalysisSystemのクエリロジック模擬
        db_path = 'large_scale_analysis/analysis.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # execution_logs.dbアタッチ
        exec_db_path = 'execution_logs.db'
        query = "SELECT * FROM analyses WHERE 1=1"
        params = []
        
        if os.path.exists(exec_db_path):
            conn.execute(f"ATTACH DATABASE '{exec_db_path}' AS exec_db")
            
            # manual_レコード数確認
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE execution_id LIKE 'manual_%'")
            manual_count = cursor.fetchone()[0]
            
            if manual_count > 0:
                # フォールバック: シンプルクエリ
                query = "SELECT * FROM analyses WHERE 1=1"
            else:
                # JOINクエリ
                query = """
                    SELECT a.* FROM analyses a
                    INNER JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                    WHERE e.status = 'SUCCESS' AND a.execution_id IS NOT NULL
                """
        
        # フィルター追加
        query += " AND symbol = ?"
        params.append(symbol)
        query += " ORDER BY sharpe_ratio DESC"
        
        cursor.execute(query, params)
        
        # カラム名取得
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        # 辞書形式に変換
        formatted_results = []
        for row in results:
            row_dict = dict(zip(columns, row))
            formatted_results.append({
                'symbol': row_dict['symbol'],
                'timeframe': row_dict['timeframe'],
                'config': row_dict['config'],
                'sharpe_ratio': float(row_dict['sharpe_ratio']) if row_dict['sharpe_ratio'] else 0,
                'win_rate': float(row_dict['win_rate']) if row_dict['win_rate'] else 0,
                'total_return': float(row_dict['total_return']) if row_dict['total_return'] else 0,
                'max_drawdown': float(row_dict['max_drawdown']) if row_dict['max_drawdown'] else 0,
                'avg_leverage': float(row_dict['avg_leverage']) if row_dict['avg_leverage'] else 0,
                'total_trades': int(row_dict['total_trades']) if row_dict['total_trades'] else 0
            })
        
        conn.close()
        
        # API形式レスポンス
        response = {
            'symbol': symbol,
            'results': formatted_results,
            'total_patterns': len(formatted_results)
        }
        
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return response
        
    except Exception as e:
        error_response = {'error': str(e)}
        print(json.dumps(error_response, indent=2))
        return error_response

if __name__ == '__main__':
    print("🧪 SOL API直接テスト実行...")
    test_sol_api()