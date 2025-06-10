#!/usr/bin/env python3
"""
スケジューラーのデモ実行
"""

import sys
import os

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduled_execution_system import ScheduledExecutionSystem


def main():
    print("=== Long Trader 定期実行システム デモ ===")
    
    # スケジューラー作成
    scheduler = ScheduledExecutionSystem()
    
    # 設定されたタスクを表示
    status = scheduler.get_task_status()
    print(f"\n📅 設定されたタスク: {status['total_tasks']}個")
    print(f"🟢 有効なタスク: {status['enabled_tasks']}個")
    print(f"🔴 失敗したタスク: {status['failed_tasks']}個")
    
    print("\n--- タスク一覧 ---")
    for task in status['tasks']:
        print(f"• {task['task_id']}")
        print(f"  タイプ: {task['type']}")
        print(f"  頻度: {task['frequency']}")
        print(f"  状態: {'有効' if task['enabled'] else '無効'}")
        if task['last_executed']:
            print(f"  前回実行: {task['last_executed']}")
        print()
    
    print("スケジューラーの動作確認が完了しました。")
    print("実際に開始するには scheduler.start_scheduler() を呼び出してください。")


if __name__ == "__main__":
    main()