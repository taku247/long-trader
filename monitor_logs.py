#!/usr/bin/env python3
"""
ログモニタリングツール
システムログとプロセスログをリアルタイムで監視
"""

import sys
import time
import subprocess
import threading
from pathlib import Path
import argparse
from datetime import datetime

class LogMonitor:
    """ログファイルのリアルタイム監視"""
    
    def __init__(self):
        self.log_files = {
            'dashboard': 'dashboard.log',
            'system': 'system.log',
            'execution': 'execution_logs.db'  # SQLiteは別途処理
        }
        self.monitoring = False
        
    def tail_file(self, filepath: str, name: str):
        """ファイルの末尾をリアルタイム表示"""
        try:
            # tail -f コマンドを使用
            process = subprocess.Popen(
                ['tail', '-f', filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            print(f"📋 {name}ログ監視開始: {filepath}")
            
            for line in iter(process.stdout.readline, ''):
                if not self.monitoring:
                    break
                    
                # タイムスタンプ付きで表示
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] {name}: {line.strip()}")
                
        except FileNotFoundError:
            print(f"⚠️  {name}ログファイルが見つかりません: {filepath}")
        except Exception as e:
            print(f"❌ {name}ログ監視エラー: {e}")
    
    def monitor_execution_db(self):
        """実行ログデータベースを定期的にチェック"""
        import sqlite3
        
        last_execution_id = None
        
        while self.monitoring:
            try:
                conn = sqlite3.connect('execution_logs.db')
                cursor = conn.cursor()
                
                # 最新の実行ログを取得
                cursor.execute("""
                    SELECT execution_id, symbol, status, current_operation, progress_percentage
                    FROM execution_logs 
                    WHERE status = 'RUNNING'
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                
                running_executions = cursor.fetchall()
                
                if running_executions:
                    for exec_id, symbol, status, operation, progress in running_executions:
                        if exec_id != last_execution_id:
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            print(f"[{timestamp}] 実行中: {symbol} - {operation or '処理中'} ({progress:.1f}%)")
                            last_execution_id = exec_id
                
                conn.close()
                
            except Exception as e:
                print(f"DB監視エラー: {e}")
                
            time.sleep(5)  # 5秒ごとにチェック
    
    def start_monitoring(self):
        """すべてのログ監視を開始"""
        self.monitoring = True
        
        print("=" * 60)
        print("🔍 Long Trader ログモニター")
        print("=" * 60)
        print("監視中のログ:")
        print("- dashboard.log: Web APIとプロセス実行")
        print("- system.log: システム全体のログ")
        print("- execution_logs.db: 実行状況データベース")
        print("\nCtrl+Cで終了")
        print("=" * 60)
        
        threads = []
        
        # 各ログファイルを別スレッドで監視
        for name, filepath in self.log_files.items():
            if filepath.endswith('.db'):
                # データベースは特別処理
                thread = threading.Thread(
                    target=self.monitor_execution_db,
                    daemon=True
                )
            else:
                # 通常のログファイル
                thread = threading.Thread(
                    target=self.tail_file,
                    args=(filepath, name),
                    daemon=True
                )
            
            thread.start()
            threads.append(thread)
        
        try:
            # メインスレッドで待機
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n👋 ログ監視を終了します")
            self.monitoring = False
            
            # スレッドの終了を待つ
            for thread in threads:
                thread.join(timeout=2)

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='Long Traderログモニター')
    parser.add_argument('--file', help='特定のログファイルのみ監視')
    parser.add_argument('--follow-symbol', help='特定のシンボルの実行を追跡')
    
    args = parser.parse_args()
    
    monitor = LogMonitor()
    
    if args.file:
        # 特定ファイルのみ
        monitor.tail_file(args.file, Path(args.file).stem)
    else:
        # すべて監視
        monitor.start_monitoring()

if __name__ == "__main__":
    main()