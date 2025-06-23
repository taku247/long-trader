#!/usr/bin/env python3
"""
シンプルなテストサーバー - SQL修正確認用
"""
import sys
import os
from pathlib import Path

# 親ディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

@app.route('/api/strategy-results/<symbol>')
def get_strategy_results(symbol):
    """戦略分析結果取得（SQL修正テスト）"""
    try:
        # 修正されたSQL: JOINなしでシンプルクエリ
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(parent_dir, "large_scale_analysis", "analysis.db")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 修正されたクエリ（エイリアスなし）
        query = "SELECT symbol, timeframe, config, sharpe_ratio, win_rate, total_return FROM analyses WHERE symbol = ? ORDER BY sharpe_ratio DESC"
        cursor.execute(query, (symbol,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'symbol': row[0],
                'timeframe': row[1], 
                'config': row[2],
                'sharpe_ratio': row[3],
                'win_rate': row[4],
                'total_return': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'results': results,
            'count': len(results),
            'symbol': symbol
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Simple test server starting on http://localhost:5002")
    app.run(host='localhost', port=5002, debug=True)