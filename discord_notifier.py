#!/usr/bin/env python3
"""
Discord通知システム - 子プロセス可視化専用（シンプル版）
"""

import os
import requests
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class DiscordNotifier:
    """Discord Webhook通知クラス（シンプル版）"""
    
    def __init__(self):
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.enabled = bool(self.webhook_url)
    
    def _send_simple_message(self, message: str) -> bool:
        """シンプルなDiscord通知送信"""
        if not self.enabled:
            return False
            
        try:
            payload = {"content": message}
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            return response.status_code == 204
            
        except Exception as e:
            print(f"Discord通知エラー: {e}")
            return False
    
    def child_process_started(self, symbol: str, strategy_name: str, timeframe: str, 
                            execution_id: str):
        """子プロセス開始通知"""
        message = f"🔄 子プロセス開始: {symbol} {strategy_name} - {timeframe}"
        return self._send_simple_message(message)
    
    def child_process_completed(self, symbol: str, strategy_name: str, timeframe: str,
                              execution_id: str, success: bool, 
                              execution_time: float, error_msg: str = ""):
        """子プロセス完了通知"""
        if success:
            message = f"✅ 子プロセス完了: {symbol} {strategy_name} - {timeframe} ({execution_time:.0f}秒)"
        else:
            message = f"❌ 子プロセス失敗: {symbol} {strategy_name} - {timeframe} - {error_msg}"
        
        return self._send_simple_message(message)

# グローバルインスタンス
discord_notifier = DiscordNotifier()