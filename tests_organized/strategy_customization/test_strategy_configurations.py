#!/usr/bin/env python3
"""
戦略カスタマイズ機能のテストケース

新しい strategy_configurations テーブルとそれに関連する機能のテスト
- 戦略設定の作成・読み取り・更新・削除
- パラメータバリデーション
- 既存データとの互換性
"""

import sys
import os
import sqlite3
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

# BaseTestを使用して安全にテスト
from tests_organized.base_test import BaseTest

class StrategyConfigurationTest(BaseTest):
    """戦略設定テーブルの基本機能テスト"""
    
    def custom_setup(self):
        """戦略設定テスト用のセットアップ"""
        # strategy_configurations テーブル作成
        self.create_strategy_configurations_table()
        
        # テスト用のデフォルト戦略設定
        self.default_strategies = [
            {
                'name': 'Conservative ML - 15m',
                'base_strategy': 'Conservative_ML',
                'timeframe': '15m',
                'parameters': json.dumps({
                    'risk_multiplier': 0.8,
                    'confidence_boost': 0.0,
                    'leverage_cap': 50,
                    'min_risk_reward': 1.1,
                    'stop_loss_percent': 3.5,
                    'take_profit_percent': 8.0
                }),
                'description': 'Conservative strategy for 15m timeframe',
                'is_default': True
            },
            {
                'name': 'Aggressive ML - 1h',
                'base_strategy': 'Aggressive_ML',
                'timeframe': '1h',
                'parameters': json.dumps({
                    'risk_multiplier': 1.2,
                    'confidence_boost': -0.05,
                    'leverage_cap': 100,
                    'min_risk_reward': 1.0,
                    'stop_loss_percent': 5.0,
                    'take_profit_percent': 12.0
                }),
                'description': 'Aggressive strategy for 1h timeframe',
                'is_default': True
            }
        ]
    
    def create_strategy_configurations_table(self):
        """strategy_configurations テーブル作成"""
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    base_strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    description TEXT,
                    created_by TEXT DEFAULT 'system',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_default BOOLEAN DEFAULT 0,
                    
                    UNIQUE(name, base_strategy, timeframe)
                )
            """)
            
            # インデックス作成
            conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_configs_base ON strategy_configurations(base_strategy)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_configs_timeframe ON strategy_configurations(timeframe)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_configs_active ON strategy_configurations(is_active)")
    
    def insert_strategy_config(self, config):
        """戦略設定を挿入"""
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                INSERT INTO strategy_configurations 
                (name, base_strategy, timeframe, parameters, description, is_default, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                config['name'],
                config['base_strategy'],
                config['timeframe'],
                config['parameters'],
                config.get('description', ''),
                config.get('is_default', False),
                config.get('created_by', 'test')
            ))
            return cursor.lastrowid
    
    def test_create_strategy_configuration(self):
        """戦略設定作成テスト"""
        print("\n🧪 戦略設定作成テスト")
        
        # デフォルト戦略の作成
        for default_strategy in self.default_strategies:
            strategy_id = self.insert_strategy_config(default_strategy)
            
            self.assertIsNotNone(strategy_id, "戦略設定IDが取得できません")
            self.assertGreater(strategy_id, 0, "戦略設定IDが正の整数ではありません")
            
            print(f"   ✅ 戦略設定作成成功: ID={strategy_id}, Name={default_strategy['name']}")
        
        # 作成された戦略設定の確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM strategy_configurations")
            count = cursor.fetchone()[0]
            
            self.assertEqual(count, len(self.default_strategies), "作成された戦略設定数が期待値と一致しません")
            print(f"   ✅ 作成確認: {count}件の戦略設定")
    
    def test_strategy_parameters_validation(self):
        """戦略パラメータバリデーションテスト"""
        print("\n🧪 戦略パラメータバリデーションテスト")
        
        # 有効なパラメータ
        valid_parameters = {
            'risk_multiplier': 1.5,
            'confidence_boost': -0.1,
            'leverage_cap': 75,
            'min_risk_reward': 1.2,
            'stop_loss_percent': 4.0,
            'take_profit_percent': 10.0,
            'custom_sltp_calculator': 'CustomCalculator',
            'additional_filters': {
                'min_volume_usd': 2000000,
                'btc_correlation_max': 0.8
            }
        }
        
        valid_config = {
            'name': 'Custom Test Strategy',
            'base_strategy': 'Custom_ML',
            'timeframe': '30m',
            'parameters': json.dumps(valid_parameters),
            'description': 'Custom test strategy with complex parameters'
        }
        
        strategy_id = self.insert_strategy_config(valid_config)
        self.assertIsNotNone(strategy_id, "有効なパラメータでの戦略作成が失敗しました")
        
        # 作成された戦略の詳細確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT name, base_strategy, timeframe, parameters 
                FROM strategy_configurations 
                WHERE id = ?
            """, (strategy_id,))
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "作成された戦略設定が見つかりません")
            
            name, base_strategy, timeframe, parameters_json = result
            parameters = json.loads(parameters_json)
            
            self.assertEqual(name, valid_config['name'])
            self.assertEqual(base_strategy, valid_config['base_strategy'])
            self.assertEqual(timeframe, valid_config['timeframe'])
            self.assertEqual(parameters['risk_multiplier'], 1.5)
            self.assertEqual(parameters['additional_filters']['min_volume_usd'], 2000000)
            
            print(f"   ✅ 複雑なパラメータでの戦略作成成功: {name}")
    
    def test_duplicate_strategy_prevention(self):
        """重複戦略防止テスト"""
        print("\n🧪 重複戦略防止テスト")
        
        # 最初の戦略作成
        first_config = {
            'name': 'Duplicate Test',
            'base_strategy': 'Conservative_ML',
            'timeframe': '15m',
            'parameters': json.dumps({'risk_multiplier': 1.0}),
            'description': 'First strategy'
        }
        
        first_id = self.insert_strategy_config(first_config)
        self.assertIsNotNone(first_id, "最初の戦略作成が失敗しました")
        print(f"   ✅ 最初の戦略作成成功: ID={first_id}")
        
        # 同じ名前・戦略・時間足での重複作成テスト
        duplicate_config = {
            'name': 'Duplicate Test',
            'base_strategy': 'Conservative_ML',
            'timeframe': '15m',
            'parameters': json.dumps({'risk_multiplier': 2.0}),  # パラメータは異なる
            'description': 'Duplicate strategy'
        }
        
        # 重複作成は失敗するはず
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_strategy_config(duplicate_config)
        
        print(f"   ✅ 重複防止機能正常動作: UNIQUE制約が有効")
    
    def test_strategy_config_queries(self):
        """戦略設定クエリテスト"""
        print("\n🧪 戦略設定クエリテスト")
        
        # テストデータ作成
        test_strategies = [
            {
                'name': 'BTC Optimized',
                'base_strategy': 'Conservative_ML',
                'timeframe': '1h',
                'parameters': json.dumps({'risk_multiplier': 0.9}),
                'description': 'BTC optimized strategy'
            },
            {
                'name': 'ETH Aggressive',
                'base_strategy': 'Aggressive_ML',
                'timeframe': '30m',
                'parameters': json.dumps({'risk_multiplier': 1.5}),
                'description': 'ETH aggressive strategy'
            },
            {
                'name': 'Generic Conservative',
                'base_strategy': 'Conservative_ML',
                'timeframe': '15m',
                'parameters': json.dumps({'risk_multiplier': 0.8}),
                'description': 'Generic conservative strategy'
            }
        ]
        
        strategy_ids = []
        for strategy in test_strategies:
            strategy_id = self.insert_strategy_config(strategy)
            strategy_ids.append(strategy_id)
        
        # 1. 基本戦略別でのクエリ
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM strategy_configurations 
                WHERE base_strategy = 'Conservative_ML'
            """)
            conservative_count = cursor.fetchone()[0]
            
            self.assertGreaterEqual(conservative_count, 2, "Conservative_ML戦略が期待数存在しません")
            print(f"   ✅ Conservative_ML戦略: {conservative_count}件")
        
        # 2. 時間足別でのクエリ
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT name, base_strategy FROM strategy_configurations 
                WHERE timeframe = '1h'
                ORDER BY name
            """)
            hour_strategies = cursor.fetchall()
            
            self.assertGreater(len(hour_strategies), 0, "1h戦略が見つかりません")
            print(f"   ✅ 1h戦略: {len(hour_strategies)}件")
            for name, base_strategy in hour_strategies:
                print(f"      - {name} ({base_strategy})")
        
        # 3. アクティブな戦略のみクエリ
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM strategy_configurations 
                WHERE is_active = 1
            """)
            active_count = cursor.fetchone()[0]
            
            # 各テストは独立して実行されるため、現在のテストで作成された戦略数のみチェック
            expected_count = len(test_strategies)
            self.assertEqual(active_count, expected_count, f"アクティブ戦略数が期待値と一致しません: 実際={active_count}, 期待={expected_count}")
            print(f"   ✅ アクティブ戦略: {active_count}件")
    
    def test_strategy_config_update(self):
        """戦略設定更新テスト"""
        print("\n🧪 戦略設定更新テスト")
        
        # 更新用戦略作成
        original_config = {
            'name': 'Update Test Strategy',
            'base_strategy': 'Balanced',
            'timeframe': '30m',
            'parameters': json.dumps({'risk_multiplier': 1.0}),
            'description': 'Original description'
        }
        
        strategy_id = self.insert_strategy_config(original_config)
        print(f"   📝 更新対象戦略作成: ID={strategy_id}")
        
        # パラメータ更新
        new_parameters = {
            'risk_multiplier': 1.3,
            'confidence_boost': -0.05,
            'leverage_cap': 80,
            'custom_filter': 'updated'
        }
        
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                UPDATE strategy_configurations 
                SET parameters = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                json.dumps(new_parameters),
                'Updated description',
                strategy_id
            ))
        
        # 更新結果確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT parameters, description FROM strategy_configurations 
                WHERE id = ?
            """, (strategy_id,))
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "更新された戦略設定が見つかりません")
            
            parameters_json, description = result
            updated_parameters = json.loads(parameters_json)
            
            self.assertEqual(updated_parameters['risk_multiplier'], 1.3)
            self.assertEqual(updated_parameters['custom_filter'], 'updated')
            self.assertEqual(description, 'Updated description')
            
            print(f"   ✅ 戦略設定更新成功: パラメータとdescription更新確認")
    
    def test_strategy_config_deactivation(self):
        """戦略設定非アクティブ化テスト"""
        print("\n🧪 戦略設定非アクティブ化テスト")
        
        # 非アクティブ化用戦略作成
        deactivate_config = {
            'name': 'Deactivate Test',
            'base_strategy': 'Test_Strategy',
            'timeframe': '5m',
            'parameters': json.dumps({'test': True}),
            'description': 'Strategy to be deactivated'
        }
        
        strategy_id = self.insert_strategy_config(deactivate_config)
        
        # 非アクティブ化
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                UPDATE strategy_configurations 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (strategy_id,))
        
        # 非アクティブ化確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT is_active FROM strategy_configurations 
                WHERE id = ?
            """, (strategy_id,))
            is_active = cursor.fetchone()[0]
            
            self.assertEqual(is_active, 0, "戦略が非アクティブ化されていません")
            print(f"   ✅ 戦略非アクティブ化成功: ID={strategy_id}")
        
        # アクティブな戦略のみのクエリでは除外されることを確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM strategy_configurations 
                WHERE is_active = 1 AND id = ?
            """, (strategy_id,))
            active_count = cursor.fetchone()[0]
            
            self.assertEqual(active_count, 0, "非アクティブ戦略がアクティブクエリに含まれています")
            print(f"   ✅ アクティブクエリでの除外確認")

def run_strategy_configuration_tests():
    """戦略設定テスト実行"""
    import unittest
    
    # テストスイート作成
    suite = unittest.TestSuite()
    test_class = StrategyConfigurationTest
    
    # 個別テストメソッドを追加
    suite.addTest(test_class('test_create_strategy_configuration'))
    suite.addTest(test_class('test_strategy_parameters_validation'))
    suite.addTest(test_class('test_duplicate_strategy_prevention'))
    suite.addTest(test_class('test_strategy_config_queries'))
    suite.addTest(test_class('test_strategy_config_update'))
    suite.addTest(test_class('test_strategy_config_deactivation'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "="*60)
    print("🧪 戦略設定テスト結果")
    print("="*60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️ エラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 すべての戦略設定テストが成功しました！")
        print("strategy_configurations テーブルの基本機能は正常に動作しています。")
    else:
        print("\n⚠️ 一部のテストが失敗しました。")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_strategy_configuration_tests()
    sys.exit(0 if success else 1)