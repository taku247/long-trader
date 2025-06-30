#!/usr/bin/env python3
"""
Discord通知システム - 子プロセス可視化専用（シンプル版）
"""

import os
import requests
from datetime import datetime
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを明示的にロード（ProcessPoolExecutor対応）
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # フォールバック

class DiscordNotifier:
    """Discord Webhook通知クラス（シンプル版）"""
    
    def __init__(self):
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.enabled = bool(self.webhook_url)
    
    def _send_simple_message(self, message: str) -> bool:
        """シンプルなDiscord通知送信"""
        # 環境変数を毎回チェック（ProcessPoolExecutor対応）
        current_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if not current_webhook_url:
            skip_msg = f"Discord通知スキップ: DISCORD_WEBHOOK_URL未設定 - {message}"
            print(skip_msg)
            
            # ファイルログも出力
            try:
                with open('/tmp/discord_notifications.log', 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().isoformat()} - {skip_msg}\n")
            except Exception:
                pass
            
            return False
            
        try:
            payload = {"content": message}
            
            response = requests.post(
                current_webhook_url,
                json=payload,
                timeout=10
            )
            success = response.status_code == 204
            log_msg = f"Discord通知送信{'成功' if success else '失敗'}: {message}"
            print(log_msg)
            
            # ファイルログも出力（ProcessPoolExecutor対応）
            try:
                import logging
                logger = logging.getLogger('discord_notifier')
                logger.info(log_msg)
                
                # 追加: 一時ファイルにもログ出力
                with open('/tmp/discord_notifications.log', 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().isoformat()} - {log_msg}\n")
            except Exception:
                pass
            
            return success
            
        except Exception as e:
            print(f"Discord通知エラー: {e} - {message}")
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
            if error_msg == "既存分析のためスキップ":
                message = f"⏩ 子プロセススキップ: {symbol} {strategy_name} - {timeframe} (既存分析)"
            else:
                message = f"✅ 子プロセス完了: {symbol} {strategy_name} - {timeframe} ({execution_time:.0f}秒)"
        else:
            message = f"❌ 子プロセス失敗: {symbol} {strategy_name} - {timeframe} - {error_msg}"
        
        return self._send_simple_message(message)

# グローバルインスタンス
discord_notifier = DiscordNotifier()