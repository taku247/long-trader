#!/usr/bin/env python3
"""
Comprehensive script to check all symbol trade data for hardcoded/anomalous values
"""
import gzip
import pickle
import os
from pathlib import Path
from collections import defaultdict
import numpy as np

def check_all_symbols():
    """Check all symbol trade data files for anomalous price values"""
    compressed_dir = Path('large_scale_analysis/compressed/')
    
    if not compressed_dir.exists():
        print(f"Directory {compressed_dir} does not exist")
        return
    
    # Get all compressed files
    all_files = [f for f in os.listdir(compressed_dir) if f.endswith('.pkl.gz')]
    
    # Group by symbol
    symbols = defaultdict(list)
    for file_name in all_files:
        if '_' in file_name:
            symbol = file_name.split('_')[0]
            symbols[symbol].append(file_name)
    
    print(f"Found {len(symbols)} symbols with {len(all_files)} total files")
    print(f"Symbols: {sorted(symbols.keys())}")
    
    # Suspicious values to check for
    common_hardcoded = [100.0, 105.0, 97.62, 97.61904761904762]
    
    # Results
    results = {}
    
    for symbol, files in symbols.items():
        print(f"\\n=== Checking {symbol} ({len(files)} files) ===")
        
        symbol_issues = {
            'files_with_issues': 0,
            'total_suspicious_values': 0,
            'total_trades': 0,
            'price_ranges': [],
            'sample_trades': []
        }
        
        for file_name in files[:2]:  # Check first 2 files per symbol
            print(f"  Checking {file_name}...")
            file_path = compressed_dir / file_name
            
            try:
                with gzip.open(file_path, 'rb') as f:
                    data = pickle.load(f)
                
                if isinstance(data, list) and len(data) > 0:
                    symbol_issues['total_trades'] += len(data)
                    
                    # Collect all prices
                    all_prices = []
                    suspicious_count = 0
                    
                    for i, trade in enumerate(data):
                        if isinstance(trade, dict):
                            trade_prices = {}
                            for field in ['entry_price', 'exit_price', 'take_profit_price', 'stop_loss_price']:
                                if field in trade:
                                    value = trade[field]
                                    if isinstance(value, (int, float)) and value > 0:
                                        all_prices.append(value)
                                        trade_prices[field] = value
                                        
                                        # Check if suspicious
                                        if any(abs(value - hv) < 0.01 for hv in common_hardcoded):
                                            suspicious_count += 1
                            
                            # Save sample trades for display
                            if i < 2 and trade_prices:
                                sample_trade = {
                                    'file': file_name,
                                    'trade_index': i,
                                    'prices': trade_prices,
                                    'leverage': trade.get('leverage', 'N/A'),
                                    'pnl_pct': trade.get('pnl_pct', 'N/A')
                                }
                                symbol_issues['sample_trades'].append(sample_trade)
                    
                    if all_prices:
                        price_range = (min(all_prices), max(all_prices), np.mean(all_prices))
                        symbol_issues['price_ranges'].append(price_range)
                        
                        print(f"    Price range: ${min(all_prices):.3f} - ${max(all_prices):.3f} (avg: ${np.mean(all_prices):.3f})")
                        print(f"    Suspicious values: {suspicious_count}/{len(all_prices)}")
                        
                        if suspicious_count > 0:
                            symbol_issues['files_with_issues'] += 1
                            symbol_issues['total_suspicious_values'] += suspicious_count
                
            except Exception as e:
                print(f"    Error reading {file_name}: {e}")
        
        results[symbol] = symbol_issues
    
    # Summary report
    print(f"\\n{'='*60}")
    print("SUMMARY REPORT")
    print(f"{'='*60}")
    
    problematic_symbols = []
    
    for symbol, issues in results.items():
        total_prices = sum(len(data) * 4 for data in issues.get('price_ranges', []))  # Approximate
        suspicious_pct = (issues['total_suspicious_values'] / max(total_prices, 1)) * 100
        
        print(f"\\n{symbol}:")
        print(f"  Files with issues: {issues['files_with_issues']}")
        print(f"  Total suspicious values: {issues['total_suspicious_values']}")
        print(f"  Total trades checked: {issues['total_trades']}")
        
        if issues['price_ranges']:
            all_mins = [r[0] for r in issues['price_ranges']]
            all_maxs = [r[1] for r in issues['price_ranges']]
            print(f"  Price range: ${min(all_mins):.3f} - ${max(all_maxs):.3f}")
        
        if issues['total_suspicious_values'] > 0:
            problematic_symbols.append(symbol)
            print(f"  ⚠️  PROBLEMATIC: {suspicious_pct:.1f}% suspicious values")
            
            # Show sample trades
            for sample in issues['sample_trades'][:1]:
                print(f"    Sample trade from {sample['file']}:")
                for field, value in sample['prices'].items():
                    is_suspicious = any(abs(value - hv) < 0.01 for hv in common_hardcoded)
                    status = " ⚠️" if is_suspicious else ""
                    print(f"      {field}: {value}{status}")
    
    print(f"\\n{'='*60}")
    print(f"PROBLEMATIC SYMBOLS: {', '.join(problematic_symbols) if problematic_symbols else 'None'}")
    print(f"{'='*60}")
    
    if problematic_symbols:
        print(f"\\nRecommendation: Run fix scripts for the following symbols:")
        for symbol in problematic_symbols:
            print(f"  - {symbol}: Create fix_{symbol.lower()}_prices.py")

if __name__ == '__main__':
    check_all_symbols()