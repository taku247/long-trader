#!/usr/bin/env python3
"""
最小限のWebサーバー - SOL APIテスト用
"""
import sys
import os
from pathlib import Path
import sqlite3
import json

sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/strategy-results/<symbol>')
def api_strategy_results_detail(symbol):
    """Get detailed strategy results for a symbol."""
    try:
        print(f"📊 戦略結果API呼び出し: {symbol}")
        
        # データベース直接アクセス
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(parent_dir, "large_scale_analysis", "analysis.db")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # execution_logs.dbアタッチ
        exec_db_path = os.path.join(parent_dir, "execution_logs.db")
        query = "SELECT * FROM analyses WHERE 1=1"
        params = []
        
        if os.path.exists(exec_db_path):
            conn.execute(f"ATTACH DATABASE '{exec_db_path}' AS exec_db")
            
            # manual_レコード数確認
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE execution_id LIKE 'manual_%'")
            manual_count = cursor.fetchone()[0]
            print(f"   manual_レコード数: {manual_count}")
            
            if manual_count > 0:
                print("   フォールバッククエリ使用")
                query = "SELECT * FROM analyses WHERE 1=1"
        
        # フィルター追加
        query += " AND symbol = ?"
        params.append(symbol)
        query += " ORDER BY sharpe_ratio DESC LIMIT 50"
        
        cursor.execute(query, params)
        
        # カラム名取得
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        print(f"   取得結果: {len(results)}件")
        
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
        
        response = {
            'symbol': symbol,
            'results': formatted_results,
            'total_patterns': len(formatted_results)
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"   エラー: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategy-results/<symbol>/<timeframe>/<config>/trades')
def api_strategy_trade_details(symbol, timeframe, config):
    """Get detailed trade data for specific strategy."""
    try:
        print(f"📊 トレード詳細API呼び出し: {symbol}/{timeframe}/{config}")
        
        # データベースからcompressed_pathを取得
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(parent_dir, "large_scale_analysis", "analysis.db")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT compressed_path FROM analyses WHERE symbol=? AND timeframe=? AND config=?",
            (symbol, timeframe, config)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            print(f"   ❌ レコードが見つかりません")
            return jsonify({'error': f'No analysis found for {symbol} {timeframe} {config}'}), 404
        
        compressed_path = result[0]
        print(f"   compressed_path: {compressed_path}")
        
        # 実際のファイル確認
        full_path = os.path.join(parent_dir, "web_dashboard", "large_scale_analysis", compressed_path)
        if not os.path.exists(full_path):
            print(f"   ❌ ファイルが見つかりません: {full_path}")
            return jsonify({'error': f'Compressed file not found: {compressed_path}'}), 404
        
        print(f"   ✅ ファイル確認: {full_path}")
        
        # numpy依存の問題のため、ダミーデータを返す
        print(f"   🔄 ダミーデータ生成中...")
        
        dummy_trades = []
        for i in range(8):  # 8トレードのダミーデータ
            trade = {
                'entry_time': f'2025-03-{20+i} 1{i}:30:00',
                'exit_time': f'2025-03-{20+i} 1{i}:45:00',
                'entry_price': 100.0 + i * 2.5,
                'exit_price': 102.0 + i * 2.8,
                'leverage': 5.0,
                'pnl_pct': 0.02 + i * 0.001,
                'is_success': i % 3 != 0,
                'confidence': 0.75 + i * 0.02,
                'strategy': config
            }
            dummy_trades.append(trade)
        
        print(f"   ✅ {len(dummy_trades)}件のダミートレード生成")
        
        return jsonify(dummy_trades)
        
    except Exception as e:
        print(f"   エラー: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test')
def test_endpoint():
    """テスト用エンドポイント"""
    return jsonify({'status': 'ok', 'message': 'Test server is running'})

if __name__ == '__main__':
    print("🚀 Minimal test server starting on http://localhost:5004")
    print("   Available endpoints:")
    print("   - /api/strategy-results/SOL")
    print("   - /api/strategy-results/SOL/30m/Aggressive_Traditional/trades")
    print("   - /test")
    app.run(host='localhost', port=5004, debug=False)