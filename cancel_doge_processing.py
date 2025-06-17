#!/usr/bin/env python3
"""
DOGE銘柄の実行中プロセスをキャンセル

実行中のDOGE処理を停止する。
"""

import sys
import os
import signal
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def cancel_doge_processing():
    """DOGE処理のキャンセル"""
    print("🛑 DOGE銘柄処理キャンセル")
    print("=" * 50)
    
    try:
        # 実行データベースから現在の状況を確認
        from execution_log_database import ExecutionLogDatabase, ExecutionStatus
        
        db = ExecutionLogDatabase()
        
        # 実行中のDOGE処理を確認
        executions = db.list_executions(limit=20)
        doge_executions = [
            exec_item for exec_item in executions 
            if exec_item.get('symbol') == 'DOGE' and exec_item.get('status') == 'RUNNING'
        ]
        
        print(f"📊 実行中のDOGE処理: {len(doge_executions)}件")
        
        if not doge_executions:
            print("✅ 実行中のDOGE処理はありません")
            return True
        
        # 実行中の処理を表示
        for i, execution in enumerate(doge_executions):
            print(f"   処理{i+1}: ID={execution.get('execution_id')}, "
                  f"開始時刻={execution.get('created_at')}, "
                  f"状態={execution.get('status')}")
        
        # 処理をキャンセル
        print(f"\n🛑 {len(doge_executions)}件のDOGE処理をキャンセル中...")
        
        cancelled_count = 0
        for execution in doge_executions:
            execution_id = execution.get('execution_id')
            try:
                # ステータスをCANCELLEDに更新
                db.update_execution_status(execution_id, ExecutionStatus.CANCELLED)
                print(f"   ✅ 処理ID {execution_id} をキャンセル")
                cancelled_count += 1
            except Exception as e:
                print(f"   ❌ 処理ID {execution_id} キャンセル失敗: {e}")
        
        # 関連プロセスの確認と終了
        print(f"\n🔍 関連プロセスの確認・終了...")
        import subprocess
        
        try:
            # DOGE関連のPythonプロセスを探す
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            
            # DOGEまたはmultiprocessing関連のプロセスを探す
            relevant_processes = []
            for line in lines:
                if ('python' in line and 'multiprocessing' in line and 
                    line.split()[1].isdigit()):  # PIDが数値
                    pid = line.split()[1]
                    relevant_processes.append(pid)
            
            print(f"   Python multiprocessing プロセス: {len(relevant_processes)}件")
            
            # 必要に応じて強制終了オプションを提供
            if len(relevant_processes) > 0:
                print("   🤔 multiprocessingプロセスが実行中です")
                print("   DOGEの処理が完全に停止しない場合は、手動でプロセス終了が必要な場合があります")
                
                # CPU使用率の高いプロセスをチェック
                high_cpu_processes = []
                for line in lines:
                    if 'python' in line and 'multiprocessing' in line:
                        parts = line.split()
                        if len(parts) > 2 and parts[2].replace('.', '').isdigit():
                            cpu_usage = float(parts[2])
                            if cpu_usage > 50:  # 50%以上のCPU使用率
                                high_cpu_processes.append((parts[1], cpu_usage))
                
                if high_cpu_processes:
                    print(f"   ⚠️ 高CPU使用率プロセス: {len(high_cpu_processes)}件")
                    for pid, cpu in high_cpu_processes:
                        print(f"     PID {pid}: CPU {cpu}%")
                    
                    # 強制終了の確認（自動実行）
                    print("   🛑 高CPU使用率プロセスを自動終了します...")
                    for pid, cpu in high_cpu_processes:
                        try:
                            subprocess.run(['kill', '-TERM', pid], check=True)
                            print(f"     ✅ PID {pid} を終了")
                            time.sleep(1)  # 少し待機
                        except subprocess.CalledProcessError:
                            try:
                                subprocess.run(['kill', '-KILL', pid], check=True)
                                print(f"     ✅ PID {pid} を強制終了")
                            except subprocess.CalledProcessError:
                                print(f"     ❌ PID {pid} 終了失敗")
                else:
                    print("   ✅ 高CPU使用率プロセスなし")
                
        except Exception as e:
            print(f"   ⚠️ プロセス確認エラー: {e}")
        
        print(f"\n✅ DOGE処理キャンセル完了 ({cancelled_count}件)")
        print("   DOGEの銘柄追加処理を停止しました")
        return True
        
    except Exception as e:
        print(f"❌ キャンセル処理エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_doge_status():
    """DOGE処理状況の確認"""
    print("\n🔍 DOGE処理状況の確認")
    print("-" * 30)
    
    try:
        from execution_log_database import ExecutionLogDatabase
        
        db = ExecutionLogDatabase()
        
        # 最近のDOGE処理を確認
        executions = db.list_executions(limit=50)
        doge_executions = [
            exec_item for exec_item in executions 
            if exec_item.get('symbol') == 'DOGE'
        ]
        
        print(f"📊 最近のDOGE処理: {len(doge_executions)}件")
        
        status_counts = {}
        for execution in doge_executions[:10]:  # 最新10件
            status = execution.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"   {execution.get('created_at')}: {status}")
        
        print(f"\n📊 ステータス集計:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}件")
        
        # 実行中の処理があるかチェック
        running_count = status_counts.get('RUNNING', 0)
        if running_count == 0:
            print("✅ 実行中のDOGE処理なし - 処理停止完了")
        else:
            print(f"⚠️ 実行中のDOGE処理: {running_count}件")
            
        return running_count == 0
        
    except Exception as e:
        print(f"❌ 状況確認エラー: {e}")
        return False

