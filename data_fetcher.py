"""
データ取得ユーティリティ

既存のohlcv_by_claude.pyの機能をプラグインシステム用にラップした
データ取得ユーティリティ。
"""

import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from hyperliquid.info import Info
from hyperliquid.utils import constants
import logging

# websocketのエラーログを抑制
logging.getLogger('websocket').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

class HyperliquidDataFetcher:
    """Hyperliquidからのデータ取得クラス"""
    
    def __init__(self):
        self.info = Info(constants.MAINNET_API_URL)
        
        # 時間足に応じた設定
        self.timeframe_config = {
            '1m': {'days': 7, 'annualize_factor': 60 * 24 * 365},
            '3m': {'days': 21, 'annualize_factor': 20 * 24 * 365},
            '5m': {'days': 30, 'annualize_factor': 288 * 365},
            '15m': {'days': 60, 'annualize_factor': 96 * 365},
            '30m': {'days': 90, 'annualize_factor': 48 * 365},
            '1h': {'days': 90, 'annualize_factor': 24 * 365}
        }
    
    def fetch_data(self, symbol: str, timeframe: str = "1h", limit: int = 1000) -> pd.DataFrame:
        """
        市場データを取得
        
        Args:
            symbol: 取引シンボル (例: 'HYPE', 'SOL', 'WIF')
            timeframe: 時間足 (例: '1h', '15m', '5m')
            limit: 取得するデータ数の上限
            
        Returns:
            pd.DataFrame: OHLCV データ
        """
        
        try:
            print(f"{symbol}の価格データを取得中...")
            print(f"時間足: {timeframe}, 制限: {limit}件")
            
            # 時間足設定の取得
            if timeframe not in self.timeframe_config:
                print(f"⚠️ サポートされていない時間足: {timeframe}")
                return pd.DataFrame()
            
            config = self.timeframe_config[timeframe]
            days_to_fetch = min(config['days'], limit // (24 * 60 // self._timeframe_to_minutes(timeframe)))
            
            # データ取得期間の計算
            now_ms = int(time.time() * 1000)
            one_day_ms = 24 * 60 * 60 * 1000
            start_ms = now_ms - days_to_fetch * one_day_ms
            
            csv_data = []
            
            for i in range(days_to_fetch):
                s = start_ms + i * one_day_ms
                e = s + one_day_ms
                
                try:
                    candles = self.info.candles_snapshot(symbol, timeframe, s, e)
                    
                    for c in candles:
                        row = {
                            "timestamp": datetime.utcfromtimestamp(c["t"] / 1000),
                            "open": float(c["o"]),
                            "high": float(c["h"]),
                            "low": float(c["l"]),
                            "close": float(c["c"]),
                            "volume": float(c["v"]),
                            "trades": int(c["n"]),
                        }
                        csv_data.append(row)
                    
                    # レート制限対策（適度な間隔）
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"日次データ取得エラー {i+1}/{days_to_fetch}: {e}")
                    continue
            
            # DataFrameに変換
            df = pd.DataFrame(csv_data)
            
            if df.empty:
                print(f"❌ {symbol}のデータを取得できませんでした")
                return pd.DataFrame()
            
            # timestamp をインデックスに設定
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # 重複削除
            df = df[~df.index.duplicated(keep='first')]
            
            # limitを適用
            if len(df) > limit:
                df = df.tail(limit)
            
            print(f"✅ {symbol}: {len(df)}件のデータを取得完了")
            return df
            
        except Exception as e:
            print(f"❌ {symbol}のデータ取得エラー: {e}")
            return pd.DataFrame()
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """時間足を分に変換"""
        timeframe_minutes = {
            '1m': 1,
            '3m': 3,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60
        }
        return timeframe_minutes.get(timeframe, 60)

# グローバル インスタンス
_data_fetcher = HyperliquidDataFetcher()

def fetch_data(symbol: str, timeframe: str = "1h", limit: int = 1000) -> pd.DataFrame:
    """
    データ取得のメイン関数（既存システムとの互換性用）
    
    Args:
        symbol: 取引シンボル
        timeframe: 時間足
        limit: データ数制限
        
    Returns:
        pd.DataFrame: OHLCV データ
    """
    return _data_fetcher.fetch_data(symbol, timeframe, limit)

def get_available_symbols() -> list:
    """利用可能なシンボル一覧を取得（簡易版）"""
    # よく使用される銘柄のリスト
    return [
        'BTC', 'ETH', 'SOL', 'HYPE', 'WIF', 'BONK', 'PEPE',
        'DOGE', 'SHIB', 'AVAX', 'MATIC', 'ADA', 'DOT', 'UNI'
    ]

# テスト実行
if __name__ == "__main__":
    # 簡単なテスト
    data = fetch_data("HYPE", "1h", 100)
    print(f"テスト結果: {len(data)}件のデータ")
    if not data.empty:
        print(data.head())
    else:
        print("データ取得に失敗")