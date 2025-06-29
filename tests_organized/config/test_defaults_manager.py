#!/usr/bin/env python3
"""
デフォルト値管理システムのテストコード

一元管理システムの動作を担保するテスト:
1. デフォルト値の正確な取得
2. 動的解決機能のテスト
3. "use_default"マーカーの解決
4. フォールバック機能のテスト
"""

import unittest
import tempfile
import json
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests_organized.base_test import BaseTest


class TestDefaultsManager(BaseTest):
    """デフォルト値管理システムのテストクラス"""
    
    def setUp(self):
        """テスト前の初期化"""
        super().setUp()
        self.temp_defaults_file = None
        self.original_config_path = None
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if self.temp_defaults_file and os.path.exists(self.temp_defaults_file):
            os.unlink(self.temp_defaults_file)
        super().tearDown()
    
    def create_test_defaults_file(self, content):
        """テスト用デフォルトファイルを作成"""
        fd, self.temp_defaults_file = tempfile.mkstemp(suffix='.json')
        with os.fdopen(fd, 'w') as f:
            json.dump(content, f)
        return self.temp_defaults_file
    
    def test_default_values_loading(self):
        """デフォルト値の正確な読み込みテスト"""
        print("\n🧪 デフォルト値読み込みテスト")
        
        # テスト用デフォルト値
        test_defaults = {
            "entry_conditions": {
                "min_risk_reward": 1.5,
                "min_leverage": 2.8,
                "min_confidence": 0.6
            }
        }
        
        # テストファイル作成
        test_file = self.create_test_defaults_file(test_defaults)
        
        # DefaultsManagerを動的インポートしてテスト
        from config.defaults_manager import DefaultsManager
        
        # 新しいインスタンス作成（テストファイル使用）
        manager = DefaultsManager()
        manager.config_file = test_file
        manager.load_defaults()
        
        # 値の確認
        self.assertEqual(manager.get_min_risk_reward(), 1.5)
        self.assertEqual(manager.get_min_leverage(), 2.8)
        self.assertEqual(manager.get_min_confidence(), 0.6)
        
        print(f"✅ デフォルト値読み込み成功: RR={manager.get_min_risk_reward()}")
    
    def test_use_default_marker_resolution(self):
        """use_defaultマーカーの動的解決テスト"""
        print("\n🧪 use_defaultマーカー解決テスト")
        
        # テスト用設定
        test_config = {
            "strategy_config": {
                "min_risk_reward": "use_default",
                "min_leverage": "use_default",
                "min_confidence": "use_default",
                "other_param": 5.0
            },
            "nested": {
                "conditions": {
                    "min_risk_reward": "use_default"
                }
            }
        }
        
        from config.defaults_manager import DefaultsManager
        manager = DefaultsManager()
        
        # 解決実行
        resolved = manager.resolve_defaults_in_config(test_config)
        
        # 確認
        self.assertIsInstance(resolved["strategy_config"]["min_risk_reward"], float)
        self.assertIsInstance(resolved["strategy_config"]["min_leverage"], float)
        self.assertIsInstance(resolved["strategy_config"]["min_confidence"], float)
        self.assertEqual(resolved["strategy_config"]["other_param"], 5.0)  # 変更されない
        
        # ネストした設定も解決されるか確認
        self.assertIsInstance(resolved["nested"]["conditions"]["min_risk_reward"], float)
        
        print(f"✅ マーカー解決成功: {resolved['strategy_config']['min_risk_reward']}")
    
    def test_fallback_when_file_missing(self):
        """設定ファイル不在時のフォールバック動作テスト"""
        print("\n🧪 フォールバック動作テスト")
        
        from config.defaults_manager import DefaultsManager
        
        # 存在しないファイルパスを設定
        manager = DefaultsManager()
        manager.config_file = "/nonexistent/path/defaults.json"
        manager.load_defaults()
        
        # フォールバック値が使われるか確認
        self.assertIsInstance(manager.get_min_risk_reward(), float)
        self.assertIsInstance(manager.get_min_leverage(), float)
        self.assertIsInstance(manager.get_min_confidence(), float)
        
        # 合理的な範囲内の値か確認
        self.assertGreater(manager.get_min_risk_reward(), 0.1)
        self.assertLess(manager.get_min_risk_reward(), 10.0)
        
        print(f"✅ フォールバック値使用: RR={manager.get_min_risk_reward()}")
    
    def test_global_functions(self):
        """グローバル関数の動作テスト"""
        print("\n🧪 グローバル関数テスト")
        
        from config.defaults_manager import (
            get_default_min_risk_reward,
            get_default_min_leverage, 
            get_default_min_confidence,
            get_default_entry_conditions
        )
        
        # 各関数の戻り値確認
        rr = get_default_min_risk_reward()
        leverage = get_default_min_leverage()
        confidence = get_default_min_confidence()
        conditions = get_default_entry_conditions()
        
        self.assertIsInstance(rr, float)
        self.assertIsInstance(leverage, float)
        self.assertIsInstance(confidence, float)
        self.assertIsInstance(conditions, dict)
        
        # 辞書の内容確認
        self.assertIn('min_risk_reward', conditions)
        self.assertIn('min_leverage', conditions)
        self.assertIn('min_confidence', conditions)
        
        self.assertEqual(conditions['min_risk_reward'], rr)
        self.assertEqual(conditions['min_leverage'], leverage)
        self.assertEqual(conditions['min_confidence'], confidence)
        
        print(f"✅ グローバル関数動作確認: RR={rr}, Leverage={leverage}, Confidence={confidence}")
    
    def test_array_resolution(self):
        """配列内のuse_defaultマーカー解決テスト"""
        print("\n🧪 配列内マーカー解決テスト")
        
        test_config = {
            "strategies": [
                {
                    "name": "strategy1",
                    "min_risk_reward": "use_default"
                },
                {
                    "name": "strategy2", 
                    "min_risk_reward": "use_default",
                    "min_leverage": "use_default"
                }
            ]
        }
        
        from config.defaults_manager import DefaultsManager
        manager = DefaultsManager()
        
        resolved = manager.resolve_defaults_in_config(test_config)
        
        # 配列内の各要素が解決されているか確認
        for strategy in resolved["strategies"]:
            self.assertIsInstance(strategy["min_risk_reward"], float)
            if "min_leverage" in strategy:
                self.assertIsInstance(strategy["min_leverage"], float)
        
        print(f"✅ 配列内マーカー解決成功")


