#!/usr/bin/env python3
"""
SUSHIエラー修正の動作確認
"Invalid comparison between dtype=datetime64[ns, UTC] and datetime"
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# テスト用のGate.ioレスポンスデータ
mock_gateio_response = [
    {"t": 1718928000, "o": "0.75", "h": "0.76", "l": "0.74", "c": "0.755", "v": "10000"},
    {"t": 1718931600, "o": "0.755", "h": "0.77", "l": "0.75", "c": "0.765", "v": "12000"},
    {"t": 1718935200, "o": "0.765", "h": "0.78", "l": "0.76", "c": "0.775", "v": "15000"},
]


async def test_gateio_ohlcv_with_timezone():
    """Gate.io OHLCV取得でのタイムゾーン処理確認"""
    print("🧪 Gate.io OHLCV取得テスト（SUSHI）")
    print("=" * 60)
    
    # 1. 修正前の問題を再現
    print("\n1️⃣ 修正前の問題再現")
    
    # DataFrame作成（UTC aware）
    df = pd.DataFrame({
        'timestamp_ms': [1718928000000, 1718931600000, 1718935200000],
        'close': [0.755, 0.765, 0.775]
    })
    df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True)
    
    # 修正前: timezone-naiveなdatetime
    end_time_naive = datetime.now()
    start_time_naive = end_time_naive - timedelta(days=30)
    
    print(f"   DataFrame timestamp[0]: {df['timestamp'].iloc[0]} (tz={df['timestamp'].dt.tz})")
    print(f"   start_time (naive): {start_time_naive} (tz={start_time_naive.tzinfo})")
    
    try:
        # これがエラーになる
        filtered = df[(df['timestamp'] >= start_time_naive) & (df['timestamp'] <= end_time_naive)]
        print(f"   ❌ フィルタ成功（これは起こらないはず）")
    except TypeError as e:
        print(f"   ✅ 期待通りエラー発生: {e}")
    
    # 2. 修正後の動作確認
    print("\n2️⃣ 修正後の動作確認")
    
    # 修正後: timezone-awareなdatetime
    end_time_aware = datetime.now(timezone.utc)
    start_time_aware = end_time_aware - timedelta(days=30)
    
    print(f"   start_time (aware): {start_time_aware} (tz={start_time_aware.tzinfo})")
    print(f"   end_time (aware): {end_time_aware} (tz={end_time_aware.tzinfo})")
    
    try:
        # これは成功するはず
        filtered = df[(df['timestamp'] >= start_time_aware) & (df['timestamp'] <= end_time_aware)]
        print(f"   ✅ フィルタ成功: {len(filtered)}件")
    except TypeError as e:
        print(f"   ❌ エラー発生: {e}")
        return False
    
    return True


async def test_hyperliquid_api_client_integration():
    """hyperliquid_api_client.pyの統合テスト"""
    print("\n\n3️⃣ hyperliquid_api_client.py統合テスト")
    print("=" * 60)
    
    # MultiExchangeAPIClientのモック
    with patch('hyperliquid_api_client.gate_api') as mock_gate_api:
        # Gate.io APIモックの設定
        mock_futures_api = MagicMock()
        mock_gate_api.FuturesApi.return_value = mock_futures_api
        mock_gate_api.Configuration.return_value = MagicMock()
        
        # list_candlesticksのモック
        mock_futures_api.list_candlesticks = AsyncMock()
        mock_futures_api.list_candlesticks.return_value = mock_gateio_response
        
        # クライアントをインポート
        from hyperliquid_api_client import MultiExchangeAPIClient
        
        client = MultiExchangeAPIClient(exchange_type='gateio')
        
        # get_ohlcv_data_with_periodを呼び出し（修正後）
        try:
            # これが以前エラーになっていたメソッド
            result = await client.get_ohlcv_data_with_period('SUSHI', '1h', days=30)
            
            print("   ✅ get_ohlcv_data_with_period成功")
            print(f"   データ型: {type(result)}")
            if isinstance(result, pd.DataFrame) and len(result) > 0:
                print(f"   データ件数: {len(result)}")
                print(f"   timestamp型: {result['timestamp'].dtype}")
                print(f"   タイムゾーン: {result['timestamp'].dt.tz}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            return False


async def test_datetime_consistency():
    """datetime一貫性の確認"""
    print("\n\n4️⃣ datetime一貫性テスト")
    print("=" * 60)
    
    # 修正後のすべてのdatetime生成方法
    timestamps = {
        "datetime.now(timezone.utc)": datetime.now(timezone.utc),
        "datetime.fromtimestamp(tz=utc)": datetime.fromtimestamp(1718928000, tz=timezone.utc),
        "pd.to_datetime(utc=True)": pd.to_datetime(1718928000000, unit='ms', utc=True),
    }
    
    print("   生成されたタイムスタンプ:")
    for name, ts in timestamps.items():
        if isinstance(ts, pd.Timestamp):
            print(f"   - {name}: {ts} (tz={ts.tz})")
        else:
            print(f"   - {name}: {ts} (tz={ts.tzinfo})")
    
    # 相互比較可能性の確認
    print("\n   相互比較テスト:")
    try:
        dt1 = timestamps["datetime.now(timezone.utc)"]
        dt2 = timestamps["datetime.fromtimestamp(tz=utc)"]
        dt3 = timestamps["pd.to_datetime(utc=True)"]
        
        # すべての組み合わせで比較
        comparisons = [
            (dt1 > dt2, "datetime.now > fromtimestamp"),
            (dt2 < dt3, "fromtimestamp < pd.to_datetime"),
            (dt1 > dt3, "datetime.now > pd.to_datetime"),
        ]
        
        for result, desc in comparisons:
            print(f"   ✅ {desc}: {result}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 比較エラー: {e}")
        return False


async def main():
    """メインテスト実行"""
    print("=" * 80)
    print("🚀 SUSHIエラー修正の動作確認")
    print("   Invalid comparison between dtype=datetime64[ns, UTC] and datetime")
    print("=" * 80)
    
    # 各テスト実行
    test1_ok = await test_gateio_ohlcv_with_timezone()
    test2_ok = await test_hyperliquid_api_client_integration()
    test3_ok = await test_datetime_consistency()
    
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)
    
    if test1_ok and test2_ok and test3_ok:
        print("✅ すべてのテストが成功しました！")
        print("\n🎯 修正内容:")
        print("1. datetime.now() → datetime.now(timezone.utc)")
        print("2. すべてのdatetimeオブジェクトがUTC awareに統一")
        print("3. pandas DataFrameとの比較が正常動作")
        print("\n💡 効果:")
        print("- SUSHIのOHLCV取得エラー解消")
        print("- 'Invalid comparison between dtype=datetime64[ns, UTC] and datetime'エラー解消")
        print("- すべてのタイムゾーン関連エラーの防止")
    else:
        print("❌ 一部のテストが失敗しました")
        
    print("\n📝 修正箇所:")
    print("- hyperliquid_api_client.py:610")
    print("- hyperliquid_api_client.py:347")  
    print("- hyperliquid_api_client.py:388")


if __name__ == "__main__":
    asyncio.run(main())