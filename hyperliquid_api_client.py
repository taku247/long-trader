#!/usr/bin/env python3
"""
Hyperliquid API統合クライアント
ohlcv_by_claude.pyの実装を参考にした実際のAPI統合
"""

import asyncio
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from hyperliquid.info import Info
from hyperliquid.utils import constants

from real_time_system.utils.colored_log import get_colored_logger


class HyperliquidAPIClient:
    """Hyperliquid API統合クライアント"""
    
    # シンボル名マッピング: ユーザー入力 -> Hyperliquid Perpsシンボル
    SYMBOL_MAPPING = {
        'PEPE': 'kPEPE',  # PEPEはPerpsではkPEPEとして取引
        # 他のマッピングが必要な場合はここに追加
    }
    
    def __init__(self):
        self.logger = get_colored_logger(__name__)
        
        # Hyperliquid APIクライアント初期化
        self.info = Info(constants.MAINNET_API_URL)
        
        # websocketのエラーログを抑制
        logging.getLogger('websocket').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        # 時間足設定（ohlcv_by_claude.pyから移植）
        self.timeframe_config = {
            '1m': {'days': 7, 'annualize_factor': 60 * 24 * 365},
            '3m': {'days': 21, 'annualize_factor': 20 * 24 * 365},
            '5m': {'days': 30, 'annualize_factor': 288 * 365},
            '15m': {'days': 60, 'annualize_factor': 96 * 365},
            '30m': {'days': 90, 'annualize_factor': 48 * 365},
            '1h': {'days': 90, 'annualize_factor': 24 * 365}
        }
    
    def _get_hyperliquid_symbol(self, user_symbol: str) -> str:
        """ユーザー入力をHyperliquid Perpsの正しいシンボル名にマッピング"""
        return self.SYMBOL_MAPPING.get(user_symbol, user_symbol)
    
    async def get_available_symbols(self) -> List[str]:
        """取引可能な銘柄リストを取得"""
        try:
            self.logger.info("🔍 Fetching available symbols from Hyperliquid...")
            
            # メタ情報を取得
            meta = self.info.meta()
            universe = meta.get('universe', [])
            
            symbols = [asset['name'] for asset in universe if asset.get('tradable', False)]
            
            self.logger.success(f"✅ Found {len(symbols)} tradable symbols on Hyperliquid")
            return symbols
            
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch symbols: {e}")
            # フォールバック: 既知のシンボルを返す
            return [
                'BTC', 'ETH', 'SOL', 'AVAX', 'DOGE', 'LINK', 'UNI', 'AAVE', 'MKR',
                'CRV', 'LDO', 'MATIC', 'ARB', 'OP', 'ATOM', 'DOT', 'ADA', 'XRP',
                'APT', 'SUI', 'SEI', 'INJ', 'TIA', 'NEAR', 'FTM', 'LUNA', 'LUNC',
                'WLD', 'FET', 'AGIX', 'RNDR', 'OCEAN', 'TAO', 'AKT',
                'JTO', 'PYTH', 'JUP', 'DRIFT', 'RAY', 'ORCA', 'MNGO',
                'PEPE', 'WIF', 'BOME', 'WEN', 'SLERF', 'POPCAT', 'PONKE',
                'HYPE', 'TRUMP', 'PNUT', 'GOAT', 'MOODENG', 'CHILLGUY', 'AI16Z',
                'W', 'STRK', 'BLUR', 'IMX', 'LRC', 'ZK', 'METIS', 'MANTA',
                'ORDI', 'SATS', '1000SATS', 'RATS', 'SHIB', 'FLOKI', 'GALA'
            ]
    
    async def get_market_info(self, symbol: str) -> Dict:
        """銘柄の市場情報を取得"""
        try:
            self.logger.debug(f"📊 Fetching market info for {symbol}")
            
            # メタ情報取得
            meta = self.info.meta()
            universe = meta.get('universe', [])
            
            # 指定銘柄の情報を検索
            symbol_info = None
            for asset in universe:
                if asset.get('name') == symbol:
                    symbol_info = asset
                    break
            
            if not symbol_info:
                raise ValueError(f"Symbol {symbol} not found in universe")
            
            # 現在価格を取得
            all_mids = self.info.all_mids()
            current_price = float(all_mids.get(symbol, 0))
            
            # レバレッジ制限計算（maxLeverage から）
            max_leverage = symbol_info.get('maxLeverage', 10)
            
            return {
                'symbol': symbol,
                'is_active': symbol_info.get('tradable', False),
                'current_price': current_price,
                'leverage_limit': max_leverage,
                'min_size': float(symbol_info.get('szDecimals', 0.01)),
                'tick_size': float(symbol_info.get('pxDecimals', 0.01)),
                'funding_rate': 0.0,  # TODO: 資金調達率の取得
                'volume_24h': 0.0,    # TODO: 24時間出来高の取得
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get market info for {symbol}: {e}")
            raise
    
    async def get_ohlcv_data(self, symbol: str, timeframe: str, 
                           start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """
        OHLCVデータを取得
        ohlcv_by_claude.pyの実装を参考にした正確なデータ取得
        """
        try:
            # シンボルマッピングを適用
            hyperliquid_symbol = self._get_hyperliquid_symbol(symbol)
            if hyperliquid_symbol != symbol:
                self.logger.info(f"🔄 Mapping {symbol} -> {hyperliquid_symbol} for data fetch")
            
            self.logger.info(f"📈 Fetching OHLCV data for {hyperliquid_symbol} ({timeframe})")
            self.logger.info(f"   Period: {start_time} to {end_time}")
            
            # タイムスタンプをミリ秒に変換
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            csv_data = []
            one_day_ms = 24 * 60 * 60 * 1000
            
            # 日毎にデータを取得（ohlcv_by_claude.pyと同じ方式）
            current_ms = start_ms
            day_count = 0
            
            failed_days = 0
            total_days = int((end_ms - start_ms) / one_day_ms) + 1
            max_allowed_failures = max(1, int(total_days * 0.3))  # 30%まで失敗を許容、最低1日
            
            while current_ms < end_ms:
                day_start = current_ms
                day_end = min(current_ms + one_day_ms, end_ms)
                
                try:
                    self.logger.debug(f"   Fetching day {day_count + 1}: {datetime.fromtimestamp(day_start/1000)}")
                    
                    # Hyperliquid APIからキャンドルデータを取得（マッピング後のシンボル使用）
                    candles = self.info.candles_snapshot(hyperliquid_symbol, timeframe, day_start, day_end)
                    
                    if not candles:
                        self.logger.warning(f"⚠️ No data returned for day {day_count + 1}: '{hyperliquid_symbol}'")
                        failed_days += 1
                    else:
                        for candle in candles:
                            row = {
                                "timestamp": datetime.fromtimestamp(candle["t"] / 1000),
                                "open": float(candle["o"]),
                                "high": float(candle["h"]),
                                "low": float(candle["l"]),
                                "close": float(candle["c"]),
                                "volume": float(candle["v"]),
                                "trades": int(candle["n"]) if "n" in candle else 0,
                            }
                            csv_data.append(row)
                
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to fetch data for day {day_count + 1}: '{hyperliquid_symbol}' - {str(e)}")
                    failed_days += 1
                
                current_ms += one_day_ms
                day_count += 1
                
                # API制限を考慮した待機
                await asyncio.sleep(0.1)
            
            # 失敗日数が多すぎる場合はエラー
            if failed_days > max_allowed_failures:
                raise ValueError(f"Too many failed requests for {symbol} (mapped to {hyperliquid_symbol}): {failed_days}/{day_count} days failed (max allowed: {max_allowed_failures})")
            
            if failed_days > 0:
                self.logger.warning(f"⚠️ Data fetch completed with {failed_days} failed days out of {day_count} for {symbol}")
            
            if not csv_data:
                raise ValueError(f"No data retrieved for {symbol} (mapped to {hyperliquid_symbol})")
            
            # DataFrameに変換
            df = pd.DataFrame(csv_data)
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 重複削除
            df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
            
            self.logger.success(f"✅ ✅ Retrieved {len(df)} data points for {symbol}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch OHLCV data for {symbol}: {e}")
            raise
    
    async def get_ohlcv_data_with_period(self, symbol: str, timeframe: str, days: int = None) -> pd.DataFrame:
        """
        指定期間のOHLCVデータを取得
        ohlcv_by_claude.pyの時間足設定を使用
        """
        # デフォルトの期間設定
        if days is None:
            days = self.timeframe_config.get(timeframe, {}).get('days', 90)
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        return await self.get_ohlcv_data(symbol, timeframe, start_time, end_time)
    
    async def validate_symbol_real(self, symbol: str) -> Dict:
        """
        実際のAPI呼び出しによる銘柄バリデーション
        """
        try:
            self.logger.debug(f"🔍 Validating {symbol} with real API call")
            
            # 市場情報取得を試行
            market_info = await self.get_market_info(symbol)
            
            return {
                'valid': True,
                'status': 'valid',
                'reason': None,
                'market_info': market_info,
                'action': 'continue'
            }
            
        except ValueError as e:
            # 銘柄が見つからない場合
            return {
                'valid': False,
                'status': 'invalid',
                'reason': str(e),
                'market_info': None,
                'action': 'reject'
            }
        except Exception as e:
            # その他のAPIエラー
            return {
                'valid': False,
                'status': 'error',
                'reason': f"API error: {str(e)}",
                'market_info': None,
                'action': 'reject'
            }
    
    async def get_funding_rate(self, symbol: str) -> float:
        """資金調達率を取得"""
        try:
            # TODO: Hyperliquid APIから資金調達率取得の実装
            # 現在はサンプル実装
            return 0.0001  # 0.01%
            
        except Exception as e:
            self.logger.warning(f"Failed to get funding rate for {symbol}: {e}")
            return 0.0
    
    async def get_24h_stats(self, symbol: str) -> Dict:
        """24時間統計を取得"""
        try:
            # TODO: 24時間統計の実装
            # 現在はサンプル実装
            return {
                'volume_24h': 1000000.0,
                'high_24h': 100.0,
                'low_24h': 95.0,
                'change_24h': 2.5,
                'change_24h_percent': 2.63
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to get 24h stats for {symbol}: {e}")
            return {}
    
    def get_timeframe_config(self, timeframe: str) -> Dict:
        """時間足設定を取得"""
        return self.timeframe_config.get(timeframe, self.timeframe_config['1h'])
    
    def is_valid_timeframe(self, timeframe: str) -> bool:
        """有効な時間足かチェック"""
        return timeframe in self.timeframe_config


async def main():
    """テスト実行"""
    client = HyperliquidAPIClient()
    
    print("=== Hyperliquid API Client Test ===")
    
    try:
        # 1. 利用可能銘柄の取得
        print("\n1. Getting available symbols...")
        symbols = await client.get_available_symbols()
        print(f"Available symbols: {len(symbols)}")
        print(f"First 10: {symbols[:10]}")
        
        # 2. 特定銘柄の市場情報取得
        test_symbol = "HYPE"
        print(f"\n2. Getting market info for {test_symbol}...")
        market_info = await client.get_market_info(test_symbol)
        print(f"Market info: {market_info}")
        
        # 3. OHLCVデータ取得
        print(f"\n3. Getting OHLCV data for {test_symbol}...")
        ohlcv_data = await client.get_ohlcv_data_with_period(test_symbol, "1h", days=7)
        print(f"OHLCV data shape: {ohlcv_data.shape}")
        print(f"Latest data:")
        print(ohlcv_data.tail())
        
        # 4. 銘柄バリデーション
        print(f"\n4. Validating symbols...")
        for symbol in ["HYPE", "INVALID_SYMBOL"]:
            validation = await client.validate_symbol_real(symbol)
            print(f"{symbol}: {validation['status']} - {validation.get('reason', 'OK')}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())