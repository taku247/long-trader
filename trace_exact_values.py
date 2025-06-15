#!/usr/bin/env python3
"""
Trace the exact source of hardcoded values by replicating the calculation
"""
import sys
import os
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to replicate the exact calculation from scalable_analysis_system.py
def simulate_trade_generation():
    """Simulate the exact trade generation logic"""
    
    # These are the values from the scalable_analysis_system.py
    current_price = 100.0  # Line 285 in scalable_analysis_system.py
    leverage = 5.0  # Default value
    
    print(f"=== SIMULATING TRADE GENERATION ===")
    print(f"Current price: {current_price}")
    print(f"Leverage: {leverage}")
    
    try:
        # Import the calculators as done in scalable_analysis_system.py
        from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator
        from interfaces.data_types import MarketContext
        
        # Create the market context as done in scalable_analysis_system.py (lines 303-310)
        market_context = MarketContext(
            current_price=current_price,
            volume_24h=1000000.0,
            volatility=0.03,
            trend_direction='BULLISH',
            market_phase='MARKUP',
            timestamp=datetime.now()
        )
        
        # Create the calculator
        sltp_calculator = DefaultSLTPCalculator()
        
        # Calculate levels exactly as done in scalable_analysis_system.py (lines 313-319)
        sltp_levels = sltp_calculator.calculate_levels(
            current_price=current_price,
            leverage=leverage,
            support_levels=[],  # Empty as in the original
            resistance_levels=[],  # Empty as in the original
            market_context=market_context
        )
        
        print(f"\n=== CALCULATED VALUES ===")
        print(f"Take Profit: {sltp_levels.take_profit_price}")
        print(f"Stop Loss: {sltp_levels.stop_loss_price}")
        print(f"Entry Price: {current_price}")
        
        # Check if these match our hardcoded values
        expected_tp = 105.0
        expected_sl = 97.61904761904762
        
        print(f"\n=== COMPARISON ===")
        print(f"Expected TP: {expected_tp}, Calculated: {sltp_levels.take_profit_price}, Match: {abs(sltp_levels.take_profit_price - expected_tp) < 0.01}")
        print(f"Expected SL: {expected_sl}, Calculated: {sltp_levels.stop_loss_price}, Match: {abs(sltp_levels.stop_loss_price - expected_sl) < 0.01}")
        
        return sltp_levels
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Simulating with manual calculations...")
        
        # Manual calculation as per DefaultSLTPCalculator logic
        # No support/resistance levels means using default percentages
        stop_loss_distance = 0.05  # 5% from line 83
        take_profit_distance = 0.08  # 8% from line 124
        
        # But we need to check the leverage adjustment
        max_loss_pct_base = 0.10  # 10% from line 31
        max_loss_pct = max_loss_pct_base / leverage  # This would be 2%
        
        # The stop loss distance is the minimum of default and leverage-adjusted
        final_stop_loss_distance = min(stop_loss_distance, max_loss_pct)
        
        stop_loss_price = current_price * (1 - final_stop_loss_distance)
        take_profit_price = current_price * (1 + take_profit_distance)
        
        print(f"\n=== MANUAL CALCULATION ===")
        print(f"Default stop loss distance: {stop_loss_distance} (5%)")
        print(f"Leverage-adjusted max loss: {max_loss_pct} ({max_loss_pct*100}%)")
        print(f"Final stop loss distance: {final_stop_loss_distance}")
        print(f"Stop Loss Price: {stop_loss_price}")
        print(f"Take Profit Price: {take_profit_price}")
        
        return None

if __name__ == "__main__":
    result = simulate_trade_generation()