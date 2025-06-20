#!/usr/bin/env python3
"""
銘柄追加時のEarly Fail検証システム

マルチプロセス生成前に軽量な検証を行い、問題のある銘柄を即座に拒否する。
カスタマイズ可能な検証ルールを提供。
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from real_time_system.utils.colored_log import get_colored_logger


class FailReason(Enum):
    """Early Fail の理由"""
    INSUFFICIENT_HISTORICAL_DATA = "insufficient_historical_data"
    SYMBOL_NOT_FOUND = "symbol_not_found"
    EXCHANGE_NOT_SUPPORTED = "exchange_not_supported"
    API_CONNECTION_FAILED = "api_connection_failed"
    CUSTOM_RULE_VIOLATION = "custom_rule_violation"


@dataclass
class EarlyFailResult:
    """Early Fail検証結果"""
    symbol: str
    passed: bool
    fail_reason: Optional[FailReason] = None
    error_message: str = ""
    suggestion: str = ""
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SymbolEarlyFailValidator:
    """
    銘柄追加時のEarly Fail検証システム
    
    軽量で高速な検証を行い、重い処理を実行する前に問題を検出する。
    カスタマイズ可能な検証ルールをサポート。
    """
    
    def __init__(self, config_path: str = "early_fail_config.json"):
        self.logger = get_colored_logger(__name__)
        self.config_path = config_path
        self.custom_validators: List[Callable] = []
        self.load_config()
    
    def load_config(self):
        """設定ファイルから検証ルールを読み込み"""
        default_config = {
            "required_historical_days": 90,
            "min_data_points": 1000,
            "supported_exchanges": ["hyperliquid", "gateio"],
            "test_timeframes": ["1h"],
            "max_validation_time_seconds": 30,
            "enable_ohlcv_check": True,
            "enable_symbol_existence_check": True,
            "enable_exchange_support_check": True
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    self.logger.info(f"📋 Early Fail設定読み込み: {self.config_path}")
            else:
                # デフォルト設定ファイルを作成
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                self.logger.info(f"📝 Early Fail設定ファイル作成: {self.config_path}")
        except Exception as e:
            self.logger.warning(f"設定ファイル読み込みエラー: {e}")
        
        self.config = default_config
    
    def add_custom_validator(self, validator_func: Callable[[str], EarlyFailResult]):
        """カスタム検証ルールを追加"""
        self.custom_validators.append(validator_func)
        self.logger.info(f"カスタム検証ルール追加: {validator_func.__name__}")
    
    async def validate_symbol(self, symbol: str) -> EarlyFailResult:
        """
        銘柄のEarly Fail検証を実行
        
        Args:
            symbol: 検証する銘柄名
            
        Returns:
            EarlyFailResult: 検証結果
        """
        self.logger.info(f"🔍 Early Fail検証開始: {symbol}")
        
        try:
            # 1. 基本的なシンボル存在チェック
            if self.config.get("enable_symbol_existence_check", True):
                result = await self._check_symbol_existence(symbol)
                if not result.passed:
                    return result
            
            # 2. 取引所サポートチェック
            if self.config.get("enable_exchange_support_check", True):
                result = await self._check_exchange_support(symbol)
                if not result.passed:
                    return result
            
            # 3. OHLCV履歴データチェック
            if self.config.get("enable_ohlcv_check", True):
                result = await self._check_historical_data_availability(symbol)
                if not result.passed:
                    return result
            
            # 4. カスタム検証ルール実行
            for custom_validator in self.custom_validators:
                try:
                    result = custom_validator(symbol)
                    if not result.passed:
                        return result
                except Exception as e:
                    self.logger.warning(f"カスタム検証エラー: {custom_validator.__name__} - {e}")
            
            # 全ての検証をパス
            self.logger.success(f"✅ {symbol}: Early Fail検証合格")
            return EarlyFailResult(
                symbol=symbol,
                passed=True,
                metadata={"validation_time": datetime.now().isoformat()}
            )
            
        except Exception as e:
            self.logger.error(f"❌ {symbol}: Early Fail検証中にエラー - {e}")
            return EarlyFailResult(
                symbol=symbol,
                passed=False,
                fail_reason=FailReason.API_CONNECTION_FAILED,
                error_message=f"検証中にエラーが発生: {str(e)}",
                suggestion="しばらく時間をおいて再度お試しください"
            )
    
    async def _check_symbol_existence(self, symbol: str) -> EarlyFailResult:
        """シンボル存在チェック"""
        try:
            exchange = self._get_current_exchange()
            
            from hyperliquid_api_client import MultiExchangeAPIClient
            api_client = MultiExchangeAPIClient(exchange_type=exchange)
            
            # 市場情報取得を試行
            market_info = await api_client.get_market_info(symbol)
            
            return EarlyFailResult(
                symbol=symbol,
                passed=True,
                metadata={"market_info": market_info}
            )
            
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['not found', 'invalid', 'does not exist']):
                return EarlyFailResult(
                    symbol=symbol,
                    passed=False,
                    fail_reason=FailReason.SYMBOL_NOT_FOUND,
                    error_message=f"{symbol}は{self._get_current_exchange()}で取引されていません",
                    suggestion="銘柄名のスペルを確認するか、別の取引所で確認してください"
                )
            else:
                raise  # その他のエラーは上位に伝播
    
    async def _check_exchange_support(self, symbol: str) -> EarlyFailResult:
        """取引所サポートチェック"""
        current_exchange = self._get_current_exchange()
        supported_exchanges = self.config.get("supported_exchanges", [])
        
        if current_exchange not in supported_exchanges:
            return EarlyFailResult(
                symbol=symbol,
                passed=False,
                fail_reason=FailReason.EXCHANGE_NOT_SUPPORTED,
                error_message=f"取引所 {current_exchange} はサポートされていません",
                suggestion=f"サポートされている取引所: {', '.join(supported_exchanges)}"
            )
        
        return EarlyFailResult(symbol=symbol, passed=True)
    
    async def _check_historical_data_availability(self, symbol: str) -> EarlyFailResult:
        """履歴データ利用可能性チェック"""
        required_days = self.config.get("required_historical_days", 90)
        test_timeframes = self.config.get("test_timeframes", ["1h"])
        
        exchange = self._get_current_exchange()
        
        try:
            from hyperliquid_api_client import MultiExchangeAPIClient
            api_client = MultiExchangeAPIClient(exchange_type=exchange)
            
            # 指定日数前のデータを軽量チェック
            test_start = datetime.now() - timedelta(days=required_days)
            test_end = test_start + timedelta(hours=2)
            
            for timeframe in test_timeframes:
                self.logger.debug(f"Testing {symbol} {timeframe} data from {test_start.strftime('%Y-%m-%d')}")
                
                test_data = await api_client.get_ohlcv_data(symbol, timeframe, test_start, test_end)
                data_points = len(test_data) if test_data is not None else 0
                
                if data_points == 0:
                    return EarlyFailResult(
                        symbol=symbol,
                        passed=False,
                        fail_reason=FailReason.INSUFFICIENT_HISTORICAL_DATA,
                        error_message=f"{symbol}は新規上場銘柄のため、十分な履歴データがありません（{required_days}日分必要）",
                        suggestion=f"{symbol}の上場から{required_days}日経過後に再度お試しください",
                        metadata={
                            "required_days": required_days,
                            "tested_timeframe": timeframe,
                            "data_points_found": data_points
                        }
                    )
            
            return EarlyFailResult(
                symbol=symbol,
                passed=True,
                metadata={"historical_data_available": True}
            )
            
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['no data', 'not found', 'invalid']):
                return EarlyFailResult(
                    symbol=symbol,
                    passed=False,
                    fail_reason=FailReason.INSUFFICIENT_HISTORICAL_DATA,
                    error_message=f"{symbol}の履歴データが取得できません",
                    suggestion="銘柄名を確認するか、しばらく時間をおいて再度お試しください"
                )
            else:
                raise  # その他のエラーは上位に伝播
    
    def _get_current_exchange(self) -> str:
        """現在の取引所設定を取得"""
        try:
            if os.path.exists('exchange_config.json'):
                with open('exchange_config.json', 'r') as f:
                    config = json.load(f)
                    return config.get('default_exchange', 'hyperliquid').lower()
        except Exception:
            pass
        return 'hyperliquid'


# カスタム検証ルールの例
def custom_meme_coin_validator(symbol: str) -> EarlyFailResult:
    """ミームコイン専用の検証ルール例"""
    meme_coins = ['DOGE', 'SHIB', 'PEPE', 'WIF', 'BOME']
    
    if symbol in meme_coins:
        # ミームコインは特別な警告を出すが許可
        return EarlyFailResult(
            symbol=symbol,
            passed=True,
            metadata={"warning": "ミームコインは高いボラティリティにご注意ください"}
        )
    
    return EarlyFailResult(symbol=symbol, passed=True)


def custom_symbol_length_validator(symbol: str) -> EarlyFailResult:
    """シンボル長制限の検証ルール例"""
    if len(symbol) > 8:
        return EarlyFailResult(
            symbol=symbol,
            passed=False,
            fail_reason=FailReason.CUSTOM_RULE_VIOLATION,
            error_message="シンボル名が長すぎます（8文字以内）",
            suggestion="短縮されたシンボル名をお試しください"
        )
    
    return EarlyFailResult(symbol=symbol, passed=True)


# モジュール使用例
async def main():
    """使用例"""
    validator = SymbolEarlyFailValidator()
    
    # カスタムルール追加
    validator.add_custom_validator(custom_meme_coin_validator)
    validator.add_custom_validator(custom_symbol_length_validator)
    
    # テスト
    test_symbols = ["BTC", "ZORA", "INVALIDTOKEN"]
    
    for symbol in test_symbols:
        result = await validator.validate_symbol(symbol)
        print(f"\n{symbol}: {'✅ PASS' if result.passed else '❌ FAIL'}")
        if not result.passed:
            print(f"  理由: {result.fail_reason.value}")
            print(f"  メッセージ: {result.error_message}")
            print(f"  提案: {result.suggestion}")


if __name__ == "__main__":
    asyncio.run(main())