#!/usr/bin/env python3
"""
Symbol Early Fail Validator のテストコード

様々なシナリオでEarly Fail検証システムをテストする。
"""

import asyncio
import json
import os
import tempfile
import sys
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

# pytest がない場合のためのダミー実装
try:
    import pytest
except ImportError:
    print("pytest not found, running without pytest decorators")
    
    class pytest:
        @staticmethod
        def mark():
            pass
        mark.asyncio = lambda x: x
        mark.skip = lambda reason: lambda x: x

# テスト対象をインポート
from symbol_early_fail_validator import (
    SymbolEarlyFailValidator, 
    EarlyFailResult, 
    FailReason,
    custom_meme_coin_validator,
    custom_symbol_length_validator
)


class TestSymbolEarlyFailValidator:
    """Early Fail Validator のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.test_config = {
            "required_historical_days": 30,  # テスト用に短縮
            "min_data_points": 100,
            "supported_exchanges": ["hyperliquid", "gateio"],
            "test_timeframes": ["1h"],
            "max_validation_time_seconds": 10,
            "enable_ohlcv_check": True,
            "enable_symbol_existence_check": True,
            "enable_exchange_support_check": True
        }
        json.dump(self.test_config, self.temp_config)
        self.temp_config.close()
        
        self.validator = SymbolEarlyFailValidator(config_path=self.temp_config.name)
    
    def teardown_method(self):
        """各テストメソッドの後に実行"""
        os.unlink(self.temp_config.name)


class TestBasicValidation:
    """基本的な検証テスト"""
    
    @pytest.mark.asyncio
    async def test_valid_symbol_passes(self):
        """有効な銘柄が検証をパスするかテスト"""
        validator = SymbolEarlyFailValidator()
        
        # Mockを使って成功ケースをシミュレート
        with patch('symbol_early_fail_validator.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 市場情報取得成功をシミュレート
            mock_client.get_market_info.return_value = {
                'symbol': 'BTC',
                'is_active': True,
                'current_price': 50000.0
            }
            
            # 履歴データ取得成功をシミュレート
            mock_data = [
                {'timestamp': datetime.now(), 'open': 50000, 'close': 50100},
                {'timestamp': datetime.now(), 'open': 50100, 'close': 50200}
            ]
            mock_client.get_ohlcv_data.return_value = mock_data
            
            result = await validator.validate_symbol('BTC')
            
            assert result.passed is True
            assert result.symbol == 'BTC'
            assert result.fail_reason is None
    
    @pytest.mark.asyncio
    async def test_invalid_symbol_fails(self):
        """無効な銘柄が検証に失敗するかテスト"""
        validator = SymbolEarlyFailValidator()
        
        with patch('symbol_early_fail_validator.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 銘柄が見つからないエラーをシミュレート
            mock_client.get_market_info.side_effect = Exception("Symbol INVALID not found")
            
            result = await validator.validate_symbol('INVALID')
            
            assert result.passed is False
            assert result.fail_reason == FailReason.SYMBOL_NOT_FOUND
            assert 'INVALID' in result.error_message


class TestHistoricalDataValidation:
    """履歴データ検証テスト"""
    
    @pytest.mark.asyncio
    async def test_insufficient_historical_data_fails(self):
        """履歴データ不足で検証が失敗するかテスト（ZORAケース）"""
        validator = SymbolEarlyFailValidator()
        
        with patch('symbol_early_fail_validator.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 市場情報は成功
            mock_client.get_market_info.return_value = {
                'symbol': 'ZORA',
                'is_active': True,
                'current_price': 1.5
            }
            
            # 履歴データは空（新規上場銘柄）
            mock_client.get_ohlcv_data.return_value = []
            
            result = await validator.validate_symbol('ZORA')
            
            assert result.passed is False
            assert result.fail_reason == FailReason.INSUFFICIENT_HISTORICAL_DATA
            assert 'ZORA' in result.error_message
            assert '90日' in result.error_message or '30日' in result.error_message  # 設定による
    
    @pytest.mark.asyncio
    async def test_sufficient_historical_data_passes(self):
        """十分な履歴データがある場合のテスト"""
        validator = SymbolEarlyFailValidator()
        
        with patch('symbol_early_fail_validator.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 市場情報は成功
            mock_client.get_market_info.return_value = {
                'symbol': 'ETH',
                'is_active': True,
                'current_price': 3000.0
            }
            
            # 十分な履歴データ
            mock_data = [
                {'timestamp': datetime.now() - timedelta(days=90), 'open': 2900, 'close': 2950},
                {'timestamp': datetime.now() - timedelta(days=89), 'open': 2950, 'close': 3000}
            ]
            mock_client.get_ohlcv_data.return_value = mock_data
            
            result = await validator.validate_symbol('ETH')
            
            assert result.passed is True


class TestCustomValidators:
    """カスタム検証ルールのテスト"""
    
    def test_custom_meme_coin_validator(self):
        """ミームコイン検証ルールのテスト"""
        # ミームコインの場合
        result = custom_meme_coin_validator('DOGE')
        assert result.passed is True
        assert 'ミームコイン' in result.metadata.get('warning', '')
        
        # 通常の銘柄の場合
        result = custom_meme_coin_validator('BTC')
        assert result.passed is True
        assert result.metadata.get('warning') is None
    
    def test_custom_symbol_length_validator(self):
        """シンボル長検証ルールのテスト"""
        # 短いシンボル（OK）
        result = custom_symbol_length_validator('BTC')
        assert result.passed is True
        
        # 長すぎるシンボル（NG）
        result = custom_symbol_length_validator('VERYLONGSYMBOL')
        assert result.passed is False
        assert result.fail_reason == FailReason.CUSTOM_RULE_VIOLATION
        assert '8文字以内' in result.error_message
    
    @pytest.mark.asyncio
    async def test_custom_validator_integration(self):
        """カスタム検証ルールの統合テスト"""
        validator = SymbolEarlyFailValidator()
        validator.add_custom_validator(custom_symbol_length_validator)
        
        with patch('symbol_early_fail_validator.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # API関連は成功をシミュレート
            mock_client.get_market_info.return_value = {'symbol': 'TOOLONG', 'is_active': True}
            mock_client.get_ohlcv_data.return_value = [{'timestamp': datetime.now()}]
            
            # カスタムルールで失敗するはず
            result = await validator.validate_symbol('VERYLONGSYMBOL')
            
            assert result.passed is False
            assert result.fail_reason == FailReason.CUSTOM_RULE_VIOLATION


class TestConfigurationManagement:
    """設定管理のテスト"""
    
    def test_config_loading(self):
        """設定ファイル読み込みのテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
            test_config = {
                "required_historical_days": 60,
                "supported_exchanges": ["hyperliquid"]
            }
            json.dump(test_config, temp_config)
            temp_config.close()
            
            validator = SymbolEarlyFailValidator(config_path=temp_config.name)
            
            assert validator.config['required_historical_days'] == 60
            assert validator.config['supported_exchanges'] == ["hyperliquid"]
            
            os.unlink(temp_config.name)
    
    def test_default_config_creation(self):
        """デフォルト設定ファイル作成のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, 'test_config.json')
            
            # 存在しない設定ファイルパスを指定
            validator = SymbolEarlyFailValidator(config_path=config_path)
            
            # デフォルト設定ファイルが作成されるはず
            assert os.path.exists(config_path)
            
            # 設定内容を確認
            with open(config_path, 'r') as f:
                config = json.load(f)
                assert 'required_historical_days' in config
                assert config['required_historical_days'] == 90


class TestExchangeSupport:
    """取引所サポートのテスト"""
    
    @pytest.mark.asyncio
    async def test_unsupported_exchange_fails(self):
        """サポートされていない取引所での検証テスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
            test_config = {
                "supported_exchanges": ["hyperliquid"],  # gateio は除外
                "enable_exchange_support_check": True
            }
            json.dump(test_config, temp_config)
            temp_config.close()
            
            validator = SymbolEarlyFailValidator(config_path=temp_config.name)
            
            # exchange_config.json を gateio に設定
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = '{"default_exchange": "gateio"}'
                
                result = await validator.validate_symbol('BTC')
                
                assert result.passed is False
                assert result.fail_reason == FailReason.EXCHANGE_NOT_SUPPORTED
            
            os.unlink(temp_config.name)


