#!/usr/bin/env python3
"""
DOGE と ATOM の実状況確認
"""

import sqlite3
from datetime import datetime

db_path = 'execution_logs.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

execution_ids = [
    'symbol_addition_20250617_171159_6f5523cb',  # DOGE
    'symbol_addition_20250617_165203_d902e5e8'   # ATOM
]

print('🔍 DOGE と ATOM のDB実状況')
print('=' * 70)

for exec_id in execution_ids:
    cursor.execute('''
        SELECT symbol, status, timestamp_start, timestamp_end, 
               progress_percentage, current_operation
        FROM execution_logs 
        WHERE execution_id = ?
    ''', (exec_id,))
    
    row = cursor.fetchone()
    if row:
        symbol, status, start, end, progress, operation = row
        print(f'\n📊 {symbol} ({exec_id[:30]}...):')
        print(f'   DB状態: {status}')
        print(f'   進捗: {progress}%')
        print(f'   開始: {start}')
        print(f'   終了: {end}')
        print(f'   操作: {operation}')
        
        if status == 'RUNNING' and end:
            print(f'   ⚠️ 異常: RUNNINGなのに終了時刻が記録されています')
        elif status != 'RUNNING':
            print(f'   ⚠️ UIではRUNNINGだがDBでは{status}')
    else:
        print(f'\n❌ {exec_id[:30]}...: レコードが見つかりません')

print('\n\n📝 推奨対応:')
print('1. 実際のプロセスが存在しない場合は手動リセットを実行')
print('2. または12時間以内であれば時間調整付きクリーンアップを実行')

conn.close()