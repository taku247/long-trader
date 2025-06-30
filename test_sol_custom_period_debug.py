#!/usr/bin/env python3
"""
SOL銘柄追加デバッグテスト - カスタム期間指定
開始日時: 2025/2/1 7:30
"""

import asyncio
import sys
import os
from datetime import datetime

# デバッグモード設定
os.environ['SUPPORT_RESISTANCE_DEBUG'] = 'true'

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer
import logging

# より詳細なログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sol_custom_period_debug.log')
    ]
)

# scalable_analysis_systemのログも有効化
logging.getLogger('scalable_analysis_system').setLevel(logging.DEBUG)

async def test_sol_with_custom_period():
    """SOLをカスタム期間で実行（デバッグモード）"""
    trainer = AutoSymbolTrainer()
    
    # カスタム期間設定
    custom_period_settings = {
        'mode': 'custom',
        'start_date': '2025-02-01T07:30:00Z',
        'end_date': '2025-06-30T00:00:00Z'
    }
    
    print(f"🚀 SOL銘柄追加開始（デバッグモード）")
    print(f"📅 期間設定: {custom_period_settings['start_date']} ～ {custom_period_settings['end_date']}")
    print(f"🔍 デバッグモード: 有効")
    
    try:
        execution_id = await trainer.add_symbol_with_training(
            symbol='SOL',
            selected_strategies=['momentum'],
            selected_timeframes=['1h'],
            custom_period_settings=custom_period_settings
        )
        
        print(f"✅ 実行完了: {execution_id}")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        
        # エラー時でも分析結果を確認
        from scalable_analysis_system import ScalableAnalysisSystem
        import sqlite3
        
        analysis_system = ScalableAnalysisSystem()
        
        # 最新のpre-taskを確認
        with sqlite3.connect(analysis_system.db_path) as conn:
            cursor = conn.execute("""
                SELECT symbol, timeframe, config, task_status, error_message 
                FROM analyses 
                WHERE symbol = 'SOL' 
                ORDER BY id DESC 
                LIMIT 5
            """)
            
            print("\n📊 最新の分析タスク状態:")
            for row in cursor.fetchall():
                print(f"   - {row[0]} {row[1]} {row[2]}: {row[3]} | {row[4]}")

if __name__ == "__main__":
    asyncio.run(test_sol_with_custom_period())