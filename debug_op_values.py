#!/usr/bin/env python3
"""
OP信頼度・レバレッジ値の異常調査

信頼度90%、support_strength 153.87などの異常値を詳細調査
"""

import sys
import logging
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

# ロギング設定 - DEBUG以上を表示
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator

def investigate_op_values():
    """OP値の異常を詳細調査"""
    print("🔍 OP信頼度・レバレッジ異常値調査")
    print("=" * 60)
    
    try:
        print("1️⃣ HighLeverageBotOrchestratorを初期化中...")
        bot = HighLeverageBotOrchestrator()
        
        print("\n2️⃣ OP分析を実行中（詳細ログ出力）...")
        print("=" * 60)
        
        # 詳細ログを有効化
        for logger_name in ['engines.leverage_decision_engine', 'adapters', 'engines']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
        
        result = bot.analyze_symbol('OP', '15m', 'Aggressive_ML')
        
        print("=" * 60)
        print("\n3️⃣ 結果分析:")
        
        if result:
            print(f"   レバレッジ: {result.get('leverage', 'N/A')}")
            print(f"   信頼度: {result.get('confidence', 'N/A')}%")
            print(f"   リスクリワード比: {result.get('risk_reward_ratio', 'N/A')}")
            print(f"   現在価格: {result.get('current_price', 'N/A')}")
            
            # 異常値の分析
            confidence = result.get('confidence', 0)
            leverage = result.get('leverage', 0)
            
            print("\n4️⃣ 異常値分析:")
            
            # 信頼度チェック
            if confidence > 80:
                print(f"   🚨 信頼度異常: {confidence}% (通常は0-100%、80%超は稀)")
                print("      → 信頼度計算ロジックに問題の可能性")
            
            # レバレッジと信頼度の関係チェック
            if confidence > 80 and leverage < 2.0:
                print(f"   🚨 レバレッジ/信頼度不整合: 信頼度{confidence}%なのにレバレッジ{leverage}x")
                print("      → レバレッジ計算ロジックに問題の可能性")
            
            # サポート強度チェック（ログから読み取り）
            print("\n5️⃣ 計算要素の妥当性:")
            print("   support_strength値をログで確認してください")
            print("   - 正常範囲: 0.0-1.0")
            print("   - 異常値: 100超")
            
        else:
            print("\n3️⃣ 分析結果: None (エラー発生)")
            
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📋 調査観点:")
    print("1. support_strength値が0-1の範囲を超えていないか")
    print("2. confidence_factors各要素が正常範囲にあるか") 
    print("3. normalized_factors処理が正常に動作しているか")
    print("4. market_risk_factor計算が正常か")

def analyze_confidence_calculation_details():
    """信頼度計算の詳細分析"""
    print("\n" + "🔬 信頼度計算詳細分析")
    print("=" * 60)
    
    try:
        # 直接エンジンを呼び出して詳細確認
        from engines.leverage_decision_engine import CoreLeverageDecisionEngine
        from interfaces.data_types import MarketContext, SupportResistanceLevel, BreakoutPrediction, BTCCorrelationRisk
        from datetime import datetime
        
        engine = CoreLeverageDecisionEngine()
        
        # モックデータでテスト
        print("📊 モックデータでの信頼度計算テスト:")
        
        now = datetime.now()
        support_levels = [
            SupportResistanceLevel(
                price=1.5, strength=0.8, touch_count=3,  # 正常な強度
                level_type='support', first_touch=now, last_touch=now,
                volume_at_level=1000.0, distance_from_current=5.0
            )
        ]
        
        resistance_levels = [
            SupportResistanceLevel(
                price=1.7, strength=0.7, touch_count=2,
                level_type='resistance', first_touch=now, last_touch=now,
                volume_at_level=800.0, distance_from_current=5.0
            )
        ]
        
        breakout_predictions = [
            BreakoutPrediction(
                level=support_levels[0],
                breakout_probability=0.3, bounce_probability=0.7,
                prediction_confidence=0.8, predicted_price_target=1.6,
                time_horizon_minutes=60, model_name='test_model'
            )
        ]
        
        btc_correlation_risk = BTCCorrelationRisk(
            symbol='OP', btc_drop_scenario=-10.0,
            predicted_altcoin_drop={60: -5.0, 120: -10.0},
            correlation_strength=0.8, risk_level='MEDIUM',
            liquidation_risk={60: 0.1, 120: 0.2}
        )
        
        market_context = MarketContext(
            current_price=1.6, volume_24h=1000000.0, volatility=0.02,
            trend_direction='BULLISH', market_phase='MARKUP', timestamp=now
        )
        
        # 正常データでの計算
        print("   正常データでの計算実行...")
        result = engine.calculate_safe_leverage(
            symbol='TEST_OP',
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            breakout_predictions=breakout_predictions,
            btc_correlation_risk=btc_correlation_risk,
            market_context=market_context
        )
        
        print(f"   → レバレッジ: {result.recommended_leverage}")
        print(f"   → 信頼度: {result.confidence_level}")
        
        # 異常な強度でのテスト
        print("\n📊 異常データでの信頼度計算テスト:")
        support_levels[0].strength = 153.87  # 異常値を設定
        
        result2 = engine.calculate_safe_leverage(
            symbol='TEST_OP_ABNORMAL',
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            breakout_predictions=breakout_predictions,
            btc_correlation_risk=btc_correlation_risk,
            market_context=market_context
        )
        
        print(f"   → レバレッジ: {result2.recommended_leverage}")
        print(f"   → 信頼度: {result2.confidence_level}")
        print(f"   → 信頼度が異常に高い場合、正規化処理に問題あり")
        
    except Exception as e:
        print(f"❌ 詳細分析エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    investigate_op_values()
    analyze_confidence_calculation_details()