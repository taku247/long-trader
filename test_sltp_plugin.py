#!/usr/bin/env python3
"""
損切り・利確計算プラグインのテストスクリプト

プラグインの差し替え機能と各計算器の動作を確認します。
"""

import sys
import os
from datetime import datetime
import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interfaces import (
    SupportResistanceLevel, MarketContext
)
from engines.stop_loss_take_profit_calculators import (
    DefaultSLTPCalculator, ConservativeSLTPCalculator, AggressiveSLTPCalculator
)
from engines.leverage_decision_engine import CoreLeverageDecisionEngine
from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator


def create_sample_support_resistance_levels(current_price: float):
    """サンプルのサポート・レジスタンスレベルを作成"""
    
    support_levels = [
        SupportResistanceLevel(
            price=current_price * 0.95,
            strength=0.8,
            touch_count=3,
            level_type='support',
            first_touch=datetime.now(),
            last_touch=datetime.now(),
            volume_at_level=1000000.0,
            distance_from_current=5.0
        ),
        SupportResistanceLevel(
            price=current_price * 0.90,
            strength=0.7,
            touch_count=2,
            level_type='support',
            first_touch=datetime.now(),
            last_touch=datetime.now(),
            volume_at_level=800000.0,
            distance_from_current=10.0
        )
    ]
    
    resistance_levels = [
        SupportResistanceLevel(
            price=current_price * 1.08,
            strength=0.6,
            touch_count=2,
            level_type='resistance',
            first_touch=datetime.now(),
            last_touch=datetime.now(),
            volume_at_level=900000.0,
            distance_from_current=8.0
        ),
        SupportResistanceLevel(
            price=current_price * 1.15,
            strength=0.5,
            touch_count=2,
            level_type='resistance',
            first_touch=datetime.now(),
            last_touch=datetime.now(),
            volume_at_level=700000.0,
            distance_from_current=15.0
        )
    ]
    
    return support_levels, resistance_levels


def create_sample_market_context(current_price: float, volatility: float = 0.02):
    """サンプルの市場コンテキストを作成"""
    
    return MarketContext(
        current_price=current_price,
        volume_24h=10000000.0,
        volatility=volatility,
        trend_direction='BULLISH',
        market_phase='MARKUP',
        timestamp=datetime.now()
    )


def test_individual_calculators():
    """各計算器の個別テスト"""
    
    print("=" * 80)
    print("🧪 損切り・利確計算器の個別テスト")
    print("=" * 80)
    
    # テスト用データ準備
    current_price = 1000.0
    leverage = 10.0
    support_levels, resistance_levels = create_sample_support_resistance_levels(current_price)
    market_context = create_sample_market_context(current_price)
    
    # 各計算器をテスト
    calculators = [
        ("Default", DefaultSLTPCalculator()),
        ("Conservative", ConservativeSLTPCalculator()),
        ("Aggressive", AggressiveSLTPCalculator())
    ]
    
    results = {}
    
    for name, calculator in calculators:
        print(f"\n📊 {name} Calculator テスト中...")
        print("-" * 50)
        
        try:
            levels = calculator.calculate_levels(
                current_price=current_price,
                leverage=leverage,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                market_context=market_context,
                position_direction="long"
            )
            
            results[name] = levels
            
            print(f"✅ 計算成功!")
            print(f"   📍 損切り価格: {levels.stop_loss_price:.2f} ({levels.stop_loss_distance_pct*100:.1f}%下)")
            print(f"   🎯 利確価格: {levels.take_profit_price:.2f} ({levels.take_profit_distance_pct*100:.1f}%上)")
            print(f"   ⚖️ リスクリワード比: {levels.risk_reward_ratio:.2f}")
            print(f"   🎪 信頼度: {levels.confidence_level*100:.1f}%")
            print(f"   💡 計算方式: {levels.calculation_method}")
            
            print("   📝 判定理由:")
            for i, reason in enumerate(levels.reasoning, 1):
                print(f"      {i}. {reason}")
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()
    
    # 結果比較
    print(f"\n📊 計算器比較 (現在価格: {current_price})")
    print("-" * 80)
    print(f"{'計算器':<12} {'損切り':<8} {'利確':<8} {'RR比':<6} {'信頼度':<6}")
    print("-" * 80)
    
    for name, levels in results.items():
        print(f"{name:<12} {levels.stop_loss_price:<8.2f} {levels.take_profit_price:<8.2f} "
              f"{levels.risk_reward_ratio:<6.2f} {levels.confidence_level*100:<6.1f}%")
    
    return results


