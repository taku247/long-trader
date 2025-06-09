#!/usr/bin/env python3
"""
Usage examples for the Real-Time Trading Monitor.
"""

import os
import sys
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from real_time_system.monitor import RealTimeMonitor


def show_configuration_example():
    """Show how to configure the monitoring system."""
    print("📋 Configuration Example")
    print("=" * 40)
    
    config_example = {
        "monitoring": {
            "default_interval_minutes": 15,
            "max_parallel_workers": 3,
            "api_rate_limit_delay": 2.0
        },
        "notifications": {
            "discord": {
                "enabled": True,
                "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"
            }
        },
        "alerts": {
            "leverage_threshold": 12.0,
            "confidence_threshold": 75.0,
            "cooldown_minutes": 30
        }
    }
    
    print("Edit real_time_system/config/monitoring_config.json:")
    print(json.dumps(config_example, indent=2))
    print()


def show_watchlist_example():
    """Show how to configure the watchlist."""
    print("📊 Watchlist Configuration Example")
    print("=" * 40)
    
    watchlist_example = {
        "symbols": {
            "CUSTOM_TOKEN": {
                "enabled": True,
                "timeframes": ["15m", "1h"],
                "strategies": ["Conservative_ML", "Full_ML"],
                "min_leverage": 8.0,
                "min_confidence": 70.0,
                "position_size_limit": 1000.0,
                "priority": "high"
            }
        }
    }
    
    print("Edit real_time_system/config/watchlist.json:")
    print(json.dumps(watchlist_example, indent=2))
    print()


def show_command_examples():
    """Show command line usage examples."""
    print("💻 Command Line Examples")
    print("=" * 40)
    
    examples = [
        ("Basic monitoring with default settings:", 
         "python real_time_system/monitor.py"),
        
        ("Monitor specific symbols with custom interval:", 
         "python real_time_system/monitor.py --symbols HYPE,SOL,WIF --interval 10"),
        
        ("Test all system components:", 
         "python real_time_system/monitor.py --test"),
        
        ("Check current system status:", 
         "python real_time_system/monitor.py --status"),
        
        ("Use custom configuration file:", 
         "python real_time_system/monitor.py --config /path/to/custom_config.json"),
        
        ("Run demo (short test run):", 
         "python demo_monitor.py")
    ]
    
    for description, command in examples:
        print(f"• {description}")
        print(f"  {command}")
        print()


def show_discord_setup():
    """Show how to set up Discord notifications."""
    print("🔔 Discord Webhook Setup")
    print("=" * 40)
    
    steps = [
        "1. Go to your Discord server settings",
        "2. Navigate to 'Integrations' > 'Webhooks'",
        "3. Click 'Create Webhook'",
        "4. Set a name (e.g., 'Trading Bot')",
        "5. Choose the channel for notifications",
        "6. Copy the webhook URL",
        "7. Update monitoring_config.json:",
        "   \"webhook_url\": \"YOUR_COPIED_URL\"",
        "8. Set \"enabled\": true in Discord config"
    ]
    
    for step in steps:
        print(f"  {step}")
    print()
    
    print("⚠️  Important: Keep your webhook URL secret!")
    print()


def show_advanced_usage():
    """Show advanced usage patterns."""
    print("🚀 Advanced Usage")
    print("=" * 40)
    
    print("• Programmatic Usage:")
    code_example = '''
from real_time_system.monitor import RealTimeMonitor

# Initialize monitor
monitor = RealTimeMonitor()

# Start monitoring
monitor.start(symbols=['HYPE', 'SOL'], interval_minutes=5)

# Later, check status
status = monitor.get_status()
print(f"Monitored symbols: {status['monitored_symbols']}")

# Stop when done
monitor.stop()
'''
    print(code_example)
    
    print("• Custom Alert Handling:")
    alert_example = '''
from real_time_system.alert_manager import AlertManager, AlertType

# Get alert history
history = alert_manager.get_alert_history(
    limit=10, 
    alert_type=AlertType.TRADING_OPPORTUNITY,
    symbol='HYPE'
)

# Get statistics
stats = alert_manager.get_statistics()
print(f"Alerts in last 24h: {stats['alerts_last_24h']}")
'''
    print(alert_example)


def main():
    """Show all examples."""
    print("🎯 Real-Time Trading Monitor - Usage Guide")
    print("=" * 50)
    print()
    
    show_command_examples()
    show_configuration_example()
    show_watchlist_example()
    show_discord_setup()
    show_advanced_usage()
    
    print("📚 For more information:")
    print("  • Read real_time_system/README.md")
    print("  • Check configuration files in real_time_system/config/")
    print("  • Run tests: python real_time_system/monitor.py --test")
    print()
    print("🏁 Happy trading!")


if __name__ == "__main__":
    main()