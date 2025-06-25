#!/usr/bin/env python3
"""
マルチプロセス処理の詳細デバッグ
実際に何が実行されているかを確認
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# scalable_analysis_system.pyの_generate_single_analysisを直接実行
def debug_single_analysis():
    """単一分析処理を直接実行してデバッグ"""
    
    print("🔍 単一分析処理の直接デバッグ\n")
    
    # テスト用の設定
    test_config = {
        'symbol': 'AAVE', 
        'timeframe': '1h',
        'config': 'Conservative_ML',
        'execution_id': 'DEBUG_DIRECT'
    }
    
    print(f"テスト設定: {test_config}")
    
    try:
        # scalable_analysis_system.pyの関数を直接インポート
        from scalable_analysis_system import ScalableAnalysisSystem
        
        # システム初期化
        system = ScalableAnalysisSystem()
        
        print("\n📊 システム初期化完了")
        print(f"データベースパス: {system.db_path}")
        
        # 環境変数設定
        os.environ['CURRENT_EXECUTION_ID'] = test_config['execution_id']
        
        # _generate_single_analysisを直接実行
        result = system._generate_single_analysis(
            test_config['symbol'],
            test_config['timeframe'], 
            test_config['config']
        )
        
        print(f"\n✅ 分析結果: {result}")
        
        # データベースの結果を確認
        with sqlite3.connect(system.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT symbol, timeframe, config, task_status, status, error_message
                FROM analyses 
                WHERE symbol = ? AND timeframe = ? AND config = ?
                ORDER BY id DESC LIMIT 1
            ''', (test_config['symbol'], test_config['timeframe'], test_config['config']))
            
            db_result = cursor.fetchone()
            if db_result:
                print(f"📊 DB結果: {db_result}")
            else:
                print("📊 DB結果: レコードなし")
        
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def debug_analysis_exists():
    """_analysis_existsチェックのデバッグ"""
    
    print("\n🔍 _analysis_existsチェックのデバッグ\n")
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # 様々な銘柄で_analysis_existsをチェック
        test_cases = [
            ('AAVE', '1h', 'Conservative_ML'),  # 新規
            ('HYPE', '1h', 'Conservative_ML'),  # 既存
            ('TURBO', '30m', 'Aggressive_ML')   # 既存
        ]
        
        for symbol, timeframe, config in test_cases:
            analysis_id = f"{symbol}_{timeframe}_{config}"
            exists = system._analysis_exists(analysis_id)
            print(f"{analysis_id}: {'既存あり' if exists else '新規'}")
            
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 1. _analysis_existsチェックのデバッグ
    debug_analysis_exists()
    
    # 2. 単一分析処理のデバッグ
    debug_single_analysis()