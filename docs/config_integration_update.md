# Configuration Integration Update

## Overview
Updated `adapters/existing_adapters.py` to use configuration values from `config/support_resistance_config.json` instead of hardcoded values. This improves maintainability and allows for easy configuration changes without modifying code.

## Changes Made

### 1. Import and Configuration Loading
- Added `import json` to support JSON configuration loading
- Added `_load_config()` method to each adapter class
- Configuration is loaded once during initialization to avoid repeated file reads
- Fallback to default values if configuration file cannot be loaded

### 2. ExistingSupportResistanceAdapter Updates

#### Configuration Values Used:
- **min_distance_from_current_price_pct**: Minimum distance (%) from current price for valid levels
  - Previous: Hardcoded `0.005` (0.5%)
  - Now: From `config.support_resistance_analysis.fractal_detection.min_distance_from_current_price_pct`
  - Converts percentage to decimal (0.5% → 0.005)

### 3. ExistingMLPredictorAdapter Updates

#### Configuration Values Used:
- **Default accuracy metrics**:
  - `default_accuracy`: 0.57
  - `default_precision`: 0.54
  - `default_recall`: 0.61
  - `default_f1_score`: 0.57
- **Prediction confidence**: Uses `confidence_threshold` (0.6)
- **Price target multipliers**:
  - `resistance_target_multiplier`: 1.02 (2% above)
  - `support_target_multiplier`: 0.98 (2% below)

### 4. ExistingBTCCorrelationAdapter Updates

#### Configuration Values Used:
- **BTC Correlation**:
  - `default_correlation_factor`: 0.8
  - `impact_multipliers`: Time-based impact factors (5min: 0.8, 15min: 0.9, etc.)
  
- **Liquidation Risk Thresholds**:
  - Critical: -80% leveraged impact, 0.9 risk probability
  - High: -60% leveraged impact, 0.6 risk probability
  - Medium: -40% leveraged impact, 0.3 risk probability
  - Low: 0% leveraged impact, 0.1 risk probability

- **Risk Level Scoring**:
  - Mapping: LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4
  - Average thresholds for determining overall risk level

## Configuration File Updates

Added missing ML-related configuration values to `config/support_resistance_config.json`:
```json
"SupportResistanceML": {
  "distance_threshold": 0.02,
  "confidence_threshold": 0.6,
  "default_accuracy": 0.57,
  "default_precision": 0.54,
  "default_recall": 0.61,
  "default_f1_score": 0.57,
  "resistance_target_multiplier": 1.02,
  "support_target_multiplier": 0.98
}
```

## Benefits

1. **Centralized Configuration**: All configuration values are in one place
2. **No Code Changes Required**: Adjust behavior by modifying JSON config
3. **Better Testing**: Easy to test with different configurations
4. **Improved Maintainability**: Clear separation between code and configuration
5. **Graceful Fallback**: Default values ensure system continues to work if config is missing

## Testing

Created `test_config_integration.py` to verify:
- Configuration files are loaded correctly
- All hardcoded values are replaced with config values
- Adapters use configuration values in their operations
- Fallback to defaults works when config is missing

All tests pass successfully, confirming the integration is working correctly.