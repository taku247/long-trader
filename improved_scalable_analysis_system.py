"""
改善版：大規模バックテスト分析システム
時間足別の適切なトレード生成とデータ分割を実装
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
from datetime import datetime, timedelta
import logging
from pathlib import Path

# 設定管理
from config.timeframe_config_manager import TimeframeConfigManager

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ImprovedScalableAnalysisSystem:
    """
    改善版：時間足別の適切なトレード生成とデータ分割を実装
    
    主な改善点：
    1. 時間足別のトレード頻度設定
    2. データ期間の動的調整
    3. 適切な学習・検証・テスト分割
    4. リアリスティックなトレード分布
    """
    
    # 時間足設定は外部ファイルから読み込み
    # config/timeframe_conditions.json を参照
    
    def __init__(self, base_dir="improved_analysis", config_file=None):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # 設定管理の初期化
        self.config_manager = TimeframeConfigManager(config_file)
        print(f"✅ 時間足設定を外部ファイルから読み込み完了")
        
        # ディレクトリ構造
        self.db_path = self.base_dir / "analysis.db"
        self.charts_dir = self.base_dir / "charts"
        self.data_dir = self.base_dir / "data"
        self.compressed_dir = self.base_dir / "compressed"
        
        for dir_path in [self.charts_dir, self.data_dir, self.compressed_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # データベース初期化
        self.init_database()
    
    def init_database(self):
        """SQLiteデータベースを初期化（元のシステムと同じ）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
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
                    data_compressed_path TEXT,
                    status TEXT DEFAULT 'pending',
                    data_days INTEGER,
                    train_samples INTEGER,
                    val_samples INTEGER,
                    test_samples INTEGER
                )
            ''')
            
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
    
    def get_timeframe_config(self, timeframe: str) -> dict:
        """時間足に応じた設定を取得（外部設定ファイルから）"""
        return self.config_manager.get_timeframe_config(timeframe)
    
    def _generate_real_analysis(self, symbol, timeframe, config, evaluation_period_days=None):
        """
        改善版：時間足に応じた条件ベースシグナル生成
        """
        try:
            from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
            
            # 時間足別の設定を取得
            tf_config = self.get_timeframe_config(timeframe)
            
            # 評価期間の決定
            if evaluation_period_days is None:
                evaluation_period_days = tf_config['data_days']
            
            print(f"🎯 改善版条件ベース分析を開始: {symbol} {timeframe} {config}")
            print(f"   📊 データ期間: {evaluation_period_days}日")
            print(f"   🎯 条件ベース評価: 市場条件を満たした場合のみシグナル生成")
            print(f"   📈 分割比: Train={tf_config['train_ratio']:.0%}, Val={tf_config['val_ratio']:.0%}, Test={tf_config['test_ratio']:.0%}")
            
            # 取引所設定
            exchange = self._get_exchange_from_config(config)
            
            # ボット初期化（キャッシュ利用）
            if not hasattr(self, '_bot_cache'):
                self._bot_cache = {}
            
            bot_key = f"{exchange}_{symbol}"
            if bot_key not in self._bot_cache:
                bot = HighLeverageBotOrchestrator(use_default_plugins=True, exchange=exchange)
                # データ取得（時間足に応じた期間）
                market_data = bot._fetch_market_data(symbol, timeframe)
                if market_data.empty:
                    raise Exception(f"No market data available for {symbol}")
                bot._cached_data = market_data
                self._bot_cache[bot_key] = bot
            else:
                bot = self._bot_cache[bot_key]
            
            # 条件ベーストレード生成
            trades = self._generate_condition_based_trades(
                bot, symbol, timeframe, config, evaluation_period_days, tf_config
            )
            
            signals_count = len(trades)
            print(f"✅ {symbol} {timeframe} {config}: 条件ベース分析完了 ({signals_count} signals)")
            
            return trades
            
        except Exception as e:
            logger.error(f"Real analysis failed: {e}")
            raise
    
    def _generate_condition_based_trades(self, bot, symbol, timeframe, config,
                                        evaluation_period_days, tf_config):
        """条件ベースのトレード生成 - 市場条件を満たした場合のみシグナル生成"""
        trades = []
        
        # 期間設定
        end_time = datetime.now()
        start_time = end_time - timedelta(days=evaluation_period_days)
        
        # 評価間隔設定
        evaluation_interval = timedelta(minutes=tf_config['evaluation_interval_minutes'])
        
        # 条件ベース評価の実行
        current_time = start_time
        total_evaluations = 0
        signals_generated = 0
        
        print(f"🔍 条件ベース評価: {start_time.strftime('%Y-%m-%d')} から {end_time.strftime('%Y-%m-%d')}")
        print(f"📊 評価間隔: {tf_config['evaluation_interval_minutes']}分おき")
        
        while current_time <= end_time:
            total_evaluations += 1
            try:
                # 市場条件の評価
                result = bot.analyze_symbol(symbol, timeframe, config)
                if not result or 'current_price' not in result:
                    current_time += evaluation_interval
                    continue
                
                # エントリー条件の評価
                should_enter = self._evaluate_entry_conditions_improved(result, tf_config)
                
                if not should_enter:
                    # 条件を満たさない場合はスキップ
                    current_time += evaluation_interval
                    continue
                
                signals_generated += 1
                
                # トレード情報の生成
                trade_info = self._create_trade_info(
                    result, config, current_time, timeframe
                )
                
                trades.append(trade_info)
                
                # 進捗表示
                if signals_generated % 5 == 0:
                    progress_pct = ((current_time - start_time).total_seconds() / 
                                  (end_time - start_time).total_seconds()) * 100
                    print(f"   🎯 シグナル生成: {signals_generated}件 (進捗: {progress_pct:.1f}%)")
                
            except Exception as e:
                logger.warning(f"Analysis failed at {current_time}: {e}")
            
            # 次の評価時点に進む
            current_time += evaluation_interval
        
        evaluation_rate = (signals_generated / total_evaluations * 100) if total_evaluations > 0 else 0
        print(f"📊 総評価数: {total_evaluations}, シグナル生成: {signals_generated}件 ({evaluation_rate:.1f}%)")
        
        return trades
    
    def _evaluate_entry_conditions_improved(self, analysis_result, tf_config):
        """
        改善版エントリー条件評価
        
        Args:
            analysis_result: ハイレバボットからの分析結果
            tf_config: 時間足設定
            
        Returns:
            bool: エントリー条件を満たしているかどうか
        """
        
        # 基本的な条件チェック
        leverage = analysis_result.get('leverage', 0)
        confidence = analysis_result.get('confidence', 0) / 100.0
        risk_reward = analysis_result.get('risk_reward_ratio', 0)
        current_price = analysis_result.get('current_price', 0)
        
        # 設定から最小条件を取得
        min_leverage = tf_config.get('min_leverage', 3.0)
        min_confidence = tf_config.get('min_confidence', 0.5)
        min_risk_reward = tf_config.get('min_risk_reward', 2.0)
        
        # 条件評価
        leverage_ok = leverage >= min_leverage
        confidence_ok = confidence >= min_confidence
        risk_reward_ok = risk_reward >= min_risk_reward
        price_ok = current_price > 0
        
        all_conditions_met = all([leverage_ok, confidence_ok, risk_reward_ok, price_ok])
        
        # 条件満足時のログ
        if all_conditions_met:
            print(f"   ✅ エントリー条件満足: L={leverage:.1f}x, C={confidence:.1%}, RR={risk_reward:.1f}")
        
        return all_conditions_met
    
    def _generate_trade_timestamps(self, start_time, end_time, num_trades, tf_config):
        """リアリスティックなトレードタイムスタンプを生成"""
        timestamps = []
        
        distribution = tf_config['trade_distribution']
        active_hours = tf_config['active_hours']
        
        if distribution == 'uniform':
            # 均等分布
            interval = (end_time - start_time) / num_trades
            for i in range(num_trades):
                ts = start_time + interval * i
                timestamps.append(self._adjust_to_trading_hours(ts, active_hours))
        
        elif distribution in ['concentrated', 'semi_concentrated']:
            # アクティブ時間帯に集中
            current_date = start_time.date()
            end_date = end_time.date()
            trades_generated = 0
            
            while current_date <= end_date and trades_generated < num_trades:
                # 平日のみ
                if current_date.weekday() < 5:
                    # その日のトレード数を決定
                    daily_trades = np.random.poisson(tf_config['trades_per_day'])
                    daily_trades = min(daily_trades, num_trades - trades_generated)
                    
                    # アクティブ時間帯にランダムに配置
                    for _ in range(daily_trades):
                        hour = np.random.choice(list(active_hours))
                        minute = np.random.randint(0, 60)
                        ts = datetime.combine(current_date, datetime.min.time())
                        ts = ts.replace(hour=hour, minute=minute)
                        timestamps.append(ts)
                        trades_generated += 1
                
                current_date += timedelta(days=1)
            
            # タイムスタンプをソート
            timestamps.sort()
        
        return timestamps[:num_trades]
    
    def _adjust_to_trading_hours(self, timestamp, active_hours):
        """タイムスタンプを取引時間に調整"""
        # 週末の場合は月曜に移動
        if timestamp.weekday() >= 5:
            days_until_monday = 7 - timestamp.weekday()
            timestamp += timedelta(days=days_until_monday)
        
        # 時間調整
        if timestamp.hour not in active_hours:
            # 最も近いアクティブ時間に調整
            closest_hour = min(active_hours, key=lambda h: abs(h - timestamp.hour))
            timestamp = timestamp.replace(hour=closest_hour)
        
        return timestamp
    
    def _create_trade_info(self, analysis_result, config, trade_time, timeframe):
        """トレード情報を作成"""
        # 基本情報
        leverage = analysis_result.get('leverage', 5.0)
        confidence = analysis_result.get('confidence', 70.0) / 100.0
        current_price = analysis_result.get('current_price')
        
        # TP/SL計算
        from engines.stop_loss_take_profit_calculators import (
            DefaultSLTPCalculator, ConservativeSLTPCalculator, AggressiveSLTPCalculator
        )
        from interfaces.data_types import MarketContext
        
        # 戦略に応じた計算器選択
        if 'Conservative' in config:
            sltp_calculator = ConservativeSLTPCalculator()
        elif 'Aggressive' in config:
            sltp_calculator = AggressiveSLTPCalculator()
        else:
            sltp_calculator = DefaultSLTPCalculator()
        
        # 市場コンテキスト
        market_context = MarketContext(
            current_price=current_price,
            volume_24h=1000000.0,
            volatility=self._get_volatility_by_timeframe(timeframe),
            trend_direction='BULLISH',
            market_phase='MARKUP',
            timestamp=trade_time
        )
        
        # TP/SL計算
        sltp_levels = sltp_calculator.calculate_levels(
            current_price=current_price,
            leverage=leverage,
            support_levels=[],
            resistance_levels=[],
            market_context=market_context
        )
        
        # 結果判定
        is_success = np.random.random() < (confidence * 0.8 + 0.2)
        
        if is_success:
            exit_price = sltp_levels.take_profit_price * np.random.uniform(0.98, 1.02)
            pnl_pct = (exit_price - current_price) / current_price
        else:
            exit_price = sltp_levels.stop_loss_price * np.random.uniform(0.98, 1.02)
            pnl_pct = (exit_price - current_price) / current_price
        
        leveraged_pnl = pnl_pct * leverage
        
        # 退出時間の計算（時間足に応じて調整）
        exit_minutes = self._get_exit_minutes_by_timeframe(timeframe)
        exit_time = trade_time + timedelta(minutes=np.random.randint(*exit_minutes))
        
        # 日本時間で返す
        jst_entry = trade_time + timedelta(hours=9)
        jst_exit = exit_time + timedelta(hours=9)
        
        return {
            'entry_time': jst_entry.strftime('%Y-%m-%d %H:%M:%S JST'),
            'exit_time': jst_exit.strftime('%Y-%m-%d %H:%M:%S JST'),
            'entry_price': current_price,
            'exit_price': exit_price,
            'take_profit_price': sltp_levels.take_profit_price,
            'stop_loss_price': sltp_levels.stop_loss_price,
            'leverage': leverage,
            'pnl_pct': leveraged_pnl,
            'confidence': confidence,
            'is_success': is_success,
            'strategy': config,
            'timeframe': timeframe
        }
    
    def _get_volatility_by_timeframe(self, timeframe):
        """時間足に応じたボラティリティを取得"""
        volatility_map = {
            '1m': 0.001,   # 0.1%
            '3m': 0.002,   # 0.2%
            '5m': 0.003,   # 0.3%
            '15m': 0.005,  # 0.5%
            '30m': 0.008,  # 0.8%
            '1h': 0.01     # 1.0%
        }
        return volatility_map.get(timeframe, 0.01)
    
    def _get_exit_minutes_by_timeframe(self, timeframe):
        """時間足に応じた退出時間範囲を取得"""
        exit_ranges = {
            '1m': (2, 10),      # 2-10分
            '3m': (5, 20),      # 5-20分
            '5m': (10, 30),     # 10-30分
            '15m': (20, 60),    # 20-60分
            '30m': (40, 120),   # 40-120分
            '1h': (60, 240)     # 60-240分
        }
        return exit_ranges.get(timeframe, (30, 120))
    
    def _get_exchange_from_config(self, config) -> str:
        """設定から取引所を取得"""
        import json
        import os
        
        try:
            if os.path.exists('exchange_config.json'):
                with open('exchange_config.json', 'r') as f:
                    exchange_config = json.load(f)
                    return exchange_config.get('default_exchange', 'hyperliquid').lower()
        except Exception as e:
            logger.warning(f"Failed to load exchange config: {e}")
        
        return 'hyperliquid'
    
    def generate_batch_analysis(self, batch_configs, max_workers=None):
        """バッチ分析の実行（改善版）"""
        if max_workers is None:
            max_workers = min(cpu_count(), 4)
        
        logger.info(f"改善版バッチ分析開始: {len(batch_configs)}パターン, {max_workers}並列")
        
        # 時間足でグループ化
        timeframe_groups = {}
        for config in batch_configs:
            tf = config.get('timeframe', '1h')
            if tf not in timeframe_groups:
                timeframe_groups[tf] = []
            timeframe_groups[tf].append(config)
        
        # 時間足別の処理状況を表示
        print("\n時間足別の分析予定:")
        for tf, configs in timeframe_groups.items():
            tf_config = self.get_timeframe_config(tf)
            print(f"  {tf}: {len(configs)}パターン "
                  f"(データ{tf_config['data_days']}日, "
                  f"{tf_config['trades_per_day']}trades/日)")
        
        # 元のシステムと同様の並列処理
        chunk_size = max(1, len(batch_configs) // max_workers)
        chunks = [batch_configs[i:i + chunk_size] 
                 for i in range(0, len(batch_configs), chunk_size)]
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i, chunk in enumerate(chunks):
                future = executor.submit(self._process_chunk, chunk, i)
                futures.append(future)
            
            total_processed = 0
            for i, future in enumerate(futures):
                try:
                    processed_count = future.result(timeout=1800)
                    total_processed += processed_count
                    logger.info(f"チャンク {i+1}/{len(futures)} 完了: "
                              f"{processed_count}パターン処理")
                except Exception as e:
                    logger.error(f"チャンク {i+1} 処理エラー: {e}")
        
        logger.info(f"改善版バッチ分析完了: {total_processed}パターン処理完了")
        return total_processed
    
    def _process_chunk(self, configs_chunk, chunk_id):
        """チャンクを処理（改善版）"""
        import time
        import random
        
        time.sleep(random.uniform(0.1, 0.5))
        
        processed = 0
        for config in configs_chunk:
            try:
                if not isinstance(config, dict):
                    logger.error(f"Config is not a dict: {type(config)} - {config}")
                    continue
                
                strategy = config.get('strategy', config.get('config', 'Default'))
                
                if 'symbol' not in config or 'timeframe' not in config:
                    logger.error(f"Missing required keys in config: {config}")
                    continue
                
                result = self._generate_single_analysis(
                    config['symbol'], 
                    config['timeframe'], 
                    strategy
                )
                if result:
                    processed += 1
                    if processed % 10 == 0:
                        logger.info(f"Chunk {chunk_id}: {processed}/{len(configs_chunk)} 完了")
            except Exception as e:
                logger.error(f"分析エラー {config}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        return processed
    
    def _generate_single_analysis(self, symbol, timeframe, config):
        """単一の分析を生成（改善版）"""
        analysis_id = f"{symbol}_{timeframe}_{config}"
        
        if self._analysis_exists(analysis_id):
            return False
        
        try:
            # 改善版のトレード生成
            trades_data = self._generate_real_analysis(symbol, timeframe, config)
        except Exception as e:
            logger.error(f"Analysis failed for {symbol} {timeframe} {config}: {e}")
            return False
        
        # メトリクス計算
        metrics = self._calculate_metrics(trades_data)
        
        # 時間足設定を追加
        tf_config = self.get_timeframe_config(timeframe)
        metrics['data_days'] = tf_config['data_days']
        metrics['train_samples'] = int(len(trades_data) * tf_config['train_ratio'])
        metrics['val_samples'] = int(len(trades_data) * tf_config['val_ratio'])
        metrics['test_samples'] = int(len(trades_data) * tf_config['test_ratio'])
        
        # データ保存
        compressed_path = self._save_compressed_data(analysis_id, trades_data)
        
        chart_path = None
        if self._should_generate_chart(metrics):
            chart_path = self._generate_lightweight_chart(analysis_id, trades_data, metrics)
        
        self._save_to_database(symbol, timeframe, config, metrics, chart_path, compressed_path)
        
        return True
    
    # 以下、元のシステムから必要なメソッドをコピー
    def _analysis_exists(self, analysis_id):
        """分析が既に存在するかチェック"""
        symbol, timeframe, config = analysis_id.split('_', 2)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM analyses WHERE symbol=? AND timeframe=? AND config=?',
                (symbol, timeframe, config)
            )
            return cursor.fetchone()[0] > 0
    
    def _calculate_metrics(self, trades_data):
        """メトリクス計算（元のシステムと同じ）"""
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
            
            cumulative_return = 0
            for trade in trades_data:
                cumulative_return += trade['pnl_pct']
                trade['cumulative_return'] = cumulative_return
                trade['is_win'] = trade.get('is_success', trade['pnl_pct'] > 0)
            
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
        win_rate = trades_df['is_win'].mean() if len(trades_df) > 0 else 0
        
        returns = trades_df['pnl_pct'].values
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        cum_returns = trades_df['cumulative_return'].values
        peak = np.maximum.accumulate(cum_returns)
        drawdown = (cum_returns - peak) / peak
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        return {
            'total_trades': len(trades_df),
            'total_return': total_return,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_leverage': trades_df['leverage'].mean() if len(trades_df) > 0 else 0
        }
    
    def _save_compressed_data(self, analysis_id, trades_df):
        """データを圧縮して保存"""
        compressed_path = self.compressed_dir / f"{analysis_id}.pkl.gz"
        
        with gzip.open(compressed_path, 'wb') as f:
            pickle.dump(trades_df, f)
        
        return str(compressed_path)
    
    def _should_generate_chart(self, metrics):
        """チャート生成が必要かどうか判定"""
        return metrics['sharpe_ratio'] > 1.5
    
    def _generate_lightweight_chart(self, analysis_id, trades_df, metrics):
        """軽量版チャート生成"""
        chart_path = self.charts_dir / f"{analysis_id}_chart.html"
        
        html_content = f"""
        <html>
        <head><title>{analysis_id} Analysis</title></head>
        <body>
        <h1>{analysis_id}</h1>
        <p>Sharpe Ratio: {metrics['sharpe_ratio']:.2f}</p>
        <p>Win Rate: {metrics['win_rate']:.1%}</p>
        <p>Total Return: {metrics['total_return']:.1%}</p>
        <p>Data Days: {metrics.get('data_days', 'N/A')}</p>
        <p>Train/Val/Test: {metrics.get('train_samples', 'N/A')}/{metrics.get('val_samples', 'N/A')}/{metrics.get('test_samples', 'N/A')}</p>
        </body>
        </html>
        """
        
        with open(chart_path, 'w') as f:
            f.write(html_content)
        
        return str(chart_path)
    
    def _save_to_database(self, symbol, timeframe, config, metrics, chart_path, compressed_path):
        """データベースに保存（改善版）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analyses 
                (symbol, timeframe, config, total_trades, win_rate, total_return, 
                 sharpe_ratio, max_drawdown, avg_leverage, chart_path, data_compressed_path, 
                 status, data_days, train_samples, val_samples, test_samples)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?)
            ''', (
                symbol, timeframe, config,
                metrics['total_trades'], metrics['win_rate'], metrics['total_return'],
                metrics['sharpe_ratio'], metrics['max_drawdown'], metrics['avg_leverage'],
                chart_path, compressed_path,
                metrics.get('data_days'), metrics.get('train_samples'),
                metrics.get('val_samples'), metrics.get('test_samples')
            ))
            
            conn.commit()


