#!/usr/bin/env python3
"""
Test script for the Web Dashboard functionality.
Performs basic integration tests.
"""

import sys
import os
import time
import requests
import threading
from pathlib import Path

# Add paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_dashboard.app import WebDashboard
from real_time_system.utils.colored_log import get_colored_logger


def test_dashboard_startup():
    """Test that dashboard starts up correctly."""
    logger = get_colored_logger("test_dashboard")
    
    logger.info("Testing web dashboard startup...")
    
    # Test basic instantiation
    try:
        dashboard = WebDashboard(host='localhost', port=5001, debug=False)
        logger.success("✅ Dashboard instance created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Dashboard instantiation failed: {e}")
        return False


def test_api_endpoints():
    """Test that API endpoints are accessible."""
    logger = get_colored_logger("test_api")
    
    # Start dashboard in background
    dashboard = WebDashboard(host='localhost', port=5001, debug=False)
    
    def run_dashboard():
        try:
            dashboard.socketio.run(
                dashboard.app,
                host='localhost',
                port=5001,
                debug=False,
                allow_unsafe_werkzeug=True
            )
        except Exception as e:
            logger.error(f"Dashboard run error: {e}")
    
    server_thread = threading.Thread(target=run_dashboard, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(3)
    
    base_url = "http://localhost:5001"
    test_results = {}
    
    # Test endpoints
    endpoints = {
        "Main page": "/",
        "Status API": "/api/status",
        "Statistics API": "/api/statistics",
        "Config API": "/api/config",
        "Alerts API": "/api/alerts"
    }
    
    for name, endpoint in endpoints.items():
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                logger.success(f"✅ {name}: {response.status_code}")
                test_results[name] = True
            else:
                logger.warning(f"⚠️ {name}: {response.status_code}")
                test_results[name] = False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ {name}: Connection failed - {e}")
            test_results[name] = False
    
    return test_results


def test_file_structure():
    """Test that all required files exist."""
    logger = get_colored_logger("test_files")
    
    logger.info("Testing file structure...")
    
    required_files = [
        "web_dashboard/app.py",
        "web_dashboard/templates/dashboard.html",
        "web_dashboard/static/css/dashboard.css",
        "web_dashboard/static/js/dashboard.js",
        "demo_dashboard.py"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            logger.success(f"✅ {file_path}")
        else:
            logger.error(f"❌ {file_path} - Missing")
            missing_files.append(file_path)
    
    return len(missing_files) == 0


def main():
    """Run all tests."""
    logger = get_colored_logger("test_main")
    
    logger.info("🧪 Starting Web Dashboard Integration Tests")
    print()
    
    tests = [
        ("File Structure", test_file_structure),
        ("Dashboard Startup", test_dashboard_startup),
        ("API Endpoints", test_api_endpoints),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"Running {test_name} test...")
        try:
            result = test_func()
            if isinstance(result, dict):
                # Multiple results
                all_passed = all(result.values())
                results[test_name] = all_passed
                if all_passed:
                    logger.success(f"✅ {test_name}: All checks passed")
                else:
                    failed_checks = [k for k, v in result.items() if not v]
                    logger.warning(f"⚠️ {test_name}: Failed checks: {', '.join(failed_checks)}")
            else:
                # Single result
                results[test_name] = result
                if result:
                    logger.success(f"✅ {test_name}: Passed")
                else:
                    logger.error(f"❌ {test_name}: Failed")
        except Exception as e:
            logger.error(f"❌ {test_name}: Exception - {e}")
            results[test_name] = False
        
        print()
    
    # Summary
    passed = sum(results.values())
    total = len(results)
    
    logger.info("📊 Test Summary:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print()
    if passed == total:
        logger.success(f"🎉 All tests passed! ({passed}/{total})")
        logger.info("🚀 Web Dashboard is ready for use!")
        logger.info("🌐 Start with: python demo_dashboard.py")
    else:
        logger.warning(f"⚠️ {passed}/{total} tests passed")
        logger.info("🔧 Please check failed tests before using")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)