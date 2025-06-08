"""
Demo Script for Proper Backtesting System
Demonstrates how to use the new time series backtesting system
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def demo_single_backtest():
    """
    Demonstrate a single backtest with proper time series methodology
    """
    print("🧪 DEMO: Single Backtest with Time Series Methodology")
    print("=" * 60)
    
    try:
        from proper_backtesting_engine import ProperBacktestingEngine
        
        # Initialize the engine
        engine = ProperBacktestingEngine(
            results_dir="demo_results",
            cache_dir="demo_cache"
        )
        
        print("✅ Engine initialized")
        print(f"📊 Available strategies: {list(engine.strategy_configs.keys())}")
        
        # Configuration for demo
        symbol = "HYPE"
        timeframe = "1h"
        strategy = "ML_Conservative"
        
        print(f"\n🎯 Running backtest:")
        print(f"   Symbol: {symbol}")
        print(f"   Timeframe: {timeframe}")
        print(f"   Strategy: {strategy}")
        print(f"   Method: Time series split with walk-forward analysis")
        
        # Run the backtest
        result = engine.run_single_backtest(
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy,
            use_walk_forward=True
        )
        
        if 'error' in result:
            print(f"❌ Backtest failed: {result['error']}")
            return False
        
        # Display results
        print(f"\n📊 BACKTEST RESULTS")
        print(f"=" * 40)
        print(f"✅ Backtest completed successfully!")
        print(f"📈 Data samples used: {result.get('data_samples', 'N/A')}")
        print(f"🔧 ML features: {result.get('feature_count', 'N/A')}")
        print(f"⚙️ Methodology: {result.get('methodology', 'N/A')}")
        
        # Trading performance
        if 'trading_results' in result and 'metrics' in result['trading_results']:
            metrics = result['trading_results']['metrics']
            if 'error' not in metrics:
                print(f"\n💰 TRADING PERFORMANCE:")
                print(f"   Total trades: {metrics.get('total_trades', 0)}")
                print(f"   Win rate: {metrics.get('win_rate', 0)*100:.1f}%")
                print(f"   Total return: {metrics.get('total_return', 0)*100:.2f}%")
                print(f"   Sharpe ratio: {metrics.get('sharpe_ratio', 0):.3f}")
                print(f"   Max drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%")
        
        # ML model performance
        if 'performance_metrics' in result:
            ml_metrics = result['performance_metrics']
            if 'error' not in ml_metrics and 'correlation' in ml_metrics:
                print(f"\n🤖 ML MODEL PERFORMANCE:")
                print(f"   Prediction correlation: {ml_metrics.get('correlation', 0):.3f}")
                print(f"   R-squared: {ml_metrics.get('r_squared', 0):.3f}")
        
        print(f"\n📁 Results saved in: demo_results/")
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

def demo_comprehensive_backtest():
    """
    Demonstrate comprehensive backtesting across multiple parameters
    """
    print("\n🔬 DEMO: Comprehensive Backtest")
    print("=" * 60)
    
    try:
        from proper_backtesting_engine import ProperBacktestingEngine
        
        # Initialize the engine
        engine = ProperBacktestingEngine(
            results_dir="demo_results",
            cache_dir="demo_cache"
        )
        
        # Test configuration (limited for demo)
        symbols = ["HYPE"]  # Single symbol for faster demo
        timeframes = ["1h"]  # Single timeframe for faster demo
        strategies = ["ML_Conservative", "ML_Aggressive"]
        
        print(f"🎯 Testing configuration:")
        print(f"   Symbols: {symbols}")
        print(f"   Timeframes: {timeframes}")
        print(f"   Strategies: {strategies}")
        print(f"   Total combinations: {len(symbols) * len(timeframes) * len(strategies)}")
        
        # Run comprehensive backtest
        results = engine.run_comprehensive_backtest(
            symbols=symbols,
            timeframes=timeframes,
            strategies=strategies,
            max_workers=2  # Reduced for demo
        )
        
        # Display summary
        if 'summary' in results and 'stats' in results['summary']:
            stats = results['summary']['stats']
            
            print(f"\n📊 COMPREHENSIVE RESULTS:")
            print(f"   Tests completed: {stats.get('total_tests', 0)}")
            print(f"   Average win rate: {stats.get('avg_win_rate', 0)*100:.1f}%")
            print(f"   Average return: {stats.get('avg_total_return', 0)*100:.2f}%")
            print(f"   Best strategy: {stats.get('best_strategy', 'N/A')}")
            print(f"   Best return: {stats.get('best_return', 0)*100:.2f}%")
            
            # Performance by strategy
            print(f"\n🎯 PERFORMANCE BY STRATEGY:")
            for strategy, return_val in stats.get('by_strategy', {}).items():
                print(f"   {strategy}: {return_val*100:.2f}%")
        
        # Failed tests
        if 'failed_tests' in results and results['failed_tests']:
            print(f"\n❌ Failed tests: {len(results['failed_tests'])}")
            for symbol, timeframe, strategy, error in results['failed_tests'][:3]:  # Show first 3
                print(f"   {symbol} {timeframe} {strategy}: {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive demo failed: {e}")
        return False

def demo_custom_strategy():
    """
    Demonstrate creating and testing a custom strategy
    """
    print("\n🎨 DEMO: Custom Strategy Configuration")
    print("=" * 60)
    
    try:
        from proper_backtesting_engine import ProperBacktestingEngine
        
        # Initialize the engine
        engine = ProperBacktestingEngine(
            results_dir="demo_results",
            cache_dir="demo_cache"
        )
        
        # Create a custom strategy
        custom_strategy = {
            'Custom_Demo': {
                'description': 'Custom demo strategy with moderate risk',
                'ml_threshold': 0.018,
                'base_leverage': 2.5,
                'max_leverage': 4.0,
                'stop_loss': 0.035,
                'take_profit': 0.07,
                'min_confidence': 0.28,
                'risk_management': 'balanced',
                'use_sr_levels': True,
                'use_traditional_signals': True
            }
        }
        
        # Add custom strategy to engine
        engine.strategy_configs.update(custom_strategy)
        
        print(f"✅ Custom strategy created: Custom_Demo")
        print(f"📋 Strategy parameters:")
        for key, value in custom_strategy['Custom_Demo'].items():
            if key != 'description':
                print(f"   {key}: {value}")
        
        # Test the custom strategy
        result = engine.run_single_backtest(
            symbol="HYPE",
            timeframe="1h",
            strategy_name="Custom_Demo",
            use_walk_forward=False  # Use simple split for faster demo
        )
        
        if 'error' not in result:
            print(f"\n✅ Custom strategy test completed!")
            
            # Show brief results
            if 'trading_results' in result and 'metrics' in result['trading_results']:
                metrics = result['trading_results']['metrics']
                if 'error' not in metrics:
                    print(f"📈 Total return: {metrics.get('total_return', 0)*100:.2f}%")
                    print(f"🎯 Win rate: {metrics.get('win_rate', 0)*100:.1f}%")
                    print(f"📊 Total trades: {metrics.get('total_trades', 0)}")
        else:
            print(f"❌ Custom strategy test failed: {result['error']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Custom strategy demo failed: {e}")
        return False

def demo_walk_forward_analysis():
    """
    Demonstrate walk-forward analysis
    """
    print("\n🔄 DEMO: Walk-Forward Analysis")
    print("=" * 60)
    
    try:
        from walk_forward_engine import WalkForwardEngine
        from extended_data_fetcher import ExtendedDataFetcher
        
        # Create sample data for demonstration
        print("📊 Creating sample data for walk-forward analysis...")
        
        # Generate larger sample dataset
        n_samples = 3000
        timestamps = pd.date_range(start='2022-01-01', periods=n_samples, freq='1H')
        
        # Create synthetic price data with trend and volatility
        np.random.seed(42)
        price = 100
        prices = [price]
        
        for i in range(1, n_samples):
            change = np.random.normal(0.0002, 0.02)  # Small upward drift with volatility
            price = price * (1 + change)
            prices.append(price)
        
        data = pd.DataFrame({
            'timestamp': timestamps,
            'close': prices,
            'volume': np.random.normal(1000000, 200000, n_samples),
            'target': pd.Series(prices).pct_change().shift(-1)  # Next period return
        })
        
        # Add some basic features
        data['sma_20'] = data['close'].rolling(20).mean()
        data['rsi'] = 50 + np.random.normal(0, 15, n_samples)  # Dummy RSI
        data['volume_sma'] = data['volume'].rolling(20).mean()
        
        data = data.dropna()
        
        print(f"✅ Sample data created: {len(data)} samples")
        
        # Initialize walk-forward engine
        wf_engine = WalkForwardEngine(
            window_size=800,   # Smaller windows for demo
            step_size=200,     # Step size
            min_train_size=400,
            validation_size=100,
            n_splits=3
        )
        
        feature_columns = ['sma_20', 'rsi', 'volume_sma']
        
        print(f"🔧 Walk-forward configuration:")
        print(f"   Window size: {wf_engine.window_size}")
        print(f"   Step size: {wf_engine.step_size}")
        print(f"   Features: {feature_columns}")
        
        # Run walk-forward analysis
        model_params = {'type': 'lightgbm', 'n_estimators': 50}
        strategy_config = {'ml_threshold': 0.01}
        
        print(f"\n🔄 Running walk-forward analysis...")
        wf_results = wf_engine.run_walk_forward_analysis(
            data=data,
            feature_columns=feature_columns,
            target_column='target',
            model_params=model_params,
            strategy_config=strategy_config,
            optimize_params=False
        )
        
        if 'error' not in wf_results:
            print(f"✅ Walk-forward analysis completed!")
            print(f"📊 Windows processed: {len(wf_results['window_results'])}")
            
            # Performance summary
            if 'performance_summary' in wf_results:
                perf = wf_results['performance_summary']
                print(f"📈 Overall correlation: {perf.get('correlation', 0):.3f}")
                print(f"📉 Overall MSE: {perf.get('mse', 0):.6f}")
            
            # Stability metrics
            if 'stability_metrics' in wf_results:
                stability = wf_results['stability_metrics']
                if stability:
                    print(f"🎯 Model stability:")
                    print(f"   Correlation mean: {stability.get('correlation_mean', 0):.3f}")
                    print(f"   Correlation std: {stability.get('correlation_std', 0):.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Walk-forward demo failed: {e}")
        return False

def show_methodology_explanation():
    """
    Explain the time series methodology used
    """
    print("\n📚 TIME SERIES BACKTESTING METHODOLOGY")
    print("=" * 60)
    
    methodology = """
