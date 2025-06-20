#!/usr/bin/env python3
"""
強化版Early Fail検証システムのテストスイート

新機能4項目の包括的テスト:
1. API接続タイムアウトチェック
2. 取引所別アクティブ状態チェック
3. 厳格データ品質チェック（5%欠落許容）
4. システムリソース不足チェック
"""

import asyncio
import json
import os
import tempfile
import sys
import time
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

# テスト対象をインポート
from symbol_early_fail_validator import (
    SymbolEarlyFailValidator, 
    EarlyFailResult, 
    FailReason
)


class EnhancedTestRunner:
    """強化版テスト実行クラス"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0
    
    async def run_test(self, test_name, test_func):
        """テスト関数を実行"""
        self.total += 1
        print(f"\n🧪 {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            print(f"✅ PASS: {test_name}")
            self.passed += 1
        except Exception as e:
            print(f"❌ FAIL: {test_name}")
            print(f"   エラー: {e}")
            self.failed += 1
    
    def print_summary(self):
        """テスト結果サマリを表示"""
        print("\n" + "=" * 70)
        print("📊 強化版Early Failテスト結果サマリ")
        print("=" * 70)
        print(f"合格: {self.passed}/{self.total}")
        print(f"失敗: {self.failed}/{self.total}")
        print(f"成功率: {(self.passed/self.total*100):.1f}%" if self.total > 0 else "N/A")
        
        if self.failed == 0:
            print("🎉 すべてのテストが合格しました！")
        else:
            print("⚠️ 一部のテストが失敗しました")


# ===== 1. API接続タイムアウトチェックテスト =====

async def test_api_timeout_success():
    """API接続成功テスト"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "api_timeouts": {"connection_check": 10},
            "fail_messages": {"api_timeout": "{symbol}: API応答が{timeout}秒でタイムアウトしました"},
            "suggestions": {"api_timeout": "ネットワーク接続を確認してください"}
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 快速応答をシミュレート（3秒）
            async def quick_response(*args, **kwargs):
                await asyncio.sleep(0.1)  # 短時間応答
                return {'symbol': 'BTC', 'is_active': True}
            
            mock_client.get_market_info.side_effect = quick_response
            
            result = await validator._check_api_connection_timeout('BTC')
            
            assert result.passed is True
            assert result.symbol == 'BTC'
            assert 'response_time' in result.metadata
        
        os.unlink(temp_config.name)


async def test_api_timeout_failure():
    """API接続タイムアウト失敗テスト"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "api_timeouts": {"connection_check": 2},  # 2秒に短縮してテスト
            "fail_messages": {"api_timeout": "{symbol}: API応答が{timeout}秒でタイムアウトしました"},
            "suggestions": {"api_timeout": "ネットワーク接続を確認してください"}
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 遅い応答をシミュレート（3秒で2秒タイムアウト）
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(3)  # タイムアウトより長い
                return {'symbol': 'SLOW', 'is_active': True}
            
            mock_client.get_market_info.side_effect = slow_response
            
            result = await validator._check_api_connection_timeout('SLOW')
            
            assert result.passed is False
            assert result.fail_reason == FailReason.API_TIMEOUT
            assert 'SLOW' in result.error_message
            assert '2秒' in result.error_message
        
        os.unlink(temp_config.name)


# ===== 2. 取引所別アクティブ状態チェックテスト =====

async def test_exchange_active_status_success():
    """取引所アクティブ状態チェック成功テスト"""
    validator = SymbolEarlyFailValidator()
    
    with patch('symbol_early_fail_validator.MultiExchangeAPIClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # アクティブな銘柄をシミュレート
        mock_client.get_market_info.return_value = {
            'symbol': 'ETH',
            'is_active': True,
            'volume_24h': 1000000  # 十分な出来高
        }
        
        result = await validator._check_current_exchange_active_status('ETH')
        
        assert result.passed is True
        assert result.metadata['is_active'] is True
        assert result.metadata['volume_24h'] > 0


async def test_exchange_inactive_symbol():
    """取引停止中銘柄テスト"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "fail_messages": {"symbol_not_tradable": "{symbol}は{exchange}で取引停止中です"},
            "suggestions": {"symbol_not_tradable": "{exchange}での取引再開をお待ちください"}
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 取引停止中の銘柄をシミュレート
            mock_client.get_market_info.return_value = {
                'symbol': 'HALTED',
                'is_active': False,  # 取引停止
                'volume_24h': 0
            }
            
            result = await validator._check_current_exchange_active_status('HALTED')
            
            assert result.passed is False
            assert result.fail_reason == FailReason.SYMBOL_NOT_TRADABLE
            assert 'HALTED' in result.error_message
            assert '取引停止中' in result.error_message
        
        os.unlink(temp_config.name)


