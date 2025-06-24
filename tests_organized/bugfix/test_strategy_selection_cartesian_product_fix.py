#!/usr/bin/env python3
"""
戦略選択デカルト積問題修正テストスイート

選択した戦略IDのみが実行され、意図しない組み合わせが生成されないことを徹底的にテスト:

1. SELECTIVE/CUSTOMモードで選択した戦略のみ実行
2. デカルト積が生成されないことを確認
3. DEFAULT モードへの影響なし
4. エッジケース：重複、無効ID、空リスト
5. 既存機能との互換性
"""

import unittest
import tempfile
import sqlite3
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from new_symbol_addition_system import NewSymbolAdditionSystem, ExecutionMode, ExecutionStatus
from tests_organized.base_test import DatabaseTest


class TestStrategySelectionCartesianProductFix(DatabaseTest):
    """戦略選択デカルト積問題修正のテスト"""
    
    def custom_setup(self):
        """テスト固有のセットアップ"""
        # BaseTestのDBを使用
        self.test_analysis_db = self.analysis_db
        self.test_execution_logs_db = self.execution_logs_db
        
        # 必要なカラム追加
        with sqlite3.connect(self.test_analysis_db) as conn:
            cursor = conn.execute("PRAGMA table_info(analyses)")
            columns = [row[1] for row in cursor.fetchall()]
            
            required_columns = ['task_status', 'error_message', 'task_completed_at']
            for col in required_columns:
                if col not in columns:
                    conn.execute(f"ALTER TABLE analyses ADD COLUMN {col} TEXT")
        
        # execution_logsに必要なカラム追加
        with sqlite3.connect(self.test_execution_logs_db) as conn:
            cursor = conn.execute("PRAGMA table_info(execution_logs)")
            columns = [row[1] for row in cursor.fetchall()]
            
            required_exec_columns = ['selected_strategy_ids', 'execution_mode', 'estimated_patterns']
            for col in required_exec_columns:
                if col not in columns:
                    if col == 'estimated_patterns':
                        conn.execute(f"ALTER TABLE execution_logs ADD COLUMN {col} INTEGER")
                    else:
                        conn.execute(f"ALTER TABLE execution_logs ADD COLUMN {col} TEXT")
        
        # テスト用戦略設定を作成
        self.setup_test_strategy_configurations()
    
    def setup_test_strategy_configurations(self):
        """テスト用戦略設定データを作成"""
        with sqlite3.connect(self.test_analysis_db) as conn:
            # strategy_configurationsテーブル作成
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
                (5, 'Conservative - 1h', 'Conservative_ML', '1h', '{}', 'Test strategy 5', 1, 1),  # default
                (6, 'Aggressive Traditional - 1h', 'Aggressive_Traditional', '1h', '{}', 'Test strategy 6', 1, 1),  # default
                (7, 'Inactive Strategy', 'Inactive', '5m', '{}', 'Inactive strategy', 0, 0),  # inactive
            ]
            
            conn.executemany("""
                INSERT OR REPLACE INTO strategy_configurations 
                (id, name, base_strategy, timeframe, parameters, description, is_active, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, strategies)
    
    def test_selective_mode_exact_strategy_execution(self):
        """SELECTIVEモード：選択した戦略のみ実行されることをテスト"""
        print("\n🧪 SELECTIVEモード：選択戦略のみ実行テスト")
        
        # テスト対象のNewSymbolAdditionSystem作成
        with patch('new_symbol_addition_system.AutoSymbolTraining') as mock_trainer:
            mock_instance = MagicMock()
            mock_instance.add_symbol_with_training = AsyncMock(return_value="test_execution_id")
            mock_trainer.return_value = mock_instance
            
            system = NewSymbolAdditionSystem()
            system.analysis_db = self.test_analysis_db
            system.execution_logs_db = self.test_execution_logs_db
            
            # 戦略変換テスト: ID [1, 3] を選択（Aggressive_ML-15m, Balanced-15m）
            strategy_configs = system.get_strategy_configs_for_legacy([1, 3])
            
            print(f"📋 変換された戦略設定数: {len(strategy_configs)}")
            for config in strategy_configs:
                print(f"  - {config['name']}: {config['base_strategy']} + {config['timeframe']}")
            
            # 期待値：選択した2つの戦略のみ
            self.assertEqual(len(strategy_configs), 2, "選択した戦略数と一致すべき")
            
            # 具体的な戦略内容確認
            expected_strategies = [
                ('Aggressive ML - 15m', 'Aggressive_ML', '15m'),
                ('Balanced - 15m', 'Balanced', '15m')
            ]
            
            actual_strategies = [(config['name'], config['base_strategy'], config['timeframe']) 
                               for config in strategy_configs]
            
            for expected in expected_strategies:
                self.assertIn(expected, actual_strategies, f"戦略 {expected} が含まれるべき")
            
            # 意図しない組み合わせが含まれていないことを確認
            unexpected_strategies = [
                ('Aggressive ML - 30m', 'Aggressive_ML', '30m'),  # 選択していない
                ('Balanced - 30m', 'Balanced', '30m'),  # 選択していない
            ]
            
            for unexpected in unexpected_strategies:
                self.assertNotIn(unexpected, actual_strategies, f"戦略 {unexpected} は含まれるべきでない")
    
    def test_custom_mode_exact_strategy_execution(self):
        """CUSTOMモード：選択した戦略のみ実行されることをテスト"""
        print("\n🧪 CUSTOMモード：選択戦略のみ実行テスト")
        
        with patch('new_symbol_addition_system.AutoSymbolTraining') as mock_trainer:
            mock_instance = MagicMock()
            mock_instance.add_symbol_with_training = AsyncMock(return_value="test_execution_id")
            mock_trainer.return_value = mock_instance
            
            system = NewSymbolAdditionSystem()
            system.analysis_db = self.test_analysis_db
            system.execution_logs_db = self.test_execution_logs_db
            
            # ETHの問題を再現：ID [1, 2, 3] を選択
            # 期待：3つの戦略のみ、4つに増えない
            strategy_configs = system.get_strategy_configs_for_legacy([1, 2, 3])
            
            print(f"📋 選択戦略ID: [1, 2, 3]")
            print(f"📋 変換された戦略設定数: {len(strategy_configs)}")
            for config in strategy_configs:
                print(f"  - ID {config['id']}: {config['name']}")
            
            # 期待値：選択した3つの戦略のみ
            self.assertEqual(len(strategy_configs), 3, "選択した3つの戦略のみ実行されるべき")
            
            # ID確認
            actual_ids = [config['id'] for config in strategy_configs]
            expected_ids = [1, 2, 3]
            
            for expected_id in expected_ids:
                self.assertIn(expected_id, actual_ids, f"戦略ID {expected_id} が含まれるべき")
            
            # 戦略4（Balanced-30m）が含まれていないことを確認
            self.assertNotIn(4, actual_ids, "戦略ID 4 は選択していないため含まれるべきでない")
    
    def test_cartesian_product_prevention(self):
        """デカルト積生成防止の詳細テスト"""
        print("\n🧪 デカルト積生成防止テスト")
        
        with patch('new_symbol_addition_system.AutoSymbolTraining'):
            system = NewSymbolAdditionSystem()
            system.analysis_db = self.test_analysis_db
            system.execution_logs_db = self.test_execution_logs_db
            
            # 複数の戦略と時間足を含む選択
            strategy_ids = [1, 2, 3]  # Aggressive_ML-15m, Aggressive_ML-30m, Balanced-15m
            strategy_configs = system.get_strategy_configs_for_legacy(strategy_ids)
            
            # 戦略と時間足の組み合わせを抽出
            strategies = list(set(config['base_strategy'] for config in strategy_configs))
            timeframes = list(set(config['timeframe'] for config in strategy_configs))
            
            print(f"📊 含まれる戦略: {strategies}")
            print(f"📊 含まれる時間足: {timeframes}")
            print(f"📊 デカルト積なら: {len(strategies)} × {len(timeframes)} = {len(strategies) * len(timeframes)}パターン")
            print(f"📊 実際の戦略数: {len(strategy_configs)}パターン")
            
            # デカルト積が生成されていないことを確認
            expected_cartesian_count = len(strategies) * len(timeframes)  # 2 × 2 = 4
            actual_count = len(strategy_configs)  # 3
            
            self.assertLess(actual_count, expected_cartesian_count, 
                          f"デカルト積({expected_cartesian_count})よりも少ない戦略数({actual_count})であるべき")
            
            # 具体的に意図しない組み合わせが含まれていないことを確認
            actual_combinations = [(config['base_strategy'], config['timeframe']) 
                                 for config in strategy_configs]
            
            # 選択した戦略のみ含まれることを確認
            expected_combinations = [
                ('Aggressive_ML', '15m'),  # ID 1
                ('Aggressive_ML', '30m'),  # ID 2
                ('Balanced', '15m'),       # ID 3
            ]
            
            for expected in expected_combinations:
                self.assertIn(expected, actual_combinations, f"選択した組み合わせ {expected} が含まれるべき")
            
            # 意図しない組み合わせが含まれていないことを確認
            unexpected_combination = ('Balanced', '30m')  # 選択していない組み合わせ
            self.assertNotIn(unexpected_combination, actual_combinations, 
                           f"選択していない組み合わせ {unexpected_combination} は含まれるべきでない")
    
    def test_default_mode_unchanged(self):
        """DEFAULTモードは変更されていないことをテスト"""
        print("\n🧪 DEFAULTモード動作不変テスト")
        
        with patch('new_symbol_addition_system.AutoSymbolTraining'):
            system = NewSymbolAdditionSystem()
            system.analysis_db = self.test_analysis_db
            system.execution_logs_db = self.test_execution_logs_db
            
            # DEFAULTモードの戦略変換（空リスト）
            strategies, timeframes = system.convert_strategy_ids_to_legacy_format([])
            
            print(f"📊 DEFAULTモード戦略: {strategies}")
            print(f"📊 DEFAULTモード時間足: {timeframes}")
            
            # is_default=1の戦略が取得されることを確認
            expected_strategies = ['Conservative_ML', 'Aggressive_Traditional']
            expected_timeframes = ['1h']
            
            for strategy in expected_strategies:
                self.assertIn(strategy, strategies, f"デフォルト戦略 {strategy} が含まれるべき")
            
            for timeframe in expected_timeframes:
                self.assertIn(timeframe, timeframes, f"デフォルト時間足 {timeframe} が含まれるべき")
    
    def test_edge_case_duplicate_strategy_ids(self):
        """エッジケース：重複する戦略IDのテスト"""
        print("\n🧪 エッジケース：重複戦略IDテスト")
        
        with patch('new_symbol_addition_system.AutoSymbolTraining'):
            system = NewSymbolAdditionSystem()
            system.analysis_db = self.test_analysis_db
            system.execution_logs_db = self.test_execution_logs_db
            
            # 重複するIDを含むリスト
            strategy_configs = system.get_strategy_configs_for_legacy([1, 1, 2, 2, 1])
            
            print(f"📋 重複ID [1,1,2,2,1] → {len(strategy_configs)}戦略")
            
            # 重複が除去されることを確認
            self.assertEqual(len(strategy_configs), 2, "重複IDは除去されるべき")
            
            actual_ids = [config['id'] for config in strategy_configs]
            expected_ids = [1, 2]
            
            for expected_id in expected_ids:
                self.assertIn(expected_id, actual_ids, f"戦略ID {expected_id} が含まれるべき")
    
    def test_edge_case_invalid_strategy_ids(self):
        """エッジケース：無効な戦略IDのテスト"""
        print("\n🧪 エッジケース：無効戦略IDテスト")
        
        with patch('new_symbol_addition_system.AutoSymbolTraining'):
            system = NewSymbolAdditionSystem()
            system.analysis_db = self.test_analysis_db
            system.execution_logs_db = self.test_execution_logs_db
            
            # 有効IDと無効IDの混合
            strategy_configs = system.get_strategy_configs_for_legacy([1, 999, 2, 888])
            
            print(f"📋 混合ID [1,999,2,888] → {len(strategy_configs)}戦略")
            
            # 有効なIDのみ取得されることを確認
            self.assertEqual(len(strategy_configs), 2, "有効なIDのみ取得されるべき")
            
            actual_ids = [config['id'] for config in strategy_configs]
            valid_ids = [1, 2]
            invalid_ids = [999, 888]
            
            for valid_id in valid_ids:
                self.assertIn(valid_id, actual_ids, f"有効ID {valid_id} が含まれるべき")
            
            for invalid_id in invalid_ids:
                self.assertNotIn(invalid_id, actual_ids, f"無効ID {invalid_id} は含まれるべきでない")
    
    def test_edge_case_inactive_strategies(self):
        """エッジケース：非アクティブ戦略のテスト"""
        print("\n🧪 エッジケース：非アクティブ戦略テスト")
        
        with patch('new_symbol_addition_system.AutoSymbolTraining'):
            system = NewSymbolAdditionSystem()
            system.analysis_db = self.test_analysis_db
            system.execution_logs_db = self.test_execution_logs_db
            
            # アクティブIDと非アクティブIDの混合
            strategy_configs = system.get_strategy_configs_for_legacy([1, 7])  # 7は非アクティブ
            
            print(f"📋 混合ID [1(active),7(inactive)] → {len(strategy_configs)}戦略")
            
            # アクティブなIDのみ取得されることを確認
            self.assertEqual(len(strategy_configs), 1, "アクティブなIDのみ取得されるべき")
            
            actual_ids = [config['id'] for config in strategy_configs]
            self.assertIn(1, actual_ids, "アクティブID 1 が含まれるべき")
            self.assertNotIn(7, actual_ids, "非アクティブID 7 は含まれるべきでない")
    
    def test_edge_case_empty_strategy_list(self):
        """エッジケース：空の戦略リストのテスト"""
        print("\n🧪 エッジケース：空戦略リストテスト")
        
        with patch('new_symbol_addition_system.AutoSymbolTraining'):
            system = NewSymbolAdditionSystem()
            system.analysis_db = self.test_analysis_db
            system.execution_logs_db = self.test_execution_logs_db
            
            # 空リスト
            strategy_configs = system.get_strategy_configs_for_legacy([])
            
            print(f"📋 空リスト [] → {strategy_configs}")
            
            # Noneが返されることを確認
            self.assertIsNone(strategy_configs, "空リストの場合はNoneが返されるべき")
    
    def test_full_integration_selective_mode_execution(self):
        """統合テスト：SELECTIVEモード完全実行フローテスト"""
        print("\n🧪 統合テスト：SELECTIVEモード完全実行フロー")
        
        execution_id = "test_selective_integration"
        symbol = "TESTCOIN"
        selected_strategy_ids = [1, 3]  # Aggressive_ML-15m, Balanced-15m
        
        # execution_logsレコード作成
        with sqlite3.connect(self.test_execution_logs_db) as conn:
            conn.execute("""
                INSERT INTO execution_logs 
                (execution_id, execution_type, symbol, status, timestamp_start, selected_strategy_ids, execution_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (execution_id, "SYMBOL_ADDITION", symbol, "RUNNING", 
                  "2025-06-24T23:00:00", json.dumps(selected_strategy_ids), "selective"))
        
        # NewSymbolAdditionSystemのテスト
        with patch('new_symbol_addition_system.AutoSymbolTraining') as mock_trainer:
            mock_instance = MagicMock()
            mock_instance.add_symbol_with_training = AsyncMock(return_value=execution_id)
            mock_trainer.return_value = mock_instance
            
            system = NewSymbolAdditionSystem()
            system.analysis_db = self.test_analysis_db
            system.execution_logs_db = self.test_execution_logs_db
            
            # execute_symbol_additionを実行
            async def run_test():
                result = await system.execute_symbol_addition(
                    symbol=symbol,
                    execution_id=execution_id,
                    execution_mode=ExecutionMode.SELECTIVE,
                    selected_strategy_ids=selected_strategy_ids
                )
                return result
            
            result = asyncio.run(run_test())
            
            # 成功することを確認
            self.assertTrue(result, "SELECTIVEモード実行が成功するべき")
            
            # add_symbol_with_trainingが正しい引数で呼ばれたことを確認
            mock_instance.add_symbol_with_training.assert_called_once()
            call_args = mock_instance.add_symbol_with_training.call_args
            
            # strategy_configsが渡されていることを確認
            self.assertIsNotNone(call_args[1]['strategy_configs'], "strategy_configsが渡されるべき")
            self.assertIsNone(call_args[1]['selected_strategies'], "selected_strategiesはNoneであるべき")
            self.assertIsNone(call_args[1]['selected_timeframes'], "selected_timeframesはNoneであるべき")
            
            # strategy_configsの内容確認
            strategy_configs = call_args[1]['strategy_configs']
            self.assertEqual(len(strategy_configs), 2, "選択した2つの戦略のみ渡されるべき")
            
            print(f"✅ 渡された戦略設定数: {len(strategy_configs)}")
            for config in strategy_configs:
                print(f"  - ID {config['id']}: {config['name']}")


if __name__ == '__main__':
    unittest.main(verbosity=2)