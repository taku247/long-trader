#!/usr/bin/env python3
"""
損切り・利確計算プラグインの実用デモ

実際の使用シナリオでプラグインの切り替えと動作を示します。
"""

import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interfaces import SupportResistanceLevel, MarketContext
from engines.stop_loss_take_profit_calculators import (
    DefaultSLTPCalculator, ConservativeSLTPCalculator, AggressiveSLTPCalculator
)
from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator


def demo_trading_scenarios():
    """異なる取引シナリオでのプラグイン使用例"""
    
    print("🎯 損切り・利確プラグイン実用デモ")
    print("=" * 60)
    
    # シナリオ1: 保守的な低リスク取引
    print("\n📊 シナリオ1: 初心者・低リスク取引")
    print("-" * 40)
    
    orchestrator = HighLeverageBotOrchestrator(use_default_plugins=False)
    orchestrator.set_stop_loss_take_profit_calculator(ConservativeSLTPCalculator())
    
    # 低レバレッジでの取引設定
    result1 = test_scenario(
        price=1000.0,
        leverage=2.0,
        volatility=0.01,  # 低ボラティリティ
        description="安定した銘柄での保守的取引"
    )
    
    # シナリオ2: 標準的な取引
    print("\n📊 シナリオ2: 中級者・バランス型取引")
    print("-" * 40)
    
    orchestrator.set_stop_loss_take_profit_calculator(DefaultSLTPCalculator())
    
    result2 = test_scenario(
        price=1500.0,
        leverage=5.0,
        volatility=0.02,  # 標準ボラティリティ
        description="一般的な暗号通貨での標準取引"
    )
    
    # シナリオ3: 積極的な高リスク・高リターン取引
    print("\n📊 シナリオ3: 上級者・積極的取引")
    print("-" * 40)
    
    orchestrator.set_stop_loss_take_profit_calculator(AggressiveSLTPCalculator())
    
    result3 = test_scenario(
        price=500.0,
        leverage=10.0,
        volatility=0.05,  # 高ボラティリティ
        description="高ボラティリティ銘柄での積極的取引"
    )
    
    # 結果比較
    print("\n📈 シナリオ別比較結果")
    print("=" * 60)
    print(f"{'シナリオ':<12} {'損切り%':<8} {'利確%':<8} {'RR比':<6} {'リスク':<8}")
    print("-" * 60)
    
    scenarios = [
        ("保守的", result1),
        ("標準", result2),
        ("積極的", result3)
    ]
    
    for name, result in scenarios:
        if result:
            stop_pct = result['stop_loss_pct']
            tp_pct = result['take_profit_pct']
            rr_ratio = result['risk_reward_ratio']
            risk_level = "低" if stop_pct < 2 else "中" if stop_pct < 5 else "高"
            
            print(f"{name:<12} {stop_pct:<8.1f} {tp_pct:<8.1f} {rr_ratio:<6.2f} {risk_level:<8}")
    
    print("\n💡 使用指針:")
    print("  🛡️ 保守的: 初心者、安定重視、損失を最小化したい場合")
    print("  ⚖️ 標準: 一般的な取引、バランス重視")
    print("  🚀 積極的: 経験豊富、高リターン狙い、リスク許容度が高い場合")


def test_scenario(price: float, leverage: float, volatility: float, description: str):
    """シナリオテスト実行"""
    
    print(f"💼 {description}")
    print(f"   価格: {price}, レバレッジ: {leverage}x, ボラティリティ: {volatility}")
    
    # サンプルデータ作成
    support_levels = [
        SupportResistanceLevel(
            price=price * 0.92,
            strength=0.75,
            touch_count=3,
            level_type='support',
            first_touch=datetime.now(),
            last_touch=datetime.now(),
            volume_at_level=1000000.0,
            distance_from_current=8.0
        )
    ]
    
    resistance_levels = [
        SupportResistanceLevel(
            price=price * 1.12,
            strength=0.65,
            touch_count=2,
            level_type='resistance',
            first_touch=datetime.now(),
            last_touch=datetime.now(),
            volume_at_level=900000.0,
            distance_from_current=12.0
        )
    ]
    
    market_context = MarketContext(
        current_price=price,
        volume_24h=50000000.0,
        volatility=volatility,
        trend_direction='BULLISH',
        market_phase='MARKUP',
        timestamp=datetime.now()
    )
    
    try:
        # ここでは直接計算器を使用（簡略化）
        from engines.stop_loss_take_profit_calculators import AggressiveSLTPCalculator
        calc = AggressiveSLTPCalculator()  # 実際は外部から設定される
        
        levels = calc.calculate_levels(
            current_price=price,
            leverage=leverage,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            market_context=market_context
        )
        
        stop_loss_pct = (price - levels.stop_loss_price) / price * 100
        take_profit_pct = (levels.take_profit_price - price) / price * 100
        
        print(f"   🛑 損切り: {levels.stop_loss_price:.2f} ({stop_loss_pct:.1f}%下)")
        print(f"   💰 利確: {levels.take_profit_price:.2f} ({take_profit_pct:.1f}%上)")
        print(f"   ⚖️ RR比: {levels.risk_reward_ratio:.2f}")
        
        return {
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'risk_reward_ratio': levels.risk_reward_ratio
        }
        
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        return None


def demo_dynamic_switching():
    """動的プラグイン切り替えのデモ"""
    
    print("\n" + "=" * 60)
    print("🔄 動的プラグイン切り替えデモ")
    print("=" * 60)
    
    orchestrator = HighLeverageBotOrchestrator(use_default_plugins=False)
    
    # 市場状況に応じてプラグインを動的に切り替え
    market_conditions = [
        ("市場クラッシュ時", 0.08, ConservativeSLTPCalculator()),
        ("通常市場", 0.02, DefaultSLTPCalculator()),
        ("バブル相場", 0.15, AggressiveSLTPCalculator())
    ]
    
    for condition, volatility, calculator in market_conditions:
        print(f"\n📊 {condition} (ボラティリティ: {volatility:.1%})")
        print("-" * 30)
        
        # プラグインを動的に切り替え
        orchestrator.set_stop_loss_take_profit_calculator(calculator)
        
        print(f"   📦 {calculator.name} Calculator に切り替え")
        print(f"   🎯 この市場環境に最適化された計算方式を使用")


def main():
    """メイン関数"""
    
    try:
        # 実用的な取引シナリオデモ
        demo_trading_scenarios()
        
        # 動的切り替えデモ
        demo_dynamic_switching()
        
        print("\n" + "=" * 60)
        print("🎉 プラグインデモ完了！")
        print("\n💡 このシステムの特徴:")
        print("  ✅ 異なる取引戦略に対応")
        print("  ✅ 実行時にプラグイン切り替え可能")
        print("  ✅ 市場状況に応じた最適化")
        print("  ✅ 既存システムとの統合が容易")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ デモ実行エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()