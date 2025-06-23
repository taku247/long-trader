#!/usr/bin/env python3
"""
APIテスト用シンプルサーバー
"""
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, jsonify
from scalable_analysis_system import ScalableAnalysisSystem

app = Flask(__name__)

@app.route('/api/strategy-results/<symbol>')
def api_strategy_results_detail(symbol):
    """Get detailed strategy results for a symbol."""
    try:
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        system = ScalableAnalysisSystem(base_dir=os.path.join(parent_dir, "large_scale_analysis"))
        
        # Query all analyses for the symbol
        filters = {'symbol': symbol}
        results_df = system.query_analyses(filters=filters, limit=50)
        
        if results_df.empty:
            return jsonify({'results': []})
        
        # Convert to list of dictionaries
        results = []
        for _, row in results_df.iterrows():
            results.append({
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'config': row['config'],
                'sharpe_ratio': float(row['sharpe_ratio']) if row['sharpe_ratio'] else 0,
                'win_rate': float(row['win_rate']) if row['win_rate'] else 0,
                'total_return': float(row['total_return']) if row['total_return'] else 0,
                'max_drawdown': float(row['max_drawdown']) if row['max_drawdown'] else 0,
                'avg_leverage': float(row['avg_leverage']) if row['avg_leverage'] else 0,
                'total_trades': int(row['total_trades']) if row['total_trades'] else 0
            })
        
        return jsonify({
            'symbol': symbol,
            'results': results,
            'total_patterns': len(results)
        })
        
    except Exception as e:
        print(f"Error getting strategy results for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 API test server starting on http://localhost:5003")
    app.run(host='localhost', port=5003, debug=False)