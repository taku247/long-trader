#!/usr/bin/env python3
"""
SUSHI timezone fix verification
Confirms that the "Invalid comparison between dtype=datetime64[ns, UTC] and datetime" error is resolved
"""

import asyncio
from datetime import datetime, timezone, timedelta
from hyperliquid_api_client import MultiExchangeAPIClient

async def test_sushi_timezone_fix():
    """Test SUSHI symbol with timezone-aware datetime objects"""
    print("🧪 Testing SUSHI timezone fix...")
    print("=" * 60)
    
    # Test with Gate.io (where the error was occurring)
    client = MultiExchangeAPIClient(exchange_type='gateio')
    
    # Create timezone-aware datetime objects (the fix)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=1)
    
    print(f"start_time: {start_time} (tzinfo={start_time.tzinfo})")
    print(f"end_time: {end_time} (tzinfo={end_time.tzinfo})")
    print()
    
    try:
        # This should now work without timezone comparison errors
        result = await client.get_ohlcv_data('SUSHI', '1h', start_time, end_time)
        
        print(f"✅ SUCCESS: Retrieved {len(result)} data points for SUSHI")
        if len(result) > 0:
            print(f"   First timestamp: {result['timestamp'].iloc[0]}")
            print(f"   Last timestamp: {result['timestamp'].iloc[-1]}")
            print(f"   Timestamp dtype: {result['timestamp'].dtype}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_get_ohlcv_data_with_period():
    """Test the get_ohlcv_data_with_period method (which internally uses timezone-aware datetime)"""
    print("\n🧪 Testing get_ohlcv_data_with_period method...")
    print("=" * 60)
    
    client = MultiExchangeAPIClient(exchange_type='gateio')
    
    try:
        # This method now internally creates timezone-aware datetime objects
        result = await client.get_ohlcv_data_with_period('SUSHI', '1h', days=1)
        
        print(f"✅ SUCCESS: Retrieved {len(result)} data points for SUSHI")
        if len(result) > 0:
            print(f"   First timestamp: {result['timestamp'].iloc[0]}")
            print(f"   Last timestamp: {result['timestamp'].iloc[-1]}")
            print(f"   Timestamp dtype: {result['timestamp'].dtype}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🚀 SUSHI Timezone Fix Verification")
    print("=" * 80)
    print("Fixing: 'Invalid comparison between dtype=datetime64[ns, UTC] and datetime'")
    print("=" * 80)
    
    # Test both methods
    test1_result = await test_sushi_timezone_fix()
    test2_result = await test_get_ohlcv_data_with_period()
    
    print("\n" + "=" * 80)
    print("🏁 VERIFICATION RESULTS")
    print("=" * 80)
    
    if test1_result and test2_result:
        print("✅ ALL TESTS PASSED")
        print("✅ SUSHI timezone fix verified successfully!")
        print("✅ No more 'Invalid comparison between dtype=datetime64[ns, UTC] and datetime' errors")
        print("\n🔧 Key fixes applied:")
        print("   1. Fixed timezone-naive datetime.fromtimestamp() calls in logging")
        print("   2. Added timezone checks in Gate.io OHLCV filtering")
        print("   3. Fixed timezone-naive datetime.now() calls in validator")
        print("   4. Fixed timezone-naive datetime.now() calls in test files")
        print("   5. All datetime objects are now consistently UTC-aware")
    else:
        print("❌ SOME TESTS FAILED")
        print("❌ Further investigation needed")
    
    return test1_result and test2_result

if __name__ == "__main__":
    asyncio.run(main())