async def test_insufficient_liquidity():
    """流動性不足テスト"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "fail_messages": {"insufficient_liquidity": "{symbol}は{exchange}で24時間取引量が0です"},
            "suggestions": {"insufficient_liquidity": "流動性のある銘柄を選択してください"}
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 出来高0の銘柄をシミュレート
            mock_client.get_market_info.return_value = {
                'symbol': 'NOLIQ',
                'is_active': True,
                'volume_24h': 0  # 出来高なし
            }
            
            result = await validator._check_current_exchange_active_status('NOLIQ')
            
            assert result.passed is False
            assert result.fail_reason == FailReason.INSUFFICIENT_LIQUIDITY
            assert 'NOLIQ' in result.error_message
            assert '24時間取引量が0' in result.error_message
        
        os.unlink(temp_config.name)


# ===== 3. 厳格データ品質チェックテスト =====

async def test_strict_data_quality_success():
    """厳格データ品質チェック成功テスト（95%完全性）"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "strict_data_quality": {
                "sample_days": 7,  # テスト用に短縮
                "min_completeness": 0.95,
                "timeout_seconds": 10
            }
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 高品質データをシミュレート（95%以上）
            sample_data = []
            expected_points = 7 * 24  # 168時間
            actual_points = int(expected_points * 0.97)  # 97%完全性
            
            for i in range(actual_points):
                sample_data.append({
                    'timestamp': datetime.now() - timedelta(hours=i),
                    'open': 50000, 'close': 50100
                })
            
            mock_client.get_ohlcv_data.return_value = sample_data
            
            result = await validator._check_strict_data_quality('BTC')
            
            assert result.passed is True
            assert 'data_completeness' in result.metadata
            assert '97.0%' in result.metadata['data_completeness']
        
        os.unlink(temp_config.name)


async def test_strict_data_quality_failure():
    """厳格データ品質チェック失敗テスト（5%未満）"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "strict_data_quality": {
                "sample_days": 7,
                "min_completeness": 0.95,
                "timeout_seconds": 10
            },
            "fail_messages": {"insufficient_data_quality": "{symbol}: データ品質不足（欠落率{missing_rate} > 5%許容）"},
            "suggestions": {"insufficient_data_quality": "データ完全性が95%以上の銘柄を選択してください"}
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 低品質データをシミュレート（90%完全性、5%欠落許容を超過）
            sample_data = []
            expected_points = 7 * 24  # 168時間
            actual_points = int(expected_points * 0.90)  # 90%完全性（不足）
            
            for i in range(actual_points):
                sample_data.append({
                    'timestamp': datetime.now() - timedelta(hours=i),
                    'open': 1000, 'close': 1100
                })
            
            mock_client.get_ohlcv_data.return_value = sample_data
            
            result = await validator._check_strict_data_quality('LOWQUAL')
            
            assert result.passed is False
            assert result.fail_reason == FailReason.INSUFFICIENT_DATA_QUALITY
            assert 'LOWQUAL' in result.error_message
            assert '10.0%' in result.metadata['missing_rate']  # 10%欠落
        
        os.unlink(temp_config.name)


# ===== 4. システムリソース不足チェックテスト =====

def test_system_resources_success():
    """システムリソースチェック成功テスト"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "resource_thresholds": {
                "max_cpu_percent": 85,
                "max_memory_percent": 85,
                "min_free_disk_gb": 2.0
            }
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        # psutilをモック
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('shutil.disk_usage') as mock_disk:
            
            # 正常なリソース状況をシミュレート
            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.free = 5 * (1024**3)  # 5GB空き
            
            # 非同期関数を同期的に実行
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(validator._check_system_resources('BTC'))
            finally:
                loop.close()
            
            assert result.passed is True
            assert 'cpu_percent' in result.metadata
            assert 'memory_percent' in result.metadata
            assert 'free_disk_gb' in result.metadata
        
        os.unlink(temp_config.name)


