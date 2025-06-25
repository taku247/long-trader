#!/usr/bin/env python3
"""
XRP クイックテスト

設定調整後のXRPで簡単なシグナル検証
"""

import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def quick_xrp_test():
    """XRP簡単テスト"""
    print("🔍 XRP簡単テスト")
    print("=" * 30)
    
    try:
        # AutoSymbolTrainerを使って実際にXRPを追加テスト
        from auto_symbol_training import AutoSymbolTrainer
        import asyncio
        
        trainer = AutoSymbolTrainer()
        
        print("🚀 XRP銘柄追加テスト開始...")
        
        # 3戦略のみでテスト
        selected_strategies = ["Conservative_ML", "Balanced", "Aggressive_ML"] 
        selected_timeframes = ["15m", "30m"]
        
        async def run_test():
            try:
                execution_id = await trainer.add_symbol_with_training(
                    symbol="XRP",
                    selected_strategies=selected_strategies,
                    selected_timeframes=selected_timeframes
                )
                print(f"✅ XRP追加テスト完了: {execution_id}")
                return True
            except Exception as e:
                print(f"❌ XRP追加テストエラー: {e}")
                return False
        
        # 非同期実行
        result = asyncio.run(run_test())
        
        if result:
            print("🎉 XRPの設定調整が効果的です")
        else:
            print("🔧 XRPにはさらなる調整が必要です")
            
        return result
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_xrp_test()
    print(f"\n📊 結果: {'成功' if success else '要改善'}")