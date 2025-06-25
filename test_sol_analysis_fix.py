#!/usr/bin/env python3
"""
SOL分析で修正効果をテスト
実際のデータで戦略別独立実行を確認
"""

import asyncio
import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer


async def test_sol_analysis_fix():
    """SOL分析で修正効果をテスト"""
    print("🧪 SOL分析修正効果テスト")
    print("=" * 60)
    
    # AutoSymbolTrainerのインスタンス作成
    trainer = AutoSymbolTrainer()
    
    # テスト用戦略設定（3つの戦略）
    strategy_configs = [
        {'id': 4, 'strategy': 'Aggressive_ML', 'timeframe': '15m'},
        {'id': 5, 'strategy': 'Aggressive_ML', 'timeframe': '1h'},
        {'id': 7, 'strategy': 'Balanced', 'timeframe': '15m'}
    ]
    
    # カスタム期間設定
    custom_period_settings = {
        'mode': 'custom',
        'start_date': '2025-04-10T21:04',
        'end_date': '2025-06-25T21:04'
    }
    
    print(f"📅 カスタム期間: {custom_period_settings['start_date']} ～ {custom_period_settings['end_date']}")
    print(f"🎯 テスト戦略: {len(strategy_configs)}個")
    for i, config in enumerate(strategy_configs):
        print(f"  {i+1}. {config['strategy']} - {config['timeframe']}")
    
    try:
        print("\n🚀 SOL分析開始...")
        
        # SOL分析を実行
        execution_id = await trainer.add_symbol_with_training(
            symbol='SOL',
            selected_strategies=[4, 5, 7],  # Aggressive_ML-15m, Aggressive_ML-1h, Balanced-15m
            strategy_configs=strategy_configs,
            custom_period_settings=custom_period_settings
        )
        
        print(f"✅ 分析完了: {execution_id}")
        
        # 実行状況の確認
        status = trainer.get_execution_status(execution_id)
        if status:
            print(f"📊 最終ステータス: {status['status']}")
            print(f"📋 完了ステップ: {len(status.get('steps', []))}")
        
        # 分析結果の確認
        analysis_results = trainer._verify_analysis_results('SOL', execution_id)
        print(f"🔍 分析結果確認: {analysis_results}")
        
        print("\n" + "=" * 60)
        print("✅ SOL分析修正効果テスト完了")
        print("期待される結果:")
        print("  - 一部戦略が失敗しても他戦略は継続実行")
        print("  - 各戦略で独立したエラーハンドリング")
        print("  - 時間足重複（15m×2）の適切な処理")
        
        return True
        
    except Exception as e:
        print(f"❌ SOL分析エラー: {e}")
        import traceback
        print(f"詳細: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_sol_analysis_fix())
    print(f"\n{'✅ テスト成功' if success else '❌ テスト失敗'}")
    sys.exit(0 if success else 1)