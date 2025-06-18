#!/usr/bin/env python3
"""
支持線・抵抗線修正のデバッグテスト
"""

import sys
import os
import asyncio
import traceback
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer


async def debug_test():
    """デバッグ用簡易テスト"""
    
    print("🔍 デバッグテスト開始")
    
    try:
        trainer = AutoSymbolTrainer()
        print("✅ AutoSymbolTrainerインスタンス作成成功")
        
        # analysis_systemが存在するか確認
        if hasattr(trainer, 'analysis_system'):
            print("✅ analysis_system属性が存在")
        else:
            print("❌ analysis_system属性が存在しません")
            return
        
        # _run_comprehensive_backtestメソッドが存在するか確認
        if hasattr(trainer, '_run_comprehensive_backtest'):
            print("✅ _run_comprehensive_backtestメソッドが存在")
        else:
            print("❌ _run_comprehensive_backtestメソッドが存在しません")
            return
        
        # モック設定
        with patch.object(trainer.analysis_system, 'generate_batch_analysis', return_value=0):
            print("✅ モック設定成功")
            
            # 実際に実行
            configs = [{'symbol': 'TEST', 'timeframe': '1h', 'strategy': 'Conservative_ML'}]
            print(f"🔄 実行開始: {configs}")
            
            await trainer._run_comprehensive_backtest("TEST")
            print("✅ 実行完了 - 例外なし")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        print(f"エラータイプ: {type(e).__name__}")
        print("詳細スタックトレース:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_test())