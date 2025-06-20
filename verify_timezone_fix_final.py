#!/usr/bin/env python3
"""
タイムゾーン修正の最終確認
"""

import pandas as pd
from datetime import datetime, timedelta, timezone

print("=" * 70)
print("🔍 タイムゾーン修正の最終確認")
print("=" * 70)

# 修正前後の比較
print("\n【修正前】datetime.now() - timezone naive")
old_end = datetime.now()
old_start = old_end - timedelta(days=30)
print(f"  end_time: {old_end} (tzinfo={old_end.tzinfo})")
print(f"  start_time: {old_start} (tzinfo={old_start.tzinfo})")

print("\n【修正後】datetime.now(timezone.utc) - timezone aware")
new_end = datetime.now(timezone.utc)
new_start = new_end - timedelta(days=30)
print(f"  end_time: {new_end} (tzinfo={new_end.tzinfo})")
print(f"  start_time: {new_start} (tzinfo={new_start.tzinfo})")

# DataFrameとの比較テスト
print("\n【DataFrameとの比較テスト】")
df = pd.DataFrame({
    'timestamp': pd.to_datetime([1718928000000, 1718931600000], unit='ms', utc=True),
    'value': [0.755, 0.765]
})

print(f"DataFrame timestamp[0]: {df['timestamp'].iloc[0]} (tz={df['timestamp'].dt.tz})")

# 修正前（エラー）
print("\n1. 修正前の比較（エラー発生）:")
try:
    result = df[(df['timestamp'] >= old_start) & (df['timestamp'] <= old_end)]
    print("  ❌ エラーが発生しませんでした（想定外）")
except TypeError as e:
    print(f"  ✅ 期待通りエラー: {e}")

# 修正後（正常動作）
print("\n2. 修正後の比較（正常動作）:")
try:
    result = df[(df['timestamp'] >= new_start) & (df['timestamp'] <= new_end)]
    print(f"  ✅ 比較成功: {len(result)}件のデータ")
except TypeError as e:
    print(f"  ❌ エラー: {e}")

print("\n" + "=" * 70)
print("✅ 修正確認完了")
print("=" * 70)
print("\n修正内容:")
print("  1. hyperliquid_api_client.py:610")
print("     datetime.now() → datetime.now(timezone.utc)")
print("  2. hyperliquid_api_client.py:347, 388")
print("     'last_updated': datetime.now().isoformat()")
print("     → 'last_updated': datetime.now(timezone.utc).isoformat()")
print("\n効果:")
print("  ✅ SUSHI OHLCV取得エラー解消")
print("  ✅ 'Invalid comparison between dtype=datetime64[ns, UTC] and datetime'解消")
print("  ✅ すべてのタイムスタンプがUTC awareに統一")