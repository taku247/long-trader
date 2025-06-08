# Proper Time Series Backtesting System

A comprehensive backtesting system that implements proper time series methodology to prevent look-ahead bias and ensure realistic trading strategy evaluation.

## 🎯 Key Features

### ✅ Proper Time Series Methodology
- **Train/Validation/Test Split**: Chronological data separation
- **Walk-Forward Analysis**: Rolling window optimization
- **No Look-Ahead Bias**: Models trained only on past data
- **Support/Resistance Detection**: Uses only historical data

### ✅ Comprehensive Data Pipeline
- **Multiple Timeframes**: 5m, 15m, 30m, 1h support
- **Extended History**: Up to 3 years of data depending on timeframe
- **100+ Technical Indicators**: Trend, momentum, volatility, volume
- **Advanced Feature Engineering**: Lag features, rolling statistics, price ratios

### ✅ Advanced ML Models
- **LightGBM**: Fast gradient boosting
- **Random Forest**: Ensemble learning
- **Hyperparameter Optimization**: Grid search with time series CV
- **Feature Selection**: Correlation-based and importance-based filtering

### ✅ Multiple Trading Strategies
- **ML Conservative**: Low risk, stable returns
- **ML Aggressive**: High risk/reward ratio
- **Hybrid Balanced**: Combines ML with traditional TA
- **Traditional TA**: Pure technical analysis
- **Scalping**: High-frequency trading for 5m timeframe

## 📁 File Structure

```
time_series_backtest.py          # Core backtesting logic with train-test splits
extended_data_fetcher.py         # Enhanced data fetching for multiple timeframes
walk_forward_engine.py           # Walk-forward analysis implementation
proper_backtesting_engine.py     # Main backtesting engine
run_proper_backtest.py           # Command-line interface
backtest_config.json             # Configuration file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install pandas numpy scikit-learn lightgbm hyperliquid
```

### 2. Run Single Backtest

```bash
# Basic single test
python run_proper_backtest.py --single-test --symbol HYPE --timeframe 1h --strategy ML_Conservative

# With walk-forward analysis
python run_proper_backtest.py --single-test --symbol SOL --timeframe 15m --strategy ML_Aggressive --walk-forward
```

### 3. Run Comprehensive Backtest

```bash
# Test multiple combinations
python run_proper_backtest.py --symbols HYPE SOL --timeframes 15m 1h --strategies ML_Conservative ML_Aggressive

# Force data refresh
python run_proper_backtest.py --symbols HYPE --timeframes 1h --strategies ML_Conservative --force-refresh
```

## 📊 Data Methodology

### Time Series Splits

The system uses proper chronological splits to prevent look-ahead bias:

```
|---- Training (60%) ----|---- Validation (20%) ----|---- Test (20%) ----|
|                                                                          |
Past Data                                                         Future Data
```

### Walk-Forward Analysis

For datasets with sufficient data (>2000 samples), the system implements walk-forward analysis:

```
Window 1: [Train 1][Val 1][Test 1]
Window 2:      [Train 2][Val 2][Test 2]
Window 3:           [Train 3][Val 3][Test 3]
```

Each window trains a new model using only past data, preventing information leakage.

### Support/Resistance Detection

Support and resistance levels are detected using only historical data up to each point in time:

```python
for i in range(window, len(data)):
    # Only use data up to current point (no look-ahead)
    current_data = data.iloc[:i+1]
    
    # Detect levels from recent window
    recent_data = current_data.tail(window)
    # ... level detection logic
```

## 🎯 Trading Strategies

### ML Conservative
- **Risk Level**: Low
- **Leverage**: 1.5x - 3.0x
- **Stop Loss**: 3%
- **Take Profit**: 6%
- **Best For**: Stable, consistent returns

### ML Aggressive
- **Risk Level**: High
- **Leverage**: 3.0x - 8.0x
- **Stop Loss**: 5%
- **Take Profit**: 10%
- **Best For**: Maximum returns with higher risk

### Hybrid Balanced
- **Risk Level**: Medium
- **Leverage**: 2.0x - 5.0x
- **Stop Loss**: 4%
- **Take Profit**: 8%
- **Best For**: Balanced risk/reward with ML + TA signals

### Traditional TA
- **Risk Level**: Low
- **Leverage**: 1.0x - 2.0x
- **Stop Loss**: 2%
- **Take Profit**: 4%
- **Best For**: Traditional technical analysis approach

## 📈 Performance Metrics

### Primary Metrics
- **Total Return**: Overall strategy performance
- **Sharpe Ratio**: Risk-adjusted returns
- **Win Rate**: Percentage of profitable trades
- **Max Drawdown**: Largest peak-to-trough decline
- **Total Trades**: Number of executed trades

### ML Model Metrics
- **Correlation**: Prediction accuracy correlation
- **MSE**: Mean squared error
- **R-squared**: Explained variance
- **Feature Importance**: Top predictive features