def force_stop_doge_processes():
    """DOGE関連プロセスの強制停止"""
    print("\n💀 DOGE関連プロセス強制停止")
    print("-" * 40)
    
    try:
        import subprocess
        
        # より積極的にPythonプロセスを探す
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        processes_to_kill = []
        for line in lines:
            if ('python' in line and 
                ('multiprocessing' in line or 'app.py' in line) and
                line.split()[1].isdigit()):
                
                pid = line.split()[1]
                cpu_usage = line.split()[2] if len(line.split()) > 2 else "0"
                processes_to_kill.append((pid, cpu_usage, line))
        
        if not processes_to_kill:
            print("✅ 強制停止対象のプロセスなし")
            return True
        
        print(f"🎯 強制停止対象: {len(processes_to_kill)}プロセス")
        
        for pid, cpu, full_line in processes_to_kill:
            print(f"   PID {pid}: CPU {cpu}%")
            try:
                subprocess.run(['kill', '-TERM', pid], check=True)
                print(f"     ✅ PID {pid} を終了")
                time.sleep(0.5)
            except subprocess.CalledProcessError:
                try:
                    subprocess.run(['kill', '-KILL', pid], check=True)
                    print(f"     ⚡ PID {pid} を強制終了")
                except subprocess.CalledProcessError:
                    print(f"     ❌ PID {pid} 終了失敗")
        
        print("✅ プロセス強制停止完了")
        return True
        
    except Exception as e:
        print(f"❌ 強制停止エラー: {e}")
        return False

def main():
    """メイン実行"""
    print("🛑 DOGE銘柄処理停止ツール")
    print("=" * 80)
    print("実行中のDOGE銘柄追加を緊急停止")
    print("=" * 80)
    
    # 現在の状況確認
    status_ok = verify_doge_status()
    
    if status_ok:
        print("\n✅ DOGE処理は既に停止済み")
        return True
    
    # 通常のキャンセル実行
    print("\n🛑 Phase 1: 通常キャンセル実行")
    cancel_success = cancel_doge_processing()
    
    # 少し待機してから再確認
    time.sleep(3)
    status_ok = verify_doge_status()
    
    if status_ok:
        print("\n✅ DOGE処理停止成功")
        return True
    
    # まだ実行中の場合は強制停止
    print("\n💀 Phase 2: 強制停止実行")
    force_success = force_stop_doge_processes()
    
    # 最終確認
    time.sleep(2)
    final_status = verify_doge_status()
    
    if final_status:
        print("\n✅ DOGE処理完全停止成功")
        print("   DOGEの銘柄追加処理が停止されました")
        return True
    else:
        print("\n⚠️ DOGE処理の一部が残っている可能性があります")
        print("   システム再起動を検討してください")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)