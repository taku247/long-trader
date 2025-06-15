#!/usr/bin/env python3
"""
Script to check FIL trade data for hardcoded/anomalous values
"""
import gzip
import pickle
import os
from pathlib import Path

def check_fil_data():
    """Check FIL trade data files for anomalous price values"""
    compressed_dir = Path('large_scale_analysis/compressed/')
    
    # Find all FIL files
    fil_files = [f for f in os.listdir(compressed_dir) if f.startswith('FIL_') and f.endswith('.pkl.gz')]
    print(f"Found {len(fil_files)} FIL files to check")
    
    suspicious_values = {100.0, 105.0, 97.62}
    
    for file_name in fil_files[:3]:  # Check first 3 files
        print(f"\nChecking {file_name}...")
        file_path = compressed_dir / file_name
        
        try:
            with gzip.open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            if isinstance(data, list) and len(data) > 0:
                print(f"  Found {len(data)} trades")
                
                # Check first few trades
                for i, trade in enumerate(data[:5]):
                    if isinstance(trade, dict):
                        print(f"  Trade {i+1}:")
                        for field in ['entry_price', 'exit_price', 'take_profit_price', 'stop_loss_price']:
                            if field in trade:
                                value = trade[field]
                                is_suspicious = value in suspicious_values if isinstance(value, (int, float)) else False
                                status = " ⚠️  SUSPICIOUS!" if is_suspicious else ""
                                print(f"    {field}: {value}{status}")
                        
                        # Check other fields
                        for field in ['leverage', 'pnl_pct', 'confidence']:
                            if field in trade:
                                print(f"    {field}: {trade[field]}")
                        print()
                
                # Count suspicious values
                suspicious_count = 0
                total_prices = 0
                
                for trade in data:
                    if isinstance(trade, dict):
                        for field in ['entry_price', 'exit_price', 'take_profit_price', 'stop_loss_price']:
                            if field in trade:
                                value = trade[field]
                                total_prices += 1
                                if isinstance(value, (int, float)) and value in suspicious_values:
                                    suspicious_count += 1
                
                print(f"  Summary: {suspicious_count}/{total_prices} prices are suspicious")
                
        except Exception as e:
            print(f"  Error reading {file_name}: {e}")
    
    return True

if __name__ == '__main__':
    check_fil_data()