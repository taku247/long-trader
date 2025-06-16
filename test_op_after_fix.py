#!/usr/bin/env python3
"""
サポート強度修正後のOPテスト
"""

import sys
import logging
import importlib
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

# 関連モジュールを強制リロード
import support_resistance_visualizer
importlib.reload(support_resistance_visualizer)

# ロギング設定
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator

def test_op_after_fix():
    """サポート強度修正後のOPテスト"""
    print("🔍 サポート強度修正後のOPテスト")
    print("=" * 60)
    
    try:
        print("1️⃣ 新しいプロセスでHighLeverageBotOrchestratorを初期化中...")
        bot = HighLeverageBotOrchestrator()
        
        print("\n2️⃣ OP分析を実行中...")
        print("   期待値: support_strength が0-1の範囲内")
        print("-" * 60)
        
        result = bot.analyze_symbol('OP', '15m', 'Aggressive_ML')
        
        print("-" * 60)
        print("\n3️⃣ 結果分析:")
        
        if result:
            print(f"   レバレッジ: {result.get('leverage', 'N/A')}")
            print(f"   信頼度: {result.get('confidence', 'N/A')}%")
            print(f"   リスクリワード比: {result.get('risk_reward_ratio', 'N/A')}")
            print(f"   現在価格: {result.get('current_price', 'N/A')}")
            
            # 値の妥当性チェック
            confidence = result.get('confidence', 0)
            leverage = result.get('leverage', 0)
            
            print("\n4️⃣ 修正効果分析:")
            
            # 信頼度チェック
            if 50 <= confidence <= 80:
                print(f"   ✅ 信頼度正常: {confidence}% (期待範囲: 50-80%)")
            elif confidence > 80:
                print(f"   ⚠️ 信頼度高め: {confidence}% (まだsupport_strengthが高い可能性)")
            else:
                print(f"   ✅ 信頼度低め: {confidence}% (正常)")
            
            # レバレッジチェック
            if leverage > 1.5:
                print(f"   ✅ レバレッジ多様化: {leverage}x (改善)")
            else:
                print(f"   ⚠️ レバレッジ低め: {leverage}x (市場条件か計算問題)")
                
        else:
            print("\n3️⃣ 分析結果: None (エラー発生)")
            
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📋 期待される改善:")
    print("1. support_strength: 0.0-1.0の範囲内")
    print("2. 信頼度: 異常に高い90%から適正値へ")
    print("3. レバレッジ: 市場条件に基づく適切な値")

if __name__ == '__main__':
    test_op_after_fix()