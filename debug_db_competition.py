#!/usr/bin/env python3
"""
DB競合仮説の検証ツール
SQLite並行処理制限とプロセス競合を詳細監視
"""

import sqlite3
import time
import os
import threading
import logging
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import signal
import sys

# SQLiteの詳細ログを有効化
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DBCompetitionValidator:
    def __init__(self):
        self.db_path = Path(__file__).parent / "large_scale_analysis" / "analysis.db"
        self.lock_errors = []
        self.timing_data = []
        self.process_monitors = []
        
    def setup_sqlite_debug_logging(self):
        """SQLiteの詳細ログを設定"""
        try:
            # SQLiteのデバッグログを有効化
            import sqlite3
            
            # SQLite接続でデバッグ情報を有効化
            def trace_callback(statement):
                logger.debug(f"SQL実行: {statement}")
            
            # SQLiteロック情報の監視
            def progress_callback(status, remaining, total):
                if status == sqlite3.SQLITE_BUSY:
                    logger.warning(f"SQLite BUSY検出: 残り{remaining}/{total}")
                    self.lock_errors.append({
                        'timestamp': datetime.now(),
                        'status': 'SQLITE_BUSY',
                        'remaining': remaining,
                        'total': total
                    })
            
            self.trace_callback = trace_callback
            self.progress_callback = progress_callback
            
            logger.info("✅ SQLiteデバッグログ設定完了")
            
        except Exception as e:
            logger.error(f"SQLiteデバッグログ設定エラー: {e}")
    
    def monitor_db_connections(self):
        """DB接続状況をリアルタイム監視"""
        logger.info("🔍 DB接続監視開始")
        
        def monitor_loop():
            while True:
                try:
                    # DB接続テスト
                    start_time = time.time()
                    
                    with sqlite3.connect(self.db_path, timeout=1.0) as conn:
                        conn.set_trace_callback(self.trace_callback)
                        cursor = conn.cursor()
                        
                        # 簡単なクエリで接続テスト
                        cursor.execute("SELECT COUNT(*) FROM analyses")
                        result = cursor.fetchone()
                        
                    end_time = time.time()
                    connection_time = end_time - start_time
                    
                    self.timing_data.append({
                        'timestamp': datetime.now(),
                        'connection_time': connection_time,
                        'success': True,
                        'records': result[0] if result else 0
                    })
                    
                    if connection_time > 0.1:
                        logger.warning(f"⚠️ DB接続時間異常: {connection_time:.3f}秒")
                    
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) or "busy" in str(e):
                        logger.error(f"🔴 DB競合検出: {e}")
                        self.lock_errors.append({
                            'timestamp': datetime.now(),
                            'error': str(e),
                            'type': 'connection_lock'
                        })
                    else:
                        logger.error(f"❌ DB接続エラー: {e}")
                
                except Exception as e:
                    logger.error(f"❌ 監視エラー: {e}")
                
                time.sleep(0.5)  # 500ms間隔で監視
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        return monitor_thread
    
    def test_concurrent_updates(self, symbol="TEST_DB_CONCURRENCY"):
        """並行DB更新のテスト"""
        logger.info(f"🧪 並行DB更新テスト開始: {symbol}")
        
        # テスト用レコードを作成
        execution_id = f"test_concurrent_{int(time.time())}"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Pre-taskレコード作成
                for i in range(30):  # 実際の戦略数と同じ
                    cursor.execute('''
                        INSERT INTO analyses 
                        (symbol, timeframe, config, task_status, execution_id, status)
                        VALUES (?, ?, ?, 'pending', ?, 'running')
                    ''', (symbol, f'1h', f'Strategy_{i}', execution_id))
                
                conn.commit()
                logger.info(f"✅ テスト用Pre-task作成完了: 30レコード")
        
        except Exception as e:
            logger.error(f"❌ テスト用レコード作成失敗: {e}")
            return
        
        # 並行更新のシミュレーション
        def update_worker(strategy_id):
            worker_start = time.time()
            try:
                with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                    conn.set_trace_callback(self.trace_callback)
                    cursor = conn.cursor()
                    
                    # 実際の_create_no_signal_recordと同じUPDATE文
                    cursor.execute("""
                        UPDATE analyses SET
                            task_status = 'completed', task_completed_at = ?,
                            total_return = ?, sharpe_ratio = ?, max_drawdown = ?, win_rate = ?, total_trades = ?,
                            status = 'no_signal', error_message = ?
                        WHERE symbol = ? AND timeframe = ? AND config = ? AND execution_id = ? AND task_status = 'pending'
                    """, (
                        datetime.now(timezone.utc).isoformat(),
                        0.0, 0.0, 0.0, 0.0, 0,
                        'No trading signals detected',
                        symbol, '1h', f'Strategy_{strategy_id}', execution_id
                    ))
                    
                    conn.commit()
                    
                worker_end = time.time()
                worker_time = worker_end - worker_start
                
                logger.info(f"✅ Worker {strategy_id}: 更新完了 ({worker_time:.3f}秒)")
                
                self.timing_data.append({
                    'timestamp': datetime.now(),
                    'worker_id': strategy_id,
                    'update_time': worker_time,
                    'success': True
                })
                
            except sqlite3.OperationalError as e:
                worker_end = time.time()
                worker_time = worker_end - worker_start
                
                logger.error(f"🔴 Worker {strategy_id}: DB競合エラー ({worker_time:.3f}秒) - {e}")
                
                self.lock_errors.append({
                    'timestamp': datetime.now(),
                    'worker_id': strategy_id,
                    'error': str(e),
                    'type': 'update_lock',
                    'duration': worker_time
                })
                
            except Exception as e:
                worker_end = time.time()
                worker_time = worker_end - worker_start
                
                logger.error(f"❌ Worker {strategy_id}: 更新エラー ({worker_time:.3f}秒) - {e}")
        
        # 30個の並行スレッドで同時更新（実際の処理を模擬）
        threads = []
        concurrent_start = time.time()
        
        for i in range(30):
            thread = threading.Thread(target=update_worker, args=(i,))
            threads.append(thread)
            thread.start()
            
            # わずかな間隔で起動（実際の処理に近づける）
            time.sleep(0.01)
        
        # 全スレッドの完了を待機
        for thread in threads:
            thread.join(timeout=10)  # 10秒でタイムアウト
        
        concurrent_end = time.time()
        total_time = concurrent_end - concurrent_start
        
        logger.info(f"📊 並行更新テスト完了: 総時間 {total_time:.3f}秒")
        
        # テスト後のクリーンアップ
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM analyses WHERE symbol = ?", (symbol,))
                conn.commit()
                logger.info(f"🧹 テストレコード削除完了")
        except Exception as e:
            logger.warning(f"⚠️ テストレコード削除失敗: {e}")
    
    def monitor_real_execution(self, symbol="HYPE"):
        """実際の銘柄追加処理を監視"""
        logger.info(f"🔍 実際の実行監視開始: {symbol}")
        
        # 監視開始
        monitor_thread = self.monitor_db_connections()
        
        # 実際のauto_symbol_training.pyを実行
        logger.info(f"🚀 {symbol} 分析実行開始...")
        
        start_time = time.time()
        
        try:
            # サブプロセスで実行
            process = subprocess.Popen([
                'python', 'auto_symbol_training.py',
                '--symbol', symbol,
                '--execution-id', f'debug_monitor_{int(time.time())}'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # プロセス監視
            self.process_monitors.append({
                'pid': process.pid,
                'start_time': start_time,
                'symbol': symbol
            })
            
            # リアルタイムログ出力
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    logger.info(f"📋 実行ログ: {output.strip()}")
            
            # 完了まで待機
            stdout, stderr = process.communicate(timeout=60)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            logger.info(f"📊 実行完了: {execution_time:.3f}秒")
            
            if stderr:
                logger.error(f"🔴 実行エラー: {stderr}")
            
            return execution_time, process.returncode
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ 実行タイムアウト: {symbol}")
            process.kill()
            return None, -1
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.error(f"❌ 実行エラー: {e} ({execution_time:.3f}秒)")
            return execution_time, -1
    
    def generate_report(self):
        """監視結果のレポート生成"""
        logger.info("📊 監視結果レポート生成")
        
        print("\n" + "="*60)
        print("🔍 DB競合監視結果レポート")
        print("="*60)
        
        # 1. DB競合エラーの統計
        print(f"\n🔴 DB競合・ロックエラー: {len(self.lock_errors)}件")
        for error in self.lock_errors[-5:]:  # 最新5件
            print(f"  {error['timestamp'].strftime('%H:%M:%S.%f')[:-3]} - {error.get('type', 'unknown')}: {error.get('error', error.get('status', 'N/A'))}")
        
        # 2. DB接続時間の統計
        if self.timing_data:
            connection_times = [t['connection_time'] for t in self.timing_data if 'connection_time' in t]
            update_times = [t['update_time'] for t in self.timing_data if 'update_time' in t]
            
            if connection_times:
                avg_connection = sum(connection_times) / len(connection_times)
                max_connection = max(connection_times)
                print(f"\n⏱️ DB接続時間統計:")
                print(f"  平均: {avg_connection:.3f}秒")
                print(f"  最大: {max_connection:.3f}秒")
                print(f"  測定回数: {len(connection_times)}回")
            
            if update_times:
                avg_update = sum(update_times) / len(update_times)
                max_update = max(update_times)
                print(f"\n🔄 DB更新時間統計:")
                print(f"  平均: {avg_update:.3f}秒")
                print(f"  最大: {max_update:.3f}秒")
                print(f"  更新回数: {len(update_times)}回")
        
        # 3. プロセス実行統計
        if self.process_monitors:
            print(f"\n🚀 プロセス実行監視: {len(self.process_monitors)}件")
            for proc in self.process_monitors:
                print(f"  PID {proc['pid']}: {proc['symbol']} (開始: {datetime.fromtimestamp(proc['start_time']).strftime('%H:%M:%S')})")
        
        # 4. 結論
        print(f"\n📋 分析結果:")
        if len(self.lock_errors) > 0:
            print(f"  🔴 DB競合が検出されました ({len(self.lock_errors)}件)")
            print(f"  ✅ 仮説: SQLite並行処理制限が5秒完了の原因である可能性が高い")
        else:
            print(f"  ✅ DB競合は検出されませんでした")
            print(f"  ❓ 他の要因を調査する必要があります")
        
        print("="*60)

def main():
    """メイン実行"""
    validator = DBCompetitionValidator()
    
    print("🔍 DB競合仮説検証ツール")
    print("="*60)
    
    try:
        # 1. SQLiteデバッグログ設定
        validator.setup_sqlite_debug_logging()
        
        # 2. 並行更新テスト
        print("\n🧪 テスト1: 並行DB更新テスト")
        validator.test_concurrent_updates()
        
        # 3. 実際の実行監視
        print("\n🔍 テスト2: 実際の銘柄追加監視")
        execution_time, return_code = validator.monitor_real_execution("DOGE")
        
        if execution_time:
            print(f"📊 実行結果: {execution_time:.3f}秒, 終了コード: {return_code}")
        
        # 短時間待機してログ収集
        print("\n⏳ ログ収集待機中...")
        time.sleep(5)
        
        # 4. レポート生成
        validator.generate_report()
        
    except KeyboardInterrupt:
        print("\n🛑 監視を中断しました")
        validator.generate_report()
    
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        validator.generate_report()

if __name__ == "__main__":
    main()