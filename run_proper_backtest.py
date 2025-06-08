"""
Run Proper Backtesting with Time Series Methodology
Main script to execute comprehensive backtesting with proper train-test separation
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import logging
from pathlib import Path

# Import our backtesting engine
from proper_backtesting_engine import ProperBacktestingEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run Proper Backtesting with Time Series Methodology')
    
    parser.add_argument('--symbols', type=str, nargs='+', 
                       default=['HYPE', 'SOL'], 
                       help='Symbols to test')
    
    parser.add_argument('--timeframes', type=str, nargs='+',
                       default=['15m', '1h'],
                       choices=['5m', '15m', '30m', '1h'],
                       help='Timeframes to test')
    
    parser.add_argument('--strategies', type=str, nargs='+',
                       default=['ML_Conservative', 'ML_Aggressive'],
                       help='Strategies to test')
    
    parser.add_argument('--single-test', action='store_true',
                       help='Run single test instead of comprehensive')
    
    parser.add_argument('--symbol', type=str, default='HYPE',
                       help='Symbol for single test')
    
    parser.add_argument('--timeframe', type=str, default='1h',
                       choices=['5m', '15m', '30m', '1h'],
                       help='Timeframe for single test')
    
    parser.add_argument('--strategy', type=str, default='ML_Conservative',
                       help='Strategy for single test')
    
    parser.add_argument('--force-refresh', action='store_true',
                       help='Force data refresh (ignore cache)')
    
    parser.add_argument('--walk-forward', action='store_true',
                       help='Use walk-forward analysis')
    
    parser.add_argument('--output-dir', type=str, default='proper_backtest_results',
                       help='Output directory for results')
    
    return parser.parse_args()

def display_welcome():
    """Display welcome message"""
    print("=" * 80)
    print("🚀 PROPER BACKTESTING ENGINE - TIME SERIES METHODOLOGY")
    print("=" * 80)
    print()
    print("✅ Prevents look-ahead bias")
    print("✅ Proper train/validation/test splits")
    print("✅ Walk-forward analysis support")
    print("✅ Comprehensive feature engineering")
    print("✅ Multiple timeframes: 5m, 15m, 30m, 1h")
    print("✅ Advanced ML models with hyperparameter optimization")
    print("✅ Support/resistance detection using only past data")
    print()

def run_single_backtest(args):
    """Run a single backtest"""
    print(f"🧪 SINGLE BACKTEST MODE")
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Strategy: {args.strategy}")
    print(f"Walk-forward: {args.walk_forward}")
    print("-" * 50)
    
    # Initialize engine
    engine = ProperBacktestingEngine(results_dir=args.output_dir)
    
    try:
        # Run backtest
        result = engine.run_single_backtest(
            symbol=args.symbol,
            timeframe=args.timeframe,
            strategy_name=args.strategy,
            data=None,
            use_walk_forward=args.walk_forward
        )
        
        if 'error' in result:
            print(f"❌ Backtest failed: {result['error']}")
            return False
        
        # Display results
        display_single_result(result)
        
        # Save result
        test_key = f"{args.symbol}_{args.timeframe}_{args.strategy}"
        engine.save_backtest_result(result, test_key)
        
        return True
        
    except Exception as e:
        logger.error(f"Single backtest failed: {e}")
        print(f"❌ Error: {e}")
        return False

def run_comprehensive_backtest(args):
    """Run comprehensive backtest"""
    print(f"🔬 COMPREHENSIVE BACKTEST MODE")
    print(f"Symbols: {args.symbols}")
    print(f"Timeframes: {args.timeframes}")
    print(f"Strategies: {args.strategies}")
    print(f"Total combinations: {len(args.symbols) * len(args.timeframes) * len(args.strategies)}")
    print("-" * 50)
    
    # Initialize engine
    engine = ProperBacktestingEngine(results_dir=args.output_dir)
    
    try:
        # Run comprehensive backtest
        results = engine.run_comprehensive_backtest(
            symbols=args.symbols,
            timeframes=args.timeframes,
            strategies=args.strategies,
            max_workers=4
        )
        
        # Display results
        display_comprehensive_results(results)
        
        return True
        
    except Exception as e:
        logger.error(f"Comprehensive backtest failed: {e}")
        print(f"❌ Error: {e}")
        return False

def display_single_result(result):
    """Display single backtest result"""
    print("\n📊 BACKTEST RESULTS")
    print("=" * 50)
    
    # Basic info
    print(f"Symbol: {result.get('symbol', 'N/A')}")
    print(f"Timeframe: {result.get('timeframe', 'N/A')}")
    print(f"Strategy: {result.get('strategy_name', 'N/A')}")
    print(f"Data samples: {result.get('data_samples', 'N/A')}")
    print(f"Features: {result.get('feature_count', 'N/A')}")
    print(f"Methodology: {result.get('methodology', 'N/A')}")
    
    # Performance metrics
    if 'trading_results' in result and 'metrics' in result['trading_results']:
        metrics = result['trading_results']['metrics']
        
        if 'error' not in metrics:
            print(f"\n💰 TRADING PERFORMANCE")
            print(f"Total trades: {metrics.get('total_trades', 0)}")
            print(f"Win rate: {metrics.get('win_rate', 0)*100:.1f}%")
            print(f"Total return: {metrics.get('total_return', 0)*100:.2f}%")
            print(f"Average return: {metrics.get('avg_return', 0)*100:.3f}%")
            print(f"Sharpe ratio: {metrics.get('sharpe_ratio', 0):.3f}")
            print(f"Max drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%")
            
            if metrics.get('total_trades', 0) > 0:
                print(f"Best trade: {metrics.get('max_return', 0)*100:.2f}%")
                print(f"Worst trade: {metrics.get('min_return', 0)*100:.2f}%")
        else:
            print(f"\n❌ Trading metrics error: {metrics['error']}")
    
    # ML performance
    if 'performance_metrics' in result:
        ml_metrics = result['performance_metrics']
        if 'error' not in ml_metrics and 'correlation' in ml_metrics:
            print(f"\n🤖 ML MODEL PERFORMANCE")
            print(f"Correlation: {ml_metrics.get('correlation', 0):.3f}")
            print(f"MSE: {ml_metrics.get('mse', 0):.6f}")
            print(f"R-squared: {ml_metrics.get('r_squared', 0):.3f}")
    
    # Stability metrics
    if 'stability_metrics' in result:
        stability = result['stability_metrics']
        if stability:
            print(f"\n📈 STABILITY METRICS")
            print(f"Correlation stability: {stability.get('correlation_mean', 0):.3f} ± {stability.get('correlation_std', 0):.3f}")
            print(f"MSE stability: {stability.get('mse_stability', 0):.3f}")

def display_comprehensive_results(results):
    """Display comprehensive backtest results"""
    print("\n📊 COMPREHENSIVE BACKTEST RESULTS")
    print("=" * 60)
    
    if 'summary' in results and 'stats' in results['summary']:
        stats = results['summary']['stats']
        
        print(f"Total tests: {stats.get('total_tests', 0)}")
        print(f"Average win rate: {stats.get('avg_win_rate', 0)*100:.1f}%")
        print(f"Average total return: {stats.get('avg_total_return', 0)*100:.2f}%")
        print(f"Average Sharpe ratio: {stats.get('avg_sharpe_ratio', 0):.3f}")
        print(f"Best strategy: {stats.get('best_strategy', 'N/A')}")
        print(f"Best return: {stats.get('best_return', 0)*100:.2f}%")
        print(f"Worst return: {stats.get('worst_return', 0)*100:.2f}%")
        
        # Performance by category
        print(f"\n📋 PERFORMANCE BY SYMBOL:")
        for symbol, return_val in stats.get('by_symbol', {}).items():
            print(f"  {symbol}: {return_val*100:.2f}%")
        
        print(f"\n⏰ PERFORMANCE BY TIMEFRAME:")
        for timeframe, return_val in stats.get('by_timeframe', {}).items():
            print(f"  {timeframe}: {return_val*100:.2f}%")
        
        print(f"\n🎯 PERFORMANCE BY STRATEGY:")
        for strategy, return_val in stats.get('by_strategy', {}).items():
            print(f"  {strategy}: {return_val*100:.2f}%")
    
    # Failed tests
    if 'failed_tests' in results and results['failed_tests']:
        print(f"\n❌ FAILED TESTS ({len(results['failed_tests'])}):")
        for symbol, timeframe, strategy, error in results['failed_tests']:
            print(f"  {symbol} {timeframe} {strategy}: {error}")
    
    # Detailed results table
    if 'summary' in results and 'detailed_results' in results['summary']:
        detailed = results['summary']['detailed_results']
        if detailed:
            print(f"\n📋 DETAILED RESULTS:")
            df = pd.DataFrame(detailed)
            
            # Select key columns for display
            display_cols = ['symbol', 'timeframe', 'strategy', 'total_trades', 'win_rate', 'total_return', 'sharpe_ratio']
            display_df = df[display_cols].copy()
            
            # Format percentages
            display_df['win_rate'] = (display_df['win_rate'] * 100).round(1)
            display_df['total_return'] = (display_df['total_return'] * 100).round(2)
            display_df['sharpe_ratio'] = display_df['sharpe_ratio'].round(3)
            
            print(display_df.to_string(index=False))

def main():
    """Main function"""
    args = parse_arguments()
    
    display_welcome()
    
    # Check output directory
    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created output directory: {output_dir}")
    else:
        print(f"📁 Using output directory: {output_dir}")
    
    print()
    
    # Run backtest
    start_time = datetime.now()
    
    if args.single_test:
        success = run_single_backtest(args)
    else:
        success = run_comprehensive_backtest(args)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "=" * 60)
    if success:
        print("✅ BACKTESTING COMPLETED SUCCESSFULLY")
    else:
        print("❌ BACKTESTING FAILED")
    
    print(f"⏱️  Duration: {duration}")
    print(f"📁 Results saved in: {args.output_dir}")
    print(f"📊 Log file: backtest.log")
    print("=" * 60)

if __name__ == "__main__":
    main()