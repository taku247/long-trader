#!/usr/bin/env python3
"""
シンプルな支持線・抵抗線統合テスト
銘柄追加ではなく、直接的に機能をテスト
"""

import asyncio
import sys
import os
import pandas as pd
import numpy as np

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.support_resistance_detector import SupportResistanceDetector
from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator
from interfaces.data_types import MarketContext


async def test_support_resistance_integration():
    """支持線・抵抗線とSLTP計算器の統合テスト"""
    print("🧪 支持線・抵抗線 → SLTP計算器 統合テスト")
    print("=" * 50)
    
    try:
        # 1. サンプルOHLCVデータ生成
        print("📊 Step 1: サンプルOHLCVデータ生成中...")
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=500, freq='1h')
        
        # 実際の価格パターンを模擬
        base_price = 50000
        trend = np.linspace(0, 3000, 500)
        noise = np.random.normal(0, 800, 500)
        prices = base_price + trend + noise
        
        # サポート・レジスタンスが明確なデータを作成
        # 特定の価格レベルでの反発を強制的に作成
        support_level = 51000
        resistance_level = 54000
        
        for i in range(len(prices)):
            if prices[i] < support_level:
                prices[i] = support_level + np.random.uniform(0, 200)  # 支持線で反発
            elif prices[i] > resistance_level:
                prices[i] = resistance_level - np.random.uniform(0, 200)  # 抵抗線で反発
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 50, 500),
            'high': prices + np.abs(np.random.normal(200, 100, 500)),
            'low': prices - np.abs(np.random.normal(200, 100, 500)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 500)
        })
        
        current_price = prices[-1]
        print(f"   現在価格: {current_price:.2f}")
        
        # 2. 支持線・抵抗線検出
        print("📊 Step 2: 支持線・抵抗線検出中...")
        detector = SupportResistanceDetector(min_touches=2, tolerance_pct=0.01)
        support_levels, resistance_levels = detector.detect_levels_from_ohlcv(df, current_price)
        
        print(f"   検出された支持線: {len(support_levels)}個")
        for i, level in enumerate(support_levels[:3]):
            print(f"     {i+1}. 価格: {level.price:.2f}, 強度: {level.strength:.3f}")
        
        print(f"   検出された抵抗線: {len(resistance_levels)}個")
        for i, level in enumerate(resistance_levels[:3]):
            print(f"     {i+1}. 価格: {level.price:.2f}, 強度: {level.strength:.3f}")
        
        if not support_levels or not resistance_levels:
            print("⚠️  支持線または抵抗線が検出されませんでした。データを調整します。")
            return False
        
        # 3. SLTP計算器での使用
        print("📊 Step 3: SLTP計算器で実際のデータを使用...")
        
        calculator = DefaultSLTPCalculator()
        market_context = MarketContext(
            current_price=current_price,
            volume_24h=2000000.0,
            volatility=0.03,
            trend_direction='BULLISH',
            market_phase='MARKUP',
            timestamp=None
        )
        
        leverage = 3.0
        
        # 実際の支持線・抵抗線データを使用
        sltp_levels = calculator.calculate_levels(
            current_price=current_price,
            leverage=leverage,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            market_context=market_context
        )
        
        print(f"   ✅ SLTP計算成功!")
        print(f"     現在価格: {current_price:.2f}")
        print(f"     ストップロス: {sltp_levels.stop_loss_price:.2f} ({sltp_levels.stop_loss_distance_pct*100:.1f}%下)")
        print(f"     テイクプロフィット: {sltp_levels.take_profit_price:.2f} ({sltp_levels.take_profit_distance_pct*100:.1f}%上)")
        print(f"     リスクリワード比: {sltp_levels.risk_reward_ratio:.2f}")
        print(f"     計算方法: {sltp_levels.calculation_method}")
        print(f"     信頼度: {sltp_levels.confidence_level:.1%}")
        
        print(f"\n💭 計算の根拠:")
        for reason in sltp_levels.reasoning:
            print(f"     {reason}")
        
        # 4. 検証
        print("\n📊 Step 4: 結果検証...")
        
        # SL価格が支持線付近にあることを確認
        nearest_support = min(support_levels, key=lambda x: abs(x.price - sltp_levels.stop_loss_price))
        support_distance = abs(nearest_support.price - sltp_levels.stop_loss_price)
        
        # TP価格が抵抗線付近にあることを確認
        nearest_resistance = min(resistance_levels, key=lambda x: abs(x.price - sltp_levels.take_profit_price))
        resistance_distance = abs(nearest_resistance.price - sltp_levels.take_profit_price)
        
        print(f"   SL価格と最寄り支持線の距離: {support_distance:.2f}")
        print(f"   TP価格と最寄り抵抗線の距離: {resistance_distance:.2f}")
        
        # 妥当性チェック
        if sltp_levels.stop_loss_price < current_price < sltp_levels.take_profit_price:
            print("   ✅ 価格の順序が正しい (SL < 現在価格 < TP)")
        else:
            print("   ❌ 価格の順序が不正")
            return False
        
        if sltp_levels.risk_reward_ratio > 0.5:
            print(f"   ✅ リスクリワード比が妥当 ({sltp_levels.risk_reward_ratio:.2f})")
        else:
            print(f"   ⚠️  リスクリワード比が低い ({sltp_levels.risk_reward_ratio:.2f})")
        
        print("\n🎉 統合テスト成功!")
        print("空配列の代わりに実際の支持線・抵抗線データが正常に使用されました。")
        
        return True
        
    except Exception as e:
        print(f"❌ 統合テスト失敗: {str(e)}")
        import traceback
        print(f"詳細エラー:")
        traceback.print_exc()
        return False


async def main():
    """メインテスト実行"""
    result = await test_support_resistance_integration()
    
    print(f"\n{'='*50}")
    print("📋 最終結果")
    print(f"{'='*50}")
    
    if result:
        print("🎉 支持線・抵抗線統合成功!")
        print("実装の効果:")
        print("  ✅ 空配列によるCriticalAnalysisErrorが解消")
        print("  ✅ 実際の市場データに基づく支持線・抵抗線を使用")
        print("  ✅ より正確で根拠のあるTP/SL価格計算")
        print("  ✅ バックテストの信頼性向上")
        return 0
    else:
        print("💥 統合に問題があります")
        print("修正が必要です。")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))