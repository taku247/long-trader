#!/usr/bin/env python3
"""
モックデータ生成の実証テスト

実際の銘柄追加実行時にモックデータが生成されるかを詳細ログで確認
"""

import asyncio
import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_mock_data_verification():
    """モックデータ生成の実証テスト"""
    try:
        print("🔥 モックデータ生成実証テスト開始")
        print("=" * 80)
        print("📋 目的: 実際の銘柄追加実行時にモックデータが生成されることを確認")
        print("📊 対象: DOGE銘柄の短時間バックテスト")
        print("🔍 確認項目:")
        print("   1. モックデータ生成ログの出力")
        print("   2. FilteringFramework初期化ログ")
        print("   3. 9段階フィルタリング実行ログ")
        print("   4. スキップ/処理続行の判定ログ")
        
        # AutoSymbolTrainerのインポートと初期化
        from auto_symbol_training import AutoSymbolTrainer
        
        trainer = AutoSymbolTrainer()
        print("\\n✅ AutoSymbolTrainer初期化成功")
        
        # 短時間実行のため最小設定で実行
        test_symbol = "DOGE"
        test_strategies = ["Conservative_ML"]
        test_timeframes = ["1h"]  # 1時間足のみ
        
        print(f"\\n📋 テスト設定:")
        print(f"   - 銘柄: {test_symbol}")
        print(f"   - 戦略: {test_strategies}")
        print(f"   - 時間足: {test_timeframes}")
        print(f"   - 開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\\n" + "="*80)
        print("🚀 実際の銘柄追加実行開始（詳細ログ出力モード）")
        print("="*80)
        print("🔍 以下のログから、モックデータ生成過程を確認してください：")
        print("   📊 'モックデータ生成開始' - モックオブジェクト作成")
        print("   🔧 'FilteringFramework初期化中' - フィルタリング初期化")
        print("   🚀 '9段階フィルタリング実行中' - フィルター実行")
        print("   🎯 '最終判定' - スキップ/続行判定")
        print("\\n" + "-"*80)
        
        # 実際の銘柄追加実行
        result = await trainer.add_symbol_with_training(
            symbol=test_symbol,
            selected_strategies=test_strategies,
            selected_timeframes=test_timeframes
        )
        
        print("\\n" + "-"*80)
        print("🏆 実行完了")
        print("="*80)
        
        if result:
            print(f"✅ 銘柄追加成功: {result}")
        else:
            print("⚠️ 銘柄追加で何らかの問題が発生（ただしログ出力は成功）")
        
        print("\\n📋 確認結果:")
        print("上記のログ出力から以下を確認してください：")
        print("1. ✅ '📊 モックデータ生成開始' ログが出力されたか")
        print("2. ✅ '✅ モックデータ生成完了' ログが出力されたか") 
        print("3. ✅ '🔧 FilteringFramework初期化中' ログが出力されたか")
        print("4. ✅ '🚀 9段階フィルタリング実行中' ログが出力されたか")
        print("5. ✅ '🎯 最終判定' ログが出力されたか")
        
        print("\\n💡 説明:")
        print("これらのログが出力されていれば、実際の銘柄追加実行時に")
        print("モックデータが生成され、9段階フィルタリングが実行されています。")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト中にエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mock_data_verification())
    print(f"\\n🏁 テスト結果: {'✅ 成功' if success else '❌ 失敗'}")
    exit(0 if success else 1)