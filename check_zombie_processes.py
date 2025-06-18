#!/usr/bin/env python3
"""
ゾンビプロセスチェックスクリプト
"""

import sqlite3
from datetime import datetime

db_path = "execution_logs.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🔍 Web UIとDBの不整合確認")
print("=" * 70)

# Web UIで表示されている実行IDを確認
ui_execution_ids = {
    "DOGE": "symbol_addition_20250617_171159_6f5523cb",
    "ATOM": "symbol_addition_20250617_165203_d902e5e8", 
    "ETH": "symbol_addition_20250617_002451_9cdd9d3a",
    "TON": "symbol_addition_20250616_170335_b316a7ea",
    "LINK": "symbol_addition_20250616_170232_68776bf0"
}

print("\nWeb UIが表示している実行IDの実際の状態:")

not_found = []
wrong_status = []

for symbol, exec_id in ui_execution_ids.items():
    cursor.execute("""
        SELECT status, timestamp_start, timestamp_end
        FROM execution_logs 
        WHERE execution_id = ?
    """, (exec_id,))
    
    row = cursor.fetchone()
    if row:
        status, start, end = row
        print(f"\n{symbol} ({exec_id[:20]}...):")
        print(f"  DB状態: {status}")
        print(f"  開始: {start}")
        print(f"  終了: {end}")
        
        if status != "RUNNING":
            wrong_status.append((symbol, status, exec_id))
    else:
        not_found.append((symbol, exec_id))

print("\n\n📊 問題のまとめ:")
if not_found:
    print("\n❌ 存在しない実行ID:")
    for symbol, exec_id in not_found:
        print(f"  - {symbol}: {exec_id}")

if wrong_status:
    print("\n⚠️ ステータス不整合:")
    for symbol, status, exec_id in wrong_status:
        print(f"  - {symbol}: UIではRUNNING、実際は{status}")

# 修正提案
if wrong_status or not_found:
    print("\n\n📝 推奨される対処法:")
    print("1. Web UIのキャッシュをクリアまたはサーバー再起動")
    print("2. execution_logsテーブルの不整合データをクリーンアップ")
    print("3. UIロジックを修正して最新の実行IDのみを表示")

conn.close()