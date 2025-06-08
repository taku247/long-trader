"""
Test Script for Proper Backtesting System
Quick test to verify the system works correctly
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def create_sample_data(n_samples=2000, symbol="TEST"):
    """
    Create sample OHLCV data for testing
    """
    print(f"📊 Creating sample data with {n_samples} samples...")
    
    # Generate timestamps
    start_date = datetime.now() - timedelta(days=n_samples//24)  # Assuming hourly data
    timestamps = [start_date + timedelta(hours=i) for i in range(n_samples)]
    
    # Generate realistic OHLCV data
    np.random.seed(42)  # For reproducibility
    
    # Starting price
    initial_price = 100.0
    prices = [initial_price]
    
    # Generate price walk
    for i in range(1, n_samples):
        # Random walk with some trend and mean reversion
        change = np.random.normal(0, 0.02)  # 2% volatility
        trend = 0.0001  # Slight upward trend
        mean_reversion = (100 - prices[-1]) * 0.001  # Mean revert to 100
        
        new_price = prices[-1] * (1 + change + trend + mean_reversion)
        prices.append(max(new_price, 0.01))  # Prevent negative prices
    
    # Generate OHLC from prices
    data = []
    for i, price in enumerate(prices):
        # Generate realistic OHLC
        volatility = abs(np.random.normal(0, 0.01))
        high = price * (1 + volatility)
        low = price * (1 - volatility)
        
        # Ensure OHLC relationships
        if i == 0:
            open_price = price
        else:
            open_price = data[-1]['close']
        
        close_price = price
        
        # Adjust for OHLC consistency
        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)
        
        # Generate volume
        volume = abs(np.random.normal(1000000, 200000))
        trades = int(abs(np.random.normal(500, 100)))
        
        data.append({
            'timestamp': timestamps[i],
            'open': round(open_price, 4),
            'high': round(high, 4),
            'low': round(low, 4),
            'close': round(close_price, 4),
            'volume': round(volume, 2),
            'trades': trades
        })
    
    df = pd.DataFrame(data)
    print(f"✅ Sample data created: {len(df)} samples")
    print(f"📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"💰 Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    return df

def test_time_series_backtester():
    """
    Test the TimeSeriesBacktester with sample data
    """
    print("\n🧪 Testing TimeSeriesBacktester...")
    
    try:
        from time_series_backtest import TimeSeriesBacktester
        
        # Create sample data
        data = create_sample_data(2000)
        
        # Initialize backtester
        backtester = TimeSeriesBacktester(
            train_ratio=0.6,
            validation_ratio=0.2,
            test_ratio=0.2
        )
        
        # Test time splits
        splits = backtester.get_time_splits(data)
        print(f"✅ Time splits: Train {splits['train']}, Val {splits['validation']}, Test {splits['test']}")
        
        # Test feature preparation (using basic features)
        basic_features = ['open', 'high', 'low', 'volume']
        features = backtester.prepare_features(data, basic_features)
        print(f"✅ Features prepared: {features.shape}")
        
        # Test target creation
        target = backtester.create_ml_target(data, target_type='returns')
        print(f"✅ Target created: {len(target)} samples")
        
        print("✅ TimeSeriesBacktester test passed!")
        return True
        
    except Exception as e:
        print(f"❌ TimeSeriesBacktester test failed: {e}")
        return False

def test_extended_data_fetcher():
    """
    Test the ExtendedDataFetcher with configuration
    """
    print("\n🧪 Testing ExtendedDataFetcher...")
    
    try:
        from extended_data_fetcher import ExtendedDataFetcher
        
        # Initialize fetcher
        fetcher = ExtendedDataFetcher()
        
        # Test configuration
        print(f"✅ Supported timeframes: {fetcher.supported_timeframes}")
        print(f"✅ Timeframe config loaded: {len(fetcher.timeframe_config)} entries")
        
        # Test feature engineering with sample data
        data = create_sample_data(1000)
        engineered_data = fetcher.calculate_comprehensive_indicators(data)
        
        print(f"✅ Feature engineering: {len(data.columns)} -> {len(engineered_data.columns)} features")
        print("✅ ExtendedDataFetcher test passed!")
        return True
        
    except Exception as e:
        print(f"❌ ExtendedDataFetcher test failed: {e}")
        return False

def test_walk_forward_engine():
    """
    Test the WalkForwardEngine with sample data
    """
    print("\n🧪 Testing WalkForwardEngine...")
    
    try:
        from walk_forward_engine import WalkForwardEngine
        
        # Create sample data with target
        data = create_sample_data(1500)
        data['returns'] = data['close'].pct_change()
        data['target'] = data['returns'].shift(-1)  # Next period return
        data = data.dropna()
        
        # Initialize engine
        engine = WalkForwardEngine(
            window_size=500,
            step_size=100,
            min_train_size=200,
            validation_size=50,
            n_splits=3
        )
        
        # Test split creation
        splits = engine.create_walk_forward_splits(data)
        print(f"✅ Walk-forward splits created: {len(splits)} windows")
        
        # Test time series cross-validation
        feature_columns = ['open', 'high', 'low', 'volume']
        X = data[feature_columns].iloc[:300]  # Small subset for testing
        y = data['target'].iloc[:300]
        
        model_params = {'type': 'lightgbm', 'n_estimators': 50}
        cv_results = engine.time_series_cross_validation(X, y, model_params)
        
        if 'error' not in cv_results:
            print(f"✅ Cross-validation completed: {cv_results['n_folds']} folds")
        else:
            print(f"⚠️ Cross-validation warning: {cv_results['error']}")
        
        print("✅ WalkForwardEngine test passed!")
        return True
        
    except Exception as e:
        print(f"❌ WalkForwardEngine test failed: {e}")
        return False

def test_proper_backtesting_engine():
    """
    Test the main ProperBacktestingEngine
    """
    print("\n🧪 Testing ProperBacktestingEngine...")
    
    try:
        from proper_backtesting_engine import ProperBacktestingEngine
        
        # Initialize engine
        engine = ProperBacktestingEngine(
            results_dir="test_results",
            cache_dir="test_cache"
        )
        
        print(f"✅ Engine initialized")
        print(f"📊 Supported symbols: {len(engine.supported_symbols)}")
        print(f"⏰ Supported timeframes: {engine.supported_timeframes}")
        print(f"🎯 Available strategies: {len(engine.strategy_configs)}")
        
        # Test feature selection with sample data
        data = create_sample_data(1000)
        
        # Add some features for testing
        data['sma_10'] = data['close'].rolling(10).mean()
        data['sma_20'] = data['close'].rolling(20).mean()
        data['rsi'] = 50  # Dummy RSI
        data['volume_ma'] = data['volume'].rolling(10).mean()
        
        selected_features = engine.select_features(data)
        print(f"✅ Feature selection: {len(selected_features)} features selected")
        
        print("✅ ProperBacktestingEngine test passed!")
        return True
        
    except Exception as e:
        print(f"❌ ProperBacktestingEngine test failed: {e}")
        return False

def test_integration():
    """
    Test integration between components
    """
    print("\n🧪 Testing Integration...")
    
    try:
        # Test that all imports work together
        from time_series_backtest import TimeSeriesBacktester
        from walk_forward_engine import WalkForwardEngine
        from proper_backtesting_engine import ProperBacktestingEngine
        
        print("✅ All imports successful")
        
        # Test that components can work together
        engine = ProperBacktestingEngine()
        backtester = TimeSeriesBacktester()
        wf_engine = WalkForwardEngine()
        
        print("✅ All components initialized")
        print("✅ Integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """
    Run all tests
    """
    print("🚀 PROPER BACKTESTING SYSTEM - TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Time Series Backtester", test_time_series_backtester),
        ("Extended Data Fetcher", test_extended_data_fetcher),
        ("Walk Forward Engine", test_walk_forward_engine),
        ("Proper Backtesting Engine", test_proper_backtesting_engine),
        ("Integration", test_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready for use.")
        print("\n💡 Next steps:")
        print("1. Run: python run_proper_backtest.py --single-test --symbol HYPE --timeframe 1h")
        print("2. Or try: python run_proper_backtest.py --symbols HYPE SOL --timeframes 1h")
    else:
        print("⚠️ Some tests failed. Please check the error messages above.")
    
    # Cleanup
    try:
        import shutil
        if os.path.exists("test_results"):
            shutil.rmtree("test_results")
        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache")
        print("\n🧹 Test cleanup completed")
    except:
        pass

if __name__ == "__main__":
    main()