# 実際のAPIテスト（統合テスト）
class TestRealAPIIntegration:
    """実際のAPIとの統合テスト（オプション）"""
    
    @pytest.mark.skip(reason="Real API test - run manually when needed")
    @pytest.mark.asyncio
    async def test_real_btc_validation(self):
        """実際のBTC検証テスト（手動実行用）"""
        validator = SymbolEarlyFailValidator()
        
        # 実際のAPIを使用
        result = await validator.validate_symbol('BTC')
        
        print(f"BTC validation result: {result.passed}")
        if result.passed:
            print("✅ BTC validation passed")
        else:
            print(f"❌ BTC validation failed: {result.error_message}")
        
        # BTCは十分古い銘柄なので成功するはず
        assert result.passed is True
    
    @pytest.mark.skip(reason="Real API test - run manually when needed")
    @pytest.mark.asyncio
    async def test_real_zora_validation(self):
        """実際のZORA検証テスト（手動実行用）"""
        validator = SymbolEarlyFailValidator()
        
        # 実際のAPIを使用
        result = await validator.validate_symbol('ZORA')
        
        print(f"ZORA validation result: {result.passed}")
        if not result.passed:
            print(f"❌ ZORA validation failed (expected): {result.error_message}")
            print(f"   Suggestion: {result.suggestion}")
        
        # ZORAは新規銘柄なので失敗するはず
        assert result.passed is False
        assert result.fail_reason == FailReason.INSUFFICIENT_HISTORICAL_DATA


