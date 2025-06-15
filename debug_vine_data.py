#!/usr/bin/env python3
"""
VINEの異常価格問題のデバッグスクリプト
"""

import gzip
import pickle
import sys

def debug_vine_data():
    # VINEのデータファイルを確認
    files_to_check = [
        '/Users/moriwakikeita/tools/long-trader/large_scale_analysis/compressed/VINE_1h_Aggressive_Traditional.pkl.gz',
        '/Users/moriwakikeita/tools/long-trader/large_scale_analysis/compressed/VINE_1h_Full_ML.pkl.gz',
        '/Users/moriwakikeita/tools/long-trader/large_scale_analysis/compressed/VINE_1h_Conservative_ML.pkl.gz'
    ]
    
    for file_path in files_to_check:
        strategy_name = file_path.split('/')[-1].replace('.pkl.gz', '')
        print(f"=== {strategy_name} ===")
        
        try:
            with gzip.open(file_path, 'rb') as f:
                trades_data = pickle.load(f)
            
            print(f"データタイプ: {type(trades_data)}")
            print(f"データ長: {len(trades_data)}")
            
            if len(trades_data) > 0:
                print(f"最初の要素のタイプ: {type(trades_data[0])}")
                
                if isinstance(trades_data[0], dict):
                    print(f"最初の要素のキー: {list(trades_data[0].keys())}")
                    
                    # entry_priceを確認
                    if 'entry_price' in trades_data[0]:
                        prices = [trade.get('entry_price', 0) for trade in trades_data]
                        print(f"\n価格統計:")
                        print(f"  最小価格: ${min(prices):.4f}")
                        print(f"  最大価格: ${max(prices):.4f}")
                        print(f"  平均価格: ${sum(prices)/len(prices):.4f}")
                        
                        # 異常価格の検出
                        high_prices = [p for p in prices if p > 500]
                        normal_prices = [p for p in prices if p <= 500]
                        
                        print(f"  正常価格: {len(normal_prices)}件 (平均: ${sum(normal_prices)/len(normal_prices) if normal_prices else 0:.4f})")
                        print(f"  高価格: {len(high_prices)}件")
                        
                        if high_prices:
                            print(f"  🚨 高価格詳細: {high_prices[:5]}...")  # 最初の5件
                            
                            # 高価格トレードの詳細を表示
                            for i, trade in enumerate(trades_data):
                                if trade.get('entry_price', 0) > 500:
                                    print(f"\n高価格トレード #{i+1}:")
                                    for key, value in trade.items():
                                        print(f"  {key}: {value}")
                                    break  # 最初の1件だけ表示
                    else:
                        print("entry_price キーが見つかりません")
                        print(f"利用可能なキー: {list(trades_data[0].keys())}")
                else:
                    print(f"最初の要素: {trades_data[0]}")
            
            print()
            
        except Exception as e:
            print(f"エラー: {e}")
            import traceback
            traceback.print_exc()
            print()

if __name__ == "__main__":
    debug_vine_data()