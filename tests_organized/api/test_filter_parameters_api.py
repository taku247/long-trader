#!/usr/bin/env python3
"""
フィルターパラメータAPI機能のテスト
銘柄追加APIでfilter_paramsが正しく処理されることを検証
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


class FilterParametersAPITest(BaseTest):
    """フィルターパラメータAPIテスト"""
    
    def setUp(self):
        super().setUp()
        # テスト用のWebアプリケーション設定
        self.setup_test_web_app()
    
    def setup_test_web_app(self):
        """テスト用WebアプリケーションSetup"""
        try:
            # 本番環境を汚染しないようにテスト環境を隔離
            with tempfile.TemporaryDirectory() as temp_dir:
                os.environ['TEST_MODE'] = 'true'
                os.environ['TEST_DB_PATH'] = os.path.join(temp_dir, 'test.db')
                
                # Webアプリケーションインポート
                from web_dashboard.app import app
                app.config['TESTING'] = True
                self.app = app.test_client()
                
        except ImportError as e:
            self.skipTest(f"Web dashboard not available: {e}")
    
    def test_filter_params_extraction_from_api_request(self):
        """APIリクエストからfilter_paramsが正しく抽出されるかテスト"""
        test_payload = {
            'symbol': 'BTC',
            'mode': 'default',
            'strategy_ids': [],
            'filter_params': {
                'support_resistance': {
                    'min_support_strength': 0.3,
                    'min_resistance_strength': 0.3,
                    'min_touch_count': 1,
                    'max_distance_pct': 0.15,
                    'tolerance_pct': 0.03,
                    'fractal_window': 5
                }
            }
        }
        
        # Mock the validation and processing functions to prevent actual analysis
        with patch('web_dashboard.app.validator') as mock_validator, \
             patch('web_dashboard.app.symbol_addition_system') as mock_system, \
             patch('web_dashboard.app.execution_db') as mock_db:
            
            # Setup mocks
            mock_validator.validate_symbol.return_value = True
            mock_db.create_execution.return_value = 'test_execution_id'
            mock_system.execute_symbol_addition.return_value = True
            
            # Execute API call
            response = self.app.post('/api/symbol/add',
                                   data=json.dumps(test_payload),
                                   content_type='application/json')
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.data)
            self.assertIn('execution_id', response_data)
            self.assertEqual(response_data['symbol'], 'BTC')
            self.assertEqual(response_data['status'], 'started')
            
            # Verify that filter_params were passed to the system
            mock_system.execute_symbol_addition.assert_called_once()
            call_args = mock_system.execute_symbol_addition.call_args
            self.assertIn('filter_params', call_args.kwargs)
            
            # Verify filter_params content
            filter_params = call_args.kwargs['filter_params']
            self.assertIsInstance(filter_params, dict)
            self.assertIn('support_resistance', filter_params)
            sr_params = filter_params['support_resistance']
            self.assertEqual(sr_params['min_support_strength'], 0.3)
            self.assertEqual(sr_params['min_resistance_strength'], 0.3)
            self.assertEqual(sr_params['min_touch_count'], 1)
    
    def test_filter_params_none_handling(self):
        """filter_paramsがNoneの場合の処理テスト"""
        test_payload = {
            'symbol': 'ETH',
            'mode': 'default',
            'strategy_ids': []
            # filter_params なし
        }
        
        with patch('web_dashboard.app.validator') as mock_validator, \
             patch('web_dashboard.app.symbol_addition_system') as mock_system, \
             patch('web_dashboard.app.execution_db') as mock_db:
            
            mock_validator.validate_symbol.return_value = True
            mock_db.create_execution.return_value = 'test_execution_id'
            mock_system.execute_symbol_addition.return_value = True
            
            response = self.app.post('/api/symbol/add',
                                   data=json.dumps(test_payload),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            
            # Verify that filter_params is passed as empty dict or None
            call_args = mock_system.execute_symbol_addition.call_args
            filter_params = call_args.kwargs.get('filter_params', {})
            self.assertIsInstance(filter_params, dict)
    
    def test_invalid_filter_params_structure(self):
        """不正なfilter_params構造のテスト"""
        test_payload = {
            'symbol': 'SOL',
            'mode': 'default',
            'strategy_ids': [],
            'filter_params': "invalid_string_not_dict"  # 不正な形式
        }
        
        with patch('web_dashboard.app.validator') as mock_validator, \
             patch('web_dashboard.app.symbol_addition_system') as mock_system, \
             patch('web_dashboard.app.execution_db') as mock_db:
            
            mock_validator.validate_symbol.return_value = True
            mock_db.create_execution.return_value = 'test_execution_id'
            mock_system.execute_symbol_addition.return_value = True
            
            response = self.app.post('/api/symbol/add',
                                   data=json.dumps(test_payload),
                                   content_type='application/json')
            
            # APIは不正なfilter_paramsでも動作する（resilient design）
            self.assertEqual(response.status_code, 200)
            
            # システムには不正な形式でも渡される（システム側でハンドリング）
            call_args = mock_system.execute_symbol_addition.call_args
            filter_params = call_args.kwargs.get('filter_params')
            self.assertEqual(filter_params, "invalid_string_not_dict")
    
    def test_filter_params_empty_dict(self):
        """空のfilter_paramsテスト"""
        test_payload = {
            'symbol': 'ADA',
            'mode': 'default',
            'strategy_ids': [],
            'filter_params': {}
        }
        
        with patch('web_dashboard.app.validator') as mock_validator, \
             patch('web_dashboard.app.symbol_addition_system') as mock_system, \
             patch('web_dashboard.app.execution_db') as mock_db:
            
            mock_validator.validate_symbol.return_value = True
            mock_db.create_execution.return_value = 'test_execution_id'
            mock_system.execute_symbol_addition.return_value = True
            
            response = self.app.post('/api/symbol/add',
                                   data=json.dumps(test_payload),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            
            call_args = mock_system.execute_symbol_addition.call_args
            filter_params = call_args.kwargs.get('filter_params', {})
            self.assertEqual(filter_params, {})
    
    def test_filter_params_comprehensive_structure(self):
        """包括的なfilter_params構造テスト"""
        test_payload = {
            'symbol': 'MATIC',
            'mode': 'default',
            'strategy_ids': [],
            'filter_params': {
                'support_resistance': {
                    'min_support_strength': 0.7,
                    'min_resistance_strength': 0.8,
                    'min_touch_count': 3,
                    'max_distance_pct': 0.05,
                    'tolerance_pct': 0.01,
                    'fractal_window': 7
                },
                'future_filter_type': {  # 将来の拡張対応テスト
                    'param1': 'value1',
                    'param2': 42
                }
            }
        }
        
        with patch('web_dashboard.app.validator') as mock_validator, \
             patch('web_dashboard.app.symbol_addition_system') as mock_system, \
             patch('web_dashboard.app.execution_db') as mock_db:
            
            mock_validator.validate_symbol.return_value = True
            mock_db.create_execution.return_value = 'test_execution_id'
            mock_system.execute_symbol_addition.return_value = True
            
            response = self.app.post('/api/symbol/add',
                                   data=json.dumps(test_payload),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            
            call_args = mock_system.execute_symbol_addition.call_args
            filter_params = call_args.kwargs.get('filter_params', {})
            
            # Verify support_resistance params
            sr_params = filter_params['support_resistance']
            self.assertEqual(sr_params['min_support_strength'], 0.7)
            self.assertEqual(sr_params['min_resistance_strength'], 0.8)
            self.assertEqual(sr_params['min_touch_count'], 3)
            
            # Verify future extensibility
            self.assertIn('future_filter_type', filter_params)
            future_params = filter_params['future_filter_type']
            self.assertEqual(future_params['param1'], 'value1')
            self.assertEqual(future_params['param2'], 42)
    
    def test_api_logs_filter_params(self):
        """APIがfilter_paramsをログ出力するかテスト"""
        test_payload = {
            'symbol': 'DOT',
            'mode': 'default',
            'strategy_ids': [],
            'filter_params': {
                'support_resistance': {
                    'min_support_strength': 0.4,
                    'min_resistance_strength': 0.4
                }
            }
        }
        
        with patch('web_dashboard.app.validator') as mock_validator, \
             patch('web_dashboard.app.symbol_addition_system') as mock_system, \
             patch('web_dashboard.app.execution_db') as mock_db:
            
            mock_validator.validate_symbol.return_value = True
            mock_db.create_execution.return_value = 'test_execution_id'
            mock_system.execute_symbol_addition.return_value = True
            
            # Capture logs
            with self.assertLogs('web_dashboard.app', level='INFO') as log_context:
                response = self.app.post('/api/symbol/add',
                                       data=json.dumps(test_payload),
                                       content_type='application/json')
                
                self.assertEqual(response.status_code, 200)
                
                # Check if filter params are logged
                log_messages = '\n'.join(log_context.output)
                self.assertIn('Filter parameters', log_messages)
                self.assertIn('support_resistance', log_messages)


if __name__ == '__main__':
    unittest.main()