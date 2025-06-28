#!/usr/bin/env python3
"""
新銘柄追加システム
統一戦略管理 + 事前タスク作成 + 詳細進捗追跡
"""

import sqlite3
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from real_time_system.utils.colored_log import get_colored_logger
from auto_symbol_training import AutoSymbolTrainer
from execution_log_database import ExecutionStatus


class TaskStatus(Enum):
    """タスクステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionMode(Enum):
    """実行モード"""
    DEFAULT = "default"      # 全デフォルト戦略
    SELECTIVE = "selective"  # 選択戦略
    CUSTOM = "custom"        # カスタム戦略のみ


@dataclass
class StrategyConfig:
    """戦略設定"""
    id: int
    name: str
    base_strategy: str
    timeframe: str
    parameters: Dict[str, Any]
    description: str
    is_default: bool
    is_active: bool


@dataclass
class PreTask:
    """事前作成タスク"""
    symbol: str
    strategy_config_id: int
    strategy_name: str
    execution_id: str
    timeframe: str
    config: str
    task_status: TaskStatus = TaskStatus.PENDING
    task_created_at: datetime = None
    task_started_at: datetime = None
    task_completed_at: datetime = None
    error_message: str = None
    retry_count: int = 0


class NewSymbolAdditionSystem:
    """新銘柄追加システム"""
    
    def __init__(self):
        self.logger = get_colored_logger(__name__)
        
        # データベースパス
        project_root = Path(__file__).parent
        self.execution_logs_db = project_root / "execution_logs.db"
        self.analysis_db = project_root / "large_scale_analysis" / "analysis.db"
        
        # 既存システム統合
        self.auto_trainer = AutoSymbolTrainer()
        
        self.logger.info("🚀 新銘柄追加システム初期化完了")
    
    def get_strategy_configurations(self, mode: ExecutionMode = ExecutionMode.DEFAULT, 
                                  selected_ids: List[int] = None) -> List[StrategyConfig]:
        """戦略設定取得"""
        with sqlite3.connect(self.analysis_db) as conn:
            if mode == ExecutionMode.DEFAULT:
                # デフォルト戦略のみ
                cursor = conn.execute("""
                    SELECT id, name, base_strategy, timeframe, parameters, description, is_default, is_active
                    FROM strategy_configurations 
                    WHERE is_default=1 AND is_active=1
                    ORDER BY base_strategy, timeframe
                """)
            elif mode == ExecutionMode.SELECTIVE and selected_ids:
                # 選択された戦略
                placeholders = ','.join('?' for _ in selected_ids)
                cursor = conn.execute(f"""
                    SELECT id, name, base_strategy, timeframe, parameters, description, is_default, is_active
                    FROM strategy_configurations 
                    WHERE id IN ({placeholders}) AND is_active=1
                    ORDER BY base_strategy, timeframe
                """, selected_ids)
            elif mode == ExecutionMode.CUSTOM:
                # カスタム戦略のみ
                cursor = conn.execute("""
                    SELECT id, name, base_strategy, timeframe, parameters, description, is_default, is_active
                    FROM strategy_configurations 
                    WHERE is_default=0 AND is_active=1
                    ORDER BY base_strategy, timeframe
                """)
            else:
                # フォールバック：デフォルト戦略
                cursor = conn.execute("""
                    SELECT id, name, base_strategy, timeframe, parameters, description, is_default, is_active
                    FROM strategy_configurations 
                    WHERE is_default=1 AND is_active=1
                    ORDER BY base_strategy, timeframe
                """)
            
            strategies = []
            for row in cursor.fetchall():
                strategies.append(StrategyConfig(
                    id=row[0],
                    name=row[1],
                    base_strategy=row[2],
                    timeframe=row[3],
                    parameters=json.loads(row[4]),
                    description=row[5],
                    is_default=bool(row[6]),
                    is_active=bool(row[7])
                ))
        
        self.logger.info(f"📋 {mode.value}モード: {len(strategies)}個の戦略を取得")
        return strategies
    
    def convert_strategy_ids_to_legacy_format(self, strategy_ids: List[int]) -> tuple:
        """戦略IDを既存システム形式に変換"""
        with sqlite3.connect(self.analysis_db) as conn:
            if not strategy_ids:
                # デフォルト戦略を使用
                cursor = conn.execute("""
                    SELECT DISTINCT base_strategy, timeframe 
                    FROM strategy_configurations 
                    WHERE is_default=1 AND is_active=1
                """)
            else:
                placeholders = ','.join('?' for _ in strategy_ids)
                cursor = conn.execute(f"""
                    SELECT DISTINCT base_strategy, timeframe 
                    FROM strategy_configurations 
                    WHERE id IN ({placeholders}) AND is_active=1
                """, strategy_ids)
            
            results = cursor.fetchall()
            
            # 戦略とタイムフレームを分離
            strategies = list(set(row[0] for row in results))
            timeframes = list(set(row[1] for row in results))
            
            self.logger.info(f"変換結果: {len(strategies)}戦略 × {len(timeframes)}時間足")
            self.logger.debug(f"戦略: {strategies}")
            self.logger.debug(f"時間足: {timeframes}")
            
            return strategies, timeframes
    
    def get_strategy_configs_for_legacy(self, strategy_ids: List[int]) -> List[Dict]:
        """戦略IDから既存システム用の設定リストを生成"""
        if not strategy_ids:
            return None
            
        with sqlite3.connect(self.analysis_db) as conn:
            placeholders = ','.join('?' for _ in strategy_ids)
            cursor = conn.execute(f"""
                SELECT id, name, base_strategy, timeframe, parameters, description, is_default, is_active
                FROM strategy_configurations 
                WHERE id IN ({placeholders}) AND is_active=1
            """, strategy_ids)
            
            configs = []
            for row in cursor.fetchall():
                configs.append({
                    'id': row[0],
                    'name': row[1],
                    'base_strategy': row[2],
                    'timeframe': row[3],
                    'parameters': json.loads(row[4]),
                    'description': row[5],
                    'is_default': bool(row[6]),
                    'is_active': bool(row[7])
                })
            
            return configs
    
    def create_pre_tasks(self, symbol: str, execution_id: str, 
                        strategies: List[StrategyConfig]) -> List[PreTask]:
        """事前タスク作成"""
        pre_tasks = []
        
        with sqlite3.connect(self.analysis_db) as conn:
            for strategy in strategies:
                try:
                    # 事前タスク作成
                    conn.execute("""
                        INSERT INTO analyses (
                            symbol, timeframe, config, strategy_config_id, strategy_name, 
                            execution_id, task_status, task_created_at, retry_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        strategy.timeframe,
                        strategy.base_strategy,
                        strategy.id,
                        strategy.name,
                        execution_id,
                        TaskStatus.PENDING.value,
                        datetime.now(timezone.utc).isoformat(),
                        0
                    ))
                    
                    pre_task = PreTask(
                        symbol=symbol,
                        strategy_config_id=strategy.id,
                        strategy_name=strategy.name,
                        execution_id=execution_id,
                        timeframe=strategy.timeframe,
                        config=strategy.base_strategy,
                        task_status=TaskStatus.PENDING,
                        task_created_at=datetime.now(timezone.utc)
                    )
                    pre_tasks.append(pre_task)
                    
                except Exception as e:
                    self.logger.error(f"タスク作成失敗 {strategy.name}: {e}")
                    continue
            
            conn.commit()
        
        self.logger.success(f"✅ {len(pre_tasks)}個の事前タスクを作成")
        return pre_tasks
    
    def update_task_status(self, execution_id: str, strategy_config_id: int, 
                          status: TaskStatus, error_message: str = None,
                          result_data: Dict = None) -> bool:
        """タスクステータス更新"""
        try:
            with sqlite3.connect(self.analysis_db) as conn:
                if status == TaskStatus.RUNNING:
                    conn.execute("""
                        UPDATE analyses SET 
                        task_status=?, task_started_at=datetime('now')
                        WHERE execution_id=? AND strategy_config_id=?
                    """, (status.value, execution_id, strategy_config_id))
                
                elif status == TaskStatus.COMPLETED:
                    # 結果データも更新
                    update_data = {
                        'task_status': status.value,
                        'task_completed_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    if result_data:
                        update_data.update(result_data)
                    
                    # 動的SQL構築
                    set_clauses = []
                    values = []
                    for key, value in update_data.items():
                        set_clauses.append(f"{key}=?")
                        values.append(value)
                    
                    values.extend([execution_id, strategy_config_id])
                    
                    conn.execute(f"""
                        UPDATE analyses SET {', '.join(set_clauses)}
                        WHERE execution_id=? AND strategy_config_id=?
                    """, values)
                
                elif status == TaskStatus.FAILED:
                    conn.execute("""
                        UPDATE analyses SET 
                        task_status=?, error_message=?, retry_count=retry_count+1
                        WHERE execution_id=? AND strategy_config_id=?
                    """, (status.value, error_message, execution_id, strategy_config_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"ステータス更新失敗: {e}")
            return False
    
    def update_execution_logs_status(self, execution_id: str, status: ExecutionStatus, 
                                   current_operation: str = None, progress_percentage: float = None):
        """execution_logsテーブルのステータス更新"""
        try:
            with sqlite3.connect(self.execution_logs_db) as conn:
                if progress_percentage is not None:
                    conn.execute("""
                        UPDATE execution_logs 
                        SET status=?, current_operation=?, progress_percentage=?, updated_at=datetime('now')
                        WHERE execution_id=?
                    """, (status.value, current_operation, progress_percentage, execution_id))
                else:
                    conn.execute("""
                        UPDATE execution_logs 
                        SET status=?, current_operation=?, updated_at=datetime('now')
                        WHERE execution_id=?
                    """, (status.value, current_operation, execution_id))
                
                conn.commit()
                self.logger.info(f"execution_logs更新: {execution_id} → {status.value}")
                return True
                
        except Exception as e:
            self.logger.error(f"execution_logsステータス更新失敗: {e}")
            return False
    
    def get_execution_progress(self, execution_id: str) -> Dict[str, Any]:
        """実行進捗取得"""
        with sqlite3.connect(self.analysis_db) as conn:
            # 全体進捗
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN task_status='completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN task_status='running' THEN 1 ELSE 0 END) as running,
                    SUM(CASE WHEN task_status='failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN task_status='pending' THEN 1 ELSE 0 END) as pending
                FROM analyses WHERE execution_id=?
            """, (execution_id,))
            
            total, completed, running, failed, pending = cursor.fetchone()
            
            # 詳細タスク情報
            cursor = conn.execute("""
                SELECT strategy_name, task_status, task_created_at, task_started_at, 
                       task_completed_at, error_message, total_return, sharpe_ratio
                FROM analyses 
                WHERE execution_id=? 
                ORDER BY strategy_config_id
            """, (execution_id,))
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'strategy_name': row[0],
                    'status': row[1],
                    'created_at': row[2],
                    'started_at': row[3],
                    'completed_at': row[4],
                    'error_message': row[5],
                    'total_return': row[6],
                    'sharpe_ratio': row[7]
                })
        
        progress_percentage = (completed / total * 100) if total > 0 else 0
        
        return {
            'execution_id': execution_id,
            'total_tasks': total,
            'completed': completed,
            'running': running,
            'failed': failed,
            'pending': pending,
            'progress_percentage': round(progress_percentage, 2),
            'is_complete': pending == 0 and running == 0,
            'tasks': tasks
        }
    
    async def execute_symbol_addition(self, symbol: str, execution_id: str,
                                    execution_mode: ExecutionMode = ExecutionMode.DEFAULT,
                                    selected_strategy_ids: List[int] = None,
                                    custom_period_settings: Dict = None,
                                    filter_params: Dict = None) -> bool:
        """銘柄追加実行（既存システム統合）"""
        self.logger.info(f"🚀 銘柄追加開始: {symbol} ({execution_mode.value})")
        
        try:
            # execution_logsステータス更新: RUNNING
            self.update_execution_logs_status(execution_id, ExecutionStatus.RUNNING, 
                                            f"{symbol}分析開始", 0)
            
            # 戦略IDを既存システム形式に変換
            if execution_mode == ExecutionMode.DEFAULT:
                # デフォルトモード: 全デフォルト戦略
                selected_strategies, selected_timeframes = self.convert_strategy_ids_to_legacy_format([])
                strategy_configs = None
            elif execution_mode == ExecutionMode.SELECTIVE or execution_mode == ExecutionMode.CUSTOM:
                # 選択/カスタムモード: 指定戦略のみ
                if not selected_strategy_ids:
                    self.logger.error("選択モードで戦略IDが未指定")
                    self.update_execution_logs_status(execution_id, ExecutionStatus.FAILED, 
                                                    "戦略未選択エラー")
                    return False
                    
                # 🔧 修正: SELECTIVE/CUSTOMモード共に戦略ID個別処理に統一
                strategy_configs = self.get_strategy_configs_for_legacy(selected_strategy_ids)
                selected_strategies = None  # デカルト積を無効化
                selected_timeframes = None
            
            self.logger.info(f"変換完了 - 戦略: {selected_strategies}, 時間足: {selected_timeframes}, 設定: {len(strategy_configs) if strategy_configs else 0}")
            self.logger.info(f"📅 カスタム期間設定: {custom_period_settings}")
            
            # 🔥 重要: Pre-task作成（これまで欠けていた処理）
            if strategy_configs:
                # カスタム戦略モードでpre-task作成
                strategy_objects = []
                for config in strategy_configs:
                    strategy_objects.append(StrategyConfig(
                        id=config['id'],
                        name=config['name'],
                        base_strategy=config['base_strategy'],
                        timeframe=config['timeframe'],
                        parameters=config['parameters'],
                        description=config['description'],
                        is_default=config.get('is_default', False),
                        is_active=config.get('is_active', True)
                    ))
                pre_tasks = self.create_pre_tasks(symbol, execution_id, strategy_objects)
                self.logger.info(f"🎯 Pre-task作成完了: {len(pre_tasks)}タスク")
            else:
                # デフォルト・選択モードでは既存システムがpre-task作成を処理
                self.logger.info("🎯 既存システムがpre-task作成を実行")
            
            # 既存のauto_symbol_trainingを呼び出し（Pre-task作成はスキップ）
            result_execution_id = await self.auto_trainer.add_symbol_with_training(
                symbol=symbol,
                execution_id=execution_id,
                selected_strategies=selected_strategies,
                selected_timeframes=selected_timeframes,
                strategy_configs=strategy_configs,
                skip_pretask_creation=True,
                custom_period_settings=custom_period_settings,
                filter_params=filter_params
            )
            
            self.logger.success(f"✅ {symbol} 分析完了: {result_execution_id}")
            
            # 新システムのanalysesテーブルにもタスクステータスを同期
            await self.sync_analysis_results_to_new_system(symbol, execution_id, selected_strategy_ids)
            
            return True
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # 詳細なエラーログ（切り詰めなし）
            self.logger.error(f"❌ {symbol} 分析失敗 ({error_type}): {error_msg}")
            
            # execution_logsステータス更新: FAILED（250文字に拡大）
            detailed_status = f"[{error_type}] {error_msg}"
            self.update_execution_logs_status(execution_id, ExecutionStatus.FAILED, 
                                            detailed_status[:250])
            
            # analysesテーブルのpendingタスクもfailedに更新（元のままフル情報）
            self.update_pending_tasks_to_failed(execution_id, symbol, error_msg)
            
            return False
    
    def update_pending_tasks_to_failed(self, execution_id: str, symbol: str, error_message: str):
        """pendingタスクをfailedに更新"""
        try:
            with sqlite3.connect(self.analysis_db) as conn:
                # pendingタスクをfailedに更新
                cursor = conn.execute("""
                    UPDATE analyses 
                    SET task_status = 'failed',
                        error_message = ?,
                        task_completed_at = datetime('now')
                    WHERE execution_id = ? 
                    AND symbol = ?
                    AND task_status = 'pending'
                """, (error_message[:1000], execution_id, symbol))  # 500→1000文字に拡大
                
                updated_count = cursor.rowcount
                conn.commit()
                
                if updated_count > 0:
                    self.logger.info(f"📝 {updated_count}件のpendingタスクをfailedに更新: {symbol}")
                    
        except Exception as e:
            self.logger.error(f"タスクステータス更新エラー: {e}")
    
    async def sync_analysis_results_to_new_system(self, symbol: str, execution_id: str, 
                                                selected_strategy_ids: List[int] = None):
        """既存システムの分析結果を新システムのanalysesテーブルに同期"""
        try:
            with sqlite3.connect(self.analysis_db) as conn:
                # 既存システムで作成された分析結果を取得（execution_idがNULLのもの）
                cursor = conn.execute("""
                    SELECT symbol, timeframe, config, total_return, sharpe_ratio, 
                           max_drawdown, win_rate, total_trades, generated_at
                    FROM analyses 
                    WHERE symbol=? AND execution_id IS NULL 
                    ORDER BY generated_at DESC
                """, (symbol,))
                
                recent_results = cursor.fetchall()
                self.logger.info(f"既存分析結果を{len(recent_results)}件発見")
                
                # 各結果を新システム形式でも記録
                for result in recent_results:
                    # 対応する戦略設定IDを検索
                    strategy_cursor = conn.execute("""
                        SELECT id, name FROM strategy_configurations 
                        WHERE base_strategy=? AND timeframe=? AND is_active=1
                        LIMIT 1
                    """, (result[2], result[1]))  # config, timeframe
                    
                    strategy_info = strategy_cursor.fetchone()
                    if strategy_info:
                        strategy_config_id, strategy_name = strategy_info
                        
                        # 選択戦略の場合は、選択されたIDに含まれるかチェック
                        if selected_strategy_ids and strategy_config_id not in selected_strategy_ids:
                            continue
                        
                        # 新システム形式でタスクを作成/更新
                        conn.execute("""
                            INSERT OR REPLACE INTO analyses 
                            (symbol, timeframe, config, strategy_config_id, strategy_name, 
                             execution_id, task_status, task_created_at, task_started_at, 
                             task_completed_at, total_return, sharpe_ratio, max_drawdown, 
                             win_rate, total_trades, generated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            result[0], result[1], result[2], strategy_config_id, strategy_name,
                            execution_id, 'completed', 
                            result[8], result[8], result[8],  # created=started=completed=generated_at
                            result[3], result[4], result[5], result[6], result[7], result[8]
                        ))
                
                conn.commit()
                self.logger.info(f"分析結果同期完了: {symbol}")
                
        except Exception as e:
            self.logger.error(f"分析結果同期失敗: {e}")
            # 同期失敗してもメイン処理は継続


if __name__ == "__main__":
    # テスト実行
    async def test_system():
        system = NewSymbolAdditionSystem()
        
        # デフォルト戦略で実行
        await system.execute_symbol_addition(
            symbol="TEST",
            execution_id="test_execution_001",
            execution_mode=ExecutionMode.DEFAULT
        )
        
        # 進捗確認
        progress = system.get_execution_progress("test_execution_001")
        print(json.dumps(progress, indent=2, ensure_ascii=False))
    
    asyncio.run(test_system())