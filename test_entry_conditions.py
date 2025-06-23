#!/usr/bin/env python3
"""
Test script to check entry conditions and why analyses table is empty
"""

def test_entry_conditions():
    """Test the entry conditions logic"""
    
    # Simulate the conditions from the debug output
    leverage = 1.0
    confidence = 0.462  # 46.2%
    risk_reward = 1.1
    
    # Load the conditions from config
    try:
        import json
        with open('config/trading_conditions.json', 'r') as f:
            config = json.load(f)
        
        # Get 1h timeframe conditions
        conditions = config['entry_conditions_by_timeframe']['1h']
        
        print("=== Entry Conditions Analysis ===")
        print(f"Timeframe: 1h")
        print(f"Required conditions:")
        print(f"  min_leverage: {conditions['min_leverage']}")
        print(f"  min_confidence: {conditions['min_confidence']}")
        print(f"  min_risk_reward: {conditions['min_risk_reward']}")
        
        print(f"\nActual values from debug:")
        print(f"  leverage: {leverage}")
        print(f"  confidence: {confidence}")
        print(f"  risk_reward: {risk_reward}")
        
        print(f"\nCondition checks:")
        leverage_ok = leverage >= conditions['min_leverage']
        confidence_ok = confidence >= conditions['min_confidence']
        risk_reward_ok = risk_reward >= conditions['min_risk_reward']
        
        print(f"  leverage: {leverage} >= {conditions['min_leverage']} = {leverage_ok}")
        print(f"  confidence: {confidence} >= {conditions['min_confidence']} = {confidence_ok}")
        print(f"  risk_reward: {risk_reward} >= {conditions['min_risk_reward']} = {risk_reward_ok}")
        
        all_ok = leverage_ok and confidence_ok and risk_reward_ok
        print(f"\nAll conditions met: {all_ok}")
        
        if not all_ok:
            print("\n❌ ENTRY CONDITIONS NOT MET - This is why no trades are generated!")
            if not risk_reward_ok:
                print(f"   Main issue: Risk-reward ratio {risk_reward} < required {conditions['min_risk_reward']}")
        else:
            print("\n✅ Entry conditions met - trades should be generated")
            
    except Exception as e:
        print(f"Error: {e}")

def check_database_state():
    """Check the current state of both databases"""
    
    print("\n=== Database State Check ===")
    
    # Check execution_logs.db
    try:
        import sqlite3
        
        # Execution logs database
        print("Execution logs database:")
        with sqlite3.connect('execution_logs.db') as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
            count = cursor.fetchone()[0]
            print(f"  Total execution logs: {count}")
            
            cursor = conn.execute("SELECT COUNT(*) FROM execution_logs WHERE status = 'SUCCESS'")
            success_count = cursor.fetchone()[0]
            print(f"  SUCCESS status logs: {success_count}")
            
            cursor = conn.execute("SELECT symbol, status FROM execution_logs ORDER BY created_at DESC LIMIT 5")
            recent = cursor.fetchall()
            print(f"  Recent logs: {recent}")
    
    except Exception as e:
        print(f"  Error checking execution logs: {e}")
    
    # Check analyses database
    try:
        print("\nAnalyses database:")
        with sqlite3.connect('large_scale_analysis/analysis.db') as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM analyses")
            count = cursor.fetchone()[0]
            print(f"  Total analyses: {count}")
            
            cursor = conn.execute("SELECT symbol, timeframe, config FROM analyses ORDER BY generated_at DESC LIMIT 5")
            recent = cursor.fetchall()
            print(f"  Recent analyses: {recent}")
    
    except Exception as e:
        print(f"  Error checking analyses: {e}")

if __name__ == "__main__":
    test_entry_conditions()
    check_database_state()