#!/usr/bin/env python3
"""
実際の銘柄検証での目立つサーバーログのデモ
"""

import asyncio
from unittest.mock import patch, AsyncMock

from symbol_early_fail_validator import SymbolEarlyFailValidator, EarlyFailResult


async def demo_real_symbol_validation():
    """実際の銘柄検証のシミュレーション"""
    print("🎯 実際の銘柄検証シミュレーション - BTCの検証")
    print("=" * 60)
    
    # デフォルト設定（フルバナー）を使用
    validator = SymbolEarlyFailValidator()
    
    # すべての検証が成功するケースをシミュレート
    with patch.object(validator, '_check_symbol_existence') as mock_exist, \
         patch.object(validator, '_check_exchange_support') as mock_exchange, \
         patch.object(validator, '_check_api_connection_timeout') as mock_timeout, \
         patch.object(validator, '_check_current_exchange_active_status') as mock_active, \
         patch.object(validator, '_check_system_resources') as mock_resource, \
         patch.object(validator, '_check_strict_data_quality') as mock_quality, \
         patch.object(validator, '_check_historical_data_availability') as mock_history:
        
        # 全て成功をシミュレート（メタデータ付き）
        mock_exist.return_value = EarlyFailResult('BTC', True, metadata={"exchange": "gateio"})
        mock_exchange.return_value = EarlyFailResult('BTC', True, metadata={"supported": True})
        mock_timeout.return_value = EarlyFailResult('BTC', True, metadata={"response_time": "2.3秒"})
        mock_active.return_value = EarlyFailResult('BTC', True, metadata={"is_active": True, "volume_24h": 1000000})
        mock_resource.return_value = EarlyFailResult('BTC', True, metadata={"cpu_percent": "45.2%", "memory_percent": "62.1%", "free_disk_gb": "15.3GB"})
        mock_quality.return_value = EarlyFailResult('BTC', True, metadata={"data_completeness": "97.5%", "data_points": 703})
        mock_history.return_value = EarlyFailResult('BTC', True, metadata={"historical_data_available": True})
        
        print("⚡ Early Fail検証を実行中...")
        print()
        
        # 実際の検証実行（目立つログが出力される）
        result = await validator.validate_symbol('BTC')
        
        print(f"🔥 検証結果: {'成功' if result.passed else '失敗'}")
        if result.passed:
            print("✅ BTCは全ての品質基準を満たし、分析処理の実行が承認されました")
            print("📈 この後、マルチプロセスでの本格的な分析が開始されます")
        
        return result


async def demo_different_symbols():
    """異なる銘柄での検証ログのデモ"""
    print("\n" + "=" * 60)
    print("🔄 複数銘柄での検証ログデモ")
    print("=" * 60)
    
    symbols = ['ETH', 'SOL', 'AVAX']
    
    for symbol in symbols:
        print(f"\n🎯 {symbol}の検証開始...")
        
        validator = SymbolEarlyFailValidator()
        
        # 成功ケースをシミュレート
        with patch.object(validator, '_check_symbol_existence', return_value=EarlyFailResult(symbol, True)), \
             patch.object(validator, '_check_exchange_support', return_value=EarlyFailResult(symbol, True)), \
             patch.object(validator, '_check_api_connection_timeout', return_value=EarlyFailResult(symbol, True)), \
             patch.object(validator, '_check_current_exchange_active_status', return_value=EarlyFailResult(symbol, True)), \
             patch.object(validator, '_check_system_resources', return_value=EarlyFailResult(symbol, True)), \
             patch.object(validator, '_check_strict_data_quality', return_value=EarlyFailResult(symbol, True)), \
             patch.object(validator, '_check_historical_data_availability', return_value=EarlyFailResult(symbol, True)):
            
            result = await validator.validate_symbol(symbol)
            print(f"✅ {symbol}: 検証完了")


async def main():
    """メインデモ実行"""
    print("🚀 Early Fail検証成功時の目立つサーバーログ - 実演デモ")
    print("=" * 80)
    print("このデモでは、実際の銘柄検証でどのような目立つログが出力されるかを確認できます")
    print("=" * 80)
    
    # 1. 詳細な単一銘柄検証
    await demo_real_symbol_validation()
    
    # 2. 複数銘柄での連続検証
    await demo_different_symbols()
    
    print("\n" + "=" * 80)
    print("🎉 目立つサーバーログのデモ完了！")
    print("=" * 80)
    print("📋 実装されたログ機能:")
    print("  ✅ フルバナー形式の詳細ログ（デフォルト）")
    print("  ✅ 検証項目8つの明確な表示")
    print("  ✅ 時刻付きの完了メッセージ")
    print("  ✅ 標準出力への重要通知")
    print("  ✅ システムログファイルへの記録")
    print()
    print("⚙️ 設定カスタマイズ:")
    print("  • banner_style: full, compact, minimal")
    print("  • success_log_level: info, success, warning")
    print("  • include_system_notification: true/false")
    print("  • enable_success_highlight: true/false")


if __name__ == "__main__":
    asyncio.run(main())