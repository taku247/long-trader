#!/usr/bin/env python3
"""
Demo script for the Web Dashboard.
Starts the dashboard with demo configuration.
"""

import sys
import os
from pathlib import Path

# Add paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_dashboard.app import WebDashboard
from real_time_system.utils.colored_log import (
    print_banner, print_success, print_info, print_warning, 
    get_colored_logger
)


def main():
    """Run the web dashboard demo."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Long Trader Web Dashboard Demo')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5001, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', default=True, help='Enable debug mode')
    
    args = parser.parse_args()
    
    logger = get_colored_logger("demo_dashboard")
    
    print_banner("WEB DASHBOARD DEMO", "Long Trader Real-Time Monitoring Dashboard")
    logger.system_start("Demo dashboard mode activated")
    
    print_info("Demo Configuration:")
    print(f"  • Host: {args.host}")
    print(f"  • Port: {args.port}")
    print("  • Debug mode: Enabled")
    print("  • Real-time monitoring: Available")
    print("  • WebSocket updates: Enabled")
    print()
    
    print_info("Access the dashboard:")
    print(f"  🌐 URL: http://{args.host}:{args.port}")
    print("  📊 Features: Status monitoring, Alert history, Real-time updates")
    print()
    
    try:
        # Initialize and run dashboard
        dashboard = WebDashboard(host=args.host, port=args.port, debug=args.debug)
        
        print_success("Starting web dashboard...")
        print_warning("Press Ctrl+C to stop the server")
        print()
        
        dashboard.run()
        
    except KeyboardInterrupt:
        logger.warning("Dashboard demo interrupted by user")
    except Exception as e:
        logger.error(f"Dashboard demo error: {e}")
    finally:
        logger.system_stop("Demo dashboard session ended")


if __name__ == "__main__":
    main()