### Stability Metrics
- **Correlation Stability**: Consistency across time windows
- **MSE Stability**: Error consistency
- **Performance Consistency**: Returns stability

## 🔧 Advanced Configuration

### Custom Strategy
```json
{
  "Custom_Strategy": {
    "ml_threshold": 0.02,
    "base_leverage": 2.5,
    "max_leverage": 6.0,
    "stop_loss": 0.04,
    "take_profit": 0.08,
    "min_confidence": 0.3,
    "risk_management": "balanced"
  }
}
```

### Feature Engineering
```python
# Custom lag features
lag_periods = [1, 2, 3, 5, 10, 20]

# Custom rolling windows
rolling_windows = [5, 10, 20, 50, 100]

# Custom technical indicators
custom_indicators = ["custom_rsi", "custom_macd", "custom_bb"]
```

## 📊 Output Examples

### Single Backtest Result
```
📊 BACKTEST RESULTS
Symbol: HYPE
Timeframe: 1h
Strategy: ML_Conservative
Data samples: 8760
Features: 127
Methodology: walk_forward

💰 TRADING PERFORMANCE
Total trades: 245
Win rate: 62.4%
Total return: 34.56%
Sharpe ratio: 1.234
Max drawdown: -8.45%

🤖 ML MODEL PERFORMANCE
Correlation: 0.187
MSE: 0.000234
R-squared: 0.156
```

### Comprehensive Results
```
📊 COMPREHENSIVE BACKTEST RESULTS
Total tests: 8
Average win rate: 58.7%
Average total return: 28.34%
Best strategy: HYPE_1h_ML_Aggressive
Best return: 45.67%

📋 PERFORMANCE BY SYMBOL:
  HYPE: 31.23%
  SOL: 25.45%

⏰ PERFORMANCE BY TIMEFRAME:
  15m: 22.34%
  1h: 34.45%

🎯 PERFORMANCE BY STRATEGY:
  ML_Conservative: 24.56%
  ML_Aggressive: 32.12%
```

## 🛠️ API Usage

### Programmatic Usage
```python
from proper_backtesting_engine import ProperBacktestingEngine

# Initialize engine
engine = ProperBacktestingEngine()

# Run single backtest
result = engine.run_single_backtest(
    symbol='HYPE',
    timeframe='1h',
    strategy_name='ML_Conservative',
    use_walk_forward=True
)

# Run comprehensive backtest
results = engine.run_comprehensive_backtest(
    symbols=['HYPE', 'SOL'],
    timeframes=['15m', '1h'],
    strategies=['ML_Conservative', 'ML_Aggressive']
)
```

### Custom Data
```python
# Use custom data
custom_data = pd.read_csv('my_data.csv')
result = engine.run_single_backtest(
    symbol='CUSTOM',
    timeframe='1h',
    strategy_name='ML_Conservative',
    data=custom_data
)
```

## 🔍 Debugging and Validation

### Data Quality Checks
- Minimum sample requirements
- Missing data validation
- Extreme price movement detection
- Volume anomaly detection

### Model Validation
- Cross-validation scores
- Feature importance analysis
- Prediction correlation tracking
- Overfitting detection

### Strategy Validation
- Minimum trade requirements
- Drawdown limits
- Sharpe ratio thresholds
- Stability requirements

## 📁 Output Files

### Results Directory Structure
```
proper_backtest_results/
├── HYPE_1h_ML_Conservative_result.json
├── SOL_15m_ML_Aggressive_result.json
├── comprehensive_backtest_20231201_143022.json
└── ...
```

### Data Cache
```
data_cache/
├── hype_1h_extended.pkl
├── sol_15m_extended.pkl
└── ...
```

## ⚠️ Important Notes

### Preventing Look-Ahead Bias
1. **Feature Engineering**: All features use only past data
2. **Support/Resistance**: Detected using rolling historical windows
3. **Model Training**: Trained only on chronologically earlier data
4. **Walk-Forward**: Each window starts after previous training period

### Data Requirements
- **Minimum Samples**: 1000 for basic split, 2000 for walk-forward
- **Data Quality**: <5% missing values, realistic price movements
- **Time Coverage**: Sufficient history for meaningful train/test splits

### Performance Considerations
- **Memory Usage**: Large datasets require significant RAM
- **Processing Time**: Walk-forward analysis is computationally intensive
- **API Limits**: Hyperliquid API has rate limiting

## 🚨 Disclaimer

This backtesting system is for educational and research purposes only. Past performance does not guarantee future results. Always conduct thorough testing and validation before deploying any trading strategy with real capital.

## 📞 Support

For issues or questions:
1. Check the log files for error details
2. Validate your data and configuration
3. Ensure all dependencies are installed
4. Review the methodology documentation