"""
Mock implementation of HighLeverageBotOrchestrator for testing purposes.
"""

import random
from datetime import datetime
from typing import Dict, Any, Optional


class MockHighLeverageBotOrchestrator:
    """Mock implementation for testing the real-time monitoring system."""
    
    def __init__(self):
        self.available = True
        
    def analyze_symbol(self, symbol: str, timeframe: str, strategy: str) -> Optional[Dict[str, Any]]:
        """
        Mock analysis that returns realistic-looking trading data.
        """
        # Simulate occasional analysis failures
        if random.random() < 0.1:  # 10% failure rate
            raise Exception(f"Mock API error for {symbol}")
        
        # Generate mock data based on symbol characteristics
        base_leverage = {
            'HYPE': (8, 25),    # High volatility meme coin
            'SOL': (5, 18),     # Major altcoin
            'WIF': (6, 22),     # Solana meme coin
            'BONK': (4, 15),    # Lower volatility
            'PEPE': (10, 30),   # High risk/reward
        }.get(symbol, (5, 20))
        
        leverage = random.uniform(*base_leverage)
        
        # Confidence correlates with leverage for realism
        if leverage >= 20:
            confidence = random.uniform(85, 95)
        elif leverage >= 15:
            confidence = random.uniform(75, 90)
        elif leverage >= 10:
            confidence = random.uniform(65, 85)
        else:
            confidence = random.uniform(40, 75)
        
        # Mock price data
        base_price = {
            'HYPE': 25.50,
            'SOL': 145.20,
            'WIF': 2.85,
            'BONK': 0.000024,
            'PEPE': 0.00001234
        }.get(symbol, 1.0)
        
        current_price = base_price * random.uniform(0.95, 1.05)
        entry_price = current_price * random.uniform(0.998, 1.002)
        
        # Calculate target and stop loss based on leverage
        price_change = leverage / 100
        target_price = entry_price * (1 + price_change)
        stop_loss = entry_price * (1 - price_change / 3)
        
        # Risk level (inverse of confidence for simplicity)
        risk_level = 100 - confidence + random.uniform(-10, 10)
        risk_level = max(0, min(100, risk_level))
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy': strategy,
            'leverage': round(leverage, 1),
            'confidence': round(confidence, 1),
            'current_price': round(current_price, 6),
            'entry_price': round(entry_price, 6),
            'target_price': round(target_price, 6),
            'stop_loss': round(stop_loss, 6),
            'position_size': random.uniform(500, 2000),
            'risk_reward_ratio': round(leverage / 3, 1),
            'risk_level': round(risk_level, 1),
            'risk_reason': self._get_risk_reason(risk_level),
            'volatility': round(random.uniform(5, 50), 1),
            'timestamp': datetime.now(),
            'mock_data': True  # Flag to indicate this is mock data
        }
    
    def _get_risk_reason(self, risk_level: float) -> str:
        """Generate appropriate risk reason based on risk level."""
        if risk_level >= 80:
            return "Extremely high volatility detected"
        elif risk_level >= 60:
            return "High market uncertainty"
        elif risk_level >= 40:
            return "Moderate risk conditions"
        else:
            return "Low risk environment"