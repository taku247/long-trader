#!/usr/bin/env python3
"""
プロセス健全性監視システム
実行中のプロセス、デッドロック、タイムアウトを検出
"""

import psutil
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import multiprocessing
import threading
import signal
import os

from execution_log_database import ExecutionLogDatabase, ExecutionStatus


@dataclass
class ProcessHealth:
    """プロセス健全性情報"""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_mb: float
    create_time: str
    runtime_seconds: float
    is_hanging: bool
    is_zombie: bool
    open_files_count: int
    threads_count: int


@dataclass
class SystemHealth:
    """システム全体の健全性情報"""
    timestamp: str
    total_processes: int
    hanging_processes: int
    zombie_processes: int
    total_cpu_percent: float
    total_memory_mb: float
    available_memory_mb: float
    disk_usage_percent: float
    active_executions: int
    failed_executions_last_hour: int
    deadlock_risks: List[str]
    recommendations: List[str]


class ProcessHealthMonitor:
    """プロセス健全性監視システム"""
    
    def __init__(self):
        self.execution_db = ExecutionLogDatabase()
        self.long_trader_base = Path(__file__).parent
        
        # 監視対象プロセス名
        self.target_processes = [
            'python',
            'python3',
            'auto_symbol_training.py',
            'scalable_analysis_system.py',
            'high_leverage_bot_orchestrator.py'
        ]
        
        # ハングアップ検出閾値（秒）
        self.hang_threshold_seconds = 1800  # 30分
        
        # 高リスク条件
        self.high_cpu_threshold = 90.0  # CPU使用率90%以上
        self.high_memory_threshold_gb = 8.0  # メモリ使用量8GB以上
    
    def scan_process_health(self) -> SystemHealth:
        """プロセス健全性をスキャン"""
        
        try:
            current_time = datetime.now()
            
            # 全プロセス取得
            all_processes = []
            hanging_count = 0
            zombie_count = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 
                                           'memory_info', 'create_time', 'open_files', 'num_threads']):
                try:
                    proc_info = proc.info
                    
                    # Long Trader関連プロセスのみを対象
                    if not self._is_long_trader_process(proc):
                        continue
                    
                    # プロセス詳細取得
                    create_time = datetime.fromtimestamp(proc_info['create_time'])
                    runtime_seconds = (current_time - create_time).total_seconds()
                    
                    # メモリ使用量をMB変換
                    memory_mb = proc_info['memory_info'].rss / 1024 / 1024 if proc_info['memory_info'] else 0
                    
                    # ファイル数取得（権限エラー対策）
                    try:
                        open_files_count = len(proc_info['open_files']) if proc_info['open_files'] else 0
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        open_files_count = 0
                    
                    # ハングアップ検出
                    is_hanging = self._detect_hanging_process(proc, runtime_seconds)
                    if is_hanging:
                        hanging_count += 1
                    
                    # ゾンビプロセス検出
                    is_zombie = proc_info['status'] == psutil.STATUS_ZOMBIE
                    if is_zombie:
                        zombie_count += 1
                    
                    process_health = ProcessHealth(
                        pid=proc_info['pid'],
                        name=proc_info['name'],
                        status=proc_info['status'],
                        cpu_percent=proc_info['cpu_percent'] or 0.0,
                        memory_mb=memory_mb,
                        create_time=create_time.strftime('%Y-%m-%d %H:%M:%S'),
                        runtime_seconds=runtime_seconds,
                        is_hanging=is_hanging,
                        is_zombie=is_zombie,
                        open_files_count=open_files_count,
                        threads_count=proc_info['num_threads'] or 1
                    )
                    
                    all_processes.append(process_health)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # システム統計取得
            cpu_stats = psutil.cpu_percent(interval=1)
            memory_stats = psutil.virtual_memory()
            disk_stats = psutil.disk_usage('/')
            
            # 実行状況統計
            active_executions = self._count_active_executions()
            failed_executions = self._count_failed_executions_last_hour()
            
            # デッドロックリスク検出
            deadlock_risks = self._detect_deadlock_risks(all_processes)
            
            # 推奨事項生成
            recommendations = self._generate_recommendations(all_processes, hanging_count, zombie_count)
            
            return SystemHealth(
                timestamp=current_time.strftime('%Y-%m-%d %H:%M:%S'),
                total_processes=len(all_processes),
                hanging_processes=hanging_count,
                zombie_processes=zombie_count,
                total_cpu_percent=cpu_stats,
                total_memory_mb=memory_stats.used / 1024 / 1024,
                available_memory_mb=memory_stats.available / 1024 / 1024,
                disk_usage_percent=disk_stats.percent,
                active_executions=active_executions,
                failed_executions_last_hour=failed_executions,
                deadlock_risks=deadlock_risks,
                recommendations=recommendations
            )
            
        except Exception as e:
            # エラー時は基本情報のみ返す
            return SystemHealth(
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                total_processes=0,
                hanging_processes=0,
                zombie_processes=0,
                total_cpu_percent=0.0,
                total_memory_mb=0.0,
                available_memory_mb=0.0,
                disk_usage_percent=0.0,
                active_executions=0,
                failed_executions_last_hour=0,
                deadlock_risks=[f"健全性チェックエラー: {str(e)}"],
                recommendations=["システムを再起動してください"]
            )
    
    def _is_long_trader_process(self, proc) -> bool:
        """Long Trader関連プロセスかどうか判定"""
        try:
            # プロセス名チェック
            if any(target in proc.name() for target in self.target_processes):
                return True
            
            # コマンドライン引数チェック
            cmdline = proc.cmdline()
            if any('long-trader' in cmd or 'auto_symbol_training' in cmd or 
                   'scalable_analysis' in cmd for cmd in cmdline):
                return True
            
            # カレントディレクトリチェック
            try:
                cwd = proc.cwd()
                if 'long-trader' in cwd:
                    return True
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            
            return False
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _detect_hanging_process(self, proc, runtime_seconds: float) -> bool:
        """ハングアッププロセス検出"""
        try:
            # 実行時間が閾値を超えているかチェック
            if runtime_seconds < self.hang_threshold_seconds:
                return False
            
            # CPU使用率が極端に低い場合はハング疑い
            cpu_percent = proc.cpu_percent()
            if cpu_percent is not None and cpu_percent < 0.1:
                return True
            
            # 大量のスレッドを持つ場合
            num_threads = proc.num_threads()
            if num_threads > 50:
                return True
            
            # 状態チェック
            status = proc.status()
            if status in [psutil.STATUS_STOPPED, psutil.STATUS_TRACING_STOP]:
                return True
            
            return False
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _count_active_executions(self) -> int:
        """アクティブな実行の数を取得"""
        try:
            executions = self.execution_db.list_executions(limit=100)
            active_count = 0
            
            for execution in executions:
                if execution['status'] == ExecutionStatus.RUNNING.value:
                    active_count += 1
            
            return active_count
            
        except Exception:
            return 0
    
    def _count_failed_executions_last_hour(self) -> int:
        """過去1時間の失敗実行数を取得"""
        try:
            one_hour_ago = datetime.now() - timedelta(hours=1)
            executions = self.execution_db.list_executions(limit=200)
            failed_count = 0
            
            for execution in executions:
                if (execution['status'] == ExecutionStatus.FAILED.value and 
                    execution['created_at'] > one_hour_ago.isoformat()):
                    failed_count += 1
            
            return failed_count
            
        except Exception:
            return 0
    
    def _detect_deadlock_risks(self, processes: List[ProcessHealth]) -> List[str]:
        """デッドロックリスク検出"""
        risks = []
        
        # 長時間実行プロセスの検出
        long_running = [p for p in processes if p.runtime_seconds > 3600]  # 1時間以上
        if long_running:
            risks.append(f"{len(long_running)}個のプロセスが1時間以上実行中")
        
        # 高CPU使用率プロセス
        high_cpu = [p for p in processes if p.cpu_percent > self.high_cpu_threshold]
        if high_cpu:
            risks.append(f"{len(high_cpu)}個のプロセスが高CPU使用率 (>{self.high_cpu_threshold}%)")
        
        # 高メモリ使用率プロセス
        high_memory = [p for p in processes if p.memory_mb > self.high_memory_threshold_gb * 1024]
        if high_memory:
            risks.append(f"{len(high_memory)}個のプロセスが高メモリ使用率 (>{self.high_memory_threshold_gb}GB)")
        
        # 多数のファイルを開いているプロセス
        many_files = [p for p in processes if p.open_files_count > 100]
        if many_files:
            risks.append(f"{len(many_files)}個のプロセスが多数のファイルを開いている (>100)")
        
        # ゾンビプロセス
        zombies = [p for p in processes if p.is_zombie]
        if zombies:
            risks.append(f"{len(zombies)}個のゾンビプロセスが検出されました")
        
        return risks
    
    def _generate_recommendations(self, processes: List[ProcessHealth], 
                                hanging_count: int, zombie_count: int) -> List[str]:
        """推奨事項生成"""
        recommendations = []
        
        if hanging_count > 0:
            recommendations.append(f"ハングアップの疑いがあるプロセス ({hanging_count}個) の強制終了を検討してください")
        
        if zombie_count > 0:
            recommendations.append(f"ゾンビプロセス ({zombie_count}個) の親プロセスを確認してください")
        
        # 高負荷プロセス
        high_load_processes = [p for p in processes 
                             if p.cpu_percent > 80 or p.memory_mb > 4096]
        if high_load_processes:
            recommendations.append(f"高負荷プロセス ({len(high_load_processes)}個) を監視してください")
        
        # 長時間実行プロセス
        long_running = [p for p in processes if p.runtime_seconds > 7200]  # 2時間以上
        if long_running:
            recommendations.append(f"長時間実行プロセス ({len(long_running)}個) の進捗を確認してください")
        
        # システムリソース
        total_memory_gb = sum(p.memory_mb for p in processes) / 1024
        if total_memory_gb > 8:
            recommendations.append(f"メモリ使用量が高い ({total_memory_gb:.1f}GB) - 不要なプロセスを終了してください")
        
        if not recommendations:
            recommendations.append("システムは正常に動作しています")
        
        return recommendations
    
    def kill_hanging_processes(self) -> Dict[str, List[int]]:
        """ハングアッププロセスを強制終了"""
        health = self.scan_process_health()
        
        killed_pids = []
        failed_pids = []
        
        for proc in psutil.process_iter(['pid']):
            try:
                if self._is_long_trader_process(proc):
                    runtime = (datetime.now() - datetime.fromtimestamp(proc.create_time())).total_seconds()
                    
                    if self._detect_hanging_process(proc, runtime):
                        try:
                            proc.terminate()  # 穏やかな終了を試行
                            time.sleep(5)
                            
                            if proc.is_running():
                                proc.kill()  # 強制終了
                            
                            killed_pids.append(proc.pid)
                            
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            failed_pids.append(proc.pid)
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            'killed': killed_pids,
            'failed': failed_pids,
            'total_attempted': len(killed_pids) + len(failed_pids)
        }
    
    def cleanup_zombie_processes(self) -> int:
        """ゾンビプロセスのクリーンアップ"""
        cleaned_count = 0
        
        for proc in psutil.process_iter(['pid', 'status', 'ppid']):
            try:
                if (proc.status() == psutil.STATUS_ZOMBIE and 
                    self._is_long_trader_process(proc)):
                    
                    # 親プロセスに SIGCHLD を送信してゾンビを回収させる
                    try:
                        parent = psutil.Process(proc.ppid())
                        parent.send_signal(signal.SIGCHLD)
                        cleaned_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return cleaned_count
    
    def get_detailed_process_info(self, pid: int) -> Optional[Dict]:
        """特定プロセスの詳細情報取得"""
        try:
            proc = psutil.Process(pid)
            
            return {
                'pid': pid,
                'name': proc.name(),
                'status': proc.status(),
                'cpu_percent': proc.cpu_percent(),
                'memory_info': proc.memory_info()._asdict(),
                'create_time': datetime.fromtimestamp(proc.create_time()).strftime('%Y-%m-%d %H:%M:%S'),
                'cmdline': proc.cmdline(),
                'cwd': proc.cwd() if hasattr(proc, 'cwd') else None,
                'open_files': [f.path for f in proc.open_files()],
                'connections': [c._asdict() for c in proc.connections()],
                'threads': proc.num_threads(),
                'children': [child.pid for child in proc.children()]
            }
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None


def main():
    """テスト実行"""
    monitor = ProcessHealthMonitor()
    
    print("プロセス健全性スキャン実行中...")
    health = monitor.scan_process_health()
    
    print(f"\n=== システム健全性レポート ({health.timestamp}) ===")
    print(f"総プロセス数: {health.total_processes}")
    print(f"ハングアップ疑い: {health.hanging_processes}")
    print(f"ゾンビプロセス: {health.zombie_processes}")
    print(f"CPU使用率: {health.total_cpu_percent:.1f}%")
    print(f"メモリ使用量: {health.total_memory_mb:.1f}MB")
    print(f"利用可能メモリ: {health.available_memory_mb:.1f}MB")
    print(f"ディスク使用率: {health.disk_usage_percent:.1f}%")
    print(f"アクティブ実行: {health.active_executions}")
    print(f"過去1時間の失敗: {health.failed_executions_last_hour}")
    
    print("\nデッドロックリスク:")
    for risk in health.deadlock_risks:
        print(f"  - {risk}")
    
    print("\n推奨事項:")
    for rec in health.recommendations:
        print(f"  - {rec}")


if __name__ == "__main__":
    main()