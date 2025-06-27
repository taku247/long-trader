#!/usr/bin/env python3
"""
Filter 3 (SupportResistanceFilter) パラメータ適用統合テスト
実際のフィルター処理でユーザー指定パラメータが正しく適用されることを検証
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pandas as pd

# パス追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests_organized.base_test import BaseTest


class Filter3ParameterIntegrationTest(BaseTest):
    """Filter 3パラメータ適用統合テスト"""
    
    def setUp(self):
        super().setUp()
        # 環境変数をクリーンアップ
        if 'FILTER_PARAMS' in os.environ:
            del os.environ['FILTER_PARAMS']
    
    def tearDown(self):
        super().tearDown()
        # テスト後も環境変数をクリーンアップ
        if 'FILTER_PARAMS' in os.environ:
            del os.environ['FILTER_PARAMS']
    
    def create_test_ohlcv_data(self, num_points=100):
        """テスト用のOHLCVデータ作成"""
        import numpy as np
        
        # 基準価格から変動するデータを生成
        base_price = 100.0
        timestamps = pd.date_range(start='2023-01-01', periods=num_points, freq='1H')
        
        # サンプルOHLCVデータ
        np.random.seed(42)  # 再現可能性のため
        price_changes = np.random.randn(num_points) * 2  # ±2の変動
        prices = base_price + np.cumsum(price_changes)
        
        data = []
        for i, (ts, price) in enumerate(zip(timestamps, prices)):
            high = price + abs(np.random.randn()) * 0.5
            low = price - abs(np.random.randn()) * 0.5
            open_price = prices[i-1] if i > 0 else price
            close_price = price
            volume = np.random.randint(1000, 10000)
            
            data.append({
                'timestamp': ts,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        return data
    
    def create_mock_prepared_data(self, ohlcv_data):
        """テスト用のPreparedDataモック作成"""
        mock_prepared_data = MagicMock()
        
        # get_ohlcv_until メソッドをモック
        mock_prepared_data.get_ohlcv_until.return_value = ohlcv_data
        
        # get_price_at メソッドをモック（最新価格を返す）
        mock_prepared_data.get_price_at.return_value = ohlcv_data[-1]['close'] if ohlcv_data else 100.0
        
        return mock_prepared_data
    
    def create_mock_strategy(self):
        """テスト用の戦略モック作成"""
        mock_strategy = MagicMock()
        mock_strategy.min_volume_threshold = 1000
        mock_strategy.max_spread_threshold = 0.01
        mock_strategy.min_liquidity_score = 0.5
        return mock_strategy
    
    def test_filter3_uses_environment_variable_params(self):
        """Filter 3が環境変数のパラメータを使用するかテスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # 特定のパラメータを環境変数に設定
        unique_params = {
            'support_resistance': {
                'min_support_strength': 0.25,  # 特殊な値
                'min_resistance_strength': 0.35,
                'min_touch_count': 1,
                'max_distance_pct': 0.20,
                'tolerance_pct': 0.04,
                'fractal_window': 3
            }
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(unique_params)
        
        # Filter 3インスタンス作成
        sr_filter = SupportResistanceFilter()
        
        # 環境変数の値が適用されているかチェック
        self.assertEqual(sr_filter.min_support_strength, 0.25)
        self.assertEqual(sr_filter.min_resistance_strength, 0.35)
        self.assertEqual(sr_filter.min_touch_count, 1)
        self.assertEqual(sr_filter.max_distance_pct, 0.20)
        self.assertEqual(sr_filter.tolerance_pct, 0.04)
        self.assertEqual(sr_filter.fractal_window, 3)
    
    def test_filter3_execution_with_custom_params(self):
        """カスタムパラメータでのFilter 3実行テスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # 緩い条件のパラメータを設定（通過しやすい条件）
        relaxed_params = {
            'support_resistance': {
                'min_support_strength': 0.1,  # 非常に緩い条件
                'min_resistance_strength': 0.1,
                'min_touch_count': 1,
                'max_distance_pct': 0.50,
                'tolerance_pct': 0.10,
                'fractal_window': 3
            }
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(relaxed_params)
        
        # テストデータ準備
        ohlcv_data = self.create_test_ohlcv_data(50)
        prepared_data = self.create_mock_prepared_data(ohlcv_data)
        strategy = self.create_mock_strategy()
        evaluation_time = datetime.now(timezone.utc)
        
        # Filter 3実行
        sr_filter = SupportResistanceFilter()
        
        with patch('engines.filters.base_filter.SupportResistanceDetector') as mock_detector_class:
            # SupportResistanceDetectorのモック設定
            mock_detector = MagicMock()
            mock_detector_class.return_value = mock_detector
            
            # 支持線・抵抗線を検出したと仮定
            mock_support = MagicMock()
            mock_support.strength = 0.15  # 緩い条件なので通過
            mock_resistance = MagicMock()
            mock_resistance.strength = 0.12  # 緩い条件なので通過
            
            mock_detector.detect_levels_from_ohlcv.return_value = ([mock_support], [mock_resistance])
            
            # フィルター実行
            result = sr_filter.execute(prepared_data, strategy, evaluation_time)
            
            # 結果検証
            self.assertTrue(result.passed, "Relaxed parameters should allow passing")
            self.assertIn("支持線・抵抗線チェック合格", result.reason)
            
            # Detectorにカスタムパラメータが渡されているかチェック
            mock_detector_class.assert_called_once()
            call_args = mock_detector_class.call_args
            self.assertEqual(call_args.kwargs['min_touches'], 1)
            self.assertEqual(call_args.kwargs['tolerance_pct'], 0.10)
            self.assertEqual(call_args.kwargs['fractal_window'], 3)
    
    def test_filter3_execution_with_strict_params(self):
        """厳格パラメータでのFilter 3実行テスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # 厳格な条件のパラメータを設定（通過しにくい条件）
        strict_params = {
            'support_resistance': {
                'min_support_strength': 0.9,  # 非常に厳格な条件
                'min_resistance_strength': 0.9,
                'min_touch_count': 5,
                'max_distance_pct': 0.02,
                'tolerance_pct': 0.005,
                'fractal_window': 10
            }
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(strict_params)
        
        # テストデータ準備
        ohlcv_data = self.create_test_ohlcv_data(50)
        prepared_data = self.create_mock_prepared_data(ohlcv_data)
        strategy = self.create_mock_strategy()
        evaluation_time = datetime.now(timezone.utc)
        
        # Filter 3実行
        sr_filter = SupportResistanceFilter()
        
        with patch('engines.filters.base_filter.SupportResistanceDetector') as mock_detector_class:
            # SupportResistanceDetectorのモック設定
            mock_detector = MagicMock()
            mock_detector_class.return_value = mock_detector
            
            # 弱い支持線・抵抗線を検出したと仮定
            mock_support = MagicMock()
            mock_support.strength = 0.3  # 厳格条件では不合格
            mock_resistance = MagicMock()
            mock_resistance.strength = 0.4  # 厳格条件では不合格
            
            mock_detector.detect_levels_from_ohlcv.return_value = ([mock_support], [mock_resistance])
            
            # フィルター実行
            result = sr_filter.execute(prepared_data, strategy, evaluation_time)
            
            # 結果検証
            self.assertFalse(result.passed, "Strict parameters should prevent passing")
            self.assertIn("有効な支持線・抵抗線なし", result.reason)
            
            # Detectorにカスタムパラメータが渡されているかチェック
            mock_detector_class.assert_called_once()
            call_args = mock_detector_class.call_args
            self.assertEqual(call_args.kwargs['min_touches'], 5)
            self.assertEqual(call_args.kwargs['tolerance_pct'], 0.005)
            self.assertEqual(call_args.kwargs['fractal_window'], 10)
    
    def test_filter3_parameter_metrics_in_result(self):
        """Filter 3の結果にパラメータメトリクスが含まれるかテスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # パラメータ設定
        test_params = {
            'support_resistance': {
                'min_support_strength': 0.6,
                'min_resistance_strength': 0.7,
                'min_touch_count': 2,
                'max_distance_pct': 0.10,
                'tolerance_pct': 0.02,
                'fractal_window': 5
            }
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(test_params)
        
        # テストデータ準備
        ohlcv_data = self.create_test_ohlcv_data(30)
        prepared_data = self.create_mock_prepared_data(ohlcv_data)
        strategy = self.create_mock_strategy()
        evaluation_time = datetime.now(timezone.utc)
        
        # Filter 3実行
        sr_filter = SupportResistanceFilter()
        
        with patch('engines.filters.base_filter.SupportResistanceDetector') as mock_detector_class:
            mock_detector = MagicMock()
            mock_detector_class.return_value = mock_detector
            
            # いくつかの支持線・抵抗線を検出
            mock_supports = [MagicMock() for _ in range(3)]
            for i, support in enumerate(mock_supports):
                support.strength = 0.65 + i * 0.1  # 0.65, 0.75, 0.85
            
            mock_resistances = [MagicMock() for _ in range(2)]
            for i, resistance in enumerate(mock_resistances):
                resistance.strength = 0.72 + i * 0.1  # 0.72, 0.82
            
            mock_detector.detect_levels_from_ohlcv.return_value = (mock_supports, mock_resistances)
            
            # フィルター実行
            result = sr_filter.execute(prepared_data, strategy, evaluation_time)
            
            # メトリクス検証
            self.assertIn('support_count', result.metrics)
            self.assertIn('resistance_count', result.metrics)
            self.assertIn('valid_support_count', result.metrics)
            self.assertIn('valid_resistance_count', result.metrics)
            self.assertIn('min_support_strength', result.metrics)
            self.assertIn('min_resistance_strength', result.metrics)
            
            # 実際の値をチェック
            self.assertEqual(result.metrics['support_count'], 3)
            self.assertEqual(result.metrics['resistance_count'], 2)
            self.assertEqual(result.metrics['min_support_strength'], 0.6)
            self.assertEqual(result.metrics['min_resistance_strength'], 0.7)
            
            # 有効な支持線・抵抗線の数をチェック
            # min_support_strength=0.6なので、0.65, 0.75, 0.85はすべて有効
            self.assertEqual(result.metrics['valid_support_count'], 3)
            # min_resistance_strength=0.7なので、0.72, 0.82はすべて有効
            self.assertEqual(result.metrics['valid_resistance_count'], 2)
    
    def test_filter3_insufficient_data_handling(self):
        """データ不足時のFilter 3処理テスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # パラメータ設定
        test_params = {
            'support_resistance': {
                'min_support_strength': 0.5,
                'min_resistance_strength': 0.5,
                'min_touch_count': 2,
                'max_distance_pct': 0.10,
                'tolerance_pct': 0.02,
                'fractal_window': 5
            }
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(test_params)
        
        # 不十分なデータ（5本未満）
        insufficient_data = self.create_test_ohlcv_data(5)
        prepared_data = self.create_mock_prepared_data(insufficient_data)
        strategy = self.create_mock_strategy()
        evaluation_time = datetime.now(timezone.utc)
        
        # Filter 3実行
        sr_filter = SupportResistanceFilter()
        result = sr_filter.execute(prepared_data, strategy, evaluation_time)
        
        # データ不足により失敗するかチェック
        self.assertFalse(result.passed)
        self.assertIn("データ不足", result.reason)
        self.assertIn('data_count', result.metrics)
        self.assertEqual(result.metrics['data_count'], 5)
    
    def test_filter3_error_handling(self):
        """Filter 3のエラーハンドリングテスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # パラメータ設定
        test_params = {
            'support_resistance': {
                'min_support_strength': 0.5,
                'min_resistance_strength': 0.5,
                'min_touch_count': 2
            }
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(test_params)
        
        # 異常なデータ（例外を発生させる）
        prepared_data = MagicMock()
        prepared_data.get_ohlcv_until.side_effect = Exception("Data access error")
        strategy = self.create_mock_strategy()
        evaluation_time = datetime.now(timezone.utc)
        
        # Filter 3実行
        sr_filter = SupportResistanceFilter()
        result = sr_filter.execute(prepared_data, strategy, evaluation_time)
        
        # エラーハンドリングの確認
        self.assertFalse(result.passed)
        self.assertIn("エラー", result.reason)
        self.assertIn("Data access error", result.reason)
        self.assertIn('error', result.metrics)


if __name__ == '__main__':
    unittest.main()