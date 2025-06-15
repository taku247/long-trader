#!/usr/bin/env python3
"""
残存ハードコード値ファイルの完全削除
Phase 1-2後に残った古いファイルを特定して削除
"""

import os
import pickle
import gzip
from pathlib import Path
from datetime import datetime

def identify_and_remove_hardcoded_files():
    """ハードコード値を含むファイルを特定して削除"""
    print("🗑️ 残存ハードコード値ファイルの完全削除")
    print("=" * 70)
    
    compressed_dir = Path("large_scale_analysis/compressed")
    
    # ハードコード値リスト
    hardcoded_values = [100.0, 105.0, 97.62, 97.619, 97.61904761904762, 1000.0, 1050.0, 976.2]
    
    # 削除対象ファイルのリスト
    files_to_delete = []
    
    # 全ファイルをスキャン
    all_files = list(compressed_dir.glob("*.pkl.gz"))
    print(f"📁 スキャン対象: {len(all_files)}ファイル")
    
    for file_path in all_files:
        try:
            with gzip.open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            if isinstance(data, list):
                df_data = data
            elif hasattr(data, 'to_dict'):
                df_data = data.to_dict('records')
            else:
                continue
            
            # ハードコード値チェック
            hardcoded_found = False
            
            for record in df_data[:10]:  # 最初の10レコードをチェック
                if isinstance(record, dict):
                    for key in ['entry_price', 'take_profit_price', 'stop_loss_price', 'exit_price']:
                        if key in record:
                            value = record[key]
                            for hv in hardcoded_values:
                                if abs(value - hv) < 0.001:
                                    hardcoded_found = True
                                    break
                    if hardcoded_found:
                        break
            
            if hardcoded_found:
                files_to_delete.append(file_path)
                
        except Exception:
            # エラーは無視
            pass
    
    print(f"\n❌ ハードコード値を含むファイル: {len(files_to_delete)}件")
    
    if files_to_delete:
        print("\n削除対象ファイル:")
        for i, file_path in enumerate(files_to_delete):
            print(f"  {i+1}. {file_path.name}")
        
        # 確認と削除
        print(f"\n🗑️ {len(files_to_delete)}ファイルを削除中...")
        
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ 削除失敗: {file_path.name} - {e}")
        
        print(f"✅ {deleted_count}ファイル削除完了")
    else:
        print("✅ ハードコード値を含むファイルはありません")

def verify_cleanup():
    """クリーンアップ後の検証"""
    print("\n🔍 クリーンアップ後の検証")
    print("=" * 70)
    
    compressed_dir = Path("large_scale_analysis/compressed")
    
    # 再度スキャン
    hardcoded_values = [100.0, 105.0, 97.62, 1000.0]
    total_hardcoded = 0
    
    all_files = list(compressed_dir.glob("*.pkl.gz"))
    print(f"📁 残存ファイル数: {len(all_files)}")
    
    for file_path in all_files:
        try:
            with gzip.open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            if isinstance(data, list):
                for record in data:
                    if isinstance(record, dict):
                        for key in ['entry_price', 'take_profit_price', 'stop_loss_price']:
                            if key in record:
                                value = record[key]
                                for hv in hardcoded_values:
                                    if abs(value - hv) < 0.001:
                                        total_hardcoded += 1
                                        
        except Exception:
            pass
    
    if total_hardcoded == 0:
        print("✅ ハードコード値は完全に削除されました！")
    else:
        print(f"❌ まだ{total_hardcoded}件のハードコード値が残っています")

def show_current_status():
    """現在のステータス表示"""
    print("\n📊 現在のステータス")
    print("=" * 70)
    
    compressed_dir = Path("large_scale_analysis/compressed")
    all_files = list(compressed_dir.glob("*.pkl.gz"))
    
    # ファイルサイズ計算
    total_size = sum(f.stat().st_size for f in all_files) / (1024 * 1024)  # MB
    
    print(f"総ファイル数: {len(all_files)}")
    print(f"総サイズ: {total_size:.1f} MB")
    
    # 最新ファイル表示
    files_with_time = [(f, f.stat().st_mtime) for f in all_files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    print("\n最新5ファイル:")
    for file_path, mtime in files_with_time[:5]:
        dt = datetime.fromtimestamp(mtime)
        print(f"  {file_path.name} - {dt.strftime('%Y-%m-%d %H:%M')}")

def main():
    """メイン実行関数"""
    print("🚀 残存ハードコード値ファイル完全削除プロセス")
    print("=" * 70)
    
    # 1. 削除実行
    identify_and_remove_hardcoded_files()
    
    # 2. 検証
    verify_cleanup()
    
    # 3. ステータス表示
    show_current_status()
    
    print("\n" + "=" * 70)
    print("✅ クリーンアッププロセス完了")

if __name__ == '__main__':
    main()