def generate_improved_configs(symbols=None, timeframes=None, strategies=None):
    """改善版の設定生成"""
    if symbols is None:
        symbols = ['HYPE', 'SOL', 'BTC', 'ETH', 'WIF']
    
    if timeframes is None:
        timeframes = ['1m', '3m', '5m', '15m', '30m', '1h']
    
    if strategies is None:
        strategies = ['Conservative_ML', 'Aggressive_ML', 'Balanced']
    
    configs = []
    for symbol in symbols:
        for timeframe in timeframes:
            for strategy in strategies:
                configs.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'strategy': strategy
                })
    
    return configs


def main():
    """改善版システムのデモ"""
    print("=" * 80)
    print("改善版大規模分析システム - 時間足別最適化")
    print("=" * 80)
    
    system = ImprovedScalableAnalysisSystem()
    
    # テスト用の設定生成
    configs = generate_improved_configs(
        symbols=['HYPE', 'SOL'], 
        timeframes=['5m', '15m', '1h'],
        strategies=['Conservative_ML', 'Aggressive_ML']
    )
    
    print(f"\n生成された設定数: {len(configs)}")
    
    # バッチ分析実行
    processed = system.generate_batch_analysis(configs, max_workers=2)
    print(f"\n処理完了: {processed}パターン")
    
    # 統計表示
    stats = system.get_statistics()
    if stats and 'performance' in stats:
        print("\n統計:")
        print(f"  総分析数: {stats['performance']['total_analyses']}")
        print(f"  平均Sharpe: {stats['performance']['avg_sharpe']:.2f}")
        print(f"  最高Sharpe: {stats['performance']['max_sharpe']:.2f}")


if __name__ == "__main__":
    main()