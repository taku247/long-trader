"""
Scheduler utilities for real-time monitoring system.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ScheduledTask:
    """Represents a scheduled monitoring task."""
    
    def __init__(self, task_id: str, func: Callable, interval: int, 
                 args: tuple = (), kwargs: dict = None):
        self.task_id = task_id
        self.func = func
        self.interval = interval  # in seconds
        self.args = args
        self.kwargs = kwargs or {}
        self.last_run = None
        self.next_run = datetime.now()
        self.is_running = False
        self.error_count = 0
        self.max_errors = 5
        
    def should_run(self) -> bool:
        """Check if task should run now."""
        return datetime.now() >= self.next_run and not self.is_running
    
    def update_next_run(self):
        """Update next run time."""
        self.next_run = datetime.now() + timedelta(seconds=self.interval)
    
    def execute(self) -> bool:
        """Execute the task."""
        if self.is_running:
            return False
            
        self.is_running = True
        try:
            logger.debug(f"Executing task: {self.task_id}")
            result = self.func(*self.args, **self.kwargs)
            self.last_run = datetime.now()
            self.error_count = 0
            self.update_next_run()
            logger.debug(f"Task {self.task_id} completed successfully")
            return True
        except Exception as e:
            self.error_count += 1
            logger.error(f"Task {self.task_id} failed: {e}")
            if self.error_count >= self.max_errors:
                logger.error(f"Task {self.task_id} exceeded max errors, disabling")
                return False
            self.update_next_run()
            return True
        finally:
            self.is_running = False


class TaskScheduler:
    """Simple task scheduler for monitoring system."""
    
    def __init__(self, max_workers: int = 5):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.max_workers = max_workers
        self.active_workers = 0
        self.running = False
        self.scheduler_thread = None
        self.worker_lock = threading.Lock()
        
    def add_task(self, task_id: str, func: Callable, interval_minutes: int,
                 args: tuple = (), kwargs: dict = None) -> bool:
        """Add a scheduled task."""
        if task_id in self.tasks:
            logger.warning(f"Task {task_id} already exists, updating")
            
        interval_seconds = interval_minutes * 60
        task = ScheduledTask(task_id, func, interval_seconds, args, kwargs)
        self.tasks[task_id] = task
        logger.info(f"Added task: {task_id} (interval: {interval_minutes}m)")
        return True
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Removed task: {task_id}")
            return True
        return False
    
    def update_task_interval(self, task_id: str, interval_minutes: int) -> bool:
        """Update task interval."""
        if task_id in self.tasks:
            self.tasks[task_id].interval = interval_minutes * 60
            self.tasks[task_id].update_next_run()
            logger.info(f"Updated task {task_id} interval to {interval_minutes}m")
            return True
        return False
    
    def get_task_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tasks."""
        status = {}
        for task_id, task in self.tasks.items():
            status[task_id] = {
                'interval_minutes': task.interval // 60,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat(),
                'is_running': task.is_running,
                'error_count': task.error_count
            }
        return status
    
    def _worker_task(self, task: ScheduledTask):
        """Execute task in worker thread."""
        try:
            with self.worker_lock:
                self.active_workers += 1
            
            success = task.execute()
            if not success:
                # Task failed too many times, remove it
                self.remove_task(task.task_id)
                
        except Exception as e:
            logger.error(f"Worker error for task {task.task_id}: {e}")
        finally:
            with self.worker_lock:
                self.active_workers -= 1
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler started")
        
        while self.running:
            try:
                # Check which tasks need to run
                ready_tasks = []
                for task in self.tasks.values():
                    if task.should_run():
                        ready_tasks.append(task)
                
                # Execute ready tasks (respecting worker limit)
                for task in ready_tasks:
                    with self.worker_lock:
                        if self.active_workers < self.max_workers:
                            worker_thread = threading.Thread(
                                target=self._worker_task,
                                args=(task,),
                                daemon=True
                            )
                            worker_thread.start()
                        else:
                            logger.debug(f"Worker limit reached, delaying task {task.task_id}")
                
                # Sleep for a short interval
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(5)
        
        logger.info("Scheduler stopped")
    
    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        self.scheduler_thread.start()
        logger.info("Scheduler thread started")
    
    def stop(self, timeout: int = 30):
        """Stop the scheduler."""
        logger.info("Stopping scheduler...")
        self.running = False
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout)
        
        # Wait for active workers to complete
        start_time = time.time()
        while self.active_workers > 0 and (time.time() - start_time) < timeout:
            logger.info(f"Waiting for {self.active_workers} active workers to complete...")
            time.sleep(1)
        
        logger.info("Scheduler stopped gracefully")
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.running and (
            self.scheduler_thread and self.scheduler_thread.is_alive()
        )


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, delay_seconds: float = 1.0):
        self.delay = delay_seconds
        self.last_call = 0
        self.lock = threading.Lock()
    
    def wait(self):
        """Wait if necessary to respect rate limit."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call
            if elapsed < self.delay:
                sleep_time = self.delay - elapsed
                time.sleep(sleep_time)
            self.last_call = time.time()


def format_duration(seconds: int) -> str:
    """Format duration in human readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"


def get_next_run_times(tasks: Dict[str, ScheduledTask]) -> List[Dict[str, str]]:
    """Get next run times for all tasks."""
    runs = []
    for task_id, task in tasks.items():
        runs.append({
            'task_id': task_id,
            'next_run': task.next_run.strftime('%Y-%m-%d %H:%M:%S'),
            'interval': format_duration(task.interval)
        })
    
    # Sort by next run time
    runs.sort(key=lambda x: x['next_run'])
    return runs