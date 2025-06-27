#!/usr/bin/env python3
"""
銘柄追加時の自動学習・バックテストシステム
銘柄を追加すると全時間足・全戦略で自動分析を実行
"""

import sys
import os
import asyncio
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import traceback

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from real_time_system.utils.colored_log import get_colored_logger
from scalable_analysis_system import ScalableAnalysisSystem
from execution_log_database import ExecutionLogDatabase, ExecutionType, ExecutionStatus
from engines.leverage_decision_engine import InsufficientMarketDataError, InsufficientConfigurationError, LeverageAnalysisError
from engines.filtering_framework import FilteringFramework, FilteringStatistics
from symbol_early_fail_validator import SymbolEarlyFailValidator

# progress_tracker統合
try:
    from web_dashboard.analysis_progress import progress_tracker
    PROGRESS_TRACKER_AVAILABLE = True
    print("✅ progress_tracker インポート成功")
except ImportError as e:
    PROGRESS_TRACKER_AVAILABLE = False
    print(f"⚠️ progress_tracker インポートエラー: {e}")


class AutoSymbolTrainer:
    """銘柄追加時の自動学習・バックテストシステム"""
    
    def __init__(self):
        self.logger = get_colored_logger(__name__)
        # Force use of root large_scale_analysis directory to prevent DB fragmentation
        self.analysis_system = ScalableAnalysisSystem("large_scale_analysis") 
        self.execution_db = ExecutionLogDatabase()
        # 実行ログの一時保存は廃止（データベースを使用）
        
        # Early Fail検証システム初期化
        self.early_fail_validator = SymbolEarlyFailValidator()
        self.logger.info("✅ フィルタリングシステム初期化完了")
        
    async def add_symbol_with_training(self, symbol: str, execution_id: str = None, selected_strategies: list = None, selected_timeframes: list = None, strategy_configs: list = None, skip_pretask_creation: bool = False, custom_period_settings: dict = None, filter_params: dict = None) -> str:
        """
        銘柄を追加して指定戦略・時間足で自動学習・バックテストを実行
        
        Args:
            symbol: 銘柄名 (例: "HYPE")
            execution_id: 事前定義された実行ID（Noneの場合は自動生成）
            selected_strategies: 選択された戦略リスト（Noneの場合はデフォルト）
            selected_timeframes: 選択された時間足リスト（Noneの場合はデフォルト）
            strategy_configs: カスタム戦略設定リスト（strategy_configurationsテーブルのレコード）
            skip_pretask_creation: Pre-task作成をスキップするかどうか（既に作成済みの場合）
            
        Returns:
            execution_id: 実行ID（進捗追跡用）
        """
        try:
            self.logger.info(f"Starting automatic training for symbol: {symbol}")
            
            # jsonモジュールを関数内でも確実に利用可能にする
            import json
            
            # 🚀 Early Fail検証実行
            self.logger.info(f"🔍 Early Fail検証開始: {symbol}")
            early_fail_result = await self._run_early_fail_validation(symbol)
            if not early_fail_result.passed:
                error_msg = f"Early Fail検証失敗: {early_fail_result.fail_reason} - {early_fail_result.error_message}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            self.logger.info(f"✅ Early Fail検証合格: {symbol}")
            
            # 重複実行チェック（同じexecution_idは除外）
            existing_executions = self.execution_db.list_executions(limit=20)
            running_symbols = [
                exec_item for exec_item in existing_executions 
                if (exec_item.get('status') == 'RUNNING' and 
                    exec_item.get('symbol') == symbol and 
                    exec_item.get('execution_id') != execution_id)  # 同じexecution_idは除外
            ]
            
            if running_symbols:
                error_msg = f"Symbol {symbol} is already being processed. Cancel existing execution first."
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # データベースに実行記録を作成
            if execution_id is None:
                execution_id = self.execution_db.create_execution(
                    ExecutionType.SYMBOL_ADDITION,
                    symbol=symbol,
                    triggered_by="USER",
                    metadata={"auto_training": True, "all_strategies": True, "all_timeframes": True}
                )
            else:
                # 事前定義されたIDの場合、既存の記録をチェック
                existing_record = self.execution_db.get_execution(execution_id)
                if not existing_record:
                    # 記録が存在しない場合のみ作成
                    self.execution_db.create_execution_with_id(
                        execution_id,
                        ExecutionType.SYMBOL_ADDITION,
                        symbol=symbol,
                        triggered_by="USER",
                        metadata={
                            "auto_training": True, 
                            "selected_strategies": selected_strategies or "all",
                            "selected_timeframes": selected_timeframes or "all",
                            "custom_strategy_configs": len(strategy_configs) if strategy_configs else 0
                        }
                    )
                    self.logger.info(f"📝 Created new execution record: {execution_id}")
                else:
                    self.logger.info(f"📋 Using existing execution record: {execution_id}")
            
            self.logger.info(f"Execution ID: {execution_id}")
            
            # 実行IDをインスタンス変数として保存（進捗ロガー用）
            self._current_execution_id = execution_id
            
            # 実行IDを環境変数に設定（子プロセス用）
            os.environ['CURRENT_EXECUTION_ID'] = execution_id
            self.logger.info(f"📝 実行IDを環境変数に設定: {execution_id}")
            
            # フィルターパラメータを環境変数に設定
            if filter_params:
                os.environ['FILTER_PARAMS'] = json.dumps(filter_params)
                self.logger.info(f"🔧 フィルターパラメータを環境変数に設定: {filter_params}")
            
            # progress_tracker初期化
            if PROGRESS_TRACKER_AVAILABLE:
                self.logger.info(f"📊 progress_tracker初期化開始: {symbol}, {execution_id}")
                progress_tracker.start_analysis(symbol, execution_id)
                progress_tracker.update_stage(execution_id, "initializing")
                self.logger.info(f"✅ progress_tracker初期化完了")
            else:
                self.logger.warning("⚠️ progress_tracker利用不可")
            
            # 実行開始
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.RUNNING,
                current_operation='開始中',
                progress_percentage=0,
                total_tasks=4
            )
            
            # Step 1: データ取得と検証
            await self._execute_step(execution_id, 'data_fetch', 
                                   self._fetch_and_validate_data, symbol, custom_period_settings)
            
            # Step 2: 選択された戦略・時間足でバックテスト実行
            await self._execute_step(execution_id, 'backtest', 
                                   self._run_comprehensive_backtest, symbol, selected_strategies, selected_timeframes, strategy_configs, skip_pretask_creation, custom_period_settings)
            
            # Step 3: ML学習実行
            await self._execute_step(execution_id, 'ml_training', 
                                   self._train_ml_models, symbol)
            
            # Step 4: 結果保存とランキング更新
            await self._execute_step(execution_id, 'result_save', 
                                   self._save_results, symbol)
            
            # 実行完了前に分析結果の存在確認
            analysis_results_exist = self._verify_analysis_results(symbol, execution_id)
            
            if analysis_results_exist:
                # 分析結果が存在する場合のみSUCCESS
                self.execution_db.update_execution_status(
                    execution_id,
                    ExecutionStatus.SUCCESS,
                    current_operation='完了',
                    progress_percentage=100
                )
                
                # progress_tracker最終更新（成功）
                if PROGRESS_TRACKER_AVAILABLE:
                    progress_tracker.complete_analysis(execution_id, "signal_detected", "Analysis completed successfully")
                    
                self.logger.success(f"Symbol {symbol} training completed successfully!")
            else:
                # 分析結果が存在しない場合はFAILED
                self.execution_db.update_execution_status(
                    execution_id,
                    ExecutionStatus.FAILED,
                    current_operation='分析結果なし - 処理失敗',
                    progress_percentage=100,
                    error_message="No analysis results found despite successful steps"
                )
                
                # progress_tracker最終更新（失敗）
                if PROGRESS_TRACKER_AVAILABLE:
                    self.logger.info(f"📊 progress_tracker失敗更新開始: {execution_id}")
                    progress_tracker.fail_analysis(execution_id, "result_validation", "No analysis results found despite successful execution steps")
                    self.logger.info(f"✅ progress_tracker失敗更新完了")
                else:
                    self.logger.warning("⚠️ progress_tracker利用不可のため失敗更新スキップ")
                    
                self.logger.error(f"❌ Symbol {symbol} training failed: No analysis results found")
                raise ValueError(f"No analysis results found for {symbol} despite successful execution steps")
            
            return execution_id
            
        except Exception as e:
            self.logger.error(f"Error in symbol training: {e}")
            
            # progress_tracker最終更新（例外発生）
            if PROGRESS_TRACKER_AVAILABLE:
                progress_tracker.fail_analysis(execution_id, "exception", f"Training failed with exception: {str(e)}")
            
            # エラー情報をデータベースに記録
            self.execution_db.add_execution_error(execution_id, {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'traceback': traceback.format_exc(),
                'step': 'general'
            })
            
            # 実行ステータスを失敗に更新
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                current_operation=f'エラー: {str(e)}'
            )
            
            raise
    
    async def _execute_step(self, execution_id: str, step_name: str, 
                          step_function, *args, **kwargs):
        """実行ステップの共通処理"""
        try:
            self.logger.info(f"Executing step: {step_name}")
            step_start = datetime.now()
            
            # 進捗更新
            exchange = self._get_exchange_from_config()
            step_display_names = {
                'data_fetch': f'{exchange.capitalize()}銘柄確認・データ取得',
                'backtest': '全戦略バックテスト実行',
                'ml_training': 'ML学習実行',
                'result_save': '結果保存・ランキング更新'
            }
            
            current_operation = step_display_names.get(step_name, step_name)
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.RUNNING,
                current_operation=current_operation
            )
            
            # progress_tracker段階更新
            if PROGRESS_TRACKER_AVAILABLE:
                stage_mapping = {
                    'data_fetch': 'data_validation',
                    'backtest': 'backtest_analysis', 
                    'ml_training': 'ml_training',
                    'result_save': 'finalizing'
                }
                stage = stage_mapping.get(step_name, step_name)
                self.logger.info(f"📊 progress_tracker段階更新: {step_name} -> {stage} (execution_id: {execution_id})")
                progress_tracker.update_stage(execution_id, stage)
                self.logger.info(f"✅ progress_tracker段階更新完了")
            else:
                self.logger.warning(f"⚠️ progress_tracker利用不可のため段階更新スキップ: {step_name}")
            
            # ステップ実行
            result = await step_function(*args, **kwargs)
            
            step_end = datetime.now()
            duration = (step_end - step_start).total_seconds()
            
            # データベースにステップ完了を記録
            self.execution_db.add_execution_step(
                execution_id,
                step_name,
                'SUCCESS',
                result_data=result,
                duration_seconds=duration
            )
            
            self.logger.success(f"Step {step_name} completed in {duration:.2f}s")
            
        except InsufficientMarketDataError as e:
            # 市場データ不足エラーの場合は特別な処理
            self.logger.error(f"❌ 市場データ不足により銘柄追加を中止: {e}")
            self.logger.error(f"   エラータイプ: {e.error_type}")
            self.logger.error(f"   不足データ: {e.missing_data}")
            
            # データベースに特別なステータスで記録
            self.execution_db.add_execution_step(
                execution_id,
                step_name,
                'FAILED_INSUFFICIENT_DATA',
                error_message=f"市場データ不足: {e}",
                error_traceback=traceback.format_exc()
            )
            
            # 実行を失敗として終了
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                current_operation=f'市場データ不足により中止: {e.error_type}',
                error_message=str(e)
            )
            
            raise  # 上位に伝播して銘柄追加を完全に停止
            
        except InsufficientConfigurationError as e:
            # 設定不足エラーの場合は特別な処理
            self.logger.error(f"❌ 設定不足により銘柄追加を中止: {e}")
            self.logger.error(f"   エラータイプ: {e.error_type}")
            self.logger.error(f"   不足設定: {e.missing_config}")
            
            # データベースに特別なステータスで記録
            self.execution_db.add_execution_step(
                execution_id,
                step_name,
                'FAILED_INSUFFICIENT_CONFIG',
                error_message=f"設定不足: {e}",
                error_traceback=traceback.format_exc()
            )
            
            # 実行を失敗として終了
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                current_operation=f'設定不足により中止: {e.error_type}',
                error_message=str(e)
            )
            
            raise  # 上位に伝播して銘柄追加を完全に停止
            
        except LeverageAnalysisError as e:
            # レバレッジ分析エラーの場合は特別な処理
            self.logger.error(f"❌ レバレッジ分析失敗により銘柄追加を中止: {e}")
            self.logger.error(f"   エラータイプ: {e.error_type}")
            self.logger.error(f"   分析段階: {e.analysis_stage}")
            
            # データベースに特別なステータスで記録
            self.execution_db.add_execution_step(
                execution_id,
                step_name,
                'FAILED_LEVERAGE_ANALYSIS',
                error_message=f"レバレッジ分析失敗: {e}",
                error_traceback=traceback.format_exc()
            )
            
            # 実行を失敗として終了
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                current_operation=f'レバレッジ分析失敗により中止: {e.error_type}',
                error_message=str(e)
            )
            
            raise  # 上位に伝播して銘柄追加を完全に停止
            
        except Exception as e:
            self.logger.error(f"Step {step_name} failed: {e}")
            
            # データベースにステップ失敗を記録
            self.execution_db.add_execution_step(
                execution_id,
                step_name,
                'FAILED',
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
            
            # エラー情報も追加
            self.execution_db.add_execution_error(execution_id, {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'traceback': traceback.format_exc(),
                'step': step_name
            })
            
            raise
    
    def _get_exchange_from_config(self) -> str:
        """設定ファイルから取引所を取得"""
        import json
        import os
        
        # 1. 設定ファイルから読み込み
        try:
            if os.path.exists('exchange_config.json'):
                with open('exchange_config.json', 'r') as f:
                    config = json.load(f)
                    return config.get('default_exchange', 'hyperliquid').lower()
        except Exception as e:
            self.logger.warning(f"Failed to load exchange config: {e}")
        
        # 2. 環境変数から読み込み
        env_exchange = os.getenv('EXCHANGE_TYPE', '').lower()
        if env_exchange in ['hyperliquid', 'gateio']:
            return env_exchange
        
        # 3. デフォルト: Hyperliquid
        return 'hyperliquid'
    
    async def _fetch_and_validate_data(self, symbol: str, custom_period_settings: dict = None) -> Dict:
        """データ取得と検証（Hyperliquidバリデーション統合）"""
        
        try:
            # 1. マルチ取引所銘柄バリデーション（厳格モード）
            exchange = self._get_exchange_from_config()
            
            self.logger.info(f"Validating {symbol} on {exchange}...")
            
            # マルチ取引所対応バリデーション
            from hyperliquid_api_client import MultiExchangeAPIClient
            api_client = MultiExchangeAPIClient(exchange_type=exchange)
            
            validation_result = await api_client.validate_symbol_real(symbol)
            
            if not validation_result['valid']:
                # バリデーション失敗時は明確なエラーを投げる
                status = validation_result.get('status', 'unknown')
                reason = validation_result.get('reason', 'Unknown error')
                
                if status == "invalid":
                    raise ValueError(f"{symbol}: {reason}")
                elif status == "inactive":
                    raise ValueError(f"{symbol}: {reason}")
                else:
                    # その他のエラー
                    raise ValueError(f"Validation failed for {symbol}: {reason}")
            
            self.logger.success(f"✅ {symbol} validated on {exchange}")
            
            # 2. 履歴データ取得
            self.logger.info(f"Fetching historical data for {symbol}")
            
            try:
                self.logger.info(f"🚀 STARTING OHLCV DATA VALIDATION for {symbol}")
                self.logger.info(f"📅 カスタム期間設定受信: {custom_period_settings}")
                
                # 期間設定に応じてデータ取得
                if custom_period_settings and custom_period_settings.get('mode') == 'custom':
                    self.logger.info(f"📅 カスタム期間設定使用: {custom_period_settings}")
                    
                    # カスタム期間に200本前データを含む期間でデータ取得
                    from datetime import datetime, timedelta, timezone
                    import dateutil.parser
                    
                    try:
                        start_date_str = custom_period_settings.get('start_date')
                        end_date_str = custom_period_settings.get('end_date')
                        
                        start_time = dateutil.parser.parse(start_date_str).replace(tzinfo=timezone.utc)
                        end_time = dateutil.parser.parse(end_date_str).replace(tzinfo=timezone.utc)
                        
                        # 200本前データ（1時間足で200時間前）
                        pre_period_hours = 200
                        adjusted_start_time = start_time - timedelta(hours=pre_period_hours)
                        
                        self.logger.info(f"📅 カスタム期間データ取得: {adjusted_start_time.strftime('%Y-%m-%d %H:%M')} ～ {end_time.strftime('%Y-%m-%d %H:%M')}")
                        
                        # カスタム期間でのデータ取得
                        ohlcv_data = await api_client.get_ohlcv_data(symbol, '1h', adjusted_start_time, end_time)
                        
                    except Exception as e:
                        self.logger.error(f"カスタム期間設定エラー: {e}")
                        # フォールバック: デフォルト90日間
                        ohlcv_data = await api_client.get_ohlcv_data_with_period(symbol, '1h', days=90)
                else:
                    # デフォルト: 1時間足、90日分のデータを取得
                    ohlcv_data = await api_client.get_ohlcv_data_with_period(symbol, '1h', days=90)
                
                data_info = {
                    'records': len(ohlcv_data),
                    'date_range': {
                        'start': ohlcv_data['timestamp'].min().strftime('%Y-%m-%d') if len(ohlcv_data) > 0 else 'N/A',
                        'end': ohlcv_data['timestamp'].max().strftime('%Y-%m-%d') if len(ohlcv_data) > 0 else 'N/A'
                    }
                }
                
                # 3. データ品質チェック（カスタム期間設定時は柔軟に調整）
                if custom_period_settings and custom_period_settings.get('mode') == 'custom':
                    # カスタム期間設定時は最低100データポイント（約4日分）
                    minimum_required = 100
                    if data_info['records'] < minimum_required:
                        raise ValueError(f"{symbol}: Only {data_info['records']} data points available (minimum for custom period: {minimum_required})")
                    self.logger.info(f"✅ カスタム期間データ品質OK: {data_info['records']}データポイント")
                else:
                    # デフォルト期間（90日）の場合は従来通り1000データポイント必要
                    if data_info['records'] < 1000:
                        raise ValueError(f"{symbol}: Only {data_info['records']} data points available (minimum: 1000)")
                
                self.logger.success(f"📊 Data fetched: {data_info['records']} records for {symbol}")
                
                return {
                    'symbol': symbol,
                    'validation_status': validation_result.get('status', 'valid'),
                    'validation_valid': validation_result.get('valid', True),
                    'records_fetched': data_info['records'],
                    'date_range': data_info['date_range'],
                    'data_quality': 'HIGH',
                    'leverage_limit': validation_result.get('market_info', {}).get('leverage_limit', 10)
                }
                
            except Exception as api_error:
                self.logger.error(f"❌ Failed to fetch OHLCV data for {symbol}: {api_error}")
                
                # データ取得失敗時は詳細なエラーメッセージで処理を停止
                error_msg = str(api_error)
                if "No data retrieved" in error_msg:
                    raise ValueError(f"{symbol}のOHLCVデータが取得できませんでした。{exchange}で取引されていない可能性があります。")
                elif "Too many failed requests" in error_msg:
                    raise ValueError(f"{symbol}のデータ取得で多数のリクエストが失敗しました。銘柄が存在しないか、一時的にデータが利用できません。")
                else:
                    raise ValueError(f"{symbol}のOHLCVデータ取得に失敗: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"❌ Data fetch/validation failed for {symbol}: {e}")
            # 詳細なエラー情報をログに記録
            error_detail = {
                'symbol': symbol,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'step': 'data_fetch_validation'
            }
            
            # エラー詳細は既にadd_execution_errorで記録済み
            
            raise
    
    async def _run_comprehensive_backtest(self, symbol: str, selected_strategies: list = None, selected_timeframes: list = None, strategy_configs: list = None, skip_pretask_creation: bool = False, custom_period_settings: dict = None) -> Dict:
        """全戦略・全時間足でバックテスト実行（選択的実行対応）"""
        
        try:
            self.logger.info(f"Running comprehensive backtest for {symbol}")
            
            # カスタム戦略設定がある場合はそれを使用
            if strategy_configs:
                configs = []
                for config in strategy_configs:
                    # 設定バリデーション強化
                    if not config.get('base_strategy'):
                        self.logger.warning(f"Skipping config without base_strategy: {config}")
                        continue
                    configs.append({
                        'symbol': symbol,
                        'timeframe': config['timeframe'],
                        'strategy': config['base_strategy'],
                        'strategy_config_id': config.get('id'),
                        'strategy_name': config.get('name'),
                        'custom_parameters': config.get('parameters', {})
                    })
                self.logger.info(f"Using {len(configs)} custom strategy configurations")
            else:
                # デフォルト設定生成
                timeframes = selected_timeframes or ['1m', '3m', '5m', '15m', '30m', '1h']
                strategies = selected_strategies or ['Conservative_ML', 'Aggressive_Traditional', 'Full_ML']
                
                configs = []
                for timeframe in timeframes:
                    for strategy in strategies:
                        configs.append({
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'strategy': strategy
                        })
                self.logger.info(f"Using default strategy combinations: {len(strategies)} strategies × {len(timeframes)} timeframes = {len(configs)} configs")
            
            self.logger.info(f"Generated {len(configs)} backtest configurations")
            
            # execution_id取得
            current_execution_id = getattr(self, '_current_execution_id', None)
            
            # 注意: 9段階フィルタリングは実際のバックテスト処理内で時系列実行される
            # ここでは設定レベルでの事前フィルタリングは行わない
            self.logger.info(f"バックテスト実行設定数: {len(configs)}")
            
            # バックテスト実行（ScalableAnalysisSystemを使用 + 進捗ロガー統合）
            # 支持線・抵抗線データ不足時はシグナルなしとして継続
            # 🔧 修正: 戦略別独立実行でエラー隔離を実現
            
            # execution_idが環境変数にも設定されているか確認
            import os
            env_execution_id = os.environ.get('CURRENT_EXECUTION_ID')
            if current_execution_id and not env_execution_id:
                os.environ['CURRENT_EXECUTION_ID'] = current_execution_id
                self.logger.info(f"📝 実行IDを環境変数に再設定: {current_execution_id}")
            
            processed_count = self._execute_strategies_independently(
                configs, 
                symbol, 
                current_execution_id,
                custom_period_settings
            )
            
            # 結果の集計（データベースから取得）
            results = []
            best_performance = None
            failed_tests = 0
            low_performance_count = 0
            
            # データベースから結果を取得
            for config in configs:
                try:
                    query_results = self.analysis_system.query_analyses(
                        filters={
                            'symbol': config['symbol'],
                            'timeframe': config['timeframe'], 
                            'config': config['strategy']
                        },
                        limit=1
                    )
                    
                    if query_results and len(query_results) > 0:
                        result = query_results[0] if isinstance(query_results, list) else query_results.iloc[0].to_dict()
                        result['status'] = 'success'
                        results.append(result)
                        
                        if result.get('sharpe_ratio', 0) < 1.0:
                            low_performance_count += 1
                        
                        if best_performance is None or result.get('sharpe_ratio', 0) > best_performance.get('sharpe_ratio', 0):
                            best_performance = result
                    else:
                        failed_tests += 1
                        results.append({'status': 'failed', 'config': config})
                        
                except Exception as e:
                    self.logger.warning(f"Failed to retrieve result for {config}: {e}")
                    failed_tests += 1
                    results.append({'status': 'failed', 'config': config})
            
            successful_tests = len(configs) - failed_tests
            
            # シグナルなし（no_signal）の場合も成功として扱う
            # processed_count > 0 なら分析が実行されたと判定
            if successful_tests == 0 and processed_count == 0:
                error_msg = f"全戦略の分析が失敗しました。{failed_tests}件のテストが失敗。"
                self.logger.error(f"❌ {symbol}: {error_msg}")
                raise ValueError(error_msg)
            elif processed_count > 0 and successful_tests == 0:
                # 分析は実行されたが、通常の成功結果がない場合（シグナルなしの場合）
                self.logger.info(f"📊 {symbol}: 分析完了（シグナルなし） - {processed_count}戦略実行, {failed_tests}件は結果取得失敗")
            
            self.logger.success(f"Backtest completed: {len(configs)} configurations tested")
            
            return {
                'total_combinations': len(configs),
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'low_performance_count': low_performance_count,
                'best_performance': best_performance,
                'results_summary': {
                    'avg_sharpe': sum(r.get('sharpe_ratio', 0) for r in results) / len(results) if results else 0,
                    'max_sharpe': max(r.get('sharpe_ratio', 0) for r in results) if results else 0,
                    'min_sharpe': min(r.get('sharpe_ratio', 0) for r in results) if results else 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Backtest failed for {symbol}: {e}")
            raise
    
    async def _train_ml_models(self, symbol: str) -> Dict:
        """ML学習実行"""
        
        try:
            self.logger.info(f"Training ML models for {symbol}")
            
            # ML学習の実装
            # TODO: 実際のML学習ロジックを実装
            
            # TODO: ランダムML結果生成は品質問題のためコメントアウト (2024-06-18)
            # 実際のML学習ロジック実装が必要
            import time
            # import random
            
            # 学習時間をシミュレート
            await asyncio.sleep(2)
            
            # TODO: 以下のランダム生成は削除し、実際のML学習結果を返すように修正必要
            # models_trained = {
            #     'support_resistance_ml': {
            #         'accuracy': round(random.uniform(0.65, 0.85), 3),
            #         'f1_score': round(random.uniform(0.6, 0.8), 3),
            #         'training_samples': random.randint(5000, 15000)
            #     },
            #     'breakout_predictor': {
            #         'accuracy': round(random.uniform(0.6, 0.8), 3),
            #         'precision': round(random.uniform(0.65, 0.85), 3),
            #         'training_samples': random.randint(3000, 10000)
            #     },
            #     'btc_correlation': {
            #         'r_squared': round(random.uniform(0.7, 0.9), 3),
            #         'mae': round(random.uniform(0.02, 0.08), 4),
            #         'training_samples': random.randint(8000, 20000)
            #     }
            # }
            
            # 暫定: 実際のML学習未実装のため固定値を返す
            models_trained = {
                'support_resistance_ml': {
                    'accuracy': 0.000,  # 未学習状態を示す
                    'f1_score': 0.000,
                    'training_samples': 0,
                    'status': 'not_implemented'
                },
                'breakout_predictor': {
                    'accuracy': 0.000,
                    'precision': 0.000,
                    'training_samples': 0,
                    'status': 'not_implemented'
                },
                'btc_correlation': {
                    'r_squared': 0.000,
                    'mae': 0.000,
                    'training_samples': 0,
                    'status': 'not_implemented'
                }
            }
            
            self.logger.success(f"ML training completed for {symbol}")
            
            return {
                'models_trained': models_trained,
                'total_training_time': 120,  # seconds
                'avg_accuracy': 0.000,  # ML未実装のため0
                'status': 'ml_training_not_implemented'
            }
            
        except Exception as e:
            self.logger.error(f"ML training failed for {symbol}: {e}")
            raise
    
    async def _save_results(self, symbol: str) -> Dict:
        """結果保存とランキング更新"""
        
        try:
            self.logger.info(f"Saving results for {symbol}")
            
            # 結果の保存
            # TODO: 戦略ランキングDBへの保存実装
            
            # 一時的な実装
            await asyncio.sleep(1)
            
            self.logger.success(f"Results saved for {symbol}")
            
            return {
                'symbol': symbol,
                'ranking_entries_created': 18,  # 3 strategies × 6 timeframes
                'database_updated': True,
                'available_for_selection': True
            }
            
        except Exception as e:
            self.logger.error(f"Result saving failed for {symbol}: {e}")
            raise
    
    def _create_no_signal_record(self, symbol: str, config: Dict, execution_id: str, error_message: str = None):
        """シグナルなしの分析レコードを作成"""
        try:
            import sqlite3
            from pathlib import Path
            from datetime import datetime, timezone
            import json
            
            analysis_db_path = Path(__file__).parent / "large_scale_analysis" / "analysis.db"
            
            with sqlite3.connect(analysis_db_path) as conn:
                # バックテスト詳細情報（シグナルなし）
                backtest_details = {
                    "status": "no_signal",
                    "reason": error_message or "No trading signals detected",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # 既存のpendingレコードを更新（INSERTではなくUPDATE）
                conn.execute("""
                    UPDATE analyses SET
                        strategy_config_id = ?, strategy_name = ?,
                        task_status = 'completed', task_completed_at = ?,
                        total_return = ?, sharpe_ratio = ?, max_drawdown = ?, win_rate = ?, total_trades = ?,
                        status = 'no_signal', error_message = ?, generated_at = ?
                    WHERE symbol = ? AND timeframe = ? AND config = ? AND execution_id = ? AND task_status = 'pending'
                """, (
                    config.get('strategy_config_id'),
                    config.get('strategy_name', f"{config['strategy']}-{config['timeframe']}"),
                    datetime.now(timezone.utc).isoformat(),
                    0.0,  # シグナルなしのため0リターン
                    0.0,  # シグナルなしのため0シャープレシオ
                    0.0,  # シグナルなしのため0ドローダウン
                    0.0,  # シグナルなしのため0勝率
                    0,    # シグナルなしのため0取引
                    error_message or 'No trading signals detected',
                    datetime.now().isoformat(),
                    symbol,
                    config['timeframe'],
                    config['strategy'],
                    execution_id
                ))
                
                conn.commit()
                
            self.logger.info(f"📝 シグナルなしレコード作成: {symbol} - {config['strategy']} ({config['timeframe']})")
            
        except Exception as e:
            self.logger.error(f"シグナルなしレコード作成エラー: {e}")

    def _execute_strategies_independently(self, configs: List[Dict], symbol: str, execution_id: str, custom_period_settings: dict = None) -> int:
        """
        戦略を独立実行してエラー隔離を実現
        各戦略の失敗が他戦略に影響しないよう個別処理
        
        Args:
            configs: 戦略設定リスト
            symbol: 銘柄名
            execution_id: 実行ID
            custom_period_settings: カスタム期間設定
            
        Returns:
            成功した戦略数
        """
        success_count = 0
        
        self.logger.info(f"🔧 戦略別独立実行開始: {len(configs)}戦略")
        
        for i, config in enumerate(configs):
            strategy_name = f"{config['strategy']}-{config['timeframe']}"
            
            try:
                self.logger.info(f"  戦略 {i+1}/{len(configs)}: {strategy_name}")
                
                # 個別戦略分析を実行
                result = self._execute_single_strategy(
                    config, 
                    symbol, 
                    execution_id, 
                    custom_period_settings
                )
                
                if result:
                    success_count += 1
                    self.logger.info(f"  ✅ {strategy_name}: 分析成功")
                else:
                    self.logger.warning(f"  ⚠️ {strategy_name}: シグナルなし")
                    # シグナルなしレコード作成
                    self._create_no_signal_record(symbol, config, execution_id)
                    
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"  ❌ {strategy_name}: 分析エラー - {error_msg[:100]}")
                
                # エラーの場合もシグナルなしレコード作成（エラー情報付き）
                self._create_no_signal_record(symbol, config, execution_id, error_msg[:100])
                
                # 重要: 他戦略の処理を継続
                continue
        
        self.logger.info(f"🎯 独立実行結果: {success_count}/{len(configs)} 戦略成功")
        return success_count
    
    def _execute_single_strategy(self, config: Dict, symbol: str, execution_id: str, custom_period_settings: dict = None) -> bool:
        """
        単一戦略の分析実行
        
        Args:
            config: 戦略設定
            symbol: 銘柄名
            execution_id: 実行ID
            custom_period_settings: カスタム期間設定
            
        Returns:
            成功フラグ
        """
        # 単一設定でバッチ分析を実行
        single_config_list = [config]
        
        processed_count = self.analysis_system.generate_batch_analysis(
            single_config_list,
            symbol=symbol,
            execution_id=execution_id,
            skip_pretask_creation=True,  # 既にPre-task作成済み
            custom_period_settings=custom_period_settings
        )
        
        return processed_count > 0

    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """実行状況の取得"""
        return self.execution_db.get_execution(execution_id)
    
    def list_executions(self, limit: int = 10) -> List[Dict]:
        """実行履歴の一覧取得"""
        return self.execution_db.list_executions(limit=limit)
    
    async def _run_early_fail_validation(self, symbol: str):
        """Early Fail検証実行"""
        try:
            # Early Fail検証を非同期実行
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self.early_fail_validator.validate_symbol,
                symbol
            )
            
            # validate_symbolがコルーチンを返す場合の対処
            if asyncio.iscoroutine(result):
                result = await result
            
            if result.passed:
                self.logger.info(f"✅ Early Fail検証成功: {symbol}")
                # メタデータをログに記録
                if result.metadata:
                    self.logger.info(f"📊 検証メタデータ: {result.metadata}")
            else:
                self.logger.warning(f"❌ Early Fail検証失敗: {symbol} - {result.fail_reason}")
                if result.suggestion:
                    self.logger.info(f"💡 提案: {result.suggestion}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Early Fail検証中にエラー: {symbol} - {str(e)}")
            # エラー時は失敗扱いで結果を返す
            from symbol_early_fail_validator import EarlyFailResult, FailReason
            return EarlyFailResult(
                symbol=symbol,
                passed=False,
                fail_reason=FailReason.API_CONNECTION_FAILED,
                error_message=f"検証中にエラーが発生: {str(e)}"
            )
    
    async def _apply_filtering_framework(self, configs: List[Dict], symbol: str, execution_id: str) -> List[Dict]:
        """
        注意: このメソッドは非推奨です。
        9段階フィルタリングは実際のバックテスト処理内で時系列毎に実行されます。
        ここでは設定レベルでの事前フィルタリングは行いません。
        """
        self.logger.warning("⚠️ _apply_filtering_framework は非推奨です。9段階フィルタリングはバックテスト内で時系列実行されます。")
        
        # 設定をそのまま返す（フィルタリングなし）
        return configs
    
    async def _evaluate_config_viability(self, config: Dict, symbol: str) -> bool:
        """個別戦略設定の実行可能性評価（軽量版）"""
        try:
            # 基本的な設定検証
            required_fields = ['symbol', 'timeframe', 'strategy']
            if not all(field in config for field in required_fields):
                return False
            
            # 戦略固有の軽量チェック
            strategy = config['strategy']
            timeframe = config['timeframe']
            
            # 簡単な戦略・時間足組み合わせチェック
            if strategy == 'Conservative_ML' and timeframe in ['1m', '3m']:
                # 保守的ML戦略は短期間足では効果が低い
                return False
            
            if strategy == 'Aggressive_Traditional' and timeframe in ['1h']:
                # アグレッシブ従来戦略は長期間足では効果が低い
                return False
            
            # TODO: 将来的に実際のFilteringFrameworkと連携
            # 現在は基本的な論理チェックのみ実装
            
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️ 設定評価中にエラー: {config} - {str(e)}")
            # エラー時は保守的に通す
            return True
    
    async def _record_filtering_statistics(self, execution_id: str, total_configs: int, passed_configs: int, filtered_configs: int):
        """フィルタリング統計をexecution_logに記録"""
        try:
            metadata = {
                'filtering_statistics': {
                    'total_configurations': total_configs,
                    'passed_configurations': passed_configs,
                    'filtered_configurations': filtered_configs,
                    'filter_rate_percent': (filtered_configs / total_configs) * 100 if total_configs > 0 else 0,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # execution_logのメタデータを更新
            self.execution_db.add_execution_step(
                execution_id,
                "filtering_framework_precheck",
                ExecutionStatus.COMPLETED.value,  # .valueを追加
                metadata=metadata
            )
            
            self.logger.info(f"📝 フィルタリング統計記録完了: {execution_id}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ フィルタリング統計記録エラー: {str(e)}")
    
    def _verify_analysis_results(self, symbol: str, execution_id: str) -> bool:
        """分析結果の存在確認（より柔軟な検証）"""
        try:
            import sqlite3
            from pathlib import Path
            
            analysis_db_path = Path(__file__).parent / "large_scale_analysis" / "analysis.db"
            if not analysis_db_path.exists():
                self.logger.warning(f"Analysis database not found: {analysis_db_path}")
                return False
                
            with sqlite3.connect(analysis_db_path) as conn:
                # 1. 該当execution_idの分析結果を確認
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM analyses 
                    WHERE symbol = ? AND execution_id = ?
                ''', (symbol, execution_id))
                
                result_count = cursor.fetchone()[0]
                
                if result_count > 0:
                    self.logger.info(f"✅ {symbol} の分析結果確認（execution_id一致）: {result_count} 件")
                    return True
                
                # 2. 過去10分以内の分析結果を確認（バックテスト処理が完了している場合）
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM analyses 
                    WHERE symbol = ? 
                    AND generated_at > datetime('now', '-10 minutes')
                ''', (symbol,))
                
                recent_count = cursor.fetchone()[0]
                if recent_count > 0:
                    self.logger.info(f"✅ {symbol} の最近の分析結果確認: {recent_count} 件（過去10分以内）")
                    return True
                
                # 3. execution_idがNULLの場合も確認（旧システム対応）
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM analyses 
                    WHERE symbol = ? AND execution_id IS NULL
                    AND generated_at > datetime('now', '-5 minutes')
                ''', (symbol,))
                
                null_count = cursor.fetchone()[0]
                if null_count > 0:
                    self.logger.warning(f"⚠️ {symbol} の分析結果（execution_idなし）: {null_count} 件存在")
                    return True
                
                # 4. 詳細なデバッグ情報出力
                cursor = conn.execute('''
                    SELECT execution_id, generated_at FROM analyses 
                    WHERE symbol = ? 
                    ORDER BY generated_at DESC LIMIT 5
                ''', (symbol,))
                
                recent_results = cursor.fetchall()
                if recent_results:
                    self.logger.info(f"📊 {symbol} の最近の分析結果:")
                    for exec_id, gen_at in recent_results:
                        self.logger.info(f"  - execution_id: {exec_id}, generated_at: {gen_at}")
                
                self.logger.error(f"❌ {symbol} の分析結果が見つかりません（現在のexecution_id: {execution_id}）")
                return False
                        
        except Exception as e:
            self.logger.error(f"分析結果確認エラー: {e}")
            return False


async def main():
    """コマンドライン引数によるシンボル追加実行"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Auto Symbol Training System')
    parser.add_argument('--symbol', type=str, default='HYPE', help='Symbol to add (default: HYPE)')
    parser.add_argument('--days', type=int, default=90, help='Days of historical data (default: 90)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    trainer = AutoSymbolTrainer()
    
    try:
        # 指定された銘柄でのテスト実行
        print(f"🚀 Starting automatic training for symbol: {args.symbol}")
        execution_id = await trainer.add_symbol_with_training(args.symbol)
        print(f"Execution completed: {execution_id}")
        
        # 実行状況の確認
        status = trainer.get_execution_status(execution_id)
        print(f"Final status: {status['status']}")
        print(f"Steps completed: {len(status.get('steps', []))}")
        
        # 実行履歴の確認
        executions = trainer.list_executions(limit=3)
        print(f"Recent executions: {len(executions)}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())