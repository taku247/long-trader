#!/usr/bin/env python3
"""
Debug script to analyze CAKE price patterns and identify hardcoded values.
"""

import pickle
import gzip
from pathlib import Path

def analyze_cake_data():
    """Analyze CAKE trade data for hardcoded price patterns."""
    
    # Load CAKE 1h data (which had mixed real/hardcoded prices)
    cake_file = Path('/Users/moriwakikeita/tools/long-trader/large_scale_analysis/compressed/CAKE_1h_Conservative_ML.pkl.gz')
    
    if not cake_file.exists():
        print(f"File not found: {cake_file}")
        return
        
    with gzip.open(cake_file, 'rb') as f:
        data = pickle.load(f)
    
    print('=== CAKE 1m Conservative ML Analysis ===')
    print(f'Total trades: {len(data)}')
    
    # Extract price data
    entry_prices = [trade['entry_price'] for trade in data]
    
    # Check for hardcoded 1000.0 pattern
    count_1000 = sum(1 for p in entry_prices if p == 1000.0)
    print(f'Trades with entry price = 1000.0: {count_1000} out of {len(data)} ({count_1000/len(data)*100:.1f}%)')
    
    # Check patterns in TP/SL for hardcoded entries
    hardcoded_trades = [trade for trade in data if trade['entry_price'] == 1000.0]
    if hardcoded_trades:
        tp_pattern = set([trade['take_profit_price'] for trade in hardcoded_trades])
        sl_pattern = set([trade['stop_loss_price'] for trade in hardcoded_trades])
        print(f'Hardcoded TP prices: {tp_pattern}')
        print(f'Hardcoded SL prices: {sl_pattern}')
    
    # Check real prices  
    real_trades = [trade for trade in data if trade['entry_price'] != 1000.0]
    
    print(f'Real trades: {len(real_trades)}')
    if real_trades:
        real_entry_prices = [trade['entry_price'] for trade in real_trades]
        print(f'Real entry price range: {min(real_entry_prices):.4f} - {max(real_entry_prices):.4f}')
        print(f'Sample real entries: {real_entry_prices[:5]}')
        
        # Check TP/SL patterns for real trades
        real_tp_prices = [trade['take_profit_price'] for trade in real_trades]
        real_sl_prices = [trade['stop_loss_price'] for trade in real_trades]
        
        print(f'Real TP price range: {min(real_tp_prices):.4f} - {max(real_tp_prices):.4f}')
        print(f'Real SL price range: {min(real_sl_prices):.4f} - {max(real_sl_prices):.4f}')
        
        print(f'Unique real entry prices: {len(set(real_entry_prices))}')
        print(f'Unique real TP prices: {len(set(real_tp_prices))}')
        print(f'Unique real SL prices: {len(set(real_sl_prices))}')

if __name__ == '__main__':
    analyze_cake_data()