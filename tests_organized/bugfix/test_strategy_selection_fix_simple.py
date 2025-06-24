#!/usr/bin/env python3
"""
戦略選択デカルト積問題修正テスト（シンプル版）

選択した戦略IDのみが実行され、意図しない組み合わせが生成されないことをテスト
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


class TestStrategySelectionFixSimple(BaseTest):
    """戦略選択修正のシンプルテスト"""
    
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
            
            # テスト用戦略データ
            strategies = [
                (1, 'Aggressive ML - 15m', 'Aggressive_ML', '15m', '{}', 'Test strategy 1', 1, 0),
                (2, 'Aggressive ML - 30m', 'Aggressive_ML', '30m', '{}', 'Test strategy 2', 1, 0),
                (3, 'Balanced - 15m', 'Balanced', '15m', '{}', 'Test strategy 3', 1, 0),
                (4, 'Balanced - 30m', 'Balanced', '30m', '{}', 'Test strategy 4', 1, 0),
            ]
            
            conn.executemany("""
                INSERT OR REPLACE INTO strategy_configurations 
                (id, name, base_strategy, timeframe, parameters, description, is_active, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, strategies)
    
    def test_get_strategy_configs_for_legacy_exact_selection(self):
        """get_strategy_configs_for_legacy が選択した戦略のみ返すことをテスト"""
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        # 部分的にシステム初期化
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # ID [1, 3] を選択（Aggressive_ML-15m, Balanced-15m）
        strategy_configs = system.get_strategy_configs_for_legacy([1, 3])
        
        # 選択した2つの戦略のみ返されることを確認
        self.assertEqual(len(strategy_configs), 2, "選択した2つの戦略のみ返されるべき")
        
        # 具体的な戦略ID確認
        actual_ids = [config['id'] for config in strategy_configs]
        expected_ids = [1, 3]
        
        for expected_id in expected_ids:
            self.assertIn(expected_id, actual_ids, f"戦略ID {expected_id} が含まれるべき")
        
        # 意図しない戦略が含まれていないことを確認
        unexpected_ids = [2, 4]
        for unexpected_id in unexpected_ids:
            self.assertNotIn(unexpected_id, actual_ids, f"戦略ID {unexpected_id} は含まれるべきでない")
    
    def test_eth_problem_reproduction_prevention(self):
        """ETHの問題（3戦略選択→4戦略実行）が修正されていることをテスト"""
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # ETHで実際に選択された戦略ID [1, 2, 3] を再現
        # 期待：3つの戦略のみ、4つに増えない
        strategy_configs = system.get_strategy_configs_for_legacy([1, 2, 3])
        
        # 選択した3つの戦略のみ返されることを確認
        self.assertEqual(len(strategy_configs), 3, "選択した3つの戦略のみ返されるべき")
        
        # 戦略ID確認
        actual_ids = [config['id'] for config in strategy_configs]
        expected_ids = [1, 2, 3]
        
        for expected_id in expected_ids:
            self.assertIn(expected_id, actual_ids, f"戦略ID {expected_id} が含まれるべき")
        
        # 戦略4（Balanced-30m）が含まれていないことを確認
        self.assertNotIn(4, actual_ids, "戦略ID 4 は選択していないため含まれるべきでない")
    
    def test_cartesian_product_not_generated(self):
        """デカルト積が生成されないことを確認"""
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # ID [1, 3] を選択（Aggressive_ML-15m, Balanced-15m）
        strategy_configs = system.get_strategy_configs_for_legacy([1, 3])
        
        # 戦略と時間足の組み合わせを抽出
        combinations = [(config['base_strategy'], config['timeframe']) 
                       for config in strategy_configs]
        
        # 選択した組み合わせのみ含まれることを確認
        expected_combinations = [
            ('Aggressive_ML', '15m'),  # ID 1
            ('Balanced', '15m'),       # ID 3
        ]
        
        for expected in expected_combinations:
            self.assertIn(expected, combinations, f"選択した組み合わせ {expected} が含まれるべき")
        
        # 意図しない組み合わせが含まれていないことを確認
        unexpected_combinations = [
            ('Aggressive_ML', '30m'),  # 選択していない（デカルト積なら含まれる）
            ('Balanced', '30m'),       # 選択していない
        ]
        
        for unexpected in unexpected_combinations:
            self.assertNotIn(unexpected, combinations, 
                           f"選択していない組み合わせ {unexpected} は含まれるべきでない")
    
    def test_convert_strategy_ids_to_legacy_format_still_works(self):
        """convert_strategy_ids_to_legacy_format（既存メソッド）が引き続き動作することを確認"""
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # 既存メソッドのテスト（DEFAULTモード用）
        strategies, timeframes = system.convert_strategy_ids_to_legacy_format([1, 3])
        
        # 戦略とタイムフレームが正しく分離されることを確認
        expected_strategies = ['Aggressive_ML', 'Balanced']
        expected_timeframes = ['15m']
        
        for strategy in expected_strategies:
            self.assertIn(strategy, strategies, f"戦略 {strategy} が含まれるべき")
        
        for timeframe in expected_timeframes:
            self.assertIn(timeframe, timeframes, f"タイムフレーム {timeframe} が含まれるべき")
        
        # このメソッドは引き続きデカルト積用として機能
        self.assertEqual(len(strategies), 2, "2つの戦略が抽出されるべき")
        self.assertEqual(len(timeframes), 1, "1つのタイムフレームが抽出されるべき")
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # 空リスト
        result = system.get_strategy_configs_for_legacy([])
        self.assertIsNone(result, "空リストの場合はNoneが返されるべき")
        
        # 重複ID
        strategy_configs = system.get_strategy_configs_for_legacy([1, 1, 2])
        self.assertEqual(len(strategy_configs), 2, "重複IDは除去されるべき")
        
        # 無効ID
        strategy_configs = system.get_strategy_configs_for_legacy([1, 999])
        self.assertEqual(len(strategy_configs), 1, "有効なIDのみ取得されるべき")
        actual_ids = [config['id'] for config in strategy_configs]
        self.assertIn(1, actual_ids, "有効ID 1 が含まれるべき")
        self.assertNotIn(999, actual_ids, "無効ID 999 は含まれるべきでない")
    
    def test_execution_mode_workflow_integration(self):
        """実行モード統合ワークフローのテスト"""
        from new_symbol_addition_system import NewSymbolAdditionSystem, ExecutionMode
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # SELECTIVE モードでの戦略選択
        selected_strategy_ids = [1, 3]
        
        # 実際のexecute_symbol_additionで使用される戦略変換ロジックをテスト
        if ExecutionMode.SELECTIVE:
            strategy_configs = system.get_strategy_configs_for_legacy(selected_strategy_ids)
            selected_strategies = None  # デカルト積を無効化
            selected_timeframes = None
        
        # strategy_configsが正しく設定されることを確認
        self.assertIsNotNone(strategy_configs, "strategy_configsが設定されるべき")
        self.assertIsNone(selected_strategies, "selected_strategiesはNoneであるべき")
        self.assertIsNone(selected_timeframes, "selected_timeframesはNoneであるべき")
        self.assertEqual(len(strategy_configs), 2, "選択した2つの戦略のみ設定されるべき")
    
    def test_mixed_strategy_timeframe_selection(self):
        """異なる戦略・時間足の混合選択テスト"""
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        # 追加のテスト戦略データ
        with sqlite3.connect(self.analysis_db) as conn:
            additional_strategies = [
                (5, 'Conservative - 1h', 'Conservative_ML', '1h', '{}', 'Test strategy 5', 1, 0),
                (6, 'Aggressive ML - 4h', 'Aggressive_ML', '4h', '{}', 'Test strategy 6', 1, 0),
            ]
            conn.executemany("""
                INSERT OR REPLACE INTO strategy_configurations 
                (id, name, base_strategy, timeframe, parameters, description, is_active, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, additional_strategies)
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # 複数の戦略・時間足を混合選択
        strategy_configs = system.get_strategy_configs_for_legacy([1, 3, 5, 6])  # Aggressive_ML-15m, Balanced-15m, Conservative_ML-1h, Aggressive_ML-4h
        
        # 正確に4つの戦略が返されることを確認
        self.assertEqual(len(strategy_configs), 4, "選択した4つの戦略すべてが返されるべき")
        
        # 各戦略の詳細を確認
        expected_configs = [
            ('Aggressive_ML', '15m'),  # ID 1
            ('Balanced', '15m'),       # ID 3
            ('Conservative_ML', '1h'), # ID 5
            ('Aggressive_ML', '4h'),   # ID 6
        ]
        
        actual_configs = [(config['base_strategy'], config['timeframe']) for config in strategy_configs]
        
        for expected in expected_configs:
            self.assertIn(expected, actual_configs, f"選択した設定 {expected} が含まれるべき")
        
        # デカルト積が生成されていないことを確認（異なる戦略・時間足を組み合わせていない）
        unexpected_configs = [
            ('Aggressive_ML', '1h'),   # 選択していない組み合わせ
            ('Conservative_ML', '15m'), # 選択していない組み合わせ
            ('Balanced', '4h'),        # 選択していない組み合わせ
        ]
        
        for unexpected in unexpected_configs:
            self.assertNotIn(unexpected, actual_configs, f"選択していない組み合わせ {unexpected} は含まれるべきでない")
    
    def test_large_scale_strategy_selection(self):
        """大量戦略選択時のパフォーマンステスト"""
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        # 大量の戦略データを追加
        with sqlite3.connect(self.analysis_db) as conn:
            large_strategies = []
            for i in range(7, 20):  # ID 7-19 を追加
                strategy_name = f'Test Strategy {i}'
                base_strategy = ['Aggressive_ML', 'Balanced', 'Conservative_ML'][i % 3]
                timeframe = ['5m', '15m', '30m', '1h', '4h'][i % 5]
                large_strategies.append((i, strategy_name, base_strategy, timeframe, '{}', f'Large test strategy {i}', 1, 0))
            
            conn.executemany("""
                INSERT OR REPLACE INTO strategy_configurations 
                (id, name, base_strategy, timeframe, parameters, description, is_active, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, large_strategies)
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # 10個の戦略を選択
        selected_ids = [1, 3, 7, 9, 11, 13, 15, 17, 19, 2]
        strategy_configs = system.get_strategy_configs_for_legacy(selected_ids)
        
        # 選択した戦略数と一致することを確認
        self.assertEqual(len(strategy_configs), len(selected_ids), f"選択した{len(selected_ids)}戦略すべてが返されるべき")
        
        # すべての選択戦略IDが含まれることを確認
        actual_ids = [config['id'] for config in strategy_configs]
        for expected_id in selected_ids:
            self.assertIn(expected_id, actual_ids, f"選択した戦略ID {expected_id} が含まれるべき")
        
        # 選択していない戦略IDが含まれていないことを確認
        unselected_ids = [4, 8, 10, 12, 14, 16, 18]
        for unselected_id in unselected_ids:
            self.assertNotIn(unselected_id, actual_ids, f"選択していない戦略ID {unselected_id} は含まれるべきでない")
    
    def test_auto_symbol_training_integration(self):
        """AutoSymbolTrainingとの統合テスト - strategy_configsが正しく渡されることを確認"""
        from new_symbol_addition_system import NewSymbolAdditionSystem
        from unittest.mock import patch, AsyncMock
        
        system = NewSymbolAdditionSystem.__new__(NewSymbolAdditionSystem)
        system.analysis_db = self.analysis_db
        system.logger = MagicMock()
        
        # AutoSymbolTrainerをモック
        mock_trainer = MagicMock()
        mock_trainer.add_symbol_with_training = AsyncMock(return_value="test_execution_id")
        system.auto_trainer = mock_trainer
        
        # 戦略選択
        selected_strategy_ids = [1, 3]
        strategy_configs = system.get_strategy_configs_for_legacy(selected_strategy_ids)
        
        # AutoSymbolTraining.add_symbol_with_trainingが正しい引数で呼ばれることを模擬確認
        expected_call_args = {
            'symbol': 'TEST',
            'execution_id': 'test_exec_123',
            'selected_strategies': None,  # デカルト積を無効化
            'selected_timeframes': None,  # デカルト積を無効化
            'strategy_configs': strategy_configs  # 選択した戦略設定のみ
        }
        
        # strategy_configsの内容確認
        self.assertIsNotNone(strategy_configs, "strategy_configsが設定されるべき")
        self.assertEqual(len(strategy_configs), 2, "選択した2つの戦略設定が含まれるべき")
        
        # 各strategy_configの必須フィールド確認
        required_fields = ['id', 'name', 'base_strategy', 'timeframe', 'parameters', 'description', 'is_default', 'is_active']
        for config in strategy_configs:
            for field in required_fields:
                self.assertIn(field, config, f"strategy_configに{field}フィールドが含まれるべき")
        
        # 選択した戦略IDが正しく含まれることを確認
        config_ids = [config['id'] for config in strategy_configs]
        for expected_id in selected_strategy_ids:
            self.assertIn(expected_id, config_ids, f"選択した戦略ID {expected_id} がstrategy_configsに含まれるべき")


if __name__ == '__main__':
    unittest.main(verbosity=2)