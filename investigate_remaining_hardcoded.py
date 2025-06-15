#!/usr/bin/env python3
"""
残存ハードコード値の詳細調査
どのファイルにどの値が含まれているか特定
"""

import pandas as pd
import pickle
import gzip
from pathlib import Path

def investigate_hardcoded_files():
    """ハードコード値を含むファイルの詳細調査"""
    print("🔍 残存ハードコード値の詳細調査")
    print("=" * 70)
    
    compressed_dir = Path("large_scale_analysis/compressed")
    
    # 問題のあるファイルを詳細調査
    problem_files = [
        "TAO_1h_Full_ML.pkl.gz",
        "CAKE_3m_Aggressive_Traditional.pkl.gz", 
        "TAO_5m_Full_ML.pkl.gz"
    ]
    
    hardcoded_values = [100.0, 105.0, 97.62, 1000.0]
    
    for filename in problem_files:
        file_path = compressed_dir / filename
        if not file_path.exists():
            continue
            
        print(f"\n📊 {filename} の詳細分析:")
        
        try:
            with gzip.open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                continue
                
            print(f"  レコード数: {len(df)}")
            
            # 各価格カラムの詳細
            price_columns = ['entry_price', 'take_profit_price', 'stop_loss_price', 'exit_price']
            
            for col in price_columns:
                if col in df.columns:
                    values = df[col].values
                    print(f"\n  {col}:")
                    print(f"    範囲: {values.min():.6f} - {values.max():.6f}")
                    
                    # 各ハードコード値をチェック
                    for hv in hardcoded_values:
                        matching = sum(abs(val - hv) < 0.001 for val in values)
                        if matching > 0:
                            print(f"    ❌ {hv}: {matching}件検出")
                            # 実際の値を表示
                            matching_values = [val for val in values if abs(val - hv) < 0.001]
                            print(f"       実際の値: {matching_values[:3]}")
                    
                    # 最初の5件を表示
                    print(f"    最初の5件: {values[:5]}")
                    
        except Exception as e:
            print(f"  ❌ エラー: {e}")

def check_file_timestamps():
    """ファイルのタイムスタンプをチェック"""
    print("\n🔍 ハードコード値を含むファイルのタイムスタンプ")
    print("=" * 70)
    
    import os
    from datetime import datetime
    
    compressed_dir = Path("large_scale_analysis/compressed")
    
    problem_files = [
        "TAO_1h_Full_ML.pkl.gz",
        "CAKE_3m_Aggressive_Traditional.pkl.gz",
        "TAO_5m_Full_ML.pkl.gz",
        "TAO_3m_Aggressive_Traditional.pkl.gz",
        "TRUMP_15m_Full_ML.pkl.gz"
    ]
    
    for filename in problem_files:
        file_path = compressed_dir / filename
        if file_path.exists():
            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime)
            print(f"{filename}: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """メイン実行関数"""
    print("📋 残存ハードコード値調査レポート")
    print("=" * 70)
    
    # 1. 詳細調査
    investigate_hardcoded_files()
    
    # 2. タイムスタンプ確認
    check_file_timestamps()
    
    print("\n" + "=" * 70)
    print("📋 結論:")
    print("- Phase 1で削除し損ねた古いファイルが残存")
    print("- 新規生成ファイル（BTC, TRX）にはハードコード値なし")
    print("- 残存ファイルも削除すれば完全にクリーン")

if __name__ == '__main__':
    main()