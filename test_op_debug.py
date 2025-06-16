#!/usr/bin/env python3
"""
OPのreturn None問題をデバッグするためのテストスクリプト
"""

import sys
import logging
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

# ロギング設定 - ERRORレベルのみ表示
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator

def test_op_analysis():
    """OPの分析を実行してreturn Noneが発生するか確認"""
    print("🔍 OP分析デバッグテスト開始")
    print("=" * 60)
    
    try:
        # ボット初期化
        print("1️⃣ HighLeverageBotOrchestratorを初期化中...")
        bot = HighLeverageBotOrchestrator()
        
        # OP分析実行
        print("\n2️⃣ OP分析を実行中...")
        print("   ⚠️ ERRORログが表示される場合は、return Noneが実行されています")
        print("-" * 60)
        
        result = bot.analyze_symbol('OP', '15m', 'Aggressive_ML')
        
        print("-" * 60)
        
        if result:
            print("\n3️⃣ 分析結果:")
            print(f"   レバレッジ: {result.get('leverage', 'N/A')}")
            print(f"   信頼度: {result.get('confidence', 'N/A')}%")
            print(f"   リスクリワード比: {result.get('risk_reward_ratio', 'N/A')}")
            print(f"   現在価格: {result.get('current_price', 'N/A')}")
            
            if result.get('leverage') is None:
                print("\n   🚨 レバレッジがNone - シグナル生成されません!")
        else:
            print("\n3️⃣ 分析結果: None (エラー発生)")
            
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📋 結論:")
    print("- ERRORログが表示された場合: return Noneが実行されています")
    print("- ERRORログが表示されない場合: 他の原因で0トレードになっています")

if __name__ == '__main__':
    test_op_analysis()