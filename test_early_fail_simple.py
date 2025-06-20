#!/usr/bin/env python3
"""
Symbol Early Fail Validator のシンプルテスト

pytestに依存しない軽量テストスイート
"""

import asyncio
import json
import os
import tempfile
import sys
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

# テスト対象をインポート
from symbol_early_fail_validator import (
    SymbolEarlyFailValidator, 
    EarlyFailResult, 
    FailReason,
    custom_meme_coin_validator,
    custom_symbol_length_validator
)


class TestRunner:
    """テスト実行クラス"""
    
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
        print("\n" + "=" * 60)
        print("📊 テスト結果サマリ")
        print("=" * 60)
        print(f"合格: {self.passed}/{self.total}")
        print(f"失敗: {self.failed}/{self.total}")
        print(f"成功率: {(self.passed/self.total*100):.1f}%" if self.total > 0 else "N/A")
        
        if self.failed == 0:
            print("🎉 すべてのテストが合格しました！")
        else:
            print("⚠️ 一部のテストが失敗しました")


def test_config_loading():
    """設定ファイル読み込みテスト"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        test_config = {
            "required_historical_days": 60,
            "supported_exchanges": ["hyperliquid"],
            "enable_ohlcv_check": True
        }
        json.dump(test_config, temp_config)
        temp_config.close()
        
        validator = SymbolEarlyFailValidator(config_path=temp_config.name)
        
        assert validator.config['required_historical_days'] == 60
        assert validator.config['supported_exchanges'] == ["hyperliquid"]
        assert validator.config['enable_ohlcv_check'] is True
        
        os.unlink(temp_config.name)


def test_custom_meme_coin_validator():
    """ミームコイン検証ルールテスト"""
    # ミームコインの場合
    result = custom_meme_coin_validator('DOGE')
    assert result.passed is True
    assert result.symbol == 'DOGE'
    assert 'ミームコイン' in result.metadata.get('warning', '')
    
    # 通常の銘柄の場合
    result = custom_meme_coin_validator('BTC')
    assert result.passed is True
    assert result.symbol == 'BTC'


def test_custom_symbol_length_validator():
    """シンボル長検証ルールテスト"""
    # 短いシンボル（OK）
    result = custom_symbol_length_validator('BTC')
    assert result.passed is True
    
    # 適度な長さのシンボル（OK）
    result = custom_symbol_length_validator('ETHEREUM')
    assert result.passed is True
    
    # 長すぎるシンボル（NG）
    result = custom_symbol_length_validator('VERYLONGSYMBOL')
    assert result.passed is False
    assert result.fail_reason == FailReason.CUSTOM_RULE_VIOLATION
    assert '8文字以内' in result.error_message


async def test_valid_symbol_with_mock():
    """Mockを使った有効銘柄テスト"""
    validator = SymbolEarlyFailValidator()
    
    with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # 市場情報取得成功をシミュレート
        mock_client.get_market_info.return_value = {
            'symbol': 'BTC',
            'is_active': True,
            'current_price': 50000.0,
            'leverage_limit': 100.0
        }
        
        # 履歴データ取得成功をシミュレート
        mock_data = [
            {'timestamp': datetime.now() - timedelta(days=90), 'open': 49000, 'close': 49500},
            {'timestamp': datetime.now() - timedelta(days=89), 'open': 49500, 'close': 50000}
        ]
        mock_client.get_ohlcv_data.return_value = mock_data
        
        result = await validator.validate_symbol('BTC')
        
        assert result.passed is True, f"Expected passed=True, got {result.passed}"
        assert result.symbol == 'BTC', f"Expected symbol=BTC, got {result.symbol}"
        assert result.fail_reason is None, f"Expected fail_reason=None, got {result.fail_reason}"
        assert result.metadata is not None, f"Expected metadata to exist, got {result.metadata}"


async def test_invalid_symbol_with_mock():
    """Mockを使った無効銘柄テスト"""
    validator = SymbolEarlyFailValidator()
    
    with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # 銘柄が見つからないエラーをシミュレート
        mock_client.get_market_info.side_effect = Exception("Symbol INVALID not found")
        
        result = await validator.validate_symbol('INVALID')
        
        assert result.passed is False
        assert result.fail_reason == FailReason.SYMBOL_NOT_FOUND
        assert 'INVALID' in result.error_message
        assert '取引されていません' in result.error_message


async def test_insufficient_historical_data():
    """履歴データ不足テスト（ZORAケース）"""
    validator = SymbolEarlyFailValidator()
    
    with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # 市場情報は成功
        mock_client.get_market_info.return_value = {
            'symbol': 'ZORA',
            'is_active': True,
            'current_price': 1.5,
            'leverage_limit': 10.0
        }
        
        # 履歴データは空（新規上場銘柄）
        mock_client.get_ohlcv_data.return_value = []
        
        result = await validator.validate_symbol('ZORA')
        
        assert result.passed is False
        assert result.fail_reason == FailReason.INSUFFICIENT_HISTORICAL_DATA
        assert 'ZORA' in result.error_message
        assert '新規上場銘柄' in result.error_message
        assert '90日' in result.error_message


async def test_custom_validator_integration():
    """カスタム検証ルールの統合テスト"""
    validator = SymbolEarlyFailValidator()
    
    # カスタムルール追加
    validator.add_custom_validator(custom_symbol_length_validator)
    
    with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # API関連は成功をシミュレート
        mock_client.get_market_info.return_value = {
            'symbol': 'VERYLONGSYMBOL',
            'is_active': True,
            'current_price': 100.0
        }
        mock_client.get_ohlcv_data.return_value = [
            {'timestamp': datetime.now(), 'open': 100, 'close': 101}
        ]
        
        # カスタムルールで失敗するはず
        result = await validator.validate_symbol('VERYLONGSYMBOL')
        
        assert result.passed is False
        assert result.fail_reason == FailReason.CUSTOM_RULE_VIOLATION
        assert '8文字以内' in result.error_message


def test_exchange_config_reading():
    """取引所設定読み込みテスト"""
    validator = SymbolEarlyFailValidator()
    
    # デフォルトでhyperliquidが返される
    exchange = validator._get_current_exchange()
    assert exchange in ['hyperliquid', 'gateio']


async def test_multiple_custom_validators():
    """複数のカスタムバリデータテスト"""
    validator = SymbolEarlyFailValidator()
    
    # 複数のカスタムルール追加
    validator.add_custom_validator(custom_meme_coin_validator)
    validator.add_custom_validator(custom_symbol_length_validator)
    
    with patch('hyperliquid_api_client.MultiExchangeAPIClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # API成功をシミュレート
        mock_client.get_market_info.return_value = {'symbol': 'DOGE', 'is_active': True}
        mock_client.get_ohlcv_data.return_value = [{'timestamp': datetime.now()}]
        
        # DOGEは短いシンボルで、ミームコインなので両方パスするはず
        result = await validator.validate_symbol('DOGE')
        
        assert result.passed is True
        assert result.symbol == 'DOGE'


def test_fail_reason_enum():
    """FailReason enumのテスト"""
    reasons = [
        FailReason.INSUFFICIENT_HISTORICAL_DATA,
        FailReason.SYMBOL_NOT_FOUND,
        FailReason.EXCHANGE_NOT_SUPPORTED,
        FailReason.API_CONNECTION_FAILED,
        FailReason.CUSTOM_RULE_VIOLATION
    ]
    
    for reason in reasons:
        assert isinstance(reason.value, str)
        assert len(reason.value) > 0


# メイン実行
async def main():
    """メインテスト実行"""
    print("🚀 Symbol Early Fail Validator - シンプルテストスイート")
    print("=" * 60)
    
    runner = TestRunner()
    
    # 基本的なテスト
    await runner.run_test("設定ファイル読み込み", test_config_loading)
    await runner.run_test("ミームコイン検証", test_custom_meme_coin_validator)
    await runner.run_test("シンボル長検証", test_custom_symbol_length_validator)
    await runner.run_test("FailReason enum", test_fail_reason_enum)
    await runner.run_test("取引所設定読み込み", test_exchange_config_reading)
    
    # 非同期テスト
    await runner.run_test("有効銘柄（Mock）", test_valid_symbol_with_mock)
    await runner.run_test("無効銘柄（Mock）", test_invalid_symbol_with_mock)
    await runner.run_test("履歴データ不足", test_insufficient_historical_data)
    await runner.run_test("カスタム検証統合", test_custom_validator_integration)
    await runner.run_test("複数カスタム検証", test_multiple_custom_validators)
    
    # 結果表示
    runner.print_summary()
    
    # 使用例デモ
    print("\n" + "=" * 60)
    print("📋 実際の使用例デモ")
    print("=" * 60)
    
    validator = SymbolEarlyFailValidator()
    
    # カスタムルール追加
    validator.add_custom_validator(custom_meme_coin_validator)
    validator.add_custom_validator(custom_symbol_length_validator)
    
    print(f"✅ バリデータ初期化完了")
    print(f"   設定ファイル: {validator.config_path}")
    print(f"   必要履歴日数: {validator.config['required_historical_days']}日")
    print(f"   サポート取引所: {validator.config['supported_exchanges']}")
    print(f"   カスタムルール数: {len(validator.custom_validators)}")
    
    return runner.failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 すべてのテストが成功しました！")
        sys.exit(0)
    else:
        print("\n⚠️ 一部のテストが失敗しました")
        sys.exit(1)