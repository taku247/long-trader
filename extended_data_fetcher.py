"""
Extended Data Fetcher with Support for Multiple Timeframes
Fetches extended periods for proper train/validation/test splits
"""

import pandas as pd
import numpy as np
import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from hyperliquid.info import Info
from hyperliquid.utils import constants
import logging

# Suppress websocket warnings
logging.getLogger('websocket').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

class ExtendedDataFetcher:
    """
    Fetches cryptocurrency data for multiple timeframes with extended periods
    """
    
    def __init__(self):
        self.info = Info(constants.MAINNET_API_URL)
        
        # Timeframe configurations for extended backtesting
        self.timeframe_config = {
            '5m': {
                'days': 90,  # 3 months for proper train/test split
                'intervals_per_day': 288,  # 24*60/5
                'min_samples_needed': 500
            },
            '15m': {
                'days': 180,  # 6 months
                'intervals_per_day': 96,   # 24*60/15
                'min_samples_needed': 400
            },
            '30m': {
                'days': 270,  # 9 months
                'intervals_per_day': 48,   # 24*60/30
                'min_samples_needed': 350
            },
            '1h': {
                'days': 365,  # 1 year
                'intervals_per_day': 24,
                'min_samples_needed': 300
            },
            '3m': {
                'days': 60,  # 2 months
                'intervals_per_day': 480,  # 24*60/3
                'min_samples_needed': 600
            },
            '1m': {
                'days': 30,  # 1 month
                'intervals_per_day': 1440,  # 24*60/1
                'min_samples_needed': 1000
            }
        }
        
        # Supported timeframes for backtesting
        self.supported_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h']
    
    def fetch_extended_data(self, 
                           symbol: str, 
                           timeframe: str,
                           custom_days: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch extended OHLCV data for backtesting
        
        Args:
            symbol: Trading symbol (e.g., 'HYPE', 'SOL', 'BTC')
            timeframe: Time interval ('5m', '15m', '30m', '1h')
            custom_days: Override default days if specified
            
        Returns:
            DataFrame with OHLCV data and metadata
        """
        if timeframe not in self.timeframe_config:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {list(self.timeframe_config.keys())}")
        
        config = self.timeframe_config[timeframe]
        days_to_fetch = custom_days if custom_days else config['days']
        
        print(f"\n📊 🔥 EXTENDED OHLCV FETCH START 🔥")
        print(f"🪙 Symbol: {symbol}")
        print(f"⏰ Timeframe: {timeframe}")
        print(f"📅 Period: {days_to_fetch} days")
        print(f"🎯 Target samples: ~{days_to_fetch * config['intervals_per_day']}")
        print(f"🔧 Config: {config}")
        
        # Calculate time range
        now_ms = int(time.time() * 1000)
        one_day_ms = 24 * 60 * 60 * 1000
        start_ms = now_ms - days_to_fetch * one_day_ms
        
        csv_data = []
        failed_days = 0
        
        # Fetch data day by day to handle API limits
        for i in range(days_to_fetch):
            s = start_ms + i * one_day_ms
            e = s + one_day_ms
            
            if i % 10 == 0:  # Progress update every 10 days
                progress = (i / days_to_fetch) * 100
                print(f"📈 Progress: {progress:.1f}% ({i}/{days_to_fetch} days)")
            
            try:
                candles = self.info.candles_snapshot(symbol, timeframe, s, e)
                
                for c in candles:
                    row = {
                        "timestamp": datetime.utcfromtimestamp(c["t"] / 1000),
                        "open": float(c["o"]),
                        "high": float(c["h"]),
                        "low": float(c["l"]),
                        "close": float(c["c"]),
                        "volume": float(c["v"]),
                        "trades": int(c["n"]),
                    }
                    csv_data.append(row)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                failed_days += 1
                if failed_days > days_to_fetch * 0.1:  # Fail if >10% of days fail
                    raise Exception(f"Too many failed days: {failed_days}")
                print(f"⚠️  Day {i} failed: {e}")
                continue
        
        if not csv_data:
            raise Exception(f"No data retrieved for {symbol}")
        
        # Convert to DataFrame
        df = pd.DataFrame(csv_data)
        df = df.sort_values('timestamp')
        df = df.drop_duplicates(subset=['timestamp'])
        df = df.reset_index(drop=True)
        
        print(f"✅ 🔥 EXTENDED OHLCV FETCH COMPLETE 🔥")
        print(f"🪙 Symbol: {symbol} | ⏰ Timeframe: {timeframe}")
        print(f"📊 Total samples: {len(df)}")
        print(f"📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"❌ Failed days: {failed_days} / {day_count}")
        print(f"✅ Success rate: {((day_count-failed_days)/day_count*100):.1f}%")
        
        # Validate data quality
        self._validate_data_quality(df, config)
        
        return df
    
    def _validate_data_quality(self, df: pd.DataFrame, config: Dict) -> None:
        """
        Validate data quality and completeness
        """
        issues = []
        
        # Check minimum samples
        if len(df) < config['min_samples_needed']:
            issues.append(f"Insufficient samples: {len(df)} < {config['min_samples_needed']}")
        
        # Check for missing values
        missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100
        if missing_pct > 5:  # More than 5% missing
            issues.append(f"High missing data: {missing_pct:.1f}%")
        
        # Check for unrealistic price movements
        returns = df['close'].pct_change().abs()
        extreme_moves = (returns > 0.5).sum()  # >50% price moves
        if extreme_moves > len(df) * 0.01:  # More than 1% of data
            issues.append(f"Suspicious price movements: {extreme_moves} extreme moves")
        
        # Check for zero volume periods
        zero_volume_pct = (df['volume'] == 0).sum() / len(df) * 100
        if zero_volume_pct > 10:  # More than 10% zero volume
            issues.append(f"High zero volume periods: {zero_volume_pct:.1f}%")
        
        if issues:
            print(f"⚠️  Data quality issues detected:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Data quality validation passed")
    
    def calculate_comprehensive_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate comprehensive technical indicators
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with technical indicators
        """
        print("🔧 Calculating technical indicators...")
        
        # Import technical analysis functions from the main script
        from ohlcv_by_claude import (
            calculate_sma, calculate_ema, calculate_rsi, calculate_macd,
            calculate_bollinger_bands, calculate_atr, calculate_stochastic,
            calculate_adx, calculate_obv, calculate_mfi, calculate_vwap,
            calculate_ichimoku, calculate_parabolic_sar, calculate_aroon,
            calculate_roc, calculate_momentum, calculate_williams_r,
            calculate_keltner_channel, calculate_donchian_channel,
            calculate_historical_volatility, calculate_cmf, calculate_ad_line,
            calculate_pivot_points, calculate_wma, calculate_hma,
            calculate_dema, calculate_tema, calculate_fractals,
            calculate_true_range_percent, detect_candlestick_patterns,
            calculate_ma_slope, calculate_seasonality_features
        )
        
        data = df.copy()
        
        # Trend indicators
        data['sma_10'] = calculate_sma(data['close'], 10)
        data['sma_20'] = calculate_sma(data['close'], 20)
        data['sma_50'] = calculate_sma(data['close'], 50)
        data['sma_100'] = calculate_sma(data['close'], 100)
        
        data['ema_10'] = calculate_ema(data['close'], 10)
        data['ema_20'] = calculate_ema(data['close'], 20)
        data['ema_50'] = calculate_ema(data['close'], 50)
        data['ema_100'] = calculate_ema(data['close'], 100)
        
        data['wma_20'] = calculate_wma(data['close'], 20)
        data['hma_20'] = calculate_hma(data['close'], 20)
        data['dema_20'] = calculate_dema(data['close'], 20)
        data['tema_20'] = calculate_tema(data['close'], 20)
        
        # Ichimoku Cloud
        ichimoku_data = calculate_ichimoku(data['high'], data['low'], data['close'])
        data['ichimoku_tenkan'], data['ichimoku_kijun'], data['ichimoku_senkou_a'], data['ichimoku_senkou_b'], data['ichimoku_chikou'] = ichimoku_data
        
        # Parabolic SAR
        data['psar'], data['psar_trend'] = calculate_parabolic_sar(data['high'], data['low'], data['close'])
        
        # Aroon
        data['aroon_up'], data['aroon_down'] = calculate_aroon(data['high'], data['low'])
        
        # Momentum indicators
        data['rsi_14'] = calculate_rsi(data['close'], 14)
        data['rsi_21'] = calculate_rsi(data['close'], 21)
        
        data['macd'], data['macd_signal'], data['macd_hist'] = calculate_macd(data['close'])
        data['stoch_k'], data['stoch_d'] = calculate_stochastic(data['high'], data['low'], data['close'])
        
        data['roc_12'] = calculate_roc(data['close'], 12)
        data['momentum_10'] = calculate_momentum(data['close'], 10)
        data['williams_r'] = calculate_williams_r(data['high'], data['low'], data['close'])
        
        # Volatility indicators
        data['bb_upper'], data['bb_middle'], data['bb_lower'] = calculate_bollinger_bands(data['close'])
        data['atr_14'] = calculate_atr(data['high'], data['low'], data['close'], 14)
        data['kc_upper'], data['kc_middle'], data['kc_lower'] = calculate_keltner_channel(data['high'], data['low'], data['close'])
        data['dc_upper'], data['dc_middle'], data['dc_lower'] = calculate_donchian_channel(data['high'], data['low'])
        
        # ADX
        data['adx'], data['di_plus'], data['di_minus'] = calculate_adx(data['high'], data['low'], data['close'])
        
        # Volume indicators
        data['obv'] = calculate_obv(data['close'], data['volume'])
        data['mfi_14'] = calculate_mfi(data['high'], data['low'], data['close'], data['volume'], 14)
        data['vwap'] = calculate_vwap(data['high'], data['low'], data['close'], data['volume'])
        data['cmf'] = calculate_cmf(data['high'], data['low'], data['close'], data['volume'])
        data['ad_line'] = calculate_ad_line(data['high'], data['low'], data['close'], data['volume'])
        
        # Pivot points
        pivot_data = calculate_pivot_points(data['high'].shift(1), data['low'].shift(1), data['close'].shift(1))
        data['pivot'], data['r1'], data['r2'], data['r3'], data['s1'], data['s2'], data['s3'] = pivot_data
        
        # Price-based features
        data['returns'] = data['close'].pct_change()
        data['log_returns'] = np.log(data['close'] / data['close'].shift(1))
        data['high_low_ratio'] = (data['high'] - data['low']) / data['close']
        data['close_location'] = (data['close'] - data['low']) / (data['high'] - data['low'])
        
        # Rolling statistics
        for window in [10, 20, 50]:
            data[f'rolling_std_{window}'] = data['close'].rolling(window=window).std()
            data[f'rolling_max_{window}'] = data['close'].rolling(window=window).max()
            data[f'rolling_min_{window}'] = data['close'].rolling(window=window).min()
            data[f'rolling_mean_{window}'] = data['close'].rolling(window=window).mean()
        
        # Z-scores
        data['z_score_20'] = (data['close'] - data['rolling_mean_20']) / data['rolling_std_20']
        data['z_score_50'] = (data['close'] - data['rolling_mean_50']) / data['rolling_std_50']
        
        # Fractals
        data['fractal_up'], data['fractal_down'] = calculate_fractals(data['high'], data['low'])
        
        # True Range %
        data['true_range_pct'] = calculate_true_range_percent(data['high'], data['low'], data['close'])
        
        # Candlestick patterns
        patterns = detect_candlestick_patterns(data['open'], data['high'], data['low'], data['close'])
        for pattern_name in patterns.columns:
            data[f'pattern_{pattern_name}'] = patterns[pattern_name]
        
        # Moving average slopes
        data['sma_20_slope'] = calculate_ma_slope(data['sma_20'])
        data['ema_20_slope'] = calculate_ma_slope(data['ema_20'])
        
        # Seasonality features
        seasonality = calculate_seasonality_features(data['timestamp'])
        for col in seasonality.columns:
            data[col] = seasonality[col]
        
        # Additional features for ML
        # Price momentum
        for periods in [1, 3, 5, 10]:
            data[f'price_momentum_{periods}'] = data['close'].pct_change(periods)
            data[f'volume_momentum_{periods}'] = data['volume'].pct_change(periods)
        
        # Volatility features
        for window in [5, 10, 20]:
            data[f'volatility_{window}'] = data['returns'].rolling(window).std()
            data[f'volume_volatility_{window}'] = data['volume'].pct_change().rolling(window).std()
        
        # Price position in range
        for window in [10, 20, 50]:
            high_window = data['high'].rolling(window).max()
            low_window = data['low'].rolling(window).min()
            data[f'price_position_{window}'] = (data['close'] - low_window) / (high_window - low_window)
        
        # Cross-over signals
        data['sma_cross_20_50'] = (data['sma_20'] > data['sma_50']).astype(int)
        data['ema_cross_10_20'] = (data['ema_10'] > data['ema_20']).astype(int)
        data['price_above_vwap'] = (data['close'] > data['vwap']).astype(int)
        
        # Bollinger Band features
        data['bb_width'] = (data['bb_upper'] - data['bb_lower']) / data['bb_middle']
        data['bb_position'] = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'])
        
        print(f"✅ Technical indicators calculated: {len([col for col in data.columns if col not in df.columns])} new features")
        
        return data
    
    def save_data(self, df: pd.DataFrame, symbol: str, timeframe: str, 
                  suffix: str = '') -> str:
        """
        Save data to CSV file
        
        Args:
            df: DataFrame to save
            symbol: Trading symbol
            timeframe: Time interval
            suffix: Optional suffix for filename
            
        Returns:
            Saved filename
        """
        filename = f"{symbol.lower()}_{timeframe}"
        if suffix:
            filename += f"_{suffix}"
        filename += ".csv"
        
        # Ensure timestamp is properly formatted
        if 'timestamp' in df.columns:
            df = df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        df.to_csv(filename, index=False)
        print(f"💾 Data saved: {filename}")
        
        return filename
    
    def get_multi_timeframe_data(self, 
                               symbol: str, 
                               timeframes: List[str],
                               custom_days: Optional[Dict[str, int]] = None) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple timeframes
        
        Args:
            symbol: Trading symbol
            timeframes: List of timeframes to fetch
            custom_days: Custom days for each timeframe
            
        Returns:
            Dictionary mapping timeframe to DataFrame
        """
        results = {}
        
        for timeframe in timeframes:
            if timeframe not in self.supported_timeframes:
                print(f"⚠️  Skipping unsupported timeframe: {timeframe}")
                continue
            
            days = custom_days.get(timeframe) if custom_days else None
            
            try:
                # Fetch raw data
                raw_data = self.fetch_extended_data(symbol, timeframe, days)
                
                # Calculate indicators
                full_data = self.calculate_comprehensive_indicators(raw_data)
                
                # Save data
                self.save_data(raw_data, symbol, timeframe, 'raw')
                self.save_data(full_data, symbol, timeframe, 'extended')
                
                results[timeframe] = full_data
                
            except Exception as e:
                print(f"❌ Failed to fetch {timeframe} data: {e}")
                continue
        
        return results


def main():
    """
    Example usage of ExtendedDataFetcher
    """
    print("Extended Data Fetcher for Time Series Backtesting")
    print("=" * 60)
    
    # Configuration
    symbol = "HYPE"
    timeframes = ['5m', '15m', '30m', '1h']
    
    # Custom periods for extended backtesting
    custom_days = {
        '5m': 60,    # 2 months for 5m (high frequency)
        '15m': 120,  # 4 months for 15m
        '30m': 180,  # 6 months for 30m
        '1h': 365    # 1 year for 1h
    }
    
    # Initialize fetcher
    fetcher = ExtendedDataFetcher()
    
    print(f"📊 Fetching {symbol} data for backtesting")
    print(f"⏰ Timeframes: {timeframes}")
    print(f"📅 Custom periods: {custom_days}")
    
    # Fetch multi-timeframe data
    try:
        data_dict = fetcher.get_multi_timeframe_data(symbol, timeframes, custom_days)
        
        print(f"\n✅ Data fetch summary:")
        for tf, df in data_dict.items():
            print(f"  {tf}: {len(df)} samples, {len(df.columns)} features")
            print(f"      Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        print(f"\n🎯 Ready for time series backtesting!")
        print(f"📁 Files saved in current directory")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()