🎯 KEY PRINCIPLES:

1. CHRONOLOGICAL DATA SPLITTING
   └── Training: Past data only (60%)
   └── Validation: More recent data (20%)
   └── Testing: Future data (20%)
   └── NO data leakage between periods

2. WALK-FORWARD ANALYSIS
   └── Rolling windows with overlapping training periods
   └── Each window trains a new model
   └── Out-of-sample testing on unseen future data
   └── Realistic performance estimation

3. FEATURE ENGINEERING
   └── Only past data used for indicator calculation
   └── Support/resistance from historical data only
   └── Lag features prevent look-ahead bias
   └── 100+ technical indicators with proper time alignment

4. ML MODEL TRAINING
   └── Models trained only on past data
   └── Time series cross-validation within training period
   └── Feature selection using historical importance
   └── Hyperparameter optimization with temporal validation

5. TRADING SIGNAL GENERATION
   └── ML predictions combined with technical analysis
   └── Support/resistance levels from past data only
   └── Dynamic position sizing based on confidence
   └── Risk management with stop-loss and take-profit

6. PERFORMANCE EVALUATION
   └── Out-of-sample testing on unseen data
   └── Stability metrics across time windows
   └── Walk-forward consistency analysis
   └── Realistic transaction costs consideration

🚫 PREVENTS LOOK-AHEAD BIAS:
   ✅ No future data in feature calculation
   ✅ No future data in model training
   ✅ No future data in signal generation
   ✅ Proper chronological order maintained
    """
    
    print(methodology)

def main():
    """
    Run all demonstrations
    """
    print("🚀 PROPER BACKTESTING SYSTEM - DEMONSTRATION")
    print("=" * 80)
    print("This demo shows how to use the new time series backtesting system")
    print("that prevents look-ahead bias and provides realistic results.")
    print()
    
    # Show methodology
    show_methodology_explanation()
    
    # Run demos
    demos = [
        ("Single Backtest Demo", demo_single_backtest),
        ("Custom Strategy Demo", demo_custom_strategy),
        ("Walk-Forward Analysis Demo", demo_walk_forward_analysis),
        ("Comprehensive Backtest Demo", demo_comprehensive_backtest),
    ]
    
    results = []
    
    for demo_name, demo_func in demos:
        try:
            print(f"\n" + "🎬 " + "=" * 60)
            result = demo_func()
            results.append((demo_name, result))
        except Exception as e:
            print(f"❌ Demo {demo_name} crashed: {e}")
            results.append((demo_name, False))
    
    # Summary
    print(f"\n" + "=" * 80)
    print("📊 DEMONSTRATION SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(results)
    
    for demo_name, result in results:
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"{status} - {demo_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} demos completed successfully")
    
    if passed > 0:
        print(f"\n🎉 Demonstration completed!")
        print(f"\n💡 Next steps:")
        print(f"1. Run your own backtests:")
        print(f"   python run_proper_backtest.py --single-test --symbol HYPE --timeframe 1h")
        print(f"2. Try comprehensive testing:")
        print(f"   python run_proper_backtest.py --symbols HYPE SOL --timeframes 15m 1h")
        print(f"3. Use walk-forward analysis:")
        print(f"   python run_proper_backtest.py --single-test --walk-forward")
        print(f"4. Check results in: demo_results/")
    
    # Cleanup
    print(f"\n🧹 Demo files saved in demo_results/ and demo_cache/")
    print(f"📝 Check the README_proper_backtesting.md for detailed documentation")

if __name__ == "__main__":
    main()