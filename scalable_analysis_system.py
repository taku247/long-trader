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

# 価格データ整合性チェックシステムのインポート
from engines.price_consistency_validator import PriceConsistencyValidator, UnifiedPriceData

# 進捗ロガーのインポート
from progress_logger import SymbolProgressLogger

# エラー例外のインポート
from engines.leverage_decision_engine import InsufficientConfigurationError

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
        
        # DB使用ログ機能追加
        caller_frame = inspect.currentframe().f_back
        caller_file = caller_frame.f_code.co_filename if caller_frame else "unknown"
        caller_function = caller_frame.f_code.co_name if caller_frame else "unknown"
        
        logger.info(f"🔍 ScalableAnalysisSystem初期化:")
        logger.info(f"  📁 base_dir: {self.base_dir.absolute()}")
        logger.info(f"  🗃️ DB path: {self.db_path.absolute()}")
        logger.info(f"  📍 呼び出し元: {os.path.basename(caller_file)}:{caller_function}")
        logger.info(f"  🕐 現在ディレクトリ: {os.getcwd()}")
        
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
    
    def init_database(self):
        """SQLiteデータベースを初期化"""
        logger.info(f"🗃️ データベース初期化: {self.db_path.absolute()}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 既存テーブル確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"  📋 既存テーブル: {existing_tables}")
            
            # analysesテーブルが存在する場合、カラム構造を確認
            if 'analyses' in existing_tables:
                cursor.execute("PRAGMA table_info(analyses);")
                columns = [row[1] for row in cursor.fetchall()]
                logger.info(f"  📊 analysesテーブルカラム: {columns}")
                
                # execution_idカラムの存在確認
                if 'execution_id' in columns:
                    logger.info("  ✅ execution_idカラム: 存在")
                else:
                    logger.warning("  ⚠️ execution_idカラム: 不在")
                    # execution_idカラムを追加
                    cursor.execute('ALTER TABLE analyses ADD COLUMN execution_id TEXT')
                    logger.info("  ✅ execution_idカラムを追加しました")
                
                if 'task_status' in columns:
                    logger.info("  ✅ task_statusカラム: 存在")
                else:
                    logger.warning("  ⚠️ task_statusカラム: 不在")
                    # 不足カラムを追加
                    cursor.execute('ALTER TABLE analyses ADD COLUMN task_status TEXT DEFAULT "pending"')
                    cursor.execute('ALTER TABLE analyses ADD COLUMN task_started_at TIMESTAMP')
                    cursor.execute('ALTER TABLE analyses ADD COLUMN task_completed_at TIMESTAMP')
                    cursor.execute('ALTER TABLE analyses ADD COLUMN error_message TEXT')
                    logger.info("  ✅ task_statusカラム等を追加しました")
            
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
    
    def generate_batch_analysis(self, batch_configs, max_workers=None, symbol=None, execution_id=None, skip_pretask_creation=False):
        """
        バッチで大量の分析を並列生成
        
        Args:
            batch_configs: [{'symbol': 'BTC', 'timeframe': '1h', 'config': 'ML'}, ...]
            max_workers: 並列数（デフォルト: CPU数）
            symbol: 銘柄名（進捗表示用）
            execution_id: 実行ID（進捗表示用）
            skip_pretask_creation: Pre-task作成をスキップするかどうか
        """
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
    
    def _process_chunk(self, configs_chunk, chunk_id, execution_id=None):
        """チャンクを処理（プロセス内で実行）"""
        import time
        import random
        import os
        
        # execution_idを環境変数に設定（子プロセス用）
        if execution_id:
            os.environ['CURRENT_EXECUTION_ID'] = execution_id
            logger.info(f"チャンク {chunk_id}: execution_id {execution_id} を環境変数に設定")
        
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
                
                result, metrics = self._generate_single_analysis(
                    config['symbol'], 
                    config['timeframe'], 
                    strategy
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
    
    def _generate_single_analysis(self, symbol, timeframe, config):
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
            trades_data = self._generate_real_analysis(symbol, timeframe, config)
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
        execution_id = os.environ.get('CURRENT_EXECUTION_ID')
        self._save_to_database(symbol, timeframe, config, metrics, chart_path, compressed_path, execution_id)
        
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
    
    def _generate_real_analysis(self, symbol, timeframe, config, evaluation_period_days=90):
        """条件ベースのハイレバレッジ分析 - 市場条件を満たした場合のみシグナル生成"""
        try:
            # 本格的な戦略分析のため、実際のAPIデータを使用
            from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
            
            # 取引所設定を取得
            exchange = self._get_exchange_from_config(config)
            
            print(f"🎯 実データによる戦略分析を開始: {symbol} {timeframe} {config} ({exchange})")
            print("   ⏳ データ取得とML分析のため、処理に数分かかる場合があります...")
            
            # 修正: ハードコード値問題解決のため、毎回新しいボットを作成（キャッシュ無効化）
            # 理由: キャッシュされたデータの再利用により、全トレードで同じエントリー価格が使用される問題を解決
            bot = HighLeverageBotOrchestrator(use_default_plugins=True, exchange=exchange)
            print(f"🔄 {symbol} 新規ボットでデータ取得中... (価格多様性確保のため)")
            
            # 複数回分析を実行してトレードデータを生成（完全ログ抑制）
            trades = []
            import sys
            import os
            import contextlib
            import time
            
            # 進捗表示用
            print(f"🔄 {symbol} {timeframe} {config}: 条件ベース分析開始")
            
            # 完全にログを抑制するコンテキストマネージャー
            @contextlib.contextmanager
            def suppress_all_output():
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
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=evaluation_period_days)
            
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
            
            # 条件ベースの分析実行
            current_time = start_time
            total_evaluations = 0
            signals_generated = 0
            
            # 時間足設定から最大評価回数を取得
            max_evaluations = tf_config.get('max_evaluations', 100)  # フォールバック値
            
            print(f"🔍 条件ベース分析: {start_time.strftime('%Y-%m-%d')} から {end_time.strftime('%Y-%m-%d')}")
            print(f"📊 評価間隔: {evaluation_interval} ({timeframe}足最適化)")
            print(f"🛡️ 最大評価回数: {max_evaluations}回")
            
            max_signals = max_evaluations // 2  # 評価回数の半分まで（例：20評価で最大10シグナル）
            
            while (current_time <= end_time and 
                   total_evaluations < max_evaluations and 
                   signals_generated < max_signals):
                total_evaluations += 1
                try:
                    # 出力抑制で市場条件の評価（バックテストフラグ付き）
                    with suppress_all_output():
                        result = bot.analyze_symbol(symbol, timeframe, config, is_backtest=True, target_timestamp=current_time)
                    
                    if not result or 'current_price' not in result:
                        current_time += evaluation_interval
                        continue
                    
                    # エントリー条件の評価
                    should_enter = self._evaluate_entry_conditions(result, timeframe)
                    
                    if not should_enter:
                        # 条件を満たさない場合はスキップ
                        # デバッグログ追加
                        if symbol == 'OP' and total_evaluations <= 5:  # 最初の5回のみログ
                            logger.error(f"🚨 OP条件不満足 #{total_evaluations}: leverage={result.get('leverage')}, confidence={result.get('confidence')}, RR={result.get('risk_reward_ratio')}")
                        current_time += evaluation_interval
                        continue
                    
                    signals_generated += 1
                    
                    # 進捗表示（条件満足時）
                    if signals_generated % 5 == 0:
                        progress_pct = ((current_time - start_time).total_seconds() / 
                                      (end_time - start_time).total_seconds()) * 100
                        print(f"🎯 {symbol} {timeframe}: シグナル生成 {signals_generated}件 (進捗: {progress_pct:.1f}%)")
                    
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
                                # ボットのfetch_market_dataメソッドを使用
                                ohlcv_data = bot._fetch_market_data(symbol, timeframe)
                            
                            if ohlcv_data.empty:
                                raise Exception("OHLCVデータが空です")
                                
                        except Exception as ohlcv_error:
                            # OHLCVデータ取得に失敗した場合はフォールバック
                            raise Exception(f"OHLCVデータ取得に失敗: {str(ohlcv_error)}")
                        
                        if len(ohlcv_data) < 50:
                            raise Exception(f"支持線・抵抗線検出に必要なデータが不足しています。{len(ohlcv_data)}本（最低50本必要）")
                        
                        # 柔軟な支持線・抵抗線検出器を初期化（設定ファイル対応）
                        detector = FlexibleSupportResistanceDetector(
                            min_touches=2, 
                            tolerance_pct=0.01,
                            use_ml_enhancement=True
                        )
                        
                        # プロバイダー情報をログに表示
                        provider_info = detector.get_provider_info()
                        print(f"       検出プロバイダー: {provider_info['base_provider']}")
                        print(f"       ML強化: {provider_info['ml_provider']}")
                        
                        # 支持線・抵抗線を検出
                        support_levels, resistance_levels = detector.detect_levels(ohlcv_data, current_price)
                        
                        # 上位レベルのみ選択（パフォーマンス向上）
                        max_levels = 3
                        support_levels = support_levels[:max_levels]
                        resistance_levels = resistance_levels[:max_levels]
                        
                        if not support_levels and not resistance_levels:
                            raise Exception(f"有効な支持線・抵抗線が検出されませんでした。市場データが不十分である可能性があります。")
                        
                        print(f"   ✅ 支持線・抵抗線検出成功: 支持線{len(support_levels)}個, 抵抗線{len(resistance_levels)}個")
                        
                        # ML予測スコア情報も表示
                        if provider_info['ml_provider'] != "Disabled":
                            if support_levels:
                                avg_ml_score = np.mean([getattr(s, 'ml_bounce_probability', 0) for s in support_levels])
                                print(f"       支持線ML反発予測: 平均{avg_ml_score:.2f}")
                            if resistance_levels:
                                avg_ml_score = np.mean([getattr(r, 'ml_bounce_probability', 0) for r in resistance_levels])
                                print(f"       抵抗線ML反発予測: 平均{avg_ml_score:.2f}")
                        else:
                            print(f"       ML予測: 無効化")
                        
                        # TP/SL価格を実際のデータで計算
                        sltp_levels = sltp_calculator.calculate_levels(
                            current_price=current_price,
                            leverage=leverage,
                            support_levels=support_levels,
                            resistance_levels=resistance_levels,
                            market_context=market_context
                        )
                        
                    except Exception as e:
                        # 支持線・抵抗線データ不足により分析を停止
                        error_msg = f"支持線・抵抗線データの検出・分析に失敗: {str(e)}"
                        print(f"❌ {symbol} {timeframe} {config}: {error_msg}")
                        logger.error(f"Support/resistance analysis error for {symbol}: {error_msg}")
                        raise Exception(f"戦略分析失敗 - {error_msg}")
                    
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
                    print(f"⚠️ 分析エラー (評価{total_evaluations}): {str(e)[:100]}")
                    logger.warning(f"Analysis failed for {symbol} at {current_time}: {e}")
                
                # 次の評価時点に進む
                current_time += evaluation_interval
            
            # 評価回数制限に達した場合の警告
            if total_evaluations >= max_evaluations:
                print(f"⚠️ {symbol} {timeframe} {config}: 最大評価回数({max_evaluations})に達しました")
            
            if not trades:
                print(f"ℹ️ {symbol} {timeframe} {config}: 評価期間中に条件を満たすシグナルが見つかりませんでした")
                return []  # 空のリストを返す（エラーにしない）
            
            evaluation_rate = (signals_generated / total_evaluations * 100) if total_evaluations > 0 else 0
            print(f"✅ {symbol} {timeframe} {config}: 条件ベース分析完了")
            print(f"   📊 総評価数: {total_evaluations}, シグナル生成: {signals_generated}件 ({evaluation_rate:.1f}%)")
            
            # 価格整合性チェック結果のサマリーを表示
            if trades:
                validation_summary = self.price_validator.get_validation_summary(hours=24)
                if validation_summary['total_validations'] > 0:
                    print(f"   🔍 価格整合性チェック: {validation_summary['consistency_rate']:.1f}% 整合性")
                    print(f"   📈 平均価格差異: {validation_summary['avg_difference_pct']:.2f}%")
                    if validation_summary['level_counts'].get('critical', 0) > 0:
                        print(f"   ⚠️ 重大な価格不整合: {validation_summary['level_counts']['critical']}件")
            
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
            
        except Exception as e:
            # 設定読み込み失敗時は銘柄追加を停止
            error_msg = f"エントリー条件設定が読み込めませんでした: {e}"
            print(f"❌ 設定エラー: {error_msg}")
            raise InsufficientConfigurationError(
                message=error_msg,
                error_type="entry_conditions_config_failed",
                missing_config="unified_entry_conditions"
            )
        
        # 条件評価
        conditions_met = []
        
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
        
        # 全ての条件が満たされているかをチェック
        all_conditions_met = all(condition[1] for condition in conditions_met)
        
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
        """データベースに保存（execution_id対応 + task_status更新）"""
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
            
            # より柔軟なマッチング（数分の誤差を許容）
            time_tolerance = timedelta(minutes=1)
            target_candles = market_data[
                abs(market_data['timestamp'] - candle_start_time) <= time_tolerance
            ]
            
            if target_candles.empty:
                # デバッグ情報を追加
                available_times = market_data['timestamp'].head(10).tolist()
                raise Exception(
                    f"該当ローソク足が見つかりません: {symbol} {timeframe} "
                    f"trade_time={target_time}, candle_start={candle_start_time}. "
                    f"利用可能な最初の10件: {available_times}. "
                    f"実際の値のみ使用のため、フォールバックは使用しません。"
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

# メソッド追加を実行
add_get_timeframe_config_method()

if __name__ == "__main__":
    main()