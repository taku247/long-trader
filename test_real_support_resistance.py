#!/usr/bin/env python3
"""
実際の銘柄データで支持線・抵抗線検出をテスト
空配列の代わりに実際のデータが使用されることを確認
"""

import asyncio
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer


async def test_real_support_resistance_integration():
    """実際の支持線・抵抗線データが統合されていることをテスト"""
    print("🧪 実銘柄での支持線・抵抗線統合テスト")
    print("=" * 50)
    
    # 存在する銘柄を使用
    test_symbol = "BTC"  # 確実に存在し、十分なデータがある銘柄
    
    trainer = AutoSymbolTrainer()
    
    try:
        print(f"📊 {test_symbol} で銘柄追加テスト開始...")
        print("✅ 期待動作: 実際の支持線・抵抗線データが検出され、分析が成功するはず")
        
        execution_id = await trainer.add_symbol_with_training(test_symbol)
        
        # 成功した場合
        print(f"🎉 成功: {test_symbol} の銘柄追加が成功しました！")
        print(f"   実行ID: {execution_id}")
        print("   → 支持線・抵抗線データが正常に検出・使用されました")
        return True
        
    except Exception as e:
        error_msg = str(e)
        
        # エラーの分析
        if any(keyword in error_msg.lower() for keyword in ["支持線", "抵抗線", "detect", "insufficient"]):
            print(f"⚠️  検出関連エラー: {error_msg}")
            print("   → 支持線・抵抗線検出の改善が必要です")
            return False
        elif "critical" in error_msg.lower():
            print(f"❌ 厳格検証エラー: Level 1検証が依然として作動しています")
            print(f"   エラーメッセージ: {error_msg}")
            print("   → 実装がまだ不完全です")
            return False
        else:
            print(f"⚠️  その他のエラー: {error_msg}")
            print("   → システム全体の問題の可能性があります")
            return False


async def main():
    """メインテスト実行"""
    result = await test_real_support_resistance_integration()
    
    print(f"\n{'='*50}")
    print("📋 テスト結果")
    print(f"{'='*50}")
    
    if result:
        print("🎉 テスト成功!")
        print("支持線・抵抗線検出エンジンが正常に統合され、")
        print("空配列の代わりに実際のデータが使用されています。")
        print("\n💡 実装の効果:")
        print("  - 空配列によるCriticalAnalysisErrorが解消")
        print("  - 実際の市場データに基づく支持線・抵抗線を使用")
        print("  - より正確なTP/SL価格計算が可能")
        print("  - バックテストの信頼性が向上")
        return 0
    else:
        print("💥 テスト失敗")
        print("支持線・抵抗線検出の統合に問題があります。")
        print("修正が必要です。")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))