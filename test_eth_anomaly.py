#!/usr/bin/env python3
"""
ETHの異常値分析テスト
エントリー価格: 1,932 USD
エグジット価格: 2,812 USD（45%上昇）
損切りライン: 2,578 USD（エントリーより33%高い）
利確ライン: 2,782 USD（エントリーより44%高い）
"""

import sys
import os
from datetime import datetime

# プロジェクトルートを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_eth_anomaly():
    """ETHの異常値分析テスト"""
    print("🔍 ETH異常値分析テスト")
    print("=" * 60)
    print("異常値:")
    print("  エントリー価格: 1,932 USD")
    print("  エグジット価格: 2,812 USD（45%上昇）")
    print("  損切りライン: 2,578 USD（エントリーより33%高い）")
    print("  利確ライン: 2,782 USD（エントリーより44%高い）")
    print("=" * 60)
    
    try:
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        print("1️⃣ ETH分析実行")
        bot = HighLeverageBotOrchestrator(use_default_plugins=True, exchange='gateio')
        
        # ETH分析実行
        result = bot.analyze_symbol('ETH', '3m', 'Aggressive_ML')
        
        if result:
            current_price = result.get('current_price', 0)
            stop_loss = result.get('stop_loss_price', 0)
            take_profit = result.get('take_profit_price', 0)
            leverage = result.get('leverage', 0)
            
            print(f"\n2️⃣ ETH分析結果:")
            print(f"   現在価格: ${current_price:.4f}")
            print(f"   損切りライン: ${stop_loss:.4f}")
            print(f"   利確ライン: ${take_profit:.4f}")
            print(f"   レバレッジ: {leverage:.1f}x")
            
            # 異常値チェック
            if stop_loss > current_price:
                print(f"\n🚨 異常値検出!")
                print(f"   損切りライン({stop_loss:.4f}) > 現在価格({current_price:.4f})")
                print(f"   差額: +{((stop_loss/current_price-1)*100):.1f}%")
                
            if take_profit > current_price * 1.2:  # 20%以上の場合
                print(f"\n🚨 異常値検出!")
                print(f"   利確ライン({take_profit:.4f})が異常に高い")
                print(f"   現在価格からの上昇: +{((take_profit/current_price-1)*100):.1f}%")
            
            # 価格の論理性チェック
            print(f"\n3️⃣ 価格論理性チェック:")
            print(f"   損切り < 現在価格 < 利確: {stop_loss < current_price < take_profit}")
            print(f"   損切り距離: {((current_price-stop_loss)/current_price*100):.1f}%")
            print(f"   利確距離: {((take_profit-current_price)/current_price*100):.1f}%")
            
        else:
            print("❌ ETH分析結果が取得できませんでした")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

def test_sltp_calculator_directly():
    """SLTP計算機を直接テストして異常値の原因を特定"""
    print(f"\n" + "=" * 60)
    print("🔧 SLTP計算機直接テスト")
    print("=" * 60)
    
    try:
        from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator, AggressiveSLTPCalculator
        from interfaces.data_types import MarketContext
        
        # ETHの現在価格を取得
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        bot = HighLeverageBotOrchestrator(exchange='gateio')
        
        # 市場データを取得してETHの実際の価格を確認
        data = bot._fetch_market_data('ETH', '3m')
        current_price = data['close'].iloc[-1] if not data.empty else 3500.0
        
        print(f"ETH現在価格（実際の市場データ）: ${current_price:.4f}")
        
        # 模擬市場コンテキスト
        market_context = MarketContext(
            current_price=current_price,
            volume_24h=1000000.0,
            volatility=0.03,
            trend_direction='BULLISH',
            market_phase='MARKUP',
            timestamp=datetime.now()
        )
        
        # 異なる計算機でテスト
        calculators = [
            ("Default", DefaultSLTPCalculator()),
            ("Aggressive", AggressiveSLTPCalculator())
        ]
        
        test_leverages = [2.0, 5.0, 10.0]
        
        for calc_name, calculator in calculators:
            print(f"\n{calc_name} 計算機テスト:")
            
            for leverage in test_leverages:
                try:
                    levels = calculator.calculate_levels(
                        current_price=current_price,
                        leverage=leverage,
                        support_levels=[],  # 簡略化
                        resistance_levels=[],  # 簡略化
                        market_context=market_context
                    )
                    
                    sl_distance = ((current_price - levels.stop_loss_price) / current_price) * 100
                    tp_distance = ((levels.take_profit_price - current_price) / current_price) * 100
                    
                    print(f"  レバレッジ {leverage}x:")
                    print(f"    損切り: ${levels.stop_loss_price:.4f} ({sl_distance:.1f}%下)")
                    print(f"    利確: ${levels.take_profit_price:.4f} ({tp_distance:.1f}%上)")
                    print(f"    RR比: {levels.risk_reward_ratio:.2f}")
                    
                    # 異常値チェック
                    if levels.stop_loss_price > current_price:
                        print(f"    🚨 異常: 損切り > 現在価格!")
                    if levels.take_profit_price > current_price * 2:
                        print(f"    🚨 異常: 利確が現在価格の2倍以上!")
                        
                except Exception as e:
                    print(f"    ❌ エラー: {e}")
                    
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メインテスト実行"""
    print("🚀 ETH異常値原因特定テスト")
    print("=" * 60)
    print("目的: ETHの異常な価格設定の原因を特定")
    print("問題: 損切りライン > エントリー価格 の論理エラー")
    print("=" * 60)
    
    # 1. ETH分析テスト
    test_eth_anomaly()
    
    # 2. SLTP計算機直接テスト
    test_sltp_calculator_directly()
    
    print(f"\n" + "=" * 60)
    print("📋 テスト完了")
    print("=" * 60)

if __name__ == '__main__':
    main()