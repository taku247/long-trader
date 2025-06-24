#!/usr/bin/env python3
"""
戦略実行失敗問題の修正・テスト

現在発生している「3つの戦略選択→全て失敗」問題の調査と修正
"""

import sys
from pathlib import Path
import sqlite3
import asyncio
from unittest.mock import patch

# プロジェクトルートを追加
sys.path.append(str(Path(__file__).parent))

def debug_current_strategy_execution():
    """現在の戦略実行を詳細デバッグ"""
    
    print("🔍 戦略実行失敗問題のデバッグ・修正")
    print("=" * 60)
    
    # 1. 失敗したDOGE実行の詳細確認
    print("📊 1. 失敗したDOGE実行の詳細確認")
    
    analysis_db = Path("large_scale_analysis/analysis.db")
    execution_logs_db = Path("execution_logs.db")
    
    # 最新の失敗実行を取得
    with sqlite3.connect(execution_logs_db) as conn:
        cursor = conn.execute("""
            SELECT execution_id, symbol, status, selected_strategy_ids, execution_mode, 
                   timestamp_start, timestamp_end, current_operation
            FROM execution_logs 
            WHERE symbol = 'DOGE' AND status = 'FAILED'
            ORDER BY timestamp_start DESC 
            LIMIT 1
        """)
        
        failed_exec = cursor.fetchone()
        if failed_exec:
            execution_id = failed_exec[0]
            print(f"   失敗実行ID: {execution_id}")
            print(f"   選択戦略: {failed_exec[3]}")
            print(f"   実行モード: {failed_exec[4]}")
            print(f"   失敗理由: {failed_exec[7]}")
            
            # 個別タスクの状況確認
            with sqlite3.connect(analysis_db) as analysis_conn:
                cursor = analysis_conn.execute("""
                    SELECT strategy_config_id, strategy_name, task_status, error_message
                    FROM analyses 
                    WHERE execution_id = ? AND symbol = 'DOGE'
                    ORDER BY strategy_config_id
                """, (execution_id,))
                
                tasks = cursor.fetchall()
                print(f"\n   📋 個別タスク状況:")
                for task in tasks:
                    print(f"     戦略ID {task[0]} ({task[1]}): {task[2]}")
                    if task[3]:
                        print(f"       エラー: {task[3]}")
        else:
            print("   ❌ 失敗したDOGE実行が見つかりません")
            return
    
    # 2. auto_symbol_training.py の失敗条件を確認
    print(f"\n📈 2. auto_symbol_training.py の失敗ロジック確認")
    
    from auto_symbol_training import AutoSymbolTrainer
    
    # auto_symbol_trainingのコードを確認
    print(f"   🔍 失敗条件: successful_tests == 0 and processed_count == 0")
    print(f"   現在の状況: processed_count = 0 (ScalableAnalysisSystemから)")
    print(f"   原因: バッチ分析で実際の分析が実行されていない")
    
    # 3. ScalableAnalysisSystemの設定確認
    print(f"\n⚙️ 3. ScalableAnalysisSystem設定分析")
    
    # この時点で、問題は以下のいずれかと推測される:
    # A. strategy_configsの形式が正しくない
    # B. 個別の分析でエラーが発生している
    # C. 例外処理で分析がスキップされている
    
    # 設定の再確認
    from new_symbol_addition_system import NewSymbolAdditionSystem
    
    system = NewSymbolAdditionSystem()
    
    # 失敗した戦略IDで設定確認
    import json
    selected_strategy_ids = json.loads(failed_exec[3])
    print(f"   選択戦略IDs: {selected_strategy_ids}")
    
    strategy_configs = system.get_strategy_configs_for_legacy(selected_strategy_ids)
    print(f"   取得した設定数: {len(strategy_configs) if strategy_configs else 0}")
    
    if strategy_configs:
        for config in strategy_configs:
            print(f"     戦略ID {config['id']}: {config['name']}")
            print(f"       ベース戦略: {config['base_strategy']}")
            print(f"       時間足: {config['timeframe']}")
            print(f"       is_active: {config.get('is_active', 'N/A')}")
            print(f"       is_default: {config.get('is_default', 'N/A')}")
    
    # 4. 支持線・抵抗線検出の警告処理問題の可能性
    print(f"\n🚨 4. 支持線・抵抗線警告処理の修正")
    
    # auto_symbol_training.py:468-472の警告処理を確認
    print(f"   現在の処理: 支持線・抵抗線未検出時に警告を出すが、processed_count = 0")
    print(f"   問題: 警告処理後もprocessed_count = 0のため、全戦略失敗と判定される")
    
    return execution_id, selected_strategy_ids, strategy_configs

def test_strategy_execution_fix():
    """戦略実行修正のテスト"""
    
    print(f"\n🔧 5. 戦略実行修正案の実装・テスト")
    
    # 修正案: auto_symbol_training.pyの_run_comprehensive_backtestメソッドで
    # 支持線・抵抗線未検出の場合も"成功"として扱う
    
    execution_id, selected_strategy_ids, strategy_configs = debug_current_strategy_execution()
    
    if not strategy_configs:
        print("   ❌ 戦略設定が取得できないため、修正テストをスキップ")
        return
    
    print(f"\n   修正案A: 支持線・抵抗線未検出時も処理を継続")
    print(f"   - processed_count = 0でも、警告として記録")
    print(f"   - successful_tests > 0になるよう、警告ケースを成功として扱う")
    
    print(f"\n   修正案B: 分析結果のチェック方法を改善")
    print(f"   - query_analysesで結果が取得できない原因を調査")
    print(f"   - 個別分析の実行状況を詳細ログで確認")
    
    # 実際の修正実装は次のステップで行う
    print(f"\n✅ 修正案確定: auto_symbol_training.pyの警告処理を改善")

if __name__ == "__main__":
    debug_current_strategy_execution()
    test_strategy_execution_fix()