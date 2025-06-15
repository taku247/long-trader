#!/usr/bin/env python3
"""
統合設定システムの動作確認テスト

統合設定（trading_conditions.json）が正しく適用されることを確認
"""

import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_unified_config_integration():
    """統合設定の動作確認"""
    print("🔧 統合設定システム動作確認テスト")
    print("=" * 60)
    
    from config.unified_config_manager import UnifiedConfigManager
    config_manager = UnifiedConfigManager()
    
    # 1. 戦略別の条件差異を確認
    print("\n📊 戦略別エントリー条件の比較:")
    print("-" * 50)
    
    timeframe = "5m"
    strategies = ["Conservative_ML", "Aggressive_ML", "Balanced"]
    
    for strategy in strategies:
        conditions = config_manager.get_entry_conditions(timeframe, strategy)
        print(f"\n{strategy} ({timeframe}):")
        print(f"  最小レバレッジ: {conditions.get('min_leverage', 'N/A')}x")
        print(f"  最小信頼度: {conditions.get('min_confidence', 0) * 100:.0f}%")
        print(f"  最小RR比: {conditions.get('min_risk_reward', 'N/A')}")
        print(f"  最大レバレッジ: {conditions.get('max_leverage', 'N/A')}x")
    
    # 2. 実際の分析での適用確認
    print("\n\n🧪 実際の分析での適用テスト:")
    print("-" * 50)
    
    from scalable_analysis_system import ScalableAnalysisSystem
    system = ScalableAnalysisSystem()
    
    # モック分析結果で条件評価をテスト
    test_cases = [
        {
            'strategy': 'Conservative_ML',
            'leverage': 6.5,
            'confidence': 65,  # パーセント表記
            'risk_reward_ratio': 1.8,
            'current_price': 150.0
        },
        {
            'strategy': 'Aggressive_ML',
            'leverage': 6.5,
            'confidence': 62,  # Aggressiveなら信頼度要件が緩い
            'risk_reward_ratio': 2.5,
            'current_price': 150.0
        },
        {
            'strategy': 'Balanced',
            'leverage': 6.0,
            'confidence': 65,
            'risk_reward_ratio': 2.0,
            'current_price': 150.0
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔍 テストケース: {test_case['strategy']}")
        print(f"   レバレッジ: {test_case['leverage']}x")
        print(f"   信頼度: {test_case['confidence']}%")
        print(f"   RR比: {test_case['risk_reward_ratio']}")
        
        # 条件評価
        meets_conditions = system._evaluate_entry_conditions(test_case, timeframe)
        print(f"   結果: {'✅ 条件満たす' if meets_conditions else '❌ 条件未達'}")
    
    # 3. 設定ファイルの内容表示
    print("\n\n📋 現在の設定ファイル:")
    print("-" * 50)
    
    # レバレッジエンジン設定
    lev_config = config_manager.get_leverage_engine_config()
    print("\nレバレッジエンジン設定:")
    print(f"  最大レバレッジ: {lev_config.get('max_leverage')}x")
    print(f"  最小RR比: {lev_config.get('min_risk_reward')}")
    print(f"  BTC相関閾値: {lev_config.get('btc_correlation_threshold')}")
    
    # リスク管理設定
    risk_config = config_manager.get_risk_management_config()
    print("\nリスク管理設定:")
    print(f"  最大日次ドローダウン: {risk_config.get('max_daily_drawdown') * 100:.0f}%")
    print(f"  最大ポジション数: {risk_config.get('max_positions')}")
    
    print("\n✅ 統合設定システムの動作確認完了")


if __name__ == "__main__":
    test_unified_config_integration()