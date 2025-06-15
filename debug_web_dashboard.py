#!/usr/bin/env python3
"""
Debug version of WebDashboard to isolate the route registration issue
"""

import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask

class DebugWebDashboard:
    def __init__(self):
        self.app = Flask(__name__)
        print("🔍 Starting route setup debug...")
        self._debug_setup_routes()
        print("✅ Route setup completed")
        
    def _debug_setup_routes(self):
        """Debug version of route setup"""
        
        print("📝 Setting up basic routes...")
        
        @self.app.route('/')
        def index():
            return "Dashboard"
        
        print("✅ Basic routes OK")
        print("📝 Setting up symbol routes...")
        
        try:
            # Test the symbol/add route specifically
            @self.app.route('/api/symbol/add', methods=['POST'])
            def api_symbol_add():
                """Add new symbol with automatic training and backtesting."""
                try:
                    from flask import request, jsonify
                    data = request.get_json()
                    if not data or 'symbol' not in data:
                        return jsonify({'error': 'Symbol is required'}), 400
                    
                    symbol = data['symbol'].upper().strip()
                    
                    if not symbol:
                        return jsonify({'error': 'Invalid symbol'}), 400
                    
                    print(f"📋 Testing imports for symbol: {symbol}")
                    
                    # Test each import individually
                    try:
                        import asyncio
                        print("  ✅ asyncio OK")
                    except Exception as e:
                        print(f"  ❌ asyncio failed: {e}")
                        raise
                    
                    try:
                        from hyperliquid_validator import HyperliquidValidator, ValidationContext
                        print("  ✅ hyperliquid_validator OK")
                    except Exception as e:
                        print(f"  ❌ hyperliquid_validator failed: {e}")
                        raise
                    
                    try:
                        from auto_symbol_training import AutoSymbolTrainer
                        print("  ✅ auto_symbol_training OK")
                    except Exception as e:
                        print(f"  ❌ auto_symbol_training failed: {e}")
                        raise
                    
                    try:
                        from datetime import datetime
                        import uuid
                        print("  ✅ datetime, uuid OK")
                    except Exception as e:
                        print(f"  ❌ datetime, uuid failed: {e}")
                        raise
                    
                    try:
                        import threading
                        print("  ✅ threading OK")
                    except Exception as e:
                        print(f"  ❌ threading failed: {e}")
                        raise
                    
                    # If we get here, all imports worked
                    return jsonify({'status': 'success', 'symbol': symbol, 'message': 'Debug test passed'})
                    
                except Exception as e:
                    print(f"❌ Error in api_symbol_add: {e}")
                    from flask import jsonify
                    return jsonify({'error': str(e)}), 500
            
            print("✅ Symbol/add route registered successfully")
            
        except Exception as e:
            print(f"❌ Failed to register symbol/add route: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        try:
            @self.app.route('/api/symbol/retry', methods=['POST'])
            def api_symbol_retry():
                """Retry failed or stalled symbol analysis."""
                from flask import request, jsonify
                return jsonify({'status': 'retry endpoint working'})
            
            print("✅ Symbol/retry route registered successfully")
            
        except Exception as e:
            print(f"❌ Failed to register symbol/retry route: {e}")
            import traceback
            traceback.print_exc()
            raise

def test_debug_dashboard():
    """Test the debug dashboard"""
    print("🔍 Testing debug dashboard...")
    
    try:
        dashboard = DebugWebDashboard()
        
        print("\n📋 All registered routes:")
        for rule in dashboard.app.url_map.iter_rules():
            if rule.endpoint != 'static':
                print(f"  {rule.rule} -> {rule.endpoint} ({rule.methods})")
        
        # Test the symbol/add endpoint
        print("\n🧪 Testing symbol/add endpoint...")
        with dashboard.app.test_client() as client:
            response = client.post('/api/symbol/add', 
                                  json={'symbol': 'ETH'},
                                  content_type='application/json')
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.get_json()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug dashboard failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_debug_dashboard()