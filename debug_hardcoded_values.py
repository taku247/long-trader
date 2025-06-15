#!/usr/bin/env python3
"""
Debug script to understand where the hardcoded values come from
"""

# Let's calculate what the DefaultSLTPCalculator would produce with a 100.0 base price
current_price = 100.0

# From the DefaultSLTPCalculator code:
# For stop loss - default is 5% without support levels
stop_loss_distance = 0.05  # 5%
stop_loss_price = current_price * (1 - stop_loss_distance)

# For take profit - default is 8% without resistance levels  
take_profit_distance = 0.08  # 8%
take_profit_price = current_price * (1 + take_profit_distance)

print(f"Base price: {current_price}")
print(f"Stop loss price (5%): {stop_loss_price}")
print(f"Take profit price (8%): {take_profit_price}")

# But wait, let me check the exact calculation that would generate 97.61904761904762
# This looks like it might be from a different calculation
print(f"\nChecking if 97.61904761904762 comes from a specific ratio:")
print(f"100 * (1 - 0.0238095) = {100 * (1 - 0.0238095238095)}")

# Let's check leverage-based calculation
leverage = 5.0
max_loss_pct_base = 0.10  # 10%
max_loss_pct = max_loss_pct_base / leverage
stop_loss_leveraged = current_price * (1 - max_loss_pct)
print(f"With leverage {leverage}: max loss {max_loss_pct*100}% = {stop_loss_leveraged}")

# Check the exact value 97.61904761904762
exact_ratio = (100.0 - 97.61904761904762) / 100.0
print(f"The exact ratio for 97.61904761904762: {exact_ratio}")
print(f"This is approximately: {exact_ratio:.10f}")

# Check if this comes from 1/42 ratio
ratio_42 = 1.0 / 42.0
print(f"1/42 = {ratio_42}")
print(f"100 * (1 - 1/42) = {100 * (1 - 1.0/42.0)}")

# The values we commonly see:
print(f"\n=== COMMON HARDCODED VALUES ===")
print(f"Entry: 100.0")
print(f"Take Profit: 105.0 (5% gain)")  
print(f"Stop Loss: 97.61904761904762 (??? ratio)")

# Let's reverse engineer the 97.62 value
target_sl = 97.61904761904762
actual_ratio = (100.0 - target_sl) / 100.0
print(f"\nReverse engineering 97.61904761904762:")
print(f"Ratio: {actual_ratio}")
print(f"1/ratio: {1/actual_ratio}")
print(f"This looks like 1/{1/actual_ratio:.1f}")