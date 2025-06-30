"""
大規模バックテスト分析システム
数千パターンに対応したスケーラブルな分析・可視化システム
"""
import pandas as pd
import numpy as np
import os
import json
import sqlite3
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import cpu_count
import shutil
import gzip
import pickle
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import asyncio
import aiohttp
import time
from typing import List
import requests

# 価格データ整合性チェックシステムのインポート
from engines.price_consistency_validator import PriceConsistencyValidator, UnifiedPriceData

# 進捗ロガーのインポート
from progress_logger import SymbolProgressLogger

# エラー例外のインポート
from engines.leverage_decision_engine import InsufficientConfigurationError

# Stage 9フィルタリングシステム削除済み (2025年6月29日)
# 理由: 性能問題 - "軽量事前チェック"と謳いながら重い計算を実行
# 詳細: README.md参照

# 環境変数読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScalableAnalysisSystem:
    def __init__(self, base_dir="large_scale_analysis"):
        import os
        import inspect
        
        # 🔧 強制的にrootディレクトリのDBを使用（完全DB統一強化版）
        script_dir = Path(__file__).parent.absolute()  # scalable_analysis_system.pyの絶対パス
        
        # 常にプロジェクトルートの正規DBを使用（相対パス禁止）
        if os.path.isabs(base_dir):
            # 絶対パス指定の場合はそのまま使用
            self.base_dir = Path(base_dir)
        else:
            # 相対パス指定は必ずスクリプトディレクトリ基準に統一
            self.base_dir = script_dir / base_dir
        
        # web_dashboardディレクトリ内のDB作成を完全に防止
        if 'web_dashboard' in str(self.base_dir):
            logger.warning(f"⚠️ web_dashboard内DB作成を阻止: {self.base_dir}")
            self.base_dir = script_dir / base_dir
            
        self.base_dir.mkdir(exist_ok=True)
        
        # ディレクトリ構造
        self.db_path = self.base_dir / "analysis.db"
        self.charts_dir = self.base_dir / "charts"
        self.data_dir = self.base_dir / "data"
        self.compressed_dir = self.base_dir / "compressed"
        
        # Note: 初期化ログを削除（冗長出力防止）
        
        for dir_path in [self.charts_dir, self.data_dir, self.compressed_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # 価格データ整合性チェックシステムの初期化
        self.price_validator = PriceConsistencyValidator(
            warning_threshold_pct=1.0,
            error_threshold_pct=5.0,
            critical_threshold_pct=10.0
        )
        
        # データベース初期化
        self.init_database()
        
        # 実行制御
        self.current_execution_id = None
        
        # Stage 9フィルタリングシステム削除済み (性能問題により撤廃)
        # 詳細: README.md参照
    
    def init_database(self):
        """SQLiteデータベースを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 既存テーブル確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # analysesテーブルが存在する場合、カラム構造を確認
            if 'analyses' in existing_tables:
                cursor.execute("PRAGMA table_info(analyses);")
                columns = [row[1] for row in cursor.fetchall()]
                
                # execution_idカラムの存在確認
                if 'execution_id' not in columns:
                    # execution_idカラムを追加
                    cursor.execute('ALTER TABLE analyses ADD COLUMN execution_id TEXT')
                    logger.info("execution_idカラムを追加しました")
                
                if 'task_status' not in columns:
                    # 不足カラムを追加
                    cursor.execute('ALTER TABLE analyses ADD COLUMN task_status TEXT DEFAULT "pending"')
                    cursor.execute('ALTER TABLE analyses ADD COLUMN task_started_at TIMESTAMP')
                    cursor.execute('ALTER TABLE analyses ADD COLUMN task_completed_at TIMESTAMP')
                    cursor.execute('ALTER TABLE analyses ADD COLUMN error_message TEXT')
                    logger.info("task_statusカラム等を追加しました")
            
            # 分析メタデータテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    config TEXT NOT NULL,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_trades INTEGER,
                    win_rate REAL,
                    total_return REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    avg_leverage REAL,
                    chart_path TEXT,
                    compressed_path TEXT,
                    status TEXT DEFAULT 'pending',
                    execution_id TEXT,
                    task_status TEXT DEFAULT 'pending',
                    task_started_at TIMESTAMP,
                    task_completed_at TIMESTAMP,
                    error_message TEXT
                )
            ''')
            
            # バックテスト結果サマリー
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtest_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER,
                    metric_name TEXT,
                    metric_value REAL,
                    FOREIGN KEY (analysis_id) REFERENCES analyses (id)
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timeframe ON analyses (symbol, timeframe)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_config ON analyses (config)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sharpe ON analyses (sharpe_ratio)')
            
            conn.commit()
    
    def _should_cancel_execution(self, execution_id: str = None) -> bool:
        """データベースをチェックしてキャンセルされているかを確認"""
        if not execution_id and hasattr(self, 'current_execution_id'):
            execution_id = self.current_execution_id
        
        if not execution_id:
            return False
            
        try:
            from execution_log_database import ExecutionLogDatabase
            db = ExecutionLogDatabase()
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.execute(
                    'SELECT status FROM execution_logs WHERE execution_id = ?',
                    (execution_id,)
                )
                row = cursor.fetchone()
                return row and row[0] == 'CANCELLED'
        except Exception as e:
            logger.warning(f"Failed to check cancellation status: {e}")
            return False
    
    def generate_batch_analysis(self, batch_configs, max_workers=None, symbol=None, execution_id=None, skip_pretask_creation=False, custom_period_settings=None):
        """
        バッチで大量の分析を並列生成
        
        Args:
            batch_configs: [{'symbol': 'BTC', 'timeframe': '1h', 'config': 'ML'}, ...]
            max_workers: 並列数（デフォルト: CPU数）
            symbol: 銘柄名（進捗表示用）
            execution_id: 実行ID（進捗表示用）
            skip_pretask_creation: Pre-task作成をスキップするかどうか
            custom_period_settings: カスタム期間設定
        """
        # カスタム期間設定の初期化（安全性のため最初に実行）
        custom_period_settings = custom_period_settings or {}
        
        if max_workers is None:
            max_workers = min(cpu_count(), 4)  # Rate Limit対策で最大4並列
        
        # 実行IDを設定
        self.current_execution_id = execution_id
        
        # 🔥 重要: Pre-task作成（リアルタイム進捗追跡のため）
        if execution_id and not skip_pretask_creation:
            self._create_pre_tasks(batch_configs, execution_id)
        
        # 進捗ロガーの初期化
        progress_logger = None
        if symbol and execution_id:
            progress_logger = SymbolProgressLogger(symbol, execution_id, len(batch_configs))
            progress_logger.log_phase_start("バックテスト", f"{len(batch_configs)}パターン, {max_workers}並列")
        else:
            logger.info(f"バッチ分析開始: {len(batch_configs)}パターン, {max_workers}並列")
        
        self.max_workers = max_workers  # インスタンス変数として保存
        # self.progress_logger = progress_logger  # 🐛 Pickle化エラー修正: インスタンス変数への保存を無効化
        
        # バッチをチャンクに分割
        chunk_size = max(1, len(batch_configs) // max_workers)
        chunks = [batch_configs[i:i + chunk_size] for i in range(0, len(batch_configs), chunk_size)]
        
        # 期間設定を環境変数に設定（子プロセス用）
        import os
        import json
        if custom_period_settings and custom_period_settings.get('mode'):
            os.environ['CUSTOM_PERIOD_SETTINGS'] = json.dumps(custom_period_settings)
            logger.info(f"📅 期間設定を環境変数に設定: {custom_period_settings}")
        
        # デバッグモードも子プロセスに伝達
        debug_mode = os.environ.get('SUPPORT_RESISTANCE_DEBUG', 'false')
        if debug_mode.lower() == 'true':
            logger.info(f"🔍 Support/Resistance デバッグモード有効")
            # 子プロセスでも確実に設定されるようにする
            os.environ['SUPPORT_RESISTANCE_DEBUG'] = 'true'
        
        # execution_idも子プロセスに伝達（progress_tracker用）
        if execution_id:
            os.environ['CURRENT_EXECUTION_ID'] = execution_id
            logger.info(f"📝 実行IDを環境変数に設定: {execution_id}")
            
            # ファイルベースprogress_trackerの初期化
            try:
                from file_based_progress_tracker import file_progress_tracker
                file_progress_tracker.start_analysis(symbol, execution_id)
                logger.info(f"📝 FileBasedProgressTracker初期化完了: {execution_id}")
            except Exception as e:
                logger.warning(f"⚠️ FileBasedProgressTracker初期化エラー: {e}")
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i, chunk in enumerate(chunks):
                # execution_idを明示的に渡す
                future = executor.submit(self._process_chunk, chunk, i, self.current_execution_id)
                futures.append(future)
            
            # 結果収集（タイムアウト付き）
            total_processed = 0
            for i, future in enumerate(futures):
                try:
                    # 各チャンクに30分のタイムアウトを設定
                    processed_count = future.result(timeout=1800)  # 30 minutes
                    total_processed += processed_count
                    
                    if progress_logger:
                        # 進捗ログは個別戦略完了時に出力されるため、ここでは簡潔に
                        pass
                    else:
                        logger.info(f"チャンク {i+1}/{len(futures)} 完了: {processed_count}パターン処理")
                except Exception as e:
                    logger.error(f"チャンク {i+1} 処理エラー: {e}")
                    if progress_logger:
                        progress_logger.log_error(f"チャンク {i+1} 処理エラー: {e}", "バックテスト")
                    # エラーが発生してもプロセスプールを破損させない
                    if "BrokenProcessPool" in str(e):
                        logger.error("プロセスプール破損検出 - 残りのチャンクをスキップ")
                        break
        
        if progress_logger:
            progress_logger.log_phase_complete("バックテスト")
            # 成功判定: 分析が実行された場合（シグナルなしでも成功）
            analysis_attempted = len(batch_configs) > 0
            
            # ファイルベースprogress_tracker更新 - 新しいFileBasedProgressTrackerを使用
            if execution_id:
                try:
                    from file_based_progress_tracker import file_progress_tracker
                    file_progress_tracker.update_stage(execution_id, "support_resistance")
                    logger.info(f"📝 新progress_tracker段階更新: backtest_completed → support_resistance")
                except Exception as e:
                    logger.warning(f"⚠️ ファイルベースprogress_tracker更新エラー: {e}")
            progress_logger.log_final_summary(analysis_attempted)
        else:
            logger.info(f"バッチ分析完了: {total_processed}パターン処理完了")
        
        return total_processed
    
    def _create_pre_tasks(self, batch_configs, execution_id):
        """Pre-task作成（分析実行前にpendingレコード作成）"""
        logger.info(f"🎯 Pre-task作成開始: {len(batch_configs)}タスク, execution_id={execution_id}")
        logger.info(f"  🗃️ 作成先DB: {self.db_path.absolute()}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            created_count = 0
            for config in batch_configs:
                symbol = config['symbol']
                timeframe = config['timeframe']
                
                # config辞書から適切なキーを取得（_process_chunkと同じロジック）
                if 'strategy' in config:
                    config_name = config['strategy']
                elif 'config' in config:
                    config_name = config['config']
                else:
                    config_name = 'Default'
                
                try:
                    # 既存のpendingタスク確認（実行中のタスクがある場合は重複作成を防ぐ）
                    cursor.execute('''
                        SELECT COUNT(*) FROM analyses 
                        WHERE symbol=? AND timeframe=? AND config=? AND execution_id=? 
                        AND task_status IN ('pending', 'running')
                    ''', (symbol, timeframe, config_name, execution_id))
                    
                    if cursor.fetchone()[0] == 0:
                        # Pendingタスク作成
                        cursor.execute('''
                            INSERT INTO analyses 
                            (symbol, timeframe, config, task_status, execution_id, status)
                            VALUES (?, ?, ?, 'pending', ?, 'running')
                        ''', (symbol, timeframe, config_name, execution_id))
                        created_count += 1
                
                except Exception as e:
                    logger.error(f"Pre-task作成エラー {symbol} {timeframe} {config_name}: {e}")
            
            conn.commit()
            logger.info(f"✅ Pre-task作成完了: {created_count}タスク作成")
            
        return created_count
    
    def _setup_child_process_logging(self):
        """子プロセスでのロギング設定を初期化"""
        import logging
        import os
        
        # 既存のハンドラーをクリア
        logger = logging.getLogger()
        logger.handlers = []
        
        # ログレベル設定
        logger.setLevel(logging.INFO)
        
        # フォーマッター
        formatter = logging.Formatter('%(asctime)s - %(process)d - %(levelname)s - %(message)s')
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # server.logファイルハンドラー（存在する場合）
        server_log_path = os.path.join(os.path.dirname(__file__), 'web_dashboard', 'server.log')
        if os.path.exists(os.path.dirname(server_log_path)):
            try:
                file_handler = logging.FileHandler(server_log_path, mode='a')
                file_handler.setLevel(logging.INFO)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                # ファイルハンドラーの追加に失敗した場合は無視
                pass
        
        # 各モジュールのロガーも再設定（ProcessPoolExecutor環境強化）
        for module_name in ['__main__', 'scalable_analysis_system', 'engines.support_resistance_detector', 
                           'engines.support_resistance_adapter', 'engines.high_leverage_bot_orchestrator',
                           'engines.analysis_result']:
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(logging.INFO)
            
            # 子プロセス用のコンソールハンドラー追加（重複チェック付き）
            has_console_handler = any(isinstance(h, logging.StreamHandler) for h in module_logger.handlers)
            if not has_console_handler:
                console_handler_child = logging.StreamHandler()
                console_handler_child.setLevel(logging.INFO)
                console_handler_child.setFormatter(formatter)
                module_logger.addHandler(console_handler_child)
    
    def _process_chunk(self, configs_chunk, chunk_id, execution_id=None):
        """チャンクを処理（プロセス内で実行）"""
        import time
        import random
        import os
        
        # 子プロセスでのロギング設定を追加
        self._setup_child_process_logging()
        
        # execution_idを環境変数に設定（子プロセス用）
        if execution_id:
            os.environ['CURRENT_EXECUTION_ID'] = execution_id
            logger.info(f"チャンク {chunk_id}: execution_id {execution_id} を環境変数に設定")
        else:
            # 環境変数から取得を試みる
            env_execution_id = os.environ.get('CURRENT_EXECUTION_ID')
            if env_execution_id:
                execution_id = env_execution_id
                logger.info(f"チャンク {chunk_id}: 環境変数からexecution_id {execution_id} を取得")
        
        # デバッグモードの確認（子プロセス内）
        debug_mode = os.environ.get('SUPPORT_RESISTANCE_DEBUG', 'false').lower() == 'true'
        if debug_mode:
            logger.info(f"チャンク {chunk_id}: Support/Resistance デバッグモード有効 (PID: {os.getpid()})")
        
        # プロセス間の競合を防ぐため、わずかな遅延を追加
        # TODO: ランダム遅延は品質問題のためコメントアウト (2024-06-18)
        # time.sleep(random.uniform(0.1, 0.5))
        # チャンクIDベースの決定的遅延に変更
        time.sleep(0.1 + (chunk_id % 5) * 0.1)  # 0.1-0.5秒の決定的遅延
        
        processed = 0
        for config in configs_chunk:
            # キャンセル確認（チャンク処理の各設定で確認）
            # ProcessPoolExecutor内では execution_id を引数から取得
            check_execution_id = execution_id or getattr(self, 'current_execution_id', None)
            if check_execution_id:
                if self._should_cancel_execution(check_execution_id):
                    logger.info(f"Cancellation detected for {check_execution_id}, stopping chunk {chunk_id}")
                    break
            
            try:
                # 設定の型チェック
                if not isinstance(config, dict):
                    logger.error(f"Config is not a dict: {type(config)} - {config}")
                    continue
                
                # config辞書から適切なキーを取得
                if 'strategy' in config:
                    strategy = config['strategy']
                elif 'config' in config:
                    strategy = config['config']
                else:
                    strategy = 'Default'
                
                # 戦略キー検証強化
                if not strategy or strategy == 'Default':
                    logger.warning(f"Invalid or missing strategy in config: {config}")
                    continue
                
                # 必要なキーの存在確認
                if 'symbol' not in config or 'timeframe' not in config:
                    logger.error(f"Missing required keys in config: {config}")
                    continue
                
                # execution_idをログ出力
                logger.info(f"🔍 分析開始: {config['symbol']} {config['timeframe']} {strategy} (execution_id: {execution_id})")
                
                result, metrics = self._generate_single_analysis(
                    config['symbol'], 
                    config['timeframe'], 
                    strategy,
                    execution_id
                )
                if result:
                    processed += 1
                    
                    # 進捗ロガーが利用可能な場合、戦略完了をログ
                    # 🐛 Pickle化エラー修正: ProcessPoolExecutor環境では進捗ログを無効化
                    # if hasattr(self, 'progress_logger') and self.progress_logger:
                    #     try:
                    #         self.progress_logger.log_strategy_complete(
                    #             config['timeframe'], 
                    #             strategy,
                    #             metrics or {}
                    #         )
                    #     except Exception as log_error:
                    #         logger.warning(f"Progress logging error: {log_error}")
                    
                    if processed % 10 == 0:
                        logger.info(f"Chunk {chunk_id}: {processed}/{len(configs_chunk)} 完了")
            except Exception as e:
                logger.error(f"分析エラー {config}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # 🔧 子プロセス完了後: 一時ファイルから詳細ログを読み取り
        try:
            import glob
            import json
            if execution_id:
                log_pattern = f"/tmp/analysis_log_{execution_id}_*.json"
                log_files = glob.glob(log_pattern)
                for log_file in log_files:
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            analysis_log = json.load(f)
                        
                        # 詳細ログを親プロセスで表示
                        logger.info(f"📋 子プロセス詳細ログ: {analysis_log['detailed_msg']}")
                        logger.info(f"💡 子プロセス詳細ログ: {analysis_log['user_msg']}")
                        if analysis_log.get('suggestions'):
                            logger.info(f"🎯 子プロセス詳細ログ: 改善提案: {'; '.join(analysis_log['suggestions'])}")
                        
                        # 一時ファイル削除
                        os.remove(log_file)
                    except Exception as read_error:
                        logger.warning(f"一時ファイル読み取りエラー: {read_error}")
        except Exception as cleanup_error:
            logger.warning(f"一時ファイル処理エラー: {cleanup_error}")
        
        return processed
    
    def _update_task_status(self, symbol, timeframe, config, status, error_message=None):
        """task_statusをリアルタイム更新"""
        execution_id = os.environ.get('CURRENT_EXECUTION_ID')
        logger.info(f"🔄 task_status更新: {symbol} {timeframe} {config} → {status}")
        logger.info(f"  🗃️ 更新先DB: {self.db_path.absolute()}")
        logger.info(f"  🔑 execution_id: {execution_id}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                if status == 'running':
                    cursor.execute('''
                        UPDATE analyses 
                        SET task_status = ?, task_started_at = ?
                        WHERE symbol = ? AND timeframe = ? AND config = ? AND execution_id = ?
                    ''', (status, datetime.now(timezone.utc).isoformat(), symbol, timeframe, config, execution_id))
                elif status == 'failed':
                    cursor.execute('''
                        UPDATE analyses 
                        SET task_status = ?, error_message = ?
                        WHERE symbol = ? AND timeframe = ? AND config = ? AND execution_id = ?
                    ''', (status, error_message, symbol, timeframe, config, execution_id))
                elif status == 'completed':
                    cursor.execute('''
                        UPDATE analyses 
                        SET task_status = ?, task_completed_at = ?
                        WHERE symbol = ? AND timeframe = ? AND config = ? AND execution_id = ?
                    ''', (status, datetime.now(timezone.utc).isoformat(), symbol, timeframe, config, execution_id))
                
                updated_rows = cursor.rowcount
                conn.commit()
                logger.info(f"✅ task_status更新成功: {updated_rows}行更新")
                
            except Exception as e:
                logger.error(f"❌ task_status更新エラー: {symbol} {timeframe} {config}")
                logger.error(f"  🗃️ DB path: {self.db_path.absolute()}")
                logger.error(f"  📝 エラー詳細: {str(e)}")
                raise
    
    def _generate_single_analysis(self, symbol, timeframe, config, execution_id=None):
        """単一の分析を生成（ハイレバレッジボット使用版 + task_status更新）"""
        analysis_id = f"{symbol}_{timeframe}_{config}"
        
        # 既存チェック
        if self._analysis_exists(analysis_id):
            return False, None
        
        # task_statusを'running'に更新
        try:
            self._update_task_status(symbol, timeframe, config, 'running')
        except Exception as e:
            logger.warning(f"Failed to update task_status to running: {e}")
        
        # ハイレバレッジボットを使用した分析を試行
        try:
            # execution_idをログ出力
            logger.info(f"🎯 リアル分析開始: {symbol} {timeframe} {config} (execution_id: {execution_id})")
            trades_data = self._generate_real_analysis(symbol, timeframe, config, execution_id=execution_id)
        except Exception as e:
            logger.error(f"Real analysis failed for {symbol} {timeframe} {config}: {e}")
            logger.error(f"Analysis terminated - no fallback to sample data")
            
            # task_statusを'failed'に更新
            try:
                self._update_task_status(symbol, timeframe, config, 'failed', str(e))
            except Exception as update_error:
                logger.warning(f"Failed to update task_status to failed: {update_error}")
            
            return False, None
        
        # メトリクス計算
        metrics = self._calculate_metrics(trades_data)
        
        # データ圧縮保存
        compressed_path = self._save_compressed_data(analysis_id, trades_data)
        
        # チャート生成（必要時のみ）
        chart_path = None
        if self._should_generate_chart(metrics):
            chart_path = self._generate_lightweight_chart(analysis_id, trades_data, metrics)
        
        # データベース保存（execution_id付き + task_status更新含む）
        # execution_idを環境変数または引数から取得（引数を優先）
        final_execution_id = execution_id or os.environ.get('CURRENT_EXECUTION_ID')
        self._save_to_database(symbol, timeframe, config, metrics, chart_path, compressed_path, final_execution_id)
        
        return True, metrics
    
    def _get_exchange_from_config(self, config) -> str:
        """設定から取引所を取得"""
        import json
        import os
        
        # 1. 設定ファイルから読み込み
        try:
            if os.path.exists('exchange_config.json'):
                with open('exchange_config.json', 'r') as f:
                    exchange_config = json.load(f)
                    return exchange_config.get('default_exchange', 'hyperliquid').lower()
        except Exception as e:
            logger.warning(f"Failed to load exchange config: {e}")
        
        # 2. 環境変数から読み込み
        env_exchange = os.getenv('EXCHANGE_TYPE', '').lower()
        if env_exchange in ['hyperliquid', 'gateio']:
            return env_exchange
        
        # 3. デフォルト: Hyperliquid
        return 'hyperliquid'
    
    def _load_timeframe_config(self, timeframe):
        """時間足設定ファイルから設定を読み込み"""
        try:
            config_path = 'config/timeframe_conditions.json'
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    return config_data.get('timeframe_configs', {}).get(timeframe, {})
        except Exception as e:
            logger.warning(f"時間足設定読み込みエラー: {e}")
        return {}
    
    def _calculate_period_with_history(self, custom_period_settings, timeframe):
        """カスタム期間に200本前データを含む期間を計算"""
        try:
            from datetime import datetime, timedelta
            
            start_date = custom_period_settings.get('start_date')
            end_date = custom_period_settings.get('end_date')
            
            if not start_date or not end_date:
                logger.warning("カスタム期間設定に開始・終了日時がありません")
                return 90  # デフォルト
            
            # 文字列から日時に変換
            if isinstance(start_date, str):
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            else:
                start_dt = start_date
                
            if isinstance(end_date, str):
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            else:
                end_dt = end_date
            
            # 時間足に応じた200本前の期間を計算
            timeframe_minutes = {
                '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30, '1h': 60
            }
            
            minutes_per_candle = timeframe_minutes.get(timeframe, 60)
            history_period = timedelta(minutes=200 * minutes_per_candle)
            
            # 開始日時から200本前を計算
            actual_start = start_dt - history_period
            
            # 必要な総期間を日数で計算
            total_period = end_dt - actual_start
            period_days = max(total_period.days + 1, 7)  # 最低7日
            
            logger.info(f"📅 期間計算: {start_dt} → {end_dt}, 200本前含む: {actual_start} ({period_days}日)")
            return period_days
            
        except Exception as e:
            logger.error(f"期間計算エラー: {e}")
            return 90  # デフォルト
    
    def _generate_real_analysis(self, symbol, timeframe, config, custom_period_days=None, execution_id=None):
        """条件ベースのハイレバレッジ分析 - 市場条件を満たした場合のみシグナル生成"""
        # 変数初期化（安全性確保）
        custom_period_settings = None
        
        try:
            # 環境変数からカスタム期間設定を読み取り
            try:
                import os
                if 'CUSTOM_PERIOD_SETTINGS' in os.environ:
                    custom_period_settings = json.loads(os.environ['CUSTOM_PERIOD_SETTINGS'])
                    logger.info(f"📅 環境変数から期間設定読み取り: {custom_period_settings}")
            except Exception as e:
                logger.warning(f"期間設定環境変数読み取りエラー: {e}")
                custom_period_settings = None
            
            # 時間足設定から評価期間を動的に取得
            tf_config = self._load_timeframe_config(timeframe)
            
            # 期間設定の優先順位: custom_period_days > custom_period_settings > 設定ファイル
            if custom_period_days is not None:
                evaluation_period_days = custom_period_days
                logger.info(f"📅 カスタム評価期間: {evaluation_period_days}日")
            elif custom_period_settings and custom_period_settings.get('mode') == 'custom':
                # カスタム期間の場合は200本前データを含む期間を計算
                evaluation_period_days = self._calculate_period_with_history(custom_period_settings, timeframe)
                logger.info(f"📅 ユーザー指定期間+200本: {evaluation_period_days}日 ({timeframe}足)")
            else:
                evaluation_period_days = tf_config.get('data_days', 90)  # 設定ファイルから取得
                logger.info(f"📅 時間足別評価期間: {evaluation_period_days}日 ({timeframe}足設定)")
            
            # 本格的な戦略分析のため、実際のAPIデータを使用
            from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
            
            # 取引所設定を取得
            exchange = self._get_exchange_from_config(config)
            
            logger.info(f"🎯 実データによる戦略分析を開始: {symbol} {timeframe} {config} ({exchange})")
            logger.info("   ⏳ データ取得とML分析のため、処理に数分かかる場合があります...")
            
            # 修正: ハードコード値問題解決のため、毎回新しいボットを作成（キャッシュ無効化）
            # 理由: キャッシュされたデータの再利用により、全トレードで同じエントリー価格が使用される問題を解決
            bot = HighLeverageBotOrchestrator(use_default_plugins=True, exchange=exchange)
            logger.info(f"🔄 {symbol} 新規ボットでデータ取得中... (価格多様性確保のため)")
            
            # 複数回分析を実行してトレードデータを生成（完全ログ抑制）
            trades = []
            import sys
            import os
            import contextlib
            import time
            
            # 進捗表示用
            logger.info(f"🔄 {symbol} {timeframe} {config}: 条件ベース分析開始")
            
            # 完全にログを抑制するコンテキストマネージャー（デバッグモード時は無効）
            @contextlib.contextmanager
            def suppress_all_output():
                debug_mode = os.environ.get('SUPPORT_RESISTANCE_DEBUG', 'false').lower() == 'true'
                if debug_mode:
                    # デバッグモードの場合は出力を抑制しない
                    yield
                else:
                    with open(os.devnull, 'w') as devnull:
                        old_stdout = sys.stdout
                        old_stderr = sys.stderr
                        try:
                            sys.stdout = devnull
                            sys.stderr = devnull
                            yield
                        finally:
                            sys.stdout = old_stdout
                            sys.stderr = old_stderr
            
            # 条件ベースのシグナル生成期間設定
            if custom_period_settings and custom_period_settings.get('mode') == 'custom':
                # ユーザー指定期間を使用
                start_time = datetime.fromisoformat(custom_period_settings['start_date'].replace('T', ' ')).replace(tzinfo=timezone.utc)
                end_time = datetime.fromisoformat(custom_period_settings['end_date'].replace('T', ' ')).replace(tzinfo=timezone.utc)
                logger.info(f"📅 ユーザー指定期間: {start_time.strftime('%Y-%m-%d %H:%M')} ～ {end_time.strftime('%Y-%m-%d %H:%M')}")
            else:
                # デフォルト期間
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=evaluation_period_days)
                logger.info(f"📅 デフォルト期間: {start_time.strftime('%Y-%m-%d %H:%M')} ～ {end_time.strftime('%Y-%m-%d %H:%M')}")
            
            # 時間足設定から評価間隔を取得
            tf_config = self._load_timeframe_config(timeframe)
            
            # 設定ファイルから評価間隔を読み込み（分単位）
            evaluation_interval_minutes = tf_config.get('evaluation_interval_minutes')
            
            if evaluation_interval_minutes:
                evaluation_interval = timedelta(minutes=evaluation_interval_minutes)
            else:
                # フォールバック: デフォルト間隔
                default_intervals = {
                    '1m': timedelta(minutes=5),   '3m': timedelta(minutes=15),
                    '5m': timedelta(minutes=30),  '15m': timedelta(hours=1),
                    '30m': timedelta(hours=2),    '1h': timedelta(hours=4),
                    '4h': timedelta(hours=12),    '1d': timedelta(days=1)
                }
                evaluation_interval = default_intervals.get(timeframe, timedelta(hours=4))
            
            # 初期化: effective_start_timeをstart_timeに設定（後でデータに基づいて調整）
            effective_start_time = start_time
            
            # 条件ベースの分析実行
            current_time = effective_start_time
            total_evaluations = 0
            signals_generated = 0
            
            # 重要変数の初期化（安全性確保）
            result = {}
            ohlcv_df = None
            bot = None
            
            # 🔧 OHLCVデータを事前取得（実データ利用）
            try:
                # APIクライアント初期化
                from hyperliquid_api_client import MultiExchangeAPIClient
                api_client = MultiExchangeAPIClient(exchange_type=exchange)
                
                # OHLCVデータ取得（評価期間 + 支持線・抵抗線用の前データ）
                logger.info(f"📊 {symbol} {timeframe} のOHLCVデータ取得中...")
                
                # 支持線・抵抗線計算用に200本前から取得
                lookback_days = 10  # 200本分の日数（時間足により調整）
                data_start_time = start_time - timedelta(days=lookback_days)
                
                ohlcv_df = api_client.get_ohlcv_dataframe(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=data_start_time,
                    end_time=end_time
                )
                
                if ohlcv_df is not None and not ohlcv_df.empty:
                    logger.info(f"✅ OHLCVデータ取得成功: {len(ohlcv_df)}本")
                    
                    # RealPreparedDataの作成
                    from engines.data_preparers import RealPreparedData
                    real_prepared_data = RealPreparedData(ohlcv_df)
                    
                    # FilteringFrameworkの初期化（実データ使用）
                    self.filtering_framework = FilteringFramework(
                        prepared_data_factory=lambda: real_prepared_data,
                        strategy_factory=lambda: self._create_strategy_from_config(config)
                    )
                else:
                    logger.warning(f"⚠️ OHLCVデータ取得失敗、モックデータを使用")
                    ohlcv_df = None
            except Exception as e:
                logger.warning(f"⚠️ OHLCVデータ取得エラー: {e}、モックデータを使用")
                ohlcv_df = None
            
            # OHLCVデータインデックスベースの評価設定
            if ohlcv_df is not None and not ohlcv_df.empty:
                # 評価対象期間の開始インデックスを特定
                evaluation_start_index = 0
                for i, row in ohlcv_df.iterrows():
                    if pd.to_datetime(row['timestamp']).replace(tzinfo=timezone.utc) >= start_time:
                        evaluation_start_index = i
                        break
                
                # 全OHLCVデータから評価対象部分のみを評価
                total_evaluations_planned = len(ohlcv_df) - evaluation_start_index
                logger.info(f"🔍 条件ベース分析: {start_time.strftime('%Y-%m-%d %H:%M')} から {end_time.strftime('%Y-%m-%d %H:%M')}")
                logger.info(f"📊 評価対象: {evaluation_start_index}本目～{len(ohlcv_df)}本目 (計{total_evaluations_planned}本の{timeframe}足)")
                print(f"💯 全データ評価: 間引きなし、制限なし")
            else:
                logger.warning("⚠️ OHLCVデータが取得できませんでした")
                return []
            
            # 全OHLCVデータを順次評価（制限なし）
            for current_index in range(evaluation_start_index, len(ohlcv_df)):
                current_row = ohlcv_df.iloc[current_index]
                current_time = pd.to_datetime(current_row['timestamp']).replace(tzinfo=timezone.utc)
                total_evaluations += 1
                
                # Stage 9フィルタリング削除済み (2025年6月29日)
                # 理由: 重複処理と性能劣化問題 - Stage 8で十分な分析実行
                
                try:
                    # 出力抑制で市場条件の評価（バックテストフラグ付き）
                    with suppress_all_output():
                        # execution_idをログ出力（初回のみ）
                        if total_evaluations == 1:
                            logger.info(f"🔍 ボット分析開始: execution_id={execution_id}")
                        
                        result = bot.analyze_symbol(symbol, timeframe, config, is_backtest=True, target_timestamp=current_time, custom_period_settings=custom_period_settings, execution_id=execution_id)
                    
                    # 🔍 ProcessPoolExecutor環境診断: 結果の型・内容詳細調査
                    logger.info(f"🔍 子プロセス結果診断: {symbol} {timeframe} {config}")
                    logger.info(f"   結果の型: {type(result)}")
                    if hasattr(result, 'early_exit'):
                        logger.info(f"   AnalysisResult detected - early_exit: {result.early_exit}")
                        if result.early_exit:
                            logger.info(f"   exit_stage: {result.exit_stage}")
                            logger.info(f"   exit_reason: {result.exit_reason}")
                    else:
                        logger.info(f"   結果内容: {result}")
                        if isinstance(result, dict):
                            logger.info(f"   辞書キー: {list(result.keys()) if result else 'None/Empty'}")
                    
                    # 🎯 DISCORD通知処理（ProcessPoolExecutor専用・確実実行版）
                    self._handle_discord_notification_for_result(result, symbol, timeframe, config, execution_id)
                    
                    # 🔍 AnalysisResult対応: Early Exitの詳細ログ出力（ProcessPoolExecutor対応強化版）
                    from engines.analysis_result import AnalysisResult
                    import sys
                    if isinstance(result, AnalysisResult):
                        # 必ずEarly Exit検出ログを出力（通知前確認用）
                        logger.info(f"⚡ AnalysisResult処理開始: early_exit={result.early_exit}")
                        
                        if result.early_exit:
                            # ProcessPoolExecutor環境での確実なログ出力
                            detailed_msg = result.get_detailed_log_message()
                            user_msg = result.get_user_friendly_message()
                            
                            # 強制的なログ出力とフラッシュ（ProcessPoolExecutor対応）
                            logger.info(f"📋 {detailed_msg}")
                            logger.info(f"💡 {user_msg}")
                            
                            # 改善提案も出力
                            suggestions = result.get_suggestions()
                            if suggestions:
                                logger.info(f"🎯 改善提案: {'; '.join(suggestions)}")
                            
                            # ProcessPoolExecutor環境での確実な出力確保
                            sys.stdout.flush()
                            sys.stderr.flush()
                            
                            # ログハンドラーの強制フラッシュ
                            for handler in logger.handlers:
                                if hasattr(handler, 'flush'):
                                    handler.flush()
                            
                            # 🎯 Discord webhook通知: 子プロセスのEarly Exit詳細送信
                            try:
                                # 同期実行（ProcessPoolExecutor環境では非同期は使用できない）
                                import requests
                                
                                # ProcessPoolExecutor環境での環境変数再読み込み
                                try:
                                    from dotenv import load_dotenv
                                    load_dotenv()
                                except ImportError:
                                    pass
                                
                                # Discord webhook URL (環境変数から取得)
                                webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
                                
                                # デバッグログ: Discord通知試行ログ
                                logger.info(f"🎯 Discord通知試行: {symbol} {timeframe} {config}")
                                logger.info(f"   webhook_url設定: {bool(webhook_url)}")
                                logger.info(f"   Early Exit詳細: {result.exit_stage}/{result.exit_reason}")
                                
                                if webhook_url:
                                    # embed作成
                                    embed = {
                                        "title": f"🚨 Early Exit Analysis: {symbol}",
                                        "color": 0xFF4444,  # 赤色
                                        "timestamp": datetime.now().isoformat(),
                                        "fields": [
                                            {"name": "Symbol", "value": symbol, "inline": True},
                                            {"name": "Timeframe", "value": timeframe, "inline": True},
                                            {"name": "Strategy", "value": config, "inline": True},
                                            {"name": "Exit Stage", "value": result.exit_stage.value if result.exit_stage else 'unknown', "inline": True},
                                            {"name": "Exit Reason", "value": result.exit_reason.value if result.exit_reason else 'unknown', "inline": True},
                                            {"name": "Execution ID", "value": f"`{execution_id}`", "inline": False},
                                            {"name": "Detailed Message", "value": detailed_msg[:1000], "inline": False},
                                            {"name": "User Message", "value": user_msg[:1000], "inline": False}
                                        ],
                                        "footer": {"text": "Long Trader - Early Exit Analysis"}
                                    }
                                    
                                    # 改善提案を追加
                                    if suggestions:
                                        embed["fields"].append({
                                            "name": "💡 Suggestions",
                                            "value": "\n".join([f"• {s}" for s in suggestions[:5]])[:1000],
                                            "inline": False
                                        })
                                    
                                    # Discord APIに送信
                                    payload = {
                                        "embeds": [embed],
                                        "username": "Long Trader Bot"
                                    }
                                    
                                    # 最大3回のリトライ（ProcessPoolExecutor環境では軽量化）
                                    for attempt in range(3):
                                        try:
                                            response = requests.post(webhook_url, json=payload, timeout=10)
                                            if response.status_code == 200:
                                                logger.info(f"✅ Discord通知送信成功: {symbol} Early Exit")
                                                break
                                            elif response.status_code == 429:  # Rate limit
                                                retry_after = int(response.headers.get('Retry-After', 1))
                                                logger.warning(f"Discord rate limit, retrying after {retry_after}s")
                                                time.sleep(retry_after)
                                            else:
                                                logger.warning(f"Discord API error: {response.status_code}")
                                                break
                                        except Exception as e:
                                            if attempt == 2:  # 最後の試行
                                                logger.error(f"❌ Discord送信失敗: {e}")
                                                break
                                            wait_time = 2 ** attempt
                                            logger.warning(f"Discord送信失敗 (attempt {attempt + 1}/3): {e}, retrying in {wait_time}s")
                                            time.sleep(wait_time)
                                else:
                                    logger.warning("⚠️ DISCORD_WEBHOOK_URL not set, skipping notification")
                                    
                            except Exception as discord_error:
                                logger.error(f"❌ Discord通知システムエラー: {discord_error}")
                                import traceback
                                logger.error(f"   スタックトレース: {traceback.format_exc()}")
                            
                            # 🔧 ProcessPoolExecutor環境用: AnalysisResult詳細を一時ファイルに出力
                            try:
                                import tempfile
                                import json
                                analysis_log = {
                                    'timestamp': datetime.now().isoformat(),
                                    'execution_id': execution_id,
                                    'symbol': symbol,
                                    'timeframe': timeframe,
                                    'strategy': config,
                                    'detailed_msg': detailed_msg,
                                    'user_msg': user_msg,
                                    'suggestions': suggestions,
                                    'early_exit': True,
                                    'stage': result.exit_stage.value if result.exit_stage else 'unknown',
                                    'reason': result.exit_reason.value if result.exit_reason else 'unknown'
                                }
                                
                                log_file = f"/tmp/analysis_log_{execution_id}_{symbol}_{timeframe}_{config}.json"
                                with open(log_file, 'w', encoding='utf-8') as f:
                                    json.dump(analysis_log, f, ensure_ascii=False, indent=2)
                                
                                # 親プロセス確認用
                                print(f"📝 子プロセス詳細ログ出力: {log_file}", flush=True)
                            except Exception as log_error:
                                logger.warning(f"一時ファイルログ出力エラー: {log_error}")
                            
                            continue
                        elif result.completed and result.recommendation:
                            # 成功時のログも出力
                            success_msg = result.get_detailed_log_message()
                            logger.info(f"✅ {success_msg}")
                            
                            # ProcessPoolExecutor環境での確実な出力確保
                            sys.stdout.flush()
                            sys.stderr.flush()
                            for handler in logger.handlers:
                                if hasattr(handler, 'flush'):
                                    handler.flush()
                            
                            # AnalysisResultから辞書形式に変換してそのまま使用
                            result = result.recommendation
                        else:
                            # 不完全な結果はスキップ
                            logger.warning(f"⚠️ 不完全なAnalysisResult: {symbol} {timeframe}")
                            continue
                    
                    # 🔍 analyze_symbolの結果を詳細ログ出力（デバッグ用）
                    if total_evaluations <= 3:  # 最初の3回のみ詳細ログ
                        logger.error(f"🔍 analyze_symbol結果詳細 #{total_evaluations} ({symbol} {timeframe}):")
                        if result:
                            if isinstance(result, dict):
                                for key, value in result.items():
                                    logger.error(f"   {key}: {value} (型: {type(value)})")
                            else:
                                logger.error(f"   結果: {result} (型: {type(result)})")
                        else:
                            logger.error(f"   結果: None または空")
                    
                    # Early Exit対応: Noneまたは無効な結果の場合はスキップ
                    if not result:
                        if total_evaluations <= 3:
                            logger.info(f"⏭️ Early Exit #{total_evaluations}: サポレジレベル不足により評価時点をスキップ")
                        continue
                    
                    if 'current_price' not in result:
                        if total_evaluations <= 3:
                            logger.error(f"🚨 analyze_symbol結果が無効 #{total_evaluations}: current_price missing")
                        continue
                    
                    # エントリー条件の評価
                    try:
                        should_enter = self._evaluate_entry_conditions(result, timeframe)
                    except Exception as e:
                        logger.error(f"🚨 エントリー条件評価でエラー #{total_evaluations}:")
                        logger.error(f"   エラー: {str(e)}")
                        logger.error(f"   分析結果: {result}")
                        continue
                    
                    if not should_enter:
                        # 条件を満たさない場合はスキップ
                        # デバッグログ追加
                        if symbol == 'OP' and total_evaluations <= 5:  # 最初の5回のみログ
                            logger.error(f"🚨 OP条件不満足 #{total_evaluations}: leverage={result.get('leverage')}, confidence={result.get('confidence')}, RR={result.get('risk_reward_ratio')}")
                        continue
                    
                    signals_generated += 1
                    
                    # 進捗表示（条件満足時）
                    if signals_generated % 5 == 0:
                        progress_pct = ((current_time - start_time).total_seconds() / 
                                      (end_time - start_time).total_seconds()) * 100
                        logger.info(f"🎯 {symbol} {timeframe}: シグナル生成 {signals_generated}件 (進捗: {progress_pct:.1f}%)")
                    
                    # レバレッジとTP/SL価格を計算
                    leverage = result.get('leverage', 5.0)
                    confidence = result.get('confidence', 70.0) / 100.0
                    risk_reward = result.get('risk_reward_ratio', 2.0)
                    current_price = result.get('current_price')
                    if current_price is None:
                        logger.error(f"No current_price in analysis result for {symbol}")
                        raise Exception(f"Missing current_price in analysis result for {symbol}")
                    
                    # TP/SL計算機能を使用
                    from engines.stop_loss_take_profit_calculators import (
                        DefaultSLTPCalculator, ConservativeSLTPCalculator, AggressiveSLTPCalculator,
                        TraditionalSLTPCalculator, MLSLTPCalculator
                    )
                    from interfaces.data_types import MarketContext
                    
                    # 条件満足時の実際のタイムスタンプ
                    trade_time = current_time
                    
                    # 戦略に応じたTP/SL計算器を選択
                    if 'Conservative' in config:
                        sltp_calculator = ConservativeSLTPCalculator()
                    elif 'Aggressive_Traditional' in config:
                        sltp_calculator = TraditionalSLTPCalculator()
                    elif 'Aggressive' in config:
                        sltp_calculator = AggressiveSLTPCalculator()
                    elif 'Full_ML' in config:
                        sltp_calculator = MLSLTPCalculator()
                    else:
                        sltp_calculator = DefaultSLTPCalculator()
                    
                    # 模擬的な市場コンテキスト
                    market_context = MarketContext(
                        current_price=current_price,
                        volume_24h=1000000.0,
                        volatility=0.03,
                        trend_direction='BULLISH',
                        market_phase='MARKUP',
                        timestamp=trade_time
                    )
                    
                    # 実際の支持線・抵抗線データを検出（柔軟なアダプター版）
                    try:
                        from engines.support_resistance_adapter import FlexibleSupportResistanceDetector
                        
                        # OHLCVデータを同期的に取得（ボット内のキャッシュされたデータを使用）
                        try:
                            # ボットが既に取得したOHLCVデータを使用
                            if hasattr(bot, '_cached_data') and not bot._cached_data.empty:
                                ohlcv_data = bot._cached_data
                            else:
                                # ボットのfetch_market_dataメソッドを使用（カスタム期間設定を渡す）
                                ohlcv_data = bot._fetch_market_data(symbol, timeframe, custom_period_settings)
                            
                            if ohlcv_data.empty:
                                raise Exception("OHLCVデータが空です")
                                
                        except Exception as ohlcv_error:
                            # OHLCVデータ取得に失敗した場合はフォールバック
                            raise Exception(f"OHLCVデータ取得に失敗: {str(ohlcv_error)}")
                        
                        if len(ohlcv_data) < 50:
                            raise Exception(f"支持線・抵抗線検出に必要なデータが不足しています。{len(ohlcv_data)}本（最低50本必要）")
                        
                        # 実データに基づく最初の有効な評価時刻を決定（初回データ取得時のみ）
                        if total_evaluations == 0:
                            data_start_time = pd.to_datetime(ohlcv_data.index[0], utc=True) if hasattr(ohlcv_data.index[0], 'tz_localize') else pd.to_datetime(ohlcv_data.index[0]).tz_localize('UTC')
                            
                            # 評価間隔の境界に合う最初の時刻を見つける
                            effective_start_time = self._find_first_valid_evaluation_time(data_start_time, evaluation_interval)
                            
                            if effective_start_time > start_time:
                                logger.warning(f"⚠️ データ制約により分析開始時刻を調整: {start_time.strftime('%Y-%m-%d %H:%M')} → {effective_start_time.strftime('%Y-%m-%d %H:%M')}")
                                current_time = effective_start_time  # current_timeも更新
                        
                        # 柔軟な支持線・抵抗線検出器を初期化（設定ファイル対応）
                        detector = FlexibleSupportResistanceDetector(
                            min_touches=2, 
                            tolerance_pct=0.01,
                            use_ml_enhancement=True
                        )
                        
                        # プロバイダー情報をログに表示
                        provider_info = detector.get_provider_info()
                        logger.info(f"       検出プロバイダー: {provider_info['base_provider']}")
                        logger.info(f"       ML強化: {provider_info['ml_provider']}")
                        
                        # 支持線・抵抗線を検出（リアルタイムは全データ使用）
                        logger.info(f"       リアルタイムモード: 全データ使用 {len(ohlcv_data)}本")
                        logger.info(f"       🔍 支持線・抵抗線検出開始 (評価{total_evaluations}回目, 時刻: {current_time.strftime('%Y-%m-%d %H:%M')})")
                        support_levels, resistance_levels = detector.detect_levels(ohlcv_data, current_price)
                        
                        # 検出結果をログに記録（ProcessPoolExecutor対応）
                        if support_levels or resistance_levels:
                            logger.info(f"   ✅ 支持線・抵抗線検出成功: 支持線{len(support_levels)}個, 抵抗線{len(resistance_levels)}個")
                            if support_levels:
                                for i, s in enumerate(support_levels[:3], 1):
                                    logger.info(f"      支持線{i}: ${s.price:.2f} (強度: {s.strength:.2f})")
                            if resistance_levels:
                                for i, r in enumerate(resistance_levels[:3], 1):
                                    logger.info(f"      抵抗線{i}: ${r.price:.2f} (強度: {r.strength:.2f})")
                        else:
                            logger.warning(f"   ⚠️  支持線・抵抗線が検出されませんでした")
                        
                        # 上位レベルのみ選択（パフォーマンス向上）
                        max_levels = 3
                        support_levels = support_levels[:max_levels]
                        resistance_levels = resistance_levels[:max_levels]
                        
                        if not support_levels and not resistance_levels:
                            # 詳細ログを追加
                            data_stats = {
                                "data_points": len(ohlcv_data),
                                "price_range": f"{ohlcv_data['low'].min():.4f} - {ohlcv_data['high'].max():.4f}",
                                "current_price": current_price,
                                "volatility": ((ohlcv_data['high'] - ohlcv_data['low']) / ohlcv_data['close']).mean(),
                                "timeframe": timeframe
                            }
                            logger.error(f"🔍 {symbol} {timeframe} 支持線・抵抗線検出失敗詳細:")
                            logger.error(f"  📊 データ統計: {data_stats}")
                            logger.error(f"  ⚙️ 検出設定: min_touches={provider_info.get('min_touches', 'N/A')}, tolerance={provider_info.get('tolerance_pct', 'N/A')}")
                            logger.error(f"  🤖 ML使用: {provider_info['ml_provider']}")
                            
                            raise Exception(f"有効な支持線・抵抗線が検出されませんでした。市場データが不十分である可能性があります。")
                        
                        logger.info(f"   ✅ 支持線・抵抗線検出成功: 支持線{len(support_levels)}個, 抵抗線{len(resistance_levels)}個")
                        
                        # ML予測スコア情報も表示
                        if provider_info['ml_provider'] != "Disabled":
                            if support_levels:
                                avg_ml_score = np.mean([getattr(s, 'ml_bounce_probability', 0) for s in support_levels])
                                logger.info(f"       支持線ML反発予測: 平均{avg_ml_score:.2f}")
                            if resistance_levels:
                                avg_ml_score = np.mean([getattr(r, 'ml_bounce_probability', 0) for r in resistance_levels])
                                logger.info(f"       抵抗線ML反発予測: 平均{avg_ml_score:.2f}")
                        else:
                            logger.info(f"       ML予測: 無効化")
                        
                        # TP/SL価格を実際のデータで計算
                        sltp_levels = sltp_calculator.calculate_levels(
                            current_price=current_price,
                            leverage=leverage,
                            support_levels=support_levels,
                            resistance_levels=resistance_levels,
                            market_context=market_context
                        )
                        
                    except Exception as e:
                        # 支持線・抵抗線データ不足の場合は、この評価をスキップして次に進む
                        error_msg = f"支持線・抵抗線データの検出・分析に失敗: {str(e)}"
                        logger.warning(f"⚠️ {symbol} {timeframe} {config}: {error_msg} (評価{total_evaluations}をスキップ)")
                        logger.info(f"   📅 スキップした時刻: {current_time.strftime('%Y-%m-%d %H:%M')} → 次の評価に継続")
                        logger.warning(f"Support/resistance analysis failed for {symbol} at {current_time}: {error_msg}")
                        # 次の評価時点に進む（continue先でevaluation_intervalが加算される）
                        continue
                    
                    # 🔧 重要な修正: 実際の市場データから各トレードのエントリー価格を取得
                    # 理由: current_priceが固定値のため、実際の時系列データを使用
                    entry_price = self._get_real_market_price(bot, symbol, timeframe, trade_time)
                    
                    # SL/TP価格をエントリー価格ベースで再計算
                    sltp_levels = sltp_calculator.calculate_levels(
                        current_price=entry_price,  # エントリー価格をベースに計算
                        leverage=leverage,
                        support_levels=support_levels,
                        resistance_levels=resistance_levels,
                        market_context=market_context
                    )
                    
                    # 実際のTP/SL価格（エントリー価格ベース）
                    tp_price = sltp_levels.take_profit_price
                    sl_price = sltp_levels.stop_loss_price
                    
                    # 🔧 ロングポジションの価格論理チェック
                    if sl_price >= entry_price:
                        logger.error(f"重大エラー: 損切り価格({sl_price:.4f})がエントリー価格({entry_price:.4f})以上")
                        continue
                    if tp_price <= entry_price:
                        logger.error(f"重大エラー: 利確価格({tp_price:.4f})がエントリー価格({entry_price:.4f})以下")
                        continue
                    if sl_price >= tp_price:
                        logger.error(f"重大エラー: 損切り価格({sl_price:.4f})が利確価格({tp_price:.4f})以上")
                        continue
                    
                    # 戦略分析では、current_priceもentry_priceと同じにして整合性を保つ
                    # これにより、同じローソク足のopen vs closeによる価格差を防ぐ
                    current_price = entry_price
                    
                    # 価格データ整合性チェック実行
                    price_consistency_result = self.price_validator.validate_price_consistency(
                        analysis_price=current_price,
                        entry_price=entry_price,
                        symbol=symbol,
                        context=f"{timeframe}_{config}_trade_{len(trades)+1}"
                    )
                    
                    if not price_consistency_result.is_consistent:
                        logger.warning(f"価格整合性問題検出: {symbol} {timeframe} - {price_consistency_result.message}")
                        for recommendation in price_consistency_result.recommendations:
                            logger.warning(f"推奨対応: {recommendation}")
                        
                        # 重大な価格不整合の場合は取引をスキップ
                        if price_consistency_result.inconsistency_level.value == 'critical':
                            logger.error(f"重大な価格不整合のためトレードをスキップ: {symbol} at {trade_time}")
                            continue
                    
                    # 統一価格データの作成
                    unified_price_data = self.price_validator.create_unified_price_data(
                        analysis_price=current_price,
                        entry_price=entry_price,
                        symbol=symbol,
                        timeframe=timeframe,
                        market_timestamp=trade_time,
                        data_source=exchange
                    )
                    
                    # TP/SL到達ベースのクローズ判定（実際の市場データを使用）
                    exit_time, exit_price, is_success = self._find_tp_sl_exit(
                        bot, symbol, timeframe, trade_time, entry_price, tp_price, sl_price
                    )
                    
                    # 到達判定が失敗した場合のフォールバック
                    if exit_time is None:
                        # 営業時間内（平日の9:00-21:00 JST = 0:00-12:00 UTC）に調整
                        if trade_time.weekday() >= 5:  # 土日は月曜に移動
                            trade_time += timedelta(days=(7 - trade_time.weekday()))
                        # 時間調整（9:00-21:00 JST = 0:00-12:00 UTC）
                        hour = trade_time.hour
                        if hour < 0:  # JST 9:00 = UTC 0:00
                            trade_time = trade_time.replace(hour=0)
                        elif hour > 12:  # JST 21:00 = UTC 12:00
                            trade_time = trade_time.replace(hour=12)
                        
                        # フォールバック: 時間足に応じた期間後に建値決済
                        exit_minutes = self._get_fallback_exit_minutes(timeframe)
                        exit_time = trade_time + timedelta(minutes=exit_minutes)
                        # フォールバック: 判定不能のため建値決済（プラマイ0）
                        is_success = None  # 判定不能を示す
                        exit_price = entry_price  # 建値決済
                    
                    # PnL計算
                    pnl_pct = (exit_price - entry_price) / entry_price
                    leveraged_pnl = pnl_pct * leverage
                    
                    # バックテスト結果の総合検証
                    backtest_validation = self.price_validator.validate_backtest_result(
                        entry_price=entry_price,
                        stop_loss_price=sl_price,
                        take_profit_price=tp_price,
                        exit_price=exit_price,
                        duration_minutes=int((exit_time - trade_time).total_seconds() / 60),
                        symbol=symbol
                    )
                    
                    if not backtest_validation['is_valid']:
                        logger.warning(f"バックテスト結果異常検知: {symbol} {timeframe}")
                        logger.warning(f"問題: {', '.join(backtest_validation['issues'])}")
                        
                        # 重大な問題がある場合は銘柄追加自体を停止
                        if backtest_validation['severity_level'] == 'critical':
                            logger.error(f"重大なバックテスト異常のため銘柄追加を停止: {symbol} at {trade_time}")
                            logger.error(f"詳細: {', '.join(backtest_validation['issues'])}")
                            raise Exception(f"重大なバックテスト異常検知: {', '.join(backtest_validation['issues'])}")
                    
                    # 日本時間（UTC+9）で表示
                    jst_entry_time = trade_time + timedelta(hours=9)
                    jst_exit_time = exit_time + timedelta(hours=9)
                    
                    trades.append({
                        'entry_time': jst_entry_time.strftime('%Y-%m-%d %H:%M:%S JST'),
                        'exit_time': jst_exit_time.strftime('%Y-%m-%d %H:%M:%S JST'),
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'take_profit_price': tp_price,
                        'stop_loss_price': sl_price,
                        'leverage': leverage,
                        'pnl_pct': leveraged_pnl,
                        'confidence': confidence,
                        'is_success': is_success,
                        'trade_type': 'breakeven' if is_success is None else ('profit' if is_success else 'loss'),
                        'strategy': config,
                        # 価格整合性情報の追加
                        'price_consistency_score': unified_price_data.consistency_score,
                        'price_validation_level': price_consistency_result.inconsistency_level.value,
                        'backtest_validation_severity': backtest_validation['severity_level'],
                        'analysis_price': current_price  # デバッグ用
                    })
                    
                except Exception as e:
                    logger.warning(f"⚠️ 分析エラー (評価{total_evaluations}): {str(e)[:100]}")
                    logger.warning(f"Analysis failed for {symbol} at {current_time}: {e}")
                
                # forループなので自動的に次のインデックスに進む
            
            # 全データ評価完了のログ
            logger.info(f"✅ {symbol} {timeframe} {config}: 全{total_evaluations}本のデータを評価完了")
            
            if not trades:
                print(f"ℹ️ {symbol} {timeframe} {config}: 評価期間中に条件を満たすシグナルが見つかりませんでした")
                return []  # 空のリストを返す（エラーにしない）
            
            evaluation_rate = (signals_generated / total_evaluations * 100) if total_evaluations > 0 else 0
            logger.info(f"✅ {symbol} {timeframe} {config}: 条件ベース分析完了")
            print(f"   📊 総評価数: {total_evaluations}, シグナル生成: {signals_generated}件 ({evaluation_rate:.1f}%)")
            
            # 価格整合性チェック結果のサマリーを表示
            if trades:
                validation_summary = self.price_validator.get_validation_summary(hours=24)
                if validation_summary['total_validations'] > 0:
                    print(f"   🔍 価格整合性チェック: {validation_summary['consistency_rate']:.1f}% 整合性")
                    print(f"   📈 平均価格差異: {validation_summary['avg_difference_pct']:.2f}%")
                    if validation_summary['level_counts'].get('critical', 0) > 0:
                        logger.warning(f"   ⚠️ 重大な価格不整合: {validation_summary['level_counts']['critical']}件")
            
            return trades
            
        except Exception as e:
            logger.error(f"Condition-based analysis failed: {e}")
            raise
    
    def _evaluate_entry_conditions(self, analysis_result, timeframe):
        """
        エントリー条件を評価して、シグナル生成が適切かを判定
        
        Args:
            analysis_result: ハイレバボットからの分析結果
            timeframe: 時間足
            
        Returns:
            bool: エントリー条件を満たしているかどうか
        """
        
        # 基本的な条件チェック
        leverage = analysis_result.get('leverage', 0)
        confidence = analysis_result.get('confidence', 0) / 100.0  # パーセントから比率に変換
        risk_reward = analysis_result.get('risk_reward_ratio', 0)
        current_price = analysis_result.get('current_price', 0)
        
        # 統合設定から条件を取得（戦略も考慮）
        try:
            from config.unified_config_manager import UnifiedConfigManager
            config_manager = UnifiedConfigManager()
            
            # 分析中の戦略を取得（デフォルトはBalanced）
            strategy = analysis_result.get('strategy', 'Balanced')
            
            # 統合設定から条件を取得
            conditions = config_manager.get_entry_conditions(timeframe, strategy)
            
            # フィルターパラメータからエントリー条件をオーバーライド
            import os
            filter_params_env = os.getenv('FILTER_PARAMS')
            if filter_params_env:
                try:
                    import json
                    filter_params = json.loads(filter_params_env)
                    entry_conditions = filter_params.get('entry_conditions', {})
                    
                    if entry_conditions:
                        # WebUIからのパラメータで設定をオーバーライド
                        original_conditions = conditions.copy()
                        if 'min_leverage' in entry_conditions:
                            conditions['min_leverage'] = entry_conditions['min_leverage']
                        if 'min_confidence' in entry_conditions:
                            conditions['min_confidence'] = entry_conditions['min_confidence']
                        if 'min_risk_reward' in entry_conditions:
                            conditions['min_risk_reward'] = entry_conditions['min_risk_reward']
                        
                        logger.info(f"🔧 エントリー条件をWebUIパラメータでオーバーライド:")
                        logger.info(f"   min_leverage: {original_conditions.get('min_leverage')} → {conditions['min_leverage']}")
                        logger.info(f"   min_confidence: {original_conditions.get('min_confidence')} → {conditions['min_confidence']}")
                        logger.info(f"   min_risk_reward: {original_conditions.get('min_risk_reward')} → {conditions['min_risk_reward']}")
                except Exception as e:
                    logger.warning(f"⚠️ フィルターパラメータのエントリー条件解析エラー: {e}")
            
        except Exception as e:
            # 設定読み込み失敗時は銘柄追加を停止
            error_msg = f"エントリー条件設定が読み込めませんでした: {e}"
            print(f"❌ 設定エラー: {error_msg}")
            raise InsufficientConfigurationError(
                message=error_msg,
                error_type="entry_conditions_config_failed",
                missing_config="unified_entry_conditions"
            )
        
        # 🔍 詳細なエラー検証とログ機能
        logger.error(f"🔍 エントリー条件評価開始:")
        logger.error(f"   分析結果の生データ:")
        logger.error(f"     leverage: {leverage} (型: {type(leverage)})")
        logger.error(f"     confidence: {confidence} (型: {type(confidence)}) [元の値: {analysis_result.get('confidence')}]")
        logger.error(f"     risk_reward_ratio: {risk_reward} (型: {type(risk_reward)})")
        logger.error(f"     current_price: {current_price} (型: {type(current_price)})")
        
        # None値チェックと詳細エラー報告
        validation_errors = []
        
        if leverage is None:
            validation_errors.append("leverage is None - 分析結果からレバレッジ値が取得できませんでした")
        if confidence is None:
            validation_errors.append("confidence is None - 分析結果から信頼度が取得できませんでした")
        if risk_reward is None:
            validation_errors.append("risk_reward_ratio is None - 分析結果からリスクリワード比が取得できませんでした")
        if current_price is None:
            validation_errors.append("current_price is None - 分析結果から現在価格が取得できませんでした")
        
        # None値がある場合は詳細エラー情報を出力
        if validation_errors:
            logger.error(f"🚨 分析結果にNone値が含まれています:")
            for error in validation_errors:
                logger.error(f"   ❌ {error}")
            logger.error(f"   📊 分析結果の全内容:")
            for key, value in analysis_result.items():
                logger.error(f"     {key}: {value} (型: {type(value)})")
            
            # None値エラーとして例外を発生
            raise ValueError(f"分析結果にNone値が含まれています: {', '.join(validation_errors)}")
        
        # 条件評価
        conditions_met = []
        
        try:
            # 1. レバレッジ条件
            leverage_ok = leverage >= conditions['min_leverage']
            conditions_met.append(('leverage', leverage_ok, f"{leverage:.1f}x >= {conditions['min_leverage']}x"))
            
            # 2. 信頼度条件
            confidence_ok = confidence >= conditions['min_confidence']
            conditions_met.append(('confidence', confidence_ok, f"{confidence:.1%} >= {conditions['min_confidence']:.1%}"))
            
            # 3. リスクリワード条件
            risk_reward_ok = risk_reward >= conditions['min_risk_reward']
            conditions_met.append(('risk_reward', risk_reward_ok, f"{risk_reward:.1f} >= {conditions['min_risk_reward']}"))
            
            # 4. 価格の有効性
            price_ok = current_price > 0
            conditions_met.append(('price', price_ok, f"price={current_price}"))
            
        except Exception as e:
            logger.error(f"🚨 エントリー条件評価中にエラーが発生:")
            logger.error(f"   エラー内容: {str(e)}")
            logger.error(f"   エラータイプ: {type(e).__name__}")
            logger.error(f"   値の詳細:")
            logger.error(f"     leverage: {leverage} (型: {type(leverage)})")
            logger.error(f"     confidence: {confidence} (型: {type(confidence)})")
            logger.error(f"     risk_reward: {risk_reward} (型: {type(risk_reward)})")
            logger.error(f"     current_price: {current_price} (型: {type(current_price)})")
            raise ValueError(f"エントリー条件評価エラー: {str(e)}") from e
        
        # 全ての条件が満たされているかをチェック
        all_conditions_met = all(condition[1] for condition in conditions_met)
        
        # 条件評価結果の詳細ログ
        logger.error(f"🎯 エントリー条件評価結果:")
        for condition_name, result, description in conditions_met:
            status = "✅ OK" if result else "❌ NG"
            logger.error(f"   {condition_name}: {status} - {description}")
        logger.error(f"   最終判定: {'✅ 通過' if all_conditions_met else '❌ 除外'}")
        
        # デバッグログ: OPの条件評価詳細
        if 'OP' in str(analysis_result.get('symbol', '')):
            logger.error(f"🔍 OP条件評価詳細:")
            logger.error(f"   レバレッジ: {leverage} (必要: {conditions['min_leverage']}) → {leverage_ok}")
            logger.error(f"   信頼度: {confidence:.1%} (必要: {conditions['min_confidence']:.1%}) → {confidence_ok}")
            logger.error(f"   RR比: {risk_reward} (必要: {conditions['min_risk_reward']}) → {risk_reward_ok}")
            logger.error(f"   結果: {all_conditions_met}")
        
        # デバッグ用ログ（条件満足時のみ詳細表示）
        if all_conditions_met:
            print(f"   ✅ エントリー条件満足: L={leverage:.1f}x, C={confidence:.1%}, RR={risk_reward:.1f}")
        
        return all_conditions_met
    
    def _create_strategy_from_config(self, config: str):
        """設定から戦略オブジェクトを作成"""
        class ConfigBasedStrategy:
            def __init__(self, config_name):
                self.name = config_name
                
                # 基本設定
                self.min_volume_threshold = 500000
                self.max_spread_threshold = 0.05
                self.min_liquidity_score = 0.5
                
                # 戦略別の設定
                if 'Conservative' in config_name:
                    self.min_ml_confidence = 0.8
                    self.min_support_strength = 0.7
                    self.min_resistance_strength = 0.7
                    self.max_volatility = 0.1
                elif 'Aggressive' in config_name:
                    self.min_ml_confidence = 0.6
                    self.min_support_strength = 0.5
                    self.min_resistance_strength = 0.5
                    self.max_volatility = 0.2
                else:
                    self.min_ml_confidence = 0.7
                    self.min_support_strength = 0.6
                    self.min_resistance_strength = 0.6
                    self.max_volatility = 0.15
                
                # 距離条件
                self.min_distance_from_support = 0.5
                self.max_distance_from_support = 5.0
                self.min_distance_from_resistance = 1.0
                self.max_distance_from_resistance = 8.0
                
                # ボラティリティ条件
                self.min_volatility = 0.01
                self.max_atr_ratio = 0.05
                
                # ML条件
                self.required_ml_signal = "BUY"
                self.min_ml_signal_strength = 0.6
        
        return ConfigBasedStrategy(config)
    
    # Stage 9フィルタリングシステム削除済み (2025年6月29日)
    # 理由: "軽量事前チェック"と謳いながら重い計算を実行し、2.6倍の性能劣化
    # 詳細: README.md参照
    
    # Stage 9フィルタリング用モックデータ削除済み (2025年6月29日)
    
    # Stage 9フィルタリングフレームワーク初期化メソッド削除済み (2025年6月29日)
    
    # Stage 9フィルタリング用モック戦略作成メソッド削除済み (2025年6月29日)
    
    def _analysis_exists(self, analysis_id):
        """分析が既に存在するかチェック"""
        # ハッシュIDの場合はDBから直接検索
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # まずハッシュIDで検索を試行
            if len(analysis_id) == 32:  # MD5ハッシュの場合
                cursor.execute(
                    'SELECT COUNT(*) FROM analyses WHERE symbol || "_" || timeframe || "_" || config = ?',
                    (analysis_id,)
                )
            else:
                # 従来の形式の場合
                try:
                    symbol, timeframe, config = analysis_id.split('_', 2)
                    cursor.execute(
                        'SELECT COUNT(*) FROM analyses WHERE symbol=? AND timeframe=? AND config=?',
                        (symbol, timeframe, config)
                    )
                except ValueError:
                    return False
            return cursor.fetchone()[0] > 0
    
    # TODO: ランダムトレード生成は品質問題のためコメントアウト (2024-06-18)
    # 現在は使用されていないが、将来的に実データベースの方法に置き換える必要あり
    # def _generate_sample_trades(self, symbol, timeframe, config, num_trades=100):
    #     """サンプルトレードデータ生成（軽量版）"""
    #     np.random.seed(hash(f"{symbol}_{timeframe}_{config}") % 2**32)
    #     
    #     # 基本性能設定
    #     base_performance = {
    #         'Conservative_ML': {'sharpe': 1.2, 'win_rate': 0.65},
    #         'Aggressive_Traditional': {'sharpe': 1.8, 'win_rate': 0.55},
    #         'Full_ML': {'sharpe': 2.1, 'win_rate': 0.62}
    #     }.get(config, {'sharpe': 1.5, 'win_rate': 0.58})
    #     
    #     trades = []
    #     cumulative_return = 0
    #     
    #     for i in range(num_trades):
    #         # ランダムトレード生成
    #         is_win = np.random.random() < base_performance['win_rate']
    #         
    #         if is_win:
    #             pnl_pct = np.random.exponential(0.03)
    #         else:
    #             pnl_pct = -np.random.exponential(0.015)
    #         
    #         leverage = np.random.uniform(2.0, 8.0)
    #         leveraged_pnl = pnl_pct * leverage
    #         cumulative_return += leveraged_pnl
    #         
    #         trades.append({
    #             'trade_id': i,
    #             'pnl_pct': leveraged_pnl,
    #             'leverage': leverage,
    #             'is_win': is_win,
    #             'cumulative_return': cumulative_return
    #         })
    #     
    #     return pd.DataFrame(trades)
    
    # 暫定実装: エラーを返す
    def _generate_sample_trades(self, symbol, timeframe, config, num_trades=100):
        """サンプルトレードデータ生成（無効化済み）"""
        raise NotImplementedError(
            "ランダムトレード生成は品質問題のため無効化されています。"
            "実際の市場データを使用してください。"
        )
    
    def _calculate_metrics(self, trades_data):
        """メトリクス計算"""
        # リストの場合はDataFrameに変換
        if isinstance(trades_data, list):
            if not trades_data:
                return {
                    'total_trades': 0,
                    'total_return': 0,
                    'win_rate': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'avg_leverage': 0
                }
            
            # 累積リターンとis_winを計算
            cumulative_return = 0
            for trade in trades_data:
                cumulative_return += trade['pnl_pct']
                trade['cumulative_return'] = cumulative_return
                
                # is_win計算の改良（建値決済対応）
                is_success = trade.get('is_success')
                if is_success is None:
                    # 建値決済（判定不能）の場合は勝敗判定対象外
                    trade['is_win'] = None
                else:
                    # 通常の勝敗判定
                    trade['is_win'] = is_success if is_success is not None else (trade['pnl_pct'] > 0)
            
            trades_df = pd.DataFrame(trades_data)
        else:
            trades_df = trades_data
        
        if len(trades_df) == 0:
            return {
                'total_trades': 0,
                'total_return': 0,
                'win_rate': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'avg_leverage': 0
            }
        
        total_return = trades_df['cumulative_return'].iloc[-1] if len(trades_df) > 0 else 0
        
        # 勝率計算の改良（建値決済を除外）
        if len(trades_df) > 0:
            valid_trades = trades_df['is_win'].notna()  # None以外（勝敗判定可能）
            win_rate = trades_df[valid_trades]['is_win'].mean() if valid_trades.sum() > 0 else 0
        else:
            win_rate = 0
        
        # Sharpe比の簡易計算
        returns = trades_df['pnl_pct'].values
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # 最大ドローダウン
        cum_returns = trades_df['cumulative_return'].values
        peak = np.maximum.accumulate(cum_returns)
        drawdown = (cum_returns - peak) / peak
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        # 価格整合性メトリクスの計算
        price_consistency_metrics = {}
        if 'price_consistency_score' in trades_df.columns:
            price_consistency_metrics = {
                'avg_price_consistency': trades_df['price_consistency_score'].mean(),
                'critical_price_issues': len(trades_df[trades_df['price_validation_level'] == 'critical']),
                'critical_backtest_issues': len(trades_df[trades_df['backtest_validation_severity'] == 'critical'])
            }
        else:
            price_consistency_metrics = {
                'avg_price_consistency': 1.0,
                'critical_price_issues': 0,
                'critical_backtest_issues': 0
            }
        
        # 建値決済統計の計算
        breakeven_stats = {}
        if len(trades_df) > 0:
            breakeven_count = trades_df['is_win'].isna().sum()
            total_decisive_trades = len(trades_df) - breakeven_count
            breakeven_stats = {
                'breakeven_trades': breakeven_count,
                'decisive_trades': total_decisive_trades,
                'breakeven_rate': (breakeven_count / len(trades_df)) if len(trades_df) > 0 else 0
            }
        else:
            breakeven_stats = {
                'breakeven_trades': 0,
                'decisive_trades': 0,
                'breakeven_rate': 0
            }
        
        base_metrics = {
            'total_trades': len(trades_df),
            'total_return': total_return,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_leverage': trades_df['leverage'].mean() if len(trades_df) > 0 else 0
        }
        
        # 建値決済統計を追加
        base_metrics.update(breakeven_stats)
        
        # 価格整合性メトリクスを結合
        base_metrics.update(price_consistency_metrics)
        return base_metrics
    
    def _save_compressed_data(self, analysis_id, trades_df):
        """データを圧縮して保存"""
        compressed_path = self.compressed_dir / f"{analysis_id}.pkl.gz"
        
        with gzip.open(compressed_path, 'wb') as f:
            pickle.dump(trades_df, f)
        
        return str(compressed_path)
    
    def _should_generate_chart(self, metrics):
        """チャート生成が必要かどうか判定（上位パフォーマーのみ）"""
        return metrics['sharpe_ratio'] > 1.5  # Sharpe > 1.5のみチャート生成
    
    def _generate_lightweight_chart(self, analysis_id, trades_df, metrics):
        """軽量版チャート生成"""
        # 実装は省略（必要に応じて実装）
        chart_path = self.charts_dir / f"{analysis_id}_chart.html"
        
        # 簡易HTML作成
        html_content = f"""
        <html>
        <head><title>{analysis_id} Analysis</title></head>
        <body>
        <h1>{analysis_id}</h1>
        <p>Sharpe Ratio: {metrics['sharpe_ratio']:.2f}</p>
        <p>Win Rate: {metrics['win_rate']:.1%}</p>
        <p>Total Return: {metrics['total_return']:.1%}</p>
        </body>
        </html>
        """
        
        with open(chart_path, 'w') as f:
            f.write(html_content)
        
        return str(chart_path)
    
    def _save_to_database(self, symbol, timeframe, config, metrics, chart_path, compressed_path, execution_id=None):
        """データベースに保存（execution_id対応 + task_status更新 + 支持線・抵抗線データ保存）"""
        logger.info(f"💾 DB保存開始: {symbol} {timeframe} {config}")
        logger.info(f"  🗃️ 保存先DB: {self.db_path.absolute()}")
        logger.info(f"  🔑 execution_id: {execution_id or os.environ.get('CURRENT_EXECUTION_ID', 'None')}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # execution_idを環境変数または引数から取得
            if not execution_id:
                execution_id = os.environ.get('CURRENT_EXECUTION_ID')
            
            try:
                # 🔥 重要: INSERTからUPDATEに変更（pre-taskレコード更新）
                cursor.execute('''
                    UPDATE analyses SET
                        total_trades=?, win_rate=?, total_return=?, 
                        sharpe_ratio=?, max_drawdown=?, avg_leverage=?, 
                        chart_path=?, compressed_path=?, 
                        status='completed', task_status='completed', task_completed_at=?
                    WHERE symbol=? AND timeframe=? AND config=? AND execution_id=?
                ''', (
                    metrics['total_trades'], metrics['win_rate'], metrics['total_return'],
                    metrics['sharpe_ratio'], metrics['max_drawdown'], metrics['avg_leverage'],
                    chart_path, compressed_path, 
                    datetime.now(timezone.utc).isoformat(),
                    symbol, timeframe, config, execution_id
                ))
                
                updated_rows = cursor.rowcount
                analysis_id = None
                
                if updated_rows == 0:
                    # Pre-taskが存在しない場合は従来通りINSERT
                    logger.warning(f"⚠️ Pre-taskレコードなし - INSERT実行: {symbol} {timeframe} {config}")
                    cursor.execute('''
                        INSERT INTO analyses 
                        (symbol, timeframe, config, total_trades, win_rate, total_return, 
                         sharpe_ratio, max_drawdown, avg_leverage, chart_path, compressed_path, status, 
                         task_status, task_completed_at, execution_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', 'completed', ?, ?)
                    ''', (
                        symbol, timeframe, config,
                        metrics['total_trades'], metrics['win_rate'], metrics['total_return'],
                        metrics['sharpe_ratio'], metrics['max_drawdown'], metrics['avg_leverage'],
                        chart_path, compressed_path, 
                        datetime.now(timezone.utc).isoformat(),
                        execution_id
                    ))
                    analysis_id = cursor.lastrowid
                else:
                    # 既存レコードのIDを取得
                    cursor.execute('''
                        SELECT id FROM analyses 
                        WHERE symbol=? AND timeframe=? AND config=? AND execution_id=?
                    ''', (symbol, timeframe, config, execution_id))
                    result = cursor.fetchone()
                    if result:
                        analysis_id = result[0]
                
                # 支持線・抵抗線データの保存
                if analysis_id and 'leverage_details' in metrics and metrics['leverage_details']:
                    logger.info(f"📊 支持線・抵抗線データ保存開始: {len(metrics['leverage_details'])}件")
                    
                    for i, detail in enumerate(metrics['leverage_details']):
                        cursor.execute('''
                            INSERT INTO leverage_calculation_details 
                            (analysis_id, trade_number, support_distance_pct, support_constraint_leverage,
                             risk_reward_ratio, risk_reward_constraint_leverage, confidence_pct, 
                             confidence_constraint_leverage, btc_correlation, btc_constraint_leverage,
                             volatility_pct, volatility_constraint_leverage, trend_strength,
                             trend_multiplier, min_constraint_leverage, safety_margin_pct, final_leverage)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            analysis_id, i + 1,
                            detail.get('support_distance_pct'),
                            detail.get('support_constraint_leverage'),
                            detail.get('risk_reward_ratio'),
                            detail.get('risk_reward_constraint_leverage'),
                            detail.get('confidence_pct'),
                            detail.get('confidence_constraint_leverage'),
                            detail.get('btc_correlation'),
                            detail.get('btc_constraint_leverage'),
                            detail.get('volatility_pct'),
                            detail.get('volatility_constraint_leverage'),
                            detail.get('trend_strength'),
                            detail.get('trend_multiplier'),
                            detail.get('min_constraint_leverage'),
                            detail.get('safety_margin_pct'),
                            detail.get('final_leverage')
                        ))
                    
                    logger.info(f"✅ 支持線・抵抗線データ保存完了: {len(metrics['leverage_details'])}件")
                
                conn.commit()
                logger.info(f"✅ DB保存成功: {symbol} {timeframe} {config} ({'UPDATE' if updated_rows > 0 else 'INSERT'})")
                
            except Exception as e:
                logger.error(f"❌ DB保存エラー: {symbol} {timeframe} {config}")
                logger.error(f"  🗃️ DB path: {self.db_path.absolute()}")
                logger.error(f"  📝 エラー詳細: {str(e)}")
                raise
    
    def query_analyses(self, filters=None, order_by='sharpe_ratio', limit=100):
        """分析結果をクエリ"""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM analyses WHERE status='completed'"
            params = []
            
            if filters:
                if 'symbol' in filters:
                    if isinstance(filters['symbol'], list):
                        query += " AND symbol IN ({})".format(','.join(['?' for _ in filters['symbol']]))
                        params.extend(filters['symbol'])
                    else:
                        query += " AND symbol = ?"
                        params.append(filters['symbol'])
                
                if 'timeframe' in filters:
                    if isinstance(filters['timeframe'], list):
                        query += " AND timeframe IN ({})".format(','.join(['?' for _ in filters['timeframe']]))
                        params.extend(filters['timeframe'])
                    else:
                        query += " AND timeframe = ?"
                        params.append(filters['timeframe'])
                
                if 'config' in filters:
                    if isinstance(filters['config'], list):
                        query += " AND config IN ({})".format(','.join(['?' for _ in filters['config']]))
                        params.extend(filters['config'])
                    else:
                        query += " AND config = ?"
                        params.append(filters['config'])
                
                if 'min_sharpe' in filters:
                    query += " AND sharpe_ratio >= ?"
                    params.append(filters['min_sharpe'])
            
            query += f" ORDER BY {order_by} DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            # Create a list of dictionaries instead of pandas DataFrame
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            return result
    
    def get_statistics(self):
        """システム統計を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 基本統計
            cursor.execute("SELECT COUNT(*) as total, status FROM analyses GROUP BY status")
            status_counts = cursor.fetchall()
            
            # 性能統計
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_analyses,
                    AVG(sharpe_ratio) as avg_sharpe,
                    MAX(sharpe_ratio) as max_sharpe,
                    AVG(total_return) as avg_return,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    COUNT(DISTINCT config) as unique_configs
                FROM analyses WHERE status='completed'
            """)
            perf_stats = cursor.fetchone()
            
            return {
                'status_counts': dict(status_counts),
                'performance': {
                    'total_analyses': perf_stats[0],
                    'avg_sharpe': perf_stats[1],
                    'max_sharpe': perf_stats[2],
                    'avg_return': perf_stats[3],
                    'unique_symbols': perf_stats[4],
                    'unique_configs': perf_stats[5]
                }
            }
    
    def load_compressed_trades(self, symbol, timeframe, config):
        """圧縮されたトレードデータを読み込み"""
        analysis_id = f"{symbol}_{timeframe}_{config}"
        
        # データベースからパスを取得
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT compressed_path FROM analyses WHERE symbol=? AND timeframe=? AND config=?",
                (symbol, timeframe, config)
            )
            result = cursor.fetchone()
            
            if not result or not result[0]:
                logger.warning(f"圧縮データが見つかりません: {analysis_id}")
                return None
            
            compressed_path = result[0]
        
        # 圧縮データを読み込み
        try:
            with gzip.open(compressed_path, 'rb') as f:
                trades_df = pickle.load(f)
            logger.info(f"トレードデータ読み込み完了: {analysis_id} ({len(trades_df)}トレード)")
            return trades_df
        except Exception as e:
            logger.error(f"データ読み込みエラー {analysis_id}: {e}")
            return None
    
    def load_multiple_trades(self, criteria=None):
        """複数の圧縮トレードデータを一括読み込み"""
        # クエリ条件に基づいて分析を取得
        analyses_df = self.query_analyses(filters=criteria)
        
        all_trades = {}
        for _, analysis in analyses_df.iterrows():
            trades_df = self.load_compressed_trades(
                analysis['symbol'], 
                analysis['timeframe'], 
                analysis['config']
            )
            if trades_df is not None:
                key = f"{analysis['symbol']}_{analysis['timeframe']}_{analysis['config']}"
                all_trades[key] = trades_df
        
        logger.info(f"読み込み完了: {len(all_trades)}件のトレードデータ")
        return all_trades
    
    def export_to_csv(self, symbol, timeframe, config, output_path=None):
        """圧縮データをCSVにエクスポート"""
        trades_df = self.load_compressed_trades(symbol, timeframe, config)
        
        if trades_df is None:
            return False
        
        if output_path is None:
            output_path = f"{symbol}_{timeframe}_{config}_trades_export.csv"
        
        trades_df.to_csv(output_path, index=False)
        logger.info(f"CSVエクスポート完了: {output_path}")
        return True
    
    def test_discord_notification(self, test_type="early_exit"):
        """Discord通知テスト機能"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        import os
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        
        if not webhook_url:
            logger.error("❌ DISCORD_WEBHOOK_URL環境変数が設定されていません")
            return False
        
        logger.info(f"🔔 Discord通知テスト開始: {test_type}")
        
        if test_type == "early_exit":
            # Early Exit模擬通知
            from engines.analysis_result import AnalysisResult, AnalysisStage, ExitReason
            
            result = AnalysisResult(
                symbol="TEST",
                timeframe="1h", 
                strategy="Conservative_ML-1h",
                execution_id="test_discord_001"
            )
            result.mark_early_exit(
                stage=AnalysisStage.SUPPORT_RESISTANCE,
                reason=ExitReason.NO_SUPPORT_RESISTANCE,
                error_message="Discord通知テスト用Early Exit"
            )
            
            return self._send_discord_notification_sync(
                symbol="TEST",
                timeframe="1h",
                strategy="Conservative_ML-1h", 
                execution_id="test_discord_001",
                result=result,
                webhook_url=webhook_url
            )
        
        elif test_type == "simple":
            # シンプルテスト通知
            payload = {
                "content": "🧪 **Discord通知テスト**\n\n"
                          "✅ ProcessPoolExecutor環境からのDiscord通知が正常に動作しています。\n"
                          f"⏰ テスト時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            import requests
            try:
                response = requests.post(webhook_url, json=payload, timeout=10)
                if response.status_code == 204:
                    logger.info("✅ Discord通知テスト成功")
                    return True
                else:
                    logger.error(f"❌ Discord通知失敗: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"❌ Discord通知エラー: {e}")
                return False
        
        return False

    def get_analysis_details(self, symbol, timeframe, config):
        """分析の詳細情報を取得（データベース + トレードデータ）"""
        # データベースから基本情報取得
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM analyses 
                WHERE symbol=? AND timeframe=? AND config=?
            """
            analysis_info = pd.read_sql_query(query, conn, params=[symbol, timeframe, config])
        
        if analysis_info.empty:
            return None
        
        # トレードデータも読み込み
        trades_df = self.load_compressed_trades(symbol, timeframe, config)
        
        return {
            'info': analysis_info.iloc[0].to_dict(),
            'trades': trades_df
        }
    
    def _handle_discord_notification_for_result(self, result, symbol, timeframe, config, execution_id):
        """ProcessPoolExecutor専用Discord通知処理"""
        try:
            from engines.analysis_result import AnalysisResult
            
            # AnalysisResultのEarly Exit確認
            if isinstance(result, AnalysisResult) and result.early_exit:
                logger.info(f"🎯 Discord通知処理開始: {symbol} {timeframe} Early Exit")
                
                # 環境変数再読み込み（ProcessPoolExecutor対応）
                try:
                    from dotenv import load_dotenv
                    load_dotenv()
                except ImportError:
                    pass
                
                webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
                
                if webhook_url:
                    # Discord通知送信
                    self._send_discord_notification_sync(
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy=config,
                        execution_id=execution_id,
                        result=result,
                        webhook_url=webhook_url
                    )
                else:
                    logger.warning("⚠️ DISCORD_WEBHOOK_URL not set in ProcessPoolExecutor")
            else:
                logger.debug(f"Discord通知スキップ: Early Exit無し ({symbol} {timeframe})")
                
        except Exception as e:
            logger.error(f"❌ Discord通知処理エラー: {e}")
    
    def _send_discord_notification_sync(self, symbol, timeframe, strategy, execution_id, result, webhook_url):
        """同期Discord通知送信（ProcessPoolExecutor専用）"""
        try:
            import requests
            
            # メッセージ作成
            detailed_msg = result.get_detailed_log_message()
            user_msg = result.get_user_friendly_message()
            suggestions = result.get_suggestions()
            
            # Embed作成
            embed = {
                "title": f"🚨 Early Exit Analysis: {symbol}",
                "color": 0xFF4444,
                "timestamp": datetime.now().isoformat(),
                "fields": [
                    {"name": "Symbol", "value": symbol, "inline": True},
                    {"name": "Timeframe", "value": timeframe, "inline": True},
                    {"name": "Strategy", "value": strategy, "inline": True},
                    {"name": "Exit Stage", "value": result.exit_stage.value if result.exit_stage else 'unknown', "inline": True},
                    {"name": "Exit Reason", "value": result.exit_reason.value if result.exit_reason else 'unknown', "inline": True},
                    {"name": "Execution ID", "value": f"`{execution_id}`", "inline": False},
                    {"name": "Detailed Message", "value": detailed_msg[:1000], "inline": False},
                    {"name": "User Message", "value": user_msg[:1000], "inline": False}
                ],
                "footer": {"text": "Long Trader - ProcessPoolExecutor Early Exit"}
            }
            
            if suggestions:
                embed["fields"].append({
                    "name": "💡 Suggestions",
                    "value": "\n".join([f"• {s}" for s in suggestions[:5]])[:1000],
                    "inline": False
                })
            
            payload = {
                "embeds": [embed],
                "username": "Long Trader Bot"
            }
            
            # 送信実行
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                logger.info(f"✅ Discord通知送信成功: {symbol} Early Exit")
                return True
            else:
                logger.warning(f"Discord通知失敗: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Discord通知送信エラー: {e}")
            return False
    
    async def send_discord_early_exit_notification(self, symbol: str, timeframe: str, strategy: str, execution_id: str, exit_stage: str, exit_reason: str, detailed_msg: str, user_msg: str, suggestions: List[str]):
        """Discord webhook通知: 子プロセスのEarly Exit詳細送信"""
        try:
            # Discord webhook URL (環境変数から取得)
            webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
            if not webhook_url:
                self.logger.warning("DISCORD_WEBHOOK_URL not set, skipping notification")
                return
            
            # embed作成
            embed = {
                "title": f"🚨 Early Exit Analysis: {symbol}",
                "color": 0xFF4444,  # 赤色
                "timestamp": datetime.now().isoformat(),
                "fields": [
                    {"name": "Symbol", "value": symbol, "inline": True},
                    {"name": "Timeframe", "value": timeframe, "inline": True},
                    {"name": "Strategy", "value": strategy, "inline": True},
                    {"name": "Exit Stage", "value": exit_stage, "inline": True},
                    {"name": "Exit Reason", "value": exit_reason, "inline": True},
                    {"name": "Execution ID", "value": f"`{execution_id}`", "inline": False},
                    {"name": "Detailed Message", "value": detailed_msg[:1000], "inline": False},
                    {"name": "User Message", "value": user_msg[:1000], "inline": False}
                ],
                "footer": {"text": "Long Trader - Early Exit Analysis"}
            }
            
            # 改善提案を追加
            if suggestions:
                embed["fields"].append({
                    "name": "💡 Suggestions",
                    "value": "\n".join([f"• {s}" for s in suggestions[:5]])[:1000],
                    "inline": False
                })
            
            # Discord APIに送信
            payload = {
                "embeds": [embed],
                "username": "Long Trader Bot"
            }
            
            # 最大8回のリトライ（指数バックオフ）
            for attempt in range(8):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(webhook_url, json=payload) as response:
                            if response.status == 200:
                                self.logger.info(f"✅ Discord通知送信成功: {symbol} Early Exit")
                                return
                            elif response.status == 429:  # Rate limit
                                retry_after = int(response.headers.get('Retry-After', 1))
                                self.logger.warning(f"Discord rate limit, retrying after {retry_after}s")
                                await asyncio.sleep(retry_after)
                            else:
                                self.logger.warning(f"Discord API error: {response.status}")
                                break
                                
                except Exception as e:
                    if attempt == 7:  # 最後の試行
                        raise e
                    
                    # 指数バックオフ (1s, 2s, 4s, 8s, 16s, 32s, 64s, 128s)
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Discord送信失敗 (attempt {attempt + 1}/8): {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    
        except Exception as e:
            self.logger.error(f"Discord通知送信エラー: {e}")
    
    def cleanup_low_performers(self, min_sharpe=0.5):
        """低パフォーマンス分析のクリーンアップ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 削除対象を取得
            cursor.execute(
                "SELECT chart_path, compressed_path FROM analyses WHERE sharpe_ratio < ?",
                (min_sharpe,)
            )
            to_delete = cursor.fetchall()
            
            # ファイル削除
            deleted_files = 0
            for chart_path, data_path in to_delete:
                for file_path in [chart_path, data_path]:
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_files += 1
            
            # データベースからも削除
            cursor.execute("DELETE FROM analyses WHERE sharpe_ratio < ?", (min_sharpe,))
            deleted_records = cursor.rowcount
            conn.commit()
            
            logger.info(f"クリーンアップ完了: {deleted_records}レコード, {deleted_files}ファイル削除")
            return deleted_records, deleted_files
    
    def _get_real_market_price(self, bot, symbol, timeframe, trade_time):
        """
        実際の市場データから指定時刻の価格を取得
        トレード時刻が属するローソク足のopen価格を使用（最も現実的）
        
        Args:
            bot: HighLeverageBotOrchestrator インスタンス
            symbol: 銘柄シンボル  
            timeframe: 時間足
            trade_time: トレード時刻
        
        Returns:
            float: 実際の市場価格（該当ローソク足のopen価格）
        """
        try:
            # ボットから実際の市場データを取得
            if hasattr(bot, '_cached_data') and not bot._cached_data.empty:
                market_data = bot._cached_data
            else:
                market_data = bot._fetch_market_data(symbol, timeframe)
            
            if market_data.empty:
                raise Exception(f"市場データが空です: {symbol}")
            
            # データの timestamp カラムを確認・作成
            if 'timestamp' not in market_data.columns:
                if market_data.index.name == 'timestamp' or pd.api.types.is_datetime64_any_dtype(market_data.index):
                    # インデックスがタイムスタンプの場合
                    market_data = market_data.reset_index()
                    if 'index' in market_data.columns:
                        market_data = market_data.rename(columns={'index': 'timestamp'})
                else:
                    # インデックスがタイムスタンプでない場合は作成
                    market_data['timestamp'] = pd.to_datetime(market_data.index, utc=True)
            
            # timestampカラムをdatetime型に確実に変換
            market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], utc=True)
            
            # trade_timeをUTCに変換
            if trade_time.tzinfo is None:
                target_time = trade_time
            else:
                target_time = trade_time.astimezone(timezone.utc)
            
            # trade_timeが属するローソク足の開始時刻を計算
            candle_start_time = self._get_candle_start_time(target_time, timeframe)
            
            # 該当するローソク足を特定（タイムゾーン考慮）
            # market_dataのタイムスタンプをUTCに統一
            if market_data['timestamp'].dt.tz is None:
                market_data['timestamp'] = market_data['timestamp'].dt.tz_localize('UTC')
            else:
                market_data['timestamp'] = market_data['timestamp'].dt.tz_convert('UTC')
            
            # candle_start_timeもUTCに統一
            if candle_start_time.tzinfo is None:
                candle_start_time = candle_start_time.replace(tzinfo=timezone.utc)
            else:
                candle_start_time = candle_start_time.astimezone(timezone.utc)
            
            # より柔軟なマッチング（段階的許容範囲拡大）
            time_tolerance = timedelta(minutes=1)
            target_candles = market_data[
                abs(market_data['timestamp'] - candle_start_time) <= time_tolerance
            ]
            
            if target_candles.empty:
                # 段階的に許容範囲を拡大（最大30分まで）
                for tolerance_minutes in [5, 15, 30]:
                    time_tolerance = timedelta(minutes=tolerance_minutes)
                    target_candles = market_data[
                        abs(market_data['timestamp'] - candle_start_time) <= time_tolerance
                    ]
                    if not target_candles.empty:
                        time_diff = abs(target_candles.iloc[0]['timestamp'] - candle_start_time)
                        logger.warning(
                            f"⚠️ {symbol} {timeframe}: {tolerance_minutes}分許容範囲で最寄りローソク足使用 "
                            f"(時差: {time_diff})"
                        )
                        break
                
                if target_candles.empty:
                    # それでも見つからない場合は最寄りのローソク足を使用
                    time_diffs = abs(market_data['timestamp'] - candle_start_time)
                    min_diff_idx = time_diffs.idxmin()
                    min_diff = time_diffs[min_diff_idx]
                    
                    if min_diff <= timedelta(hours=2):  # 2時間以内なら使用
                        target_candles = market_data.iloc[[min_diff_idx]]
                        logger.warning(
                            f"⚠️ {symbol} {timeframe}: 最寄りローソク足使用 (時差: {min_diff})"
                        )
                    else:
                        # デバッグ情報を追加
                        available_times = market_data['timestamp'].head(10).tolist()
                        raise Exception(
                            f"該当ローソク足が見つかりません: {symbol} {timeframe} "
                            f"trade_time={target_time}, candle_start={candle_start_time}. "
                            f"利用可能な最初の10件: {available_times}. "
                            f"最小時差: {min_diff} (2時間を超過)"
                        )
            
            # 最も近いローソク足を選択
            target_candle = target_candles.iloc[0]
            
            # そのローソク足のopen価格を返す（最も現実的なエントリー価格）
            open_price = float(target_candle['open'])
            
            return open_price
            
        except Exception as e:
            # フォールバックは使用せず、エラーで戦略分析を終了
            raise Exception(f"実際の市場価格取得に失敗: {symbol} - {str(e)}")
    
    def _get_candle_start_time(self, trade_time, timeframe):
        """
        トレード時刻が属するローソク足の開始時刻を計算
        
        Args:
            trade_time: トレード時刻
            timeframe: 時間足（例: '15m', '1h', '4h'）
        
        Returns:
            datetime: ローソク足の開始時刻
        """
        # 時間足を分単位に変換
        timeframe_minutes = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, 
            '30m': 30, '1h': 60, '4h': 240, '1d': 1440
        }
        
        if timeframe not in timeframe_minutes:
            raise Exception(f"サポートされていない時間足: {timeframe}")
        
        minutes_interval = timeframe_minutes[timeframe]
        
        # trade_timeを該当するローソク足の開始時刻に丸める
        if timeframe == '1d':
            # 日足の場合は00:00:00に丸める
            candle_start = trade_time.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # 分足・時間足の場合
            total_minutes = trade_time.hour * 60 + trade_time.minute
            candle_minutes = (total_minutes // minutes_interval) * minutes_interval
            
            candle_hour = candle_minutes // 60
            candle_minute = candle_minutes % 60
            
            candle_start = trade_time.replace(
                hour=candle_hour, 
                minute=candle_minute, 
                second=0, 
                microsecond=0
            )
        
        return candle_start
    
    def _find_first_valid_evaluation_time(self, data_start_time, evaluation_interval):
        """
        実際のOHLCVデータ開始時刻に基づいて、評価間隔の境界に合う最初の有効な評価時刻を見つける
        
        Args:
            data_start_time: 実際のOHLCVデータの最初のタイムスタンプ
            evaluation_interval: 評価間隔（timedelta）
            
        Returns:
            datetime: 最初の有効な評価時刻
        """
        # 評価間隔を分単位に変換
        interval_minutes = int(evaluation_interval.total_seconds() / 60)
        
        # データ開始時刻を評価間隔の境界に合わせる
        # 例: データ開始が06:30、評価間隔が60分の場合 → 07:00を返す
        
        # 現在の時刻から評価間隔の境界時刻を計算
        current = data_start_time
        
        # 時間・分を評価間隔の境界に合わせる
        if interval_minutes >= 60:
            # 1時間以上の間隔の場合、時間境界に合わせる
            hours_interval = interval_minutes // 60
            aligned_hour = (current.hour // hours_interval + 1) * hours_interval
            if aligned_hour >= 24:
                current = current.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                current = current.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
        else:
            # 1時間未満の間隔の場合、分境界に合わせる
            total_minutes = current.hour * 60 + current.minute
            aligned_minutes = ((total_minutes // interval_minutes) + 1) * interval_minutes
            
            if aligned_minutes >= 24 * 60:
                current = current.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                aligned_hour = aligned_minutes // 60
                aligned_minute = aligned_minutes % 60
                current = current.replace(hour=aligned_hour, minute=aligned_minute, second=0, microsecond=0)
        
        return current
    
    def _find_tp_sl_exit(self, bot, symbol, timeframe, entry_time, entry_price, tp_price, sl_price):
        """
        TP/SL到達ベースのクローズ判定
        
        Args:
            bot: HighLeverageBotOrchestrator インスタンス
            symbol: 銘柄シンボル
            timeframe: 時間足
            entry_time: エントリー時刻
            entry_price: エントリー価格
            tp_price: 利確価格
            sl_price: 損切り価格
            
        Returns:
            tuple: (exit_time, exit_price, is_success)
        """
        try:
            # ボットから市場データを取得
            if hasattr(bot, '_cached_data') and not bot._cached_data.empty:
                market_data = bot._cached_data
            else:
                market_data = bot._fetch_market_data(symbol, timeframe)
            
            if market_data.empty:
                return None, None, None
            
            # タイムスタンプカラムの準備
            if 'timestamp' not in market_data.columns:
                if market_data.index.name == 'timestamp' or pd.api.types.is_datetime64_any_dtype(market_data.index):
                    market_data = market_data.reset_index()
                    if 'index' in market_data.columns:
                        market_data = market_data.rename(columns={'index': 'timestamp'})
                else:
                    market_data['timestamp'] = pd.to_datetime(market_data.index, utc=True)
            
            # タイムスタンプを統一
            market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], utc=True)
            if market_data['timestamp'].dt.tz is None:
                market_data['timestamp'] = market_data['timestamp'].dt.tz_localize('UTC')
            else:
                market_data['timestamp'] = market_data['timestamp'].dt.tz_convert('UTC')
            
            # entry_timeをUTCに変換
            if entry_time.tzinfo is None:
                entry_time_utc = entry_time.replace(tzinfo=timezone.utc)
            else:
                entry_time_utc = entry_time.astimezone(timezone.utc)
            
            # エントリー後のデータを取得
            after_entry_data = market_data[market_data['timestamp'] > entry_time_utc].copy()
            
            if after_entry_data.empty:
                return None, None, None
            
            # 各ローソク足でTP/SL到達をチェック
            for _, candle in after_entry_data.iterrows():
                # ロングポジションを想定
                candle_high = float(candle['high'])
                candle_low = float(candle['low'])
                
                # 利確ライン到達チェック
                if candle_high >= tp_price:
                    exit_time = candle['timestamp']
                    exit_price = tp_price
                    is_success = True
                    return exit_time, exit_price, is_success
                
                # 損切りライン到達チェック
                if candle_low <= sl_price:
                    exit_time = candle['timestamp']
                    exit_price = sl_price
                    is_success = False
                    return exit_time, exit_price, is_success
            
            # 評価期間内に到達しなかった場合
            return None, None, None
            
        except Exception as e:
            logger.warning(f"TP/SL到達判定エラー: {symbol} - {e}")
            return None, None, None
    
    def _get_fallback_exit_minutes(self, timeframe):
        """時間足に応じたフォールバック退出時間を取得"""
        fallback_minutes = {
            '1m': 15,    # 15分後
            '3m': 30,    # 30分後
            '5m': 45,    # 45分後
            '15m': 60,   # 1時間後
            '30m': 90,   # 1.5時間後
            '1h': 120    # 2時間後
        }
        return fallback_minutes.get(timeframe, 60)

def generate_large_scale_configs(symbols_count=20, timeframes=4, configs=10):
    """大規模設定を生成"""
    symbols = [f"TOKEN{i:03d}" for i in range(1, symbols_count + 1)]
    timeframes_list = ['1m', '3m', '5m', '15m', '30m', '1h'][:timeframes]
    configs_list = [f"Config_{i:02d}" for i in range(1, configs + 1)]
    
    batch_configs = []
    for symbol in symbols:
        for timeframe in timeframes_list:
            for config in configs_list:
                batch_configs.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'config': config
                })
    
    return batch_configs

