#!/usr/bin/env python3
"""
取引所切り替えデモスクリプト
フラグ1つでHyperliquid ⇄ Gate.io の切り替えを実演
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta

from hyperliquid_api_client import MultiExchangeAPIClient, ExchangeType
from exchange_switcher import ExchangeSwitcher


async def demo_exchange_switching():
    """取引所切り替えのデモンストレーション"""
    
    print("🚀 Multi-Exchange API Demo")
    print("=" * 50)
    
    # 1. 設定ファイルによる切り替えデモ
    print("\n📋 1. Configuration File Based Switching")
    switcher = ExchangeSwitcher()
    
    # 現在の設定を表示
    switcher.show_status()
    
    # 2. 直接指定による切り替えデモ
    print("\n🔧 2. Direct Exchange Specification")
    
    test_symbol = "BTC"
    test_timeframe = "1h"
    test_days = 1
    
    # Hyperliquidでテスト
    print(f"\n🔥 Testing {test_symbol} on Hyperliquid...")
    try:
        hyperliquid_client = MultiExchangeAPIClient(exchange_type=ExchangeType.HYPERLIQUID)
        
        # OHLCVデータ取得
        ohlcv_hl = await hyperliquid_client.get_ohlcv_data_with_period(
            test_symbol, test_timeframe, days=test_days
        )
        
        print(f"✅ Hyperliquid: {len(ohlcv_hl)} data points")
        print(f"   Date range: {ohlcv_hl['timestamp'].min()} to {ohlcv_hl['timestamp'].max()}")
        print(f"   Latest price: ${ohlcv_hl['close'].iloc[-1]:,.2f}")
        
    except Exception as e:
        print(f"❌ Hyperliquid failed: {e}")
        ohlcv_hl = None
    
    # Gate.ioでテスト
    print(f"\n🌐 Testing {test_symbol} on Gate.io...")
    try:
        gateio_client = MultiExchangeAPIClient(exchange_type=ExchangeType.GATEIO)
        
        # OHLCVデータ取得
        ohlcv_gate = await gateio_client.get_ohlcv_data_with_period(
            test_symbol, test_timeframe, days=test_days
        )
        
        print(f"✅ Gate.io: {len(ohlcv_gate)} data points")
        print(f"   Date range: {ohlcv_gate['timestamp'].min()} to {ohlcv_gate['timestamp'].max()}")
        print(f"   Latest price: ${ohlcv_gate['close'].iloc[-1]:,.2f}")
        
    except Exception as e:
        print(f"❌ Gate.io failed: {e}")
        ohlcv_gate = None
    
    # 3. 動的切り替えデモ
    print(f"\n🔄 3. Dynamic Exchange Switching")
    
    try:
        # 1つのクライアントで動的に切り替え
        dynamic_client = MultiExchangeAPIClient(exchange_type=ExchangeType.HYPERLIQUID)
        print(f"🔥 Started with: {dynamic_client.get_current_exchange()}")
        
        # Gate.ioに切り替え
        dynamic_client.switch_exchange(ExchangeType.GATEIO)
        print(f"🌐 Switched to: {dynamic_client.get_current_exchange()}")
        
        # データ取得テスト
        symbols = await dynamic_client.get_available_symbols()
        print(f"✅ Available symbols after switch: {len(symbols)}")
        
        # Hyperliquidに戻す
        dynamic_client.switch_exchange(ExchangeType.HYPERLIQUID)
        print(f"🔥 Switched back to: {dynamic_client.get_current_exchange()}")
        
    except Exception as e:
        print(f"❌ Dynamic switching failed: {e}")
    
    # 4. データ比較（両方成功した場合）
    if ohlcv_hl is not None and ohlcv_gate is not None:
        print(f"\n📊 4. Data Comparison")
        print(f"Hyperliquid vs Gate.io for {test_symbol}:")
        
        # 最新価格比較
        hl_price = ohlcv_hl['close'].iloc[-1]
        gate_price = ohlcv_gate['close'].iloc[-1]
        price_diff = abs(hl_price - gate_price)
        price_diff_pct = (price_diff / hl_price) * 100
        
        print(f"   Hyperliquid: ${hl_price:,.2f}")
        print(f"   Gate.io:     ${gate_price:,.2f}")
        print(f"   Difference:  ${price_diff:,.2f} ({price_diff_pct:.3f}%)")
        
        # データポイント数比較
        print(f"   Data points: Hyperliquid={len(ohlcv_hl)}, Gate.io={len(ohlcv_gate)}")
    
    # 5. 環境変数による切り替えデモ
    print(f"\n🌍 5. Environment Variable Demo")
    import os
    
    # 環境変数設定例
    os.environ['EXCHANGE_TYPE'] = 'gateio'
    env_client = MultiExchangeAPIClient()  # 環境変数から自動設定
    print(f"✅ Client from env var: {env_client.get_current_exchange()}")
    
    # クリーンアップ
    del os.environ['EXCHANGE_TYPE']
    
    print(f"\n🎉 Demo completed!")
    print(f"💡 取引所の切り替えはユーザーが明示的に指定した場合のみ実行されます:")
    print(f"   - python exchange_switcher.py hyperliquid")
    print(f"   - python exchange_switcher.py gateio")
    print(f"   - MultiExchangeAPIClient(exchange_type='hyperliquid')")
    print(f"   - MultiExchangeAPIClient(exchange_type='gateio')")
    print(f"   - client.switch_exchange('gateio')  # 明示的な切り替え")
    print(f"")
    print(f"⚠️ 重要: エラーが発生しても自動的な切り替えは行われません")


async def quick_comparison():
    """クイック比較テスト"""
    print("⚡ Quick Exchange Comparison")
    print("-" * 30)
    
    symbols_to_test = ["BTC", "ETH", "SOL"]
    
    for symbol in symbols_to_test:
        print(f"\n💰 Testing {symbol}:")
        
        # Hyperliquid
        try:
            hl_client = MultiExchangeAPIClient(exchange_type="hyperliquid")
            hl_data = await hl_client.get_ohlcv_data_with_period(symbol, "1h", days=1)
            hl_price = hl_data['close'].iloc[-1]
            print(f"   🔥 Hyperliquid: ${hl_price:>8.2f} ({len(hl_data)} points)")
        except Exception as e:
            print(f"   🔥 Hyperliquid: ❌ {str(e)[:50]}...")
        
        # Gate.io
        try:
            gate_client = MultiExchangeAPIClient(exchange_type="gateio")
            gate_data = await gate_client.get_ohlcv_data_with_period(symbol, "1h", days=1)
            gate_price = gate_data['close'].iloc[-1]
            print(f"   🌐 Gate.io:     ${gate_price:>8.2f} ({len(gate_data)} points)")
        except Exception as e:
            print(f"   🌐 Gate.io:     ❌ {str(e)[:50]}...")


def main():
    """メイン実行関数"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        # クイック比較モード
        asyncio.run(quick_comparison())
    else:
        # フルデモモード
        asyncio.run(demo_exchange_switching())


if __name__ == "__main__":
    main()