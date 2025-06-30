#!/usr/bin/env python3
"""
Discord通知の手動テスト
"""

import os
import sys
import time
sys.path.append('/Users/moriwakikeita/tools/long-trader')

# 環境変数が正しく設定されているか確認
print("環境変数確認:")
discord_url = os.getenv('DISCORD_WEBHOOK_URL')
print(f"DISCORD_WEBHOOK_URL設定: {bool(discord_url)}")
if discord_url:
    print(f"URL: {discord_url[:50]}...")

# Discord notifierを直接インポート
from discord_notifier import discord_notifier

print("\n手動Discord通知テスト:")

# 開始通知
print("1. 開始通知送信中...")
result1 = discord_notifier.child_process_started(
    symbol="MANUAL_TEST",
    strategy_name="Conservative_ML",
    timeframe="1h",
    execution_id="manual_test_20250701"
)
print(f"   結果: {result1}")

# 少し待機
time.sleep(2)

# 成功通知
print("2. 成功通知送信中...")
result2 = discord_notifier.child_process_completed(
    symbol="MANUAL_TEST",
    strategy_name="Conservative_ML", 
    timeframe="1h",
    execution_id="manual_test_20250701",
    success=True,
    execution_time=180.0
)
print(f"   結果: {result2}")

# 少し待機
time.sleep(2)

# 失敗通知
print("3. 失敗通知送信中...")
result3 = discord_notifier.child_process_completed(
    symbol="MANUAL_TEST",
    strategy_name="Aggressive_Traditional", 
    timeframe="30m",
    execution_id="manual_test_20250701",
    success=False,
    execution_time=45.0,
    error_msg="テストエラー: データ不足"
)
print(f"   結果: {result3}")

print("\n✅ Discord通知テスト完了！")
print("Discordチャンネルを確認してください。")