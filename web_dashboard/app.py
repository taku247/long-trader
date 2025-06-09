#!/usr/bin/env python3
"""
Web Dashboard for Long Trader Real-Time Monitoring System.
"""

import sys
import os
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from real_time_system.monitor import RealTimeMonitor
from real_time_system.utils.colored_log import get_colored_logger


class WebDashboard:
    """Web dashboard for monitoring system."""
    
    def __init__(self, host='localhost', port=5000, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        
        # Initialize Flask app
        self.app = Flask(__name__, 
                        template_folder='templates',
                        static_folder='static')
        self.app.config['SECRET_KEY'] = 'long-trader-dashboard-secret-key'
        
        # Initialize SocketIO
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Initialize logger
        self.logger = get_colored_logger(__name__)
        
        # Monitor reference
        self.monitor: Optional[RealTimeMonitor] = None
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Setup routes
        self._setup_routes()
        self._setup_socketio_events()
        
        self.logger.info("Web dashboard initialized")
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return render_template('dashboard.html')
        
        @self.app.route('/api/status')
        def api_status():
            """Get system status."""
            if not self.monitor:
                return jsonify({
                    'status': 'stopped',
                    'monitored_symbols': [],
                    'uptime_seconds': 0,
                    'last_update': None
                })
            
            try:
                status = self.monitor.get_status()
                return jsonify(status)
            except Exception as e:
                self.logger.error(f"Error getting status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/alerts')
        def api_alerts():
            """Get alert history."""
            limit = request.args.get('limit', 50, type=int)
            alert_type = request.args.get('type')
            symbol = request.args.get('symbol')
            
            if not self.monitor or not self.monitor.alert_manager:
                return jsonify([])
            
            try:
                from real_time_system.alert_manager import AlertType
                alert_type_enum = AlertType(alert_type) if alert_type else None
                
                alerts = self.monitor.alert_manager.get_alert_history(
                    limit=limit,
                    alert_type=alert_type_enum,
                    symbol=symbol
                )
                return jsonify(alerts)
            except Exception as e:
                self.logger.error(f"Error getting alerts: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/statistics')
        def api_statistics():
            """Get system statistics."""
            if not self.monitor or not self.monitor.alert_manager:
                return jsonify({})
            
            try:
                stats = self.monitor.alert_manager.get_statistics()
                return jsonify(stats)
            except Exception as e:
                self.logger.error(f"Error getting statistics: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/monitor/start', methods=['POST'])
        def api_monitor_start():
            """Start the monitoring system."""
            data = request.get_json() or {}
            symbols = data.get('symbols', ['HYPE', 'SOL'])
            interval_minutes = data.get('interval_minutes', 15)
            
            try:
                self._start_monitor(symbols, interval_minutes)
                return jsonify({'status': 'started', 'symbols': symbols, 'interval_minutes': interval_minutes})
            except Exception as e:
                self.logger.error(f"Error starting monitor: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/monitor/stop', methods=['POST'])
        def api_monitor_stop():
            """Stop the monitoring system."""
            try:
                self._stop_monitor()
                return jsonify({'status': 'stopped'})
            except Exception as e:
                self.logger.error(f"Error stopping monitor: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/config')
        def api_config():
            """Get current configuration."""
            if not self.monitor:
                return jsonify({})
            
            try:
                config = self.monitor.config
                # Remove sensitive information
                safe_config = {
                    'monitoring': config.get('monitoring', {}),
                    'alerts': config.get('alerts', {}),
                    'notifications': {
                        'console': config.get('notifications', {}).get('console', {}),
                        'file': config.get('notifications', {}).get('file', {}),
                        'discord': {
                            'enabled': config.get('notifications', {}).get('discord', {}).get('enabled', False)
                        }
                    }
                }
                return jsonify(safe_config)
            except Exception as e:
                self.logger.error(f"Error getting config: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _setup_socketio_events(self):
        """Setup SocketIO events."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            self.logger.info(f"Client connected: {request.sid}")
            emit('status', {'message': 'Connected to Long Trader Dashboard'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            self.logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('subscribe_updates')
        def handle_subscribe():
            """Handle subscription to real-time updates."""
            self.logger.info(f"Client subscribed to updates: {request.sid}")
            # Send current status immediately
            if self.monitor:
                try:
                    status = self.monitor.get_status()
                    emit('status_update', status)
                except Exception as e:
                    self.logger.error(f"Error sending status update: {e}")
    
    def _start_monitor(self, symbols: list, interval_minutes: int):
        """Start the monitoring system."""
        if self.monitor and self.monitor.is_running():
            self.logger.warning("Monitor is already running")
            return
        
        self.logger.info(f"Starting monitor with symbols: {symbols}, interval: {interval_minutes}m")
        
        # Initialize monitor
        self.monitor = RealTimeMonitor()
        
        # Start monitor in separate thread
        def run_monitor():
            try:
                self.monitor.start(symbols=symbols, interval_minutes=interval_minutes)
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
        
        self.monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        self.monitor_thread.start()
        
        # Start status broadcasting
        self._start_status_broadcasting()
    
    def _stop_monitor(self):
        """Stop the monitoring system."""
        if self.monitor:
            self.logger.info("Stopping monitor")
            self.monitor.stop()
            self.monitor = None
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            self.monitor_thread = None
    
    def _start_status_broadcasting(self):
        """Start broadcasting status updates to connected clients."""
        def broadcast_status():
            while self.monitor and self.monitor.is_running():
                try:
                    status = self.monitor.get_status()
                    self.socketio.emit('status_update', status)
                    
                    # Broadcast recent alerts
                    if self.monitor.alert_manager:
                        recent_alerts = self.monitor.alert_manager.get_alert_history(limit=5)
                        self.socketio.emit('new_alerts', recent_alerts)
                    
                except Exception as e:
                    self.logger.error(f"Error broadcasting status: {e}")
                
                # Wait 10 seconds before next broadcast
                self.socketio.sleep(10)
        
        # Start broadcasting in background
        self.socketio.start_background_task(broadcast_status)
    
    def run(self):
        """Run the web dashboard."""
        self.logger.system_start(f"Starting web dashboard on http://{self.host}:{self.port}")
        
        try:
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=self.debug,
                allow_unsafe_werkzeug=True
            )
        except KeyboardInterrupt:
            self.logger.warning("Dashboard interrupted by user")
        except Exception as e:
            self.logger.error(f"Dashboard error: {e}")
        finally:
            self._stop_monitor()
            self.logger.system_stop("Web dashboard stopped")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Long Trader Web Dashboard')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    dashboard = WebDashboard(host=args.host, port=args.port, debug=args.debug)
    dashboard.run()


if __name__ == '__main__':
    main()