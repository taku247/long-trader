#!/usr/bin/env python3
"""
GMT トレードデータの価格チェック
圧縮されたトレードデータから価格情報を取得して検証
"""

import pickle
import gzip
import pandas as pd
import numpy as np
from pathlib import Path
import json

def load_compressed_trades(symbol, timeframe, config):
    """圧縮されたトレードデータを読み込み"""
    file_path = f"large_scale_analysis/compressed/{symbol}_{timeframe}_{config}.pkl.gz"
    
    try:
        with gzip.open(file_path, 'rb') as f:
            trades_data = pickle.load(f)
        return trades_data
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def analyze_trade_prices(trades_data, symbol, timeframe, config):
    """トレード価格を分析"""
    if trades_data is None:
        return None
    
    # DataFrameに変換（必要に応じて）
    if isinstance(trades_data, list):
        df = pd.DataFrame(trades_data)
    elif isinstance(trades_data, dict):
        df = pd.DataFrame(trades_data)
    else:
        df = trades_data
    
    print(f"\n=== {symbol} {timeframe} {config} ===")
    print(f"Total trades: {len(df)}")
    
    # 価格カラムを確認
    price_columns = []
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['price', 'entry', 'exit', 'profit', 'loss']):
            price_columns.append(col)
    
    print(f"Price columns: {price_columns}")
    
    # 価格統計
    results = {}
    for col in price_columns:
        if col in df.columns:
            values = df[col].dropna()
            if len(values) > 0:
                # 数値列のみ処理
                try:
                    # 文字列を除外して数値のみ取得
                    if values.dtype == 'object':
                        # 数値に変換可能な値のみフィルタ
                        numeric_values = pd.to_numeric(values, errors='coerce').dropna()
                    else:
                        numeric_values = values
                    
                    if len(numeric_values) > 0:
                        stats = {
                            'count': len(numeric_values),
                            'mean': float(numeric_values.mean()),
                            'min': float(numeric_values.min()),
                            'max': float(numeric_values.max()),
                            'std': float(numeric_values.std()),
                            'unique_values': len(numeric_values.unique()),
                            'sample_values': numeric_values.head(10).tolist()
                        }
                        results[col] = stats
                    else:
                        print(f"  ⚠️  No numeric values in {col}")
                        continue
                except Exception as e:
                    print(f"  ❌ Error processing {col}: {e}")
                    continue
                
                print(f"\n{col}:")
                print(f"  Count: {stats['count']}")
                print(f"  Range: {stats['min']:.6f} - {stats['max']:.6f}")
                print(f"  Mean: {stats['mean']:.6f}")
                print(f"  Std: {stats['std']:.6f}")
                print(f"  Unique values: {stats['unique_values']}")
                print(f"  Sample: {stats['sample_values'][:5]}")
                
                # 異常値チェック
                if stats['unique_values'] <= 3:
                    print(f"  ⚠️  WARNING: Only {stats['unique_values']} unique values!")
                
                if stats['std'] < 0.001:
                    print(f"  ⚠️  WARNING: Very low variation (std={stats['std']:.6f})")
    
    return results

def check_current_gmt_price():
    """現在のGMT価格を確認（参考）"""
    try:
        import asyncio
        from hyperliquid_api_client import MultiExchangeAPIClient
        
        async def get_current_price():
            client = MultiExchangeAPIClient()
            from datetime import datetime, timedelta, timezone
            
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            data = await client.get_ohlcv_data('GMT', '1h', start_time, end_time)
            if not data.empty:
                return data['close'].iloc[-1]
            return None
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            current_price = loop.run_until_complete(get_current_price())
            loop.close()
            
            if current_price:
                print(f"\n📊 Current GMT price: {current_price:.6f}")
                return current_price
        except Exception as e:
            print(f"Could not fetch current price: {e}")
            loop.close()
            
    except Exception as e:
        print(f"API client error: {e}")
    
    return None

def main():
    """メイン実行"""
    print("=" * 60)
    print("🔍 GMT トレードデータ価格検証")
    print("=" * 60)
    
    # 現在価格を取得
    current_price = check_current_gmt_price()
    
    # GMT の全戦略データを確認
    gmt_files = []
    compressed_dir = Path("large_scale_analysis/compressed")
    
    if compressed_dir.exists():
        for file_path in compressed_dir.glob("GMT_*.pkl.gz"):
            parts = file_path.stem.replace('.pkl', '').split('_')
            if len(parts) >= 3:
                symbol = parts[0]
                timeframe = parts[1]
                config = '_'.join(parts[2:])
                gmt_files.append((symbol, timeframe, config))
    
    print(f"\n Found {len(gmt_files)} GMT strategy files")
    
    all_results = {}
    
    for symbol, timeframe, config in gmt_files:
        trades_data = load_compressed_trades(symbol, timeframe, config)
        results = analyze_trade_prices(trades_data, symbol, timeframe, config)
        
        if results:
            all_results[f"{symbol}_{timeframe}_{config}"] = results
    
    # 異常検出サマリー
    print("\n" + "=" * 60)
    print("🚨 異常値検出サマリー")
    print("=" * 60)
    
    anomalies = []
    
    for strategy_key, strategy_results in all_results.items():
        for price_col, stats in strategy_results.items():
            # 異常値の条件
            if stats['unique_values'] <= 3:
                anomalies.append({
                    'strategy': strategy_key,
                    'column': price_col,
                    'issue': f'Only {stats["unique_values"]} unique values',
                    'values': stats['sample_values']
                })
            
            if stats['std'] < 0.001 and 'price' in price_col.lower():
                anomalies.append({
                    'strategy': strategy_key,
                    'column': price_col,
                    'issue': f'Very low variation (std={stats["std"]:.6f})',
                    'values': stats['sample_values']
                })
            
            # 現在価格との比較（もしあれば）
            if current_price and 'price' in price_col.lower():
                price_diff = abs(stats['mean'] - current_price) / current_price
                if price_diff > 0.5:  # 50%以上の差
                    anomalies.append({
                        'strategy': strategy_key,
                        'column': price_col,
                        'issue': f'Large deviation from current price ({price_diff:.1%})',
                        'values': f"Mean: {stats['mean']:.6f}, Current: {current_price:.6f}"
                    })
    
    if anomalies:
        print("❌ Found anomalies:")
        for i, anomaly in enumerate(anomalies, 1):
            print(f"\n{i}. {anomaly['strategy']} - {anomaly['column']}")
            print(f"   Issue: {anomaly['issue']}")
            print(f"   Values: {anomaly['values']}")
    else:
        print("✅ No obvious anomalies detected")
    
    # 結果をJSONで保存
    output_file = "gmt_price_analysis_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'analysis_results': all_results,
            'anomalies': anomalies,
            'current_price': current_price,
            'timestamp': pd.Timestamp.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Detailed results saved to: {output_file}")

if __name__ == "__main__":
    main()