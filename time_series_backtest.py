"""
Time Series Backtesting System with Proper Train-Test Split
Prevents look-ahead bias and implements realistic backtesting
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

class TimeSeriesBacktester:
    """
    Implements proper time series backtesting with train-test separation
    """
    
    def __init__(self, 
                 train_ratio: float = 0.6,
                 validation_ratio: float = 0.2,
                 test_ratio: float = 0.2,
                 walk_forward_steps: int = 5,
                 min_train_samples: int = 100):
        """
        Initialize the backtester
        
        Args:
            train_ratio: Portion of data for training
            validation_ratio: Portion of data for validation
            test_ratio: Portion of data for testing
            walk_forward_steps: Number of walk-forward analysis steps
            min_train_samples: Minimum samples needed for training
        """
        self.train_ratio = train_ratio
        self.validation_ratio = validation_ratio
        self.test_ratio = test_ratio
        self.walk_forward_steps = walk_forward_steps
        self.min_train_samples = min_train_samples
        
        # Ensure ratios sum to 1
        total = train_ratio + validation_ratio + test_ratio
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Ratios must sum to 1.0, got {total}")
        
        # Model and scaler storage
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        
    def get_time_splits(self, data: pd.DataFrame) -> Dict[str, Tuple[int, int]]:
        """
        Calculate time-based splits for train/validation/test
        
        Args:
            data: DataFrame with datetime index or timestamp column
            
        Returns:
            Dictionary with split indices
        """
        n_samples = len(data)
        
        # Calculate split points
        train_end = int(n_samples * self.train_ratio)
        val_end = train_end + int(n_samples * self.validation_ratio)
        
        splits = {
            'train': (0, train_end),
            'validation': (train_end, val_end),
            'test': (val_end, n_samples)
        }
        
        # Ensure minimum training samples
        if train_end < self.min_train_samples:
            raise ValueError(f"Insufficient training data: {train_end} < {self.min_train_samples}")
        
        return splits
    
    def prepare_features(self, data: pd.DataFrame, feature_columns: List[str]) -> pd.DataFrame:
        """
        Prepare features for ML training
        
        Args:
            data: Input DataFrame
            feature_columns: List of feature column names
            
        Returns:
            Cleaned feature DataFrame
        """
        # Select only feature columns
        features = data[feature_columns].copy()
        
        # Handle missing values
        features = features.ffill().bfill()
        
        # Remove infinite values
        features = features.replace([np.inf, -np.inf], np.nan)
        features = features.fillna(0)
        
        return features
    
    def create_ml_target(self, data: pd.DataFrame, 
                        lookahead_periods: int = 1,
                        target_type: str = 'returns') -> pd.Series:
        """
        Create target variable for ML prediction
        
        Args:
            data: Input DataFrame with price data
            lookahead_periods: How many periods ahead to predict
            target_type: 'returns', 'price', or 'breakout'
            
        Returns:
            Target series
        """
        if target_type == 'returns':
            # Future returns
            target = data['close'].pct_change(lookahead_periods).shift(-lookahead_periods)
        elif target_type == 'price':
            # Future price
            target = data['close'].shift(-lookahead_periods)
        elif target_type == 'breakout':
            # Binary breakout signal
            future_high = data['high'].rolling(lookahead_periods).max().shift(-lookahead_periods)
            current_close = data['close']
            target = (future_high / current_close - 1 > 0.02).astype(int)  # 2% breakout
        else:
            raise ValueError(f"Unknown target_type: {target_type}")
        
        return target
    
    def train_ml_model(self, 
                       features: pd.DataFrame, 
                       target: pd.Series,
                       model_type: str = 'lightgbm') -> Tuple[Any, StandardScaler]:
        """
        Train ML model on training data only
        
        Args:
            features: Feature DataFrame
            target: Target series
            model_type: Type of model to train
            
        Returns:
            Trained model and scaler
        """
        # Remove rows with NaN target
        valid_idx = ~target.isna()
        X = features[valid_idx]
        y = target[valid_idx]
        
        if len(X) < self.min_train_samples:
            raise ValueError(f"Insufficient valid samples: {len(X)}")
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = pd.DataFrame(
            scaler.fit_transform(X),
            columns=X.columns,
            index=X.index
        )
        
        # Train model
        if model_type == 'lightgbm':
            model = lgb.LGBMRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                verbosity=-1,
                force_col_wise=True
            )
        elif model_type == 'random_forest':
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        else:
            raise ValueError(f"Unknown model_type: {model_type}")
        
        model.fit(X_scaled, y)
        
        return model, scaler
    
    def walk_forward_analysis(self, 
                             data: pd.DataFrame,
                             feature_columns: List[str],
                             target_type: str = 'returns') -> Dict[str, Any]:
        """
        Perform walk-forward analysis
        
        Args:
            data: Full dataset
            feature_columns: List of feature columns
            target_type: Type of target variable
            
        Returns:
            Walk-forward analysis results
        """
        results = {
            'predictions': [],
            'actuals': [],
            'dates': [],
            'models': [],
            'performance_by_period': []
        }
        
        n_samples = len(data)
        window_size = n_samples // self.walk_forward_steps
        
        for step in range(self.walk_forward_steps):
            # Define rolling window
            start_idx = step * (window_size // 2)  # Overlapping windows
            train_end = start_idx + int(window_size * 0.7)
            test_start = train_end
            test_end = min(test_start + int(window_size * 0.3), n_samples)
            
            if train_end - start_idx < self.min_train_samples:
                continue
            
            if test_end <= test_start:
                continue
            
            # Split data
            train_data = data.iloc[start_idx:train_end]
            test_data = data.iloc[test_start:test_end]
            
            # Prepare features and target
            X_train = self.prepare_features(train_data, feature_columns)
            X_test = self.prepare_features(test_data, feature_columns)
            
            y_train = self.create_ml_target(train_data, target_type=target_type)
            y_test = self.create_ml_target(test_data, target_type=target_type)
            
            try:
                # Train model
                model, scaler = self.train_ml_model(X_train, y_train)
                
                # Make predictions
                X_test_scaled = pd.DataFrame(
                    scaler.transform(X_test),
                    columns=X_test.columns,
                    index=X_test.index
                )
                
                predictions = model.predict(X_test_scaled)
                
                # Store results
                results['predictions'].extend(predictions)
                results['actuals'].extend(y_test.values)
                results['dates'].extend(test_data.index if hasattr(test_data, 'index') else test_data['timestamp'])
                results['models'].append({
                    'step': step,
                    'train_period': (start_idx, train_end),
                    'test_period': (test_start, test_end),
                    'model': model,
                    'scaler': scaler
                })
                
                # Calculate period performance
                valid_mask = ~np.isnan(y_test.values)
                if np.sum(valid_mask) > 0:
                    period_corr = np.corrcoef(predictions[valid_mask], y_test.values[valid_mask])[0, 1]
                    period_mse = np.mean((predictions[valid_mask] - y_test.values[valid_mask]) ** 2)
                    
                    results['performance_by_period'].append({
                        'step': step,
                        'correlation': period_corr if not np.isnan(period_corr) else 0,
                        'mse': period_mse,
                        'n_samples': np.sum(valid_mask)
                    })
                
            except Exception as e:
                print(f"Walk-forward step {step} failed: {e}")
                continue
        
        return results
    
    def detect_support_resistance_levels(self, 
                                       data: pd.DataFrame,
                                       window: int = 20,
                                       min_strength: int = 3) -> pd.DataFrame:
        """
        Detect support and resistance levels using only past data
        
        Args:
            data: OHLCV data
            window: Rolling window for level detection
            min_strength: Minimum number of touches for valid level
            
        Returns:
            DataFrame with support/resistance levels
        """
        levels = []
        
        for i in range(window, len(data)):
            # Only use data up to current point (no look-ahead)
            current_data = data.iloc[:i+1]
            
            # Find local highs and lows in recent window
            recent_data = current_data.tail(window)
            
            # Resistance levels (local highs)
            high_peaks = recent_data['high'].rolling(5, center=True).max() == recent_data['high']
            resistance_candidates = recent_data.loc[high_peaks, 'high'].values
            
            # Support levels (local lows)
            low_peaks = recent_data['low'].rolling(5, center=True).min() == recent_data['low']
            support_candidates = recent_data.loc[low_peaks, 'low'].values
            
            # Count touches for each level
            for level in resistance_candidates:
                touches = np.sum(np.abs(current_data['high'] - level) / level < 0.01)  # 1% tolerance
                if touches >= min_strength:
                    levels.append({
                        'timestamp': data.index[i] if hasattr(data, 'index') else data.iloc[i]['timestamp'],
                        'level': level,
                        'type': 'resistance',
                        'strength': touches
                    })
            
            for level in support_candidates:
                touches = np.sum(np.abs(current_data['low'] - level) / level < 0.01)  # 1% tolerance
                if touches >= min_strength:
                    levels.append({
                        'timestamp': data.index[i] if hasattr(data, 'index') else data.iloc[i]['timestamp'],
                        'level': level,
                        'type': 'support',
                        'strength': touches
                    })
        
        return pd.DataFrame(levels)
    
    def backtest_strategy(self, 
                         data: pd.DataFrame,
                         feature_columns: List[str],
                         strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Backtest strategy with proper time series split
        
        Args:
            data: Full dataset
            feature_columns: Feature column names
            strategy_config: Strategy configuration
            
        Returns:
            Backtest results
        """
        # Get time splits
        splits = self.get_time_splits(data)
        
        # Split data
        train_data = data.iloc[splits['train'][0]:splits['train'][1]]
        val_data = data.iloc[splits['validation'][0]:splits['validation'][1]]
        test_data = data.iloc[splits['test'][0]:splits['test'][1]]
        
        # Train models only on training data
        print(f"Training period: {len(train_data)} samples")
        print(f"Validation period: {len(val_data)} samples")
        print(f"Test period: {len(test_data)} samples")
        
        # Detect support/resistance only on training data
        sr_levels = self.detect_support_resistance_levels(train_data)
        
        # Train ML model only on training data
        X_train = self.prepare_features(train_data, feature_columns)
        y_train = self.create_ml_target(train_data, target_type='returns')
        
        model, scaler = self.train_ml_model(X_train, y_train)
        
        # Generate signals for validation and test data
        all_signals = []
        all_returns = []
        
        for period_name, period_data in [('validation', val_data), ('test', test_data)]:
            X_period = self.prepare_features(period_data, feature_columns)
            X_period_scaled = pd.DataFrame(
                scaler.transform(X_period),
                columns=X_period.columns,
                index=X_period.index
            )
            
            predictions = model.predict(X_period_scaled)
            
            # Generate trading signals
            signals = self.generate_trading_signals(
                period_data, predictions, sr_levels, strategy_config
            )
            
            # Calculate returns
            period_returns = self.calculate_strategy_returns(
                period_data, signals, strategy_config
            )
            
            all_signals.extend(signals)
            all_returns.extend(period_returns)
        
        # Calculate performance metrics
        results = self.calculate_performance_metrics(
            pd.DataFrame(all_signals), 
            pd.Series(all_returns),
            strategy_config
        )
        
        results['train_period'] = splits['train']
        results['validation_period'] = splits['validation']
        results['test_period'] = splits['test']
        results['model'] = model
        results['scaler'] = scaler
        results['sr_levels'] = sr_levels
        
        return results
    
    def generate_trading_signals(self, 
                               data: pd.DataFrame,
                               ml_predictions: np.ndarray,
                               sr_levels: pd.DataFrame,
                               config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate trading signals based on ML predictions and S/R levels
        """
        signals = []
        
        for i, (idx, row) in enumerate(data.iterrows()):
            if i >= len(ml_predictions):
                break
            
            signal = {
                'timestamp': idx if hasattr(data, 'index') else row['timestamp'],
                'price': row['close'],
                'ml_prediction': ml_predictions[i],
                'signal': 0,  # 0: hold, 1: buy, -1: sell
                'confidence': 0,
                'reason': []
            }
            
            # ML signal
            ml_threshold = config.get('ml_threshold', 0.02)
            if ml_predictions[i] > ml_threshold:
                signal['signal'] = 1
                signal['confidence'] += 0.5
                signal['reason'].append(f"ML_bullish_{ml_predictions[i]:.4f}")
            elif ml_predictions[i] < -ml_threshold:
                signal['signal'] = -1
                signal['confidence'] += 0.5
                signal['reason'].append(f"ML_bearish_{ml_predictions[i]:.4f}")
            
            # Support/Resistance signal
            current_price = row['close']
            
            # Find nearby S/R levels
            nearby_support = sr_levels[
                (sr_levels['type'] == 'support') & 
                (abs(sr_levels['level'] - current_price) / current_price < 0.02)
            ]
            
            nearby_resistance = sr_levels[
                (sr_levels['type'] == 'resistance') & 
                (abs(sr_levels['level'] - current_price) / current_price < 0.02)
            ]
            
            if not nearby_support.empty and signal['signal'] >= 0:
                signal['signal'] = 1
                signal['confidence'] += 0.3
                signal['reason'].append("support_bounce")
            
            if not nearby_resistance.empty and signal['signal'] <= 0:
                signal['signal'] = -1
                signal['confidence'] += 0.3
                signal['reason'].append("resistance_rejection")
            
            signals.append(signal)
        
        return signals
    
    def calculate_strategy_returns(self, 
                                 data: pd.DataFrame,
                                 signals: List[Dict[str, Any]],
                                 config: Dict[str, Any]) -> List[float]:
        """
        Calculate strategy returns based on signals
        """
        returns = []
        position = 0
        entry_price = 0
        
        base_leverage = config.get('base_leverage', 2.0)
        max_leverage = config.get('max_leverage', 10.0)
        
        for i, signal_data in enumerate(signals):
            if i >= len(data) - 1:
                break
            
            current_price = signal_data['price']
            next_price = data.iloc[i + 1]['close'] if i + 1 < len(data) else current_price
            
            # Position management
            if position == 0 and signal_data['signal'] != 0:
                # Enter position
                position = signal_data['signal']
                entry_price = current_price
                
                # Dynamic leverage based on confidence
                confidence = signal_data['confidence']
                leverage = min(base_leverage * (1 + confidence), max_leverage)
                
            elif position != 0:
                # Calculate return
                price_change = (next_price - entry_price) / entry_price
                strategy_return = position * price_change * leverage
                
                returns.append(strategy_return)
                
                # Exit conditions
                if (position > 0 and signal_data['signal'] < 0) or \
                   (position < 0 and signal_data['signal'] > 0) or \
                   abs(strategy_return) > 0.1:  # 10% stop loss/take profit
                    position = 0
                    entry_price = 0
            
            if position == 0:
                returns.append(0.0)
        
        return returns
    
    def calculate_performance_metrics(self, 
                                    signals_df: pd.DataFrame,
                                    returns_series: pd.Series,
                                    config: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics
        """
        returns_array = returns_series.values
        returns_array = returns_array[~np.isnan(returns_array)]
        
        if len(returns_array) == 0:
            return {'error': 'No valid returns'}
        
        metrics = {}
        
        # Basic metrics
        metrics['total_return'] = np.sum(returns_array)
        metrics['mean_return'] = np.mean(returns_array)
        metrics['volatility'] = np.std(returns_array)
        metrics['sharpe_ratio'] = metrics['mean_return'] / metrics['volatility'] if metrics['volatility'] > 0 else 0
        
        # Trade statistics
        trades = returns_array[returns_array != 0]
        if len(trades) > 0:
            metrics['total_trades'] = len(trades)
            metrics['win_rate'] = np.sum(trades > 0) / len(trades)
            metrics['avg_win'] = np.mean(trades[trades > 0]) if np.sum(trades > 0) > 0 else 0
            metrics['avg_loss'] = np.mean(trades[trades < 0]) if np.sum(trades < 0) > 0 else 0
            metrics['profit_factor'] = abs(metrics['avg_win'] / metrics['avg_loss']) if metrics['avg_loss'] != 0 else float('inf')
        else:
            metrics['total_trades'] = 0
            metrics['win_rate'] = 0
            metrics['avg_win'] = 0
            metrics['avg_loss'] = 0
            metrics['profit_factor'] = 0
        
        # Drawdown analysis
        cumulative_returns = np.cumsum(returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = cumulative_returns - running_max
        metrics['max_drawdown'] = np.min(drawdown)
        
        return metrics


def main():
    """
    Example usage of the TimeSeriesBacktester
    """
    print("Time Series Backtesting System")
    print("=" * 50)
    
    # Example configuration
    strategy_config = {
        'ml_threshold': 0.02,
        'base_leverage': 2.0,
        'max_leverage': 5.0,
        'stop_loss': 0.05,
        'take_profit': 0.10
    }
    
    # Initialize backtester
    backtester = TimeSeriesBacktester(
        train_ratio=0.6,
        validation_ratio=0.2,
        test_ratio=0.2,
        walk_forward_steps=5
    )
    
    print("✅ Time Series Backtester initialized")
    print(f"📊 Train/Validation/Test split: {backtester.train_ratio:.1%}/{backtester.validation_ratio:.1%}/{backtester.test_ratio:.1%}")
    print(f"🔄 Walk-forward steps: {backtester.walk_forward_steps}")
    print(f"📈 Strategy configuration: {strategy_config}")


if __name__ == "__main__":
    main()