#!/usr/bin/env python3
"""
ハードコード値問題修正の検証テスト

修正前後でのエントリー価格多様性を比較し、
キャッシュ無効化の効果を確認する。
"""

import sys
import time
from pathlib import Path

# プロジェクトルートを追加
sys.path.append(str(Path(__file__).parent))

def test_price_diversity_fix():
    """価格多様性修正の効果をテスト"""
    print("🔧 ハードコード値問題修正テスト開始")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        print("📊 テスト対象: SUI 15m Conservative_ML")
        print("   目的: エントリー価格の多様性確認")
        print("   期待: 修正により価格多様性が大幅向上")
        print()
        
        # 修正後の動作テスト（小規模）
        print("🔍 修正後の動作テスト実行中...")
        start_time = time.time()
        
        # 短時間での分析を3回実行
        entry_prices = []
        for i in range(3):
            print(f"   分析 {i+1}/3 実行中...")
            
            result = system._generate_real_analysis(
                symbol='SUI',
                timeframe='15m', 
                config='Conservative_ML'
            )
            
            if result and len(result) > 0:
                # 最初のトレードのエントリー価格を取得
                first_trade = result[0]
                entry_price = first_trade.get('entry_price', 0)
                entry_prices.append(entry_price)
                print(f"     → エントリー価格: ${entry_price:.6f}")
            else:
                print(f"     → データなし")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 結果分析
        print(f"\n📈 結果分析:")
        print(f"   実行時間: {execution_time:.1f}秒")
        print(f"   取得価格数: {len(entry_prices)}")
        
        if entry_prices:
            unique_prices = len(set(entry_prices))
            diversity = unique_prices / len(entry_prices) * 100
            
            print(f"   ユニーク価格数: {unique_prices}")
            print(f"   価格多様性: {diversity:.1f}%")
            print(f"   価格範囲: ${min(entry_prices):.6f} - ${max(entry_prices):.6f}")
            
            # 判定
            print(f"\n🏆 修正効果判定:")
            if unique_prices == len(entry_prices):
                print("   ✅ 完全多様性 - 全ての価格が異なる")
                print("   ✅ ハードコード値問題が解決されました")
            elif unique_prices > len(entry_prices) * 0.5:
                print("   ✅ 改善確認 - 価格に多様性が生まれました")
                print("   ✅ 修正が効果的に機能しています")
            else:
                print("   ⚠️ 改善不十分 - さらなる調査が必要")
        else:
            print("   ❌ テストデータを取得できませんでした")
        
        return len(entry_prices) > 0 and len(set(entry_prices)) > 1
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        return False

def test_processing_time_impact():
    """処理時間への影響をテスト"""
    print(f"\n" + "=" * 60)
    print("⏱️ 処理時間影響テスト")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem()
        
        print("📊 1回の分析にかかる時間を測定...")
        
        start_time = time.time()
        result = system._generate_real_analysis(
            symbol='SUI',
            timeframe='15m',
            config='Conservative_ML'
        )
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"   1回の分析時間: {execution_time:.1f}秒")
        
        # 推定総時間
        estimated_total = execution_time * 18  # 18パターン
        print(f"   推定総処理時間: {estimated_total:.1f}秒 ({estimated_total/60:.1f}分)")
        
        if execution_time < 15:
            print("   ✅ 許容範囲内の処理時間")
        elif execution_time < 30:
            print("   ⚠️ やや長い処理時間だが許容範囲")
        else:
            print("   🚨 処理時間が長すぎます")
        
        return execution_time < 30
        
    except Exception as e:
        print(f"❌ 処理時間テストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 ハードコード値問題修正の検証開始")
    print("=" * 60)
    print("🎯 目的:")
    print("   - scalable_analysis_system.py の修正効果を確認")
    print("   - エントリー価格の多様性改善を検証") 
    print("   - 処理時間への影響を測定")
    print("=" * 60)
    
    # テスト実行
    diversity_test = test_price_diversity_fix()
    time_test = test_processing_time_impact()
    
    # 総合判定
    print(f"\n" + "=" * 60)
    print("📋 総合テスト結果")
    print("=" * 60)
    print(f"価格多様性テスト: {'✅ 成功' if diversity_test else '❌ 失敗'}")
    print(f"処理時間テスト: {'✅ 成功' if time_test else '❌ 失敗'}")
    
    if diversity_test and time_test:
        print("\n🎉 修正が成功しました！")
        print("✅ ハードコード値問題が解決")
        print("✅ 処理時間も許容範囲内")
        print("\n📝 次のステップ:")
        print("   1. SUI銘柄の完全再分析")
        print("   2. 異常チェックAPIでの検証")
        print("   3. 他銘柄への展開")
    else:
        print("\n⚠️ 一部のテストが失敗しました")
        print("詳細を確認して追加の修正が必要です")
    
    return diversity_test and time_test

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)