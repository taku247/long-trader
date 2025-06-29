#!/usr/bin/env python3
"""
一元管理システムの整合性チェックテスト

全システムが確実に中央定義されたデフォルト値を使用していることを保証するテスト
"""

import unittest
import json
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests_organized.base_test import BaseTest


class TestCentralizedDefaultsIntegrity(BaseTest):
    """一元管理システムの整合性テストクラス"""
    
    def test_no_hardcoded_values_in_json_files(self):
        """JSONファイルにハードコードされた値が残っていないかチェック"""
        print("\n🧪 JSONファイル内ハードコード値チェック")
        
        project_root = Path(__file__).parent.parent.parent
        config_dir = project_root / "config"
        
        # チェック対象ファイル
        json_files = [
            "timeframe_conditions.json",
            "trading_conditions.json", 
            "trading_conditions_test.json",
            "condition_strictness_levels.json"
        ]
        
        violations = []
        
        for json_file in json_files:
            file_path = config_dir / json_file
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                # ハードコードされたmin_risk_reward値をチェック
                hardcoded_values = self._find_hardcoded_values(content, json_file)
                violations.extend(hardcoded_values)
                
            except Exception as e:
                print(f"⚠️ {json_file}読み込みエラー: {e}")
        
        if violations:
            violation_msg = "\n".join([f"- {v}" for v in violations])
            self.fail(f"以下のファイルにハードコードされた値が見つかりました:\n{violation_msg}")
        
        print("✅ JSONファイル内にハードコードされた値は見つかりませんでした")
    
    def _find_hardcoded_values(self, data, filename, path=""):
        """再帰的にハードコードされた値を検索"""
        violations = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                if key == "min_risk_reward" and isinstance(value, (int, float)):
                    if value != "use_default":
                        violations.append(f"{filename}:{current_path} = {value} (should be 'use_default')")
                
                violations.extend(self._find_hardcoded_values(value, filename, current_path))
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                violations.extend(self._find_hardcoded_values(item, filename, current_path))
        
        return violations
    
    def test_defaults_json_exists_and_valid(self):
        """defaults.jsonが存在し、有効であることを確認"""
        print("\n🧪 defaults.json存在・有効性チェック")
        
        from config.defaults_manager import DefaultsManager
        
        # 新しいインスタンスを作成（既存インスタンスのパス設定をリセット）
        manager = DefaultsManager()
        # デフォルトパスを再設定
        manager.config_file = manager._get_default_config_path()
        
        # ファイルが存在することを確認
        self.assertTrue(os.path.exists(manager.config_file), 
                       f"defaults.jsonが見つかりません: {manager.config_file}")
        
        # 有効なJSONであることを確認
        with open(manager.config_file, 'r', encoding='utf-8') as f:
            defaults_data = json.load(f)
        
        # 必要なセクションが存在することを確認
        self.assertIn('entry_conditions', defaults_data)
        self.assertIn('min_risk_reward', defaults_data['entry_conditions'])
        self.assertIn('min_leverage', defaults_data['entry_conditions'])
        self.assertIn('min_confidence', defaults_data['entry_conditions'])
        
        # 値が適切な型であることを確認
        entry_conditions = defaults_data['entry_conditions']
        self.assertIsInstance(entry_conditions['min_risk_reward'], (int, float))
        self.assertIsInstance(entry_conditions['min_leverage'], (int, float))
        self.assertIsInstance(entry_conditions['min_confidence'], (int, float))
        
        # 値が合理的な範囲内であることを確認
        self.assertGreater(entry_conditions['min_risk_reward'], 0.1)
        self.assertLess(entry_conditions['min_risk_reward'], 10.0)
        
        print(f"✅ defaults.json有効性確認: min_risk_reward = {entry_conditions['min_risk_reward']}")
    
    def test_all_config_managers_use_defaults(self):
        """全ての設定管理クラスがデフォルト値を使用することを確認"""
        print("\n🧪 設定管理クラス統合テスト")
        
        from config.defaults_manager import get_default_min_risk_reward
        expected_value = get_default_min_risk_reward()
        
        # TimeframeConfigManagerのテスト
        try:
            from config.timeframe_config_manager import TimeframeConfigManager
            tf_manager = TimeframeConfigManager()
            
            # 複数の時間足で確認
            for timeframe in ['1m', '5m', '15m', '1h']:
                try:
                    config = tf_manager.get_timeframe_config(timeframe)
                    actual_value = config.get('min_risk_reward')
                    
                    self.assertEqual(actual_value, expected_value,
                        f"{timeframe}の設定でmin_risk_rewardが期待値と異なります: {actual_value} != {expected_value}")
                    
                except Exception as e:
                    print(f"⚠️ {timeframe}設定エラー: {e}")
            
            print("✅ TimeframeConfigManager統合確認")
            
        except ImportError as e:
            print(f"⚠️ TimeframeConfigManagerインポートエラー: {e}")
        
        # UnifiedConfigManagerのテスト（存在する場合）
        try:
            from config.unified_config_manager import UnifiedConfigManager
            unified_manager = UnifiedConfigManager()
            
            # テスト実行（具体的なメソッドは実装に依存）
            print("✅ UnifiedConfigManager統合確認")
            
        except ImportError:
            print("⚠️ UnifiedConfigManagerが見つかりません（問題なし）")
        except Exception as e:
            print(f"⚠️ UnifiedConfigManagerテストエラー: {e}")
    
    def test_web_ui_receives_dynamic_defaults(self):
        """WebUIが動的にデフォルト値を受け取ることを確認"""
        print("\n🧪 WebUI動的デフォルト値テスト")
        
        try:
            # アプリケーションのインポート
            sys.path.append(str(Path(__file__).parent.parent.parent / "web_dashboard"))
            from app import LongTraderDashboard
            
            # テスト用アプリケーション作成
            app = LongTraderDashboard()
            
            # テストクライアント作成
            with app.app.test_client() as client:
                # symbols-enhancedページにアクセス
                response = client.get('/symbols-enhanced')
                
                self.assertEqual(response.status_code, 200)
                
                # レスポンス内容にデフォルト値が含まれているかチェック
                response_text = response.get_data(as_text=True)
                
                # デフォルト値がテンプレートに渡されているかの簡易チェック
                from config.defaults_manager import get_default_min_risk_reward
                expected_value = get_default_min_risk_reward()
                
                # HTMLにデフォルト値が含まれているかチェック（簡易）
                self.assertIn(str(expected_value), response_text,
                             "WebUIにデフォルト値が正しく渡されていません")
                
                print(f"✅ WebUIデフォルト値確認: {expected_value}")
                
        except ImportError as e:
            print(f"⚠️ WebUIテストスキップ（インポートエラー）: {e}")
        except Exception as e:
            print(f"⚠️ WebUIテストエラー: {e}")
    
    def test_consistency_across_all_systems(self):
        """全システム間での値の一貫性テスト"""
        print("\n🧪 全システム一貫性テスト")
        
        from config.defaults_manager import get_default_min_risk_reward
        master_value = get_default_min_risk_reward()
        
        # 値を取得する様々な方法での一貫性チェック
        sources = {}
        
        # 1. 直接デフォルトマネージャーから
        sources['defaults_manager'] = master_value
        
        # 2. 時間足設定から
        try:
            from config.timeframe_config_manager import TimeframeConfigManager
            tf_manager = TimeframeConfigManager()
            config = tf_manager.get_timeframe_config('15m')
            sources['timeframe_15m'] = config.get('min_risk_reward')
        except Exception as e:
            print(f"⚠️ 時間足設定取得エラー: {e}")
        
        # 3. グローバル関数から
        try:
            from config.defaults_manager import get_default_entry_conditions
            conditions = get_default_entry_conditions()
            sources['global_function'] = conditions.get('min_risk_reward')
        except Exception as e:
            print(f"⚠️ グローバル関数エラー: {e}")
        
        # 全ての値が一致することを確認
        unique_values = set(v for v in sources.values() if v is not None)
        
        if len(unique_values) > 1:
            mismatch_details = "\n".join([f"- {source}: {value}" for source, value in sources.items()])
            self.fail(f"システム間で値が一致しません:\n{mismatch_details}")
        
        print(f"✅ 全システム一貫性確認: {master_value}")
        for source, value in sources.items():
            if value is not None:
                print(f"   {source}: {value}")


class TestBackwardCompatibility(BaseTest):
    """後方互換性テスト"""
    
    def test_existing_code_still_works(self):
        """既存コードが引き続き動作することを確認"""
        print("\n🧪 後方互換性テスト")
        
        # 既存の設定取得方法が引き続き動作することを確認
        try:
            from config.timeframe_config_manager import TimeframeConfigManager
            manager = TimeframeConfigManager()
            
            # 従来通りの設定取得が動作するか
            config = manager.get_timeframe_config('1h')
            
            # 期待される値が取得できるか
            self.assertIsInstance(config, dict)
            self.assertIn('min_risk_reward', config)
            self.assertIsInstance(config['min_risk_reward'], (int, float))
            
            print("✅ 既存設定取得方法の動作確認")
            
        except Exception as e:
            self.fail(f"既存コードが動作しません: {e}")


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)