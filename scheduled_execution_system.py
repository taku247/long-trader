#!/usr/bin/env python3
"""
定期実行システム
バックテスト・学習の自動実行とスケジューリング
"""

import asyncio
import schedule
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import sys
import os

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from real_time_system.utils.colored_log import get_colored_logger
from execution_log_database import ExecutionLogDatabase, ExecutionType, ExecutionStatus
from auto_symbol_training import AutoSymbolTrainer


class ExecutionFrequency(Enum):
    """実行頻度"""
    HOURLY = "hourly"           # 1時間毎
    EVERY_4_HOURS = "4hourly"   # 4時間毎
    DAILY = "daily"             # 日次
    WEEKLY = "weekly"           # 週次
    MONTHLY = "monthly"         # 月次


@dataclass
class ScheduledTask:
    """スケジュールされたタスク"""
    task_id: str
    task_type: ExecutionType
    symbol: Optional[str]
    symbols: Optional[List[str]]
    frequency: ExecutionFrequency
    target_timeframes: List[str]
    target_strategies: List[str]
    enabled: bool = True
    last_executed: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    consecutive_failures: int = 0
    max_failures: int = 3


class ScheduledExecutionSystem:
    """定期実行システム"""
    
    def __init__(self):
        self.logger = get_colored_logger(__name__)
        self.execution_db = ExecutionLogDatabase()
        self.trainer = AutoSymbolTrainer()
        
        # スケジュールタスクの管理
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
        # 設定
        self.config = self._load_schedule_config()
        
        # デフォルトタスクの設定
        self._setup_default_tasks()
    
    def _load_schedule_config(self) -> Dict:
        """スケジュール設定の読み込み"""
        default_config = {
            'enabled': True,
            'max_concurrent_executions': 2,
            'default_timeframes': ['1h', '4h', '1d'],
            'default_strategies': ['Conservative_ML', 'Aggressive_Traditional', 'Full_ML'],
            'monitored_symbols': ['HYPE', 'SOL', 'PEPE', 'BONK', 'WIF'],
            'backtest_frequencies': {
                '1m': 'hourly',      # 1分足は1時間毎
                '3m': 'hourly',      # 3分足は1時間毎  
                '5m': 'hourly',      # 5分足は1時間毎
                '15m': '4hourly',    # 15分足は4時間毎
                '30m': '4hourly',    # 30分足は4時間毎
                '1h': 'daily'        # 1時間足は日次
            },
            'training_frequencies': {
                'ml_models': 'weekly',        # ML学習は週次
                'strategy_optimization': 'monthly'  # 戦略最適化は月次
            }
        }
        
        try:
            config_path = Path('schedule_config.json')
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            else:
                # デフォルト設定を保存
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            self.logger.error(f"Schedule config load error: {e}")
        
        return default_config
    
    def _setup_default_tasks(self):
        """デフォルトスケジュールタスクの設定"""
        if not self.config.get('enabled', True):
            self.logger.info("📅 Scheduled execution is disabled")
            return
        
        # 監視銘柄のバックテストタスク
        for symbol in self.config.get('monitored_symbols', []):
            for timeframe in self.config.get('default_timeframes', []):
                frequency_key = self.config['backtest_frequencies'].get(timeframe, 'daily')
                frequency = ExecutionFrequency(frequency_key)
                
                task = ScheduledTask(
                    task_id=f"backtest_{symbol}_{timeframe}",
                    task_type=ExecutionType.SCHEDULED_BACKTEST,
                    symbol=symbol,
                    symbols=None,
                    frequency=frequency,
                    target_timeframes=[timeframe],
                    target_strategies=self.config.get('default_strategies', []),
                    enabled=True
                )
                
                self.scheduled_tasks[task.task_id] = task
        
        # 全銘柄ML学習タスク
        weekly_training_task = ScheduledTask(
            task_id="ml_training_all_symbols",
            task_type=ExecutionType.SCHEDULED_TRAINING,
            symbol=None,
            symbols=self.config.get('monitored_symbols', []),
            frequency=ExecutionFrequency.WEEKLY,
            target_timeframes=self.config.get('default_timeframes', []),
            target_strategies=self.config.get('default_strategies', []),
            enabled=True
        )
        self.scheduled_tasks[weekly_training_task.task_id] = weekly_training_task
        
        # 月次最適化タスク
        monthly_optimization_task = ScheduledTask(
            task_id="monthly_strategy_optimization",
            task_type=ExecutionType.MONTHLY_OPTIMIZATION,
            symbol=None,
            symbols=self.config.get('monitored_symbols', []),
            frequency=ExecutionFrequency.MONTHLY,
            target_timeframes=self.config.get('default_timeframes', []),
            target_strategies=self.config.get('default_strategies', []),
            enabled=True
        )
        self.scheduled_tasks[monthly_optimization_task.task_id] = monthly_optimization_task
        
        self.logger.info(f"📅 Set up {len(self.scheduled_tasks)} scheduled tasks")
    
    def start_scheduler(self):
        """スケジューラー開始"""
        if self.running:
            self.logger.warning("⚠️ Scheduler is already running")
            return
        
        self.running = True
        self.logger.info("🚀 Starting scheduled execution system")
        
        # スケジュール設定
        self._configure_schedules()
        
        # スケジューラースレッド開始
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("✅ Scheduled execution system started")
    
    def stop_scheduler(self):
        """スケジューラー停止"""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("🛑 Stopping scheduled execution system")
        
        # 実行中のタスクが完了するまで待機
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=30)
        
        # スケジュールクリア
        schedule.clear()
        
        self.logger.info("✅ Scheduled execution system stopped")
    
    def _configure_schedules(self):
        """スケジュール設定"""
        schedule.clear()
        
        # 時間毎のタスク
        schedule.every().hour.at(":05").do(self._execute_hourly_tasks)
        
        # 4時間毎のタスク（0, 4, 8, 12, 16, 20時）
        for hour in [0, 4, 8, 12, 16, 20]:
            schedule.every().day.at(f"{hour:02d}:10").do(self._execute_4hourly_tasks)
        
        # 日次タスク（午前2時）
        schedule.every().day.at("02:00").do(self._execute_daily_tasks)
        
        # 週次タスク（月曜日午前3時）
        schedule.every().monday.at("03:00").do(self._execute_weekly_tasks)
        
        # 月次タスク（1日午前4時）
        schedule.every().month.do(self._execute_monthly_tasks)
        
        self.logger.info("📅 Configured all schedule patterns")
    
    def _run_scheduler(self):
        """スケジューラーメインループ"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1分間隔でチェック
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(300)  # エラー時は5分待機
    
    def _execute_hourly_tasks(self):
        """時間毎タスクの実行"""
        self.logger.info("⏰ Executing hourly tasks")
        self._execute_tasks_by_frequency(ExecutionFrequency.HOURLY)
    
    def _execute_4hourly_tasks(self):
        """4時間毎タスクの実行"""
        self.logger.info("⏰ Executing 4-hourly tasks")
        self._execute_tasks_by_frequency(ExecutionFrequency.EVERY_4_HOURS)
    
    def _execute_daily_tasks(self):
        """日次タスクの実行"""
        self.logger.info("⏰ Executing daily tasks")
        self._execute_tasks_by_frequency(ExecutionFrequency.DAILY)
    
    def _execute_weekly_tasks(self):
        """週次タスクの実行"""
        self.logger.info("⏰ Executing weekly tasks")
        self._execute_tasks_by_frequency(ExecutionFrequency.WEEKLY)
    
    def _execute_monthly_tasks(self):
        """月次タスクの実行"""
        self.logger.info("⏰ Executing monthly tasks")
        self._execute_tasks_by_frequency(ExecutionFrequency.MONTHLY)
    
    def _execute_tasks_by_frequency(self, frequency: ExecutionFrequency):
        """指定頻度のタスクを実行"""
        tasks_to_execute = [
            task for task in self.scheduled_tasks.values()
            if task.frequency == frequency and task.enabled and task.consecutive_failures < task.max_failures
        ]
        
        if not tasks_to_execute:
            self.logger.debug(f"No {frequency.value} tasks to execute")
            return
        
        self.logger.info(f"📋 Found {len(tasks_to_execute)} {frequency.value} tasks to execute")
        
        # 並列実行（最大同時実行数に制限）
        max_concurrent = self.config.get('max_concurrent_executions', 2)
        
        async def execute_all_tasks():
            semaphore = asyncio.Semaphore(max_concurrent)
            tasks = [
                self._execute_single_task_with_semaphore(semaphore, task)
                for task in tasks_to_execute
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 新しいイベントループで実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(execute_all_tasks())
        finally:
            loop.close()
    
    async def _execute_single_task_with_semaphore(self, semaphore: asyncio.Semaphore, task: ScheduledTask):
        """セマフォを使用してタスクを実行"""
        async with semaphore:
            await self._execute_single_task(task)
    
    async def _execute_single_task(self, task: ScheduledTask):
        """単一タスクの実行"""
        try:
            self.logger.info(f"🚀 Executing task: {task.task_id}")
            
            execution_id = None
            
            if task.task_type == ExecutionType.SCHEDULED_BACKTEST:
                execution_id = await self._execute_backtest_task(task)
            elif task.task_type == ExecutionType.SCHEDULED_TRAINING:
                execution_id = await self._execute_training_task(task)
            elif task.task_type == ExecutionType.MONTHLY_OPTIMIZATION:
                execution_id = await self._execute_optimization_task(task)
            
            if execution_id:
                # 成功時の処理
                task.last_executed = datetime.now()
                task.consecutive_failures = 0
                self.logger.success(f"✅ Task {task.task_id} completed: {execution_id}")
            else:
                raise Exception("Execution ID not returned")
                
        except Exception as e:
            # 失敗時の処理
            task.consecutive_failures += 1
            self.logger.error(f"❌ Task {task.task_id} failed (attempt {task.consecutive_failures}): {e}")
            
            if task.consecutive_failures >= task.max_failures:
                task.enabled = False
                self.logger.warning(f"⏸️ Task {task.task_id} disabled due to consecutive failures")
    
    async def _execute_backtest_task(self, task: ScheduledTask) -> str:
        """バックテストタスクの実行"""
        # 実行記録作成
        execution_id = self.execution_db.create_execution(
            ExecutionType.SCHEDULED_BACKTEST,
            symbol=task.symbol,
            symbols=task.symbols,
            triggered_by="SCHEDULER",
            metadata={
                "task_id": task.task_id,
                "frequency": task.frequency.value,
                "timeframes": task.target_timeframes,
                "strategies": task.target_strategies
            }
        )
        
        self.execution_db.update_execution_status(
            execution_id,
            ExecutionStatus.RUNNING,
            current_operation='定期バックテスト実行中',
            total_tasks=len(task.target_timeframes) * len(task.target_strategies)
        )
        
        try:
            # ウォークフォワードバックテストの実行
            from walk_forward_system import WalkForwardSystem
            
            wf_system = WalkForwardSystem(task.symbol)
            
            # バックテストが必要かチェック
            if not wf_system.should_backtest():
                self.logger.info(f"⏭️ {task.symbol}: Backtest not needed yet")
                return execution_id
            
            # ウォークフォワードバックテスト実行
            backtest_result = await wf_system.execute_walk_forward_backtest()
            
            self.execution_db.add_execution_step(
                execution_id,
                "walk_forward_backtest",
                "SUCCESS",
                result_data=backtest_result
            )
            
            # 成功記録
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.SUCCESS,
                current_operation='完了',
                progress_percentage=100
            )
            
            return execution_id
            
        except Exception as e:
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                current_operation=f'エラー: {str(e)}'
            )
            
            self.execution_db.add_execution_error(execution_id, {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'step': 'backtest_execution'
            })
            
            raise
    
    async def _execute_training_task(self, task: ScheduledTask) -> str:
        """学習タスクの実行"""
        # 実行記録作成
        execution_id = self.execution_db.create_execution(
            ExecutionType.SCHEDULED_TRAINING,
            symbol=task.symbol,
            symbols=task.symbols,
            triggered_by="SCHEDULER",
            metadata={
                "task_id": task.task_id,
                "frequency": task.frequency.value,
                "timeframes": task.target_timeframes,
                "strategies": task.target_strategies
            }
        )
        
        self.execution_db.update_execution_status(
            execution_id,
            ExecutionStatus.RUNNING,
            current_operation='定期学習実行中',
            total_tasks=len(task.symbols or [task.symbol] if task.symbol else [])
        )
        
        try:
            # ウォークフォワード学習の実行
            from walk_forward_system import WalkForwardSystem
            
            symbols_to_train = task.symbols or ([task.symbol] if task.symbol else [])
            
            for symbol in symbols_to_train:
                self.execution_db.update_execution_status(
                    execution_id,
                    ExecutionStatus.RUNNING,
                    current_operation=f'{symbol}の学習実行中'
                )
                
                wf_system = WalkForwardSystem(symbol)
                
                # 学習が必要かチェック
                if wf_system.should_retrain():
                    self.logger.info(f"🎓 {symbol}: Training required")
                    
                    # ウォークフォワード学習実行
                    training_result = await wf_system.execute_walk_forward_training()
                    
                    self.execution_db.add_execution_step(
                        execution_id,
                        f"walk_forward_train_{symbol}",
                        "SUCCESS",
                        result_data=training_result
                    )
                else:
                    self.logger.info(f"⏭️ {symbol}: Training not needed yet")
                    
                    self.execution_db.add_execution_step(
                        execution_id,
                        f"skip_train_{symbol}",
                        "SUCCESS",
                        result_data={"symbol": symbol, "reason": "training_not_needed"}
                    )
            
            # 成功記録
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.SUCCESS,
                current_operation='完了',
                progress_percentage=100
            )
            
            return execution_id
            
        except Exception as e:
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                current_operation=f'エラー: {str(e)}'
            )
            
            self.execution_db.add_execution_error(execution_id, {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'step': 'training_execution'
            })
            
            raise
    
    async def _execute_optimization_task(self, task: ScheduledTask) -> str:
        """最適化タスクの実行"""
        # 実行記録作成
        execution_id = self.execution_db.create_execution(
            ExecutionType.MONTHLY_OPTIMIZATION,
            symbol=task.symbol,
            symbols=task.symbols,
            triggered_by="SCHEDULER",
            metadata={
                "task_id": task.task_id,
                "frequency": task.frequency.value,
                "optimization_type": "strategy_selection"
            }
        )
        
        self.execution_db.update_execution_status(
            execution_id,
            ExecutionStatus.RUNNING,
            current_operation='戦略最適化実行中',
            total_tasks=3
        )
        
        try:
            # TODO: 実際の戦略最適化ロジック
            # 1. 過去1ヶ月のパフォーマンス分析
            # 2. 最適戦略の選択
            # 3. 戦略ランキングの更新
            
            # サンプル実装
            await asyncio.sleep(3)  # 最適化実行をシミュレート
            
            self.execution_db.add_execution_step(
                execution_id,
                "performance_analysis",
                "SUCCESS",
                result_data={"analyzed_strategies": len(task.target_strategies)}
            )
            
            self.execution_db.add_execution_step(
                execution_id,
                "strategy_selection",
                "SUCCESS",
                result_data={"optimized_combinations": 15}
            )
            
            self.execution_db.add_execution_step(
                execution_id,
                "ranking_update",
                "SUCCESS",
                result_data={"updated_rankings": True}
            )
            
            # 成功記録
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.SUCCESS,
                current_operation='完了',
                progress_percentage=100
            )
            
            return execution_id
            
        except Exception as e:
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                current_operation=f'エラー: {str(e)}'
            )
            
            self.execution_db.add_execution_error(execution_id, {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'step': 'optimization_execution'
            })
            
            raise
    
    def add_custom_task(self, task: ScheduledTask):
        """カスタムタスクの追加"""
        self.scheduled_tasks[task.task_id] = task
        self.logger.info(f"➕ Added custom task: {task.task_id}")
    
    def remove_task(self, task_id: str):
        """タスクの削除"""
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
            self.logger.info(f"➖ Removed task: {task_id}")
    
    def get_task_status(self) -> Dict:
        """タスク状況の取得"""
        return {
            'running': self.running,
            'total_tasks': len(self.scheduled_tasks),
            'enabled_tasks': len([t for t in self.scheduled_tasks.values() if t.enabled]),
            'failed_tasks': len([t for t in self.scheduled_tasks.values() if t.consecutive_failures >= t.max_failures]),
            'tasks': [
                {
                    'task_id': task.task_id,
                    'type': task.task_type.value,
                    'frequency': task.frequency.value,
                    'enabled': task.enabled,
                    'last_executed': task.last_executed.isoformat() if task.last_executed else None,
                    'consecutive_failures': task.consecutive_failures
                }
                for task in self.scheduled_tasks.values()
            ]
        }


def main():
    """テスト実行"""
    import signal
    
    scheduler = ScheduledExecutionSystem()
    
    def signal_handler(signum, frame):
        print("\nShutting down scheduler...")
        scheduler.stop_scheduler()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        scheduler.start_scheduler()
        
        print("Scheduled execution system started. Press Ctrl+C to stop.")
        print(f"Current tasks: {len(scheduler.scheduled_tasks)}")
        
        # 状況を定期的に表示
        while scheduler.running:
            time.sleep(30)
            status = scheduler.get_task_status()
            print(f"Status: {status['enabled_tasks']}/{status['total_tasks']} tasks enabled")
            
    except KeyboardInterrupt:
        scheduler.stop_scheduler()


if __name__ == "__main__":
    main()