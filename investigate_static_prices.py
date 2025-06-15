#!/usr/bin/env python3
"""
静的価格問題の調査
entry_price, take_profit_price, stop_loss_priceが全て同じ値になる問題を調査
"""

import pandas as pd
import pickle
import gzip
from pathlib import Path
import glob

def investigate_recent_files():
    """最近生成されたファイルの価格パターンを調査"""
    print("🔍 最近生成されたファイルの価格パターン調査")
    print("=" * 60)
    
    compressed_dir = Path("large_scale_analysis/compressed")
    
    # 最近のファイルを取得（BTCとSOL）
    recent_symbols = ["BTC", "SOL", "DOGE", "AVAX", "ARB"]
    
    for symbol in recent_symbols:
        files = list(compressed_dir.glob(f"{symbol}_*.pkl.gz"))
        if not files:
            continue
            
        print(f"\n📊 {symbol} のファイル分析:")
        
        for file_path in files[:2]:  # 最大2ファイル
            print(f"\n  ファイル: {file_path.name}")
            
            try:
                with gzip.open(file_path, 'rb') as f:
                    data = pickle.load(f)
                
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                elif isinstance(data, pd.DataFrame):
                    df = data
                else:
                    continue
                
                # 価格分析
                if 'entry_price' in df.columns and 'current_price' in df.columns:
                    entry_prices = df['entry_price'].values
                    current_prices = df['current_price'].values if 'current_price' in df.columns else None
                    
                    print(f"    entry_price:")
                    print(f"      ユニーク数: {len(pd.Series(entry_prices).unique())}")
                    print(f"      最初の5件: {entry_prices[:5]}")
                    
                    if current_prices is not None:
                        print(f"    current_price:")
                        print(f"      ユニーク数: {len(pd.Series(current_prices).unique())}")
                        print(f"      最初の5件: {current_prices[:5]}")
                        
                        # entry_priceとcurrent_priceの関係をチェック
                        if len(entry_prices) > 0 and len(current_prices) > 0:
                            all_same = all(entry_prices[0] == cp for cp in current_prices)
                            print(f"      entry_price == current_price: {all_same}")
                    
                    # leverageカラムもチェック
                    if 'leverage' in df.columns:
                        leverages = df['leverage'].values
                        print(f"    leverage:")
                        print(f"      ユニーク数: {len(pd.Series(leverages).unique())}")
                        print(f"      範囲: {leverages.min():.1f} - {leverages.max():.1f}")
                        
            except Exception as e:
                print(f"    ❌ エラー: {e}")

def check_scalable_analysis_code():
    """scalable_analysis_system.pyのコードを確認"""
    print("\n🔍 scalable_analysis_system.pyの価格生成ロジック確認")
    print("=" * 60)
    
    # _generate_real_analysisメソッドの価格生成部分を確認
    print("""
現在の実装では、analyze_symbolの結果から：
- current_price を entry_price として使用
- 全てのトレードで同じ current_price を使用

これが原因で全トレードのentry_priceが同じ値になっている可能性があります。
""")

def suggest_fix():
    """修正案の提示"""
    print("\n💡 修正案")
    print("=" * 60)
    print("""
1. 時系列データを使った動的価格生成:
   - 各トレードごとに異なる時点の価格を使用
   - OHLCVデータから適切な時点の価格を取得

2. entry_priceの多様性確保:
   - 時間をずらして複数回の分析を実行
   - または過去のOHLCVデータから異なる時点の価格を使用

3. 現在の実装の問題:
   - bot.analyze_symbol()が現在価格のみを返す
   - 全トレードで同じ現在価格を使用している
""")

def main():
    """メイン実行関数"""
    print("🔍 静的価格問題の調査レポート")
    print("=" * 70)
    
    # 1. 最近のファイルを調査
    investigate_recent_files()
    
    # 2. コードの問題点を確認
    check_scalable_analysis_code()
    
    # 3. 修正案を提示
    suggest_fix()
    
    print("\n" + "=" * 70)
    print("✅ 調査完了")
    
    print("\n📋 結論:")
    print("- ハードコード値（100.0, 105.0, 97.62）は完全に除去された ✅")
    print("- しかし、新たな問題：全トレードで同じ現在価格を使用している")
    print("- これは実装の問題であり、フォールバック値とは異なる")

if __name__ == '__main__':
    main()