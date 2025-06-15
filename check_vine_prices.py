#!/usr/bin/env python3
import pickle
import gzip
import pandas as pd
import numpy as np
import os

def check_vine_prices():
    # VINE関連の全ファイルを調査
    compressed_dir = 'large_scale_analysis/compressed/'
    vine_files = [f for f in os.listdir(compressed_dir) if f.startswith('VINE_') and f.endswith('.pkl.gz')]
    print(f'Found {len(vine_files)} VINE files')

    all_prices = []
    anomalous_prices = []
    file_summary = {}

    for file_name in vine_files:
        print(f'\nChecking {file_name}...')
        file_path = os.path.join(compressed_dir, file_name)
        
        try:
            with gzip.open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            if isinstance(data, list):
                prices = []
                for trade in data:
                    if isinstance(trade, dict):
                        entry_price = trade.get('entry_price', 0)
                        exit_price = trade.get('exit_price', 0)
                        tp_price = trade.get('take_profit_price', 0)
                        sl_price = trade.get('stop_loss_price', 0)
                        
                        trade_prices = [entry_price, exit_price, tp_price, sl_price]
                        trade_prices = [p for p in trade_prices if p is not None and p > 0]
                        prices.extend(trade_prices)
                
                if prices:
                    min_price = min(prices)
                    max_price = max(prices)
                    print(f'  Price range: ${min_price:.6f} - ${max_price:.6f}')
                    all_prices.extend(prices)
                    
                    # $100以上の異常価格をチェック
                    anomalous = [p for p in prices if p >= 100.0]
                    if anomalous:
                        print(f'  *** ANOMALOUS PRICES FOUND: {anomalous} ***')
                        anomalous_prices.extend(anomalous)
                        file_summary[file_name] = {
                            'min_price': min_price,
                            'max_price': max_price,
                            'anomalous_count': len(anomalous),
                            'anomalous_prices': anomalous
                        }
                    else:
                        file_summary[file_name] = {
                            'min_price': min_price,
                            'max_price': max_price,
                            'anomalous_count': 0,
                            'anomalous_prices': []
                        }
                        
        except Exception as e:
            print(f'  Error reading {file_name}: {e}')

    print(f'\n=== SUMMARY ===')
    if all_prices:
        print(f'Overall price range: ${min(all_prices):.6f} - ${max(all_prices):.6f}')
        print(f'Total anomalous prices (>=$100): {len(anomalous_prices)}')
        if anomalous_prices:
            print(f'Anomalous prices found: {set(anomalous_prices)}')
            print('\nFiles with anomalous prices:')
            for file_name, summary in file_summary.items():
                if summary['anomalous_count'] > 0:
                    print(f'  {file_name}: {summary["anomalous_count"]} anomalous prices')
        else:
            print('No anomalous prices found - all prices are in normal range!')
    else:
        print('No price data found')

if __name__ == '__main__':
    check_vine_prices()