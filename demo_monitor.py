#!/usr/bin/env python3
"""
Demo script for the real-time monitoring system.
Runs for a short period to demonstrate functionality.
"""

import sys
import os
import time
import threading
from datetime import datetime

# Add paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from real_time_system.monitor import RealTimeMonitor
from real_time_system.utils.colored_log import (
    print_banner, print_success, print_info, print_warning, 
    print_system_status, get_colored_logger
)
from colorama import Fore, Style


def demo_monitor():
    """Run a demo of the monitoring system."""
    
    # Initialize colored logger for demo
    logger = get_colored_logger("demo_monitor")
    
    print_banner("DEMO MONITOR", "Real-Time Trading Opportunity Detection Demo")
    logger.system_start("Demo mode activated")
    
    # Initialize monitor
    monitor = RealTimeMonitor()
    
    # Set shorter intervals for demo
    demo_config = {
        "monitoring": {"default_interval_minutes": 1},
        "notifications": {
            "discord": {"enabled": False},
            "console": {"enabled": True}
        },
        "alerts": {
            "leverage_threshold": 5.0,  # Lower threshold for more alerts in demo
            "confidence_threshold": 60.0
        }
    }
    
    # Override config for demo
    monitor.config.update(demo_config)
    monitor.alert_manager.config.update(demo_config)
    monitor.alert_manager.leverage_threshold = 5.0
    monitor.alert_manager.confidence_threshold = 60.0
    
    print_info("Demo Configuration:")
    print(f"  {Fore.CYAN}• Monitoring interval: 1 minute")
    print(f"  • Symbols: HYPE, SOL")
    print(f"  • Leverage threshold: 5.0x")
    print(f"  • Confidence threshold: 60%")
    print(f"  • Discord notifications: Disabled{Style.RESET_ALL}")
    print()
    
    # Create stop event
    stop_event = threading.Event()
    
    def run_monitor():
        try:
            monitor.start(symbols=['HYPE', 'SOL'], interval_minutes=1)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
        finally:
            stop_event.set()
    
    # Start monitor in separate thread
    monitor_thread = threading.Thread(target=run_monitor, daemon=True)
    monitor_thread.start()
    
    # Run for demo duration
    demo_duration = 20  # 20 seconds
    logger.info(f"Running demo for {demo_duration} seconds...")
    print_info("Watch for trading opportunity alerts!")
    print()
    
    start_time = time.time()
    try:
        while time.time() - start_time < demo_duration and not stop_event.is_set():
            time.sleep(1)
            
            # Show progress
            elapsed = int(time.time() - start_time)
            remaining = demo_duration - elapsed
            if elapsed % 5 == 0 and elapsed > 0:  # Every 5 seconds
                logger.progress(f"Demo running", elapsed, demo_duration)
    
    except KeyboardInterrupt:
        logger.warning("Demo interrupted by user")
    
    # Stop monitor
    logger.warning("Stopping monitor...")
    monitor.stop()
    
    # Show final status
    logger.info("Final Demo Status:")
    status = monitor.get_status()
    uptime = status.get('uptime_seconds', 0)
    symbols_count = len(status.get('monitored_symbols', []))
    
    print(f"  {Fore.GREEN}• Uptime: {uptime:.1f} seconds")
    print(f"  • Monitored symbols: {symbols_count}")
    
    alert_stats = status.get('alert_stats', {})
    total_alerts = alert_stats.get('total_alerts', 0)
    alerts_by_type = alert_stats.get('by_type', {})
    
    print(f"  • Total alerts: {total_alerts}")
    print(f"  • Alerts by type: {alerts_by_type}{Style.RESET_ALL}")
    
    print_success("Demo completed successfully!")
    
    print_info("Next Steps:")
    print(f"  {Fore.CYAN}• Run full system: python real_time_system/monitor.py")
    print(f"  • Test components: python real_time_system/monitor.py --test{Style.RESET_ALL}")
    
    logger.system_stop("Demo session ended")


if __name__ == "__main__":
    demo_monitor()