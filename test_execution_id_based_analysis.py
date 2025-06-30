#!/usr/bin/env python3
"""
execution_id別の分析実行テスト

⚠️ 注意: _analysis_existsメソッドは2025-07-01に削除されました
このテストは無効化されています
理由: execution_id別の独立実行を阻害するため
"""

import sys
import os
import tempfile
import sqlite3
from pathlib import Path

# プロジェクトパスを追加
sys.path.append('/Users/moriwakikeita/tools/long-trader')

def test_execution_id_based_analysis():
    """execution_id別の分析実行をテスト"""
    from scalable_analysis_system import ScalableAnalysisSystem
    
    print("🧪 execution_id別分析実行テスト")
    print("=" * 50)
    
    # テスト用の一時ディレクトリ作成
    temp_dir = tempfile.mkdtemp()
    test_db_dir = Path(temp_dir) / "test_analysis"
    test_db_dir.mkdir(parents=True, exist_ok=True)
    test_db_path = test_db_dir / "analysis.db"
    
    try:
        # ScalableAnalysisSystemのインスタンス作成
        system = ScalableAnalysisSystem.__new__(ScalableAnalysisSystem)
        system.db_path = test_db_path
        system.base_dir = test_db_dir
        
        # テスト用データベースの作成
        with sqlite3.connect(test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    config TEXT NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    total_return REAL DEFAULT 0.0,
                    win_rate REAL DEFAULT 0.0,
                    sharpe_ratio REAL DEFAULT 0.0,
                    max_drawdown REAL DEFAULT 0.0,
                    avg_leverage REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    execution_id TEXT,
                    task_status TEXT DEFAULT 'pending'
                )
            ''')
            conn.commit()
        
        # テストケース1: 初回実行（execution_id: test_001）
        print("\n🔍 テストケース1: 初回実行")
        symbol, timeframe, config = "SOL", "1h", "Conservative_ML"
        execution_id_1 = "test_execution_001"
        
        # 既存チェック（execution_id別）
        analysis_id = f"{symbol}_{timeframe}_{config}"
        exists_1 = system._analysis_exists(analysis_id, execution_id_1)
        print(f"   execution_id={execution_id_1}: 既存分析={exists_1}")
        
        # テストケース2: 異なるexecution_idでの実行（test_002）
        print("\n🔍 テストケース2: 異なるexecution_idでの実行")
        execution_id_2 = "test_execution_002"
        exists_2 = system._analysis_exists(analysis_id, execution_id_2)
        print(f"   execution_id={execution_id_2}: 既存分析={exists_2}")
        
        # テストケース3: 全体での既存チェック（execution_id指定なし）
        print("\n🔍 テストケース3: 全体での既存チェック")
        exists_global = system._analysis_exists(analysis_id)
        print(f"   execution_id=None: 既存分析={exists_global}")
        
        # テストケース4: force_refresh=Trueでの実行
        print("\n🔍 テストケース4: force_refresh=Trueでの実行")
        exists_force = system._analysis_exists(analysis_id, force_refresh=True)
        print(f"   force_refresh=True: 既存分析={exists_force}")
        
        # 既存データを作成してテスト
        print("\n📊 既存データを作成してテスト実行...")
        with sqlite3.connect(test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO analyses (symbol, timeframe, config, execution_id, total_trades)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, timeframe, config, execution_id_1, 100))
            conn.commit()
        
        # 再テスト
        print("\n🔄 既存データ作成後の再テスト:")
        exists_1_after = system._analysis_exists(analysis_id, execution_id_1)
        exists_2_after = system._analysis_exists(analysis_id, execution_id_2) 
        exists_global_after = system._analysis_exists(analysis_id)
        
        print(f"   execution_id={execution_id_1}: 既存分析={exists_1_after} (既存データあり)")
        print(f"   execution_id={execution_id_2}: 既存分析={exists_2_after} (新規execution_id)")
        print(f"   execution_id=None: 既存分析={exists_global_after} (全体チェック)")
        
        # 検証結果の確認
        print("\n✅ 検証結果:")
        print(f"   ✅ 同一execution_idでは既存判定: {exists_1_after}")
        print(f"   ✅ 異なるexecution_idでは新規判定: {not exists_2_after}")
        print(f"   ✅ 全体チェックでは既存判定: {exists_global_after}")
        
        # 期待される動作の確認
        expected_behavior = (
            exists_1_after == True and      # 同一execution_idは既存
            exists_2_after == False and     # 異なるexecution_idは新規
            exists_global_after == True     # 全体では既存
        )
        
        if expected_behavior:
            print("🎉 execution_id別の分析管理が正常に動作しています！")
        else:
            print("❌ execution_id別の分析管理に問題があります。")
            
    finally:
        # クリーンアップ
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    test_execution_id_based_analysis()