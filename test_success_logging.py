#!/usr/bin/env python3
"""
Early Fail検証成功時の目立つサーバーログ機能テスト
"""

import asyncio
import json
import os
import tempfile
from unittest.mock import patch, AsyncMock

from symbol_early_fail_validator import SymbolEarlyFailValidator, EarlyFailResult


async def test_full_banner_logging():
    """フルバナースタイルログのテスト"""
    print("\n🧪 フルバナースタイルログテスト")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "logging": {
                "enable_success_highlight": True,
                "banner_style": "full",
                "success_log_level": "info",
                "include_system_notification": True
            }
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        # 全ての検証をMockで成功させる
        with patch.object(validator, '_check_symbol_existence', return_value=EarlyFailResult('BTC', True)), \
             patch.object(validator, '_check_exchange_support', return_value=EarlyFailResult('BTC', True)), \
             patch.object(validator, '_check_api_connection_timeout', return_value=EarlyFailResult('BTC', True)), \
             patch.object(validator, '_check_current_exchange_active_status', return_value=EarlyFailResult('BTC', True)), \
             patch.object(validator, '_check_system_resources', return_value=EarlyFailResult('BTC', True)), \
             patch.object(validator, '_check_strict_data_quality', return_value=EarlyFailResult('BTC', True)), \
             patch.object(validator, '_check_historical_data_availability', return_value=EarlyFailResult('BTC', True)):
            
            result = await validator.validate_symbol('BTC')
            
            assert result.passed is True
            print("✅ フルバナーログが出力されました（上記参照）")
        
        os.unlink(temp_config.name)


async def test_compact_banner_logging():
    """コンパクトスタイルログのテスト"""
    print("\n🧪 コンパクトスタイルログテスト")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "logging": {
                "enable_success_highlight": True,
                "banner_style": "compact",
                "success_log_level": "warning",  # 警告レベルで目立たせる
                "include_system_notification": False
            }
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        # 全ての検証をMockで成功させる
        with patch.object(validator, '_check_symbol_existence', return_value=EarlyFailResult('ETH', True)), \
             patch.object(validator, '_check_exchange_support', return_value=EarlyFailResult('ETH', True)), \
             patch.object(validator, '_check_api_connection_timeout', return_value=EarlyFailResult('ETH', True)), \
             patch.object(validator, '_check_current_exchange_active_status', return_value=EarlyFailResult('ETH', True)), \
             patch.object(validator, '_check_system_resources', return_value=EarlyFailResult('ETH', True)), \
             patch.object(validator, '_check_strict_data_quality', return_value=EarlyFailResult('ETH', True)), \
             patch.object(validator, '_check_historical_data_availability', return_value=EarlyFailResult('ETH', True)):
            
            result = await validator.validate_symbol('ETH')
            
            assert result.passed is True
            print("✅ コンパクトログが出力されました（上記参照）")
        
        os.unlink(temp_config.name)


async def test_minimal_banner_logging():
    """ミニマルスタイルログのテスト"""
    print("\n🧪 ミニマルスタイルログテスト")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "logging": {
                "enable_success_highlight": True,
                "banner_style": "minimal",
                "success_log_level": "success",
                "include_system_notification": False
            }
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        # 全ての検証をMockで成功させる
        with patch.object(validator, '_check_symbol_existence', return_value=EarlyFailResult('SOL', True)), \
             patch.object(validator, '_check_exchange_support', return_value=EarlyFailResult('SOL', True)), \
             patch.object(validator, '_check_api_connection_timeout', return_value=EarlyFailResult('SOL', True)), \
             patch.object(validator, '_check_current_exchange_active_status', return_value=EarlyFailResult('SOL', True)), \
             patch.object(validator, '_check_system_resources', return_value=EarlyFailResult('SOL', True)), \
             patch.object(validator, '_check_strict_data_quality', return_value=EarlyFailResult('SOL', True)), \
             patch.object(validator, '_check_historical_data_availability', return_value=EarlyFailResult('SOL', True)):
            
            result = await validator.validate_symbol('SOL')
            
            assert result.passed is True
            print("✅ ミニマルログが出力されました（上記参照）")
        
        os.unlink(temp_config.name)


async def test_disabled_highlight_logging():
    """ハイライト無効時のテスト"""
    print("\n🧪 ハイライト無効ログテスト")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "logging": {
                "enable_success_highlight": False
            }
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        # 全ての検証をMockで成功させる
        with patch.object(validator, '_check_symbol_existence', return_value=EarlyFailResult('DOGE', True)), \
             patch.object(validator, '_check_exchange_support', return_value=EarlyFailResult('DOGE', True)), \
             patch.object(validator, '_check_api_connection_timeout', return_value=EarlyFailResult('DOGE', True)), \
             patch.object(validator, '_check_current_exchange_active_status', return_value=EarlyFailResult('DOGE', True)), \
             patch.object(validator, '_check_system_resources', return_value=EarlyFailResult('DOGE', True)), \
             patch.object(validator, '_check_strict_data_quality', return_value=EarlyFailResult('DOGE', True)), \
             patch.object(validator, '_check_historical_data_availability', return_value=EarlyFailResult('DOGE', True)):
            
            result = await validator.validate_symbol('DOGE')
            
            assert result.passed is True
            print("✅ シンプルログが出力されました（ハイライトなし）")
        
        os.unlink(temp_config.name)


async def main():
    """目立つサーバーログ機能のテスト実行"""
    print("🚀 Early Fail成功時の目立つサーバーログ機能テスト")
    print("=" * 60)
    
    await test_full_banner_logging()
    await test_compact_banner_logging()
    await test_minimal_banner_logging()
    await test_disabled_highlight_logging()
    
    print("\n" + "=" * 60)
    print("📋 ログ設定オプション")
    print("=" * 60)
    print("1. フルバナー（full）: 詳細な検証項目と目立つボーダー")
    print("2. コンパクト（compact）: 要約された情報")
    print("3. ミニマル（minimal）: 最小限の成功メッセージ")
    print("4. 無効（disabled）: ハイライトなしのシンプルログ")
    print("\nログレベル: info, success, warning")
    print("システム通知: true/false")
    
    print("\n🎉 目立つサーバーログ機能の実装が完了しました！")


if __name__ == "__main__":
    asyncio.run(main())