#!/usr/bin/env python3
"""
Configuration Integration Test Script

This script tests that the adapters correctly load and use configuration values
from config/support_resistance_config.json instead of hardcoded values.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from adapters.existing_adapters import (
    ExistingSupportResistanceAdapter,
    ExistingMLPredictorAdapter,
    ExistingBTCCorrelationAdapter
)
from interfaces import SupportResistanceLevel

def create_test_data(days=30):
    """Create test market data"""
    dates = pd.date_range(end=datetime.now(), periods=days*24, freq='H')
    np.random.seed(42)
    
    # Generate realistic price data
    base_price = 100
    prices = []
    for i in range(len(dates)):
        if i == 0:
            prices.append(base_price)
        else:
            change = np.random.normal(0, 0.02)  # 2% volatility
            prices.append(prices[-1] * (1 + change))
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': np.random.uniform(1000, 10000, len(dates))
    })
    
    return data

def test_support_resistance_config():
    """Test that ExistingSupportResistanceAdapter uses config values"""
    print("=" * 80)
    print("Testing Support/Resistance Configuration Loading")
    print("=" * 80)
    
    adapter = ExistingSupportResistanceAdapter()
    
    # Check if config was loaded
    assert adapter.config is not None, "Config should be loaded"
    print("✓ Config loaded successfully")
    
    # Check min_distance_from_current_price_pct
    expected_min_distance = 0.5  # From config
    actual_min_distance = adapter.config.get('support_resistance_analysis', {}).get(
        'fractal_detection', {}).get('min_distance_from_current_price_pct')
    
    assert actual_min_distance == expected_min_distance, \
        f"Expected min_distance_from_current_price_pct={expected_min_distance}, got {actual_min_distance}"
    print(f"✓ min_distance_from_current_price_pct correctly loaded: {actual_min_distance}%")
    
    # Test that find_levels uses the config value
    data = create_test_data()
    levels = adapter.find_levels(data)
    print(f"✓ find_levels executed successfully with {len(levels)} levels found")
    
    return True

def test_ml_predictor_config():
    """Test that ExistingMLPredictorAdapter uses config values"""
    print("\n" + "=" * 80)
    print("Testing ML Predictor Configuration Loading")
    print("=" * 80)
    
    adapter = ExistingMLPredictorAdapter()
    
    # Check if config was loaded
    assert adapter.config is not None, "Config should be loaded"
    print("✓ Config loaded successfully")
    
    # Check ML settings
    ml_settings = adapter.config.get('provider_settings', {}).get('SupportResistanceML', {})
    
    expected_values = {
        'confidence_threshold': 0.6,
        'distance_threshold': 0.02,
        'default_accuracy': 0.57,
        'default_precision': 0.54,
        'default_recall': 0.61,
        'default_f1_score': 0.57,
        'resistance_target_multiplier': 1.02,
        'support_target_multiplier': 0.98
    }
    
    for key, expected in expected_values.items():
        actual = ml_settings.get(key)
        assert actual == expected, f"Expected {key}={expected}, got {actual}"
        print(f"✓ {key} correctly loaded: {actual}")
    
    # Test model training uses config values
    data = create_test_data()
    test_level = SupportResistanceLevel(
        price=100.0,
        strength=0.8,
        touch_count=3,
        level_type='resistance',
        first_touch=datetime.now(),
        last_touch=datetime.now(),
        volume_at_level=5000.0,
        distance_from_current=2.0
    )
    
    adapter.train_model(data, [test_level])
    
    # Check that accuracy metrics use default values
    assert adapter.accuracy_metrics['accuracy'] == 0.57
    assert adapter.accuracy_metrics['precision'] == 0.54
    assert adapter.accuracy_metrics['recall'] == 0.61
    assert adapter.accuracy_metrics['f1_score'] == 0.57
    print("✓ Model training uses config default accuracy metrics")
    
    # Test prediction uses config values
    prediction = adapter.predict_breakout(data, test_level)
    assert prediction.prediction_confidence == 0.6  # confidence_threshold from config
    print(f"✓ Prediction confidence uses config value: {prediction.prediction_confidence}")
    
    return True

def test_btc_correlation_config():
    """Test that ExistingBTCCorrelationAdapter uses config values"""
    print("\n" + "=" * 80)
    print("Testing BTC Correlation Configuration Loading")
    print("=" * 80)
    
    adapter = ExistingBTCCorrelationAdapter()
    
    # Check if config was loaded
    assert adapter.config is not None, "Config should be loaded"
    print("✓ Config loaded successfully")
    
    # Check BTC correlation settings
    btc_config = adapter.config.get('support_resistance_analysis', {}).get('btc_correlation', {})
    
    assert btc_config.get('default_correlation_factor') == 0.8
    print(f"✓ default_correlation_factor correctly loaded: {btc_config.get('default_correlation_factor')}")
    
    # Check impact multipliers
    impact_multipliers = btc_config.get('impact_multipliers', {})
    expected_multipliers = {
        '5_min': 0.8,
        '15_min': 0.9,
        '60_min': 1.0,
        '240_min': 1.1
    }
    
    for key, expected in expected_multipliers.items():
        actual = impact_multipliers.get(key)
        assert actual == expected, f"Expected {key}={expected}, got {actual}"
        print(f"✓ impact_multiplier[{key}] correctly loaded: {actual}")
    
    # Check liquidation risk thresholds
    risk_thresholds = adapter.config.get('support_resistance_analysis', {}).get(
        'liquidation_risk_thresholds', {})
    
    assert risk_thresholds.get('critical', {}).get('leveraged_impact_pct') == -80
    assert risk_thresholds.get('critical', {}).get('risk_probability') == 0.9
    print("✓ Liquidation risk thresholds correctly loaded")
    
    # Test fallback prediction uses config values
    risk = adapter._fallback_prediction('BTCUSDT', -10.0)
    assert risk.correlation_strength == 0.8  # From config
    print(f"✓ Fallback prediction uses config correlation factor: {risk.correlation_strength}")
    
    return True

def main():
    """Run all configuration tests"""
    print("Configuration Integration Test")
    print("Testing that adapters use config values instead of hardcoded values")
    
    try:
        # Run tests
        test_support_resistance_config()
        test_ml_predictor_config()
        test_btc_correlation_config()
        
        print("\n" + "=" * 80)
        print("✅ All configuration tests passed!")
        print("Adapters are correctly loading and using values from config/support_resistance_config.json")
        print("=" * 80)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())