#!/usr/bin/env python3
"""
Simple test to debug resistance level calculation bug
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

def create_test_data():
    """
    Test data that demonstrates the bug:
    - Price starts at 4.0, goes to 4.6, then drops to 4.2
    - Current price is 4.61
    - Resistance level at 4.24 will be detected (below current price)
    """
    
    # Create sample OHLCV data
    timestamps = pd.date_range('2025-01-01', periods=100, freq='15min')
    
    # Price pattern that creates the bug
    base_prices = []
    for i in range(100):
        if i < 20:
            # Initial period: around 4.0
            price = 4.0 + np.random.uniform(-0.1, 0.1)
        elif i < 40:
            # Rising period: 4.0 to 4.6
            price = 4.0 + (i - 20) * 0.03 + np.random.uniform(-0.05, 0.05)
        elif i < 60:
            # Peak period: around 4.6 (creates resistance level)
            price = 4.6 + np.random.uniform(-0.05, 0.05)
        elif i < 80:
            # Drop period: 4.6 to 4.2
            price = 4.6 - (i - 60) * 0.02 + np.random.uniform(-0.05, 0.05)
        else:
            # Recent period: rising from 4.2 to 4.61
            price = 4.2 + (i - 80) * 0.02 + np.random.uniform(-0.02, 0.02)
        
        base_prices.append(max(price, 3.5))  # Ensure minimum price
    
    # Create OHLCV from base prices
    data = []
    for i, base_price in enumerate(base_prices):
        spread = base_price * 0.005  # 0.5% spread
        high = base_price + np.random.uniform(0, spread)
        low = base_price - np.random.uniform(0, spread)
        open_price = base_price + np.random.uniform(-spread/2, spread/2)
        close = base_price + np.random.uniform(-spread/2, spread/2)
        volume = np.random.uniform(1000, 5000)
        
        data.append({
            'timestamp': timestamps[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    current_price = 4.61  # Set current price higher than old resistance
    
    return df, current_price

def test_resistance_bug():
    """Test the resistance level bug"""
    print("🔍 Resistance Level Bug Test")
    print("=" * 60)
    
    # Create test data
    df, current_price = create_test_data()
    print(f"Test data created: {len(df)} candles")
    print(f"Current price: ${current_price:.2f}")
    print(f"Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
    
    # Import the fractal detection function
    try:
        from support_resistance_visualizer import detect_fractal_levels, cluster_price_levels, calculate_level_details
        
        # Detect fractal levels
        resistance_levels, support_levels = detect_fractal_levels(df)
        print(f"\nFractal detection:")
        print(f"  Resistance candidates: {len(resistance_levels)}")
        print(f"  Support candidates: {len(support_levels)}")
        
        # Analyze resistance levels vs current price
        resistance_above = [r for r in resistance_levels if r[1] > current_price]
        resistance_below = [r for r in resistance_levels if r[1] <= current_price]
        
        print(f"\nResistance analysis:")
        print(f"  Above current price ({current_price:.2f}): {len(resistance_above)}")
        print(f"  Below current price ({current_price:.2f}): {len(resistance_below)} ⚠️")
        
        if resistance_below:
            print(f"\n🚨 BUG DETECTED: Resistance levels below current price")
            for i, (timestamp, price) in enumerate(resistance_below[:5]):
                print(f"    R{i+1}: ${price:.2f} at {timestamp}")
        
        # Cluster the levels
        resistance_clusters = cluster_price_levels(resistance_levels)
        print(f"\nAfter clustering: {len(resistance_clusters)} resistance clusters")
        
        # Check clustered levels
        for i, cluster in enumerate(resistance_clusters[:10]):
            avg_price = np.mean([level[1] for level in cluster])
            status = "ABOVE" if avg_price > current_price else "BELOW ⚠️"
            print(f"  Cluster {i+1}: ${avg_price:.2f} ({status} current price)")
        
        # Test the SL/TP calculation
        print(f"\n" + "=" * 60)
        print("🧪 SL/TP Calculation Test")
        print("=" * 60)
        
        # Create mock support/resistance levels from clusters
        from interfaces import SupportResistanceLevel
        
        support_objects = []
        resistance_objects = []
        
        # Create resistance levels (some may be below current price - this is the bug!)
        for cluster in resistance_clusters[:5]:
            avg_price = np.mean([level[1] for level in cluster])
            level_obj = SupportResistanceLevel(
                price=avg_price,
                strength=0.7,
                level_type='resistance',
                touch_count=len(cluster),
                first_touch=min([level[0] for level in cluster]),
                last_touch=max([level[0] for level in cluster]),
                volume_at_level=1000.0,
                distance_from_current=abs(avg_price - current_price) / current_price
            )
            resistance_objects.append(level_obj)
        
        # Create support levels
        support_clusters = cluster_price_levels(support_levels)
        for cluster in support_clusters[:5]:
            avg_price = np.mean([level[1] for level in cluster])
            if avg_price < current_price:  # Support should be below current price
                level_obj = SupportResistanceLevel(
                    price=avg_price,
                    strength=0.6,
                    level_type='support',
                    touch_count=len(cluster),
                    first_touch=min([level[0] for level in cluster]),
                    last_touch=max([level[0] for level in cluster]),
                    volume_at_level=1000.0,
                    distance_from_current=abs(avg_price - current_price) / current_price
                )
                support_objects.append(level_obj)
        
        print(f"Created {len(resistance_objects)} resistance levels")
        print(f"Created {len(support_objects)} support levels")
        
        # Check which resistance levels are problematic
        problematic_resistance = [r for r in resistance_objects if r.price <= current_price]
        valid_resistance = [r for r in resistance_objects if r.price > current_price]
        
        print(f"\nResistance level analysis:")
        print(f"  Valid (above current): {len(valid_resistance)}")
        print(f"  Problematic (below current): {len(problematic_resistance)}")
        
        if problematic_resistance:
            print(f"\n🚨 PROBLEMATIC RESISTANCE LEVELS:")
            for r in problematic_resistance:
                print(f"    ${r.price:.2f} (strength: {r.strength:.2f})")
        
        # Test SL/TP calculation
        try:
            from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator
            from interfaces import MarketContext
            
            calculator = DefaultSLTPCalculator()
            mock_context = MarketContext(
                trend_direction='up',
                volatility=0.02,
                volume_profile='normal',
                market_phase='trending'
            )
            
            print(f"\n🧮 Attempting SL/TP calculation...")
            print(f"  Current price: ${current_price:.2f}")
            print(f"  Available resistance levels: {len(resistance_objects)}")
            print(f"  Available support levels: {len(support_objects)}")
            
            levels = calculator.calculate_levels(
                current_price=current_price,
                leverage=2.0,
                support_levels=support_objects,
                resistance_levels=resistance_objects,
                market_context=mock_context
            )
            
            print(f"\n✅ Calculation successful:")
            print(f"  Entry price: ${current_price:.2f}")
            print(f"  Take profit: ${levels.take_profit_price:.2f}")
            print(f"  Stop loss: ${levels.stop_loss_price:.2f}")
            
            if levels.take_profit_price <= current_price:
                print(f"🚨 BUG REPRODUCED: Take profit ({levels.take_profit_price:.2f}) <= Entry price ({current_price:.2f})")
            else:
                print(f"✅ No bug: Take profit > Entry price")
                
        except Exception as calc_error:
            print(f"❌ SL/TP calculation error: {calc_error}")
            if "現在価格より上の抵抗線データが不足" in str(calc_error):
                print(f"✅ Level 1 validation working: Proper error thrown")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

def propose_fix():
    """Propose a fix for the resistance level bug"""
    print(f"\n" + "=" * 60)
    print("🔧 PROPOSED FIX")
    print("=" * 60)
    
    print("ROOT CAUSE:")
    print("  - Fractal analysis detects ALL local maxima as resistance")
    print("  - This includes old peaks that are now below current price")
    print("  - These invalid resistance levels cause TP < entry price")
    print()
    
    print("SOLUTION:")
    print("  1. Filter resistance levels to only include those ABOVE current price")
    print("  2. Filter support levels to only include those BELOW current price") 
    print("  3. Add minimum distance requirement (e.g., 0.5% away from current price)")
    print("  4. Prioritize recent levels over old ones")
    print()
    
    print("IMPLEMENTATION:")
    print("  - Modify support_resistance_visualizer.py")
    print("  - Add current_price parameter to find_all_levels()")
    print("  - Filter levels based on position relative to current price")
    print("  - Add recency weighting to prioritize recent levels")

if __name__ == '__main__':
    test_resistance_bug()
    propose_fix()