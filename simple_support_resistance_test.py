#!/usr/bin/env python3
"""
シンプルな支持線・抵抗線テスト
"""

import asyncio
from hyperliquid_api_client import MultiExchangeAPIClient
from engines.support_resistance_detector import SupportResistanceDetector

async def test_support_resistance():
    print("🔍 DOGE 支持線・抵抗線シンプルテスト")
    
    # データ取得
    api_client = MultiExchangeAPIClient(exchange_type='hyperliquid')
    ohlcv_data = await api_client.get_ohlcv_data_with_period("DOGE", "15m", days=30)
    print(f"データ取得: {len(ohlcv_data)}件")
    
    # 支持線・抵抗線検出
    sr_engine = SupportResistanceDetector()
    current_price = ohlcv_data['close'].iloc[-1]
    
    try:
        support_levels, resistance_levels = sr_engine.detect_levels_from_ohlcv(ohlcv_data, current_price)
        print(f"支持線数: {len(support_levels)}")
        print(f"抵抗線数: {len(resistance_levels)}")
        
        if len(support_levels) == 0 and len(resistance_levels) == 0:
            print("❌ 支持線・抵抗線が検出されませんでした")
        else:
            print("✅ 支持線・抵抗線検出成功")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_support_resistance())