#!/usr/bin/env python3
"""
SQLite詳細監視ツール
ロック競合、トランザクション、WALモードの分析
"""

import sqlite3
import time
import os
import threading
import logging
import subprocess
from datetime import datetime
from pathlib import Path
import json

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLiteDetailedMonitor:
    def __init__(self):
        self.db_path = Path(__file__).parent / "large_scale_analysis" / "analysis.db"
        self.monitoring_data = []
        self.lock_events = []
        self.transaction_timings = []
        self.connection_pool = []
        
    def enable_sqlite_logging(self):
        """SQLiteの詳細ログを有効化"""
        logger.info("🔧 SQLite詳細ログ設定")
        
        # SQLiteのデバッグビルドでない場合の代替監視方法
        try:
            # WALモードの確認
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA synchronous")
                synchronous = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA cache_size")
                cache_size = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA temp_store")
                temp_store = cursor.fetchone()[0]
                
                logger.info(f"📊 SQLite設定:")
                logger.info(f"  journal_mode: {journal_mode}")
                logger.info(f"  synchronous: {synchronous}")
                logger.info(f"  cache_size: {cache_size}")
                logger.info(f"  temp_store: {temp_store}")
                
                # パフォーマンス最適化の提案
                if journal_mode != 'WAL':
                    logger.warning("⚠️ WALモード未使用 - 並行処理性能が制限される可能性")
                
                return {
                    'journal_mode': journal_mode,
                    'synchronous': synchronous,
                    'cache_size': cache_size,
                    'temp_store': temp_store
                }
                
        except Exception as e:
            logger.error(f"❌ SQLite設定取得エラー: {e}")
            return None
    
    def optimize_sqlite_settings(self):
        """SQLiteのパフォーマンス最適化"""
        logger.info("⚡ SQLite設定最適化")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # WALモードに変更（並行読み取り向上）
                cursor.execute("PRAGMA journal_mode=WAL")
                logger.info("  ✅ WALモード有効化")
                
                # 同期設定の最適化
                cursor.execute("PRAGMA synchronous=NORMAL")
                logger.info("  ✅ 同期モード最適化")
                
                # キャッシュサイズ増加
                cursor.execute("PRAGMA cache_size=10000")
                logger.info("  ✅ キャッシュサイズ増加")
                
                # 一時ストレージをメモリに
                cursor.execute("PRAGMA temp_store=MEMORY")
                logger.info("  ✅ 一時ストレージメモリ化")
                
                # 接続タイムアウト設定
                conn.execute("PRAGMA busy_timeout=30000")  # 30秒
                logger.info("  ✅ ビジータイムアウト設定")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ SQLite最適化エラー: {e}")
    
    def monitor_database_locks(self, duration_seconds=60):
        """データベースロック状況の監視"""
        logger.info(f"🔒 データベースロック監視開始 ({duration_seconds}秒)")
        
        def lock_monitor():
            start_time = time.time()
            connection_attempts = 0
            successful_connections = 0
            lock_timeouts = 0
            
            while time.time() - start_time < duration_seconds:
                try:
                    connection_attempts += 1
                    lock_start = time.time()
                    
                    # タイムアウト付きDB接続テスト
                    with sqlite3.connect(self.db_path, timeout=1.0) as conn:
                        conn.execute("PRAGMA busy_timeout=1000")  # 1秒
                        cursor = conn.cursor()
                        
                        # 軽いクエリでロック状況テスト
                        cursor.execute("SELECT COUNT(*) FROM analyses WHERE task_status='pending'")
                        result = cursor.fetchone()
                        
                        successful_connections += 1
                        lock_end = time.time()
                        lock_duration = lock_end - lock_start
                        
                        self.monitoring_data.append({
                            'timestamp': lock_end,
                            'operation': 'connection_test',
                            'duration': lock_duration,
                            'success': True,
                            'pending_tasks': result[0] if result else 0
                        })
                        
                        if lock_duration > 0.1:
                            logger.warning(f"⚠️ 長時間接続: {lock_duration:.3f}秒")
                
                except sqlite3.OperationalError as e:
                    lock_end = time.time()
                    lock_duration = lock_end - lock_start
                    
                    if "database is locked" in str(e) or "busy" in str(e):
                        lock_timeouts += 1
                        logger.error(f"🔴 ロックタイムアウト #{lock_timeouts}: {lock_duration:.3f}秒")
                        
                        self.lock_events.append({
                            'timestamp': lock_end,
                            'error': str(e),
                            'duration': lock_duration,
                            'type': 'lock_timeout'
                        })
                    else:
                        logger.error(f"❌ DB接続エラー: {e}")
                
                except Exception as e:
                    logger.error(f"❌ 監視エラー: {e}")
                
                time.sleep(0.2)  # 200ms間隔
            
            # 監視結果サマリー
            success_rate = (successful_connections / connection_attempts * 100) if connection_attempts > 0 else 0
            logger.info(f"📊 ロック監視完了:")
            logger.info(f"  接続試行: {connection_attempts}回")
            logger.info(f"  成功: {successful_connections}回 ({success_rate:.1f}%)")
            logger.info(f"  ロックタイムアウト: {lock_timeouts}回")
        
        monitor_thread = threading.Thread(target=lock_monitor, daemon=True)
        monitor_thread.start()
        return monitor_thread
    
    def test_concurrent_transactions(self, num_workers=30):
        """並行トランザクションのストレステスト"""
        logger.info(f"🔥 並行トランザクションテスト開始: {num_workers}ワーカー")
        
        test_symbol = f"STRESS_TEST_{int(time.time())}"
        
        def transaction_worker(worker_id):
            worker_start = time.time()
            transaction_success = False
            
            try:
                # 実際の処理と同じ重いトランザクション
                with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                    conn.execute("PRAGMA busy_timeout=10000")  # 10秒
                    cursor = conn.cursor()
                    
                    # BEGIN TRANSACTION
                    trans_start = time.time()
                    
                    # INSERT
                    cursor.execute('''
                        INSERT INTO analyses 
                        (symbol, timeframe, config, task_status, execution_id, status)
                        VALUES (?, ?, ?, 'pending', ?, 'running')
                    ''', (test_symbol, '1h', f'Worker_{worker_id}', f'stress_test_{worker_id}'))
                    
                    # 処理時間をシミュレート
                    time.sleep(0.01)  # 10ms処理時間
                    
                    # UPDATE
                    cursor.execute('''
                        UPDATE analyses SET
                            task_status = 'completed', total_return = ?, sharpe_ratio = ?,
                            status = 'no_signal', error_message = ?
                        WHERE symbol = ? AND timeframe = ? AND config = ?
                    ''', (0.0, 0.0, 'Stress test', test_symbol, '1h', f'Worker_{worker_id}'))
                    
                    # COMMIT
                    conn.commit()
                    trans_end = time.time()
                    
                    transaction_success = True
                    trans_duration = trans_end - trans_start
                    
                    self.transaction_timings.append({
                        'worker_id': worker_id,
                        'duration': trans_duration,
                        'success': True,
                        'start_time': trans_start,
                        'end_time': trans_end
                    })
                    
                    logger.debug(f"✅ Worker {worker_id}: トランザクション成功 ({trans_duration:.3f}秒)")
            
            except sqlite3.OperationalError as e:
                worker_end = time.time()
                worker_duration = worker_end - worker_start
                
                logger.error(f"🔴 Worker {worker_id}: DB競合エラー ({worker_duration:.3f}秒) - {e}")
                
                self.transaction_timings.append({
                    'worker_id': worker_id,
                    'duration': worker_duration,
                    'success': False,
                    'error': str(e),
                    'start_time': worker_start,
                    'end_time': worker_end
                })
                
                self.lock_events.append({
                    'timestamp': worker_end,
                    'worker_id': worker_id,
                    'error': str(e),
                    'type': 'transaction_lock',
                    'duration': worker_duration
                })
            
            except Exception as e:
                worker_end = time.time()
                worker_duration = worker_end - worker_start
                
                logger.error(f"❌ Worker {worker_id}: 予期しないエラー ({worker_duration:.3f}秒) - {e}")
                
                self.transaction_timings.append({
                    'worker_id': worker_id,
                    'duration': worker_duration,
                    'success': False,
                    'error': str(e),
                    'start_time': worker_start,
                    'end_time': worker_end
                })
        
        # 並行実行
        threads = []
        stress_start = time.time()
        
        for i in range(num_workers):
            thread = threading.Thread(target=transaction_worker, args=(i,))
            threads.append(thread)
            thread.start()
            
            # 少しずらして起動（リアルな並行状況を模擬）
            time.sleep(0.01)
        
        # 全完了待機
        for thread in threads:
            thread.join(timeout=30)  # 30秒でタイムアウト
        
        stress_end = time.time()
        total_stress_time = stress_end - stress_start
        
        # 結果分析
        successful_transactions = len([t for t in self.transaction_timings if t['success']])
        failed_transactions = len([t for t in self.transaction_timings if not t['success']])
        
        logger.info(f"📊 並行トランザクションテスト完了:")
        logger.info(f"  総時間: {total_stress_time:.3f}秒")
        logger.info(f"  成功: {successful_transactions}個")
        logger.info(f"  失敗: {failed_transactions}個")
        
        # クリーンアップ
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM analyses WHERE symbol = ?", (test_symbol,))
                conn.commit()
                logger.info("🧹 ストレステストレコード削除完了")
        except Exception as e:
            logger.warning(f"⚠️ クリーンアップ失敗: {e}")
    
    def analyze_wal_file(self):
        """WALファイルの分析"""
        wal_path = Path(str(self.db_path) + "-wal")
        shm_path = Path(str(self.db_path) + "-shm")
        
        logger.info("📁 WALファイル分析")
        
        try:
            if wal_path.exists():
                wal_size = wal_path.stat().st_size
                logger.info(f"  WALファイルサイズ: {wal_size:,} bytes")
                
                if wal_size > 1000000:  # 1MB以上
                    logger.warning(f"⚠️ 大きなWALファイル検出: {wal_size:,} bytes")
                    logger.warning("  WALチェックポイントが必要な可能性")
            else:
                logger.info("  WALファイル: 存在しません")
            
            if shm_path.exists():
                shm_size = shm_path.stat().st_size
                logger.info(f"  SHMファイルサイズ: {shm_size:,} bytes")
            else:
                logger.info("  SHMファイル: 存在しません")
                
        except Exception as e:
            logger.error(f"❌ WALファイル分析エラー: {e}")
    
    def generate_sqlite_report(self):
        """SQLite監視レポート生成"""
        print("\n" + "="*70)
        print("🗃️ SQLite詳細監視レポート")
        print("="*70)
        
        # 1. ロック競合統計
        lock_count = len(self.lock_events)
        print(f"\n🔒 ロック競合統計:")
        print(f"  ロックイベント: {lock_count}件")
        
        if lock_count > 0:
            lock_types = {}
            for event in self.lock_events:
                event_type = event.get('type', 'unknown')
                lock_types[event_type] = lock_types.get(event_type, 0) + 1
            
            for lock_type, count in lock_types.items():
                print(f"    {lock_type}: {count}件")
            
            # 最新5件のロックイベント
            print(f"  最新ロックイベント:")
            for event in self.lock_events[-5:]:
                timestamp = event['timestamp']
                if isinstance(timestamp, float):
                    time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3]
                else:
                    time_str = str(timestamp)
                print(f"    {time_str} - {event.get('type', 'unknown')}: {event.get('error', 'N/A')}")
        
        # 2. トランザクション統計
        if self.transaction_timings:
            successful_trans = [t for t in self.transaction_timings if t['success']]
            failed_trans = [t for t in self.transaction_timings if not t['success']]
            
            print(f"\n💾 トランザクション統計:")
            print(f"  総数: {len(self.transaction_timings)}個")
            print(f"  成功: {len(successful_trans)}個")
            print(f"  失敗: {len(failed_trans)}個")
            
            if successful_trans:
                trans_times = [t['duration'] for t in successful_trans]
                avg_time = sum(trans_times) / len(trans_times)
                max_time = max(trans_times)
                
                print(f"  平均時間: {avg_time:.3f}秒")
                print(f"  最大時間: {max_time:.3f}秒")
                
                if max_time > 1.0:
                    print(f"  ⚠️ 長時間トランザクション検出: {max_time:.3f}秒")
        
        # 3. 接続監視統計
        if self.monitoring_data:
            connection_times = [m['duration'] for m in self.monitoring_data if m['success']]
            
            if connection_times:
                print(f"\n🔌 接続監視統計:")
                print(f"  成功接続: {len(connection_times)}回")
                print(f"  平均接続時間: {sum(connection_times)/len(connection_times):.3f}秒")
                print(f"  最大接続時間: {max(connection_times):.3f}秒")
        
        # 4. SQLite健全性評価
        print(f"\n🏥 SQLite健全性評価:")
        
        # ロック競合率
        total_operations = len(self.monitoring_data) + len(self.transaction_timings)
        if total_operations > 0:
            lock_rate = len(self.lock_events) / total_operations * 100
            print(f"  ロック競合率: {lock_rate:.1f}%")
            
            if lock_rate > 10:
                print(f"  🔴 高いロック競合率 - SQLite並行処理限界の可能性")
            elif lock_rate > 5:
                print(f"  🟡 中程度のロック競合 - 最適化が推奨")
            else:
                print(f"  ✅ 健全なロック競合率")
        
        # 結論
        print(f"\n📋 分析結論:")
        if len(self.lock_events) > 5:
            print(f"  🚨 SQLite並行処理制限が5秒完了の原因である可能性が高い")
            print(f"  💡 推奨対応: WALモード、接続プール、またはPostgreSQLへの移行")
        elif len(self.lock_events) > 0:
            print(f"  ⚠️ 軽微なロック競合検出 - 監視継続が必要")
        else:
            print(f"  ✅ SQLiteロック問題は検出されませんでした")
        
        print("="*70)

