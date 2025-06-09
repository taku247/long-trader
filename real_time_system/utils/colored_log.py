"""
Colored logging utility for enhanced visual feedback.
Provides colored console output while maintaining normal file logging.
"""

import sys
import logging
from colorama import Fore, Back, Style, init
from datetime import datetime
from typing import Optional, Dict, Any

# Initialize colorama for cross-platform support
init(autoreset=True)


class ColorFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output."""
    
    # Color mappings for different log levels
    LEVEL_COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.BLUE,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    # Special colors for specific message types
    MESSAGE_COLORS = {
        'trading_opportunity': Fore.GREEN + Style.BRIGHT,
        'system_start': Fore.BLUE + Style.BRIGHT,
        'system_stop': Fore.BLUE + Style.BRIGHT,
        'alert_sent': Fore.YELLOW + Style.BRIGHT,
        'success': Fore.GREEN,
        'progress': Fore.CYAN,
    }
    
    def __init__(self, fmt=None, datefmt=None, use_colors=True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record):
        # Get the base formatted message
        message = super().format(record)
        
        if not self.use_colors:
            return message
        
        # Check for special message types in the log message
        lower_msg = record.getMessage().lower()
        special_color = None
        
        for msg_type, color in self.MESSAGE_COLORS.items():
            if msg_type.replace('_', ' ') in lower_msg:
                special_color = color
                break
        
        # Apply color based on level or special type
        if special_color:
            colored_message = f"{special_color}{message}{Style.RESET_ALL}"
        else:
            level_color = self.LEVEL_COLORS.get(record.levelname, '')
            colored_message = f"{level_color}{message}{Style.RESET_ALL}"
        
        return colored_message


class ColoredLogger:
    """Enhanced logger with color support and special formatting."""
    
    def __init__(self, name: str, log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ColorFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler without colors (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def set_level(self, level):
        """Set logging level."""
        self.logger.setLevel(level)
    
    def debug(self, message):
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message):
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message):
        """Log critical message."""
        self.logger.critical(message)
    
    def trading_opportunity(self, symbol: str, leverage: float, confidence: float, strategy: str = None):
        """Log trading opportunity with special formatting."""
        icon = "🎯"
        frame = "=" * 60
        message = f"\n{frame}\n{icon} TRADING OPPORTUNITY DETECTED {icon}\n"
        message += f"Symbol: {symbol}\n"
        message += f"Leverage: {leverage:.1f}x\n"
        message += f"Confidence: {confidence:.1f}%\n"
        if strategy:
            message += f"Strategy: {strategy}\n"
        message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += frame
        
        # Use info level but with special formatting
        self.logger.info(message)
    
    def system_start(self, details: Dict[str, Any] = None):
        """Log system start with special formatting."""
        icon = "🚀"
        message = f"{icon} SYSTEM STARTED {icon}"
        if details:
            message += f" - {details}"
        self.logger.info(message)
    
    def system_stop(self, details: Dict[str, Any] = None):
        """Log system stop with special formatting."""
        icon = "🛑"
        message = f"{icon} SYSTEM STOPPED {icon}"
        if details:
            message += f" - {details}"
        self.logger.info(message)
    
    def alert_sent(self, alert_type: str, target: str = None):
        """Log alert sent with special formatting."""
        icon = "📢"
        message = f"{icon} ALERT SENT: {alert_type}"
        if target:
            message += f" to {target}"
        self.logger.info(message)
    
    def success(self, message: str):
        """Log success message with special formatting."""
        icon = "✅"
        self.logger.info(f"{icon} {message}")
    
    def progress(self, message: str, current: int = None, total: int = None):
        """Log progress message with special formatting."""
        icon = "⏳"
        if current is not None and total is not None:
            percentage = (current / total) * 100
            progress_bar = self._create_progress_bar(percentage)
            message = f"{icon} {message} [{current}/{total}] {progress_bar} {percentage:.1f}%"
        else:
            message = f"{icon} {message}"
        self.logger.info(message)
    
    def health_check(self, status: str, details: Dict[str, Any] = None):
        """Log health check with special formatting."""
        icon = "💓" if status.lower() == "ok" else "🚨"
        message = f"{icon} Health Check: {status}"
        if details:
            message += f" - {details}"
        self.logger.info(message)
    
    def monitor_status(self, symbols: list, uptime: str = None):
        """Log monitoring status with special formatting."""
        icon = "📊"
        message = f"{icon} Monitoring {len(symbols)} symbols: {', '.join(symbols)}"
        if uptime:
            message += f" (Uptime: {uptime})"
        self.logger.info(message)
    
    def task_status(self, task_name: str, status: str, details: str = None):
        """Log task status with special formatting."""
        status_icons = {
            'started': '▶️',
            'completed': '✅',
            'failed': '❌',
            'running': '🔄',
            'queued': '⏸️'
        }
        icon = status_icons.get(status.lower(), '📋')
        message = f"{icon} Task {task_name}: {status}"
        if details:
            message += f" - {details}"
        
        if status.lower() == 'failed':
            self.logger.error(message)
        elif status.lower() == 'completed':
            self.logger.info(message)
        else:
            self.logger.info(message)
    
    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a simple progress bar."""
        filled = int(width * percentage / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}]"


def get_colored_logger(name: str, log_file: Optional[str] = None) -> ColoredLogger:
    """Get a colored logger instance."""
    return ColoredLogger(name, log_file)


# Convenience functions for quick colored output
def print_success(message: str):
    """Print success message in green."""
    print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")

def print_error(message: str):
    """Print error message in red."""
    print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")

def print_warning(message: str):
    """Print warning message in yellow."""
    print(f"{Fore.YELLOW}⚠️ {message}{Style.RESET_ALL}")

def print_info(message: str):
    """Print info message in blue."""
    print(f"{Fore.BLUE}ℹ️ {message}{Style.RESET_ALL}")

def print_trading_opportunity(symbol: str, leverage: float, confidence: float):
    """Print trading opportunity with special formatting."""
    frame = "=" * 50
    print(f"{Fore.GREEN + Style.BRIGHT}")
    print(frame)
    print(f"🎯 TRADING OPPORTUNITY: {symbol}")
    print(f"💰 Leverage: {leverage:.1f}x")
    print(f"🎯 Confidence: {confidence:.1f}%")
    print(f"🕒 Time: {datetime.now().strftime('%H:%M:%S')}")
    print(frame)
    print(Style.RESET_ALL)

def print_system_status(status: str, details: str = None):
    """Print system status with colors."""
    status_colors = {
        'starting': Fore.BLUE,
        'running': Fore.GREEN,
        'stopping': Fore.YELLOW,
        'stopped': Fore.RED,
        'error': Fore.RED + Style.BRIGHT
    }
    
    color = status_colors.get(status.lower(), Fore.WHITE)
    icon = "🔄" if status.lower() == 'running' else "📊"
    
    message = f"{color}{icon} System {status.upper()}"
    if details:
        message += f": {details}"
    message += Style.RESET_ALL
    
    print(message)

def print_banner(title: str, subtitle: str = None):
    """Print a colored banner."""
    width = 60
    print(f"\n{Fore.CYAN + Style.BRIGHT}{'=' * width}")
    print(f"{title:^{width}}")
    if subtitle:
        print(f"{subtitle:^{width}}")
    print(f"{'=' * width}{Style.RESET_ALL}\n")