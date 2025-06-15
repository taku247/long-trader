#!/usr/bin/env python3
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from flask import Flask, render_template, jsonify, request
import logging
from real_time_system.utils.colored_log import get_colored_logger

class TestWebDashboard:
    def __init__(self):
        self.app = Flask(__name__, 
                        template_folder='web_dashboard/templates',
                        static_folder='web_dashboard/static')
        self.logger = get_colored_logger(__name__)
        
        # Setup routes step by step to find where it fails
        self._setup_routes_with_debug()
        
    def _setup_routes_with_debug(self):
        """Setup Flask routes with debug info."""
        
        try:
            print("Setting up basic routes...")
            
            @self.app.route('/')
            def index():
                return render_template('dashboard.html')
            
            @self.app.route('/api/status')
            def api_status():
                return jsonify({'status': 'ok'})
            
            print("Basic routes OK")
            
            print("Setting up strategy results routes...")
            
            @self.app.route('/strategy-results')
            def strategy_results_page():
                return render_template('strategy_results.html')
            
            @self.app.route('/api/strategy-results/symbols')
            def api_strategy_results_symbols():
                return jsonify([])
            
            @self.app.route('/api/strategy-results/symbols-with-progress')
            def api_strategy_results_symbols_with_progress():
                return jsonify([])
            
            print("Strategy results basic routes OK")
            
            print("Setting up problematic route: /api/strategy-results/<symbol>")
            
            @self.app.route('/api/strategy-results/<symbol>')
            def api_strategy_results_detail(symbol):
                """Get detailed strategy results for a symbol."""
                try:
                    from scalable_analysis_system import ScalableAnalysisSystem
                    system = ScalableAnalysisSystem()
                    
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
                            'total_trades': int(row['total_trades']) if row['total_trades'] else 0,
                            'generated_at': row['generated_at']
                        })
                    
                    return jsonify({
                        'symbol': symbol,
                        'results': results,
                        'total_patterns': len(results)
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error getting strategy results for {symbol}: {e}")
                    return jsonify({'error': str(e)}), 500
            
            print("Strategy results detail route OK")
            
            print("Setting up symbol management routes...")
            
            @self.app.route('/api/symbol/add', methods=['POST'])
            def api_symbol_add():
                """Add new symbol with automatic training and backtesting."""
                return jsonify({'status': 'ok'})
            
            print("Symbol add route OK")
            
            @self.app.route('/api/execution/<execution_id>/status')
            def api_execution_status(execution_id):
                """Get execution status for training/backtesting."""
                return jsonify({'status': 'ok'})
            
            print("Execution status route OK")
            
            @self.app.route('/api/executions')
            def api_executions_list():
                """Get list of recent executions."""
                return jsonify([])
            
            print("Executions list route OK")
            
            print("All routes setup successfully!")
            
        except Exception as e:
            print(f"Error during route setup: {e}")
            import traceback
            traceback.print_exc()

# Test the route setup
dashboard = TestWebDashboard()
print(f"\nTotal routes registered: {len([r for r in dashboard.app.url_map.iter_rules() if r.endpoint != 'static'])}")

# List all routes
print("\nAll registered routes:")
for rule in dashboard.app.url_map.iter_rules():
    if rule.endpoint != 'static':
        print(f"  {rule.rule} -> {rule.endpoint}")