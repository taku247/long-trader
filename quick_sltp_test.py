#!/usr/bin/env python3
"""
損切り・利確計算プラグインの簡単なテスト
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

def quick_test():
    """クイックテスト"""
    
    print("🚀 損切り・利確プラグインクイックテスト")
    print("=" * 50)
    
    # テストデータ
    current_price = 1000.0
    leverage = 5.0
    
    support_levels = [
        SupportResistanceLevel(
            price=950.0, strength=0.8, touch_count=3, level_type='support',
            first_touch=datetime.now(), last_touch=datetime.now(),
            volume_at_level=1000000.0, distance_from_current=5.0
        )
    ]
    
    resistance_levels = [
        SupportResistanceLevel(
            price=1080.0, strength=0.6, touch_count=2, level_type='resistance',
            first_touch=datetime.now(), last_touch=datetime.now(),
            volume_at_level=900000.0, distance_from_current=8.0
        )
    ]
    
    market_context = MarketContext(
        current_price=current_price, volume_24h=10000000.0, volatility=0.02,
        trend_direction='BULLISH', market_phase='MARKUP', timestamp=datetime.now()
    )
    
    # 3つの計算器をテスト
    calculators = [
        DefaultSLTPCalculator(),
        ConservativeSLTPCalculator(),
        AggressiveSLTPCalculator()
    ]
    
    for calc in calculators:
        print(f"\n📊 {calc.name} Calculator:")
        
        levels = calc.calculate_levels(
            current_price=current_price,
            leverage=leverage,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            market_context=market_context
        )
        
        print(f"  損切り: {levels.stop_loss_price:.2f}")
        print(f"  利確: {levels.take_profit_price:.2f}")
        print(f"  RR比: {levels.risk_reward_ratio:.2f}")
    
    # オーケストレーターテスト
    print(f"\n🎭 オーケストレーターテスト:")
    orchestrator = HighLeverageBotOrchestrator(use_default_plugins=False)
    orchestrator.set_stop_loss_take_profit_calculator(AggressiveSLTPCalculator())
    print("✅ プラグイン設定完了")
    
    print("\n🎉 クイックテスト完了!")

if __name__ == "__main__":
    quick_test()