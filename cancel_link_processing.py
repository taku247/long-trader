#!/usr/bin/env python3
"""
LINK銘柄の実行中プロセスをキャンセル

"Symbol LINK is already being processed" エラーを解決するため、
実行中のLINK処理をキャンセルする。
"""

import sys
import os
import signal
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def cancel_link_processing():
    """LINK処理のキャンセル"""
    print("🛑 LINK銘柄処理キャンセル")
    print("=" * 50)
    
    try:
        # 実行データベースから現在の状況を確認
        from execution_log_database import ExecutionLogDatabase
        
        db = ExecutionLogDatabase()
        
        # 実行中のLINK処理を確認
        executions = db.list_executions(limit=20)
        link_executions = [
            exec_item for exec_item in executions 
            if exec_item.get('symbol') == 'LINK' and exec_item.get('status') == 'RUNNING'
        ]
        
        print(f"📊 実行中のLINK処理: {len(link_executions)}件")
        
        if not link_executions:
            print("✅ 実行中のLINK処理はありません")
            return True
        
        # 実行中の処理を表示
        for i, execution in enumerate(link_executions):
            print(f"   処理{i+1}: ID={execution.get('execution_id')}, "
                  f"開始時刻={execution.get('created_at')}, "
                  f"状態={execution.get('status')}")
        
        # 処理をキャンセル
        print(f"\n🛑 {len(link_executions)}件のLINK処理をキャンセル中...")
        
        for execution in link_executions:
            execution_id = execution.get('execution_id')
            try:
                # ステータスをCANCELLEDに更新
                from execution_log_database import ExecutionStatus
                db.update_execution_status(execution_id, ExecutionStatus.CANCELLED)
                print(f"   ✅ 処理ID {execution_id} をキャンセル")
            except Exception as e:
                print(f"   ❌ 処理ID {execution_id} キャンセル失敗: {e}")
        
        # プロセスも確認
        print(f"\n🔍 関連プロセスの確認...")
        import subprocess
        
        try:
            # multiprocessing プロセスをチェック
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            
            python_processes = [
                line for line in lines 
                if 'python' in line and 'multiprocessing' in line
            ]
            
            print(f"   Python multiprocessing プロセス: {len(python_processes)}件")
            
            # 必要に応じて警告
            if len(python_processes) > 10:
                print("   ⚠️ 多数のmultiprocessingプロセスが実行中")
                print("   必要に応じて手動でプロセスを終了してください")
            else:
                print("   ✅ プロセス数は正常範囲")
                
        except Exception as e:
            print(f"   ⚠️ プロセス確認エラー: {e}")
        
        print(f"\n✅ LINK処理キャンセル完了")
        print("   新しいLINK銘柄追加を実行できます")
        return True
        
    except Exception as e:
        print(f"❌ キャンセル処理エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_link_status():
    """LINK処理状況の確認"""
    print("\n🔍 LINK処理状況の確認")
    print("-" * 30)
    
    try:
        from execution_log_database import ExecutionLogDatabase
        
        db = ExecutionLogDatabase()
        
        # 最近のLINK処理を確認
        executions = db.list_executions(limit=50)
        link_executions = [
            exec_item for exec_item in executions 
            if exec_item.get('symbol') == 'LINK'
        ]
        
        print(f"📊 最近のLINK処理: {len(link_executions)}件")
        
        status_counts = {}
        for execution in link_executions[:10]:  # 最新10件
            status = execution.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"   {execution.get('created_at')}: {status}")
        
        print(f"\n📊 ステータス集計:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}件")
        
        # 実行中の処理があるかチェック
        running_count = status_counts.get('RUNNING', 0)
        if running_count == 0:
            print("✅ 実行中のLINK処理なし - 新規追加可能")
        else:
            print(f"⚠️ 実行中のLINK処理: {running_count}件")
            
        return running_count == 0
        
    except Exception as e:
        print(f"❌ 状況確認エラー: {e}")
        return False

def main():
    """メイン実行"""
    print("🛑 LINK銘柄処理キャンセルツール")
    print("=" * 80)
    print("'Symbol LINK is already being processed' エラー解決")
    print("=" * 80)
    
    # 現在の状況確認
    status_ok = verify_link_status()
    
    if status_ok:
        print("\n✅ LINK処理は既にクリア済み")
        print("   新しいLINK銘柄追加を実行できます")
        return True
    
    # キャンセル実行
    cancel_success = cancel_link_processing()
    
    # 再確認
    if cancel_success:
        time.sleep(2)  # 少し待機
        final_status = verify_link_status()
        
        if final_status:
            print("\n✅ LINK処理キャンセル成功")
            print("   ブラウザでLINK銘柄追加を再実行してください")
            return True
        else:
            print("\n⚠️ LINK処理が完全にクリアされていません")
            print("   しばらく待ってから再試行してください")
            return False
    else:
        print("\n❌ LINK処理キャンセル失敗")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)