#!/usr/bin/env python3
"""
取引所切り替えユーティリティ
フラグ1つで簡単に取引所を切り替え可能
"""

import json
import os
from typing import Dict, Any
from datetime import datetime

from hyperliquid_api_client import MultiExchangeAPIClient, ExchangeType


class ExchangeSwitcher:
    """取引所切り替え管理クラス"""
    
    def __init__(self, config_file: str = "exchange_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load config: {e}")
        
        # デフォルト設定
        return {
            "default_exchange": "hyperliquid",
            "exchanges": {
                "hyperliquid": {"enabled": True, "rate_limit_delay": 0.5},
                "gateio": {"enabled": True, "rate_limit_delay": 0.1, "futures_only": True}
            }
        }
    
    def _save_config(self):
        """設定ファイルを保存"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"✅ Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"❌ Failed to save config: {e}")
    
    def switch_to_hyperliquid(self):
        """Hyperliquidに切り替え"""
        self.config["default_exchange"] = "hyperliquid"
        self._save_config()
        print("🔥 Switched to Hyperliquid")
    
    def switch_to_gateio(self):
        """Gate.ioに切り替え"""
        self.config["default_exchange"] = "gateio"
        self._save_config()
        print("🌐 Switched to Gate.io")
    
    def get_current_exchange(self) -> str:
        """現在の取引所を取得"""
        return self.config.get("default_exchange", "hyperliquid")
    
    def create_client(self) -> MultiExchangeAPIClient:
        """現在の設定でAPIクライアントを作成"""
        return MultiExchangeAPIClient(config_file=self.config_file)
    
    def show_status(self):
        """現在の状態を表示"""
        current = self.get_current_exchange()
        print(f"📊 Current Exchange: {current.upper()}")
        
        for exchange, settings in self.config.get("exchanges", {}).items():
            status = "✅ Enabled" if settings.get("enabled", False) else "❌ Disabled"
            delay = settings.get("rate_limit_delay", "N/A")
            print(f"   {exchange.upper()}: {status} (Rate limit: {delay}s)")


def main():
    """CLI インターフェース"""
    import sys
    
    switcher = ExchangeSwitcher()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python exchange_switcher.py status")
        print("  python exchange_switcher.py hyperliquid")
        print("  python exchange_switcher.py gateio")
        print("  python exchange_switcher.py test")
        switcher.show_status()
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        switcher.show_status()
    
    elif command == "hyperliquid":
        switcher.switch_to_hyperliquid()
        switcher.show_status()
    
    elif command == "gateio":
        switcher.switch_to_gateio()
        switcher.show_status()
    
    elif command == "test":
        print("🧪 Testing current configuration...")
        import asyncio
        
        async def test_current_exchange():
            try:
                client = switcher.create_client()
                print(f"✅ Client created for: {client.get_current_exchange()}")
                
                # 簡単なテスト
                symbols = await client.get_available_symbols()
                print(f"✅ Available symbols: {len(symbols)}")
                print(f"   First 5: {symbols[:5]}")
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
        
        asyncio.run(test_current_exchange())
    
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    main()