#!/usr/bin/env python3
"""
Real-time monitoring system for high-leverage trading opportunities.
Phase 1: Automated monitoring and alerting system.
"""

import os
import sys
import json
import argparse
import logging
import signal
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add parent directory to path to import existing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
except ImportError:
    print("Warning: Could not import HighLeverageBotOrchestrator, using mock")
    try:
        from mock_high_leverage_bot import MockHighLeverageBotOrchestrator as HighLeverageBotOrchestrator
    except ImportError:
        print("Warning: Could not import mock bot either")
        HighLeverageBotOrchestrator = None

from real_time_system.alert_manager import AlertManager, AlertType, AlertPriority
from real_time_system.utils.scheduler_utils import TaskScheduler, RateLimiter
from real_time_system.utils.colored_log import get_colored_logger, print_banner, print_system_status, print_trading_opportunity


class RealTimeMonitor:
    """Real-time monitoring system for trading opportunities."""
    
    def __init__(self, config_path: Optional[str] = None):
        # Setup paths
        self.base_dir = Path(__file__).parent
        self.config_dir = self.base_dir / "config"
        self.logs_dir = self.base_dir / "logs"
        
        # Create directories
        self.logs_dir.mkdir(exist_ok=True)
        
        # Setup basic logging first
        self.logger = get_colored_logger(__name__, self.logs_dir / "monitoring.log")
        
        # Load configuration
        self.config = self._load_config(config_path)
        self.watchlist = self._load_watchlist()
        
        # Setup detailed logging level
        log_level = self.config.get('notifications', {}).get('console', {}).get('log_level', 'INFO')
        self.logger.set_level(getattr(logging, log_level))
        
        # Initialize components
        self.alert_manager = AlertManager(self.config)
        self.scheduler = TaskScheduler(
            max_workers=self.config.get('monitoring', {}).get('max_parallel_workers', 5)
        )
        self.rate_limiter = RateLimiter(
            delay_seconds=self.config.get('monitoring', {}).get('api_rate_limit_delay', 1.0)
        )
        
        # Initialize trading bot orchestrator
        self.trading_bot = None
        if HighLeverageBotOrchestrator:
            try:
                self.trading_bot = HighLeverageBotOrchestrator()
                self.logger.success("High leverage bot orchestrator initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize trading bot: {e}")
        
        # Runtime state
        self.running = False
        self.start_time = None
        self.monitored_symbols = set()
        self.last_config_reload = datetime.now()
        
        # Setup signal handlers (only if running in main thread)
        try:
            if threading.current_thread() == threading.main_thread():
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
                self.logger.debug("Signal handlers registered")
            else:
                self.logger.debug("Skipping signal handlers (not in main thread)")
        except Exception as e:
            self.logger.warning(f"Could not register signal handlers: {e}")
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load monitoring configuration."""
        if config_path:
            config_file = Path(config_path)
        else:
            config_file = self.config_dir / "monitoring_config.json"
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            self.logger.success(f"Loaded config from {config_file}")
            return config
        except Exception as e:
            print(f"Error loading config from {config_file}: {e}")
            # Return default config
            return {
                "monitoring": {"default_interval_minutes": 15},
                "notifications": {"console": {"enabled": True}},
                "alerts": {"leverage_threshold": 10.0, "confidence_threshold": 70.0}
            }
    
    def _load_watchlist(self) -> Dict[str, Any]:
        """Load watchlist configuration."""
        watchlist_file = self.config_dir / "watchlist.json"
        
        try:
            with open(watchlist_file, 'r') as f:
                watchlist = json.load(f)
            return watchlist
        except Exception as e:
            self.logger.error(f"Error loading watchlist from {watchlist_file}: {e}")
            # Return default watchlist
            return {
                "default_settings": {"enabled": True, "timeframes": ["1h"]},
                "symbols": {"HYPE": {"enabled": True}}
            }
    
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def _reload_config_if_needed(self):
        """Reload configuration if enough time has passed."""
        reload_interval = self.config.get('system', {}).get('config_reload_interval', 600)
        if (datetime.now() - self.last_config_reload).total_seconds() >= reload_interval:
            try:
                new_config = self._load_config()
                new_watchlist = self._load_watchlist()
                
                self.config = new_config
                self.watchlist = new_watchlist
                self.last_config_reload = datetime.now()
                
                self.logger.success("Configuration reloaded")
                
                # Update alert manager config
                self.alert_manager.config = new_config
                
            except Exception as e:
                self.logger.error(f"Failed to reload configuration: {e}")
    
    def _analyze_symbol(self, symbol: str, symbol_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a single symbol for trading opportunities."""
        if not self.trading_bot:
            self.logger.warning("Trading bot not available for analysis")
            return None
        
        try:
            # Rate limiting
            self.rate_limiter.wait()
            
            results = []
            timeframes = symbol_config.get('timeframes', ['1h'])
            strategies = symbol_config.get('strategies', ['Conservative_ML'])
            
            for timeframe in timeframes:
                for strategy in strategies:
                    try:
                        # Analyze using the trading bot
                        analysis = self.trading_bot.analyze_symbol(
                            symbol=symbol,
                            timeframe=timeframe,
                            strategy=strategy
                        )
                        
                        if analysis and 'leverage' in analysis and 'confidence' in analysis:
                            analysis['symbol'] = symbol
                            analysis['timeframe'] = timeframe
                            analysis['strategy'] = strategy
                            analysis['timestamp'] = datetime.now()
                            results.append(analysis)
                            
                    except Exception as e:
                        self.logger.error(f"Analysis failed for {symbol} {timeframe} {strategy}: {e}")
            
            return {'symbol': symbol, 'results': results} if results else None
            
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def _process_analysis_results(self, analysis: Dict[str, Any]):
        """Process analysis results and generate alerts."""
        if not analysis or 'results' not in analysis:
            return
        
        symbol = analysis['symbol']
        symbol_config = self.watchlist['symbols'].get(symbol, {})
        min_leverage = symbol_config.get('min_leverage', self.config['alerts']['leverage_threshold'])
        min_confidence = symbol_config.get('min_confidence', self.config['alerts']['confidence_threshold'])
        
        for result in analysis['results']:
            leverage = result.get('leverage', 0)
            confidence = result.get('confidence', 0)
            strategy = result.get('strategy', 'Unknown')
            timeframe = result.get('timeframe', 'Unknown')
            
            # Check for trading opportunities
            if leverage >= min_leverage and confidence >= min_confidence:
                # Log trading opportunity with special formatting
                self.logger.trading_opportunity(symbol, leverage, confidence, strategy)
                
                alert = self.alert_manager.create_trading_opportunity_alert(
                    symbol=symbol,
                    strategy=strategy,
                    timeframe=timeframe,
                    leverage=leverage,
                    confidence=confidence,
                    details={
                        'entry_price': result.get('entry_price'),
                        'target_price': result.get('target_price'),
                        'stop_loss': result.get('stop_loss'),
                        'position_size': result.get('position_size'),
                        'risk_reward_ratio': result.get('risk_reward_ratio'),
                        'analysis_timestamp': result.get('timestamp', datetime.now()).isoformat()
                    }
                )
                
                success = self.alert_manager.send_alert(alert)
                if success:
                    self.logger.alert_sent(f"Trading opportunity for {symbol}")
                else:
                    self.logger.error(f"Failed to send alert for {symbol}")
            
            # Check for risk warnings
            risk_level = result.get('risk_level', 0)
            if risk_level >= self.config.get('alerts', {}).get('risk_warning_threshold', 50):
                risk_alert = self.alert_manager.create_risk_warning_alert(
                    symbol=symbol,
                    risk_level=risk_level,
                    reason=result.get('risk_reason', 'High risk detected'),
                    details={
                        'current_price': result.get('current_price'),
                        'volatility': result.get('volatility'),
                        'strategy': strategy,
                        'timeframe': timeframe
                    }
                )
                
                self.alert_manager.send_alert(risk_alert)
    
    def _monitor_symbol_task(self, symbol: str):
        """Task function for monitoring a single symbol."""
        symbol_config = self.watchlist['symbols'].get(symbol, {})
        
        if not symbol_config.get('enabled', True):
            return
        
        self.logger.debug(f"Monitoring {symbol}")
        
        try:
            analysis = self._analyze_symbol(symbol, symbol_config)
            if analysis:
                self._process_analysis_results(analysis)
        except Exception as e:
            self.logger.error(f"Error in monitoring task for {symbol}: {e}")
    
    def _health_check_task(self):
        """Periodic health check task."""
        try:
            # Check scheduler status
            if not self.scheduler.is_running():
                self.logger.error("Scheduler is not running!")
                return
            
            # Check trading bot
            if not self.trading_bot:
                self.logger.warning("Trading bot not available")
            
            # Reload config if needed
            self._reload_config_if_needed()
            
            # Log system status
            uptime = datetime.now() - self.start_time if self.start_time else "Unknown"
            active_symbols = len([s for s, cfg in self.watchlist['symbols'].items() if cfg.get('enabled')])
            
            self.logger.health_check("OK", {
                'uptime': str(uptime),
                'active_symbols': active_symbols
            })
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
    
    def add_symbol_monitoring(self, symbol: str, interval_minutes: Optional[int] = None):
        """Add or update symbol monitoring."""
        if symbol not in self.watchlist['symbols']:
            self.logger.error(f"Symbol {symbol} not found in watchlist")
            return False
        
        symbol_config = self.watchlist['symbols'][symbol]
        if not symbol_config.get('enabled', True):
            self.logger.info(f"Symbol {symbol} is disabled in watchlist")
            return False
        
        # Use provided interval or default
        if interval_minutes is None:
            interval_minutes = self.config['monitoring']['default_interval_minutes']
        
        # Create task ID
        task_id = f"monitor_{symbol}"
        
        # Add or update monitoring task
        self.scheduler.add_task(
            task_id=task_id,
            func=self._monitor_symbol_task,
            interval_minutes=interval_minutes,
            args=(symbol,)
        )
        
        self.monitored_symbols.add(symbol)
        self.logger.task_status(f"monitor_{symbol}", "started", f"interval: {interval_minutes}m")
        return True
    
    def remove_symbol_monitoring(self, symbol: str):
        """Remove symbol monitoring."""
        task_id = f"monitor_{symbol}"
        
        if self.scheduler.remove_task(task_id):
            self.monitored_symbols.discard(symbol)
            self.logger.task_status(f"monitor_{symbol}", "completed", "monitoring removed")
            return True
        return False
    
    def update_monitoring_interval(self, symbol: str, interval_minutes: int):
        """Update monitoring interval for a symbol."""
        task_id = f"monitor_{symbol}"
        
        if self.scheduler.update_task_interval(task_id, interval_minutes):
            self.logger.success(f"Updated {symbol} monitoring interval to {interval_minutes}m")
            return True
        return False
    
    def start(self, symbols: Optional[List[str]] = None, interval_minutes: Optional[int] = None):
        """Start the monitoring system."""
        if self.running:
            self.logger.warning("Monitor is already running")
            return
        
        print_banner("LONG TRADER REAL-TIME MONITOR", "Automated Trading Opportunity Detection")
        self.logger.system_start({
            'symbols': symbols or list(self.watchlist['symbols'].keys()),
            'interval': interval_minutes or self.config['monitoring']['default_interval_minutes']
        })
        self.start_time = datetime.now()
        self.running = True
        
        # Send startup alert
        startup_alert = self.alert_manager.create_system_status_alert(
            status="started",
            message=f"Real-time monitoring system started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            details={
                'symbols_to_monitor': symbols or list(self.watchlist['symbols'].keys()),
                'interval_minutes': interval_minutes or self.config['monitoring']['default_interval_minutes']
            }
        )
        self.alert_manager.send_alert(startup_alert)
        
        # Determine symbols to monitor
        if symbols:
            symbols_to_monitor = symbols
        else:
            symbols_to_monitor = [
                symbol for symbol, config in self.watchlist['symbols'].items()
                if config.get('enabled', True)
            ]
        
        # Start scheduler
        self.scheduler.start()
        
        # Add monitoring tasks for each symbol
        for symbol in symbols_to_monitor:
            self.add_symbol_monitoring(symbol, interval_minutes)
        
        # Add health check task
        health_check_interval = self.config.get('system', {}).get('health_check_interval', 300) // 60
        self.scheduler.add_task(
            task_id="health_check",
            func=self._health_check_task,
            interval_minutes=health_check_interval
        )
        
        self.logger.monitor_status(symbols_to_monitor)
        self.logger.success(f"Monitor started with {len(symbols_to_monitor)} symbols")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
            self.stop()
    
    def stop(self):
        """Stop the monitoring system."""
        if not self.running:
            return
        
        self.logger.system_stop({
            'uptime': str(datetime.now() - self.start_time) if self.start_time else "Unknown",
            'symbols': list(self.monitored_symbols)
        })
        self.running = False
        
        # Send shutdown alert
        shutdown_alert = self.alert_manager.create_system_status_alert(
            status="stopped",
            message=f"Real-time monitoring system stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            details={
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                'monitored_symbols': list(self.monitored_symbols)
            }
        )
        self.alert_manager.send_alert(shutdown_alert)
        
        # Stop scheduler
        timeout = self.config.get('system', {}).get('graceful_shutdown_timeout', 30)
        self.scheduler.stop(timeout)
        
        self.logger.success("Monitor stopped gracefully")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'running': self.running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime_seconds': uptime,
            'monitored_symbols': list(self.monitored_symbols),
            'scheduler_running': self.scheduler.is_running(),
            'task_status': self.scheduler.get_task_status(),
            'alert_stats': self.alert_manager.get_statistics()
        }
    
    def test_system(self) -> Dict[str, Any]:
        """Test all system components."""
        results = {
            'config_loaded': bool(self.config),
            'watchlist_loaded': bool(self.watchlist),
            'trading_bot_available': bool(self.trading_bot),
            'scheduler_available': bool(self.scheduler),
            'alert_manager_available': bool(self.alert_manager)
        }
        
        # Test notifications
        if self.alert_manager:
            notification_tests = self.alert_manager.test_notifications()
            results.update({f'notification_{k}': v for k, v in notification_tests.items()})
        
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Real-time trading opportunity monitor")
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--interval', type=int, help='Monitoring interval in minutes')
    parser.add_argument('--symbols', help='Comma-separated list of symbols to monitor')
    parser.add_argument('--test', action='store_true', help='Test system components and exit')
    parser.add_argument('--status', action='store_true', help='Show system status and exit')
    
    args = parser.parse_args()
    
    # Initialize monitor
    try:
        monitor = RealTimeMonitor(config_path=args.config)
    except Exception as e:
        print(f"Failed to initialize monitor: {e}")
        sys.exit(1)
    
    # Handle test mode
    if args.test:
        print("Testing system components...")
        results = monitor.test_system()
        
        print("\\nTest Results:")
        for component, status in results.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {component}: {'OK' if status else 'FAILED'}")
        
        all_passed = all(results.values())
        print(f"\\nOverall: {'✅ All tests passed' if all_passed else '❌ Some tests failed'}")
        sys.exit(0 if all_passed else 1)
    
    # Handle status mode
    if args.status:
        status = monitor.get_status()
        print("\\nSystem Status:")
        print(json.dumps(status, indent=2, default=str))
        sys.exit(0)
    
    # Parse symbols
    symbols = None
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    
    # Start monitoring
    try:
        monitor.start(symbols=symbols, interval_minutes=args.interval)
    except Exception as e:
        monitor.logger.error(f"Monitor failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()