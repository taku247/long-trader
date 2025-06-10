#!/usr/bin/env python3
"""
Hyperliquid銘柄バリデーションシステム
既存システムに影響を与えない段階的なバリデーション実装
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from real_time_system.utils.colored_log import get_colored_logger

# aiohttp は実際のAPI実装時に追加
# 現在はHTTP通信なしでサンプル実装


class ValidationContext(Enum):
    """バリデーションコンテキスト"""
    NEW_ADDITION = "new_addition"           # 新規追加時（厳格）
    EXISTING_MONITORING = "existing_monitoring"  # 既存監視（緩やか）
    SCHEDULED_TASK = "scheduled_task"       # 定期実行（段階的）
    MIGRATION = "migration"                 # マイグレーション（非破壊的）


@dataclass
class ValidationResult:
    """バリデーション結果"""
    symbol: str
    valid: bool
    status: str
    reason: Optional[str] = None
    market_info: Optional[Dict] = None
    action: str = "continue"  # continue, suspend, flag_for_review
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class SymbolError(Exception):
    """銘柄関連エラーの基底クラス"""
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.error_code = error_code or self.__class__.__name__


class InvalidSymbolError(SymbolError):
    """存在しない銘柄"""
    def __init__(self, message: str):
        super().__init__(message, "INVALID_SYMBOL")


class InactiveSymbolError(SymbolError):
    """取引停止中の銘柄"""
    def __init__(self, message: str):
        super().__init__(message, "INACTIVE_SYMBOL")


class InsufficientDataError(SymbolError):
    """データ不足"""
    def __init__(self, message: str):
        super().__init__(message, "INSUFFICIENT_DATA")


class HyperliquidAPIError(SymbolError):
    """HyperliquidAPI接続エラー"""
    def __init__(self, message: str):
        super().__init__(message, "API_ERROR")


class HyperliquidValidator:
    """
    Hyperliquid固有の銘柄・取引制約バリデーター
    既存システムに影響を与えない段階的実装
    """
    
    # Hyperliquid Perpsで取引可能な主要銘柄（2025年6月時点）
    # 注意: Spot市場ではなくPerps（先物）市場のシンボル名
    KNOWN_VALID_SYMBOLS = {
        # メジャー銘柄
        'BTC', 'ETH', 'SOL', 'AVAX', 'DOGE', 'LINK', 'UNI', 'AAVE', 'MKR', 
        'CRV', 'LDO', 'MATIC', 'ARB', 'OP', 'ATOM', 'DOT', 'ADA', 'XRP',
        
        # Layer 1/Layer 2
        'APT', 'SUI', 'SEI', 'INJ', 'TIA', 'NEAR', 'FTM', 'LUNA', 'LUNC',
        
        # AI/Gaming
        'WLD', 'FET', 'AGIX', 'RNDR', 'OCEAN', 'TAO', 'AKT',
        
        # DeFi
        'JTO', 'PYTH', 'JUP', 'DRIFT', 'RAY', 'ORCA', 'MNGO',
        
        # Meme coins (Perpsでの正しいシンボル名)
        'kPEPE', 'WIF', 'BOME', 'WEN', 'SLERF', 'POPCAT', 'PONKE',
        
        # New tokens
        'HYPE',  # 特に重要
        'TRUMP', 'PNUT', 'GOAT', 'MOODENG', 'CHILLGUY', 'AI16Z',
        
        # Infrastructure
        'W', 'STRK', 'BLUR', 'IMX', 'LRC', 'ZK', 'METIS', 'MANTA',
        
        # Other popular
        'ORDI', 'SATS', '1000SATS', 'RATS', 'SHIB', 'FLOKI', 'GALA'
    }
    
    # シンボル名マッピング: ユーザー入力 -> Hyperliquid Perpsシンボル
    SYMBOL_MAPPING = {
        'PEPE': 'kPEPE',  # PEPEはPerpsではkPEPEとして取引
        # 他のマッピングが必要な場合はここに追加
    }
    
    # レバレッジ制限（概算）
    LEVERAGE_LIMITS = {
        'BTC': 50, 'ETH': 50, 'SOL': 20, 'AVAX': 20, 'DOGE': 20,
        'HYPE': 20, 'WIF': 10, 'PEPE': 10, 'BONK': 10,
        # デフォルト値
        'default': 10
    }
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.logger = get_colored_logger(__name__)
        # self.session: Optional[aiohttp.ClientSession] = None  # 実際のAPI実装時に有効化
        
        # キャッシュ
        self._market_info_cache = {}
        self._cache_expiry = {}
        self.cache_duration = timedelta(minutes=5)
        
        # エラー追跡
        self.consecutive_failures = {}
        self.blacklisted_symbols: Set[str] = set()
        
        # 設定
        self.config = self._load_validation_config()
    
    def _load_validation_config(self) -> Dict:
        """バリデーション設定の読み込み"""
        default_config = {
            'enable_strict_validation': {
                'new_symbol_addition': True,      # 新規追加時のみ厳格
                'existing_monitoring': False,     # 既存監視は現状維持
                'scheduled_tasks': False,         # 定期実行も現状維持
                'migration': True                 # マイグレーションは有効
            },
            'retry_attempts': 3,
            'api_timeout': 10,
            'min_data_points': 1000,
            'max_consecutive_failures': 3
        }
        
        try:
            # config.json から読み込み（あれば）
            with open('hyperliquid_validation_config.json', 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except FileNotFoundError:
            # デフォルト設定を保存
            with open('hyperliquid_validation_config.json', 'w') as f:
                json.dump(default_config, f, indent=2)
        
        return default_config
    
    async def __aenter__(self):
        """非同期コンテキストマネージャー"""
        # self.session = aiohttp.ClientSession()  # 実際のAPI実装時に有効化
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """セッションクリーンアップ"""
        # if self.session:  # 実際のAPI実装時に有効化
        #     await self.session.close()
        pass
    
    async def validate_symbol(self, symbol: str, 
                            context: ValidationContext = ValidationContext.NEW_ADDITION) -> ValidationResult:
        """
        コンテキストに応じた銘柄バリデーション
        
        Args:
            symbol: 銘柄名
            context: バリデーションコンテキスト
            
        Returns:
            ValidationResult: バリデーション結果
        """
        symbol = symbol.upper().strip()
        
        # コンテキストに応じた処理選択
        if context == ValidationContext.NEW_ADDITION:
            return await self._strict_validation(symbol)
        elif context == ValidationContext.EXISTING_MONITORING:
            return await self._lenient_validation(symbol)
        elif context == ValidationContext.SCHEDULED_TASK:
            return await self._graceful_validation(symbol)
        elif context == ValidationContext.MIGRATION:
            return await self._migration_validation(symbol)
        else:
            return await self._basic_validation(symbol)
    
    def _get_hyperliquid_symbol(self, user_symbol: str) -> str:
        """ユーザー入力をHyperliquid Perpsの正しいシンボル名にマッピング"""
        return self.SYMBOL_MAPPING.get(user_symbol, user_symbol)

    async def _strict_validation(self, symbol: str) -> ValidationResult:
        """新規追加時の厳格バリデーション"""
        self.logger.info(f"🔍 Strict validation for new symbol: {symbol}")
        
        try:
            # 1. 基本的な銘柄確認
            if not self._is_valid_symbol_format(symbol):
                raise InvalidSymbolError(f"Invalid symbol format: {symbol}")
            
            # 2. シンボルマッピングを適用
            hyperliquid_symbol = self._get_hyperliquid_symbol(symbol)
            if hyperliquid_symbol != symbol:
                self.logger.info(f"🔄 Mapping {symbol} -> {hyperliquid_symbol} for Hyperliquid Perps")
            
            # 3. 既知の有効銘柄チェック（マッピング後のシンボル）
            if hyperliquid_symbol not in self.KNOWN_VALID_SYMBOLS:
                self.logger.warning(f"⚠️ {hyperliquid_symbol} not in known valid symbols list")
            
            # 4. Hyperliquid API確認
            market_info = await self._fetch_market_info(hyperliquid_symbol)
            
            if not market_info.get('is_active', False):
                raise InactiveSymbolError(f"{hyperliquid_symbol} is not active on Hyperliquid")
            
            # 5. データ利用可能性確認
            data_availability = await self._check_data_availability(hyperliquid_symbol)
            if data_availability['available_points'] < self.config['min_data_points']:
                raise InsufficientDataError(
                    f"{hyperliquid_symbol}: Only {data_availability['available_points']} data points available "
                    f"(minimum: {self.config['min_data_points']})"
                )
            
            self.logger.success(f"✅ ✅ {symbol} passed strict validation")
            
            return ValidationResult(
                symbol=symbol,  # 元のシンボル名を返す
                valid=True,
                status="valid",
                market_info={**market_info, 'hyperliquid_symbol': hyperliquid_symbol},
                action="continue"
            )
            
        except (InvalidSymbolError, InactiveSymbolError, InsufficientDataError) as e:
            self.logger.error(f"❌ {symbol} failed strict validation: {e}")
            return ValidationResult(
                symbol=symbol,
                valid=False,
                status="invalid",
                reason=str(e),
                action="reject"
            )
        except Exception as e:
            self.logger.error(f"🔥 Unexpected error validating {symbol}: {e}")
            return ValidationResult(
                symbol=symbol,
                valid=False,
                status="error",
                reason=f"Validation error: {str(e)}",
                action="reject"
            )
    
    async def _lenient_validation(self, symbol: str) -> ValidationResult:
        """既存監視の緩やかバリデーション"""
        self.logger.debug(f"🔄 Lenient validation for existing symbol: {symbol}")
        
        try:
            # 基本的な確認のみ
            if symbol in self.blacklisted_symbols:
                return ValidationResult(
                    symbol=symbol,
                    valid=False,
                    status="blacklisted",
                    reason="Symbol is blacklisted",
                    action="suspend"
                )
            
            # 軽量な市場情報確認
            market_info = await self._fetch_market_info_cached(symbol)
            
            if market_info and not market_info.get('is_active', True):
                self.logger.warning(f"⚠️ {symbol} appears to be inactive")
                return ValidationResult(
                    symbol=symbol,
                    valid=True,  # 既存は継続
                    status="warning",
                    reason="Symbol may be inactive",
                    action="continue",
                    warnings=["Symbol may be inactive on Hyperliquid"]
                )
            
            return ValidationResult(
                symbol=symbol,
                valid=True,
                status="ok",
                market_info=market_info,
                action="continue"
            )
            
        except Exception as e:
            self.logger.warning(f"🔄 {symbol}: Validation issue (continuing): {e}")
            return ValidationResult(
                symbol=symbol,
                valid=True,  # エラーでも既存は継続
                status="warning",
                reason=f"Validation error: {str(e)}",
                action="continue",
                warnings=[f"Validation error: {str(e)}"]
            )
    
    async def _graceful_validation(self, symbol: str) -> ValidationResult:
        """定期実行の段階的バリデーション"""
        self.logger.debug(f"⏰ Graceful validation for scheduled task: {symbol}")
        
        # 連続失敗回数をチェック
        failure_count = self.consecutive_failures.get(symbol, 0)
        
        if failure_count >= self.config['max_consecutive_failures']:
            self.logger.warning(f"⏸️ {symbol}: Too many failures, temporary suspension")
            return ValidationResult(
                symbol=symbol,
                valid=False,
                status="suspended",
                reason=f"Too many consecutive failures ({failure_count})",
                action="suspend"
            )
        
        try:
            # 基本的な市場確認
            market_info = await self._fetch_market_info_cached(symbol)
            
            if market_info and market_info.get('is_active', True):
                # 成功したら失敗カウントリセット
                if symbol in self.consecutive_failures:
                    del self.consecutive_failures[symbol]
                
                return ValidationResult(
                    symbol=symbol,
                    valid=True,
                    status="ok",
                    market_info=market_info,
                    action="continue"
                )
            else:
                # 失敗カウント増加
                self.consecutive_failures[symbol] = failure_count + 1
                
                return ValidationResult(
                    symbol=symbol,
                    valid=True,  # まだ継続
                    status="warning",
                    reason="Market info unavailable",
                    action="continue",
                    warnings=["Market information unavailable"]
                )
                
        except Exception as e:
            # 失敗カウント増加
            self.consecutive_failures[symbol] = failure_count + 1
            
            self.logger.warning(f"⚠️ {symbol}: Validation issue (attempt {failure_count + 1}): {e}")
            
            return ValidationResult(
                symbol=symbol,
                valid=True,  # しばらくは継続
                status="warning",
                reason=str(e),
                action="continue",
                warnings=[f"Validation issue: {str(e)}"]
            )
    
    async def _migration_validation(self, symbol: str) -> ValidationResult:
        """マイグレーション用の非破壊的バリデーション"""
        self.logger.debug(f"🔄 Migration validation for: {symbol}")
        
        try:
            # 非破壊的な確認のみ
            basic_check = self._is_valid_symbol_format(symbol)
            known_symbol = symbol in self.KNOWN_VALID_SYMBOLS
            
            if not basic_check:
                return ValidationResult(
                    symbol=symbol,
                    valid=False,
                    status="format_invalid",
                    reason="Invalid symbol format",
                    action="flag_for_review"
                )
            
            if not known_symbol:
                return ValidationResult(
                    symbol=symbol,
                    valid=True,  # 継続はするが要確認
                    status="unknown",
                    reason="Not in known symbols list",
                    action="flag_for_review",
                    warnings=["Symbol not in known valid symbols"]
                )
            
            return ValidationResult(
                symbol=symbol,
                valid=True,
                status="ok",
                action="continue"
            )
            
        except Exception as e:
            return ValidationResult(
                symbol=symbol,
                valid=True,  # エラーでも継続
                status="error",
                reason=str(e),
                action="continue",
                warnings=[f"Migration check error: {str(e)}"]
            )
    
    async def _basic_validation(self, symbol: str) -> ValidationResult:
        """最低限のバリデーション"""
        if self._is_valid_symbol_format(symbol):
            return ValidationResult(
                symbol=symbol,
                valid=True,
                status="basic_ok",
                action="continue"
            )
        else:
            return ValidationResult(
                symbol=symbol,
                valid=False,
                status="format_invalid",
                reason="Invalid symbol format",
                action="reject"
            )
    
    def _is_valid_symbol_format(self, symbol: str) -> bool:
        """銘柄フォーマットの基本チェック"""
        if not symbol or not isinstance(symbol, str):
            return False
        
        symbol = symbol.strip().upper()
        
        # 基本的なフォーマットチェック
        if len(symbol) < 2 or len(symbol) > 10:
            return False
        
        if not symbol.isalnum():
            return False
        
        # 明らかに無効なパターン
        invalid_patterns = ['TEST', 'FAKE', 'INVALID', 'NULL', 'NONE']
        if symbol in invalid_patterns:
            return False
        
        return True
    
    async def _fetch_market_info(self, symbol: str) -> Dict:
        """Hyperliquid APIから市場情報を取得"""
        # TODO: 実際のHyperliquid API実装
        # 現在はサンプル実装
        
        await asyncio.sleep(0.1)  # API呼び出しをシミュレート
        
        if symbol in self.KNOWN_VALID_SYMBOLS:
            return {
                'symbol': symbol,
                'is_active': True,
                'leverage_limit': self.LEVERAGE_LIMITS.get(symbol, self.LEVERAGE_LIMITS['default']),
                'min_size': 0.01,
                'price': 100.0  # サンプル価格
            }
        else:
            raise InvalidSymbolError(f"{symbol} not found on Hyperliquid")
    
    async def _fetch_market_info_cached(self, symbol: str) -> Optional[Dict]:
        """キャッシュ付きの市場情報取得"""
        now = datetime.now()
        
        # キャッシュチェック
        if (symbol in self._market_info_cache and 
            symbol in self._cache_expiry and 
            now < self._cache_expiry[symbol]):
            return self._market_info_cache[symbol]
        
        try:
            market_info = await self._fetch_market_info(symbol)
            
            # キャッシュに保存
            self._market_info_cache[symbol] = market_info
            self._cache_expiry[symbol] = now + self.cache_duration
            
            return market_info
        except Exception:
            # エラー時はキャッシュされた古い情報を返す（あれば）
            return self._market_info_cache.get(symbol)
    
    async def _check_data_availability(self, symbol: str) -> Dict:
        """データ利用可能性の確認"""
        # TODO: 実際のデータ確認実装
        # 現在はサンプル実装
        
        await asyncio.sleep(0.1)
        
        if symbol in self.KNOWN_VALID_SYMBOLS:
            return {
                'available_points': 5000,
                'earliest_date': '2023-01-01',
                'latest_date': '2024-01-10'
            }
        else:
            return {
                'available_points': 0,
                'earliest_date': None,
                'latest_date': None
            }
    
    def get_leverage_limit(self, symbol: str) -> int:
        """銘柄のレバレッジ制限を取得"""
        return self.LEVERAGE_LIMITS.get(symbol, self.LEVERAGE_LIMITS['default'])
    
    def is_blacklisted(self, symbol: str) -> bool:
        """銘柄がブラックリストに登録されているかチェック"""
        return symbol in self.blacklisted_symbols
    
    def add_to_blacklist(self, symbol: str, reason: str = None):
        """銘柄をブラックリストに追加"""
        self.blacklisted_symbols.add(symbol)
        self.logger.warning(f"🚫 Added {symbol} to blacklist: {reason or 'No reason provided'}")
    
    def remove_from_blacklist(self, symbol: str):
        """銘柄をブラックリストから削除"""
        self.blacklisted_symbols.discard(symbol)
        self.logger.info(f"✅ Removed {symbol} from blacklist")


# 使用例とテスト
async def main():
    """テスト実行"""
    async with HyperliquidValidator() as validator:
        
        # 新規追加時のテスト
        print("=== 新規追加時のバリデーション ===")
        result = await validator.validate_symbol("HYPE", ValidationContext.NEW_ADDITION)
        print(f"HYPE: {result.status} - {result.reason}")
        
        result = await validator.validate_symbol("INVALID", ValidationContext.NEW_ADDITION)
        print(f"INVALID: {result.status} - {result.reason}")
        
        # 既存監視のテスト
        print("\n=== 既存監視のバリデーション ===")
        result = await validator.validate_symbol("SOL", ValidationContext.EXISTING_MONITORING)
        print(f"SOL: {result.status} - {result.action}")
        
        # マイグレーションテスト
        print("\n=== マイグレーションバリデーション ===")
        result = await validator.validate_symbol("BTC", ValidationContext.MIGRATION)
        print(f"BTC: {result.status} - {result.action}")


if __name__ == "__main__":
    asyncio.run(main())