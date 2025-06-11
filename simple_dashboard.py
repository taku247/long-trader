#!/usr/bin/env python3
"""
Simple Web Dashboard for Long Trader (without SocketIO)
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Flask, render_template, jsonify, request
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Import API functions from main dashboard
from web_dashboard.app import WebDashboard

class SimpleDashboard:
    def __init__(self, host='localhost', port=8080, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        
        # Initialize Flask app
        self.app = Flask(__name__, 
                        template_folder='web_dashboard/templates',
                        static_folder='web_dashboard/static')
        self.app.config['SECRET_KEY'] = 'long-trader-simple-dashboard'
        
        # Setup routes
        self._setup_routes()
        
        print(f"Simple dashboard initialized on {host}:{port}")
    
    def _setup_routes(self):
        """Setup basic Flask routes without SocketIO."""
        
        # Import the route setup from WebDashboard but only the API parts
        dashboard = WebDashboard()
        
        # Copy all the API routes
        for rule in dashboard.app.url_map.iter_rules():
            if rule.endpoint.startswith('api_'):
                # Get the function from the original dashboard
                func = dashboard.app.view_functions[rule.endpoint]
                # Add it to our app
                self.app.add_url_rule(rule.rule, rule.endpoint, func, methods=rule.methods)
        
        # Add basic page routes
        @self.app.route('/')
        def index():
            return render_template('dashboard.html')
        
        @self.app.route('/strategy-results')
        def strategy_results_page():
            return render_template('strategy_results.html')
        
        @self.app.route('/symbols')
        def symbols_page():
            return render_template('symbols.html')
        
        @self.app.route('/settings')
        def settings_page():
            return render_template('settings.html')
        
        @self.app.route('/analysis')
        def analysis_page():
            return render_template('analysis.html')
    
    def run(self):
        """Run the simple dashboard."""
        print(f"Starting simple dashboard on http://{self.host}:{self.port}")
        
        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=self.debug,
                threaded=True
            )
        except KeyboardInterrupt:
            print("Dashboard interrupted by user")
        except Exception as e:
            print(f"Dashboard error: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Long Trader Web Dashboard')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    dashboard = SimpleDashboard(host=args.host, port=args.port, debug=args.debug)
    dashboard.run()

if __name__ == '__main__':
    main()