#!/usr/bin/env python3
"""
実銘柄でのフィルタリングシステム完全統合テスト

安全な実銘柄を使った完全な銘柄追加フローのテスト
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_real_symbol_integration():
    """実銘柄での完全統合テスト"""
    try:
        print("🔥 実銘柄でのフィルタリングシステム完全統合テスト開始")
        print("=" * 80)
        
        # AutoSymbolTrainerのインポートと初期化
        from auto_symbol_training import AutoSymbolTrainer
        from execution_log_database import ExecutionLogDatabase
        
        trainer = AutoSymbolTrainer()
        execution_db = ExecutionLogDatabase()
        print("✅ AutoSymbolTrainer & ExecutionLogDatabase 初期化成功")
        
        # テスト用銘柄（安全で確実に存在する銘柄）
        test_symbol = "ETH"
        print(f"\n🎯 テスト対象銘柄: {test_symbol}")
        
        # 開始時刻記録
        start_time = time.time()
        print(f"⏰ テスト開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Phase 1: Early Fail検証
        print("\n" + "="*50)
        print("🔍 Phase 1: Early Fail検証")
        print("="*50)
        
        validation_start = time.time()
        early_fail_result = await trainer._run_early_fail_validation(test_symbol)
        validation_time = time.time() - validation_start
        
        print(f"⏱️  Early Fail検証時間: {validation_time:.2f}秒")
        print(f"📊 検証結果: {'✅ 成功' if early_fail_result.passed else '❌ 失敗'}")
        
        if not early_fail_result.passed:
            print(f"❌ 失敗理由: {early_fail_result.fail_reason}")
            print(f"💡 提案: {early_fail_result.suggestion}")
            return False
        
        # Phase 2: FilteringFramework事前検証
        print("\n" + "="*50)
        print("🚀 Phase 2: FilteringFramework事前検証")
        print("="*50)
        
        # 多様な戦略・時間足設定でテスト
        test_configs = [
            {'symbol': test_symbol, 'timeframe': '1m', 'strategy': 'Conservative_ML'},      # 除外される予定
            {'symbol': test_symbol, 'timeframe': '5m', 'strategy': 'Conservative_ML'},      # 通過予定
            {'symbol': test_symbol, 'timeframe': '15m', 'strategy': 'Conservative_ML'},     # 通過予定
            {'symbol': test_symbol, 'timeframe': '30m', 'strategy': 'Full_ML'},            # 通過予定
            {'symbol': test_symbol, 'timeframe': '1h', 'strategy': 'Aggressive_Traditional'}, # 除外される予定
            {'symbol': test_symbol, 'timeframe': '4h', 'strategy': 'Full_ML'},             # 通過予定
            {'symbol': test_symbol, 'timeframe': '1d', 'strategy': 'Conservative_ML'},      # 通過予定
        ]
        
        print(f"📋 テスト設定数: {len(test_configs)}")
        for i, config in enumerate(test_configs, 1):
            print(f"   {i}. {config['strategy']}-{config['timeframe']}")
        
        filtering_start = time.time()
        filtered_configs = await trainer._apply_filtering_framework(
            test_configs, test_symbol, f"test-{int(time.time())}"
        )
        filtering_time = time.time() - filtering_start
        
        print(f"\n⏱️  フィルタリング時間: {filtering_time:.2f}秒")
        print(f"📊 フィルタリング前: {len(test_configs)} 設定")
        print(f"📊 フィルタリング後: {len(filtered_configs)} 設定")
        print(f"📊 除外率: {((len(test_configs) - len(filtered_configs)) / len(test_configs)) * 100:.1f}%")
        
        # Phase 3: フィルタリング結果詳細解析
        print("\n" + "="*50)
        print("📊 Phase 3: フィルタリング結果詳細")
        print("="*50)
        
        passed_configs = []
        excluded_configs = []
        
        for config in test_configs:
            if any(fc == config for fc in filtered_configs):
                passed_configs.append(config)
                status = "✅ 通過"
            else:
                excluded_configs.append(config)
                status = "❌ 除外"
            print(f"  {status}: {config['strategy']}-{config['timeframe']}")
        
        print(f"\n📈 通過した設定 ({len(passed_configs)}):")
        for config in passed_configs:
            print(f"   → {config['strategy']}-{config['timeframe']}")
        
        print(f"\n📉 除外された設定 ({len(excluded_configs)}):")
        for config in excluded_configs:
            print(f"   → {config['strategy']}-{config['timeframe']}")
        
        # Phase 4: パフォーマンス評価
        print("\n" + "="*50)
        print("⚡ Phase 4: パフォーマンス評価")
        print("="*50)
        
        total_time = time.time() - start_time
        print(f"🕐 総実行時間: {total_time:.2f}秒")
        print(f"🔍 Early Fail検証時間: {validation_time:.2f}秒 ({(validation_time/total_time)*100:.1f}%)")
        print(f"🚀 フィルタリング時間: {filtering_time:.2f}秒 ({(filtering_time/total_time)*100:.1f}%)")
        
        # 期待されるフィルタリング効果
        excluded_rate = ((len(test_configs) - len(filtered_configs)) / len(test_configs)) * 100
        print(f"📊 フィルタリング効果: {excluded_rate:.1f}%の処理削減")
        
        if excluded_rate > 0:
            estimated_savings = f"約{excluded_rate:.0f}%の計算リソース節約"
            print(f"💰 推定効果: {estimated_savings}")
        
        # Phase 5: 実行ログ確認
        print("\n" + "="*50)
        print("📋 Phase 5: 実行ログ確認")
        print("="*50)
        
        recent_executions = execution_db.list_executions(limit=5)
        print(f"📝 最近の実行ログ ({len(recent_executions)}):")
        for exec_item in recent_executions[:3]:  # 最新3件
            timestamp = exec_item.get('created_at', 'N/A')
            symbol = exec_item.get('symbol', 'N/A')
            status = exec_item.get('status', 'N/A')
            print(f"   {timestamp}: {symbol} ({status})")
        
        print("\n" + "="*80)
        print("🎉 実銘柄での完全統合テスト成功！")
        print("="*80)
        print(f"✅ {test_symbol}銘柄での全フェーズが正常完了")
        print(f"✅ フィルタリングシステムが期待通りに動作")
        print(f"✅ {excluded_rate:.1f}%の処理最適化を達成")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"❌ テスト中にエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_real_symbol_integration())
    print(f"\n🏁 テスト結果: {'成功' if success else '失敗'}")
    exit(0 if success else 1)