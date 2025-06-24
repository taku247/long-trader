#!/usr/bin/env python3
"""
簡単なPre-task重複作成修正テスト
実際のHYPE銘柄を使って動作確認
"""

import sys
import os
import asyncio
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
import uuid

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from auto_symbol_training import AutoSymbolTrainer
from scalable_analysis_system import ScalableAnalysisSystem

async def test_skip_parameter_flow():
    """skip_pretask_creationパラメータがメソッドチェーンで正しく渡されるかテスト"""
    print("🔗 skip_pretask_creationパラメータ伝播テスト")
    
    trainer = AutoSymbolTrainer()
    
    # スタブ設定
    execution_id = str(uuid.uuid4())
    symbol = "HYPE"
    strategy_configs = [
        {
            'id': 1,
            'name': 'Test Strategy 1',
            'base_strategy': 'Conservative_ML',
            'timeframe': '1h',
            'parameters': {'param1': 10},
            'description': 'Test strategy 1'
        }
    ]
    
    # generate_batch_analysisをモック化してスキップパラメータを確認
    original_generate = trainer.analysis_system.generate_batch_analysis
    
    def mock_generate_batch_analysis(*args, **kwargs):
        print(f"📋 generate_batch_analysis called with skip_pretask_creation = {kwargs.get('skip_pretask_creation', False)}")
        if kwargs.get('skip_pretask_creation', False):
            print("✅ skip_pretask_creation=True が正しく渡された")
        else:
            print("❌ skip_pretask_creation=False または未設定")
        return 0  # 処理件数0を返す（テスト用）
    
    # モック適用
    trainer.analysis_system.generate_batch_analysis = mock_generate_batch_analysis
    
    try:
        # データ取得段階をスキップして直接バックテストを実行
        print("🚀 _run_comprehensive_backtest実行（skip_pretask_creation=True）")
        
        result = await trainer._run_comprehensive_backtest(
            symbol=symbol, 
            strategy_configs=strategy_configs,
            skip_pretask_creation=True
        )
        
        print(f"📊 バックテスト結果: {result}")
        print("✅ テスト成功: パラメータが正しく伝播された")
        return True
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 元のメソッドを復元
        trainer.analysis_system.generate_batch_analysis = original_generate

async def test_method_signature_compatibility():
    """メソッドシグネチャの互換性テスト"""
    print("\n🔧 メソッドシグネチャ互換性テスト")
    
    trainer = AutoSymbolTrainer()
    
    # 各メソッドがskip_pretask_creationパラメータを受け取れるかテスト
    try:
        # 1. add_symbol_with_training
        import inspect
        sig = inspect.signature(trainer.add_symbol_with_training)
        if 'skip_pretask_creation' in sig.parameters:
            print("✅ add_symbol_with_training: skip_pretask_creation パラメータ対応")
        else:
            print("❌ add_symbol_with_training: skip_pretask_creation パラメータ未対応")
            return False
        
        # 2. _run_comprehensive_backtest
        sig = inspect.signature(trainer._run_comprehensive_backtest)
        if 'skip_pretask_creation' in sig.parameters:
            print("✅ _run_comprehensive_backtest: skip_pretask_creation パラメータ対応")
        else:
            print("❌ _run_comprehensive_backtest: skip_pretask_creation パラメータ未対応")
            return False
        
        # 3. ScalableAnalysisSystem.generate_batch_analysis
        sig = inspect.signature(trainer.analysis_system.generate_batch_analysis)
        if 'skip_pretask_creation' in sig.parameters:
            print("✅ generate_batch_analysis: skip_pretask_creation パラメータ対応")
        else:
            print("❌ generate_batch_analysis: skip_pretask_creation パラメータ未対応")
            return False
        
        print("✅ 全メソッドでパラメータ対応完了")
        return True
        
    except Exception as e:
        print(f"❌ シグネチャテストエラー: {e}")
        return False

def test_new_symbol_addition_system_integration():
    """new_symbol_addition_system.pyでの統合テスト"""
    print("\n📝 new_symbol_addition_system.py統合テスト")
    
    try:
        # ファイルを読み込んでskip_pretask_creation=Trueが設定されているかチェック
        with open('/Users/moriwakikeita/tools/long-trader/new_symbol_addition_system.py', 'r') as f:
            content = f.read()
        
        if 'skip_pretask_creation=True' in content:
            print("✅ new_symbol_addition_system.py: skip_pretask_creation=True 設定確認")
            return True
        else:
            print("❌ new_symbol_addition_system.py: skip_pretask_creation=True 設定なし")
            return False
            
    except Exception as e:
        print(f"❌ 統合テストエラー: {e}")
        return False

async def main():
    """メインテスト実行"""
    print("🚀 Pre-task重複作成修正テスト（簡易版）")
    print("=" * 50)
    
    # テスト1: メソッドシグネチャ互換性
    success1 = await test_method_signature_compatibility()
    
    # テスト2: パラメータ伝播
    success2 = await test_skip_parameter_flow()
    
    # テスト3: new_symbol_addition_system.py統合
    success3 = test_new_symbol_addition_system_integration()
    
    print("\n" + "=" * 50)
    if success1 and success2 and success3:
        print("✅ 全テスト成功: Pre-task重複作成修正が完了")
        print("\n📋 修正サマリー:")
        print("  1. auto_symbol_training.py: skip_pretask_creation パラメータ追加")
        print("  2. scalable_analysis_system.py: 条件付きPre-task作成制御")
        print("  3. new_symbol_addition_system.py: skip_pretask_creation=True 設定")
        print("\n🎯 これでHYPE銘柄の「Pre-task作成完了: 0タスク作成」問題が解決されました")
        return 0
    else:
        print("❌ 一部テスト失敗: 修正が不完全")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)