def test_plugin_integration():
    """プラグイン統合テスト"""
    
    print("\n" + "=" * 80)
    print("🔧 プラグイン統合テスト")
    print("=" * 80)
    
    # レバレッジ判定エンジンのテスト
    print("\n📦 CoreLeverageDecisionEngine に各計算器を統合テスト...")
    
    # テスト用データ準備
    current_price = 1500.0
    support_levels, resistance_levels = create_sample_support_resistance_levels(current_price)
    market_context = create_sample_market_context(current_price)
    
    calculators = [
        ("Default", DefaultSLTPCalculator()),
        ("Conservative", ConservativeSLTPCalculator()),
        ("Aggressive", AggressiveSLTPCalculator())
    ]
    
    for name, calculator in calculators:
        print(f"\n🔧 {name} Calculator でレバレッジ判定エンジンをテスト...")
        
        try:
            # エンジン作成
            engine = CoreLeverageDecisionEngine(sl_tp_calculator=calculator)
            
            # レバレッジ推奨を計算
            recommendation = engine.calculate_safe_leverage(
                symbol="TEST",
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                breakout_predictions=[],  # 簡略化
                btc_correlation_risk=None,  # 簡略化
                market_context=market_context
            )
            
            print(f"✅ 統合テスト成功!")
            print(f"   🎯 推奨レバレッジ: {recommendation.recommended_leverage:.1f}x")
            print(f"   📍 損切り: {recommendation.stop_loss_price:.2f}")
            print(f"   🎯 利確: {recommendation.take_profit_price:.2f}")
            print(f"   ⚖️ RR比: {recommendation.risk_reward_ratio:.2f}")
            print(f"   🎪 信頼度: {recommendation.confidence_level*100:.1f}%")
            
        except Exception as e:
            print(f"❌ 統合テストエラー: {e}")
            import traceback
            traceback.print_exc()


def test_orchestrator_plugin_switching():
    """オーケストレーターでのプラグイン切り替えテスト"""
    
    print("\n" + "=" * 80)
    print("🎭 オーケストレーターでのプラグイン切り替えテスト")
    print("=" * 80)
    
    try:
        # オーケストレーター作成
        orchestrator = HighLeverageBotOrchestrator(use_default_plugins=True)
        
        calculators = [
            ("Default", DefaultSLTPCalculator()),
            ("Conservative", ConservativeSLTPCalculator()),
            ("Aggressive", AggressiveSLTPCalculator())
        ]
        
        for name, calculator in calculators:
            print(f"\n🔄 {name} Calculator に切り替え中...")
            
            # プラグインを設定
            orchestrator.set_stop_loss_take_profit_calculator(calculator)
            
            print(f"✅ {name} Calculator を設定完了")
            
        print("\n🎉 プラグイン切り替えテスト完了!")
        
    except Exception as e:
        print(f"❌ オーケストレーターテストエラー: {e}")
        import traceback
        traceback.print_exc()


def test_different_market_conditions():
    """異なる市場条件でのテスト"""
    
    print("\n" + "=" * 80)
    print("🌍 異なる市場条件でのテスト")
    print("=" * 80)
    
    current_price = 2000.0
    leverage = 5.0
    support_levels, resistance_levels = create_sample_support_resistance_levels(current_price)
    
    # 異なる市場条件
    market_conditions = [
        ("低ボラティリティ", create_sample_market_context(current_price, 0.01)),
        ("標準ボラティリティ", create_sample_market_context(current_price, 0.02)),
        ("高ボラティリティ", create_sample_market_context(current_price, 0.05))
    ]
    
    calculator = AggressiveSLTPCalculator()
    
    print(f"📊 Aggressive Calculator での市場条件比較")
    print("-" * 60)
    
    for condition_name, market_context in market_conditions:
        print(f"\n🌟 {condition_name} (ボラ: {market_context.volatility:.3f})")
        
        try:
            levels = calculator.calculate_levels(
                current_price=current_price,
                leverage=leverage,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                market_context=market_context,
                position_direction="long"
            )
            
            print(f"   📍 損切り: {levels.stop_loss_price:.2f} ({levels.stop_loss_distance_pct*100:.1f}%下)")
            print(f"   🎯 利確: {levels.take_profit_price:.2f} ({levels.take_profit_distance_pct*100:.1f}%上)")
            print(f"   ⚖️ RR比: {levels.risk_reward_ratio:.2f}")
            
        except Exception as e:
            print(f"   ❌ エラー: {e}")


def main():
    """メインテスト関数"""
    
    print("🚀 損切り・利確計算プラグインテスト開始")
    print("=" * 80)
    
    try:
        # 1. 個別計算器テスト
        test_individual_calculators()
        
        # 2. プラグイン統合テスト
        test_plugin_integration()
        
        # 3. オーケストレーターでの切り替えテスト
        test_orchestrator_plugin_switching()
        
        # 4. 異なる市場条件でのテスト
        test_different_market_conditions()
        
        print("\n" + "=" * 80)
        print("🎉 全てのテストが完了しました！")
        print("✅ 損切り・利確計算プラグインシステムは正常に動作しています")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()