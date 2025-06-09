"""
Real-time monitoring system for high-leverage trading opportunities.
Phase 1: Automated monitoring and alerting system.
"""

from .monitor import RealTimeMonitor
from .alert_manager import AlertManager, Alert, AlertType, AlertPriority
from .utils.scheduler_utils import TaskScheduler, RateLimiter

__version__ = "1.0.0"
__author__ = "Long Trader Bot"

__all__ = [
    'RealTimeMonitor',
    'AlertManager',
    'Alert',
    'AlertType', 
    'AlertPriority',
    'TaskScheduler',
    'RateLimiter'
]