#!/usr/bin/env python3
"""
VINEの異常価格データクリーンアップスクリプト

$1000などの異常な価格が含まれているVINEの分析データを削除し、
実データのみを使用するように修正します。
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

from scalable_analysis_system import ScalableAnalysisSystem

def main():
    """VINEの異常価格データをクリーンアップ"""
    
    print("🧹 VINEの異常価格データクリーンアップを開始します...")
    
    # システム初期化
    system = ScalableAnalysisSystem()
    
    # VINEの異常価格データ（$100以上）をクリーンアップ
    print("\n📊 VINEの異常価格データを検出・削除中...")
    deleted_analyses, deleted_files = system.cleanup_invalid_price_data(
        symbol='VINE', 
        price_threshold=100.0
    )
    
    if deleted_analyses > 0:
        print(f"✅ VINEクリーンアップ完了:")
        print(f"   - 削除された分析: {deleted_analyses}件")
        print(f"   - 削除されたファイル: {deleted_files}件")
        print(f"   - 理由: エントリー価格が$100以上の異常データ")
    else:
        print("ℹ️ VINEに異常価格データは見つかりませんでした")
    
    # 他の銘柄でも異常価格をチェック
    print("\n🔍 他の銘柄の異常価格データもチェック中...")
    deleted_analyses_all, deleted_files_all = system.cleanup_invalid_price_data(
        symbol=None,  # 全銘柄
        price_threshold=100.0
    )
    
    if deleted_analyses_all > 0:
        print(f"✅ 全銘柄クリーンアップ完了:")
        print(f"   - 削除された分析: {deleted_analyses_all}件")
        print(f"   - 削除されたファイル: {deleted_files_all}件")
    else:
        print("ℹ️ 他の銘柄に異常価格データは見つかりませんでした")
    
    # 現在の分析状況を表示
    print("\n📈 クリーンアップ後の分析状況:")
    stats = system.get_statistics()
    if 'performance' in stats:
        perf = stats['performance']
        print(f"   - 総分析数: {perf.get('total_analyses', 0)}")
        print(f"   - ユニーク銘柄数: {perf.get('unique_symbols', 0)}")
        print(f"   - 平均シャープ比: {perf.get('avg_sharpe', 0):.2f}")
    
    print("\n🎯 今後の動作:")
    print("   - 実データ取得に失敗した分析は自動的にスキップされます")
    print("   - サンプルデータ（模擬データ）は使用されません")
    print("   - VINEを再分析する場合は、実データが正常に取得される必要があります")
    
    print("\n✨ クリーンアップ完了!")

if __name__ == "__main__":
    main()