#!/usr/bin/env python3
"""
条件ベース動作の簡易確認テスト
max_evaluations=100の設定で正常に動作することを確認
"""

import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_quick_condition_check():
    """簡易動作確認"""
    print("🚀 条件ベース動作確認テスト（max_evaluations=100）")
    print("=" * 60)
    
    from scalable_analysis_system import ScalableAnalysisSystem
    system = ScalableAnalysisSystem()
    
    # configから設定を読み込んで表示
    try:
        # 時間足設定マネージャーから設定を取得
        if hasattr(system, 'get_timeframe_config'):
            config_1h = system.get_timeframe_config('1h')
            print(f"\n📋 1h足の現在設定:")
            print(f"   最大評価回数: {config_1h.get('max_evaluations', 'N/A')}回")
            print(f"   評価間隔: {config_1h.get('evaluation_interval_minutes', 'N/A')}分")
            print(f"   最小レバレッジ: {config_1h.get('min_leverage', 'N/A')}x")
        
        # モックデータで動作確認
        print("\n🧪 モック条件評価テスト...")
        
        # _evaluate_entry_conditionsメソッドの存在確認
        if hasattr(system, '_evaluate_entry_conditions'):
            # モックのanalysis_result
            mock_result = {
                'leverage': 5.0,
                'confidence': 0.6,
                'risk_reward_ratio': 2.5,
                'entry_price': 100.0,
                'take_profit_price': 105.0,
                'stop_loss_price': 97.5
            }
            
            # 条件評価
            meets_conditions = system._evaluate_entry_conditions(mock_result, '1h')
            print(f"   条件評価結果: {'✅ 条件満たす' if meets_conditions else '❌ 条件未達'}")
            print(f"   レバレッジ: {mock_result['leverage']}x")
            print(f"   信頼度: {mock_result['confidence'] * 100:.0f}%")
            print(f"   RR比: {mock_result['risk_reward_ratio']}")
        else:
            print("   ❌ _evaluate_entry_conditionsメソッドが見つかりません")
        
        # 評価ループの確認
        print("\n🔄 評価ループ動作確認...")
        import datetime
        
        # 評価間隔の計算
        eval_interval = config_1h.get('evaluation_interval_minutes', 240)
        max_evals = config_1h.get('max_evaluations', 100)
        
        total_time = eval_interval * max_evals
        total_days = total_time / (60 * 24)
        
        print(f"   評価間隔: {eval_interval}分")
        print(f"   最大評価回数: {max_evals}回")
        print(f"   最大カバー期間: {total_days:.1f}日")
        
        # 設定の妥当性チェック
        print("\n📊 設定妥当性チェック:")
        if total_days < 7:
            print(f"   ⚠️ カバー期間が短い可能性があります（{total_days:.1f}日）")
            print(f"   💡 max_evaluationsを増やすか、評価間隔を調整してください")
        else:
            print(f"   ✅ 十分なカバー期間です（{total_days:.1f}日）")
        
        print("\n✅ 動作確認完了")
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_quick_condition_check()