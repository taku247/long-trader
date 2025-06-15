#!/usr/bin/env python3
"""
BTCで生成されたデータの検証
ハードコード値が含まれていないことを確認
"""

import pandas as pd
import pickle
import gzip
from pathlib import Path

def verify_btc_data():
    """BTCの生成データを検証"""
    print("🔍 BTC生成データの検証")
    print("=" * 60)
    
    # BTCのデータファイルを探す
    compressed_dir = Path("large_scale_analysis/compressed")
    btc_files = list(compressed_dir.glob("BTC_*.pkl.gz"))
    
    if not btc_files:
        print("❓ BTCのデータファイルが見つかりません")
        return
    
    print(f"📁 BTCファイル数: {len(btc_files)}")
    
    # ハードコード値リスト
    hardcoded_values = [100.0, 105.0, 97.62, 1000.0]
    
    # 各ファイルを検証
    total_hardcoded = 0
    
    for file_path in btc_files:
        print(f"\n📊 検証中: {file_path.name}")
        
        try:
            with gzip.open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            # データ形式に応じて処理
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                print(f"   ❓ 未知のデータ形式: {type(data)}")
                continue
            
            print(f"   レコード数: {len(df)}")
            
            # 価格カラムを検証
            price_columns = ['entry_price', 'take_profit_price', 'stop_loss_price', 
                           'exit_price', 'current_price']
            
            file_hardcoded = 0
            
            for col in price_columns:
                if col in df.columns:
                    values = df[col].values
                    unique_count = len(pd.Series(values).unique())
                    
                    print(f"\n   {col}:")
                    print(f"     ユニーク値数: {unique_count}")
                    print(f"     範囲: {values.min():.2f} - {values.max():.2f}")
                    
                    # ハードコード値チェック
                    for hv in hardcoded_values:
                        matching = sum(abs(val - hv) < 0.001 for val in values)
                        if matching > 0:
                            print(f"     ❌ ハードコード値 {hv}: {matching}件")
                            file_hardcoded += matching
                    
                    # BTCの妥当な価格範囲チェック (70,000 - 120,000)
                    btc_range_check = all(70000 <= val <= 120000 for val in values)
                    if btc_range_check:
                        print(f"     ✅ BTC価格範囲内")
                    else:
                        out_of_range = sum(1 for val in values if val < 70000 or val > 120000)
                        print(f"     ⚠️ 範囲外の値: {out_of_range}件")
            
            if file_hardcoded > 0:
                print(f"\n   ❌ ハードコード値合計: {file_hardcoded}件")
                total_hardcoded += file_hardcoded
            else:
                print(f"\n   ✅ ハードコード値なし")
                
        except Exception as e:
            print(f"   ❌ エラー: {e}")
    
    # 最終結果
    print("\n" + "=" * 60)
    if total_hardcoded > 0:
        print(f"❌ 総ハードコード値検出数: {total_hardcoded}件")
    else:
        print("✅ 全ファイルでハードコード値なし - 実データのみ使用確認！")

def check_latest_generated_files():
    """最新の生成ファイルをチェック"""
    print("\n🔍 最新生成ファイルの確認")
    print("=" * 60)
    
    import os
    from datetime import datetime
    
    compressed_dir = Path("large_scale_analysis/compressed")
    all_files = list(compressed_dir.glob("*.pkl.gz"))
    
    # 作成時刻でソート（新しい順）
    files_with_time = []
    for file_path in all_files:
        mtime = os.path.getmtime(file_path)
        files_with_time.append((file_path, mtime))
    
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    print("📅 最新の5ファイル:")
    for i, (file_path, mtime) in enumerate(files_with_time[:5]):
        dt = datetime.fromtimestamp(mtime)
        print(f"   {i+1}. {file_path.name} - {dt.strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """メイン実行関数"""
    print("🔍 Phase 2完了後のデータ検証")
    print("=" * 70)
    
    # 1. BTCデータの検証
    verify_btc_data()
    
    # 2. 最新生成ファイルの確認
    check_latest_generated_files()
    
    print("\n" + "=" * 70)
    print("✅ 検証完了")

if __name__ == '__main__':
    main()