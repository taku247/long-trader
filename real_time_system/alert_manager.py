"""
Alert management system for real-time trading monitoring.
"""

import json
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import os
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent))
from utils.colored_log import get_colored_logger


class AlertType(Enum):
    TRADING_OPPORTUNITY = "trading_opportunity"
    RISK_WARNING = "risk_warning"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"


class AlertPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    alert_id: str
    alert_type: AlertType
    priority: AlertPriority
    title: str
    message: str
    symbol: Optional[str] = None
    strategy: Optional[str] = None
    timeframe: Optional[str] = None
    leverage: Optional[float] = None
    confidence: Optional[float] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class AlertManager:
    """Manages alerts and notifications for the monitoring system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        log_file = config.get('notifications', {}).get('file', {}).get('log_file', 'logs/alerts.log')
        self.logger = get_colored_logger(__name__, log_file)
        
        # Alert history and rate limiting
        self.alert_history: List[Alert] = []
        self.last_alert_times: Dict[str, datetime] = {}
        self.hourly_alert_count = 0
        self.last_hour_reset = datetime.now()
        
        # Notification settings
        self.discord_enabled = config.get('notifications', {}).get('discord', {}).get('enabled', False)
        self.discord_webhook = config.get('notifications', {}).get('discord', {}).get('webhook_url')
        self.console_enabled = config.get('notifications', {}).get('console', {}).get('enabled', True)
        self.file_enabled = config.get('notifications', {}).get('file', {}).get('enabled', True)
        
        # Alert thresholds
        self.leverage_threshold = config.get('alerts', {}).get('leverage_threshold', 10.0)
        self.confidence_threshold = config.get('alerts', {}).get('confidence_threshold', 70.0)
        self.cooldown_minutes = config.get('alerts', {}).get('cooldown_minutes', 60)
        self.max_alerts_per_hour = config.get('alerts', {}).get('max_alerts_per_hour', 10)
        
        # Database integration
        self.db_enabled = config.get('database', {}).get('enabled', True)
        self.db_writer = None
        if self.db_enabled:
            try:
                from alert_history_system.alert_db_writer import AlertDBWriter
                self.db_writer = AlertDBWriter()
                self.logger.success("Database integration enabled")
            except Exception as e:
                self.logger.warning(f"Could not initialize database writer: {e}")
                self.db_enabled = False
        
        # Initialize log file
        if self.file_enabled:
            self._init_log_file()
    
    def _init_log_file(self):
        """Initialize alert log file."""
        log_dir = os.path.dirname(self.config.get('notifications', {}).get('file', {}).get('log_file', 'logs/alerts.log'))
        os.makedirs(log_dir, exist_ok=True)
    
    def _reset_hourly_count(self):
        """Reset hourly alert count if needed."""
        now = datetime.now()
        if (now - self.last_hour_reset).total_seconds() >= 3600:
            self.hourly_alert_count = 0
            self.last_hour_reset = now
    
    def _can_send_alert(self, alert_key: str) -> bool:
        """Check if alert can be sent based on rate limiting."""
        self._reset_hourly_count()
        
        # Check hourly limit
        if self.hourly_alert_count >= self.max_alerts_per_hour:
            return False
        
        # Check cooldown
        if alert_key in self.last_alert_times:
            time_diff = datetime.now() - self.last_alert_times[alert_key]
            if time_diff.total_seconds() < (self.cooldown_minutes * 60):
                return False
        
        return True
    
    def _record_alert_sent(self, alert_key: str):
        """Record that an alert was sent."""
        self.last_alert_times[alert_key] = datetime.now()
        self.hourly_alert_count += 1
    
    def create_trading_opportunity_alert(self, symbol: str, strategy: str, timeframe: str,
                                       leverage: float, confidence: float, 
                                       details: Dict[str, Any]) -> Alert:
        """Create a trading opportunity alert."""
        
        # Determine priority based on leverage and confidence
        if leverage >= 20 and confidence >= 90:
            priority = AlertPriority.CRITICAL
        elif leverage >= 15 and confidence >= 80:
            priority = AlertPriority.HIGH
        elif leverage >= 10 and confidence >= 70:
            priority = AlertPriority.MEDIUM
        else:
            priority = AlertPriority.LOW
        
        title = f"🎯 Trading Opportunity: {symbol}"
        message = (
            f"**Symbol:** {symbol}\\n"
            f"**Strategy:** {strategy}\\n"
            f"**Timeframe:** {timeframe}\\n"
            f"**Leverage:** {leverage:.1f}x\\n"
            f"**Confidence:** {confidence:.1f}%\\n"
            f"**Entry Price:** ${details.get('entry_price', 'N/A')}\\n"
            f"**Target:** ${details.get('target_price', 'N/A')}\\n"
            f"**Stop Loss:** ${details.get('stop_loss', 'N/A')}"
        )
        
        alert = Alert(
            alert_id=f"trade_{symbol}_{strategy}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            alert_type=AlertType.TRADING_OPPORTUNITY,
            priority=priority,
            title=title,
            message=message,
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            leverage=leverage,
            confidence=confidence,
            metadata=details
        )
        
        return alert
    
    def create_risk_warning_alert(self, symbol: str, risk_level: float, 
                                 reason: str, details: Dict[str, Any]) -> Alert:
        """Create a risk warning alert."""
        
        if risk_level >= 80:
            priority = AlertPriority.CRITICAL
            emoji = "🚨"
        elif risk_level >= 60:
            priority = AlertPriority.HIGH
            emoji = "⚠️"
        else:
            priority = AlertPriority.MEDIUM
            emoji = "⚡"
        
        title = f"{emoji} Risk Warning: {symbol}"
        message = (
            f"**Symbol:** {symbol}\\n"
            f"**Risk Level:** {risk_level:.1f}%\\n"
            f"**Reason:** {reason}\\n"
            f"**Current Price:** ${details.get('current_price', 'N/A')}\\n"
            f"**Volatility:** {details.get('volatility', 'N/A')}%"
        )
        
        alert = Alert(
            alert_id=f"risk_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            alert_type=AlertType.RISK_WARNING,
            priority=priority,
            title=title,
            message=message,
            symbol=symbol,
            metadata=details
        )
        
        return alert
    
    def create_system_status_alert(self, status: str, message: str, 
                                  details: Dict[str, Any] = None) -> Alert:
        """Create a system status alert."""
        
        status_emojis = {
            'started': '🟢',
            'stopped': '🔴',
            'error': '💥',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        
        emoji = status_emojis.get(status, '📊')
        priority = AlertPriority.HIGH if status in ['error', 'stopped'] else AlertPriority.MEDIUM
        
        title = f"{emoji} System {status.title()}"
        
        alert = Alert(
            alert_id=f"system_{status}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            alert_type=AlertType.SYSTEM_STATUS,
            priority=priority,
            title=title,
            message=message,
            metadata=details or {}
        )
        
        return alert
    
    def _send_discord_notification(self, alert: Alert) -> bool:
        """Send Discord notification."""
        if not self.discord_enabled or not self.discord_webhook:
            return False
        
        try:
            # Choose color based on priority
            color_map = {
                AlertPriority.LOW: 0x95a5a6,      # Gray
                AlertPriority.MEDIUM: 0xf39c12,   # Orange
                AlertPriority.HIGH: 0xe74c3c,     # Red
                AlertPriority.CRITICAL: 0x8e44ad  # Purple
            }
            
            embed = {
                "title": alert.title,
                "description": alert.message,
                "color": color_map.get(alert.priority, 0x3498db),
                "timestamp": alert.timestamp.isoformat(),
                "footer": {
                    "text": f"Long Trader Bot • {alert.alert_type.value}"
                }
            }
            
            # Add fields for trading opportunities
            if alert.alert_type == AlertType.TRADING_OPPORTUNITY:
                embed["fields"] = [
                    {"name": "Leverage", "value": f"{alert.leverage:.1f}x", "inline": True},
                    {"name": "Confidence", "value": f"{alert.confidence:.1f}%", "inline": True},
                    {"name": "Strategy", "value": alert.strategy, "inline": True}
                ]
            
            payload = {
                "embeds": [embed]
            }
            
            # Add mention if configured
            mention_role = self.config.get('notifications', {}).get('discord', {}).get('mention_role')
            if mention_role and alert.priority in [AlertPriority.HIGH, AlertPriority.CRITICAL]:
                payload["content"] = f"<@&{mention_role}>"
            
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.success(f"Discord notification sent for alert {alert.alert_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Discord notification: {e}")
            return False
    
    def _log_alert(self, alert: Alert):
        """Log alert to console and file."""
        log_message = (
            f"[{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"{alert.priority.value.upper()} - {alert.title}: {alert.message}"
        )
        
        # Console logging with enhanced formatting
        if self.console_enabled:
            # Format message based on alert type and priority
            if alert.alert_type == AlertType.TRADING_OPPORTUNITY:
                self.logger.trading_opportunity(
                    alert.symbol or "Unknown",
                    alert.leverage or 0,
                    alert.confidence or 0,
                    alert.strategy
                )
            elif alert.alert_type == AlertType.SYSTEM_STATUS:
                if "started" in alert.message.lower():
                    self.logger.system_start(alert.message)
                elif "stopped" in alert.message.lower():
                    self.logger.system_stop(alert.message)
                else:
                    self.logger.info(log_message)
            elif alert.priority == AlertPriority.CRITICAL:
                self.logger.critical(log_message)
            elif alert.priority == AlertPriority.HIGH:
                self.logger.error(log_message)
            elif alert.priority == AlertPriority.MEDIUM:
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)
        
        # File logging
        if self.file_enabled:
            log_file = self.config.get('notifications', {}).get('file', {}).get('log_file', 'logs/alerts.log')
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(log_message + '\\n')
            except Exception as e:
                self.logger.error(f"Failed to write to alert log file: {e}")
    
    def send_alert(self, alert: Alert) -> bool:
        """Send an alert through all configured channels."""
        
        # Create alert key for rate limiting
        alert_key = f"{alert.alert_type.value}_{alert.symbol or 'system'}"
        
        # Check rate limiting
        if not self._can_send_alert(alert_key):
            self.logger.warning(f"Alert rate limited: {alert_key}")
            return False
        
        # Add to history
        self.alert_history.append(alert)
        
        # Keep only last 1000 alerts in memory
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        # Save to database
        if self.db_enabled and self.db_writer and alert.alert_type == AlertType.TRADING_OPPORTUNITY:
            try:
                alert_data = {
                    'alert_id': alert.alert_id,
                    'symbol': alert.symbol,
                    'alert_type': alert.alert_type.value,
                    'priority': alert.priority.value,
                    'timestamp': alert.timestamp,
                    'leverage': alert.leverage,
                    'confidence': alert.confidence,
                    'strategy': alert.strategy,
                    'timeframe': alert.timeframe,
                    'metadata': alert.metadata or {}
                }
                
                if self.db_writer.save_trading_opportunity_alert(alert_data):
                    self.logger.success(f"Alert saved to database: {alert.alert_id}")
                else:
                    self.logger.warning(f"Failed to save alert to database: {alert.alert_id}")
            except Exception as e:
                self.logger.error(f"Database save error: {e}")
        
        # Send through all channels
        success = True
        
        # Discord notification
        if self.discord_enabled:
            discord_success = self._send_discord_notification(alert)
            if discord_success:
                self.logger.alert_sent(f"{alert.alert_type.value}", "Discord")
            else:
                self.logger.error(f"Failed to send Discord notification for {alert.alert_type.value}")
            success = success and discord_success
        
        # Console and file logging
        self._log_alert(alert)
        
        # Record that alert was sent
        self._record_alert_sent(alert_key)
        
        return success
    
    def get_alert_history(self, limit: int = 50, 
                         alert_type: Optional[AlertType] = None,
                         symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get alert history."""
        
        filtered_alerts = self.alert_history
        
        # Filter by type
        if alert_type:
            filtered_alerts = [a for a in filtered_alerts if a.alert_type == alert_type]
        
        # Filter by symbol
        if symbol:
            filtered_alerts = [a for a in filtered_alerts if a.symbol == symbol]
        
        # Sort by timestamp (newest first)
        filtered_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Convert to dict and limit
        result = []
        for alert in filtered_alerts[:limit]:
            alert_dict = asdict(alert)
            alert_dict['timestamp'] = alert.timestamp.isoformat()
            alert_dict['alert_type'] = alert.alert_type.value
            alert_dict['priority'] = alert.priority.value
            result.append(alert_dict)
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        now = datetime.now()
        
        # Count alerts by type in last 24 hours
        last_24h = now - timedelta(hours=24)
        recent_alerts = [a for a in self.alert_history if a.timestamp >= last_24h]
        
        stats = {
            'total_alerts': len(self.alert_history),
            'alerts_last_24h': len(recent_alerts),
            'alerts_this_hour': self.hourly_alert_count,
            'by_type': {},
            'by_priority': {},
            'by_symbol': {}
        }
        
        for alert in recent_alerts:
            # By type
            alert_type = alert.alert_type.value
            stats['by_type'][alert_type] = stats['by_type'].get(alert_type, 0) + 1
            
            # By priority
            priority = alert.priority.value
            stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
            
            # By symbol
            if alert.symbol:
                stats['by_symbol'][alert.symbol] = stats['by_symbol'].get(alert.symbol, 0) + 1
        
        return stats
    
    def test_notifications(self) -> Dict[str, bool]:
        """Test all notification channels."""
        results = {}
        
        # Test Discord
        if self.discord_enabled:
            test_alert = Alert(
                alert_id="test_discord",
                alert_type=AlertType.SYSTEM_STATUS,
                priority=AlertPriority.MEDIUM,
                title="🧪 Discord Test",
                message="This is a test notification from Long Trader Bot"
            )
            results['discord'] = self._send_discord_notification(test_alert)
        else:
            results['discord'] = True  # Pass test if disabled
        
        # Test console/file logging
        test_alert = Alert(
            alert_id="test_logging",
            alert_type=AlertType.SYSTEM_STATUS,
            priority=AlertPriority.MEDIUM,
            title="Test Logging",
            message="This is a test log message"
        )
        
        try:
            self._log_alert(test_alert)
            self.logger.success("Logging test completed successfully")
            results['logging'] = True
        except Exception as e:
            self.logger.error(f"Logging test failed: {e}")
            results['logging'] = False
        
        return results