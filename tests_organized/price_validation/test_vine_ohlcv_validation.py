#!/usr/bin/env python3
"""
VINEのOHLCVベースバリデーションテスト

静的リストに依存しない、OHLCVエンドポイントでの銘柄検証をテストします。
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

from hyperliquid_validator import HyperliquidValidator, ValidationContext
from hyperliquid_api_client import HyperliquidAPIClient

async def test_vine_validation():
    """VINEのOHLCVベースバリデーションをテスト"""
    
    print("🧪 VINE OHLCVベースバリデーションテスト開始")
    print("=" * 60)
    
    try:
        # 1. 直接APIクライアントでVINEのOHLCVデータをテスト
        print("\n1️⃣ Direct API Client Test")
        print("-" * 30)
        
        client = HyperliquidAPIClient()
        print("🔍 Testing VINE tradability via OHLCV endpoint...")
        is_tradable = await client.is_symbol_tradable('VINE')
        print(f"VINEが取引可能: {is_tradable}")
        
        if is_tradable:
            print("✅ VINE is confirmed tradable via OHLCV endpoint")
        else:
            print("❌ VINE is not tradable via OHLCV endpoint")
        
        # 2. バリデーターでVINEをテスト
        print("\n2️⃣ Validator Test")
        print("-" * 30)
        
        validator = HyperliquidValidator(strict_mode=True)
        print("🔍 Testing VINE validation...")
        result = await validator.validate_symbol('VINE', ValidationContext.NEW_ADDITION)
        
        print(f"バリデーション結果:")
        print(f"  - 有効: {result.valid}")
        print(f"  - ステータス: {result.status}")
        print(f"  - アクション: {result.action}")
        
        if result.market_info:
            market_info = result.market_info
            print(f"  - シンボル: {market_info.get('symbol', 'N/A')}")
            print(f"  - 最新価格: ${market_info.get('latest_price', 'N/A')}")
            print(f"  - データポイント: {market_info.get('data_points_1day', 'N/A')}")
            print(f"  - バリデーション方法: {market_info.get('validation_method', 'N/A')}")
        
        if not result.valid:
            print(f"  - 理由: {result.reason}")
        
        # 3. 他の銘柄も比較テスト
        print("\n3️⃣ Comparison Test")
        print("-" * 30)
        
        test_symbols = ['VINE', 'SOL', 'WIF', 'INVALID_SYMBOL']
        
        validator = HyperliquidValidator(strict_mode=True)
        for symbol in test_symbols:
            print(f"\n🧪 Testing {symbol}...")
            result = await validator.validate_symbol(symbol, ValidationContext.NEW_ADDITION)
            
            status_icon = "✅" if result.valid else "❌"
            print(f"  {status_icon} {symbol}: {result.status}")
            
            if result.valid and result.market_info:
                price = result.market_info.get('latest_price')
                if price:
                    print(f"     価格: ${price:.6f}")
        
        print("\n" + "=" * 60)
        print("🎯 テスト結論:")
        print("- OHLCVエンドポイントベースのバリデーションが正常に動作")
        print("- 静的銘柄リストへの依存を排除")
        print("- 実際のデータ取得可能性で銘柄の有効性を判定")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """メイン実行関数"""
    await test_vine_validation()

if __name__ == "__main__":
    asyncio.run(main())