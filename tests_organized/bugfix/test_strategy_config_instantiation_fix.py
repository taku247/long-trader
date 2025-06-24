#!/usr/bin/env python3
"""
StrategyConfig インスタンス作成エラー修正テスト

get_strategy_configs_for_legacy で取得した設定から StrategyConfig インスタンスが
正常に作成できることをテスト（is_default, is_active フィールドの欠如問題を防止）
"""

import unittest
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests_organized.base_test import BaseTest


class TestStrategyConfigInstantiationFix(BaseTest):
    """StrategyConfig インスタンス作成修正のテスト"""
    
    def setUp(self):
        super().setUp()
        
        # strategy_configurationsテーブル作成
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    base_strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    parameters TEXT,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # テスト用戦略データ（is_default, is_active を含む）
            strategies = [
                (1, 'Aggressive ML - 15m', 'Aggressive_ML', '15m', '{}', 'Test strategy 1', 1, 0),
                (2, 'Aggressive ML - 30m', 'Aggressive_ML', '30m', '{}', 'Test strategy 2', 1, 0),
                (3, 'Balanced - 15m', 'Balanced', '15m', '{}', 'Test strategy 3', 1, 1),  # is_default=1
            ]
            
            conn.executemany("""
                INSERT OR REPLACE INTO strategy_configurations 
                (id, name, base_strategy, timeframe, parameters, description, is_active, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, strategies)
    
    def test_get_strategy_configs_for_legacy_includes_all_fields(self):
        """get_strategy_configs_for_legacy が is_default, is_active フィールドを含むことをテスト"""
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # 戦略設定を取得
        strategy_configs = system.get_strategy_configs_for_legacy([1, 2, 3])
        
        # 3つの戦略が取得されることを確認
        self.assertEqual(len(strategy_configs), 3, "3つの戦略設定が取得されるべき")
        
        # 各設定に必須フィールドが含まれることを確認
        required_fields = ['id', 'name', 'base_strategy', 'timeframe', 'parameters', 'description', 'is_default', 'is_active']
        
        for config in strategy_configs:
            for field in required_fields:
                self.assertIn(field, config, f"戦略設定に {field} フィールドが含まれるべき")
            
            # is_default, is_active がbool型であることを確認
            self.assertIsInstance(config['is_default'], bool, "is_default はbool型であるべき")
            self.assertIsInstance(config['is_active'], bool, "is_active はbool型であるべき")
        
        # 特定の戦略の is_default 値を確認
        strategy_3 = next(config for config in strategy_configs if config['id'] == 3)
        self.assertTrue(strategy_3['is_default'], "戦略ID 3 は is_default=True であるべき")
        
        strategy_1 = next(config for config in strategy_configs if config['id'] == 1)
        self.assertFalse(strategy_1['is_default'], "戦略ID 1 は is_default=False であるべき")
    
    def test_strategy_config_instantiation_success(self):
        """strategy_configs から StrategyConfig インスタンスが正常に作成できることをテスト"""
        from new_symbol_addition_system import NewSymbolAdditionSystem, StrategyConfig
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # 戦略設定を取得
        strategy_configs = system.get_strategy_configs_for_legacy([1, 2])
        
        # StrategyConfig インスタンスの作成をテスト
        strategy_objects = []
        for config in strategy_configs:
            try:
                strategy_obj = StrategyConfig(
                    id=config['id'],
                    name=config['name'],
                    base_strategy=config['base_strategy'],
                    timeframe=config['timeframe'],
                    parameters=config['parameters'],
                    description=config['description'],
                    is_default=config.get('is_default', False),
                    is_active=config.get('is_active', True)
                )
                strategy_objects.append(strategy_obj)
            except Exception as e:
                self.fail(f"StrategyConfig インスタンス作成が失敗: {e}")
        
        # 作成されたインスタンス数を確認
        self.assertEqual(len(strategy_objects), 2, "2つの StrategyConfig インスタンスが作成されるべき")
        
        # 各インスタンスのフィールドを確認
        for strategy_obj in strategy_objects:
            self.assertIsInstance(strategy_obj.id, int, "id は int 型であるべき")
            self.assertIsInstance(strategy_obj.name, str, "name は str 型であるべき")
            self.assertIsInstance(strategy_obj.base_strategy, str, "base_strategy は str 型であるべき")
            self.assertIsInstance(strategy_obj.timeframe, str, "timeframe は str 型であるべき")
            self.assertIsInstance(strategy_obj.parameters, dict, "parameters は dict 型であるべき")
            self.assertIsInstance(strategy_obj.description, str, "description は str 型であるべき")
            self.assertIsInstance(strategy_obj.is_default, bool, "is_default は bool 型であるべき")
            self.assertIsInstance(strategy_obj.is_active, bool, "is_active は bool 型であるべき")
    
    def test_execute_symbol_addition_strategy_config_creation(self):
        """execute_symbol_addition 内の StrategyConfig 作成部分をテスト"""
        from new_symbol_addition_system import NewSymbolAdditionSystem, StrategyConfig
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # 戦略設定を取得
        selected_strategy_ids = [1, 3]
        strategy_configs = system.get_strategy_configs_for_legacy(selected_strategy_ids)
        
        # execute_symbol_addition 内の StrategyConfig 作成ロジックを再現
        strategy_objects = []
        try:
            for config in strategy_configs:
                strategy_objects.append(StrategyConfig(
                    id=config['id'],
                    name=config['name'],
                    base_strategy=config['base_strategy'],
                    timeframe=config['timeframe'],
                    parameters=config['parameters'],
                    description=config['description'],
                    is_default=config.get('is_default', False),
                    is_active=config.get('is_active', True)
                ))
        except Exception as e:
            self.fail(f"execute_symbol_addition 内の StrategyConfig 作成が失敗: {e}")
        
        # 作成されたオブジェクト数を確認
        self.assertEqual(len(strategy_objects), len(selected_strategy_ids), 
                        f"{len(selected_strategy_ids)}個の StrategyConfig オブジェクトが作成されるべき")
        
        # 各オブジェクトが正しい戦略IDを持つことを確認
        created_ids = [obj.id for obj in strategy_objects]
        for expected_id in selected_strategy_ids:
            self.assertIn(expected_id, created_ids, f"戦略ID {expected_id} のオブジェクトが作成されるべき")
    
    def test_missing_fields_error_reproduction(self):
        """is_default, is_active フィールドが不足している場合のエラーを再現テスト"""
        from new_symbol_addition_system import StrategyConfig
        
        # 不完全な設定データ（is_default, is_active が不足）
        incomplete_config = {
            'id': 1,
            'name': 'Test Strategy',
            'base_strategy': 'Aggressive_ML',
            'timeframe': '15m',
            'parameters': {},
            'description': 'Test description'
            # is_default, is_active が不足
        }
        
        # エラーが発生することを確認（修正前の状況を再現）
        with self.assertRaises(TypeError) as context:
            StrategyConfig(
                id=incomplete_config['id'],
                name=incomplete_config['name'],
                base_strategy=incomplete_config['base_strategy'],
                timeframe=incomplete_config['timeframe'],
                parameters=incomplete_config['parameters'],
                description=incomplete_config['description']
                # is_default, is_active を省略
            )
        
        # エラーメッセージに必須引数不足が含まれることを確認
        error_message = str(context.exception)
        self.assertIn("missing", error_message.lower(), "必須引数不足のエラーメッセージが含まれるべき")
        self.assertIn("required", error_message.lower(), "必須引数のエラーメッセージが含まれるべき")
    
    def test_default_values_usage(self):
        """デフォルト値が正しく使用されることをテスト"""
        from new_symbol_addition_system import StrategyConfig
        
        # 部分的な設定データ
        config_without_defaults = {
            'id': 1,
            'name': 'Test Strategy',
            'base_strategy': 'Aggressive_ML',
            'timeframe': '15m',
            'parameters': {},
            'description': 'Test description'
            # is_default, is_active は .get() でデフォルト値を使用
        }
        
        # デフォルト値を使用して StrategyConfig を作成
        strategy_obj = StrategyConfig(
            id=config_without_defaults['id'],
            name=config_without_defaults['name'],
            base_strategy=config_without_defaults['base_strategy'],
            timeframe=config_without_defaults['timeframe'],
            parameters=config_without_defaults['parameters'],
            description=config_without_defaults['description'],
            is_default=config_without_defaults.get('is_default', False),  # デフォルト: False
            is_active=config_without_defaults.get('is_active', True)      # デフォルト: True
        )
        
        # デフォルト値が設定されることを確認
        self.assertFalse(strategy_obj.is_default, "is_default のデフォルト値は False であるべき")
        self.assertTrue(strategy_obj.is_active, "is_active のデフォルト値は True であるべき")


if __name__ == '__main__':
    unittest.main(verbosity=2)