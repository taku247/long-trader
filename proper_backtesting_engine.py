"""
Proper Backtesting Engine with Time Series Split
Implements realistic backtesting with proper train-test separation
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import warnings
from pathlib import Path
import logging

# Import our custom modules
from time_series_backtest import TimeSeriesBacktester
from extended_data_fetcher import ExtendedDataFetcher
from walk_forward_engine import WalkForwardEngine

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProperBacktestingEngine:
    """
    Complete backtesting engine with proper time series methodology
    """
    
    def __init__(self, 
                 results_dir: str = "proper_backtest_results",
                 cache_dir: str = "data_cache",
                 exchange: str = None):
        """
        Initialize the backtesting engine
        
        Args:
            results_dir: Directory to store results
            cache_dir: Directory to cache data
            exchange: Exchange to use ('hyperliquid' or 'gateio'). If None, uses config file
        """
        self.results_dir = Path(results_dir)
        self.cache_dir = Path(cache_dir)
        
        # Create directories
        self.results_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Set exchange
        self.exchange = self._determine_exchange(exchange)
        
        # Initialize components with exchange
        self.data_fetcher = ExtendedDataFetcher(exchange=self.exchange)
        self.ts_backtester = TimeSeriesBacktester()
        self.walk_forward_engine = WalkForwardEngine()
        
        # Configuration storage
        self.strategy_configs = self._load_default_strategies()
        self.supported_symbols = self._get_supported_symbols()
        self.supported_timeframes = ['5m', '15m', '30m', '1h']
        
        logger.info(f"Proper Backtesting Engine initialized with {self.exchange}")
    
    def _determine_exchange(self, exchange: str = None) -> str:
        """取引所を決定（設定ファイル優先）"""
        import json
        import os
        
        # 1. 引数で指定された場合
        if exchange:
            return exchange.lower()
        
        # 2. 設定ファイルから読み込み
        try:
            if os.path.exists('exchange_config.json'):
                with open('exchange_config.json', 'r') as f:
                    config = json.load(f)
                    return config.get('default_exchange', 'hyperliquid').lower()
        except Exception as e:
            logger.warning(f"Failed to load exchange config: {e}")
        
        # 3. 環境変数から読み込み
        env_exchange = os.getenv('EXCHANGE_TYPE', '').lower()
        if env_exchange in ['hyperliquid', 'gateio']:
            return env_exchange
        
        # 4. デフォルト: Hyperliquid
        return 'hyperliquid'
    
    def _get_supported_symbols(self) -> List[str]:
        """取引所に応じたサポート銘柄を取得"""
        if self.exchange == 'gateio':
            # Gate.ioで確実に利用可能な銘柄
            return ['BTC', 'ETH', 'SOL', 'AVAX', 'DOGE', 'LINK', 'UNI', 'AAVE', 'MATIC']
        else:
            # Hyperliquid
            return ['HYPE', 'SOL', 'BTC', 'ETH', 'BONK', 'WIF', 'PEPE']
    
    def _load_default_strategies(self) -> Dict[str, Dict[str, Any]]:
        """
        Load default strategy configurations
        """
        return {
            'ML_Conservative': {
                'ml_threshold': 0.015,
                'base_leverage': 1.5,
                'max_leverage': 3.0,
                'stop_loss': 0.03,
                'take_profit': 0.06,
                'min_confidence': 0.3,
                'risk_management': 'conservative'
            },
            'ML_Aggressive': {
                'ml_threshold': 0.01,
                'base_leverage': 3.0,
                'max_leverage': 8.0,
                'stop_loss': 0.05,
                'take_profit': 0.10,
                'min_confidence': 0.2,
                'risk_management': 'aggressive'
            },
            'Hybrid_Balanced': {
                'ml_threshold': 0.012,
                'base_leverage': 2.0,
                'max_leverage': 5.0,
                'stop_loss': 0.04,
                'take_profit': 0.08,
                'min_confidence': 0.25,
                'risk_management': 'balanced',
                'use_sr_levels': True
            },
            'Traditional_TA': {
                'ml_threshold': 0,  # No ML signals
                'base_leverage': 1.0,
                'max_leverage': 2.0,
                'stop_loss': 0.02,
                'take_profit': 0.04,
                'min_confidence': 0.4,
                'risk_management': 'traditional',
                'use_sr_levels': True,
                'use_traditional_signals': True
            }
        }
    
    def get_cached_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Get cached data if available and recent
        """
        cache_file = self.cache_dir / f"{symbol.lower()}_{timeframe}_extended.pkl"
        
        if cache_file.exists():
            try:
                # Check file age
                file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_age.total_seconds() < 3600:  # 1 hour cache
                    logger.info(f"Using cached data for {symbol} {timeframe}")
                    return pd.read_pickle(cache_file)
            except Exception as e:
                logger.warning(f"Failed to load cached data: {e}")
        
        return None
    
    def cache_data(self, data: pd.DataFrame, symbol: str, timeframe: str) -> None:
        """
        Cache data for future use
        """
        try:
            cache_file = self.cache_dir / f"{symbol.lower()}_{timeframe}_extended.pkl"
            data.to_pickle(cache_file)
            logger.info(f"Data cached for {symbol} {timeframe}")
        except Exception as e:
            logger.warning(f"Failed to cache data: {e}")
    
    def prepare_data_for_backtesting(self, 
                                   symbol: str, 
                                   timeframe: str,
                                   force_refresh: bool = False) -> pd.DataFrame:
        """
        Prepare data for backtesting with proper time series methodology
        
        Args:
            symbol: Trading symbol
            timeframe: Time interval
            force_refresh: Force data refresh
            
        Returns:
            Prepared DataFrame with features
        """
        logger.info(f"Preparing data for {symbol} {timeframe}")
        
        # Check cache first
        if not force_refresh:
            cached_data = self.get_cached_data(symbol, timeframe)
            if cached_data is not None:
                return cached_data
        
        # Fetch fresh data
        try:
            # Get raw OHLCV data
            raw_data = self.data_fetcher.fetch_extended_data(symbol, timeframe)
            
            # Calculate comprehensive indicators
            full_data = self.data_fetcher.calculate_comprehensive_indicators(raw_data)
            
            # Feature engineering for ML
            engineered_data = self._engineer_features(full_data)
            
            # Cache the data
            self.cache_data(engineered_data, symbol, timeframe)
            
            logger.info(f"Data preparation complete: {len(engineered_data)} samples, {len(engineered_data.columns)} features")
            return engineered_data
            
        except Exception as e:
            logger.error(f"Data preparation failed: {e}")
            raise
    
    def _engineer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Additional feature engineering for ML models
        """
        df = data.copy()
        
        # Lag features for time series
        for lag in [1, 2, 3, 5, 10]:
            df[f'close_lag_{lag}'] = df['close'].shift(lag)
            df[f'volume_lag_{lag}'] = df['volume'].shift(lag)
            df[f'returns_lag_{lag}'] = df['returns'].shift(lag)
        
        # Rolling features
        windows = [5, 10, 20, 50]
        for window in windows:
            # Price features
            df[f'close_ma_{window}'] = df['close'].rolling(window).mean()
            df[f'close_std_{window}'] = df['close'].rolling(window).std()
            df[f'close_skew_{window}'] = df['close'].rolling(window).skew()
            df[f'close_kurt_{window}'] = df['close'].rolling(window).kurt()
            
            # Volume features
            df[f'volume_ma_{window}'] = df['volume'].rolling(window).mean()
            df[f'volume_std_{window}'] = df['volume'].rolling(window).std()
            
            # Returns features
            if 'returns' in df.columns:
                df[f'returns_ma_{window}'] = df['returns'].rolling(window).mean()
                df[f'returns_std_{window}'] = df['returns'].rolling(window).std()
        
        # Price ratios and relationships
        df['high_close_ratio'] = df['high'] / df['close']
        df['low_close_ratio'] = df['low'] / df['close']
        df['open_close_ratio'] = df['open'] / df['close']
        
        # Volume relationships
        df['volume_price_trend'] = df['volume'] * np.sign(df['returns'])
        df['volume_sma_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # Technical indicator relationships
        if all(col in df.columns for col in ['bb_upper', 'bb_lower', 'bb_middle']):
            df['bb_squeeze'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # RSI features
        if 'rsi_14' in df.columns:
            df['rsi_overbought'] = (df['rsi_14'] > 70).astype(int)
            df['rsi_oversold'] = (df['rsi_14'] < 30).astype(int)
            df['rsi_neutral'] = ((df['rsi_14'] >= 40) & (df['rsi_14'] <= 60)).astype(int)
        
        # MACD features
        if all(col in df.columns for col in ['macd', 'macd_signal']):
            df['macd_crossover'] = ((df['macd'] > df['macd_signal']) & 
                                   (df['macd'].shift(1) <= df['macd_signal'].shift(1))).astype(int)
            df['macd_crossunder'] = ((df['macd'] < df['macd_signal']) & 
                                    (df['macd'].shift(1) >= df['macd_signal'].shift(1))).astype(int)
        
        # Support/Resistance proximity
        if all(col in df.columns for col in ['s1', 's2', 'r1', 'r2']):
            df['near_support'] = (abs(df['close'] - df['s1']) / df['close'] < 0.02).astype(int)
            df['near_resistance'] = (abs(df['close'] - df['r1']) / df['close'] < 0.02).astype(int)
        
        # Clean up infinite and NaN values
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(method='ffill').fillna(0)
        
        return df
    
    def select_features(self, data: pd.DataFrame, 
                       correlation_threshold: float = 0.95,
                       min_importance_percentile: float = 20) -> List[str]:
        """
        Select relevant features for ML models
        
        Args:
            data: DataFrame with features
            correlation_threshold: Threshold for correlation-based filtering
            min_importance_percentile: Minimum importance percentile to keep
            
        Returns:
            List of selected feature names
        """
        logger.info("Selecting features for ML models")
        
        # Exclude non-feature columns
        exclude_cols = [
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'trades',
            'returns', 'log_returns'
        ]
        
        # Get potential feature columns
        feature_candidates = [col for col in data.columns if col not in exclude_cols]
        
        # Remove highly correlated features
        correlation_matrix = data[feature_candidates].corr().abs()
        
        # Find pairs of highly correlated features
        high_corr_pairs = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                if correlation_matrix.iloc[i, j] > correlation_threshold:
                    high_corr_pairs.append((
                        correlation_matrix.columns[i],
                        correlation_matrix.columns[j],
                        correlation_matrix.iloc[i, j]
                    ))
        
        # Remove one feature from each highly correlated pair
        features_to_remove = set()
        for feat1, feat2, corr in high_corr_pairs:
            if feat1 not in features_to_remove:
                features_to_remove.add(feat2)
        
        remaining_features = [f for f in feature_candidates if f not in features_to_remove]
        
        logger.info(f"Feature selection: {len(feature_candidates)} -> {len(remaining_features)} (removed {len(features_to_remove)} correlated)")
        
        # TODO: Add importance-based filtering using a quick model
        # For now, return the correlation-filtered features
        
        return remaining_features
    
    def run_single_backtest(self, 
                          symbol: str,
                          timeframe: str,
                          strategy_name: str,
                          data: Optional[pd.DataFrame] = None,
                          use_walk_forward: bool = True) -> Dict[str, Any]:
        """
        Run a single backtest with proper methodology
        
        Args:
            symbol: Trading symbol
            timeframe: Time interval
            strategy_name: Strategy configuration name
            data: Pre-loaded data (optional)
            use_walk_forward: Whether to use walk-forward analysis
            
        Returns:
            Backtest results
        """
        logger.info(f"Running backtest: {symbol} {timeframe} {strategy_name}")
        
        # Get strategy configuration
        if strategy_name not in self.strategy_configs:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        strategy_config = self.strategy_configs[strategy_name].copy()
        
        # Prepare data
        if data is None:
            data = self.prepare_data_for_backtesting(symbol, timeframe)
        
        # Select features
        feature_columns = self.select_features(data)
        
        # Create target variable for ML
        target_data = data.copy()
        target_data['target'] = target_data['close'].pct_change(1).shift(-1)  # Next period return
        
        # Remove rows with NaN target
        valid_data = target_data.dropna(subset=['target'])
        
        if len(valid_data) < 1000:
            return {'error': f'Insufficient data: {len(valid_data)} samples'}
        
        logger.info(f"Data prepared: {len(valid_data)} samples, {len(feature_columns)} features")
        
        # Choose analysis method
        if use_walk_forward and len(valid_data) >= 2000:
            # Walk-forward analysis for large datasets
            results = self._run_walk_forward_backtest(
                valid_data, feature_columns, strategy_config, symbol, timeframe, strategy_name
            )
        else:
            # Simple train-test split for smaller datasets
            results = self._run_simple_backtest(
                valid_data, feature_columns, strategy_config, symbol, timeframe, strategy_name
            )
        
        # Add metadata
        results.update({
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy_name': strategy_name,
            'data_samples': len(valid_data),
            'feature_count': len(feature_columns),
            'backtest_date': datetime.now().isoformat(),
            'methodology': 'walk_forward' if use_walk_forward else 'simple_split'
        })
        
        return results
    
    def _run_walk_forward_backtest(self, 
                                 data: pd.DataFrame,
                                 feature_columns: List[str],
                                 strategy_config: Dict[str, Any],
                                 symbol: str,
                                 timeframe: str,
                                 strategy_name: str) -> Dict[str, Any]:
        """
        Run walk-forward backtest
        """
        logger.info("Running walk-forward analysis")
        
        # Configure walk-forward engine
        n_samples = len(data)
        window_size = min(1500, n_samples // 3)  # Adaptive window size
        step_size = max(50, window_size // 10)   # 10% step size
        
        wf_engine = WalkForwardEngine(
            window_size=window_size,
            step_size=step_size,
            min_train_size=max(500, window_size // 3),
            validation_size=max(100, window_size // 10),
            n_splits=3
        )
        
        # Model parameters
        model_params = {
            'type': 'lightgbm',
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'random_state': 42
        }
        
        # Run walk-forward analysis
        wf_results = wf_engine.run_walk_forward_analysis(
            data=data,
            feature_columns=feature_columns,
            target_column='target',
            model_params=model_params,
            strategy_config=strategy_config,
            optimize_params=False  # Set to True for parameter optimization
        )
        
        if 'error' in wf_results:
            return wf_results
        
        # Convert to trading results
        trading_results = self._convert_predictions_to_trades(
            wf_results['predictions'], strategy_config, data
        )
        
        # Combine results
        results = {
            'walk_forward_results': wf_results,
            'trading_results': trading_results,
            'performance_metrics': wf_results.get('performance_summary', {}),
            'stability_metrics': wf_results.get('stability_metrics', {})
        }
        
        return results
    
    def _run_simple_backtest(self, 
                           data: pd.DataFrame,
                           feature_columns: List[str],
                           strategy_config: Dict[str, Any],
                           symbol: str,
                           timeframe: str,
                           strategy_name: str) -> Dict[str, Any]:
        """
        Run simple train-test split backtest
        """
        logger.info("Running simple train-test split backtest")
        
        # Use TimeSeriesBacktester
        backtest_results = self.ts_backtester.backtest_strategy(
            data=data,
            feature_columns=feature_columns,
            strategy_config=strategy_config
        )
        
        return {
            'simple_backtest_results': backtest_results,
            'performance_metrics': backtest_results,
            'methodology': 'simple_split'
        }
    
    def _convert_predictions_to_trades(self, 
                                     predictions_df: pd.DataFrame,
                                     strategy_config: Dict[str, Any],
                                     original_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Convert ML predictions to trading signals and calculate returns
        """
        if predictions_df.empty:
            return {'error': 'No predictions available'}
        
        # Merge predictions with price data
        if 'timestamp' in original_data.columns:
            price_data = original_data[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            price_data['timestamp'] = pd.to_datetime(price_data['timestamp'])
            predictions_df['date'] = pd.to_datetime(predictions_df['date'])
            
            merged = pd.merge(predictions_df, price_data, left_on='date', right_on='timestamp', how='inner')
        else:
            merged = predictions_df.copy()
            merged['close'] = original_data['close'].iloc[:len(merged)]
        
        if merged.empty:
            return {'error': 'Unable to merge predictions with price data'}
        
        # Generate trading signals
        threshold = strategy_config.get('ml_threshold', 0.01)
        min_confidence = strategy_config.get('min_confidence', 0.2)
        
        signals = []
        position = 0
        entry_price = 0
        trades = []
        
        for i, row in merged.iterrows():
            signal = 0
            confidence = abs(row['predicted'])
            
            # Generate signal based on prediction and confidence
            if row['predicted'] > threshold and confidence > min_confidence:
                signal = 1  # Buy
            elif row['predicted'] < -threshold and confidence > min_confidence:
                signal = -1  # Sell
            
            # Position management
            if position == 0 and signal != 0:
                # Enter position
                position = signal
                entry_price = row['close']
                entry_date = row['date']
                
                # Calculate dynamic leverage
                base_leverage = strategy_config.get('base_leverage', 2.0)
                max_leverage = strategy_config.get('max_leverage', 5.0)
                leverage = min(base_leverage * (1 + confidence), max_leverage)
                
            elif position != 0:
                # Check exit conditions
                current_return = (row['close'] - entry_price) / entry_price
                position_return = position * current_return * leverage
                
                stop_loss = strategy_config.get('stop_loss', 0.05)
                take_profit = strategy_config.get('take_profit', 0.10)
                
                exit_signal = False
                exit_reason = ""
                
                # Stop loss / take profit
                if position_return <= -stop_loss:
                    exit_signal = True
                    exit_reason = "stop_loss"
                elif position_return >= take_profit:
                    exit_signal = True
                    exit_reason = "take_profit"
                # Opposite signal
                elif (position > 0 and signal < 0) or (position < 0 and signal > 0):
                    exit_signal = True
                    exit_reason = "signal_change"
                
                if exit_signal:
                    # Record trade
                    trade = {
                        'entry_date': entry_date,
                        'exit_date': row['date'],
                        'entry_price': entry_price,
                        'exit_price': row['close'],
                        'position': position,
                        'leverage': leverage,
                        'return': position_return,
                        'exit_reason': exit_reason,
                        'confidence': confidence
                    }
                    trades.append(trade)
                    
                    # Reset position
                    position = 0
                    entry_price = 0
            
            signals.append({
                'date': row['date'],
                'price': row['close'],
                'predicted': row['predicted'],
                'signal': signal,
                'confidence': confidence,
                'position': position
            })
        
        # Calculate performance metrics
        if trades:
            returns = [t['return'] for t in trades]
            
            trading_metrics = {
                'total_trades': len(trades),
                'winning_trades': sum(1 for r in returns if r > 0),
                'losing_trades': sum(1 for r in returns if r <= 0),
                'win_rate': sum(1 for r in returns if r > 0) / len(returns),
                'total_return': sum(returns),
                'avg_return': np.mean(returns),
                'std_return': np.std(returns),
                'max_return': max(returns),
                'min_return': min(returns),
                'sharpe_ratio': np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            }
            
            # Calculate max drawdown
            cumulative_returns = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = cumulative_returns - running_max
            trading_metrics['max_drawdown'] = np.min(drawdown)
            
        else:
            trading_metrics = {'error': 'No trades generated'}
        
        return {
            'signals': signals,
            'trades': trades,
            'metrics': trading_metrics
        }
    
    def run_comprehensive_backtest(self, 
                                 symbols: Optional[List[str]] = None,
                                 timeframes: Optional[List[str]] = None,
                                 strategies: Optional[List[str]] = None,
                                 max_workers: int = 4) -> Dict[str, Any]:
        """
        Run comprehensive backtest across multiple parameters
        
        Args:
            symbols: List of symbols to test
            timeframes: List of timeframes to test
            strategies: List of strategies to test
            max_workers: Maximum number of parallel workers
            
        Returns:
            Comprehensive backtest results
        """
        symbols = symbols or ['HYPE', 'SOL']  # Subset for testing
        timeframes = timeframes or ['15m', '1h']
        strategies = strategies or ['ML_Conservative', 'ML_Aggressive']
        
        logger.info(f"Starting comprehensive backtest")
        logger.info(f"Symbols: {symbols}")
        logger.info(f"Timeframes: {timeframes}")
        logger.info(f"Strategies: {strategies}")
        
        # Generate all combinations
        test_combinations = []
        for symbol in symbols:
            for timeframe in timeframes:
                for strategy in strategies:
                    test_combinations.append((symbol, timeframe, strategy))
        
        logger.info(f"Total combinations: {len(test_combinations)}")
        
        # Run backtests
        results = {}
        failed_tests = []
        
        for i, (symbol, timeframe, strategy) in enumerate(test_combinations):
            try:
                logger.info(f"Progress: {i+1}/{len(test_combinations)} - {symbol} {timeframe} {strategy}")
                
                result = self.run_single_backtest(symbol, timeframe, strategy)
                
                test_key = f"{symbol}_{timeframe}_{strategy}"
                results[test_key] = result
                
                # Save individual result
                self.save_backtest_result(result, test_key)
                
            except Exception as e:
                logger.error(f"Failed: {symbol} {timeframe} {strategy} - {e}")
                failed_tests.append((symbol, timeframe, strategy, str(e)))
                continue
        
        # Generate summary
        summary = self._generate_summary(results)
        
        comprehensive_results = {
            'individual_results': results,
            'summary': summary,
            'failed_tests': failed_tests,
            'test_combinations': test_combinations,
            'test_date': datetime.now().isoformat()
        }
        
        # Save comprehensive results
        self.save_comprehensive_results(comprehensive_results)
        
        logger.info(f"Comprehensive backtest completed: {len(results)} successful, {len(failed_tests)} failed")
        
        return comprehensive_results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary statistics from individual results
        """
        if not results:
            return {'error': 'No results to summarize'}
        
        summary_data = []
        
        for test_key, result in results.items():
            if 'error' in result:
                continue
            
            # Extract key metrics
            metrics = {}
            
            # Get performance metrics from different result types
            if 'trading_results' in result and 'metrics' in result['trading_results']:
                metrics = result['trading_results']['metrics']
            elif 'performance_metrics' in result:
                metrics = result['performance_metrics']
            
            if metrics and 'error' not in metrics:
                summary_row = {
                    'test_key': test_key,
                    'symbol': result.get('symbol', ''),
                    'timeframe': result.get('timeframe', ''),
                    'strategy': result.get('strategy_name', ''),
                    'total_trades': metrics.get('total_trades', 0),
                    'win_rate': metrics.get('win_rate', 0),
                    'total_return': metrics.get('total_return', 0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                    'max_drawdown': metrics.get('max_drawdown', 0),
                    'avg_return': metrics.get('avg_return', 0)
                }
                summary_data.append(summary_row)
        
        if not summary_data:
            return {'error': 'No valid results to summarize'}
        
        summary_df = pd.DataFrame(summary_data)
        
        # Generate aggregate statistics
        summary_stats = {
            'total_tests': len(summary_data),
            'avg_win_rate': summary_df['win_rate'].mean(),
            'avg_total_return': summary_df['total_return'].mean(),
            'avg_sharpe_ratio': summary_df['sharpe_ratio'].mean(),
            'best_strategy': summary_df.loc[summary_df['total_return'].idxmax()]['test_key'],
            'best_return': summary_df['total_return'].max(),
            'worst_return': summary_df['total_return'].min(),
            'by_symbol': summary_df.groupby('symbol')['total_return'].mean().to_dict(),
            'by_timeframe': summary_df.groupby('timeframe')['total_return'].mean().to_dict(),
            'by_strategy': summary_df.groupby('strategy')['total_return'].mean().to_dict()
        }
        
        return {
            'stats': summary_stats,
            'detailed_results': summary_data
        }
    
    def save_backtest_result(self, result: Dict[str, Any], test_key: str) -> None:
        """
        Save individual backtest result
        """
        try:
            filename = self.results_dir / f"{test_key}_result.json"
            
            # Prepare for JSON serialization
            serializable_result = self._make_json_serializable(result)
            
            with open(filename, 'w') as f:
                json.dump(serializable_result, f, indent=2, default=str)
            
            logger.info(f"Result saved: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save result {test_key}: {e}")
    
    def save_comprehensive_results(self, results: Dict[str, Any]) -> None:
        """
        Save comprehensive backtest results
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.results_dir / f"comprehensive_backtest_{timestamp}.json"
            
            # Prepare for JSON serialization
            serializable_results = self._make_json_serializable(results)
            
            with open(filename, 'w') as f:
                json.dump(serializable_results, f, indent=2, default=str)
            
            logger.info(f"Comprehensive results saved: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save comprehensive results: {e}")
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """
        Make object JSON serializable
        """
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict('records')
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif pd.isna(obj):
            return None
        else:
            return obj


def main():
    """
    Example usage of ProperBacktestingEngine
    """
    print("Proper Backtesting Engine with Time Series Methodology")
    print("=" * 60)
    
    # Initialize engine
    engine = ProperBacktestingEngine()
    
    print("✅ Engine initialized")
    print(f"📊 Supported symbols: {engine.supported_symbols}")
    print(f"⏰ Supported timeframes: {engine.supported_timeframes}")
    print(f"🎯 Available strategies: {list(engine.strategy_configs.keys())}")
    
    # Example: Run a single backtest
    try:
        print(f"\n🧪 Running example backtest...")
        result = engine.run_single_backtest(
            symbol='HYPE',
            timeframe='1h',
            strategy_name='ML_Conservative'
        )
        
        if 'error' not in result:
            print(f"✅ Backtest completed successfully")
            print(f"📊 Data samples: {result['data_samples']}")
            print(f"🔧 Features used: {result['feature_count']}")
            print(f"📅 Method: {result['methodology']}")
        else:
            print(f"❌ Backtest failed: {result['error']}")
    
    except Exception as e:
        print(f"❌ Example failed: {e}")
    
    print(f"\n🎯 Ready for comprehensive backtesting!")
    print(f"💡 Use engine.run_comprehensive_backtest() for full analysis")


if __name__ == "__main__":
    main()