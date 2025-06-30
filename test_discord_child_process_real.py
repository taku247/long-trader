#!/usr/bin/env python3
"""
実際のProcessPoolExecutor環境でのDiscord通知テスト
"""

import os
import sys
from concurrent.futures import ProcessPoolExecutor
import time

def child_process_discord_test(test_id):
    """子プロセス内でDiscord通知をテスト"""
    try:
        # 環境変数確認
        discord_url = os.getenv('DISCORD_WEBHOOK_URL')
        print(f"子プロセス {test_id}: DISCORD_WEBHOOK_URL設定={bool(discord_url)}")
        
        # Discord notifierをインポート
        sys.path.append('/Users/moriwakikeita/tools/long-trader')
        from discord_notifier import discord_notifier
        
        # Discord通知実行
        print(f"子プロセス {test_id}: Discord通知送信中...")
        result = discord_notifier.child_process_started(
            symbol=f"TEST_CHILD_{test_id}",
            strategy_name="ProcessPool_Test",
            timeframe="1h",
            execution_id=f"child_test_{test_id}"
        )
        
        print(f"子プロセス {test_id}: Discord通知結果={result}")
        
        # 少し待機
        time.sleep(1)
        
        # 完了通知
        result2 = discord_notifier.child_process_completed(
            symbol=f"TEST_CHILD_{test_id}",
            strategy_name="ProcessPool_Test",
            timeframe="1h",
            execution_id=f"child_test_{test_id}",
            success=True,
            execution_time=2.0
        )
        
        print(f"子プロセス {test_id}: Discord完了通知結果={result2}")
        
        return f"子プロセス {test_id}: Discord通知完了"
        
    except Exception as e:
        return f"子プロセス {test_id}: エラー - {e}"

def main():
    """ProcessPoolExecutorでDiscord通知をテスト"""
    print("🧪 ProcessPoolExecutor環境でのDiscord通知テスト開始")
    print("=" * 60)
    
    # メインプロセスでの環境変数確認
    discord_url = os.getenv('DISCORD_WEBHOOK_URL')
    print(f"メインプロセス: DISCORD_WEBHOOK_URL設定={bool(discord_url)}")
    if discord_url:
        print(f"URL: {discord_url[:50]}...")
    
    # ProcessPoolExecutorで子プロセステスト
    with ProcessPoolExecutor(max_workers=2) as executor:
        futures = []
        
        # 2つの子プロセスでテスト
        for i in range(2):
            future = executor.submit(child_process_discord_test, i+1)
            futures.append(future)
        
        # 結果を収集
        for i, future in enumerate(futures):
            try:
                result = future.result(timeout=30)
                print(f"結果 {i+1}: {result}")
            except Exception as e:
                print(f"結果 {i+1}: エラー - {e}")
    
    print("\n✅ ProcessPoolExecutorでのDiscord通知テスト完了")
    print("Discord チャンネルを確認してください:")
    print("  - TEST_CHILD_1 ProcessPool_Test - 1h の開始・完了通知")
    print("  - TEST_CHILD_2 ProcessPool_Test - 1h の開始・完了通知")

if __name__ == '__main__':
    main()