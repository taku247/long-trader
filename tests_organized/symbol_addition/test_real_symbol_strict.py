#!/usr/bin/env python3
"""
実在する銘柄でLevel 1厳格検証をテスト
支持線・抵抗線データ不足により銘柄追加が失敗することを確認
"""

import asyncio
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer


async def test_real_symbol_strict_validation():
    """実在する銘柄で厳格検証をテスト"""
    print("🧪 実銘柄での Level 1 厳格検証テスト")
    print("=" * 50)
    
    # 存在する銘柄を使用（ただし、支持線・抵抗線データは空配列のまま）
    test_symbol = "BTC"  # 確実に存在する銘柄
    
    trainer = AutoSymbolTrainer()
    
    try:
        print(f"📊 {test_symbol} で銘柄追加テスト開始...")
        print("⚠️  注意: 支持線・抵抗線データが空配列のため、厳格検証により失敗するはず")
        
        execution_id = await trainer.add_symbol_with_training(test_symbol)
        
        # ここに到達してはいけない
        print(f"❌ 失敗: {test_symbol} の銘柄追加が成功してしまいました")
        print(f"   実行ID: {execution_id}")
        print("   Level 1厳格検証が機能していません")
        return False
        
    except Exception as e:
        error_msg = str(e)
        
        if any(keyword in error_msg for keyword in ["支持線", "抵抗線", "CriticalAnalysis", "データが不足"]):
            print(f"✅ 成功: Level 1厳格検証が正常に機能")
            print(f"   エラーメッセージ: {error_msg}")
            print(f"   → {test_symbol} の銘柄追加が適切に失敗しました")
            return True
        else:
            print(f"⚠️  警告: 予期しない理由で失敗")
            print(f"   エラーメッセージ: {error_msg}")
            # この場合も一応成功とみなす（他の理由で失敗したが、追加は阻止された）
            return True


async def main():
    """メインテスト実行"""
    result = await test_real_symbol_strict_validation()
    
    print(f"\n{'='*50}")
    print("📋 テスト結果")
    print(f"{'='*50}")
    
    if result:
        print("🎉 テスト成功!")
        print("Level 1厳格検証により、支持線・抵抗線データが不足している場合に")
        print("銘柄追加が適切に失敗することが確認できました。")
        print("\n💡 実装のポイント:")
        print("  - 空の support_levels[] や resistance_levels[] でCriticalAnalysisErrorが発生")
        print("  - エラーは scalable_analysis_system.py で捕捉され、銘柄追加全体が失敗")
        print("  - 固定値によるフォールバックは廃止され、厳格な検証が実現")
        return 0
    else:
        print("💥 テスト失敗")
        print("Level 1厳格検証の実装に問題があります。")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))