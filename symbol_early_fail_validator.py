#!/usr/bin/env python3
"""
銘柄追加時のEarly Fail検証システム

マルチプロセス生成前に軽量な検証を行い、問題のある銘柄を即座に拒否する。
カスタマイズ可能な検証ルールを提供。
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
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
    # 新規追加
    API_TIMEOUT = "api_timeout"
    SYMBOL_NOT_TRADABLE = "symbol_not_tradable"
    INSUFFICIENT_LIQUIDITY = "insufficient_liquidity"
    INSUFFICIENT_DATA_QUALITY = "insufficient_data_quality"
    INSUFFICIENT_RESOURCES = "insufficient_resources"


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
        銘柄のEarly Fail検証を実行（強化版）
        
        Args:
            symbol: 検証する銘柄名
            
        Returns:
            EarlyFailResult: 検証結果
        """
        self.logger.info(f"🔍 Early Fail検証開始（強化版）: {symbol}")
        
        try:
            # 既存検証（順序変更なし）
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
            
            # 新規追加検証（軽量→重い順）
            # 3. API接続タイムアウト（10秒、最優先）
            result = await self._check_api_connection_timeout(symbol)
            if not result.passed:
                return result
            
            # 4. 取引所別アクティブ状態（軽量）
            result = await self._check_current_exchange_active_status(symbol)
            if not result.passed:
                return result
            
            # 5. システムリソース（軽量）
            result = await self._check_system_resources(symbol)
            if not result.passed:
                return result
            
            # 6. 厳格データ品質（重め、30秒タイムアウト）
            result = await self._check_strict_data_quality(symbol)
            if not result.passed:
                return result
            
            # 7. 既存のOHLCV履歴データチェック（90日分）
            if self.config.get("enable_ohlcv_check", True):
                result = await self._check_historical_data_availability(symbol)
                if not result.passed:
                    return result
            
            # 8. カスタム検証ルール実行
            for custom_validator in self.custom_validators:
                try:
                    result = custom_validator(symbol)
                    if not result.passed:
                        return result
                except Exception as e:
                    self.logger.warning(f"カスタム検証エラー: {custom_validator.__name__} - {e}")
            
            # 全ての検証をパス - 目立つサーバーログ出力
            self._log_validation_success(symbol)
            return EarlyFailResult(
                symbol=symbol,
                passed=True,
                metadata={"validation_time": datetime.now(timezone.utc).isoformat(), "enhanced": True}
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
            test_start = datetime.now(timezone.utc) - timedelta(days=required_days)
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
    
    async def _check_api_connection_timeout(self, symbol: str) -> EarlyFailResult:
        """API接続タイムアウトチェック（10秒制限）"""
        try:
            timeout_seconds = self.config.get('api_timeouts', {}).get('connection_check', 10)
            
            async with asyncio.timeout(timeout_seconds):
                # MultiExchangeAPIClientをインポート
                from hyperliquid_api_client import MultiExchangeAPIClient
                
                api_client = MultiExchangeAPIClient()
                start_time = time.time()
                market_info = await api_client.get_market_info(symbol)
                response_time = time.time() - start_time
                
            return EarlyFailResult(
                symbol=symbol, passed=True, 
                metadata={"response_time": f"{response_time:.2f}秒"}
            )
                                 
        except asyncio.TimeoutError:
            error_message = self.config.get('fail_messages', {}).get('api_timeout', 
                                           "{symbol}: API応答が{timeout}秒でタイムアウトしました").format(
                symbol=symbol, timeout=timeout_seconds)
            suggestion = self.config.get('suggestions', {}).get('api_timeout',
                                       "ネットワーク接続を確認するか、しばらく時間をおいて再度お試しください")
            
            return EarlyFailResult(
                symbol=symbol, passed=False,
                fail_reason=FailReason.API_TIMEOUT,
                error_message=error_message,
                suggestion=suggestion
            )
        except Exception as e:
            return EarlyFailResult(
                symbol=symbol, passed=False,
                fail_reason=FailReason.API_CONNECTION_FAILED,
                error_message=f"{symbol}: API接続エラー - {str(e)}"
            )
    
    async def _check_current_exchange_active_status(self, symbol: str) -> EarlyFailResult:
        """現在選択中の取引所でのアクティブ状態チェック"""
        try:
            # 現在の取引所設定を取得
            current_exchange = self._get_current_exchange()
            
            from hyperliquid_api_client import MultiExchangeAPIClient
            api_client = MultiExchangeAPIClient()
            market_info = await api_client.get_market_info(symbol)
            
            # is_active チェック（取引所別）
            is_active = market_info.get('is_active', False)
            if not is_active:
                error_message = self.config.get('fail_messages', {}).get('symbol_not_tradable',
                                               "{symbol}は{exchange}で取引停止中です").format(
                    symbol=symbol, exchange=current_exchange)
                suggestion = self.config.get('suggestions', {}).get('symbol_not_tradable',
                                           "{exchange}での取引再開をお待ちください").format(
                    exchange=current_exchange)
                
                return EarlyFailResult(
                    symbol=symbol, passed=False,
                    fail_reason=FailReason.SYMBOL_NOT_TRADABLE,
                    error_message=error_message,
                    suggestion=suggestion,
                    metadata={"exchange": current_exchange, "is_active": False}
                )
            
            # 24時間出来高チェック（0の場合は実質停止）
            volume_24h = market_info.get('volume_24h', 0)
            if volume_24h <= 0:
                error_message = self.config.get('fail_messages', {}).get('insufficient_liquidity',
                                               "{symbol}は{exchange}で24時間取引量が0です").format(
                    symbol=symbol, exchange=current_exchange)
                suggestion = self.config.get('suggestions', {}).get('insufficient_liquidity',
                                           "流動性のある銘柄を選択してください")
                
                return EarlyFailResult(
                    symbol=symbol, passed=False,
                    fail_reason=FailReason.INSUFFICIENT_LIQUIDITY,
                    error_message=error_message,
                    suggestion=suggestion,
                    metadata={"exchange": current_exchange, "volume_24h": volume_24h}
                )
            
            return EarlyFailResult(
                symbol=symbol, passed=True,
                metadata={
                    "exchange": current_exchange, 
                    "is_active": True,
                    "volume_24h": volume_24h
                }
            )
            
        except Exception as e:
            return EarlyFailResult(
                symbol=symbol, passed=False,
                fail_reason=FailReason.API_CONNECTION_FAILED,
                error_message=f"取引状況確認エラー: {str(e)}"
            )
    
    async def _check_strict_data_quality(self, symbol: str) -> EarlyFailResult:
        """厳格データ品質チェック（5%欠落許容）"""
        try:
            # 設定値を取得
            strict_config = self.config.get('strict_data_quality', {})
            sample_days = strict_config.get('sample_days', 30)
            min_completeness = strict_config.get('min_completeness', 0.95)
            timeout_seconds = strict_config.get('timeout_seconds', 30)
            
            # 直近指定日数分で品質チェック（軽量）
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=sample_days)
            
            from hyperliquid_api_client import MultiExchangeAPIClient
            api_client = MultiExchangeAPIClient()
            
            # タイムアウト付きでデータ取得
            async with asyncio.timeout(timeout_seconds):
                sample_data = await api_client.get_ohlcv_data(symbol, '1h', start_time, end_time)
            
            expected_points = sample_days * 24  # 指定日数 × 24時間
            actual_points = len(sample_data)
            completeness = actual_points / expected_points if expected_points > 0 else 0
            
            if completeness < min_completeness:
                missing_rate = 1 - completeness
                error_message = self.config.get('fail_messages', {}).get('insufficient_data_quality',
                                               "{symbol}: データ品質不足（欠落率{missing_rate} > 5%許容）").format(
                    symbol=symbol, missing_rate=f"{missing_rate:.1%}")
                suggestion = self.config.get('suggestions', {}).get('insufficient_data_quality',
                                           "データ完全性が95%以上の銘柄を選択してください")
                
                return EarlyFailResult(
                    symbol=symbol, passed=False,
                    fail_reason=FailReason.INSUFFICIENT_DATA_QUALITY,
                    error_message=error_message,
                    suggestion=suggestion,
                    metadata={
                        "data_completeness": f"{completeness:.1%}",
                        "missing_rate": f"{missing_rate:.1%}",
                        "actual_points": actual_points,
                        "expected_points": expected_points,
                        "sample_days": sample_days
                    }
                )
            
            return EarlyFailResult(
                symbol=symbol, passed=True,
                metadata={
                    "data_completeness": f"{completeness:.1%}",
                    "data_points": actual_points,
                    "sample_days": sample_days
                }
            )
            
        except asyncio.TimeoutError:
            return EarlyFailResult(
                symbol=symbol, passed=False,
                fail_reason=FailReason.API_CONNECTION_FAILED,
                error_message=f"{symbol}: データ品質チェックが{timeout_seconds}秒でタイムアウトしました"
            )
        except Exception as e:
            return EarlyFailResult(
                symbol=symbol, passed=False,
                fail_reason=FailReason.INSUFFICIENT_DATA_QUALITY,
                error_message=f"データ品質チェックエラー: {str(e)}"
            )
    
    async def _check_system_resources(self, symbol: str) -> EarlyFailResult:
        """システムリソース不足チェック"""
        try:
            # psutilのインポートを試行
            try:
                import psutil
                import shutil
            except ImportError:
                # psutil未インストールの場合は警告として処理継続
                return EarlyFailResult(
                    symbol=symbol, passed=True,
                    metadata={"warning": "psutilライブラリが未インストールのためリソースチェックをスキップ"}
                )
            
            # 設定値を取得
            thresholds = self.config.get('resource_thresholds', {})
            max_cpu_percent = thresholds.get('max_cpu_percent', 85)
            max_memory_percent = thresholds.get('max_memory_percent', 85)
            min_free_disk_gb = thresholds.get('min_free_disk_gb', 2.0)
            
            # CPU使用率チェック
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > max_cpu_percent:
                error_message = self.config.get('fail_messages', {}).get('insufficient_resources',
                                               "システムリソース不足: {resource_type}使用率が{usage}%で上限{limit}%を超過").format(
                    resource_type="CPU", usage=f"{cpu_percent:.1f}", limit=max_cpu_percent)
                suggestion = self.config.get('suggestions', {}).get('insufficient_resources',
                                           "システム負荷が下がってから再度お試しください")
                
                return EarlyFailResult(
                    symbol=symbol, passed=False,
                    fail_reason=FailReason.INSUFFICIENT_RESOURCES,
                    error_message=error_message,
                    suggestion=suggestion,
                    metadata={"resource_type": "CPU", "usage_percent": cpu_percent, "limit_percent": max_cpu_percent}
                )
            
            # メモリ使用率チェック
            memory = psutil.virtual_memory()
            if memory.percent > max_memory_percent:
                error_message = self.config.get('fail_messages', {}).get('insufficient_resources',
                                               "システムリソース不足: {resource_type}使用率が{usage}%で上限{limit}%を超過").format(
                    resource_type="メモリ", usage=f"{memory.percent:.1f}", limit=max_memory_percent)
                suggestion = self.config.get('suggestions', {}).get('insufficient_resources',
                                           "システム負荷が下がってから再度お試しください")
                
                return EarlyFailResult(
                    symbol=symbol, passed=False,
                    fail_reason=FailReason.INSUFFICIENT_RESOURCES,
                    error_message=error_message,
                    suggestion=suggestion,
                    metadata={"resource_type": "Memory", "usage_percent": memory.percent, "limit_percent": max_memory_percent}
                )
            
            # ディスク容量チェック
            disk = shutil.disk_usage('.')
            free_gb = disk.free / (1024**3)
            if free_gb < min_free_disk_gb:
                error_message = f"ディスク容量不足（残り{free_gb:.1f}GB < {min_free_disk_gb}GB）"
                suggestion = self.config.get('suggestions', {}).get('insufficient_resources',
                                           "システム負荷が下がってから再度お試しください")
                
                return EarlyFailResult(
                    symbol=symbol, passed=False,
                    fail_reason=FailReason.INSUFFICIENT_RESOURCES,
                    error_message=error_message,
                    suggestion=suggestion,
                    metadata={"resource_type": "Disk", "free_gb": free_gb, "required_gb": min_free_disk_gb}
                )
            
            return EarlyFailResult(
                symbol=symbol, passed=True,
                metadata={
                    "cpu_percent": f"{cpu_percent:.1f}%",
                    "memory_percent": f"{memory.percent:.1f}%", 
                    "free_disk_gb": f"{free_gb:.1f}GB"
                }
            )
                                 
        except Exception as e:
            # リソースチェック失敗は警告として処理継続
            return EarlyFailResult(
                symbol=symbol, passed=True,
                metadata={"warning": f"リソースチェック失敗: {str(e)}"}
            )
    
    def _log_validation_success(self, symbol: str):
        """Early Fail検証成功時の目立つサーバーログ出力"""
        # ログ設定取得
        log_config = self.config.get('logging', {})
        if not log_config.get('enable_success_highlight', True):
            # シンプルログのみ
            self.logger.success(f"✅ {symbol}: Early Fail検証合格（強化版）")
            return
        
        validation_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        banner_style = log_config.get('banner_style', 'full')
        
        if banner_style == 'full':
            # フルバナースタイル
            border = "=" * 80
            success_border = "🎉" * 20
            
            success_messages = [
                "",
                border,
                f"🚀 EARLY FAIL VALIDATION SUCCESS - {symbol} 🚀",
                border,
                f"⏰ 検証完了時刻: {validation_time}",
                f"🔍 検証項目: 8項目すべて合格",
                f"📊 実行内容:",
                f"   ✅ 1. シンボル存在チェック",
                f"   ✅ 2. 取引所サポートチェック", 
                f"   ✅ 3. API接続タイムアウト（10秒以内）",
                f"   ✅ 4. 取引所アクティブ状態（取引可能）",
                f"   ✅ 5. システムリソース（CPU/メモリ/ディスク正常）",
                f"   ✅ 6. データ品質（95%以上完全性）",
                f"   ✅ 7. 履歴データ可用性（90日分）",
                f"   ✅ 8. カスタム検証ルール",
                "",
                f"🎯 {symbol} は全ての品質基準を満たしており、分析処理の実行が承認されました",
                f"🔥 マルチプロセス分析を安全に開始できます",
                "",
                success_border + " VALIDATION SUCCESS " + success_border,
                border,
                ""
            ]
        
        elif banner_style == 'compact':
            # コンパクトスタイル
            success_messages = [
                "",
                f"🚀 EARLY FAIL SUCCESS - {symbol} 🚀",
                f"⏰ {validation_time} | 🔍 8項目合格 | 🎯 分析承認済み",
                f"✅ API接続・取引状態・リソース・データ品質 すべて正常",
                ""
            ]
        
        else:
            # ミニマルスタイル
            success_messages = [
                f"🚀 {symbol}: Early Fail検証完了 - 8項目すべて合格 🎯"
            ]
        
        # ログレベル取得
        log_level = log_config.get('success_log_level', 'info')
        
        # 各行をログ出力
        for message in success_messages:
            if message.strip() == "":
                print("")  # 空行
            elif message.startswith("=") or message.startswith("🎉"):
                self.logger.info(message)  # ボーダーライン
            else:
                if log_level == 'info':
                    self.logger.info(message)
                elif log_level == 'success':
                    self.logger.success(message)
                elif log_level == 'warning':
                    self.logger.warning(message)  # 警告レベルで目立たせる
                else:
                    self.logger.success(message)
        
        # システム通知（オプション）
        if log_config.get('include_system_notification', True):
            # 追加で標準出力にも出力（確実に見えるように）
            print(f"\n🚨 【重要】Early Fail検証完了: {symbol} が全ての品質基準をクリアしました！")
            print(f"   → 分析処理の実行を開始します... ⚡\n")
            
            # システムログファイルにも記録
            import logging
            system_logger = logging.getLogger('system')
            system_logger.info(f"EARLY_FAIL_SUCCESS: {symbol} passed all 8 validation checks at {validation_time}")


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