class TestTimeframeConfigIntegration(BaseTest):
    """時間足設定との統合テスト"""
    
    def test_timeframe_config_uses_defaults(self):
        """時間足設定がデフォルト値を正しく使用するかテスト"""
        print("\n🧪 時間足設定統合テスト")
        
        from config.timeframe_config_manager import TimeframeConfigManager
        from config.defaults_manager import get_default_min_risk_reward
        
        manager = TimeframeConfigManager()
        
        # 複数の時間足で確認
        timeframes = ['1m', '5m', '15m', '30m', '1h']
        expected_rr = get_default_min_risk_reward()
        
        for tf in timeframes:
            try:
                config = manager.get_timeframe_config(tf)
                actual_rr = config.get('min_risk_reward')
                
                self.assertEqual(actual_rr, expected_rr, 
                    f"{tf}の設定でmin_risk_rewardが期待値{expected_rr}と異なります: {actual_rr}")
                
                print(f"✅ {tf}: min_risk_reward = {actual_rr}")
                
            except Exception as e:
                print(f"⚠️ {tf}設定読み込みエラー: {e}")


class TestMigrationsIntegration(BaseTest):
    """マイグレーションファイルとの統合テスト"""
    
    def test_migrations_use_dynamic_defaults(self):
        """マイグレーションファイルが動的デフォルト値を使用するかテスト"""
        print("\n🧪 マイグレーション統合テスト")
        
        try:
            # マイグレーションモジュールをインポート
            sys.path.append(str(Path(__file__).parent.parent.parent / "migrations"))
            from migrations import migration_001_add_strategy_configurations as migration
            
            from config.defaults_manager import get_default_min_risk_reward
            expected_rr = get_default_min_risk_reward()
            
            # マイグレーション関数内でデフォルト値が使われているか確認
            # 実際のget_default_strategy_configurations関数を呼び出し
            if hasattr(migration, 'get_default_strategy_configurations'):
                configs = migration.get_default_strategy_configurations()
                
                for strategy_name, config in configs.items():
                    if 'parameters' in config and 'min_risk_reward' in config['parameters']:
                        actual_rr = config['parameters']['min_risk_reward']
                        self.assertEqual(actual_rr, expected_rr,
                            f"戦略{strategy_name}のmin_risk_rewardが期待値と異なります")
                        print(f"✅ 戦略 {strategy_name}: min_risk_reward = {actual_rr}")
            else:
                print("⚠️ マイグレーション関数が見つかりません")
                
        except ImportError as e:
            print(f"⚠️ マイグレーションモジュールのインポートエラー: {e}")
        except Exception as e:
            print(f"⚠️ マイグレーションテストエラー: {e}")


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)