# テスト実行関数
async def run_quick_tests():
    """クイックテストの実行"""
    print("🧪 Symbol Early Fail Validator - クイックテスト")
    print("=" * 60)
    
    # 1. 基本的な設定テスト
    print("\n1. 設定ファイルテスト...")
    try:
        validator = SymbolEarlyFailValidator()
        print("✅ 設定ファイル読み込み成功")
        print(f"   必要日数: {validator.config['required_historical_days']}日")
        print(f"   サポート取引所: {validator.config['supported_exchanges']}")
    except Exception as e:
        print(f"❌ 設定ファイルテスト失敗: {e}")
    
    # 2. カスタム検証ルールテスト
    print("\n2. カスタム検証ルールテスト...")
    try:
        # シンボル長チェック
        result = custom_symbol_length_validator('BTC')
        assert result.passed
        print("✅ 短いシンボル: OK")
        
        result = custom_symbol_length_validator('VERYLONGSYMBOL')
        assert not result.passed
        print("✅ 長いシンボル: NG（期待通り）")
        
        # ミームコインチェック
        result = custom_meme_coin_validator('DOGE')
        assert result.passed
        print("✅ ミームコインチェック: OK")
        
    except Exception as e:
        print(f"❌ カスタム検証ルールテスト失敗: {e}")
    
    # 3. Mock APIテスト
    print("\n3. Mock APIテスト...")
    try:
        validator = SymbolEarlyFailValidator()
        
        with patch('symbol_early_fail_validator.MultiExchangeAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 成功ケース
            mock_client.get_market_info.return_value = {'symbol': 'TEST', 'is_active': True}
            mock_client.get_ohlcv_data.return_value = [{'timestamp': datetime.now()}]
            
            result = await validator.validate_symbol('TEST')
            assert result.passed
            print("✅ Mock API成功ケース: OK")
            
            # 失敗ケース（データなし）
            mock_client.get_ohlcv_data.return_value = []
            
            result = await validator.validate_symbol('NEWTOKEN')
            assert not result.passed
            print("✅ Mock API失敗ケース: OK（期待通り）")
            
    except Exception as e:
        print(f"❌ Mock APIテスト失敗: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 クイックテスト完了！")


# メイン実行
if __name__ == "__main__":
    print("Symbol Early Fail Validator テストスイート")
    print("=" * 60)
    
    # クイックテスト実行
    asyncio.run(run_quick_tests())
    
    print("\n📋 より詳細なテストを実行するには:")
    print("   pytest test_symbol_early_fail_validator.py -v")
    print("\n📋 実際のAPIテストを実行するには:")
    print("   pytest test_symbol_early_fail_validator.py::TestRealAPIIntegration -v -s")