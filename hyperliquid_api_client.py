#!/usr/bin/env python3
"""
マルチ取引所API統合クライアント
Hyperliquid および Gate.io 先物のOHLCV取得をサポート
フラグ1つで取引所を切り替え可能
"""

import asyncio
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union
import logging
import json
import os
from enum import Enum

# Hyperliquid
try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
    HYPERLIQUID_AVAILABLE = True
except ImportError:
    HYPERLIQUID_AVAILABLE = False
    print("⚠️ Hyperliquid library not available")

# CCXT for Gate.io
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    print("⚠️ CCXT library not available. Install with: pip install ccxt")

from real_time_system.utils.colored_log import get_colored_logger


class ExchangeType(Enum):
    """サポートされている取引所"""
    HYPERLIQUID = "hyperliquid"
    GATEIO = "gateio"


class MultiExchangeAPIClient:
    """
    マルチ取引所API統合クライアント（旧HyperliquidAPIClient）
    
    重要: 取引所の切り替えはユーザーが明示的に指定した場合のみ実行されます。
    エラーが発生しても自動的な切り替えは行われません。
    """
    
    # シンボル名マッピング
    HYPERLIQUID_SYMBOL_MAPPING = {
        'PEPE': 'kPEPE',  # PEPEはPerpsではkPEPEとして取引
        # 他のマッピングが必要な場合はここに追加
    }
    
    GATEIO_SYMBOL_MAPPING = {
        'PEPE': 'PEPE',  # Gate.ioでは通常通り
        'kPEPE': 'PEPE',  # 逆マッピング
        # Gate.io固有のマッピングが必要な場合はここに追加
    }
    
    def __init__(self, exchange_type: Union[str, ExchangeType] = None, config_file: str = None):
        self.logger = get_colored_logger(__name__)
        
        # 設定ファイルから取引所タイプを読み込み
        self.exchange_type = self._load_exchange_config(exchange_type, config_file)
        
        # 各取引所のクライアント初期化
        self.hyperliquid_client = None
        self.gateio_client = None
        
        # 使用する取引所に応じてクライアントを初期化
        if self.exchange_type == ExchangeType.HYPERLIQUID:
            self._init_hyperliquid()
        elif self.exchange_type == ExchangeType.GATEIO:
            self._init_gateio()
        else:
            # デフォルトではHyperliquidを使用
            self.exchange_type = ExchangeType.HYPERLIQUID
            self._init_hyperliquid()
        
        # 時間足設定（ohlcv_by_claude.pyから移植）
        self.timeframe_config = {
            '1m': {'days': 7, 'annualize_factor': 60 * 24 * 365},
            '3m': {'days': 21, 'annualize_factor': 20 * 24 * 365},
            '5m': {'days': 30, 'annualize_factor': 288 * 365},
            '15m': {'days': 60, 'annualize_factor': 96 * 365},
            '30m': {'days': 90, 'annualize_factor': 48 * 365},
            '1h': {'days': 90, 'annualize_factor': 24 * 365}
        }
        
        self.logger.info(f"🔄 Multi-Exchange API Client initialized with: {self.exchange_type.value}")
    
    def _load_exchange_config(self, exchange_type: Union[str, ExchangeType] = None, 
                            config_file: str = None) -> ExchangeType:
        """取引所設定を読み込み"""
        
        # 1. 引数で直接指定された場合
        if exchange_type:
            if isinstance(exchange_type, str):
                try:
                    return ExchangeType(exchange_type.lower())
                except ValueError:
                    self.logger.warning(f"⚠️ Unknown exchange type: {exchange_type}, using default")
            elif isinstance(exchange_type, ExchangeType):
                return exchange_type
        
        # 2. 設定ファイルから読み込み
        config_path = config_file or 'exchange_config.json'
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    exchange_name = config.get('default_exchange', 'hyperliquid')
                    return ExchangeType(exchange_name.lower())
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to load config from {config_path}: {e}")
        
        # 3. 環境変数から読み込み
        env_exchange = os.getenv('EXCHANGE_TYPE', '').lower()
        if env_exchange:
            try:
                return ExchangeType(env_exchange)
            except ValueError:
                pass
        
        # 4. デフォルト: Hyperliquid
        return ExchangeType.HYPERLIQUID
    
    def _init_hyperliquid(self):
        """Hyperliquid APIクライアント初期化"""
        if not HYPERLIQUID_AVAILABLE:
            raise ImportError("Hyperliquid library not available. Please install hyperliquid-python-sdk")
        
        try:
            self.hyperliquid_client = Info(constants.MAINNET_API_URL)
            
            # websocketのエラーログを抑制
            logging.getLogger('websocket').setLevel(logging.WARNING)
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            
            self.logger.success("✅ Hyperliquid client initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Hyperliquid client: {e}")
            raise
    
    def _init_gateio(self):
        """Gate.io CCXTクライアント初期化"""
        if not CCXT_AVAILABLE:
            raise ImportError("CCXT library not available. Please install ccxt")
        
        try:
            self.gateio_client = ccxt.gateio({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future'  # 先物取引を指定
                },
                'timeout': 30000,  # 30秒タイムアウト
                'sandbox': False   # 本番環境
            })
            
            self.logger.success("✅ Gate.io client initialized (futures)")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Gate.io client: {e}")
            raise
    
    def _get_exchange_symbol(self, user_symbol: str) -> str:
        """ユーザー入力を各取引所の正しいシンボル名にマッピング"""
        if self.exchange_type == ExchangeType.HYPERLIQUID:
            return self.HYPERLIQUID_SYMBOL_MAPPING.get(user_symbol, user_symbol)
        elif self.exchange_type == ExchangeType.GATEIO:
            # Gate.ioでは先物のシンボル形式に変換（例: BTC -> BTC/USDT:USDT）
            gateio_symbol = self.GATEIO_SYMBOL_MAPPING.get(user_symbol, user_symbol)
            return f"{gateio_symbol}/USDT:USDT"
        else:
            return user_symbol
    
    def _normalize_timeframe(self, timeframe: str) -> str:
        """時間足を各取引所の形式に正規化"""
        if self.exchange_type == ExchangeType.GATEIO:
            # Gate.io/CCXTの時間足形式に変換
            timeframe_mapping = {
                '1m': '1m',
                '3m': '3m', 
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '4h': '4h',
                '1d': '1d'
            }
            return timeframe_mapping.get(timeframe, timeframe)
        else:
            # Hyperliquidはそのまま
            return timeframe
    
    def switch_exchange(self, exchange_type: Union[str, ExchangeType]):
        """
        明示的に取引所を切り替え
        
        注意: この切り替えはユーザーが明示的に呼び出した場合のみ実行されます。
        システムが自動的に切り替えを行うことはありません。
        """
        if isinstance(exchange_type, str):
            exchange_type = ExchangeType(exchange_type.lower())
        
        if exchange_type == self.exchange_type:
            self.logger.info(f"🔄 Already using {exchange_type.value}")
            return
        
        self.logger.info(f"🔄 User-requested switch from {self.exchange_type.value} to {exchange_type.value}")
        
        self.exchange_type = exchange_type
        
        if exchange_type == ExchangeType.HYPERLIQUID:
            self._init_hyperliquid()
        elif exchange_type == ExchangeType.GATEIO:
            self._init_gateio()
        
        self.logger.success(f"✅ Switched to {exchange_type.value} (user-requested)")
    
    def get_current_exchange(self) -> str:
        """現在の取引所を取得"""
        return self.exchange_type.value
    
    async def get_available_symbols(self) -> List[str]:
        """取引可能な銘柄リストを取得"""
        try:
            if self.exchange_type == ExchangeType.HYPERLIQUID:
                return await self._get_hyperliquid_symbols()
            elif self.exchange_type == ExchangeType.GATEIO:
                return await self._get_gateio_symbols()
            else:
                raise ValueError(f"Unsupported exchange type: {self.exchange_type}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch symbols from {self.exchange_type.value}: {e}")
            # フォールバック: 既知のシンボルを返す
            return self._get_fallback_symbols()
    
    async def _get_hyperliquid_symbols(self) -> List[str]:
        """Hyperliquidの取引可能銘柄を取得"""
        self.logger.info("🔍 Fetching available symbols from Hyperliquid...")
        
        # メタ情報を取得
        meta = self.hyperliquid_client.meta()
        universe = meta.get('universe', [])
        
        symbols = [asset['name'] for asset in universe if asset.get('tradable', False)]
        
        self.logger.success(f"✅ Found {len(symbols)} tradable symbols on Hyperliquid")
        return symbols
    
    async def _get_gateio_symbols(self) -> List[str]:
        """Gate.io先物の取引可能銘柄を取得"""
        self.logger.info("🔍 Fetching available symbols from Gate.io futures...")
        
        # Gate.io先物マーケットを取得
        markets = await asyncio.get_event_loop().run_in_executor(
            None, self.gateio_client.load_markets
        )
        
        # USDT先物のシンボルのみを抽出
        symbols = []
        for symbol, market in markets.items():
            if (market.get('type') == 'future' and 
                market.get('quote') == 'USDT' and 
                market.get('active', False)):
                # _USDTを除いたベースシンボルを追加
                base_symbol = market.get('base', symbol.split('_')[0])
                if base_symbol not in symbols:
                    symbols.append(base_symbol)
        
        self.logger.success(f"✅ Found {len(symbols)} tradable symbols on Gate.io futures")
        return sorted(symbols)
    
    def _get_fallback_symbols(self) -> List[str]:
        """フォールバック用の既知シンボルリスト"""
        return [
            'BTC', 'ETH', 'SOL', 'AVAX', 'DOGE', 'LINK', 'UNI', 'AAVE', 'MKR',
            'CRV', 'LDO', 'MATIC', 'ARB', 'OP', 'ATOM', 'DOT', 'ADA', 'XRP',
            'APT', 'SUI', 'SEI', 'INJ', 'TIA', 'NEAR', 'FTM', 'LUNA', 'LUNC',
            'WLD', 'FET', 'AGIX', 'RNDR', 'OCEAN', 'TAO', 'AKT',
            'JTO', 'PYTH', 'JUP', 'DRIFT', 'RAY', 'ORCA', 'MNGO',
            'PEPE', 'WIF', 'BOME', 'WEN', 'SLERF', 'POPCAT', 'PONKE', 'FARTCOIN',
            'HYPE', 'TRUMP', 'PNUT', 'GOAT', 'MOODENG', 'CHILLGUY', 'AI16Z',
            'W', 'STRK', 'BLUR', 'IMX', 'LRC', 'ZK', 'METIS', 'MANTA',
            'ORDI', 'SATS', '1000SATS', 'RATS', 'SHIB', 'FLOKI', 'GALA',
            'SPX'  # S&P 500インデックス関連
        ]
    
    async def get_market_info(self, symbol: str) -> Dict:
        """銘柄の市場情報を取得"""
        try:
            self.logger.debug(f"📊 Fetching market info for {symbol}")
            
            if self.exchange_type == ExchangeType.HYPERLIQUID:
                return await self._get_hyperliquid_market_info(symbol)
            elif self.exchange_type == ExchangeType.GATEIO:
                return await self._get_gateio_market_info(symbol)
            else:
                raise ValueError(f"Unsupported exchange type: {self.exchange_type}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get market info for {symbol}: {e}")
            raise
    
    async def _get_hyperliquid_market_info(self, symbol: str) -> Dict:
        """Hyperliquid市場情報を取得"""
        try:
            # メタ情報取得
            meta = self.hyperliquid_client.meta()
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
            all_mids = self.hyperliquid_client.all_mids()
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
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"❌ Failed to get Hyperliquid market info for {symbol}: {e}")
            raise
    
    async def _get_gateio_market_info(self, symbol: str) -> Dict:
        """Gate.io市場情報を取得"""
        try:
            # Gate.io futures symbol format is SYMBOL/USDT:USDT
            gateio_symbol = f"{symbol}/USDT:USDT"
            
            # 市場情報を取得
            markets = self.gateio_client.load_markets()
            
            if gateio_symbol not in markets:
                # Try alternative formats
                alt_formats = [f"{symbol}/USDT", f"{symbol}_USDT"]
                found_symbol = None
                for alt_format in alt_formats:
                    if alt_format in markets:
                        found_symbol = alt_format
                        break
                
                if not found_symbol:
                    raise ValueError(f"Symbol {symbol} not found in Gate.io markets (tried {gateio_symbol}, {alt_formats})")
                
                gateio_symbol = found_symbol
            
            market_info = markets[gateio_symbol]
            ticker = self.gateio_client.fetch_ticker(gateio_symbol)
            
            return {
                'symbol': symbol,
                'is_active': market_info.get('active', False),
                'current_price': float(ticker.get('last', 0)),
                'leverage_limit': float(market_info.get('limits', {}).get('leverage', {}).get('max', 10)),
                'min_size': float(market_info.get('limits', {}).get('amount', {}).get('min', 0.01)),
                'tick_size': float(market_info.get('precision', {}).get('price', 0.01)),
                'funding_rate': 0.0,  # TODO: 資金調達率の取得
                'volume_24h': float(ticker.get('baseVolume', 0)),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"❌ Failed to get Gate.io market info for {symbol}: {e}")
            raise
    
    async def get_ohlcv_data(self, symbol: str, timeframe: str, 
                           start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """
        統合OHLCVデータ取得メソッド
        現在の取引所設定に応じて適切なAPIを使用
        """
        try:
            if self.exchange_type == ExchangeType.HYPERLIQUID:
                return await self._get_hyperliquid_ohlcv(symbol, timeframe, start_time, end_time)
            elif self.exchange_type == ExchangeType.GATEIO:
                return await self._get_gateio_ohlcv(symbol, timeframe, start_time, end_time)
            else:
                raise ValueError(f"Unsupported exchange type: {self.exchange_type}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch OHLCV data for {symbol} from {self.exchange_type.value}: {e}")
            raise
    
    async def _get_hyperliquid_ohlcv(self, symbol: str, timeframe: str, 
                                   start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """
        Hyperliquid APIからOHLCVデータを取得
        ohlcv_by_claude.pyの実装を参考にした正確なデータ取得
        """
        # シンボルマッピングを適用
        hyperliquid_symbol = self._get_exchange_symbol(symbol)
        if hyperliquid_symbol != symbol:
            self.logger.info(f"🔄 Mapping {symbol} -> {hyperliquid_symbol} for Hyperliquid")
        
        # 期間情報を詳細に計算
        period_days = (end_time - start_time).days
        self.logger.info(f"📈 🔥 HYPERLIQUID OHLCV FETCH START 🔥 Symbol: {hyperliquid_symbol} | Timeframe: {timeframe} | Period: {period_days}日間")
        self.logger.info(f"   📅 Range: {start_time.strftime('%Y-%m-%d %H:%M')} → {end_time.strftime('%Y-%m-%d %H:%M')}")
        
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
                self.logger.debug(f"   Fetching day {day_count + 1}: {datetime.fromtimestamp(day_start/1000, tz=timezone.utc)}")
                
                # Hyperliquid APIからキャンドルデータを取得（マッピング後のシンボル使用）
                candles = self.hyperliquid_client.candles_snapshot(hyperliquid_symbol, timeframe, day_start, day_end)
                
                if not candles:
                    self.logger.warning(f"⚠️ No data returned for day {day_count + 1}: '{hyperliquid_symbol}'")
                    failed_days += 1
                else:
                    for candle in candles:
                        row = {
                            "timestamp": datetime.fromtimestamp(candle["t"] / 1000, tz=timezone.utc),
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
            
            # API制限を考慮した待機（適度な間隔）
            await asyncio.sleep(0.5)  # Gate.io比較で少し控えめ
        
        # 失敗日数が多すぎる場合はエラー
        if failed_days > max_allowed_failures:
            raise ValueError(f"Too many failed requests for {symbol} (mapped to {hyperliquid_symbol}): {failed_days}/{day_count} days failed (max allowed: {max_allowed_failures})")
        
        if failed_days > 0:
            self.logger.warning(f"⚠️ Hyperliquid data fetch completed with {failed_days} failed days out of {day_count} for {symbol}")
        
        if not csv_data:
            raise ValueError(f"No data retrieved for {symbol} (mapped to {hyperliquid_symbol})")
        
        # DataFrameに変換
        df = pd.DataFrame(csv_data)
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 重複削除
        df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
        
        self.logger.success(f"✅ 🔥 HYPERLIQUID OHLCV COMPLETE 🔥 Symbol: {symbol} | Timeframe: {timeframe} | Points: {len(df)} | Success Rate: {((total_days-failed_days)/total_days*100):.1f}%")
        
        return df
    
    async def _get_gateio_ohlcv(self, symbol: str, timeframe: str, 
                              start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """
        Gate.io APIからOHLCVデータを取得（ccxt使用）
        """
        # シンボルマッピングを適用
        gateio_symbol = self._get_exchange_symbol(symbol)
        normalized_timeframe = self._normalize_timeframe(timeframe)
        
        if gateio_symbol != symbol:
            self.logger.info(f"🔄 Mapping {symbol} -> {gateio_symbol} for Gate.io")
        
        # 期間情報を詳細に計算
        period_days = (end_time - start_time).days
        self.logger.info(f"📈 🔥 GATE.IO OHLCV FETCH START 🔥 Symbol: {gateio_symbol} | Timeframe: {normalized_timeframe} | Period: {period_days}日間")
        self.logger.info(f"   📅 Range: {start_time.strftime('%Y-%m-%d %H:%M')} → {end_time.strftime('%Y-%m-%d %H:%M')}")
        
        try:
            # CCXTを使ってOHLCVデータを取得
            since = int(start_time.timestamp() * 1000)
            
            all_ohlcv = []
            current_since = since
            end_timestamp = int(end_time.timestamp() * 1000)
            
            # 1回のリクエストで1000本取得、必要に応じて複数回リクエスト
            while current_since < end_timestamp:
                self.logger.debug(f"   Fetching OHLCV from {datetime.fromtimestamp(current_since/1000, tz=timezone.utc)}")
                
                # 非同期でOHLCVデータを取得
                ohlcv = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.gateio_client.fetch_ohlcv(
                        gateio_symbol, 
                        normalized_timeframe, 
                        since=current_since,
                        limit=1000
                    )
                )
                
                if not ohlcv:
                    # 最新データが存在しない場合は警告を出すが継続（取引所の最新データがまだ生成されていない可能性）
                    if current_since >= end_timestamp - (1000 * 60 * 60):  # 最後の1時間以内
                        self.logger.debug(f"No data for {gateio_symbol} at {datetime.fromtimestamp(current_since/1000, tz=timezone.utc)} (might be too recent)")
                    else:
                        self.logger.warning(f"⚠️ No data returned for {gateio_symbol} from {datetime.fromtimestamp(current_since/1000, tz=timezone.utc)}")
                    break
                
                all_ohlcv.extend(ohlcv)
                
                # 最後のタイムスタンプを更新
                last_timestamp = ohlcv[-1][0]
                if last_timestamp <= current_since:
                    # タイムスタンプが進まない場合は終了
                    break
                current_since = last_timestamp + 1
                
                # レート制限を考慮
                await asyncio.sleep(0.1)  # Gate.ioのレート制限に配慮
            
            if not all_ohlcv:
                raise ValueError(f"No data retrieved for {symbol} (mapped to {gateio_symbol})")
            
            # DataFrameに変換
            df = pd.DataFrame(all_ohlcv, columns=['timestamp_ms', 'open', 'high', 'low', 'close', 'volume'])
            
            # タイムスタンプをdatetimeに変換（UTC aware）
            df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True)
            
            # 不要な列を削除
            df = df.drop('timestamp_ms', axis=1)
            
            # 指定期間でフィルタリング
            # start_timeとend_timeがtimezone-naiveの場合はUTCに変換してから比較
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            
            df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
            
            # 型変換
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # Hyperliquidとの互換性のためtrades列を追加（Gate.ioでは利用不可）
            df['trades'] = 0
            
            # ソートと重複削除
            df = df.sort_values('timestamp').reset_index(drop=True)
            df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
            
            self.logger.success(f"✅ 🔥 GATE.IO OHLCV COMPLETE 🔥 Symbol: {symbol} | Timeframe: {timeframe} | Points: {len(df)}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Gate.io OHLCV fetch failed for {symbol}: {e}")
            raise
    
    async def get_ohlcv_data_with_period(self, symbol: str, timeframe: str, days: int = None) -> pd.DataFrame:
        """
        指定期間のOHLCVデータを取得
        ohlcv_by_claude.pyの時間足設定を使用
        """
        # デフォルトの期間設定
        if days is None:
            days = self.timeframe_config.get(timeframe, {}).get('days', 90)
        
        self.logger.info(f"🎯 OHLCV REQUEST: {symbol} {timeframe} for {days} days (timeframe config)")
        
        end_time = datetime.now(timezone.utc)
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


# 後方互換性のためのエイリアス
HyperliquidAPIClient = MultiExchangeAPIClient


async def create_exchange_config():
    """設定ファイルを作成"""
    config = {
        "default_exchange": "hyperliquid",  # hyperliquid or gateio
        "exchanges": {
            "hyperliquid": {
                "enabled": True,
                "rate_limit_delay": 0.5
            },
            "gateio": {
                "enabled": True,
                "rate_limit_delay": 0.1,
                "futures_only": True
            }
        }
    }
    
    with open('exchange_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ exchange_config.json created")


async def main():
    """テスト実行"""
    print("=== Multi-Exchange API Client Test ===")
    
    # 設定ファイル作成
    await create_exchange_config()
    
    # Hyperliquidでテスト
    print("\n🔥 Testing with Hyperliquid 🔥")
    try:
        hyperliquid_client = MultiExchangeAPIClient(exchange_type="hyperliquid")
        
        # 1. 利用可能銘柄の取得
        print("\n1. Getting available symbols from Hyperliquid...")
        symbols = await hyperliquid_client.get_available_symbols()
        print(f"Available symbols: {len(symbols)}")
        print(f"First 10: {symbols[:10]}")
        
        # 2. 特定銘柄の市場情報取得
        test_symbol = "HYPE"
        print(f"\n2. Getting market info for {test_symbol}...")
        market_info = await hyperliquid_client.get_market_info(test_symbol)
        print(f"Market info: {market_info}")
        
        # 3. OHLCVデータ取得
        print(f"\n3. Getting OHLCV data for {test_symbol}...")
        ohlcv_data = await hyperliquid_client.get_ohlcv_data_with_period(test_symbol, "1h", days=1)
        print(f"OHLCV data shape: {ohlcv_data.shape}")
        print(f"Latest data:")
        print(ohlcv_data.tail(3))
        
    except Exception as e:
        print(f"Hyperliquid Error: {e}")
    
    # Gate.ioでテスト
    print("\n\n🌐 Testing with Gate.io 🌐")
    try:
        gateio_client = MultiExchangeAPIClient(exchange_type="gateio")
        
        # 1. 利用可能銘柄の取得
        print("\n1. Getting available symbols from Gate.io...")
        symbols = await gateio_client.get_available_symbols()
        print(f"Available symbols: {len(symbols)}")
        print(f"First 10: {symbols[:10]}")
        
        # 2. OHLCVデータ取得
        test_symbol = "BTC"  # Gate.ioで確実に存在する銘柄
        print(f"\n2. Getting OHLCV data for {test_symbol}...")
        ohlcv_data = await gateio_client.get_ohlcv_data_with_period(test_symbol, "1h", days=1)
        print(f"OHLCV data shape: {ohlcv_data.shape}")
        print(f"Latest data:")
        print(ohlcv_data.tail(3))
        
    except Exception as e:
        print(f"Gate.io Error: {e}")
    
    # 動的切り替えテスト
    print("\n\n🔄 Testing Dynamic Exchange Switching 🔄")
    try:
        # Hyperliquidで開始
        client = MultiExchangeAPIClient(exchange_type="hyperliquid")
        print(f"Current exchange: {client.get_current_exchange()}")
        
        # Gate.ioに切り替え
        client.switch_exchange("gateio")
        print(f"After switch: {client.get_current_exchange()}")
        
        # 簡単なデータ取得テスト
        symbols = await client.get_available_symbols()
        print(f"Gate.io symbols count: {len(symbols)}")
        
    except Exception as e:
        print(f"Switch test error: {e}")


if __name__ == "__main__":
    asyncio.run(main())