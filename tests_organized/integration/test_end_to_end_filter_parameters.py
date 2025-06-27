#!/usr/bin/env python3
"""
エンドツーエンド フィルターパラメータテスト
フロントエンド → API → 環境変数 → Filter適用 → 結果の全工程をテスト
"""

import os
import sys
import json
import tempfile
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

# パス追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests_organized.base_test import BaseTest


class EndToEndFilterParametersTest(BaseTest):
    """エンドツーエンドフィルターパラメータテスト"""
    
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
                return True
                
        except ImportError as e:
            self.skipTest(f"Web dashboard not available: {e}")
            return False
    
    def test_full_pipeline_relaxed_parameters(self):
        """緩い条件パラメータでの全工程テスト"""
        if not self.setup_test_web_app():
            return
        
        # 1. フロントエンドからのAPIリクエスト（緩い条件）
        relaxed_payload = {
            'symbol': 'BTC',
            'mode': 'default',
            'strategy_ids': [],
            'filter_params': {
                'support_resistance': {
                    'min_support_strength': 0.2,  # 緩い条件
                    'min_resistance_strength': 0.2,
                    'min_touch_count': 1,
                    'max_distance_pct': 0.25,
                    'tolerance_pct': 0.05,
                    'fractal_window': 3
                }
            }
        }
        
        # 2. モック設定
        with patch('web_dashboard.app.validator') as mock_validator, \
             patch('web_dashboard.app.symbol_addition_system') as mock_system, \
             patch('web_dashboard.app.execution_db') as mock_db, \
             patch('auto_symbol_training.AutoSymbolTrainer') as mock_trainer_class:
            
            # 基本モック設定
            mock_validator.validate_symbol.return_value = True
            mock_db.create_execution.return_value = 'test_execution_relaxed'
            
            # AutoSymbolTrainerのインスタンスモック
            mock_trainer = MagicMock()
            mock_trainer_class.return_value = mock_trainer
            
            # add_symbol_with_trainingをAsyncMockに設定
            mock_trainer.add_symbol_with_training = AsyncMock(return_value='test_execution_relaxed')
            
            # システムのexecute_symbol_additionをAsyncMockに設定
            async def mock_execute_symbol_addition(*args, **kwargs):
                # filter_paramsが正しく渡されているかチェック
                filter_params = kwargs.get('filter_params', {})
                if filter_params:
                    # 環境変数に設定（実際の処理をシミュレート）
                    os.environ['FILTER_PARAMS'] = json.dumps(filter_params)
                
                # AutoSymbolTrainerを呼び出し
                await mock_trainer.add_symbol_with_training(*args, **kwargs)
                return True
            
            mock_system.execute_symbol_addition = AsyncMock(side_effect=mock_execute_symbol_addition)
            
            # 3. APIリクエスト実行
            response = self.app.post('/api/symbol/add',
                                   data=json.dumps(relaxed_payload),
                                   content_type='application/json')
            
            # 4. レスポンス検証
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.data)
            self.assertEqual(response_data['symbol'], 'BTC')
            self.assertEqual(response_data['status'], 'started')
            
            # 5. filter_paramsがシステムに渡されているか検証
            mock_system.execute_symbol_addition.assert_called_once()
            call_args = mock_system.execute_symbol_addition.call_args
            passed_filter_params = call_args.kwargs.get('filter_params', {})
            
            self.assertIn('support_resistance', passed_filter_params)
            sr_params = passed_filter_params['support_resistance']
            self.assertEqual(sr_params['min_support_strength'], 0.2)
            self.assertEqual(sr_params['min_resistance_strength'], 0.2)
            self.assertEqual(sr_params['min_touch_count'], 1)
            
            # 6. 環境変数が設定されているか検証
            self.assertIn('FILTER_PARAMS', os.environ)
            env_params = json.loads(os.environ['FILTER_PARAMS'])
            self.assertEqual(env_params, passed_filter_params)
    
    def test_full_pipeline_strict_parameters(self):
        """厳格条件パラメータでの全工程テスト"""
        if not self.setup_test_web_app():
            return
        
        # 1. フロントエンドからのAPIリクエスト（厳格条件）
        strict_payload = {
            'symbol': 'ETH',
            'mode': 'default',
            'strategy_ids': [],
            'filter_params': {
                'support_resistance': {
                    'min_support_strength': 0.85,  # 厳格条件
                    'min_resistance_strength': 0.90,
                    'min_touch_count': 5,
                    'max_distance_pct': 0.03,
                    'tolerance_pct': 0.008,
                    'fractal_window': 12
                }
            }
        }
        
        # 2. モック設定
        with patch('web_dashboard.app.validator') as mock_validator, \
             patch('web_dashboard.app.symbol_addition_system') as mock_system, \
             patch('web_dashboard.app.execution_db') as mock_db:
            
            mock_validator.validate_symbol.return_value = True
            mock_db.create_execution.return_value = 'test_execution_strict'
            
            # システムのモック設定
            async def mock_execute_strict(*args, **kwargs):
                filter_params = kwargs.get('filter_params', {})
                if filter_params:
                    os.environ['FILTER_PARAMS'] = json.dumps(filter_params)
                return True
            
            mock_system.execute_symbol_addition = AsyncMock(side_effect=mock_execute_strict)
            
            # 3. APIリクエスト実行
            response = self.app.post('/api/symbol/add',
                                   data=json.dumps(strict_payload),
                                   content_type='application/json')
            
            # 4. レスポンス検証
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.data)
            self.assertEqual(response_data['symbol'], 'ETH')
            
            # 5. 厳格パラメータが正しく渡されているか検証
            call_args = mock_system.execute_symbol_addition.call_args
            passed_filter_params = call_args.kwargs.get('filter_params', {})
            sr_params = passed_filter_params['support_resistance']
            
            self.assertEqual(sr_params['min_support_strength'], 0.85)
            self.assertEqual(sr_params['min_resistance_strength'], 0.90)
            self.assertEqual(sr_params['min_touch_count'], 5)
            self.assertEqual(sr_params['max_distance_pct'], 0.03)
    
    def test_full_pipeline_no_filter_params(self):
        """filter_paramsなしでの全工程テスト"""
        if not self.setup_test_web_app():
            return
        
        # 1. filter_paramsなしのAPIリクエスト
        no_filter_payload = {
            'symbol': 'SOL',
            'mode': 'default',
            'strategy_ids': []
            # filter_params なし
        }
        
        # 2. モック設定
        with patch('web_dashboard.app.validator') as mock_validator, \
             patch('web_dashboard.app.symbol_addition_system') as mock_system, \
             patch('web_dashboard.app.execution_db') as mock_db:
            
            mock_validator.validate_symbol.return_value = True
            mock_db.create_execution.return_value = 'test_execution_no_filter'
            mock_system.execute_symbol_addition = AsyncMock(return_value=True)
            
            # 3. APIリクエスト実行
            response = self.app.post('/api/symbol/add',
                                   data=json.dumps(no_filter_payload),
                                   content_type='application/json')
            
            # 4. レスポンス検証
            self.assertEqual(response.status_code, 200)
            
            # 5. filter_paramsが空辞書として渡されているか検証
            call_args = mock_system.execute_symbol_addition.call_args
            passed_filter_params = call_args.kwargs.get('filter_params', {})
            self.assertIsInstance(passed_filter_params, dict)
    
    def test_filter_parameter_processing_in_auto_symbol_training(self):
        """AutoSymbolTrainingでのfilter_params処理テスト"""
        try:
            from auto_symbol_training import AutoSymbolTrainer
        except ImportError:
            self.skipTest("AutoSymbolTrainer not available")
        
        # テスト用パラメータ
        test_filter_params = {
            'support_resistance': {
                'min_support_strength': 0.4,
                'min_resistance_strength': 0.5,
                'min_touch_count': 2,
                'max_distance_pct': 0.12
            }
        }
        
        # AutoSymbolTrainerインスタンス作成
        trainer = AutoSymbolTrainer()
        
        # _verify_analysis_resultsメソッドをモック
        with patch.object(trainer, '_verify_analysis_results') as mock_verify, \
             patch.object(trainer, '_run_early_fail_validation') as mock_early_fail, \
             patch.object(trainer.execution_db, 'create_execution') as mock_create_exec:
            
            # モック設定
            mock_early_fail_result = MagicMock()
            mock_early_fail_result.passed = True
            mock_early_fail.return_value = mock_early_fail_result
            
            mock_create_exec.return_value = 'test_execution_id'
            
            # _verify_analysis_resultsで環境変数設定をシミュレート
            def mock_verify_implementation(*args, **kwargs):
                if 'filter_params' in kwargs and kwargs['filter_params']:
                    os.environ['FILTER_PARAMS'] = json.dumps(kwargs['filter_params'])
                    trainer.logger.info(f"🔧 フィルターパラメータを環境変数に設定: {kwargs['filter_params']}")
                return True
            
            mock_verify.side_effect = mock_verify_implementation
            
            # add_symbol_with_trainingを実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    trainer.add_symbol_with_training(
                        symbol="TEST",
                        execution_id="test_exec_123",
                        filter_params=test_filter_params
                    )
                )
                
                # 結果検証
                self.assertEqual(result, "test_exec_123")
                
                # 環境変数が設定されているか検証
                self.assertIn('FILTER_PARAMS', os.environ)
                env_params = json.loads(os.environ['FILTER_PARAMS'])
                self.assertEqual(env_params, test_filter_params)
                
                # _verify_analysis_resultsが呼ばれているか検証
                mock_verify.assert_called()
                call_args = mock_verify.call_args
                self.assertEqual(call_args.kwargs.get('filter_params'), test_filter_params)
                
            finally:
                loop.close()
    
    def test_support_resistance_filter_reads_environment_in_pipeline(self):
        """パイプライン内でSupportResistanceFilterが環境変数を読むかテスト"""
        try:
            from engines.filters.base_filter import SupportResistanceFilter
        except ImportError:
            self.skipTest("SupportResistanceFilter not available")
        
        # 1. 環境変数にパラメータを設定（実際のパイプラインをシミュレート）
        pipeline_params = {
            'support_resistance': {
                'min_support_strength': 0.33,
                'min_resistance_strength': 0.44,
                'min_touch_count': 3,
                'max_distance_pct': 0.15,
                'tolerance_pct': 0.035,
                'fractal_window': 7
            }
        }
        
        os.environ['FILTER_PARAMS'] = json.dumps(pipeline_params)
        
        # 2. Filter 3インスタンス作成（環境変数から読み込み）
        sr_filter = SupportResistanceFilter()
        
        # 3. パラメータが正しく読み込まれているか検証
        self.assertEqual(sr_filter.min_support_strength, 0.33)
        self.assertEqual(sr_filter.min_resistance_strength, 0.44)
        self.assertEqual(sr_filter.min_touch_count, 3)
        self.assertEqual(sr_filter.max_distance_pct, 0.15)
        self.assertEqual(sr_filter.tolerance_pct, 0.035)
        self.assertEqual(sr_filter.fractal_window, 7)
        
        # 4. フィルター統計にパラメータ情報が含まれるか検証
        stats = sr_filter.get_statistics()
        self.assertIn('name', stats)
        self.assertEqual(stats['name'], 'support_resistance')
    
    def test_error_resilience_in_full_pipeline(self):
        """全工程でのエラー耐性テスト"""
        if not self.setup_test_web_app():
            return
        
        # 1. 不正なJSONを含むリクエスト
        malformed_payload = {
            'symbol': 'ADA',
            'mode': 'default',
            'strategy_ids': [],
            'filter_params': {
                'support_resistance': {
                    'min_support_strength': "invalid_string",  # 不正な型
                    'min_resistance_strength': None,
                    'min_touch_count': -1  # 不正な値
                }
            }
        }
        
        # 2. モック設定
        with patch('web_dashboard.app.validator') as mock_validator, \
             patch('web_dashboard.app.symbol_addition_system') as mock_system, \
             patch('web_dashboard.app.execution_db') as mock_db:
            
            mock_validator.validate_symbol.return_value = True
            mock_db.create_execution.return_value = 'test_execution_error'
            mock_system.execute_symbol_addition = AsyncMock(return_value=True)
            
            # 3. APIリクエスト実行（エラーが発生しても処理は続行される）
            response = self.app.post('/api/symbol/add',
                                   data=json.dumps(malformed_payload),
                                   content_type='application/json')
            
            # 4. APIは成功するはず（resilient design）
            self.assertEqual(response.status_code, 200)
            
            # 5. 不正なパラメータでもシステムに渡されるか検証
            call_args = mock_system.execute_symbol_addition.call_args
            passed_filter_params = call_args.kwargs.get('filter_params', {})
            self.assertIsInstance(passed_filter_params, dict)
            self.assertIn('support_resistance', passed_filter_params)


if __name__ == '__main__':
    unittest.main()