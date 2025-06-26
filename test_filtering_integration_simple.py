#!/usr/bin/env python3
"""
フィルタリングシステム統合の簡単な動作確認
"""

import asyncio
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_filtering_integration():
    """フィルタリング統合の簡単な動作確認"""
    try:
        print("🧪 フィルタリングシステム統合テスト開始")
        
        # AutoSymbolTrainerのインポートと初期化
        from auto_symbol_training import AutoSymbolTrainer
        print("✅ AutoSymbolTrainer インポート成功")
        
        trainer = AutoSymbolTrainer()
        print("✅ AutoSymbolTrainer 初期化成功")
        
        # Early Fail検証のテスト
        print("\n🔍 Early Fail検証テスト")
        test_symbol = "BTC"  # 実際に存在する銘柄でテスト
        result = await trainer._run_early_fail_validation(test_symbol)
        print(f"検証結果: {result.passed}")
        
        # FilteringFrameworkのテスト
        print("\n🚀 FilteringFramework事前検証テスト")
        test_configs = [
            {'symbol': test_symbol, 'timeframe': '1m', 'strategy': 'Conservative_ML'},
            {'symbol': test_symbol, 'timeframe': '5m', 'strategy': 'Conservative_ML'},
            {'symbol': test_symbol, 'timeframe': '1h', 'strategy': 'Aggressive_Traditional'},
            {'symbol': test_symbol, 'timeframe': '15m', 'strategy': 'Full_ML'},
        ]
        
        filtered_configs = await trainer._apply_filtering_framework(
            test_configs, test_symbol, "test-exec-001"
        )
        
        print(f"フィルタリング前: {len(test_configs)} 設定")
        print(f"フィルタリング後: {len(filtered_configs)} 設定")
        
        # フィルタリング結果の詳細
        print("\n📊 フィルタリング結果:")
        for config in test_configs:
            if config in filtered_configs:
                status = "✅ 通過"
            else:
                status = "❌ 除外"
            print(f"  {status}: {config['strategy']}-{config['timeframe']}")
        
        print("\n🎉 フィルタリングシステム統合テスト完了!")
        return True
        
    except Exception as e:
        print(f"❌ テスト中にエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_filtering_integration())
    exit(0 if success else 1)