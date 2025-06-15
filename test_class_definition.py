#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import traceback

sys.path.append(str(Path(__file__).parent))

try:
    # Import and test class definition
    from web_dashboard.app import WebDashboard
    print("✅ WebDashboard class imported successfully")
    
    # Test class instantiation
    dashboard = WebDashboard()
    print("✅ WebDashboard instance created successfully")
    
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc()