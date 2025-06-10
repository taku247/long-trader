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
                    'running': False,
                    'monitored_symbols': [],
                    'uptime_seconds': 0,
                    'start_time': None
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
        
        # Alert History Analysis Routes
        @self.app.route('/analysis')
        def analysis_page():
            """Alert history analysis page."""
            return render_template('analysis.html')
        
        @self.app.route('/api/analysis/chart-data')
        def api_analysis_chart_data():
            """Get chart data with prices."""
            symbol = request.args.get('symbol', 'HYPE')
            days = request.args.get('days', 30, type=int)
            
            try:
                from alert_history_system.price_fetcher import PriceFetcher
                fetcher = PriceFetcher()
                
                chart_data = fetcher.get_chart_data_with_prices(symbol, days)
                return jsonify({
                    'symbol': symbol,
                    'days': days,
                    'prices': chart_data
                })
            except Exception as e:
                self.logger.error(f"Error getting chart data: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/analysis/alerts')
        def api_analysis_alerts():
            """Get alert history with performance."""
            symbol = request.args.get('symbol', 'HYPE')
            days = request.args.get('days', 30, type=int)
            strategy = request.args.get('strategy', '')
            
            try:
                from alert_history_system.alert_db_writer import AlertDBWriter
                from alert_history_system.price_fetcher import PriceFetcher
                
                db_writer = AlertDBWriter()
                fetcher = PriceFetcher()
                
                # Get alerts from database
                alerts = db_writer.db.get_alerts_by_symbol(symbol, 100)
                
                # Filter by days
                from datetime import datetime, timedelta
                cutoff_date = datetime.now() - timedelta(days=days)
                alerts = [a for a in alerts if a.timestamp >= cutoff_date]
                
                # Filter by strategy if specified
                if strategy:
                    alerts = [a for a in alerts if a.strategy == strategy]
                
                # Add performance calculation
                result = []
                for alert in alerts:
                    alert_data = {
                        'alert_id': alert.alert_id,
                        'symbol': alert.symbol,
                        'timestamp': alert.timestamp.isoformat(),
                        'entry_price': alert.entry_price,
                        'leverage': alert.leverage,
                        'confidence': alert.confidence,
                        'strategy': alert.strategy,
                        'timeframe': alert.timeframe
                    }
                    
                    # Calculate current performance
                    if alert.entry_price and alert.timestamp:
                        performance = fetcher.calculate_performance(
                            alert.entry_price, alert.timestamp, alert.symbol
                        )
                        if 'error' not in performance:
                            alert_data['performance'] = performance
                    
                    result.append(alert_data)
                
                return jsonify(result)
            except Exception as e:
                self.logger.error(f"Error getting alerts: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/analysis/statistics')
        def api_analysis_statistics():
            """Get analysis statistics."""
            symbol = request.args.get('symbol')
            strategy = request.args.get('strategy', '')
            
            try:
                from alert_history_system.alert_db_writer import AlertDBWriter
                
                db_writer = AlertDBWriter()
                stats = db_writer.get_statistics(symbol if symbol else None)
                
                # Add strategy breakdown if available
                stats['by_strategy'] = {}
                
                return jsonify(stats)
            except Exception as e:
                self.logger.error(f"Error getting statistics: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/analysis/alert-detail/<alert_id>')
        def api_analysis_alert_detail(alert_id):
            """Get detailed alert information."""
            try:
                from alert_history_system.alert_db_writer import AlertDBWriter
                from alert_history_system.price_fetcher import PriceFetcher
                
                db_writer = AlertDBWriter()
                fetcher = PriceFetcher()
                
                # Get alert from database
                session = db_writer.db.get_session()
                try:
                    from alert_history_system.database.models import Alert
                    alert = session.query(Alert).filter_by(alert_id=alert_id).first()
                    
                    if not alert:
                        return jsonify({'error': 'Alert not found'}), 404
                    
                    alert_data = {
                        'alert_id': alert.alert_id,
                        'symbol': alert.symbol,
                        'timestamp': alert.timestamp.isoformat(),
                        'entry_price': alert.entry_price,
                        'target_price': alert.target_price,
                        'stop_loss': alert.stop_loss,
                        'leverage': alert.leverage,
                        'confidence': alert.confidence,
                        'strategy': alert.strategy,
                        'timeframe': alert.timeframe,
                        'metadata': alert.get_extra_data()
                    }
                    
                    # Calculate performance
                    if alert.entry_price and alert.timestamp:
                        performance = fetcher.calculate_performance(
                            alert.entry_price, alert.timestamp, alert.symbol
                        )
                        if 'error' not in performance:
                            alert_data['performance'] = performance
                    
                    return jsonify(alert_data)
                finally:
                    session.close()
                    
            except Exception as e:
                self.logger.error(f"Error getting alert detail: {e}")
                return jsonify({'error': str(e)}), 500
        
        # Settings Management Routes
        @self.app.route('/settings')
        def settings_page():
            """Settings management page."""
            return render_template('settings.html')
        
        @self.app.route('/api/settings/save', methods=['POST'])
        def api_settings_save():
            """Save settings configuration."""
            try:
                settings = request.get_json()
                if not settings:
                    return jsonify({'error': 'No settings data provided'}), 400
                
                # Save to config file
                config_path = Path(__file__).parent.parent / 'config.json'
                
                # Load existing config
                current_config = {}
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        current_config = json.load(f)
                
                # Update with new settings
                current_config.update({
                    'monitoring': {
                        'symbols': settings.get('symbols', []),
                        'interval_minutes': settings.get('monitoring', {}).get('interval_minutes', 15)
                    },
                    'alerts': settings.get('alerts', {}),
                    'notifications': settings.get('notifications', {})
                })
                
                # Save updated config
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(current_config, f, ensure_ascii=False, indent=2)
                
                self.logger.info("Settings saved successfully")
                return jsonify({'status': 'saved', 'timestamp': datetime.now().isoformat()})
                
            except Exception as e:
                self.logger.error(f"Error saving settings: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/settings/reset', methods=['POST'])
        def api_settings_reset():
            """Reset settings to defaults."""
            try:
                default_settings = {
                    'monitoring': {
                        'symbols': ['HYPE', 'SOL'],
                        'interval_minutes': 15
                    },
                    'alerts': {
                        'leverage_threshold': 10.0,
                        'confidence_threshold': 70,
                        'cooldown_minutes': 60,
                        'max_alerts_hour': 10
                    },
                    'notifications': {
                        'discord': {
                            'enabled': False,
                            'webhook_url': '',
                            'mention_role': ''
                        },
                        'console': {
                            'level': 'INFO'
                        },
                        'file': {
                            'enabled': True
                        }
                    }
                }
                
                config_path = Path(__file__).parent.parent / 'config.json'
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_settings, f, ensure_ascii=False, indent=2)
                
                self.logger.info("Settings reset to defaults")
                return jsonify({'status': 'reset', 'settings': default_settings})
                
            except Exception as e:
                self.logger.error(f"Error resetting settings: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/settings/profile/<profile_name>')
        def api_settings_profile_load(profile_name):
            """Load settings profile."""
            try:
                profiles_path = Path(__file__).parent.parent / 'settings_profiles.json'
                
                if not profiles_path.exists():
                    return jsonify({'error': 'No profiles found'}), 404
                
                with open(profiles_path, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
                
                if profile_name not in profiles:
                    return jsonify({'error': f'Profile "{profile_name}" not found'}), 404
                
                return jsonify(profiles[profile_name])
                
            except Exception as e:
                self.logger.error(f"Error loading profile: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/settings/profile/save', methods=['POST'])
        def api_settings_profile_save():
            """Save settings profile."""
            try:
                data = request.get_json()
                if not data or 'name' not in data or 'settings' not in data:
                    return jsonify({'error': 'Invalid profile data'}), 400
                
                profile_name = data['name']
                settings = data['settings']
                
                profiles_path = Path(__file__).parent.parent / 'settings_profiles.json'
                
                # Load existing profiles
                profiles = {}
                if profiles_path.exists():
                    with open(profiles_path, 'r', encoding='utf-8') as f:
                        profiles = json.load(f)
                
                # Save new profile
                profiles[profile_name] = settings
                
                with open(profiles_path, 'w', encoding='utf-8') as f:
                    json.dump(profiles, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"Profile '{profile_name}' saved")
                return jsonify({'status': 'saved', 'profile': profile_name})
                
            except Exception as e:
                self.logger.error(f"Error saving profile: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/settings/profiles')
        def api_settings_profiles_list():
            """List all settings profiles."""
            try:
                profiles_path = Path(__file__).parent.parent / 'settings_profiles.json'
                
                if not profiles_path.exists():
                    return jsonify([])
                
                with open(profiles_path, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
                
                return jsonify([{'name': name} for name in profiles.keys()])
                
            except Exception as e:
                self.logger.error(f"Error listing profiles: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/test-discord', methods=['POST'])
        def api_test_discord():
            """Test Discord notification."""
            try:
                data = request.get_json()
                webhook_url = data.get('webhook_url')
                
                if not webhook_url:
                    return jsonify({'error': 'Webhook URL required'}), 400
                
                # Send test message
                import requests
                test_payload = {
                    'content': '🔍 **Long Trader設定テスト**\n設定ページからのテスト通知です。Discordが正常に設定されています！',
                    'username': 'Long Trader Bot'
                }
                
                response = requests.post(webhook_url, json=test_payload, timeout=10)
                
                if response.status_code == 204:
                    self.logger.info("Discord test notification sent successfully")
                    return jsonify({'status': 'success'})
                else:
                    return jsonify({'error': f'Discord API error: {response.status_code}'}), 500
                
            except Exception as e:
                self.logger.error(f"Error testing Discord: {e}")
                return jsonify({'error': str(e)}), 500
        
        # Strategy Results Routes
        @self.app.route('/strategy-results')
        def strategy_results_page():
            """Strategy analysis results page."""
            return render_template('strategy_results.html')
        
        @self.app.route('/api/strategy-results/symbols')
        def api_strategy_results_symbols():
            """Get symbols that have completed analysis."""
            try:
                from scalable_analysis_system import ScalableAnalysisSystem
                system = ScalableAnalysisSystem()
                
                # Get symbols with completed analyses
                query = """
                    SELECT symbol, COUNT(*) as pattern_count, AVG(sharpe_ratio) as avg_sharpe
                    FROM analyses 
                    WHERE status='completed' 
                    GROUP BY symbol 
                    HAVING pattern_count >= 6
                    ORDER BY avg_sharpe DESC
                """
                
                import sqlite3
                with sqlite3.connect(system.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    results = cursor.fetchall()
                    
                    symbols = [
                        {
                            'symbol': row[0],
                            'pattern_count': row[1],
                            'avg_sharpe': round(row[2], 2) if row[2] else 0
                        }
                        for row in results
                    ]
                    
                return jsonify(symbols)
                
            except Exception as e:
                self.logger.error(f"Error getting strategy symbols: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/strategy-results/<symbol>')
        def api_strategy_results_detail(symbol):
            """Get detailed strategy results for a symbol."""
            try:
                from scalable_analysis_system import ScalableAnalysisSystem
                system = ScalableAnalysisSystem()
                
                # Query all analyses for the symbol
                filters = {'symbol': symbol}
                results_df = system.query_analyses(filters=filters, limit=50)
                
                if results_df.empty:
                    return jsonify({'results': []})
                
                # Convert to list of dictionaries
                results = []
                for _, row in results_df.iterrows():
                    results.append({
                        'symbol': row['symbol'],
                        'timeframe': row['timeframe'],
                        'config': row['config'],
                        'sharpe_ratio': float(row['sharpe_ratio']) if row['sharpe_ratio'] else 0,
                        'win_rate': float(row['win_rate']) if row['win_rate'] else 0,
                        'total_return': float(row['total_return']) if row['total_return'] else 0,
                        'max_drawdown': float(row['max_drawdown']) if row['max_drawdown'] else 0,
                        'avg_leverage': float(row['avg_leverage']) if row['avg_leverage'] else 0,
                        'total_trades': int(row['total_trades']) if row['total_trades'] else 0,
                        'generated_at': row['generated_at']
                    })
                
                return jsonify({
                    'symbol': symbol,
                    'results': results,
                    'total_patterns': len(results)
                })
                
            except Exception as e:
                self.logger.error(f"Error getting strategy results for {symbol}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/strategy-results/<symbol>/<timeframe>/<config>/trades')
        def api_strategy_trade_details(symbol, timeframe, config):
            """Get detailed trade data for specific strategy."""
            try:
                from scalable_analysis_system import ScalableAnalysisSystem
                system = ScalableAnalysisSystem()
                
                # Load compressed trade data
                trades_df = system.load_compressed_trades(symbol, timeframe, config)
                
                if trades_df is None:
                    self.logger.warning(f"No trade data found for {symbol} {timeframe} {config}")
                    return jsonify([])
                
                # Check if it's a DataFrame and if it's empty
                if hasattr(trades_df, 'empty') and trades_df.empty:
                    self.logger.warning(f"Empty DataFrame for {symbol} {timeframe} {config}")
                    return jsonify([])
                
                # Check if it's a list and if it's empty
                if isinstance(trades_df, list) and len(trades_df) == 0:
                    self.logger.warning(f"Empty list for {symbol} {timeframe} {config}")
                    return jsonify([])
                
                # Convert DataFrame to list of dictionaries
                if hasattr(trades_df, 'to_dict'):
                    # It's a pandas DataFrame
                    trades = trades_df.to_dict('records')
                else:
                    # It's already a list
                    trades = trades_df if isinstance(trades_df, list) else []
                
                # Ensure consistent format
                formatted_trades = []
                for i, trade in enumerate(trades):
                    # Debug: Log first trade to see what keys are available
                    if i == 0:
                        self.logger.info(f"First trade keys for {symbol} {timeframe} {config}: {list(trade.keys()) if isinstance(trade, dict) else 'Not a dict'}")
                        self.logger.info(f"First trade data: {trade}")
                    
                    formatted_trade = {
                        'entry_time': trade.get('entry_time', 'N/A'),
                        'leverage': float(trade.get('leverage', 0)),
                        'pnl_pct': float(trade.get('pnl_pct', 0)),
                        'is_success': bool(trade.get('is_success', trade.get('is_win', False))),
                        'confidence': float(trade.get('confidence', 0))
                    }
                    formatted_trades.append(formatted_trade)
                
                return jsonify(formatted_trades)
                
            except Exception as e:
                self.logger.error(f"Error getting trade details for {symbol} {timeframe} {config}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/strategy-results/<symbol>/export')
        def api_strategy_results_export(symbol):
            """Export strategy results as CSV."""
            try:
                from scalable_analysis_system import ScalableAnalysisSystem
                import io
                from flask import make_response
                
                system = ScalableAnalysisSystem()
                
                # Get results
                filters = {'symbol': symbol}
                results_df = system.query_analyses(filters=filters, limit=50)
                
                if results_df.empty:
                    return jsonify({'error': 'No data to export'}), 404
                
                # Create CSV
                output = io.StringIO()
                results_df.to_csv(output, index=False)
                csv_content = output.getvalue()
                output.close()
                
                # Create response
                response = make_response(csv_content)
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = f'attachment; filename="{symbol}_strategy_results.csv"'
                
                return response
                
            except Exception as e:
                self.logger.error(f"Error exporting results for {symbol}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/monitor/add-strategy', methods=['POST'])
        def api_monitor_add_strategy():
            """Add recommended strategy to monitoring system."""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                symbol = data.get('symbol')
                timeframe = data.get('timeframe')
                strategy = data.get('strategy')
                
                if not all([symbol, timeframe, strategy]):
                    return jsonify({'error': 'Missing required fields'}), 400
                
                # TODO: Implement actual monitoring system integration
                # For now, just return success
                self.logger.info(f"Added strategy to monitoring: {symbol} {timeframe} {strategy}")
                
                return jsonify({
                    'status': 'success',
                    'message': f'{symbol} {timeframe} {strategy} を監視システムに追加しました',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'strategy': strategy
                })
                
            except Exception as e:
                self.logger.error(f"Error adding strategy to monitoring: {e}")
                return jsonify({'error': str(e)}), 500

        # Symbol Addition Routes
        @self.app.route('/api/symbol/add', methods=['POST'])
        def api_symbol_add():
            """Add new symbol with automatic training and backtesting."""
            try:
                data = request.get_json()
                if not data or 'symbol' not in data:
                    return jsonify({'error': 'Symbol is required'}), 400
                
                symbol = data['symbol'].upper().strip()
                
                if not symbol:
                    return jsonify({'error': 'Invalid symbol'}), 400
                
                # Validate symbol exists on Hyperliquid before starting training
                import asyncio
                from hyperliquid_validator import HyperliquidValidator, ValidationContext
                
                async def validate_symbol_async():
                    async with HyperliquidValidator(strict_mode=True) as validator:
                        return await validator.validate_symbol(symbol, ValidationContext.NEW_ADDITION)
                
                # Run validation synchronously
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    validation_result = loop.run_until_complete(validate_symbol_async())
                    loop.close()
                    
                    if not validation_result.valid:
                        # Create more descriptive error messages
                        if validation_result.status == 'invalid':
                            error_message = f"{symbol}はHyperliquidで取引されていません"
                            detailed_message = validation_result.reason or "この銘柄はHyperliquidでサポートされていません"
                        elif validation_result.status == 'inactive':
                            error_message = f"{symbol}は現在取引停止中です"
                            detailed_message = validation_result.reason or "この銘柄は一時的に取引が停止されています"
                        else:
                            error_message = f"{symbol}: {validation_result.reason}"
                            detailed_message = validation_result.reason
                        
                        self.logger.warning(f"Symbol validation failed: {error_message}")
                        return jsonify({
                            'error': detailed_message,
                            'validation_status': validation_result.status,
                            'symbol': symbol,
                            'user_message': error_message,
                            'suggestion': '正しい銘柄名（例: BTC, ETH, SOL, HYPE等）を入力してください'
                        }), 400
                        
                    self.logger.info(f"✅ Symbol {symbol} validated successfully on Hyperliquid")
                    
                except Exception as validation_error:
                    error_message = f"Hyperliquid validation failed for {symbol}: {str(validation_error)}"
                    self.logger.error(error_message)
                    return jsonify({
                        'error': error_message,
                        'validation_status': 'error',
                        'symbol': symbol
                    }), 400
                
                # Generate execution ID first, then start training
                from auto_symbol_training import AutoSymbolTrainer
                from datetime import datetime
                import uuid
                
                # Create execution ID that will be used
                execution_id = f"symbol_addition_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
                
                trainer = AutoSymbolTrainer()
                
                # Execute training asynchronously with the predetermined ID
                import threading
                
                def run_training():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Pass the execution_id to ensure consistency
                        result_execution_id = loop.run_until_complete(
                            trainer.add_symbol_with_training(symbol, execution_id=execution_id)
                        )
                        self.logger.info(f"Symbol {symbol} training started with ID: {result_execution_id}")
                    except Exception as e:
                        self.logger.error(f"Training failed for {symbol}: {e}")
                    finally:
                        loop.close()
                
                # Start training thread
                training_thread = threading.Thread(target=run_training, daemon=True)
                training_thread.start()
                
                self.logger.info(f"Symbol addition request received: {symbol}")
                
                return jsonify({
                    'status': 'started',
                    'symbol': symbol,
                    'execution_id': execution_id,
                    'validation_status': validation_result.status,
                    'leverage_limit': validation_result.market_info.get('leverage_limit') if validation_result.market_info else None,
                    'message': f'{symbol}の学習・バックテストを開始しました'
                })
                
            except Exception as e:
                self.logger.error(f"Error adding symbol: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/execution/<execution_id>/status')
        def api_execution_status(execution_id):
            """Get execution status for training/backtesting."""
            try:
                from auto_symbol_training import AutoSymbolTrainer
                trainer = AutoSymbolTrainer()
                
                status = trainer.get_execution_status(execution_id)
                
                if not status:
                    return jsonify({'error': 'Execution not found'}), 404
                
                return jsonify(status)
                
            except Exception as e:
                self.logger.error(f"Error getting execution status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/executions')
        def api_executions_list():
            """Get list of recent executions."""
            try:
                limit = request.args.get('limit', 10, type=int)
                
                from auto_symbol_training import AutoSymbolTrainer
                trainer = AutoSymbolTrainer()
                
                executions = trainer.list_executions(limit=limit)
                
                return jsonify(executions)
                
            except Exception as e:
                self.logger.error(f"Error listing executions: {e}")
                return jsonify({'error': str(e)}), 500
        
        # Scheduler Management Routes
        @self.app.route('/api/scheduler/status')
        def api_scheduler_status():
            """Get scheduler status."""
            try:
                from scheduled_execution_system import ScheduledExecutionSystem
                
                # シングルトンインスタンスまたは状態ファイルから取得
                # TODO: 実際の実装ではシングルトンまたは永続化された状態を使用
                
                # サンプルレスポンス
                return jsonify({
                    'running': False,  # TODO: 実際の状態を取得
                    'total_tasks': 0,
                    'enabled_tasks': 0,
                    'failed_tasks': 0,
                    'next_execution': None,
                    'last_execution': None,
                    'tasks': []
                })
                
            except Exception as e:
                self.logger.error(f"Error getting scheduler status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/scheduler/start', methods=['POST'])
        def api_scheduler_start():
            """Start the scheduler."""
            try:
                # TODO: スケジューラーの開始実装
                # グローバルスケジューラーインスタンスまたはプロセス管理
                
                self.logger.info("Scheduler start requested")
                return jsonify({'status': 'started', 'message': 'スケジューラーを開始しました'})
                
            except Exception as e:
                self.logger.error(f"Error starting scheduler: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/scheduler/stop', methods=['POST'])
        def api_scheduler_stop():
            """Stop the scheduler."""
            try:
                # TODO: スケジューラーの停止実装
                
                self.logger.info("Scheduler stop requested")
                return jsonify({'status': 'stopped', 'message': 'スケジューラーを停止しました'})
                
            except Exception as e:
                self.logger.error(f"Error stopping scheduler: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/scheduler/tasks')
        def api_scheduler_tasks():
            """Get scheduler tasks list."""
            try:
                # TODO: タスク一覧の取得実装
                
                sample_tasks = [
                    {
                        'task_id': 'backtest_HYPE_1h',
                        'type': 'SCHEDULED_BACKTEST',
                        'symbol': 'HYPE',
                        'frequency': 'daily',
                        'enabled': True,
                        'last_executed': None,
                        'next_execution': None,
                        'consecutive_failures': 0
                    },
                    {
                        'task_id': 'ml_training_all_symbols',
                        'type': 'SCHEDULED_TRAINING',
                        'symbols': ['HYPE', 'SOL', 'PEPE'],
                        'frequency': 'weekly',
                        'enabled': True,
                        'last_executed': None,
                        'next_execution': None,
                        'consecutive_failures': 0
                    }
                ]
                
                return jsonify(sample_tasks)
                
            except Exception as e:
                self.logger.error(f"Error getting scheduler tasks: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/scheduler/task/<task_id>/toggle', methods=['POST'])
        def api_scheduler_task_toggle(task_id):
            """Toggle task enabled/disabled."""
            try:
                # TODO: タスクの有効/無効切り替え実装
                
                self.logger.info(f"Task toggle requested: {task_id}")
                return jsonify({'status': 'toggled', 'task_id': task_id})
                
            except Exception as e:
                self.logger.error(f"Error toggling task: {e}")
                return jsonify({'error': str(e)}), 500
        
        # Migration Routes
        @self.app.route('/api/migration/status')
        def api_migration_status():
            """Get migration system status and history."""
            try:
                from legacy_migration_system import LegacyMigrationSystem
                
                migration_system = LegacyMigrationSystem()
                history = migration_system.get_migration_history()
                
                return jsonify({
                    'migration_available': True,
                    'recent_migrations': history[:5],  # 最新5件
                    'backup_directory': str(migration_system.backup_dir),
                    'new_config_exists': migration_system.new_config_path.exists()
                })
                
            except Exception as e:
                self.logger.error(f"Error getting migration status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/migration/dry-run', methods=['POST'])
        def api_migration_dry_run():
            """Run dry-run migration (check only)."""
            try:
                import asyncio
                from legacy_migration_system import LegacyMigrationSystem
                
                self.logger.info("Starting dry-run migration")
                
                migration_system = LegacyMigrationSystem()
                
                # 非同期実行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    summary = loop.run_until_complete(migration_system.dry_run_migration())
                finally:
                    loop.close()
                
                # 結果をJSON serializable形式に変換
                summary_dict = {
                    'total_symbols': summary.total_symbols,
                    'successful_migrations': summary.successful_migrations,
                    'failed_migrations': summary.failed_migrations,
                    'warnings_count': summary.warnings_count,
                    'backup_created': summary.backup_created,
                    'execution_id': summary.execution_id,
                    'started_at': summary.started_at.isoformat(),
                    'completed_at': summary.completed_at.isoformat() if summary.completed_at else None,
                    'results': [
                        {
                            'symbol': result.symbol,
                            'status': result.status.value,
                            'validation_status': result.validation_result.status if result.validation_result else None,
                            'validation_valid': result.validation_result.valid if result.validation_result else None,
                            'error_message': result.error_message,
                            'warnings': result.warnings,
                            'migrated_to_new_system': result.migrated_to_new_system
                        }
                        for result in summary.results
                    ]
                }
                
                return jsonify(summary_dict)
                
            except Exception as e:
                self.logger.error(f"Error in dry-run migration: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/migration/execute', methods=['POST'])
        def api_migration_execute():
            """Execute actual migration."""
            try:
                import asyncio
                from legacy_migration_system import LegacyMigrationSystem
                
                self.logger.info("Starting actual migration")
                
                migration_system = LegacyMigrationSystem()
                
                # 非同期実行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    summary = loop.run_until_complete(migration_system.run_migration(dry_run=False))
                finally:
                    loop.close()
                
                # 結果をJSON serializable形式に変換
                summary_dict = {
                    'total_symbols': summary.total_symbols,
                    'successful_migrations': summary.successful_migrations,
                    'failed_migrations': summary.failed_migrations,
                    'warnings_count': summary.warnings_count,
                    'backup_created': summary.backup_created,
                    'execution_id': summary.execution_id,
                    'started_at': summary.started_at.isoformat(),
                    'completed_at': summary.completed_at.isoformat() if summary.completed_at else None,
                    'results': [
                        {
                            'symbol': result.symbol,
                            'status': result.status.value,
                            'validation_status': result.validation_result.status if result.validation_result else None,
                            'validation_valid': result.validation_result.valid if result.validation_result else None,
                            'error_message': result.error_message,
                            'warnings': result.warnings,
                            'migrated_to_new_system': result.migrated_to_new_system
                        }
                        for result in summary.results
                    ]
                }
                
                return jsonify(summary_dict)
                
            except Exception as e:
                self.logger.error(f"Error in migration execution: {e}")
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