"""
高精度ML予測器のテストスクリプト

実際の市場データを使用して57%から70%以上への精度向上をテストします。
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines import HighLeverageBotOrchestrator
from adapters.enhanced_ml_adapter import EnhancedMLPredictorAdapter
from data_fetcher import fetch_data

def test_enhanced_ml_system():
    """高精度MLシステムのテスト"""
    
    print("🚀 高精度ML予測システムのテスト開始")
    print("="*60)
    
    # 1. オーケストレーターの初期化
    orchestrator = HighLeverageBotOrchestrator(use_default_plugins=False)
    
    # 2. 高精度ML予測器をセット
    enhanced_predictor = EnhancedMLPredictorAdapter()
    orchestrator.set_breakout_predictor(enhanced_predictor)
    
    # 3. 他のプラグインは既存のものを使用
    from adapters import ExistingSupportResistanceAdapter, ExistingBTCCorrelationAdapter
    from engines.leverage_decision_engine import SimpleMarketContextAnalyzer, CoreLeverageDecisionEngine
    
    orchestrator.set_support_resistance_analyzer(ExistingSupportResistanceAdapter())
    orchestrator.set_btc_correlation_analyzer(ExistingBTCCorrelationAdapter())
    orchestrator.set_market_context_analyzer(SimpleMarketContextAnalyzer())
    orchestrator.set_leverage_decision_engine(CoreLeverageDecisionEngine())
    
    print("✅ 高精度ML予測器を統合完了")
    
    # 4. テスト対象シンボル
    test_symbols = ['HYPE', 'SOL']
    
    for symbol in test_symbols:
        print(f"\n📊 {symbol} で高精度ML予測をテスト中...")
        print("-"*40)
        
        try:
            # レバレッジ分析実行
            recommendation = orchestrator.analyze_leverage_opportunity(symbol, '1h')
            
            # 結果表示
            print(f"💰 現在価格: {recommendation.market_conditions.current_price:.4f}")
            print(f"🎪 推奨レバレッジ: {recommendation.recommended_leverage:.1f}x")
            print(f"🎯 信頼度: {recommendation.confidence_level*100:.1f}%")
            print(f"⚖️ リスクリワード比: {recommendation.risk_reward_ratio:.2f}")
            
            # ML予測器の詳細情報
            if hasattr(enhanced_predictor, 'get_performance_summary'):
                summary = enhanced_predictor.get_performance_summary()
                print(f"🤖 ML予測器状態: {summary.get('status', 'unknown')}")
                if 'latest_auc' in summary:
                    auc = summary['latest_auc']
                    print(f"📈 予測精度(AUC): {auc:.3f}")
                    
                    # 改善率計算
                    baseline = 0.57
                    if auc > baseline:
                        improvement = (auc - baseline) / baseline * 100
                        print(f"🚀 精度改善: +{improvement:.1f}% (ベースライン57%から)")
                    else:
                        decline = (baseline - auc) / baseline * 100
                        print(f"📉 精度低下: -{decline:.1f}% (ベースライン57%から)")
            
        except Exception as e:
            print(f"❌ {symbol}のテストでエラー: {e}")
    
    print("\n" + "="*60)
    print("🎯 高精度ML予測システムのテスト完了")

def compare_ml_predictions():
    """既存MLと高精度MLの予測を比較"""
    
    print("\n🔬 ML予測器比較テスト開始")
    print("="*60)
    
    # データ取得
    symbol = 'HYPE'
    data = fetch_data(symbol, '1h', 500)
    
    if data.empty:
        print("❌ データ取得に失敗")
        return
    
    print(f"📊 比較用データ: {len(data)}件")
    
    # サポレジレベル検出
    from adapters import ExistingSupportResistanceAdapter
    sr_analyzer = ExistingSupportResistanceAdapter()
    levels = sr_analyzer.find_levels(data)
    
    if not levels:
        print("❌ サポレジレベルが検出されませんでした")
        return
    
    print(f"📍 検出レベル: {len(levels)}個")
    
    # 既存ML予測器
    from adapters import ExistingMLPredictorAdapter
    existing_predictor = ExistingMLPredictorAdapter()
    
    # 高精度ML予測器
    enhanced_predictor = EnhancedMLPredictorAdapter()
    
    # 両方を訓練
    print("\n🏋️ ML予測器訓練中...")
    
    existing_trained = existing_predictor.train_model(data, levels)
    enhanced_trained = enhanced_predictor.train_model(data, levels)
    
    print(f"既存ML訓練結果: {'✅ 成功' if existing_trained else '❌ 失敗'}")
    print(f"高精度ML訓練結果: {'✅ 成功' if enhanced_trained else '❌ 失敗'}")
    
    if not (existing_trained and enhanced_trained):
        print("⚠️ 一部のモデル訓練に失敗しました")
        return
    
    # 予測比較
    print("\n🎯 予測精度比較:")
    
    # 既存ML精度
    existing_accuracy = existing_predictor.get_model_accuracy()
    existing_auc = existing_accuracy.get('accuracy', 0.0)
    
    # 高精度ML精度  
    enhanced_accuracy = enhanced_predictor.get_model_accuracy()
    enhanced_auc = enhanced_accuracy.get('ensemble_auc', 0.0)
    
    print(f"既存ML精度:  {existing_auc:.3f}")
    print(f"高精度ML精度: {enhanced_auc:.3f}")
    
    if enhanced_auc > existing_auc:
        improvement = (enhanced_auc - existing_auc) / existing_auc * 100
        print(f"🚀 改善: +{improvement:.1f}%")
    else:
        decline = (existing_auc - enhanced_auc) / existing_auc * 100
        print(f"📉 低下: -{decline:.1f}%")
    
    # 個別予測テスト
    print("\n🔍 個別予測比較:")
    test_level = levels[0]  # 最初のレベルでテスト
    
    existing_pred = existing_predictor.predict_breakout(data, test_level)
    enhanced_pred = enhanced_predictor.predict_breakout(data, test_level)
    
    print(f"テストレベル: {test_level.level_type} at {test_level.price:.4f}")
    print(f"既存ML予測:   ブレイクアウト{existing_pred.breakout_probability:.2f}, 信頼度{existing_pred.prediction_confidence:.2f}")
    print(f"高精度ML予測: ブレイクアウト{enhanced_pred.breakout_probability:.2f}, 信頼度{enhanced_pred.prediction_confidence:.2f}")
    
    print("\n🎉 ML予測器比較テスト完了")

if __name__ == "__main__":
    # 高精度MLシステムのテスト
    test_enhanced_ml_system()
    
    # ML予測器比較テスト
    compare_ml_predictions()