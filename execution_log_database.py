#!/usr/bin/env python3
"""
学習・バックテスト実行ログデータベース
実行履歴の永続化とクエリ機能
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from real_time_system.utils.colored_log import get_colored_logger


class ExecutionStatus(Enum):
    """実行ステータス"""
    PENDING = "PENDING"       # 待機中
    RUNNING = "RUNNING"       # 実行中
    SUCCESS = "SUCCESS"       # 成功
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"  # 部分成功
    FAILED = "FAILED"         # 失敗
    CANCELLED = "CANCELLED"   # キャンセル


class ExecutionType(Enum):
    """実行タイプ"""
    SYMBOL_ADDITION = "SYMBOL_ADDITION"           # 銘柄追加
    SCHEDULED_BACKTEST = "SCHEDULED_BACKTEST"     # 定期バックテスト
    SCHEDULED_TRAINING = "SCHEDULED_TRAINING"     # 定期学習
    MONTHLY_OPTIMIZATION = "MONTHLY_OPTIMIZATION" # 月次最適化
    EMERGENCY_RETRAIN = "EMERGENCY_RETRAIN"       # 緊急再学習
    MANUAL_EXECUTION = "MANUAL_EXECUTION"         # 手動実行


@dataclass
class ExecutionStep:
    """実行ステップ"""
    step_name: str
    status: str
    timestamp_start: Optional[datetime] = None
    timestamp_end: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    result_data: Optional[Dict] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None


@dataclass
class ExecutionRecord:
    """実行記録"""
    execution_id: str
    execution_type: str
    symbol: Optional[str]
    symbols: Optional[List[str]]
    timestamp_start: datetime
    timestamp_end: Optional[datetime]
    status: str
    duration_seconds: Optional[float]
    triggered_by: str
    server_id: Optional[str]
    version: Optional[str]
    
    # 進捗情報
    current_operation: Optional[str]
    progress_percentage: float
    completed_tasks: List[str]
    total_tasks: int
    
    # リソース使用状況
    cpu_usage_avg: Optional[float]
    memory_peak_mb: Optional[int]
    disk_io_mb: Optional[int]
    
    # メタデータ
    metadata: Optional[Dict]
    
    # 実行ステップ
    steps: List[ExecutionStep]
    
    # エラー情報
    errors: List[Dict]


class ExecutionLogDatabase:
    """実行ログデータベース管理"""
    
    def __init__(self, db_path: str = "execution_logs.db"):
        self.db_path = Path(db_path)
        self.logger = get_colored_logger(__name__)
        self._init_database()
    
    def _init_database(self):
        """データベース初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 実行記録テーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS execution_logs (
                        execution_id TEXT PRIMARY KEY,
                        execution_type TEXT NOT NULL,
                        symbol TEXT,
                        symbols TEXT,  -- JSON array
                        timestamp_start TEXT NOT NULL,
                        timestamp_end TEXT,
                        status TEXT NOT NULL,
                        duration_seconds REAL,
                        triggered_by TEXT,
                        server_id TEXT,
                        version TEXT,
                        
                        -- 進捗情報
                        current_operation TEXT,
                        progress_percentage REAL DEFAULT 0,
                        completed_tasks TEXT,  -- JSON array
                        total_tasks INTEGER DEFAULT 0,
                        
                        -- リソース使用状況
                        cpu_usage_avg REAL,
                        memory_peak_mb INTEGER,
                        disk_io_mb INTEGER,
                        
                        -- メタデータ
                        metadata TEXT,  -- JSON
                        
                        -- エラー情報
                        errors TEXT,  -- JSON array
                        
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 実行ステップテーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS execution_steps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        execution_id TEXT NOT NULL,
                        step_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        timestamp_start TEXT,
                        timestamp_end TEXT,
                        duration_seconds REAL,
                        result_data TEXT,  -- JSON
                        error_message TEXT,
                        error_traceback TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (execution_id) REFERENCES execution_logs (execution_id)
                    )
                """)
                
                # インデックス作成
                conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_type ON execution_logs(execution_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON execution_logs(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON execution_logs(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp_start ON execution_logs(timestamp_start)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_step_execution ON execution_steps(execution_id)")
                
                conn.commit()
                
            self.logger.debug(f"📊 Execution log database initialized: {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_execution(self, execution_type: ExecutionType, 
                        symbol: Optional[str] = None,
                        symbols: Optional[List[str]] = None,
                        triggered_by: str = "SYSTEM",
                        metadata: Optional[Dict] = None) -> str:
        """新規実行記録を作成"""
        execution_id = f"{execution_type.value.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO execution_logs (
                        execution_id, execution_type, symbol, symbols,
                        timestamp_start, status, triggered_by, metadata,
                        completed_tasks, errors
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id,
                    execution_type.value,
                    symbol,
                    json.dumps(symbols) if symbols else None,
                    datetime.now().isoformat(),
                    ExecutionStatus.PENDING.value,
                    triggered_by,
                    json.dumps(metadata) if metadata else None,
                    json.dumps([]),
                    json.dumps([])
                ))
                conn.commit()
            
            self.logger.info(f"📝 Created execution record: {execution_id}")
            return execution_id
            
        except Exception as e:
            self.logger.error(f"Failed to create execution record: {e}")
            raise
    
    def create_execution_with_id(self, execution_id: str, execution_type: ExecutionType, 
                                symbol: Optional[str] = None,
                                symbols: Optional[List[str]] = None,
                                triggered_by: str = "SYSTEM",
                                metadata: Optional[Dict] = None) -> str:
        """事前定義されたIDで実行記録を作成"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO execution_logs (
                        execution_id, execution_type, symbol, symbols,
                        timestamp_start, status, triggered_by, metadata,
                        completed_tasks, errors
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id,
                    execution_type.value,
                    symbol,
                    json.dumps(symbols) if symbols else None,
                    datetime.now().isoformat(),
                    ExecutionStatus.PENDING.value,
                    triggered_by,
                    json.dumps(metadata) if metadata else None,
                    json.dumps([]),
                    json.dumps([])
                ))
                conn.commit()
            
            self.logger.info(f"📝 Created execution record with ID: {execution_id}")
            return execution_id
            
        except Exception as e:
            self.logger.error(f"Failed to create execution record with ID: {e}")
            raise
    
    def update_execution_status(self, execution_id: str, status: ExecutionStatus,
                               current_operation: Optional[str] = None,
                               progress_percentage: Optional[float] = None,
                               **kwargs):
        """実行ステータス更新"""
        try:
            updates = ["status = ?", "updated_at = ?"]
            values = [status.value, datetime.now().isoformat()]
            
            if current_operation:
                updates.append("current_operation = ?")
                values.append(current_operation)
            
            if progress_percentage is not None:
                updates.append("progress_percentage = ?")
                values.append(progress_percentage)
            
            # 完了時の処理
            if status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                updates.append("timestamp_end = ?")
                values.append(datetime.now().isoformat())
                
                # 実行時間計算
                execution = self.get_execution(execution_id)
                if execution:
                    start_time = datetime.fromisoformat(execution['timestamp_start'])
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    updates.append("duration_seconds = ?")
                    values.append(duration)
            
            # その他のフィールド更新
            for key, value in kwargs.items():
                if key in ['cpu_usage_avg', 'memory_peak_mb', 'disk_io_mb', 'total_tasks']:
                    updates.append(f"{key} = ?")
                    values.append(value)
            
            values.append(execution_id)  # WHERE条件用
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"""
                    UPDATE execution_logs 
                    SET {', '.join(updates)}
                    WHERE execution_id = ?
                """, values)
                conn.commit()
            
            self.logger.debug(f"Updated execution {execution_id}: {status.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to update execution status: {e}")
            raise
    
    def add_execution_step(self, execution_id: str, step_name: str, 
                          status: str, result_data: Optional[Dict] = None,
                          error_message: Optional[str] = None,
                          error_traceback: Optional[str] = None,
                          duration_seconds: Optional[float] = None):
        """実行ステップを追加"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO execution_steps (
                        execution_id, step_name, status, timestamp_start,
                        timestamp_end, duration_seconds, result_data,
                        error_message, error_traceback
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id,
                    step_name,
                    status,
                    datetime.now().isoformat(),
                    datetime.now().isoformat() if status in ['SUCCESS', 'FAILED'] else None,
                    duration_seconds,
                    json.dumps(result_data) if result_data else None,
                    error_message,
                    error_traceback
                ))
                conn.commit()
            
            # 完了タスクリストを更新
            if status == 'SUCCESS':
                self._update_completed_tasks(execution_id, step_name)
            
            self.logger.debug(f"Added step {step_name} to {execution_id}: {status}")
            
        except Exception as e:
            self.logger.error(f"Failed to add execution step: {e}")
            raise
    
    def _update_completed_tasks(self, execution_id: str, step_name: str):
        """完了タスクリストを更新"""
        try:
            execution = self.get_execution(execution_id)
            if execution:
                completed_tasks = json.loads(execution.get('completed_tasks', '[]'))
                if step_name not in completed_tasks:
                    completed_tasks.append(step_name)
                    
                    total_tasks = execution.get('total_tasks', 0)
                    progress = (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0
                    
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("""
                            UPDATE execution_logs 
                            SET completed_tasks = ?, progress_percentage = ?
                            WHERE execution_id = ?
                        """, (json.dumps(completed_tasks), progress, execution_id))
                        conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to update completed tasks: {e}")
    
    def add_execution_error(self, execution_id: str, error_info: Dict):
        """実行エラーを追加"""
        try:
            execution = self.get_execution(execution_id)
            if execution:
                errors = json.loads(execution.get('errors', '[]'))
                error_info['timestamp'] = datetime.now().isoformat()
                errors.append(error_info)
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        UPDATE execution_logs 
                        SET errors = ?
                        WHERE execution_id = ?
                    """, (json.dumps(errors), execution_id))
                    conn.commit()
                
                self.logger.warning(f"Added error to {execution_id}: {error_info.get('error_message', 'Unknown error')}")
        except Exception as e:
            self.logger.error(f"Failed to add execution error: {e}")
    
    def get_execution(self, execution_id: str) -> Optional[Dict]:
        """実行記録を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM execution_logs WHERE execution_id = ?
                """, (execution_id,))
                row = cursor.fetchone()
                
                if row:
                    execution = dict(row)
                    
                    # ステップ情報を追加
                    steps_cursor = conn.execute("""
                        SELECT * FROM execution_steps 
                        WHERE execution_id = ? 
                        ORDER BY created_at
                    """, (execution_id,))
                    execution['steps'] = [dict(step) for step in steps_cursor.fetchall()]
                    
                    return execution
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get execution: {e}")
            return None
    
    def list_executions(self, limit: int = 50, offset: int = 0,
                       execution_type: Optional[str] = None,
                       symbol: Optional[str] = None,
                       status: Optional[str] = None,
                       days: Optional[int] = None) -> List[Dict]:
        """実行記録一覧を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                where_conditions = []
                params = []
                
                if execution_type:
                    where_conditions.append("execution_type = ?")
                    params.append(execution_type)
                
                if symbol:
                    where_conditions.append("(symbol = ? OR symbols LIKE ?)")
                    params.extend([symbol, f'%"{symbol}"%'])
                
                if status:
                    where_conditions.append("status = ?")
                    params.append(status)
                
                if days:
                    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                    where_conditions.append("timestamp_start >= ?")
                    params.append(cutoff_date)
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                cursor = conn.execute(f"""
                    SELECT execution_id, execution_type, symbol, symbols,
                           timestamp_start, timestamp_end, status, duration_seconds,
                           triggered_by, current_operation, progress_percentage,
                           total_tasks, completed_tasks
                    FROM execution_logs 
                    WHERE {where_clause}
                    ORDER BY timestamp_start DESC 
                    LIMIT ? OFFSET ?
                """, params + [limit, offset])
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to list executions: {e}")
            return []
    
    def get_execution_statistics(self, days: int = 30) -> Dict:
        """実行統計を取得"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 基本統計
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_executions,
                        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                        AVG(duration_seconds) as avg_duration,
                        SUM(duration_seconds) as total_duration
                    FROM execution_logs 
                    WHERE timestamp_start >= ?
                """, (cutoff_date,))
                
                row = cursor.fetchone()
                basic_stats = dict(row) if row else {}
                
                # タイプ別統計
                cursor = conn.execute("""
                    SELECT 
                        execution_type,
                        COUNT(*) as count,
                        AVG(duration_seconds) as avg_duration,
                        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful
                    FROM execution_logs 
                    WHERE timestamp_start >= ?
                    GROUP BY execution_type
                    ORDER BY count DESC
                """, (cutoff_date,))
                
                type_stats = [dict(row) for row in cursor.fetchall()]
                
                # 成功率計算
                total = basic_stats.get('total_executions', 0)
                successful = basic_stats.get('successful', 0)
                success_rate = (successful / total * 100) if total > 0 else 0
                
                return {
                    'period_days': days,
                    'total_executions': total,
                    'success_rate': round(success_rate, 1),
                    'failed_executions': basic_stats.get('failed', 0),
                    'avg_duration_seconds': round(basic_stats.get('avg_duration', 0) or 0, 1),
                    'total_compute_hours': round((basic_stats.get('total_duration', 0) or 0) / 3600, 2),
                    'by_type': type_stats
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get execution statistics: {e}")
            return {}
    
    def cleanup_old_executions(self, days: int = 90):
        """古い実行記録をクリーンアップ"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # 古いステップを削除
                cursor = conn.execute("""
                    DELETE FROM execution_steps 
                    WHERE execution_id IN (
                        SELECT execution_id FROM execution_logs 
                        WHERE timestamp_start < ?
                    )
                """, (cutoff_date,))
                steps_deleted = cursor.rowcount
                
                # 古い実行記録を削除
                cursor = conn.execute("""
                    DELETE FROM execution_logs 
                    WHERE timestamp_start < ?
                """, (cutoff_date,))
                executions_deleted = cursor.rowcount
                
                conn.commit()
                
                self.logger.info(f"🧹 Cleaned up {executions_deleted} executions and {steps_deleted} steps older than {days} days")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old executions: {e}")


# 使用例とテスト
def main():
    """テスト実行"""
    db = ExecutionLogDatabase("test_execution_logs.db")
    
    # テスト実行記録作成
    execution_id = db.create_execution(
        ExecutionType.SYMBOL_ADDITION,
        symbol="HYPE",
        triggered_by="USER:test",
        metadata={"test": True}
    )
    print(f"Created execution: {execution_id}")
    
    # ステータス更新
    db.update_execution_status(
        execution_id, 
        ExecutionStatus.RUNNING,
        current_operation="データ取得中",
        progress_percentage=25.0,
        total_tasks=4
    )
    
    # ステップ追加
    db.add_execution_step(
        execution_id,
        "data_fetch",
        "SUCCESS",
        result_data={"records": 5000}
    )
    
    # 実行記録取得
    execution = db.get_execution(execution_id)
    print(f"Execution: {execution['status']} - {execution['current_operation']}")
    
    # 統計取得
    stats = db.get_execution_statistics(30)
    print(f"Statistics: {stats}")


if __name__ == "__main__":
    main()