def test_system_resources_cpu_failure():
    """CPU使用率過多テスト"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "resource_thresholds": {"max_cpu_percent": 85},
            "fail_messages": {"insufficient_resources": "システムリソース不足: {resource_type}使用率が{usage}%で上限{limit}%を超過"},
            "suggestions": {"insufficient_resources": "システム負荷が下がってから再度お試しください"}
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        # 高CPU使用率をシミュレート
        with patch('psutil.cpu_percent', return_value=95.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('shutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.free = 5 * (1024**3)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(validator._check_system_resources('HIGHCPU'))
            finally:
                loop.close()
            
            assert result.passed is False
            assert result.fail_reason == FailReason.INSUFFICIENT_RESOURCES
            assert 'CPU' in result.error_message
            assert '95.0%' in result.error_message
        
        os.unlink(temp_config.name)


def test_system_resources_psutil_missing():
    """psutil未インストール時のテスト"""
    validator = SymbolEarlyFailValidator()
    
    # psutilが見つからない場合をシミュレート
    with patch('builtins.__import__', side_effect=ImportError("No module named 'psutil'")):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(validator._check_system_resources('TEST'))
        finally:
            loop.close()
        
        assert result.passed is True  # 警告として処理継続
        assert 'warning' in result.metadata
        assert 'psutil' in result.metadata['warning']


# ===== 統合テスト =====

async def test_enhanced_validate_symbol_success():
    """強化版検証システム統合成功テスト"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "api_timeouts": {"connection_check": 10},
            "strict_data_quality": {"sample_days": 7, "min_completeness": 0.95},
            "resource_thresholds": {"max_cpu_percent": 85, "max_memory_percent": 85},
            "enable_symbol_existence_check": True,
            "enable_exchange_support_check": True,
            "enable_ohlcv_check": True
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        with patch('symbol_early_fail_validator.MultiExchangeAPIClient') as mock_client_class, \
             patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('shutil.disk_usage') as mock_disk:
            
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 全て成功するケースをシミュレート
            mock_client.get_market_info.return_value = {
                'symbol': 'BTC', 'is_active': True, 'volume_24h': 1000000
            }
            
            # 高品質データ
            sample_data = [{'timestamp': datetime.now(), 'open': 50000, 'close': 50100} 
                          for _ in range(int(7 * 24 * 0.97))]
            mock_client.get_ohlcv_data.return_value = sample_data
            
            # 正常リソース
            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.free = 5 * (1024**3)
            
            result = await validator.validate_symbol('BTC')
            
            assert result.passed is True
            assert result.metadata['enhanced'] is True
        
        os.unlink(temp_config.name)


async def test_enhanced_validate_symbol_api_timeout():
    """強化版検証システム統合失敗テスト（API timeout）"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "api_timeouts": {"connection_check": 1},  # 1秒に短縮
            "fail_messages": {"api_timeout": "{symbol}: API応答が{timeout}秒でタイムアウトしました"}
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 遅いAPI応答をシミュレート
            async def slow_api(*args, **kwargs):
                await asyncio.sleep(2)  # 1秒タイムアウトより長い
                return {'symbol': 'TIMEOUT', 'is_active': True}
            
            mock_client.get_market_info.side_effect = slow_api
            
            result = await validator.validate_symbol('TIMEOUT')
            
            assert result.passed is False
            assert result.fail_reason == FailReason.API_TIMEOUT
        
        os.unlink(temp_config.name)


# ===== メインテスト実行 =====

async def main():
    """強化版Early Failテストの実行"""
    print("🚀 強化版Early Fail検証システム - 包括的テストスイート")
    print("=" * 70)
    
    runner = EnhancedTestRunner()
    
    # 1. API接続タイムアウトテスト
    print("\n📡 API接続タイムアウトテスト")
    await runner.run_test("API接続成功", test_api_timeout_success)
    await runner.run_test("API接続タイムアウト", test_api_timeout_failure)
    
    # 2. 取引所アクティブ状態テスト
    print("\n🏪 取引所アクティブ状態テスト")
    await runner.run_test("アクティブ状態チェック成功", test_exchange_active_status_success)
    await runner.run_test("取引停止中銘柄", test_exchange_inactive_symbol)
    await runner.run_test("流動性不足", test_insufficient_liquidity)
    
    # 3. 厳格データ品質テスト
    print("\n📊 厳格データ品質テスト")
    await runner.run_test("データ品質チェック成功", test_strict_data_quality_success)
    await runner.run_test("データ品質不足", test_strict_data_quality_failure)
    
    # 4. システムリソーステスト
    print("\n💻 システムリソーステスト")
    await runner.run_test("リソースチェック成功", test_system_resources_success)
    await runner.run_test("CPU使用率過多", test_system_resources_cpu_failure)
    await runner.run_test("psutil未インストール", test_system_resources_psutil_missing)
    
    # 5. 統合テスト
    print("\n🔗 統合テスト")
    await runner.run_test("強化版検証成功", test_enhanced_validate_symbol_success)
    await runner.run_test("強化版検証失敗（timeout）", test_enhanced_validate_symbol_api_timeout)
    
    # 結果表示
    runner.print_summary()
    
    # 使用例デモ
    print("\n" + "=" * 70)
    print("📋 強化版Early Fail検証システム使用例")
    print("=" * 70)
    
    validator = SymbolEarlyFailValidator()
    print(f"✅ 強化版バリデータ初期化完了")
    print(f"   新機能: API timeout, Active status, Data quality, Resources")
    print(f"   最大検証時間: {validator.config.get('max_validation_time_seconds', 120)}秒")
    print(f"   厳格品質要件: {validator.config.get('strict_data_quality', {}).get('min_completeness', 0.95):.1%}完全性")
    
    return runner.failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 すべてのテストが成功しました！")
        print("強化版Early Fail検証システムの実装が完了しました。")
        sys.exit(0)
    else:
        print("\n⚠️ 一部のテストが失敗しました")
        sys.exit(1)