#!/usr/bin/env python3
"""
ハードコード値ファイルの削除リスト生成

debug_hardcoded_analysis.pyの結果を基に、削除すべきファイルのリストを生成
"""

import json
import os
from pathlib import Path

def generate_delete_list():
    """削除対象ファイルリストを生成"""
    
    # 分析結果ファイルを読み込み
    analysis_files = list(Path('.').glob('hardcoded_bug_analysis_*.json'))
    
    if not analysis_files:
        print("❌ 分析結果ファイルが見つかりません")
        return
    
    # 最新の分析結果を使用
    latest_file = max(analysis_files, key=lambda f: f.stat().st_mtime)
    print(f"📊 分析結果ファイル: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
    
    # 削除対象ファイルを特定
    files_to_delete = set()
    
    # 1. ハードコード値違反ファイル
    for violation in analysis_data.get('hardcoded_violations', []):
        if violation.get('severity') == 'HIGH':
            file_path = violation.get('file_path')
            if file_path:
                files_to_delete.add(file_path)
    
    # 2. 静的価格設定ファイル（HIGH）
    for strategy in analysis_data.get('static_pricing_strategies', []):
        if strategy.get('severity') == 'HIGH':
            # ファイルパスを構築
            symbol = strategy.get('symbol')
            timeframe = strategy.get('timeframe')
            strategy_name = strategy.get('strategy')
            if symbol and timeframe and strategy_name:
                file_path = f"large_scale_analysis/compressed/{symbol}_{timeframe}_{strategy_name}.pkl.gz"
                files_to_delete.add(file_path)
    
    # 3. TOKEN系ファイル（存在しない銘柄）
    token_patterns = ['TOKEN001', 'TOKEN002', 'TOKEN003', 'TOKEN004', 'TOKEN005',
                     'TOKEN006', 'TOKEN007', 'TOKEN008', 'TOKEN009', 'TOKEN010']
    
    for pattern in token_patterns:
        token_files = list(Path('large_scale_analysis/compressed').glob(f'{pattern}_*.pkl.gz'))
        for file_path in token_files:
            files_to_delete.add(str(file_path))
    
    # 削除リストを保存
    delete_list = sorted(list(files_to_delete))
    
    print(f"\n📋 削除対象ファイル数: {len(delete_list)}")
    
    # カテゴリ別統計
    categories = {
        'TOKEN系': sum(1 for f in delete_list if any(token in f for token in token_patterns)),
        'HYPE系': sum(1 for f in delete_list if 'HYPE' in f),
        'GMT系': sum(1 for f in delete_list if 'GMT' in f),
        'CAKE系': sum(1 for f in delete_list if 'CAKE' in f),
        'FIL系': sum(1 for f in delete_list if 'FIL' in f),
        'その他': 0
    }
    categories['その他'] = len(delete_list) - sum(categories.values())
    
    print("\n📊 カテゴリ別統計:")
    for category, count in categories.items():
        if count > 0:
            print(f"   {category}: {count}件")
    
    # ファイルリストを保存
    with open('hardcoded_files_to_delete.txt', 'w', encoding='utf-8') as f:
        for file_path in delete_list:
            f.write(f"{file_path}\n")
    
    print(f"\n💾 削除リスト保存: hardcoded_files_to_delete.txt")
    
    # 最初の20件を表示
    print("\n📋 削除対象ファイル（最初の20件）:")
    for i, file_path in enumerate(delete_list[:20]):
        print(f"   {i+1:2d}. {os.path.basename(file_path)}")
    
    if len(delete_list) > 20:
        print(f"   ... および {len(delete_list)-20} 件")
    
    return delete_list

def main():
    """メイン実行関数"""
    print("🗂️ ハードコード値ファイル削除リスト生成")
    print("=" * 50)
    
    delete_list = generate_delete_list()
    
    if delete_list:
        print(f"\n✅ 削除リスト生成完了: {len(delete_list)}件")
        print("\n⚠️ 次のステップ:")
        print("1. hardcoded_files_to_delete.txt の内容を確認")
        print("2. 問題ないことを確認後、削除実行")
        print("3. コマンド例:")
        print("   cat hardcoded_files_to_delete.txt | head -10  # 最初の10件確認")
        print("   wc -l hardcoded_files_to_delete.txt         # 総数確認")
    else:
        print("❌ 削除リスト生成に失敗しました")

if __name__ == '__main__':
    main()