def main():
    """メイン実行"""
    monitor = SQLiteDetailedMonitor()
    
    print("🗃️ SQLite詳細監視ツール")
    print("="*70)
    
    try:
        # 1. 現在のSQLite設定確認
        print("\n📊 現在のSQLite設定確認")
        settings = monitor.enable_sqlite_logging()
        
        # 2. SQLite最適化
        print("\n⚡ SQLite設定最適化")
        monitor.optimize_sqlite_settings()
        
        # 3. WALファイル分析
        print("\n📁 WALファイル分析")
        monitor.analyze_wal_file()
        
        # 4. ロック監視開始
        print("\n🔒 ロック監視開始")
        lock_thread = monitor.monitor_database_locks(duration_seconds=30)
        
        # 5. 並行トランザクションテスト
        print("\n🔥 並行トランザクションストレステスト")
        monitor.test_concurrent_transactions(num_workers=30)
        
        # 6. 完了待機
        print("\n⏳ 監視完了待機...")
        time.sleep(5)
        
        # 7. レポート生成
        monitor.generate_sqlite_report()
        
    except KeyboardInterrupt:
        print("\n🛑 監視を中断しました")
        monitor.generate_sqlite_report()
        
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        monitor.generate_sqlite_report()

if __name__ == "__main__":
    main()