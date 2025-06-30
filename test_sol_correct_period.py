#!/usr/bin/env python3
"""
SOL銘柄追加テスト - 修正した期間指定
開始日時: 2024/2/1 7:30 (2025ではなく2024に修正)
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_sol_with_correct_period():
    """SOLを正しい期間で実行"""
    trainer = AutoSymbolTrainer()
    
    # 2024年の日付に修正
    custom_period_settings = {
        'mode': 'custom',
        'start_date': '2024-02-01T07:30:00Z',  # 2025→2024に修正
        'end_date': '2024-06-30T00:00:00Z'     # 終了日も過去の日付に
    }
    
    print(f"🚀 SOL銘柄追加開始（期間修正版）")
    print(f"📅 期間設定: {custom_period_settings['start_date']} ～ {custom_period_settings['end_date']}")
    
    try:
        execution_id = await trainer.add_symbol_with_training(
            symbol='SOL',
            selected_strategies=['momentum'],
            selected_timeframes=['1h'],
            custom_period_settings=custom_period_settings
        )
        
        print(f"✅ 実行完了: {execution_id}")
        
        # 実行後の状態確認
        from execution_log_database import ExecutionLogDatabase
        db = ExecutionLogDatabase()
        executions = db.list_executions(limit=1)
        
        if executions:
            latest = executions[0]
            print(f"\n📊 実行結果:")
            print(f"   状態: {latest.get('status')}")
            print(f"   現在操作: {latest.get('current_operation')}")
            
        # 分析結果の確認
        from scalable_analysis_system import ScalableAnalysisSystem
        analysis_system = ScalableAnalysisSystem()
        
        import sqlite3
        with sqlite3.connect(analysis_system.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*), SUM(total_trades) 
                FROM analyses 
                WHERE symbol = 'SOL' AND execution_id = ?
            """, (execution_id,))
            count, total_trades = cursor.fetchone()
            print(f"\n📊 分析結果:")
            print(f"   保存された結果: {count}件")
            print(f"   総トレード数: {total_trades or 0}")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sol_with_correct_period())