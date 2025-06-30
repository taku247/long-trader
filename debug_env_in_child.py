#!/usr/bin/env python3
"""
子プロセス内での環境変数確認スクリプト
"""

import os
import sys
from pathlib import Path

def debug_child_process_env():
    """子プロセス内での環境変数を詳細に確認"""
    print("🔍 子プロセス環境変数デバッグ")
    print("=" * 50)
    
    # 1. 直接的な環境変数チェック
    discord_url = os.getenv('DISCORD_WEBHOOK_URL')
    print(f"1. os.getenv('DISCORD_WEBHOOK_URL'): {bool(discord_url)}")
    if discord_url:
        print(f"   URL: {discord_url[:50]}...")
    
    # 2. .envファイルの存在確認
    env_path = Path(__file__).parent / '.env'
    print(f"2. .envファイル存在: {env_path.exists()}")
    if env_path.exists():
        print(f"   パス: {env_path}")
        
        # .envファイルの内容確認
        try:
            with open(env_path, 'r') as f:
                content = f.read()
                has_discord = 'DISCORD_WEBHOOK_URL' in content
                print(f"   DISCORD_WEBHOOK_URL記載: {has_discord}")
        except Exception as e:
            print(f"   .env読み込みエラー: {e}")
    
    # 3. dotenvで読み込み後の確認
    try:
        from dotenv import load_dotenv
        print("3. dotenv読み込み試行...")
        
        # 明示的にパス指定で読み込み
        if env_path.exists():
            load_dotenv(env_path)
            discord_url_after = os.getenv('DISCORD_WEBHOOK_URL')
            print(f"   明示的読み込み後: {bool(discord_url_after)}")
            if discord_url_after:
                print(f"   URL: {discord_url_after[:50]}...")
        
        # フォールバック読み込み
        load_dotenv()
        discord_url_fallback = os.getenv('DISCORD_WEBHOOK_URL')
        print(f"   フォールバック読み込み後: {bool(discord_url_fallback)}")
        
    except ImportError:
        print("3. dotenvモジュールなし")
    except Exception as e:
        print(f"3. dotenv読み込みエラー: {e}")
    
    # 4. 実際のDiscord通知テスト
    try:
        sys.path.append('/Users/moriwakikeita/tools/long-trader')
        from discord_notifier import discord_notifier
        
        print("4. Discord通知テスト...")
        result = discord_notifier.child_process_started(
            symbol="ENV_DEBUG_TEST",
            strategy_name="Environment_Debug",
            timeframe="1h",
            execution_id="env_debug_001"
        )
        print(f"   通知結果: {result}")
        
    except Exception as e:
        print(f"4. Discord通知エラー: {e}")
    
    print("\n✅ 環境変数デバッグ完了")

if __name__ == '__main__':
    debug_child_process_env()