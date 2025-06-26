#!/usr/bin/env python3
"""
progress_tracker 強制更新ツール
実際の分析が完了したexecution_idに対してprogress_trackerを手動更新
"""

import sys
import os
from datetime import datetime

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from web_dashboard.analysis_progress import progress_tracker, SupportResistanceResult, MLPredictionResult, MarketContextResult, LeverageDecisionResult
    print("✅ progress_tracker インポート成功")
except ImportError as e:
    print(f"❌ progress_tracker インポートエラー: {e}")
    sys.exit(1)

def update_sol_analysis():
    """SOL分析の進捗を手動更新"""
    
    # 現在のSOL execution_idを直接指定
    execution_id = "symbol_addition_20250626_044614_bb9756e4"
    
    print(f"🎯 指定execution_idでSOL進捗更新: {execution_id}")
    
    # データが存在するか確認
    recent = progress_tracker.get_all_recent(24)
    existing = [r for r in recent if r.execution_id == execution_id]
    
    if existing:
        print(f"   既存データ確認: {existing[0].symbol} / {existing[0].current_stage}")
    else:
        print("   既存データなし - 新規作成します")
        progress_tracker.start_analysis("SOL", execution_id)
    
    print(f"🎯 SOL分析進捗更新開始")
    
    # Support/Resistance検出成功をシミュレート
    print("📊 Support/Resistance検出結果を更新...")
    sr_result = SupportResistanceResult(
        status="success",
        supports_count=5,
        resistances_count=5,
        supports=[
            {"price": 142.26, "strength": 0.680, "touch_count": 13},
            {"price": 144.79, "strength": 0.638, "touch_count": 15},
            {"price": 130.30, "strength": 0.608, "touch_count": 4},
            {"price": 126.05, "strength": 0.583, "touch_count": 4},
            {"price": 147.38, "strength": 0.562, "touch_count": 11}
        ],
        resistances=[
            {"price": 147.91, "strength": 0.737, "touch_count": 22},
            {"price": 153.37, "strength": 0.590, "touch_count": 12},
            {"price": 141.60, "strength": 0.488, "touch_count": 3},
            {"price": 158.05, "strength": 0.455, "touch_count": 6},
            {"price": 150.25, "strength": 0.366, "touch_count": 7}
        ]
    )
    progress_tracker.update_support_resistance(execution_id, sr_result)
    print("✅ Support/Resistance更新完了")
    
    # ML予測失敗をシミュレート
    print("📊 ML予測結果を更新...")
    ml_result = MLPredictionResult(
        status="failed",
        predictions_count=0,
        confidence=0.0,
        error_message="Insufficient training data"
    )
    progress_tracker.update_ml_prediction(execution_id, ml_result)
    print("✅ ML予測更新完了")
    
    # Market Context成功をシミュレート
    print("📊 Market Context結果を更新...")
    market_result = MarketContextResult(
        status="success",
        trend_direction="neutral",
        market_phase="consolidation"
    )
    progress_tracker.update_market_context(execution_id, market_result)
    print("✅ Market Context更新完了")
    
    # Leverage Decision失敗をシミュレート
    print("📊 Leverage Decision結果を更新...")
    leverage_result = LeverageDecisionResult(
        status="failed",
        recommended_leverage=0.0,
        confidence_level=0.0,
        risk_reward_ratio=0.0,
        error_message="No valid trading signal generated"
    )
    progress_tracker.update_leverage_decision(execution_id, leverage_result)
    print("✅ Leverage Decision更新完了")
    
    # 最終的に失敗として完了
    print("📊 分析完了を更新...")
    progress_tracker.fail_analysis(execution_id, "leverage_decision", "All strategies resulted in no signal")
    print("✅ 分析完了更新完了")
    
    print(f"\n🎉 SOL分析進捗更新完了: {execution_id}")

if __name__ == "__main__":
    print("🔧 progress_tracker強制更新ツール")
    print("=" * 50)
    update_sol_analysis()
    print("\n📊 更新後の状態を確認してください:")
    print("   http://localhost:5001/analysis-progress")