#!/usr/bin/env python3
"""
実際の銘柄での簡単な動作確認テスト
"""

import asyncio
import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer


async def test_real_symbol():
    """実際の銘柄でのテスト実行"""
    
    print("🧪 実際の銘柄での動作確認テスト開始")
    print("=" * 60)
    
    # テスト用の銘柄（SOLは確実に存在する）
    test_symbol = "SOL"
    
    # AutoSymbolTrainerの初期化
    trainer = AutoSymbolTrainer()
    
    try:
        # 実行IDを生成
        execution_id = datetime.now().strftime('%Y%m%d_%H%M%S_test')
        
        print(f"📊 テスト銘柄: {test_symbol}")
        print(f"📅 実行ID: {execution_id}")
        print(f"🎯 選択戦略: Balanced_Conservative のみ")
        print(f"⏰ 選択時間足: 1h のみ")
        print("=" * 60)
        
        # 限定的な設定でテスト実行（1戦略・1時間足のみ）
        result_id = await trainer.add_symbol_with_training(
            symbol=test_symbol,
            execution_id=execution_id,
            selected_strategies=["Balanced_Conservative"],
            selected_timeframes=["1h"],
            custom_period_settings={
                "mode": "custom",
                "period_days": 7  # 7日間のみ
            }
        )
        
        print(f"\n✅ テスト完了!")
        print(f"📊 実行ID: {result_id}")
        
        # 分析結果の確認
        from scalable_analysis_system import ScalableAnalysisSystem
        analysis_system = ScalableAnalysisSystem("large_scale_analysis")
        
        # 結果を取得
        results = analysis_system.query_analyses(
            filters={
                'symbol': test_symbol,
                'execution_id': result_id
            }
        )
        
        if results and len(results) > 0:
            print(f"\n📊 分析結果:")
            for result in results:
                print(f"   - 時間足: {result.get('timeframe')}")
                print(f"   - 戦略: {result.get('config')}")
                print(f"   - 総取引数: {result.get('total_trades', 0)}")
                print(f"   - シャープレシオ: {result.get('sharpe_ratio', 0):.2f}")
                print()
        
        # FilteringFrameworkの統計確認
        if hasattr(analysis_system, 'filtering_framework') and analysis_system.filtering_framework:
            stats = analysis_system.filtering_framework.get_statistics()
            efficiency = stats.get_efficiency_metrics()
            
            print("\n📊 フィルタリング統計:")
            print(f"   - 総評価数: {stats.total_evaluations}")
            print(f"   - 有効取引数: {stats.valid_trades}")
            print(f"   - 通過率: {efficiency.get('pass_rate', 0):.2f}%")
            print(f"   - 除外率: {efficiency.get('exclusion_rate', 0):.2f}%")
        
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n🎉 テスト終了")


if __name__ == "__main__":
    asyncio.run(test_real_symbol())