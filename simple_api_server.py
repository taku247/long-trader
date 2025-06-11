#!/usr/bin/env python3
"""
Simple API Server for Trade Details (without SocketIO)
"""
import sys
import json
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, render_template

sys.path.append('.')
from scalable_analysis_system import ScalableAnalysisSystem

app = Flask(__name__, 
           template_folder='web_dashboard/templates',
           static_folder='web_dashboard/static')

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/strategy-results')
def strategy_results_page():
    return render_template('strategy_results.html')

@app.route('/symbols')
def symbols_page():
    return render_template('symbols.html')

@app.route('/settings')
def settings_page():
    return render_template('settings.html')

@app.route('/analysis')
def analysis_page():
    return render_template('analysis.html')

@app.route('/api/strategy-results/symbols')
def api_strategy_results_symbols():
    """Get symbols that have completed analysis."""
    try:
        system = ScalableAnalysisSystem()
        
        query = """
            SELECT symbol, COUNT(*) as pattern_count, AVG(sharpe_ratio) as avg_sharpe
            FROM analyses 
            WHERE status='completed' 
            GROUP BY symbol 
            HAVING pattern_count >= 18
            ORDER BY avg_sharpe DESC
        """
        
        with sqlite3.connect(system.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            symbols = [
                {
                    'symbol': row[0],
                    'pattern_count': row[1],
                    'avg_sharpe': round(row[2], 2) if row[2] else 0
                }
                for row in results
            ]
            
        return jsonify(symbols)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategy-results/<symbol>')
def api_strategy_results_detail(symbol):
    """Get detailed strategy results for a symbol."""
    try:
        system = ScalableAnalysisSystem()
        
        filters = {'symbol': symbol}
        results_df = system.query_analyses(filters=filters, limit=50)
        
        if results_df.empty:
            return jsonify({'results': []})
        
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
                'total_trades': int(row['total_trades']) if row['total_trades'] else 0,
                'generated_at': row['generated_at']
            })
        
        return jsonify({
            'symbol': symbol,
            'results': results,
            'total_patterns': len(results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategy-results/<symbol>/<timeframe>/<config>/trades')
def api_strategy_trade_details(symbol, timeframe, config):
    """Get detailed trade data for specific strategy."""
    try:
        system = ScalableAnalysisSystem()
        
        trades_data = system.load_compressed_trades(symbol, timeframe, config)
        
        if not trades_data:
            return jsonify([])
        
        # Format trade details with enhanced information
        formatted_trades = []
        for trade in trades_data:
            entry_price = trade.get('entry_price')
            exit_price = trade.get('exit_price')
            leverage = float(trade.get('leverage', 0))
            
            # Calculate take profit and stop loss based on strategy
            take_profit_price = None
            stop_loss_price = None
            
            if entry_price is not None:
                entry_price = float(entry_price)
                
                # Strategy-based TP/SL calculation
                if 'Conservative' in config:
                    tp_pct = 0.02 * leverage  # 2% * leverage
                    sl_pct = 0.01 * leverage  # 1% * leverage
                elif 'Aggressive' in config:
                    tp_pct = 0.03 * leverage  # 3% * leverage
                    sl_pct = 0.015 * leverage  # 1.5% * leverage
                else:  # Full_ML
                    tp_pct = 0.025 * leverage  # 2.5% * leverage
                    sl_pct = 0.012 * leverage  # 1.2% * leverage
                
                take_profit_price = entry_price * (1 + tp_pct)
                stop_loss_price = entry_price * (1 - sl_pct)
            
            formatted_trade = {
                'entry_time': trade.get('entry_time', 'N/A'),
                'exit_time': trade.get('exit_time', 'N/A'),
                'entry_price': entry_price,
                'exit_price': float(exit_price) if exit_price is not None else None,
                'take_profit_price': take_profit_price,
                'stop_loss_price': stop_loss_price,
                'leverage': leverage,
                'pnl_pct': float(trade.get('pnl_pct', 0)),
                'is_success': bool(trade.get('is_success', trade.get('is_win', False))),
                'confidence': float(trade.get('confidence', 0)),
                'strategy': trade.get('strategy', config)
            }
            formatted_trades.append(formatted_trade)
        
        return jsonify(formatted_trades)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple API Server')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting simple API server on http://localhost:{args.port}")
    app.run(host='localhost', port=args.port, debug=False, threaded=True)