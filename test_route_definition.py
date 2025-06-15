#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import traceback

sys.path.append(str(Path(__file__).parent))

from flask import Flask
from real_time_system.utils.colored_log import get_colored_logger

class TestRouteSetup:
    def __init__(self):
        self.app = Flask(__name__)
        self.logger = get_colored_logger(__name__)
        
        try:
            print("Testing route definition that causes issues...")
            
            # This is the exact route definition from app.py line 622-692
            @self.app.route('/api/strategy-results/symbols-with-progress')
            def api_strategy_results_symbols_with_progress():
                """Get all symbols with their analysis progress with failure detection."""
                try:
                    from scalable_analysis_system import ScalableAnalysisSystem
                    from execution_log_database import ExecutionLogDatabase
                    from datetime import datetime, timedelta
                    system = ScalableAnalysisSystem()
                    exec_db = ExecutionLogDatabase()
                    
                    # Get all symbols with their progress (18 = 3 strategies × 6 timeframes)
                    query = """
                        SELECT symbol, COUNT(*) as completed_patterns, AVG(sharpe_ratio) as avg_sharpe,
                               MAX(generated_at) as latest_completion
                        FROM analyses 
                        WHERE status='completed' 
                        GROUP BY symbol 
                        ORDER BY completed_patterns DESC, avg_sharpe DESC
                    """
                    
                    import sqlite3
                    with sqlite3.connect(system.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute(query)
                        results = cursor.fetchall()
                        
                        symbols = []
                        for row in results:
                            symbol, completed, avg_sharpe, latest_completion = row
                            completion_rate = (completed / 18) * 100
                            
                            # Check execution status for failure detection
                            try:
                                execution_status, failure_info = self._check_symbol_execution_status(
                                    exec_db, symbol, completed, latest_completion
                                )
                            except Exception as check_error:
                                self.logger.warning(f"Error checking execution status for {symbol}: {check_error}")
                                execution_status, failure_info = 'unknown', None
                            
                            # rest of code omitted for brevity
                            symbols.append({'symbol': symbol, 'status': 'test'})
                        
                        return symbols
                    
                except Exception as e:
                    self.logger.error(f"Error getting symbols with progress: {e}")
                    return []
            
            print("✅ symbols-with-progress route defined successfully")
            
            # Test the problematic _check_symbol_execution_status method
            print("Testing _check_symbol_execution_status method definition...")
            
            def _check_symbol_execution_status(self, exec_db, symbol, completed_patterns, latest_completion):
                """Check if symbol analysis has failed or stalled."""
                try:
                    from datetime import datetime, timedelta
                    
                    # Get recent executions for this symbol
                    executions = exec_db.list_executions(limit=50)
                    symbol_executions = [e for e in executions if e.get('symbol') == symbol]
                    
                    if not symbol_executions:
                        return 'unknown', None
                    
                    return 'normal', None
                    
                except Exception as e:
                    self.logger.error(f"Error checking execution status for {symbol}: {e}")
                    return 'unknown', None
            
            # Bind the method to self
            self._check_symbol_execution_status = _check_symbol_execution_status.__get__(self, TestRouteSetup)
            
            print("✅ _check_symbol_execution_status method defined successfully")
            
            # Now try to define the next route
            @self.app.route('/api/strategy-results/<symbol>')
            def api_strategy_results_detail(symbol):
                """Get detailed strategy results for a symbol."""
                return {'symbol': symbol}
            
            print("✅ strategy-results/<symbol> route defined successfully")
            
            @self.app.route('/api/symbol/add', methods=['POST'])
            def api_symbol_add():
                """Add new symbol."""
                return {'status': 'ok'}
            
            print("✅ symbol/add route defined successfully")
            
        except Exception as e:
            print(f"❌ Error during route setup: {e}")
            traceback.print_exc()
        
        # Count routes
        routes = [rule.rule for rule in self.app.url_map.iter_rules() if rule.endpoint != 'static']
        print(f"\nTotal routes registered: {len(routes)}")
        for route in routes:
            print(f"  {route}")

if __name__ == "__main__":
    test = TestRouteSetup()