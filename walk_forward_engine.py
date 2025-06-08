"""
Walk-Forward Analysis Engine
Implements walk-forward optimization and time series cross-validation
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Callable
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error
import lightgbm as lgb
import warnings
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import cpu_count
import logging

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WalkForwardEngine:
    """
    Implements walk-forward analysis for time series backtesting
    """
    
    def __init__(self, 
                 window_size: int = 1000,
                 step_size: int = 100,
                 min_train_size: int = 500,
                 max_train_size: Optional[int] = None,
                 n_splits: int = 5,
                 validation_size: int = 200):
        """
        Initialize walk-forward engine
        
        Args:
            window_size: Size of each walk-forward window
            step_size: Step size between windows
            min_train_size: Minimum training samples
            max_train_size: Maximum training samples (None = no limit)
            n_splits: Number of time series cross-validation splits
            validation_size: Size of validation set in each window
        """
        self.window_size = window_size
        self.step_size = step_size
        self.min_train_size = min_train_size
        self.max_train_size = max_train_size
        self.n_splits = n_splits
        self.validation_size = validation_size
        
        # Results storage
        self.results = []
        self.models = {}
        self.performance_history = []
        
    def create_walk_forward_splits(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Create walk-forward analysis splits
        
        Args:
            data: Time series data
            
        Returns:
            List of split definitions
        """
        splits = []
        n_samples = len(data)
        
        # Calculate number of possible windows
        max_start = n_samples - self.window_size
        n_windows = max(1, (max_start // self.step_size) + 1)
        
        logger.info(f"Creating {n_windows} walk-forward windows")
        logger.info(f"Window size: {self.window_size}, Step size: {self.step_size}")
        
        for i in range(n_windows):
            start_idx = i * self.step_size
            end_idx = min(start_idx + self.window_size, n_samples)
            
            if end_idx - start_idx < self.min_train_size + self.validation_size:
                break
            
            # Define train/validation/test splits within window
            window_size = end_idx - start_idx
            train_size = min(window_size - self.validation_size - 50, 
                           self.max_train_size if self.max_train_size else window_size)
            train_size = max(train_size, self.min_train_size)
            
            train_start = start_idx
            train_end = train_start + train_size
            val_start = train_end
            val_end = val_start + self.validation_size
            test_start = val_end
            test_end = end_idx
            
            if test_end <= test_start:
                # No test data in this window
                continue
            
            split = {
                'window_id': i,
                'window_start': start_idx,
                'window_end': end_idx,
                'train': (train_start, train_end),
                'validation': (val_start, val_end),
                'test': (test_start, test_end),
                'train_dates': None,
                'validation_dates': None,
                'test_dates': None
            }
            
            # Add date information if available
            if hasattr(data, 'index') and isinstance(data.index, pd.DatetimeIndex):
                split['train_dates'] = (data.index[train_start], data.index[train_end-1])
                split['validation_dates'] = (data.index[val_start], data.index[val_end-1])
                split['test_dates'] = (data.index[test_start], data.index[test_end-1])
            elif 'timestamp' in data.columns:
                split['train_dates'] = (data.iloc[train_start]['timestamp'], data.iloc[train_end-1]['timestamp'])
                split['validation_dates'] = (data.iloc[val_start]['timestamp'], data.iloc[val_end-1]['timestamp'])
                split['test_dates'] = (data.iloc[test_start]['timestamp'], data.iloc[test_end-1]['timestamp'])
            
            splits.append(split)
        
        logger.info(f"Created {len(splits)} valid walk-forward splits")
        return splits
    
    def time_series_cross_validation(self, 
                                   X: pd.DataFrame, 
                                   y: pd.Series,
                                   model_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform time series cross-validation within training period
        
        Args:
            X: Feature matrix
            y: Target variable
            model_params: Model parameters
            
        Returns:
            Cross-validation results
        """
        tscv = TimeSeriesSplit(n_splits=self.n_splits)
        
        cv_scores = []
        feature_importance_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            try:
                # Split data
                X_train_fold = X.iloc[train_idx]
                X_val_fold = X.iloc[val_idx]
                y_train_fold = y.iloc[train_idx]
                y_val_fold = y.iloc[val_idx]
                
                # Scale features
                scaler = StandardScaler()
                X_train_scaled = pd.DataFrame(
                    scaler.fit_transform(X_train_fold),
                    columns=X_train_fold.columns,
                    index=X_train_fold.index
                )
                X_val_scaled = pd.DataFrame(
                    scaler.transform(X_val_fold),
                    columns=X_val_fold.columns,
                    index=X_val_fold.index
                )
                
                # Train model
                model = self._create_model(model_params)
                model.fit(X_train_scaled, y_train_fold)
                
                # Predict
                y_pred = model.predict(X_val_scaled)
                
                # Calculate metrics
                mse = mean_squared_error(y_val_fold, y_pred)
                mae = mean_absolute_error(y_val_fold, y_pred)
                
                # Handle correlation calculation safely
                try:
                    corr = np.corrcoef(y_val_fold, y_pred)[0, 1]
                    if np.isnan(corr):
                        corr = 0.0
                except:
                    corr = 0.0
                
                cv_scores.append({
                    'fold': fold,
                    'mse': mse,
                    'mae': mae,
                    'correlation': corr,
                    'n_train': len(X_train_fold),
                    'n_val': len(X_val_fold)
                })
                
                # Feature importance
                if hasattr(model, 'feature_importances_'):
                    importance = pd.Series(model.feature_importances_, index=X_train_fold.columns)
                    feature_importance_scores.append(importance)
                
            except Exception as e:
                logger.warning(f"CV fold {fold} failed: {e}")
                continue
        
        if not cv_scores:
            return {'error': 'All CV folds failed'}
        
        # Aggregate results
        cv_results = {
            'mean_mse': np.mean([s['mse'] for s in cv_scores]),
            'std_mse': np.std([s['mse'] for s in cv_scores]),
            'mean_mae': np.mean([s['mae'] for s in cv_scores]),
            'std_mae': np.std([s['mae'] for s in cv_scores]),
            'mean_correlation': np.mean([s['correlation'] for s in cv_scores]),
            'std_correlation': np.std([s['correlation'] for s in cv_scores]),
            'n_folds': len(cv_scores),
            'fold_scores': cv_scores
        }
        
        # Feature importance summary
        if feature_importance_scores:
            importance_df = pd.DataFrame(feature_importance_scores)
            cv_results['feature_importance_mean'] = importance_df.mean()
            cv_results['feature_importance_std'] = importance_df.std()
        
        return cv_results
    
    def _create_model(self, params: Dict[str, Any]) -> Any:
        """
        Create model instance based on parameters
        """
        model_type = params.get('type', 'lightgbm')
        
        if model_type == 'lightgbm':
            return lgb.LGBMRegressor(
                n_estimators=params.get('n_estimators', 100),
                max_depth=params.get('max_depth', 6),
                learning_rate=params.get('learning_rate', 0.1),
                subsample=params.get('subsample', 0.8),
                colsample_bytree=params.get('colsample_bytree', 0.8),
                random_state=params.get('random_state', 42),
                verbosity=-1,
                force_col_wise=True
            )
        elif model_type == 'random_forest':
            return RandomForestRegressor(
                n_estimators=params.get('n_estimators', 100),
                max_depth=params.get('max_depth', 10),
                min_samples_split=params.get('min_samples_split', 5),
                min_samples_leaf=params.get('min_samples_leaf', 2),
                random_state=params.get('random_state', 42),
                n_jobs=-1
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def optimize_parameters(self, 
                          X_train: pd.DataFrame,
                          y_train: pd.Series,
                          param_grid: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        Optimize model parameters using time series cross-validation
        
        Args:
            X_train: Training features
            y_train: Training target
            param_grid: Parameter grid to search
            
        Returns:
            Best parameters and optimization results
        """
        logger.info("Starting parameter optimization")
        
        # Generate parameter combinations
        import itertools
        param_combinations = []
        
        keys = param_grid.keys()
        values = param_grid.values()
        
        for combination in itertools.product(*values):
            param_dict = dict(zip(keys, combination))
            param_combinations.append(param_dict)
        
        logger.info(f"Testing {len(param_combinations)} parameter combinations")
        
        best_score = float('inf')
        best_params = None
        optimization_results = []
        
        for i, params in enumerate(param_combinations):
            try:
                cv_results = self.time_series_cross_validation(X_train, y_train, params)
                
                if 'error' not in cv_results:
                    score = cv_results['mean_mse']
                    
                    optimization_results.append({
                        'params': params,
                        'score': score,
                        'cv_results': cv_results
                    })
                    
                    if score < best_score:
                        best_score = score
                        best_params = params
                    
                    if i % 10 == 0:
                        logger.info(f"Optimization progress: {i}/{len(param_combinations)}")
                
            except Exception as e:
                logger.warning(f"Parameter combination {i} failed: {e}")
                continue
        
        if best_params is None:
            logger.error("No valid parameter combinations found")
            return {'error': 'Parameter optimization failed'}
        
        logger.info(f"Best parameters found: {best_params}")
        logger.info(f"Best score: {best_score}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'optimization_results': optimization_results
        }
    
    def run_walk_forward_analysis(self, 
                                data: pd.DataFrame,
                                feature_columns: List[str],
                                target_column: str,
                                model_params: Dict[str, Any],
                                strategy_config: Dict[str, Any],
                                optimize_params: bool = False,
                                param_grid: Optional[Dict[str, List[Any]]] = None) -> Dict[str, Any]:
        """
        Run complete walk-forward analysis
        
        Args:
            data: Complete dataset
            feature_columns: List of feature column names
            target_column: Target column name
            model_params: Model parameters
            strategy_config: Strategy configuration
            optimize_params: Whether to optimize parameters
            param_grid: Parameter grid for optimization
            
        Returns:
            Walk-forward analysis results
        """
        logger.info("Starting walk-forward analysis")
        logger.info(f"Data shape: {data.shape}")
        logger.info(f"Features: {len(feature_columns)}")
        
        # Create walk-forward splits
        splits = self.create_walk_forward_splits(data)
        
        if not splits:
            return {'error': 'No valid splits created'}
        
        results = {
            'splits': splits,
            'window_results': [],
            'predictions': [],
            'performance_summary': {},
            'feature_importance_evolution': []
        }
        
        all_predictions = []
        all_actuals = []
        all_dates = []
        
        for split in splits:
            try:
                window_result = self._process_window(
                    data, split, feature_columns, target_column,
                    model_params, strategy_config, optimize_params, param_grid
                )
                
                if 'error' not in window_result:
                    results['window_results'].append(window_result)
                    
                    # Collect predictions
                    if 'predictions' in window_result:
                        all_predictions.extend(window_result['predictions'])
                        all_actuals.extend(window_result['actuals'])
                        all_dates.extend(window_result['dates'])
                    
                    # Track feature importance evolution
                    if 'feature_importance' in window_result:
                        results['feature_importance_evolution'].append({
                            'window_id': split['window_id'],
                            'importance': window_result['feature_importance']
                        })
                
                logger.info(f"Completed window {split['window_id']}")
                
            except Exception as e:
                logger.error(f"Window {split['window_id']} failed: {e}")
                continue
        
        # Aggregate results
        results['predictions'] = pd.DataFrame({
            'date': all_dates,
            'predicted': all_predictions,
            'actual': all_actuals
        })
        
        # Calculate overall performance
        if all_predictions and all_actuals:
            results['performance_summary'] = self._calculate_overall_performance(
                all_predictions, all_actuals
            )
        
        # Calculate stability metrics
        results['stability_metrics'] = self._calculate_stability_metrics(
            results['window_results']
        )
        
        self.results = results
        
        logger.info("Walk-forward analysis completed")
        return results
    
    def _process_window(self, 
                       data: pd.DataFrame,
                       split: Dict[str, Any],
                       feature_columns: List[str],
                       target_column: str,
                       model_params: Dict[str, Any],
                       strategy_config: Dict[str, Any],
                       optimize_params: bool,
                       param_grid: Optional[Dict[str, List[Any]]]) -> Dict[str, Any]:
        """
        Process a single walk-forward window
        """
        # Extract data for this window
        train_start, train_end = split['train']
        val_start, val_end = split['validation']
        test_start, test_end = split['test']
        
        X_train = data.iloc[train_start:train_end][feature_columns]
        y_train = data.iloc[train_start:train_end][target_column]
        
        X_val = data.iloc[val_start:val_end][feature_columns]
        y_val = data.iloc[val_start:val_end][target_column]
        
        X_test = data.iloc[test_start:test_end][feature_columns]
        y_test = data.iloc[test_start:test_end][target_column]
        
        # Clean data
        X_train = X_train.fillna(method='ffill').fillna(0)
        X_val = X_val.fillna(method='ffill').fillna(0)
        X_test = X_test.fillna(method='ffill').fillna(0)
        
        y_train = y_train.fillna(0)
        y_val = y_val.fillna(0)
        y_test = y_test.fillna(0)
        
        window_result = {
            'window_id': split['window_id'],
            'train_period': split['train_dates'],
            'validation_period': split['validation_dates'],
            'test_period': split['test_dates'],
            'n_train': len(X_train),
            'n_val': len(X_val),
            'n_test': len(X_test)
        }
        
        # Parameter optimization
        if optimize_params and param_grid:
            optimization = self.optimize_parameters(X_train, y_train, param_grid)
            if 'error' not in optimization:
                model_params = optimization['best_params']
                window_result['optimization'] = optimization
        
        # Train model
        scaler = StandardScaler()
        X_train_scaled = pd.DataFrame(
            scaler.fit_transform(X_train),
            columns=X_train.columns,
            index=X_train.index
        )
        
        model = self._create_model(model_params)
        model.fit(X_train_scaled, y_train)
        
        # Validate model
        X_val_scaled = pd.DataFrame(
            scaler.transform(X_val),
            columns=X_val.columns,
            index=X_val.index
        )
        val_predictions = model.predict(X_val_scaled)
        
        val_metrics = {
            'mse': mean_squared_error(y_val, val_predictions),
            'mae': mean_absolute_error(y_val, val_predictions),
            'correlation': np.corrcoef(y_val, val_predictions)[0, 1] if len(np.unique(y_val)) > 1 else 0
        }
        window_result['validation_metrics'] = val_metrics
        
        # Test predictions
        X_test_scaled = pd.DataFrame(
            scaler.transform(X_test),
            columns=X_test.columns,
            index=X_test.index
        )
        test_predictions = model.predict(X_test_scaled)
        
        # Store predictions for aggregation
        window_result['predictions'] = test_predictions.tolist()
        window_result['actuals'] = y_test.tolist()
        
        # Get dates
        if hasattr(data, 'index') and isinstance(data.index, pd.DatetimeIndex):
            window_result['dates'] = data.index[test_start:test_end].tolist()
        elif 'timestamp' in data.columns:
            window_result['dates'] = data.iloc[test_start:test_end]['timestamp'].tolist()
        else:
            window_result['dates'] = list(range(test_start, test_end))
        
        # Feature importance
        if hasattr(model, 'feature_importances_'):
            importance = pd.Series(model.feature_importances_, index=feature_columns)
            window_result['feature_importance'] = importance.to_dict()
        
        # Test metrics
        test_metrics = {
            'mse': mean_squared_error(y_test, test_predictions),
            'mae': mean_absolute_error(y_test, test_predictions),
            'correlation': np.corrcoef(y_test, test_predictions)[0, 1] if len(np.unique(y_test)) > 1 else 0
        }
        window_result['test_metrics'] = test_metrics
        
        # Store model and scaler
        window_result['model'] = model
        window_result['scaler'] = scaler
        
        return window_result
    
    def _calculate_overall_performance(self, 
                                     predictions: List[float],
                                     actuals: List[float]) -> Dict[str, float]:
        """
        Calculate overall performance metrics
        """
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        # Remove NaN values
        valid_mask = ~(np.isnan(predictions) | np.isnan(actuals))
        predictions = predictions[valid_mask]
        actuals = actuals[valid_mask]
        
        if len(predictions) == 0:
            return {'error': 'No valid predictions'}
        
        metrics = {
            'total_samples': len(predictions),
            'mse': mean_squared_error(actuals, predictions),
            'mae': mean_absolute_error(actuals, predictions),
            'rmse': np.sqrt(mean_squared_error(actuals, predictions))
        }
        
        # Correlation
        if len(np.unique(actuals)) > 1:
            metrics['correlation'] = np.corrcoef(actuals, predictions)[0, 1]
        else:
            metrics['correlation'] = 0.0
        
        # R-squared
        ss_res = np.sum((actuals - predictions) ** 2)
        ss_tot = np.sum((actuals - np.mean(actuals)) ** 2)
        metrics['r_squared'] = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return metrics
    
    def _calculate_stability_metrics(self, 
                                   window_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate stability metrics across windows
        """
        if not window_results:
            return {}
        
        # Extract metrics from each window
        correlations = []
        mse_values = []
        
        for result in window_results:
            if 'test_metrics' in result:
                corr = result['test_metrics']['correlation']
                mse = result['test_metrics']['mse']
                
                if not np.isnan(corr):
                    correlations.append(corr)
                if not np.isnan(mse):
                    mse_values.append(mse)
        
        stability = {}
        
        if correlations:
            stability['correlation_mean'] = np.mean(correlations)
            stability['correlation_std'] = np.std(correlations)
            stability['correlation_min'] = np.min(correlations)
            stability['correlation_max'] = np.max(correlations)
        
        if mse_values:
            stability['mse_mean'] = np.mean(mse_values)
            stability['mse_std'] = np.std(mse_values)
            stability['mse_stability'] = 1 / (1 + stability['mse_std'] / stability['mse_mean'])
        
        return stability
    
    def save_results(self, filename: str) -> None:
        """
        Save walk-forward analysis results
        """
        if not self.results:
            logger.warning("No results to save")
            return
        
        # Prepare results for serialization
        serializable_results = self.results.copy()
        
        # Convert models to None (can't pickle easily)
        for window_result in serializable_results.get('window_results', []):
            if 'model' in window_result:
                del window_result['model']
            if 'scaler' in window_result:
                del window_result['scaler']
        
        # Save to JSON
        if filename.endswith('.json'):
            import json
            with open(filename, 'w') as f:
                json.dump(serializable_results, f, indent=2, default=str)
        else:
            # Save to pickle
            with open(filename, 'wb') as f:
                pickle.dump(serializable_results, f)
        
        logger.info(f"Results saved to {filename}")


def main():
    """
    Example usage of WalkForwardEngine
    """
    print("Walk-Forward Analysis Engine")
    print("=" * 40)
    
    # Initialize engine
    engine = WalkForwardEngine(
        window_size=1000,
        step_size=200,
        min_train_size=500,
        n_splits=3,
        validation_size=100
    )
    
    print(f"✅ Walk-forward engine initialized")
    print(f"📊 Window size: {engine.window_size}")
    print(f"👣 Step size: {engine.step_size}")
    print(f"🔄 CV splits: {engine.n_splits}")
    print(f"📈 Ready for time series analysis!")


if __name__ == "__main__":
    main()