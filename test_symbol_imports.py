#!/usr/bin/env python3
"""
Test the imports used in the symbol/add endpoint
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("Testing imports used in /api/symbol/add endpoint...")

try:
    import asyncio
    print("✅ asyncio - OK")
except ImportError as e:
    print(f"❌ asyncio - {e}")

try:
    from hyperliquid_validator import HyperliquidValidator, ValidationContext
    print("✅ hyperliquid_validator - OK")
except ImportError as e:
    print(f"❌ hyperliquid_validator - {e}")

try:
    from auto_symbol_training import AutoSymbolTrainer
    print("✅ auto_symbol_training.AutoSymbolTrainer - OK")
except ImportError as e:
    print(f"❌ auto_symbol_training.AutoSymbolTrainer - {e}")

try:
    from datetime import datetime
    import uuid
    print("✅ datetime, uuid - OK")
except ImportError as e:
    print(f"❌ datetime, uuid - {e}")

try:
    import threading
    print("✅ threading - OK")
except ImportError as e:
    print(f"❌ threading - {e}")

print("\nTesting the actual endpoint function...")

try:
    from web_dashboard.app import WebDashboard
    
    # Check if the route registration errors
    dashboard = WebDashboard()
    print("✅ WebDashboard created successfully")
    
    # Check if all routes are registered
    symbol_routes = [rule for rule in dashboard.app.url_map.iter_rules() if 'symbol' in rule.rule]
    print(f"Symbol-related routes found: {[rule.rule for rule in symbol_routes]}")
    
except Exception as e:
    print(f"❌ WebDashboard creation failed: {e}")
    import traceback
    traceback.print_exc()