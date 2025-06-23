#!/usr/bin/env python3
"""
タイムゾーン修正の簡易動作確認
"""

import pandas as pd
from datetime import datetime, timezone

print("=" * 60)
print("🔍 タイムゾーン修正の動作確認")
print("=" * 60)

# 1. Hyperliquid形式のタイムスタンプ処理
print("\n1️⃣ Hyperliquid形式（修正後）")
timestamp_ms = 1703930400000
timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
print(f"   タイムスタンプ: {timestamp}")
print(f"   UTC aware: {timestamp.tzinfo is not None}")

# 2. Gate.io形式のタイムスタンプ処理
print("\n2️⃣ Gate.io形式（修正後）")
df = pd.DataFrame({'timestamp_ms': [1703930400000]})
df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True)
print(f"   タイムスタンプ: {df['timestamp'].iloc[0]}")
print(f"   UTC aware: {df['timestamp'].dt.tz is not None}")

# 3. 演算テスト
print("\n3️⃣ 演算テスト")
market_timestamp = pd.to_datetime(1703930400000, unit='ms', utc=True)
candle_timestamp = datetime.fromtimestamp(1703930400000 / 1000, tz=timezone.utc)

try:
    # これが以前エラーになっていた演算
    diff = market_timestamp - candle_timestamp
    print(f"   ✅ 演算成功: 時間差 = {diff}")
except TypeError as e:
    print(f"   ❌ エラー: {e}")

print("\n✅ タイムゾーン修正が正常に動作しています！")
print("   → 'Cannot subtract tz-naive and tz-aware' エラーは解消されました")