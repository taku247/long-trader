#!/usr/bin/env python3
"""
Find the exact source of the 105.0 and 97.61904761904762 values
"""
import sys
import os
import numpy as np
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_exact_conservative_calculation():
    """Test Conservative calculator with exact 100.0 base price"""
    
    # Set the exact same conditions that might generate the hardcoded values
    current_price = 100.0
    leverage = 5.0
    
    print(f"=== TESTING CONSERVATIVE CALCULATOR ===")
    print(f"Current price: {current_price}")
    print(f"Leverage: {leverage}")
    
    try:
        from engines.stop_loss_take_profit_calculators import ConservativeSLTPCalculator
        from interfaces.data_types import MarketContext
        
        # Create market context
        market_context = MarketContext(
            current_price=current_price,
            volume_24h=1000000.0,
            volatility=0.03,
            trend_direction='BULLISH',
            market_phase='MARKUP',
            timestamp=datetime.now()
        )
        
        # Conservative calculator
        sltp_calculator = ConservativeSLTPCalculator()
        
        # Calculate with empty support/resistance (as in scalable_analysis_system.py)
        sltp_levels = sltp_calculator.calculate_levels(
            current_price=current_price,
            leverage=leverage,
            support_levels=[],
            resistance_levels=[],
            market_context=market_context
        )
        
        print(f"\n=== CONSERVATIVE RESULTS ===")
        print(f"Take Profit: {sltp_levels.take_profit_price}")
        print(f"Stop Loss: {sltp_levels.stop_loss_price}")
        print(f"Entry: {current_price}")
        
        # Check for the exact hardcoded values
        print(f"\n=== HARDCODED VALUE CHECK ===")
        print(f"TP = 105.0? {abs(sltp_levels.take_profit_price - 105.0) < 0.01}")
        print(f"SL = 97.62? {abs(sltp_levels.stop_loss_price - 97.61904761904762) < 0.01}")
        
        # Let's manually calculate what Conservative would produce
        print(f"\n=== MANUAL CONSERVATIVE CALCULATION ===")
        
        # From Conservative calculator: fixed 3% stop loss (line 226)
        stop_loss_distance = 0.03  # 3%
        manual_sl = current_price * (1 - stop_loss_distance)
        print(f"Manual SL (3%): {manual_sl}")
        
        # From Conservative calculator: fixed 5% take profit (line 254/257)
        take_profit_distance = 0.05  # 5%
        manual_tp = current_price * (1 + take_profit_distance)
        print(f"Manual TP (5%): {manual_tp}")
        
        print(f"Manual TP = 105.0? {abs(manual_tp - 105.0) < 0.01}")
        print(f"Manual SL = 97.0? {abs(manual_sl - 97.0) < 0.01}")
        
        return sltp_levels
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_with_leverage_adjustment():
    """Test with leverage adjustment that might produce 97.61904761904762"""
    
    current_price = 100.0
    
    print(f"\n=== TESTING LEVERAGE ADJUSTMENT ===")
    
    # Test different leverage values to see if any produce the exact SL value
    for leverage in [1.0, 2.0, 5.0, 10.0, 42.0]:
        print(f"\nTesting leverage: {leverage}")
        
        # Conservative max_loss_pct_base = 0.05 (5%)
        max_loss_pct_base = 0.05
        max_loss_pct = max_loss_pct_base / leverage
        
        # Conservative min_stop_loss_distance = 0.015 (1.5%)
        min_stop_loss_distance = 0.015
        
        # Basic stop loss without support levels would be 0.03 (3%)
        basic_stop_loss_distance = 0.03
        
        # Final distance is max of min and min of basic and leverage-adjusted
        final_distance = max(min_stop_loss_distance, min(basic_stop_loss_distance, max_loss_pct))
        
        stop_loss_price = current_price * (1 - final_distance)
        
        print(f"  Max loss %: {max_loss_pct*100:.2f}%")
        print(f"  Final distance: {final_distance*100:.2f}%")
        print(f"  Stop loss price: {stop_loss_price}")
        print(f"  Matches 97.62? {abs(stop_loss_price - 97.61904761904762) < 0.01}")

def check_exact_ratio():
    """Check what produces the exact 97.61904761904762 ratio"""
    
    print(f"\n=== CHECKING EXACT RATIO ===")
    
    target_sl = 97.61904761904762
    current_price = 100.0
    ratio = (current_price - target_sl) / current_price
    
    print(f"Target SL: {target_sl}")
    print(f"Ratio: {ratio}")
    print(f"Ratio as fraction: {ratio} = 1/{1/ratio}")
    
    # This is exactly 1/42
    print(f"1/42 = {1.0/42.0}")
    print(f"Matches 1/42? {abs(ratio - 1.0/42.0) < 0.0000001}")
    
    # Check if any Conservative calculator logic uses this ratio
    print(f"\nLooking for where 1/42 ratio might be used...")
    print(f"If leverage = 42, max_loss_pct = 0.05/42 = {0.05/42}")
    print(f"If leverage = 2.1, max_loss_pct = 0.05/2.1 = {0.05/2.1}")

if __name__ == "__main__":
    test_exact_conservative_calculation()
    test_with_leverage_adjustment()
    check_exact_ratio()