def main():
    """大規模分析のデモ"""
    system = ScalableAnalysisSystem()
    
    # 1000パターンの設定生成
    configs = generate_large_scale_configs(symbols_count=10, timeframes=4, configs=25)
    print(f"生成された設定数: {len(configs)}")
    
    # バッチ分析実行
    processed = system.generate_batch_analysis(configs, max_workers=4)
    print(f"処理完了: {processed}パターン")
    
    # 統計表示
    stats = system.get_statistics()
    print("\n統計:")
    print(f"  総分析数: {stats['performance']['total_analyses']}")
    print(f"  平均Sharpe: {stats['performance']['avg_sharpe']:.2f}")
    print(f"  最高Sharpe: {stats['performance']['max_sharpe']:.2f}")
    print(f"  ユニーク銘柄数: {stats['performance']['unique_symbols']}")
    
    # 上位結果表示
    top_results = system.query_analyses(
        filters={'min_sharpe': 1.5},
        order_by='sharpe_ratio',
        limit=10
    )
    print(f"\n上位10結果:")
    print(top_results[['symbol', 'timeframe', 'config', 'sharpe_ratio', 'total_return']].to_string())

# ScalableAnalysisSystem クラスにメソッドを追加
def add_get_timeframe_config_method():
    """ScalableAnalysisSystemに設定取得メソッドを追加"""
    import types
    
    def get_timeframe_config(self, timeframe: str):
        """時間足設定を取得（外部設定ファイル対応）"""
        try:
            from config.timeframe_config_manager import TimeframeConfigManager
            config_manager = TimeframeConfigManager()
            return config_manager.get_timeframe_config(timeframe)
        except:
            # フォールバック設定
            default_configs = {
                '1m': {'max_evaluations': 100},
                '3m': {'max_evaluations': 80},
                '5m': {'max_evaluations': 120},
                '15m': {'max_evaluations': 100},
                '30m': {'max_evaluations': 80},
                '1h': {'max_evaluations': 100}
            }
            base_config = {
                'data_days': 90,
                'evaluation_interval_minutes': 240,
                'max_evaluations': 50,
                'min_leverage': 3.0,
                'min_confidence': 0.5,
                'min_risk_reward': 2.0
            }
            base_config.update(default_configs.get(timeframe, {}))
            return base_config
    
    # クラスにメソッドを動的に追加
    ScalableAnalysisSystem.get_timeframe_config = get_timeframe_config
    
    # 🔧 古い進捗トラッキングシステムは新しいFileBasedProgressTrackerに統一済み
    # def _init_file_based_progress_tracker(self, execution_id: str, symbol: str):
    #     """旧: ファイルベースprogress_tracker初期化（FileBasedProgressTrackerに統合済み）"""
    #     pass
    
    # def _update_file_based_progress_tracker(self, execution_id: str, completed_phase: str, next_phase: str):
    #     """旧: ファイルベースprogress_tracker更新（FileBasedProgressTrackerに統合済み）"""
    #     pass

# メソッド追加を実行
add_get_timeframe_config_method()

if __name__ == "__main__":
    main()