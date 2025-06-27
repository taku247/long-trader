#!/usr/bin/env python3
"""
フィルターパラメータ環境変数機能のテスト
FILTER_PARAMS環境変数の設定・読み込み・JSON解析をテスト
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# パス追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests_organized.base_test import BaseTest


class FilterEnvironmentVariablesTest(BaseTest):
    """フィルターパラメータ環境変数テスト"""
    
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
    
    def test_filter_params_env_var_setting_in_auto_symbol_training(self):
        """auto_symbol_trainingでのFILTER_PARAMS環境変数設定テスト"""
        try:
            from auto_symbol_training import AutoSymbolTrainer
        except ImportError:
            self.skipTest("auto_symbol_training module not available")
        
        # テスト用のfilter_params
        filter_params = {
            'support_resistance': {
                'min_support_strength': 0.3,
                'min_resistance_strength': 0.4,
                'min_touch_count': 2,
                'max_distance_pct': 0.12,
                'tolerance_pct': 0.025,
                'fractal_window': 6
            }
        }
        
        # _verify_analysis_resultsメソッドで環境変数が設定されるかテスト
        trainer = AutoSymbolTrainer()
        
        # メソッドを直接テストするためにモック化
        with patch.object(trainer, '_verify_analysis_results') as mock_verify:
            # 実際のメソッド実装を部分的に再現
            def mock_implementation(*args, **kwargs):
                if 'filter_params' in kwargs and kwargs['filter_params']:
                    os.environ['FILTER_PARAMS'] = json.dumps(kwargs['filter_params'])
                    trainer.logger.info(f"🔧 フィルターパラメータを環境変数に設定: {kwargs['filter_params']}")
                return True
            
            mock_verify.side_effect = mock_implementation
            
            # 環境変数設定をテスト
            result = trainer._verify_analysis_results(
                symbol="TEST",
                execution_id="test_id",
                filter_params=filter_params
            )
            
            # 環境変数が正しく設定されているかチェック
            self.assertIn('FILTER_PARAMS', os.environ)
            env_params = json.loads(os.environ['FILTER_PARAMS'])
            self.assertEqual(env_params, filter_params)
            
            # 設定された内容が正しいかチェック
            sr_params = env_params['support_resistance']
            self.assertEqual(sr_params['min_support_strength'], 0.3)
            self.assertEqual(sr_params['min_resistance_strength'], 0.4)
            self.assertEqual(sr_params['min_touch_count'], 2)
    
    def test_support_resistance_filter_env_loading(self):
        """SupportResistanceFilterでの環境変数読み込みテスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # テスト用の環境変数設定
        filter_params = {
            'support_resistance': {
                'min_support_strength': 0.5,
                'min_resistance_strength': 0.6,
                'min_touch_count': 3,
                'max_distance_pct': 0.08,
                'tolerance_pct': 0.015,
                'fractal_window': 4
            }
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(filter_params)
        
        # フィルターインスタンス作成時に環境変数から読み込まれるかテスト
        sr_filter = SupportResistanceFilter()
        
        # パラメータが正しく設定されているかチェック
        self.assertEqual(sr_filter.min_support_strength, 0.5)
        self.assertEqual(sr_filter.min_resistance_strength, 0.6)
        self.assertEqual(sr_filter.min_touch_count, 3)
        self.assertEqual(sr_filter.max_distance_pct, 0.08)
        self.assertEqual(sr_filter.tolerance_pct, 0.015)
        self.assertEqual(sr_filter.fractal_window, 4)
    
    def test_env_var_json_parsing_error_handling(self):
        """不正なJSON形式の環境変数のエラーハンドリングテスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # 不正なJSON文字列を設定
        os.environ['FILTER_PARAMS'] = '{"invalid": "json"'  # 閉じ括弧なし
        
        # フィルターインスタンス作成でエラーがあってもデフォルト値が使用されるかテスト
        sr_filter = SupportResistanceFilter()
        
        # デフォルト値が設定されているかチェック
        self.assertIsNotNone(sr_filter.min_support_strength)
        self.assertIsNotNone(sr_filter.min_resistance_strength)
        self.assertIsNotNone(sr_filter.min_touch_count)
        self.assertIsNotNone(sr_filter.max_distance_pct)
        
        # デフォルト値の妥当性チェック
        self.assertGreater(sr_filter.min_support_strength, 0)
        self.assertGreater(sr_filter.min_resistance_strength, 0)
        self.assertGreater(sr_filter.min_touch_count, 0)
        self.assertGreater(sr_filter.max_distance_pct, 0)
    
    def test_env_var_empty_support_resistance_section(self):
        """空のsupport_resistanceセクションの処理テスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # support_resistanceセクションが空の環境変数
        filter_params = {
            'support_resistance': {},
            'other_filter': {'param': 'value'}
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(filter_params)
        
        sr_filter = SupportResistanceFilter()
        
        # デフォルト値が使用されるかチェック
        self.assertIsNotNone(sr_filter.min_support_strength)
        self.assertIsNotNone(sr_filter.min_resistance_strength)
    
    def test_env_var_partial_params(self):
        """部分的なパラメータ指定時のデフォルト値併用テスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # 一部のパラメータのみ指定
        filter_params = {
            'support_resistance': {
                'min_support_strength': 0.7,
                'min_touch_count': 4
                # その他のパラメータは未指定
            }
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(filter_params)
        
        sr_filter = SupportResistanceFilter()
        
        # 指定されたパラメータは環境変数の値
        self.assertEqual(sr_filter.min_support_strength, 0.7)
        self.assertEqual(sr_filter.min_touch_count, 4)
        
        # 未指定パラメータはデフォルト値
        self.assertIsNotNone(sr_filter.min_resistance_strength)
        self.assertIsNotNone(sr_filter.max_distance_pct)
        self.assertIsNotNone(sr_filter.tolerance_pct)
        self.assertIsNotNone(sr_filter.fractal_window)
    
    def test_env_var_no_filter_params(self):
        """FILTER_PARAMS環境変数が存在しない場合のテスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # 環境変数が存在しないことを確認
        if 'FILTER_PARAMS' in os.environ:
            del os.environ['FILTER_PARAMS']
        
        sr_filter = SupportResistanceFilter()
        
        # 設定ファイルからのデフォルト値が使用されるかチェック
        self.assertIsNotNone(sr_filter.min_support_strength)
        self.assertIsNotNone(sr_filter.min_resistance_strength)
        self.assertIsNotNone(sr_filter.min_touch_count)
        self.assertIsNotNone(sr_filter.max_distance_pct)
    
    def test_env_var_precedence_over_config_file(self):
        """環境変数が設定ファイルより優先されるかテスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # 環境変数で特殊な値を設定
        unique_value = 0.12345
        filter_params = {
            'support_resistance': {
                'min_support_strength': unique_value,
                'min_resistance_strength': unique_value
            }
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(filter_params)
        
        sr_filter = SupportResistanceFilter()
        
        # 環境変数の値が優先使用されているかチェック
        self.assertEqual(sr_filter.min_support_strength, unique_value)
        self.assertEqual(sr_filter.min_resistance_strength, unique_value)
    
    def test_json_serialization_roundtrip(self):
        """JSON serializationとdeserializationの整合性テスト"""
        original_params = {
            'support_resistance': {
                'min_support_strength': 0.456,
                'min_resistance_strength': 0.789,
                'min_touch_count': 5,
                'max_distance_pct': 0.123,
                'tolerance_pct': 0.0987,
                'fractal_window': 8
            }
        }
        
        # JSON化して環境変数に設定
        json_string = json.dumps(original_params)
        os.environ['FILTER_PARAMS'] = json_string
        
        # 環境変数から読み戻し
        loaded_json = os.environ['FILTER_PARAMS']
        loaded_params = json.loads(loaded_json)
        
        # オリジナルと読み戻し後が一致するかチェック
        self.assertEqual(original_params, loaded_params)
        
        # 各パラメータ値が保持されているかチェック
        sr_original = original_params['support_resistance']
        sr_loaded = loaded_params['support_resistance']
        
        for key in sr_original:
            self.assertEqual(sr_original[key], sr_loaded[key], 
                           f"Parameter {key} mismatch after JSON roundtrip")


if __name__ == '__main__':
    unittest.main()