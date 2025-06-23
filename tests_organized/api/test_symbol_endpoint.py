#!/usr/bin/env python3
"""
Test the symbol/add endpoint directly
"""

import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_dashboard.app import WebDashboard

def test_symbol_endpoint():
    """Test if the symbol/add endpoint exists"""
    
    # Create dashboard instance
    dashboard = WebDashboard(host='localhost', port=5003, debug=True)
    
    # Check if the route exists
    with dashboard.app.test_client() as client:
        # Test the endpoint
        response = client.post('/api/symbol/add', 
                              json={'symbol': 'ETH'},
                              content_type='application/json')
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.get_json()}")
        
        # List all routes
        print("\nAll available routes:")
        for rule in dashboard.app.url_map.iter_rules():
            if rule.endpoint != 'static':
                print(f"  {rule.rule} -> {rule.endpoint} ({rule.methods})")

if __name__ == "__main__":
    test_symbol_endpoint()