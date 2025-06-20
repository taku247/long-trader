#!/usr/bin/env python3
"""
強化されたプロセス健全性監視モジュール
孤児プロセスの定期的な清理とタイムアウト機能を提供
"""

import os
import sys
import time
import signal
import threading
import psutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from execution_log_database import ExecutionLogDatabase, ExecutionStatus
from real_time_system.utils.colored_log import get_colored_logger


@dataclass
class ProcessInfo:
    """プロセス情報"""
    pid: int
    name: str
    cmdline: str
    cpu_percent: float
    memory_mb: float
    create_time: float
    age_minutes: float
    ppid: Optional[int]
    is_orphan: bool
    execution_id: Optional[str]
    symbol: Optional[str]


class EnhancedProcessMonitor:
    """強化されたプロセス健全性監視"""
    
    def __init__(self, check_interval: int = 300, max_execution_hours: int = 6):
        """
        Args:
            check_interval: チェック間隔（秒）
            max_execution_hours: 最大実行時間（時間）
        """
        self.check_interval = check_interval
        self.max_execution_hours = max_execution_hours
        self.logger = get_colored_logger(__name__)
        self.db = ExecutionLogDatabase()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # 監視対象キーワード
        self.target_keywords = [
            'multiprocessing',
            'spawn_main',
            'resource_tracker',
            'scalable_analysis',
            'auto_symbol_training',
            'support_resistance_ml',
            'Pool',
            'Process-'
        ]
        
        # 除外するプロセス（システムプロセスなど）
        self.excluded_processes = {
            'kernel_task',
            'launchd',
            'init',
            'systemd'
        }
        
    def start_monitoring(self):
        """監視を開始"""
        if self._running:
            self.logger.warning("Enhanced process monitor is already running")
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info(f"🔍 Enhanced process monitor started (interval: {self.check_interval}s, max_exec: {self.max_execution_hours}h)")
    
    def stop_monitoring(self):
        """監視を停止"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        self.logger.info("🛑 Enhanced process monitor stopped")
    
    def _monitor_loop(self):
        """監視ループ"""
        while self._running:
            try:
                self._perform_health_check()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Error in enhanced process monitor: {e}")
                time.sleep(min(self.check_interval, 60))  # エラー時は最大1分待機
    
    def _perform_health_check(self):
        """健全性チェックを実行"""
        self.logger.debug("🔍 Performing enhanced health check...")
        
        # 1. 孤児プロセスの清理
        orphan_processes = self._find_orphan_processes()
        if orphan_processes:
            self._cleanup_orphan_processes(orphan_processes)
        
        # 2. 長時間実行プロセスのタイムアウト処理
        long_running_processes = self._find_long_running_processes()
        if long_running_processes:
            self._handle_timeout_processes(long_running_processes)
        
        # 3. データベースの実行記録と実際のプロセスの整合性チェック
        self._check_db_process_consistency()
        
        # 4. 統計情報の更新
        self._update_process_statistics()
    
    def _find_orphan_processes(self) -> List[ProcessInfo]:
        """孤児プロセスを検出"""
        orphan_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid', 'create_time']):
            try:
                proc_info = proc.info
                if not proc_info['cmdline']:
                    continue
                
                cmdline_list = proc_info.get('cmdline', [])
                if cmdline_list is None:
                    cmdline_list = []
                cmdline = ' '.join(str(x) for x in cmdline_list)
                
                # Pythonプロセスかつ監視対象キーワードを含む
                if ('python' in proc_info['name'].lower() and 
                    any(keyword in cmdline for keyword in self.target_keywords)):
                    
                    # 除外プロセスをスキップ
                    if proc_info['name'] in self.excluded_processes:
                        continue
                    
                    is_orphan = False
                    
                    # 孤児プロセスの判定
                    ppid = proc_info.get('ppid')
                    if ppid == 1:  # init プロセスの子
                        is_orphan = True
                    elif ppid is None:  # 親プロセスなし
                        is_orphan = True
                    else:
                        try:
                            parent = proc.parent()
                            if parent is None:
                                is_orphan = True
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            is_orphan = True
                    
                    if is_orphan:
                        cpu_percent = proc.cpu_percent()
                        memory_mb = proc.memory_info().rss / 1024 / 1024
                        create_time = proc_info.get('create_time', time.time())
                        age_minutes = (time.time() - create_time) / 60
                        
                        # execution_idとsymbolを推定
                        execution_id = self._extract_execution_id(cmdline)
                        symbol = self._extract_symbol(cmdline)
                        
                        process_info = ProcessInfo(
                            pid=proc_info['pid'],
                            name=proc_info['name'],
                            cmdline=cmdline,
                            cpu_percent=cpu_percent,
                            memory_mb=memory_mb,
                            create_time=create_time,
                            age_minutes=age_minutes,
                            ppid=ppid,
                            is_orphan=True,
                            execution_id=execution_id,
                            symbol=symbol
                        )
                        
                        orphan_processes.append(process_info)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return orphan_processes
    
    def _find_long_running_processes(self) -> List[ProcessInfo]:
        """長時間実行プロセスを検出"""
        long_running_processes = []
        max_age_seconds = self.max_execution_hours * 3600
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid', 'create_time', 'environ']):
            try:
                proc_info = proc.info
                if not proc_info['cmdline']:
                    continue
                
                cmdline_list = proc_info.get('cmdline', [])
                if cmdline_list is None:
                    cmdline_list = []
                cmdline = ' '.join(str(x) for x in cmdline_list)
                
                # 監視対象プロセスかチェック
                if ('python' in proc_info['name'].lower() and 
                    any(keyword in cmdline for keyword in self.target_keywords)):
                    
                    create_time = proc_info.get('create_time', time.time())
                    age_seconds = time.time() - create_time
                    
                    # 最大実行時間を超過
                    if age_seconds > max_age_seconds:
                        cpu_percent = proc.cpu_percent()
                        memory_mb = proc.memory_info().rss / 1024 / 1024
                        age_minutes = age_seconds / 60
                        
                        # execution_idとsymbolを推定
                        execution_id = self._extract_execution_id(cmdline)
                        symbol = self._extract_symbol(cmdline)
                        
                        process_info = ProcessInfo(
                            pid=proc_info['pid'],
                            name=proc_info['name'],
                            cmdline=cmdline,
                            cpu_percent=cpu_percent,
                            memory_mb=memory_mb,
                            create_time=create_time,
                            age_minutes=age_minutes,
                            ppid=proc_info.get('ppid'),
                            is_orphan=False,
                            execution_id=execution_id,
                            symbol=symbol
                        )
                        
                        long_running_processes.append(process_info)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return long_running_processes
    
    def _extract_execution_id(self, cmdline: str) -> Optional[str]:
        """コマンドラインからexecution_idを抽出"""
        import re
        
        # execution_idのパターン（例: symbol_addition_20250620_123456_abcd1234）
        pattern = r'(symbol_addition|scheduled_backtest|manual_execution)_\d{8}_\d{6}_[a-f0-9]{8}'
        match = re.search(pattern, cmdline)
        if match:
            return match.group(0)
        
        # より柔軟なパターン（引数なし形式: scheduled_backtest_20250620_654321_efgh5678）
        pattern2 = r'(symbol_addition|scheduled_backtest|manual_execution)_\d{8}_\d{6}_[a-zA-Z0-9]{8}'
        match = re.search(pattern2, cmdline)
        return match.group(0) if match else None
    
    def _extract_symbol(self, cmdline: str) -> Optional[str]:
        """コマンドラインからsymbolを抽出"""
        import re
        
        # 一般的な暗号通貨シンボルパターン
        symbol_patterns = [
            r'--symbol\s+([A-Z]{2,10})',
            r'-s\s+([A-Z]{2,10})',
            r'symbol[=:]([A-Z]{2,10})',
            r'([A-Z]{2,10})_analysis',
            r'([A-Z]{2,10})_training'
        ]
        
        for pattern in symbol_patterns:
            match = re.search(pattern, cmdline)
            if match:
                return match.group(1)
        
        return None
    
    def _cleanup_orphan_processes(self, orphan_processes: List[ProcessInfo]):
        """孤児プロセスを清理"""
        self.logger.warning(f"🚫 Detected {len(orphan_processes)} orphan processes")
        
        cleaned_count = 0
        
        for proc_info in orphan_processes:
            try:
                proc = psutil.Process(proc_info.pid)
                
                # 5分以上実行されている孤児プロセスのみ清理
                if proc_info.age_minutes > 5:
                    self.logger.warning(
                        f"Terminating orphan process: PID {proc_info.pid} "
                        f"({proc_info.name}, age: {proc_info.age_minutes:.1f}min, "
                        f"CPU: {proc_info.cpu_percent:.1f}%, "
                        f"Memory: {proc_info.memory_mb:.1f}MB)"
                    )
                    
                    # 段階的終了
                    proc.terminate()  # SIGTERM
                    
                    # 3秒待機
                    time.sleep(3)
                    
                    # まだ生きている場合は強制終了
                    if proc.is_running():
                        proc.kill()  # SIGKILL
                        self.logger.warning(f"Force killed orphan process: PID {proc_info.pid}")
                    
                    # データベースの実行記録を更新
                    if proc_info.execution_id:
                        self._update_execution_status_cancelled(proc_info.execution_id, "Orphan process cleanup")
                    
                    cleaned_count += 1
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.logger.debug(f"Could not terminate process {proc_info.pid}: {e}")
                continue
        
        if cleaned_count > 0:
            self.logger.info(f"🧹 Cleaned up {cleaned_count} orphan processes")
    
    def _handle_timeout_processes(self, long_running_processes: List[ProcessInfo]):
        """タイムアウトプロセスを処理"""
        self.logger.warning(f"⏰ Detected {len(long_running_processes)} long-running processes")
        
        timeout_count = 0
        
        for proc_info in long_running_processes:
            try:
                proc = psutil.Process(proc_info.pid)
                
                self.logger.warning(
                    f"Timeout process: PID {proc_info.pid} "
                    f"({proc_info.name}, age: {proc_info.age_minutes:.1f}min, "
                    f"symbol: {proc_info.symbol or 'N/A'})"
                )
                
                # データベースの実行記録を先に更新
                if proc_info.execution_id:
                    self._update_execution_status_cancelled(
                        proc_info.execution_id, 
                        f"Process timeout after {self.max_execution_hours} hours"
                    )
                
                # プロセス終了
                proc.terminate()
                time.sleep(3)
                
                if proc.is_running():
                    proc.kill()
                    self.logger.warning(f"Force killed timeout process: PID {proc_info.pid}")
                
                timeout_count += 1
                
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.logger.debug(f"Could not terminate timeout process {proc_info.pid}: {e}")
                continue
        
        if timeout_count > 0:
            self.logger.info(f"⏰ Terminated {timeout_count} timeout processes")
    
    def _update_execution_status_cancelled(self, execution_id: str, reason: str):
        """実行記録をキャンセル状態に更新"""
        try:
            self.db.update_execution_status(
                execution_id,
                ExecutionStatus.CANCELLED,
                current_operation=f"Auto-cancelled: {reason}"
            )
            
            # エラー情報も追加
            self.db.add_execution_error(execution_id, {
                "error_type": "AutoCancellation",
                "error_message": reason,
                "cancelled_by": "EnhancedProcessMonitor"
            })
            
            self.logger.info(f"Updated execution {execution_id} to CANCELLED: {reason}")
            
        except Exception as e:
            self.logger.error(f"Failed to update execution status for {execution_id}: {e}")
    
    def _check_db_process_consistency(self):
        """データベース記録と実際のプロセスの整合性をチェック"""
        try:
            # 実行中ステータスの記録を取得
            running_executions = self.db.list_executions(
                status="RUNNING",
                limit=100
            )
            
            inconsistent_count = 0
            
            for execution in running_executions:
                execution_id = execution['execution_id']
                symbol = execution.get('symbol')
                
                # 対応するプロセスが存在するかチェック
                process_found = False
                
                for proc in psutil.process_iter(['pid', 'cmdline', 'environ']):
                    try:
                        cmdline_list = proc.info.get('cmdline', [])
                        if cmdline_list is None:
                            cmdline_list = []
                        cmdline = ' '.join(str(x) for x in cmdline_list)
                        environ = proc.info.get('environ', {})
                        
                        if (execution_id in cmdline or 
                            environ.get('CURRENT_EXECUTION_ID') == execution_id or
                            (symbol and symbol in cmdline)):
                            process_found = True
                            break
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # プロセスが見つからない場合、実行記録を修正
                if not process_found:
                    # 1時間以上前の記録のみ修正（最近の記録は起動中の可能性）
                    start_time_str = execution.get('timestamp_start')
                    if start_time_str:
                        start_time = datetime.fromisoformat(start_time_str)
                        age_hours = (datetime.now() - start_time).total_seconds() / 3600
                        
                        if age_hours > 1:
                            self._update_execution_status_cancelled(
                                execution_id,
                                "Process not found during consistency check"
                            )
                            inconsistent_count += 1
                            self.logger.warning(f"Marked stale execution as cancelled: {execution_id}")
            
            if inconsistent_count > 0:
                self.logger.info(f"🔧 Fixed {inconsistent_count} inconsistent execution records")
                
        except Exception as e:
            self.logger.error(f"Error checking DB-process consistency: {e}")
    
    def _update_process_statistics(self):
        """プロセス統計情報を更新"""
        try:
            # 現在実行中のプロセス数をカウント
            target_process_count = 0
            total_cpu_usage = 0
            total_memory_mb = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline_list = proc.info.get('cmdline', [])
                    if cmdline_list is None:
                        cmdline_list = []
                    cmdline = ' '.join(str(x) for x in cmdline_list)
                    
                    if ('python' in proc.info['name'].lower() and 
                        any(keyword in cmdline for keyword in self.target_keywords)):
                        target_process_count += 1
                        total_cpu_usage += proc.cpu_percent()
                        total_memory_mb += proc.memory_info().rss / 1024 / 1024
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # ログ出力（デバッグレベル）
            self.logger.debug(
                f"📊 Process stats: {target_process_count} active processes, "
                f"CPU: {total_cpu_usage:.1f}%, Memory: {total_memory_mb:.1f}MB"
            )
            
        except Exception as e:
            self.logger.error(f"Error updating process statistics: {e}")
    
    def get_process_health_status(self) -> Dict:
        """プロセス健全性ステータスを取得"""
        try:
            orphan_processes = self._find_orphan_processes()
            long_running_processes = self._find_long_running_processes()
            
            # 実行中プロセスの統計
            active_processes = []
            total_cpu = 0
            total_memory = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    proc_info = proc.info
                    cmdline_list = proc_info.get('cmdline', [])
                    if cmdline_list is None:
                        cmdline_list = []
                    cmdline = ' '.join(str(x) for x in cmdline_list)
                    
                    if ('python' in proc.info['name'].lower() and 
                        any(keyword in cmdline for keyword in self.target_keywords)):
                        
                        cpu_percent = proc.cpu_percent()
                        memory_mb = proc.memory_info().rss / 1024 / 1024
                        create_time = proc.info.get('create_time', time.time())
                        age_minutes = (time.time() - create_time) / 60
                        
                        total_cpu += cpu_percent
                        total_memory += memory_mb
                        
                        active_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline,
                            'cpu_percent': cpu_percent,
                            'memory_mb': memory_mb,
                            'age_minutes': age_minutes
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'monitoring_active': self._running,
                'check_interval_seconds': self.check_interval,
                'max_execution_hours': self.max_execution_hours,
                'orphan_processes': len(orphan_processes),
                'long_running_processes': len(long_running_processes),
                'active_processes': len(active_processes),
                'total_cpu_usage': total_cpu,
                'total_memory_mb': total_memory,
                'processes': active_processes
            }
            
        except Exception as e:
            self.logger.error(f"Error getting process health status: {e}")
            return {'error': str(e)}
    
    def manual_cleanup(self) -> Dict:
        """手動でクリーンアップを実行"""
        self.logger.info("🧹 Manual cleanup initiated")
        
        try:
            orphan_processes = self._find_orphan_processes()
            long_running_processes = self._find_long_running_processes()
            
            # 清理実行
            if orphan_processes:
                self._cleanup_orphan_processes(orphan_processes)
            
            if long_running_processes:
                self._handle_timeout_processes(long_running_processes)
            
            # 整合性チェック
            self._check_db_process_consistency()
            
            return {
                'success': True,
                'orphan_processes_cleaned': len(orphan_processes),
                'timeout_processes_handled': len(long_running_processes),
                'message': 'Manual cleanup completed successfully'
            }
            
        except Exception as e:
            self.logger.error(f"Error during manual cleanup: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# グローバルインスタンス
_enhanced_monitor_instance: Optional[EnhancedProcessMonitor] = None


def get_enhanced_process_monitor() -> EnhancedProcessMonitor:
    """強化されたプロセス健全性監視のグローバルインスタンスを取得"""
    global _enhanced_monitor_instance
    if _enhanced_monitor_instance is None:
        _enhanced_monitor_instance = EnhancedProcessMonitor()
    return _enhanced_monitor_instance


def start_enhanced_process_monitoring():
    """強化されたプロセス監視を開始"""
    monitor = get_enhanced_process_monitor()
    monitor.start_monitoring()


def stop_enhanced_process_monitoring():
    """強化されたプロセス監視を停止"""
    monitor = get_enhanced_process_monitor()
    monitor.stop_monitoring()


# 使用例とテスト
def main():
    """テスト実行"""
    print("🔍 Enhanced Process Health Monitor Test")
    
    monitor = EnhancedProcessMonitor(check_interval=30, max_execution_hours=2)
    
    # 健全性ステータス取得
    status = monitor.get_process_health_status()
    print(f"Health status: {status}")
    
    # 手動クリーンアップ
    cleanup_result = monitor.manual_cleanup()
    print(f"Cleanup result: {cleanup_result}")
    
    # 監視開始テスト（コメントアウト：実際の監視は別途実行）
    # monitor.start_monitoring()
    # time.sleep(60)
    # monitor.stop_monitoring()


if __name__ == "__main__":
    main()