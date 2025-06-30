#!/usr/bin/env python3
"""
SOL銘柄追加テスト - カスタム期間指定
開始日時: 2025/2/1 7:30
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sol_custom_period_test.log')
    ]
)

async def test_sol_with_custom_period():
    """SOLをカスタム期間で実行"""
    trainer = AutoSymbolTrainer()
    
    # カスタム期間設定
    custom_period_settings = {
        'mode': 'custom',
        'start_date': '2025-02-01T07:30:00Z',
        'end_date': '2025-06-30T00:00:00Z'
    }
    
    print(f"🚀 SOL銘柄追加開始")
    print(f"📅 期間設定: {custom_period_settings['start_date']} ～ {custom_period_settings['end_date']}")
    
    try:
        execution_id = await trainer.add_symbol_with_training(
            symbol='SOL',
            selected_strategies=['momentum'],  # テスト用に1戦略のみ
            selected_timeframes=['1h'],       # テスト用に1時間足のみ
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
            print(f"   エラー: {latest.get('errors', 'なし')}")
            
        # 分析結果の確認
        from scalable_analysis_system import ScalableAnalysisSystem
        analysis_system = ScalableAnalysisSystem()
        
        import sqlite3
        with sqlite3.connect(analysis_system.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses 
                WHERE symbol = 'SOL' AND execution_id = ?
            """, (execution_id,))
            count = cursor.fetchone()[0]
            print(f"\n📊 保存された分析結果: {count}件")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sol_with_custom_period())