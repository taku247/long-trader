#!/usr/bin/env python3
"""
NEARの状態をクリアして再追加可能にする
"""

from execution_log_database import ExecutionLogDatabase
import sqlite3

def clear_near_status():
    """NEARの実行記録を確認し、必要に応じてクリア"""
    db = ExecutionLogDatabase()
    
    # NEARの状態を確認
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute('''
            SELECT execution_id, status
            FROM execution_logs 
            WHERE symbol = 'NEAR' AND status = 'RUNNING'
            ORDER BY timestamp_start DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        
        if row:
            exec_id, status = row
            print(f"❌ NEARにRUNNING状態の記録があります: {exec_id}")
            
            # CANCELLEDに更新
            cursor.execute('''
                UPDATE execution_logs 
                SET status = 'CANCELLED',
                    timestamp_end = datetime('now'),
                    current_operation = 'Manually cleared for re-addition'
                WHERE execution_id = ?
            ''', (exec_id,))
            
            conn.commit()
            print("✅ NEARのステータスをCANCELLEDに更新しました")
        else:
            print("✅ NEARにRUNNING状態の記録はありません（追加可能）")
    
    # キャッシュファイルの確認
    import os
    cache_files = [
        'symbol_processing_state.json',
        'ml_models/NEAR_support_resistance_analysis.json',
        'ml_models/NEAR_ml_model.pkl'
    ]
    
    for file in cache_files:
        if os.path.exists(file):
            print(f"⚠️ キャッシュファイル発見: {file}")
            # os.remove(file)  # 必要に応じてコメントアウトを外す
            # print(f"  → 削除しました")

if __name__ == "__main__":
    print("🔍 NEARの状態をチェックしています...")
    clear_near_status()
    print("\n✅ 完了しました。ブラウザをリロードしてNEARを追加してください。")