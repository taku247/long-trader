#!/usr/bin/env python3
"""
プロセス実行時間の詳細計測ツール
各ステップの実行時間とボトルネックを特定
"""

import time
import os
import psutil
import subprocess
import threading
import logging
from datetime import datetime, timezone
import json
import signal
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProcessTimingProfiler:
    def __init__(self):
        self.timing_data = []
        self.process_stats = []
        self.step_timings = {}
        self.resource_usage = []
        
    def profile_step(self, step_name):
        """ステップ実行時間の計測デコレータ"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                step_start = time.time()
                cpu_start = psutil.cpu_percent()
                memory_start = psutil.virtual_memory().percent
                
                logger.info(f"🏁 ステップ開始: {step_name}")
                
                try:
                    result = func(*args, **kwargs)
                    
                    step_end = time.time()
                    step_duration = step_end - step_start
                    cpu_end = psutil.cpu_percent()
                    memory_end = psutil.virtual_memory().percent
                    
                    self.timing_data.append({
                        'step': step_name,
                        'duration': step_duration,
                        'start_time': step_start,
                        'end_time': step_end,
                        'cpu_usage': {'start': cpu_start, 'end': cpu_end},
                        'memory_usage': {'start': memory_start, 'end': memory_end},
                        'success': True
                    })
                    
                    logger.info(f"✅ ステップ完了: {step_name} ({step_duration:.3f}秒)")
                    return result
                    
                except Exception as e:
                    step_end = time.time()
                    step_duration = step_end - step_start
                    
                    self.timing_data.append({
                        'step': step_name,
                        'duration': step_duration,
                        'start_time': step_start,
                        'end_time': step_end,
                        'success': False,
                        'error': str(e)
                    })
                    
                    logger.error(f"❌ ステップ失敗: {step_name} ({step_duration:.3f}秒) - {e}")
                    raise
                    
            return wrapper
        return decorator
    
    def monitor_system_resources(self, duration_seconds=60):
        """システムリソースをリアルタイム監視"""
        logger.info(f"📊 システムリソース監視開始 ({duration_seconds}秒)")
        
        def monitor_loop():
            start_time = time.time()
            while time.time() - start_time < duration_seconds:
                try:
                    current_time = time.time()
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    memory = psutil.virtual_memory()
                    disk_io = psutil.disk_io_counters()
                    
                    # Pythonプロセスの詳細監視
                    python_processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                        try:
                            if 'python' in proc.info['name'].lower():
                                python_processes.append(proc.info)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    self.resource_usage.append({
                        'timestamp': current_time,
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_available': memory.available,
                        'disk_read_bytes': disk_io.read_bytes if disk_io else 0,
                        'disk_write_bytes': disk_io.write_bytes if disk_io else 0,
                        'python_processes': len(python_processes),
                        'python_cpu_total': sum(p.get('cpu_percent', 0) for p in python_processes)
                    })
                    
                    time.sleep(0.5)  # 500ms間隔
                    
                except Exception as e:
                    logger.warning(f"リソース監視エラー: {e}")
                    
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        return monitor_thread
    
    def profile_multiprocess_execution(self, symbol="PROFILE_TEST"):
        """マルチプロセス実行の詳細プロファイル"""
        logger.info(f"🚀 マルチプロセス実行プロファイル開始: {symbol}")
        
        # システムリソース監視開始
        monitor_thread = self.monitor_system_resources(duration_seconds=120)
        
        # プロファイル実行
        execution_start = time.time()
        
        try:
            # 実際のauto_symbol_training.pyを詳細ログ付きで実行
            execution_id = f"profile_{symbol}_{int(time.time())}"
            
            process = subprocess.Popen([
                'python', 'auto_symbol_training.py',
                '--symbol', symbol,
                '--execution-id', execution_id
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, 
               env={**os.environ, 'PYTHONUNBUFFERED': '1'})
            
            # プロセス詳細監視
            process_start = time.time()
            self.process_stats.append({
                'pid': process.pid,
                'symbol': symbol,
                'execution_id': execution_id,
                'start_time': process_start
            })
            
            # リアルタイムログ解析
            step_patterns = {
                'data_validation': '✅.*validated',
                'data_fetch': 'Fetching historical data',
                'backtest_start': '🎯 実データによる戦略分析を開始',
                'analysis_loop': '条件ベース分析開始',
                'signal_detection': '支持線・抵抗線が検出されませんでした',
                'db_update': 'シグナルなしとして記録します',
                'completion': 'training completed'
            }
            
            detected_steps = {}
            output_lines = []
            
            # リアルタイム出力監視
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                    
                if output:
                    line = output.strip()
                    output_lines.append({
                        'timestamp': time.time(),
                        'content': line
                    })
                    
                    # ステップ検出
                    for step_name, pattern in step_patterns.items():
                        if pattern in line and step_name not in detected_steps:
                            step_time = time.time()
                            detected_steps[step_name] = {
                                'timestamp': step_time,
                                'elapsed': step_time - process_start,
                                'line': line
                            }
                            logger.info(f"📍 ステップ検出: {step_name} ({step_time - process_start:.3f}秒)")
            
            # プロセス完了待機
            stdout, stderr = process.communicate(timeout=180)  # 3分タイムアウト
            
            execution_end = time.time()
            total_execution_time = execution_end - execution_start
            
            # 結果分析
            self.step_timings[symbol] = {
                'total_time': total_execution_time,
                'return_code': process.returncode,
                'detected_steps': detected_steps,
                'output_lines': len(output_lines),
                'stderr': stderr if stderr else None
            }
            
            logger.info(f"📊 プロファイル完了: {symbol} ({total_execution_time:.3f}秒)")
            
            # ステップ間隔の分析
            self.analyze_step_intervals(detected_steps, process_start)
            
            return total_execution_time, process.returncode
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ プロセスタイムアウト: {symbol}")
            process.kill()
            execution_end = time.time()
            return execution_end - execution_start, -1
            
        except Exception as e:
            execution_end = time.time()
            logger.error(f"❌ プロファイル実行エラー: {e}")
            return execution_end - execution_start, -1
    
    def analyze_step_intervals(self, detected_steps, process_start):
        """ステップ間隔の詳細分析"""
        logger.info("🔍 ステップ間隔分析")
        
        # ステップの時系列順ソート
        sorted_steps = sorted(detected_steps.items(), key=lambda x: x[1]['timestamp'])
        
        prev_time = process_start
        for i, (step_name, step_data) in enumerate(sorted_steps):
            step_time = step_data['timestamp']
            interval = step_time - prev_time
            
            logger.info(f"  {i+1}. {step_name}: +{interval:.3f}秒 (累計: {step_data['elapsed']:.3f}秒)")
            
            # 異常に長い間隔を検出
            if interval > 5.0:
                logger.warning(f"    ⚠️ 長時間間隔検出: {interval:.3f}秒")
            
            prev_time = step_time
    
    def profile_db_operations_timing(self):
        """DB操作の詳細タイミング分析"""
        logger.info("🗃️ DB操作タイミング分析")
        
        # 直接scalable_analysis_systemの_create_no_signal_recordを呼び出して計測
        try:
            from auto_symbol_training import AutoSymbolTraining
            
            trainer = AutoSymbolTraining()
            symbol = "TIMING_TEST"
            execution_id = f"db_timing_{int(time.time())}"
            
            # テスト用設定
            configs = [
                {'symbol': symbol, 'timeframe': '1h', 'strategy': f'Strategy_{i}'}
                for i in range(30)
            ]
            
            # DB操作のタイミング計測
            db_start = time.time()
            
            for i, config in enumerate(configs):
                operation_start = time.time()
                
                try:
                    trainer._create_no_signal_record(symbol, config, execution_id)
                    operation_end = time.time()
                    operation_time = operation_end - operation_start
                    
                    self.timing_data.append({
                        'operation': f'db_update_{i}',
                        'duration': operation_time,
                        'success': True,
                        'config': config['strategy']
                    })
                    
                    if operation_time > 0.1:
                        logger.warning(f"⚠️ 長時間DB操作: {config['strategy']} ({operation_time:.3f}秒)")
                
                except Exception as e:
                    operation_end = time.time()
                    operation_time = operation_end - operation_start
                    
                    logger.error(f"❌ DB操作エラー: {config['strategy']} - {e}")
                    self.timing_data.append({
                        'operation': f'db_update_{i}',
                        'duration': operation_time,
                        'success': False,
                        'error': str(e),
                        'config': config['strategy']
                    })
            
            db_end = time.time()
            total_db_time = db_end - db_start
            
            logger.info(f"📊 DB操作完了: 30回更新 ({total_db_time:.3f}秒)")
            
            # クリーンアップ
            try:
                import sqlite3
                from pathlib import Path
                
                db_path = Path(__file__).parent / "large_scale_analysis" / "analysis.db"
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM analyses WHERE symbol = ?", (symbol,))
                    conn.commit()
                logger.info("🧹 テストレコード削除完了")
            except Exception as e:
                logger.warning(f"⚠️ クリーンアップ失敗: {e}")
                
        except Exception as e:
            logger.error(f"❌ DB操作分析エラー: {e}")
    
    def generate_timing_report(self):
        """詳細タイミングレポート生成"""
        print("\n" + "="*70)
        print("📊 プロセス実行時間詳細分析レポート")
        print("="*70)
        
        # 1. 全体実行時間サマリー
        if self.step_timings:
            print(f"\n🚀 実行時間サマリー:")
            for symbol, timing in self.step_timings.items():
                print(f"  {symbol}: {timing['total_time']:.3f}秒 (終了コード: {timing['return_code']})")
                
                if timing['detected_steps']:
                    print(f"    検出ステップ数: {len(timing['detected_steps'])}個")
                    
                    # 最初と最後のステップ
                    steps_sorted = sorted(timing['detected_steps'].items(), 
                                        key=lambda x: x[1]['timestamp'])
                    if len(steps_sorted) >= 2:
                        first_step = steps_sorted[0]
                        last_step = steps_sorted[-1]
                        active_duration = last_step[1]['elapsed'] - first_step[1]['elapsed']
                        print(f"    アクティブ期間: {active_duration:.3f}秒")
        
        # 2. DB操作統計
        db_operations = [t for t in self.timing_data if t.get('operation', '').startswith('db_update')]
        if db_operations:
            db_times = [op['duration'] for op in db_operations if op['success']]
            db_errors = [op for op in db_operations if not op['success']]
            
            print(f"\n🗃️ DB操作統計:")
            print(f"  総操作数: {len(db_operations)}回")
            print(f"  成功: {len(db_times)}回")
            print(f"  エラー: {len(db_errors)}回")
            
            if db_times:
                avg_db_time = sum(db_times) / len(db_times)
                max_db_time = max(db_times)
                total_db_time = sum(db_times)
                
                print(f"  平均時間: {avg_db_time:.3f}秒")
                print(f"  最大時間: {max_db_time:.3f}秒")
                print(f"  総時間: {total_db_time:.3f}秒")
                
                if max_db_time > 0.1:
                    print(f"  ⚠️ 長時間操作検出: {max_db_time:.3f}秒")
        
        # 3. システムリソース統計
        if self.resource_usage:
            cpu_usage = [r['cpu_percent'] for r in self.resource_usage]
            memory_usage = [r['memory_percent'] for r in self.resource_usage]
            python_processes = [r['python_processes'] for r in self.resource_usage]
            
            print(f"\n💻 システムリソース統計:")
            print(f"  CPU使用率: 平均{sum(cpu_usage)/len(cpu_usage):.1f}%, 最大{max(cpu_usage):.1f}%")
            print(f"  メモリ使用率: 平均{sum(memory_usage)/len(memory_usage):.1f}%, 最大{max(memory_usage):.1f}%")
            print(f"  Pythonプロセス数: 平均{sum(python_processes)/len(python_processes):.1f}個, 最大{max(python_processes)}個")
        
        # 4. ボトルネック分析
        print(f"\n🔍 ボトルネック分析:")
        
        long_operations = [t for t in self.timing_data if t.get('duration', 0) > 1.0]
        if long_operations:
            print(f"  長時間操作 (>1秒): {len(long_operations)}個")
            for op in sorted(long_operations, key=lambda x: x['duration'], reverse=True)[:5]:
                print(f"    {op.get('step', op.get('operation', 'unknown'))}: {op['duration']:.3f}秒")
        else:
            print(f"  ✅ 長時間操作は検出されませんでした")
        
        # 5. 結論
        print(f"\n📋 分析結論:")
        if any(timing['total_time'] < 10 for timing in self.step_timings.values()):
            print(f"  🚨 高速完了を確認: システムが予期せず早期終了している")
            print(f"  📊 推定原因: プロセス競合、DB制限、または例外による中断")
        else:
            print(f"  ✅ 正常な実行時間を確認")
        
        print("="*70)

def main():
    """メイン実行"""
    profiler = ProcessTimingProfiler()
    
    print("⏱️ プロセス実行時間詳細計測ツール")
    print("="*70)
    
    try:
        # 1. DB操作タイミング分析
        print("\n🗃️ テスト1: DB操作タイミング分析")
        profiler.profile_db_operations_timing()
        
        # 2. マルチプロセス実行プロファイル
        print("\n🚀 テスト2: マルチプロセス実行プロファイル")
        execution_time, return_code = profiler.profile_multiprocess_execution("PEPE")
        
        # 3. レポート生成
        print("\n📊 詳細レポート生成中...")
        time.sleep(2)  # ログ収集待機
        profiler.generate_timing_report()
        
    except KeyboardInterrupt:
        print("\n🛑 計測を中断しました")
        profiler.generate_timing_report()
        
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        profiler.generate_timing_report()

if __name__ == "__main__":
    main()