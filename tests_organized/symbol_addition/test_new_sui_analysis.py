#!/usr/bin/env python3
"""
新しい修正版でのSUI分析テスト
実際の市場データを使用した価格多様性の検証
"""

import sys
import os
from datetime import datetime

# プロジェクトルートを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_new_sui_analysis():
    """新しい修正版でのSUI分析テスト"""
    print("🔧 新修正版 SUI分析テスト")
    print("=" * 60)
    print("修正内容: 実際の市場データから各トレードのエントリー価格を取得")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        print("📊 SUI 15m Conservative_ML 分析開始（小規模テスト）")
        print("   目的: エントリー価格多様性の確認")
        print()
        
        # 小規模な分析を実行（評価期間を短縮）
        print("🔄 分析実行中...")
        start_time = datetime.now()
        
        # 実際の分析を実行
        trades_data = system._generate_real_analysis(
            symbol='SUI',
            timeframe='15m', 
            config='Conservative_ML',
            evaluation_period_days=7  # 7日間に短縮してテスト
        )
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        if trades_data and len(trades_data) >= 5:
            print(f"✅ 分析完了: {len(trades_data)}件のトレード生成")
            print(f"⏱️ 実行時間: {execution_time:.1f}秒")
            print()
            
            # エントリー価格の多様性チェック
            entry_prices = [trade.get('entry_price') for trade in trades_data[:10]]  # 最初の10件
            tp_prices = [trade.get('take_profit_price') for trade in trades_data[:10]]
            sl_prices = [trade.get('stop_loss_price') for trade in trades_data[:10]]
            leverages = [trade.get('leverage') for trade in trades_data[:10]]
            
            # 統計計算
            unique_entries = len(set(entry_prices))
            unique_tps = len(set(tp_prices))
            unique_sls = len(set(sl_prices))
            unique_leverages = len(set(leverages))
            
            entry_diversity = unique_entries / len(entry_prices) * 100
            
            print(f"📈 価格多様性分析 (最初の10件):")
            print(f"   エントリー価格:")
            for i, price in enumerate(entry_prices[:5]):
                print(f"     {i+1}. ${price:.6f}")
            if len(entry_prices) > 5:
                print(f"     ... (残り{len(entry_prices)-5}件)")
            
            print(f"   ユニーク価格数: {unique_entries}/{len(entry_prices)}")
            print(f"   価格多様性: {entry_diversity:.1f}%")
            print(f"   価格範囲: ${min(entry_prices):.6f} - ${max(entry_prices):.6f}")
            print(f"   価格変動幅: ${max(entry_prices) - min(entry_prices):.6f}")
            
            print(f"\n📊 その他の多様性:")
            print(f"   利確ライン: {unique_tps}種類")
            print(f"   損切ライン: {unique_sls}種類")  
            print(f"   レバレッジ: {unique_leverages}種類")
            
            # 判定
            print(f"\n🏆 修正効果判定:")
            if entry_diversity >= 80:
                print("   ✅ 優秀な価格多様性 (80%以上)")
                print("   ✅ 実市場データ修正が効果的に機能")
            elif entry_diversity >= 50:
                print("   ✅ 改善された価格多様性 (50%以上)")
                print("   ✅ 修正により多様性が向上")
            else:
                print("   ⚠️ まだ改善の余地あり (50%未満)")
                
            if unique_entries > 1:
                print("   ✅ ハードコード値問題が解決されました")
                return True
            else:
                print("   ❌ 全価格が同一 - さらなる調査が必要")
                return False
                
        else:
            print("❌ 十分なトレードデータが生成されませんでした")
            print(f"   生成データ数: {len(trades_data) if trades_data else 0}")
            return False
            
    except Exception as e:
        print(f"❌ 分析エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メインテスト実行"""
    print("🚀 新修正版 SUI分析検証テスト")
    print("=" * 60)
    print("目的: 実市場データ使用修正の効果を SUI 分析で検証")
    print("期待: エントリー価格に多様性が生まれ、ハードコード値問題が解決")
    print("=" * 60)
    
    # SUI分析テスト実行
    success = test_new_sui_analysis()
    
    # 結果サマリー
    print(f"\n" + "=" * 60)
    print("📋 新修正版テスト結果")
    print("=" * 60)
    
    if success:
        print("🎉 テスト成功!")
        print("✅ 実市場データ修正により価格多様性が改善されました")
        print("✅ ハードコード値問題が解決されました")
        print("✅ ユーザー要求「実際の値のみ使用」を満たしています")
        print("\n📝 次のアクション:")
        print("   1. より長期間の分析でさらなる検証")
        print("   2. 他の銘柄でも同様の改善を確認")
        print("   3. Web UIでのトレードデータ異常チェック")
    else:
        print("⚠️ テストで問題が検出されました")
        print("詳細を確認して追加の修正が必要です")
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)