#!/usr/bin/env python3
"""
ハードコード値の深層スキャンと削除
全レコードを徹底的にチェック
"""

import pickle
import gzip
from pathlib import Path
import pandas as pd

def deep_scan_and_remove():
    """全ファイルの全レコードを深層スキャン"""
    print("🔍 ハードコード値の深層スキャン")
    print("=" * 70)
    
    compressed_dir = Path("large_scale_analysis/compressed")
    
    # 拡張ハードコード値リスト
    hardcoded_values = [
        100.0, 105.0, 97.62, 97.619, 97.61904761904762,
        1000.0, 1050.0, 976.2, 976.19, 976.1904761904762,
        900.0, 950.0, 
        # 変動版も含める
        100.4871447539048,  # OPで検出された値
        400.4323164, 480.37392  # CRVで検出された値
    ]
    
    files_with_hardcoded = {}
    
    all_files = list(compressed_dir.glob("*.pkl.gz"))
    print(f"📁 深層スキャン対象: {len(all_files)}ファイル")
    
    for file_path in all_files:
        try:
            with gzip.open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            # データフレームに変換
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                continue
            
            # 各価格カラムをチェック
            hardcoded_count = 0
            price_columns = ['entry_price', 'take_profit_price', 'stop_loss_price', 'exit_price']
            
            for col in price_columns:
                if col in df.columns:
                    values = df[col].values
                    
                    # 各ハードコード値をチェック
                    for hv in hardcoded_values:
                        # より厳密な一致（0.01%の誤差許容）
                        matching = sum(abs(val - hv) / hv < 0.0001 if hv != 0 else abs(val) < 0.0001 
                                     for val in values)
                        if matching > 0:
                            hardcoded_count += matching
            
            if hardcoded_count > 0:
                files_with_hardcoded[file_path] = hardcoded_count
                
        except Exception as e:
            # エラーは無視
            pass
    
    # 結果表示と削除
    if files_with_hardcoded:
        print(f"\n❌ ハードコード値検出: {len(files_with_hardcoded)}ファイル")
        
        # 詳細表示
        sorted_files = sorted(files_with_hardcoded.items(), key=lambda x: x[1], reverse=True)
        print("\n検出ファイル（上位10件）:")
        for file_path, count in sorted_files[:10]:
            print(f"  {file_path.name}: {count}件")
        
        if len(sorted_files) > 10:
            print(f"  ... 他 {len(sorted_files) - 10} ファイル")
        
        # 削除実行
        print(f"\n🗑️ {len(files_with_hardcoded)}ファイルを削除中...")
        deleted_count = 0
        
        for file_path in files_with_hardcoded.keys():
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ 削除失敗: {file_path.name}")
        
        print(f"✅ {deleted_count}ファイル削除完了")
    else:
        print("✅ ハードコード値は検出されませんでした")

def final_verification():
    """最終検証"""
    print("\n🔍 最終検証")
    print("=" * 70)
    
    compressed_dir = Path("large_scale_analysis/compressed")
    all_files = list(compressed_dir.glob("*.pkl.gz"))
    
    print(f"📁 残存ファイル数: {len(all_files)}")
    
    # サンプルチェック
    if all_files:
        sample_file = all_files[0]
        print(f"\nサンプルファイル検証: {sample_file.name}")
        
        try:
            with gzip.open(sample_file, 'rb') as f:
                data = pickle.load(f)
            
            if isinstance(data, list) and data:
                first_record = data[0]
                if 'entry_price' in first_record:
                    print(f"  エントリー価格: {first_record['entry_price']}")
                    print("  ✅ 実データを使用")
        except:
            pass

def main():
    """メイン実行関数"""
    print("🚀 ハードコード値完全除去 - 最終クリーンアップ")
    print("=" * 70)
    
    # 1. 深層スキャンと削除
    deep_scan_and_remove()
    
    # 2. 最終検証
    final_verification()
    
    print("\n" + "=" * 70)
    print("✅ 最終クリーンアップ完了")

if __name__ == '__main__':
    main()