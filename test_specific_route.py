#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import traceback

sys.path.append(str(Path(__file__).parent))

def test_symbols_with_progress_route():
    """Test if symbols-with-progress route works without error"""
    from web_dashboard.app import WebDashboard
    
    try:
        print("Creating WebDashboard instance...")
        dashboard = WebDashboard()
        
        print("Dashboard created successfully")
        
        # Check if the route exists
        routes = [rule.rule for rule in dashboard.app.url_map.iter_rules() if rule.endpoint != 'static']
        print(f"Total routes: {len(routes)}")
        
        if '/api/strategy-results/symbols-with-progress' in routes:
            print("✅ symbols-with-progress route exists")
        else:
            print("❌ symbols-with-progress route missing")
            
        if '/api/strategy-results/<symbol>' in routes:
            print("✅ strategy-results/<symbol> route exists")
        else:
            print("❌ strategy-results/<symbol> route missing")
            
        if '/api/symbol/add' in routes:
            print("✅ symbol/add route exists")
        else:
            print("❌ symbol/add route missing")
            
        # Try to test the actual route call
        print("\nTesting symbols-with-progress endpoint...")
        with dashboard.app.test_client() as client:
            response = client.get('/api/strategy-results/symbols-with-progress')
            print(f"symbols-with-progress response: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_symbols_with_progress_route()