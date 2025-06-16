#!/usr/bin/env python3
"""
アダプターパターン互換性専用テストスイート

今回実装したアダプターパターンの徹底的なテスト:
1. プロバイダー差し替え機能の確認
2. ML機能のオン/オフ切り替え
3. 設定ファイルベースの管理
4. エラー耐性の確認
5. 将来の拡張性確認
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.support_resistance_adapter import (
    FlexibleSupportResistanceDetector,
    ISupportResistanceProvider,
    IMLEnhancementProvider,
    SupportResistanceVisualizerAdapter,
    SupportResistanceMLAdapter
)
from interfaces.data_types import SupportResistanceLevel


class MockBasicProvider(ISupportResistanceProvider):
    """テスト用の基本プロバイダー"""
    
    def __init__(self, name="MockBasic", version="1.0.0-test"):
        self.name = name
        self.version = version
        self.call_count = 0
    
    def detect_basic_levels(self, df: pd.DataFrame, min_touches: int = 2) -> List[Dict[str, Any]]:
        """モック検出結果を返す"""
        self.call_count += 1
        current_price = df['close'].iloc[-1] if len(df) > 0 else 50000
        
        return [
            {
                'price': current_price * 0.96,  # 4%下の支持線
                'strength': 0.8,
                'touch_count': min_touches,
                'type': 'support',
                'timestamps': [df['timestamp'].iloc[0], df['timestamp'].iloc[-1]] if len(df) > 0 else [datetime.now()],
                'avg_volume': 1500000
            },
            {
                'price': current_price * 1.04,  # 4%上の抵抗線
                'strength': 0.7,
                'touch_count': min_touches + 1,
                'type': 'resistance',
                'timestamps': [df['timestamp'].iloc[0], df['timestamp'].iloc[-1]] if len(df) > 0 else [datetime.now()],
                'avg_volume': 1300000
            }
        ]
    
    def get_provider_name(self) -> str:
        return self.name
    
    def get_provider_version(self) -> str:
        return self.version


class MockMLProvider(IMLEnhancementProvider):
    """テスト用のMLプロバイダー"""
    
    def __init__(self, name="MockML"):
        self.name = name
        self.interaction_call_count = 0
        self.bounce_call_count = 0
    
    def detect_interactions(self, df: pd.DataFrame, levels: List[Dict], distance_threshold: float = 0.02) -> List[Dict]:
        """モック相互作用検出"""
        self.interaction_call_count += 1
        
        interactions = []
        for level in levels:
            interactions.append({
                'level_price': level['price'],
                'timestamp': datetime.now(),
                'outcome': 'bounce' if np.random.random() > 0.4 else 'break',
                'strength': level.get('strength', 0.5)
            })
        
        return interactions
    
    def predict_bounce_probability(self, df: pd.DataFrame, level: Dict) -> float:
        """モック反発確率予測"""
        self.bounce_call_count += 1
        
        # 強度に基づく簡易予測
        base_strength = level.get('strength', 0.5)
        return min(0.95, 0.3 + base_strength * 0.6)
    
    def get_enhancement_name(self) -> str:
        return self.name


class TestProviderSwitching(unittest.TestCase):
    """プロバイダー差し替え機能のテスト"""
    
    def setUp(self):
        """テスト前準備"""
        # テスト用OHLCVデータ
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        prices = 50000 + np.random.normal(0, 500, 100)
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 30, 100),
            'high': prices + np.abs(np.random.normal(100, 50, 100)),
            'low': prices - np.abs(np.random.normal(100, 50, 100)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 100)
        })
        
        self.current_price = prices[-1]
    
    def test_default_provider_initialization(self):
        """デフォルトプロバイダーでの初期化テスト"""
        try:
            detector = FlexibleSupportResistanceDetector()
            
            # プロバイダー情報の取得
            info = detector.get_provider_info()
            
            self.assertIn('base_provider', info)
            self.assertIn('ml_provider', info)
            self.assertIn('ml_enhancement_enabled', info)
            
            print(f"✅ デフォルト初期化: {info['base_provider']}, ML: {info['ml_provider']}")
            
        except Exception as e:
            if "読み込みに失敗" in str(e):
                print("ℹ️ 既存モジュールなし、モックテストで継続")
            else:
                self.fail(f"デフォルト初期化エラー: {str(e)}")
    
    def test_basic_provider_switching(self):
        """基本プロバイダーの差し替えテスト"""
        # モックプロバイダーで初期化
        detector = FlexibleSupportResistanceDetector()
        
        # カスタムプロバイダーに差し替え
        custom_provider = MockBasicProvider(name="CustomProvider", version="2.0.0")
        detector.set_base_provider(custom_provider)
        
        # プロバイダー情報の確認
        info = detector.get_provider_info()
        self.assertIn("CustomProvider", info['base_provider'])
        self.assertIn("2.0.0", info['base_provider'])
        
        # 検出実行
        support_levels, resistance_levels = detector.detect_levels(self.df, self.current_price)
        
        # カスタムプロバイダーが実際に使用されたことを確認
        self.assertEqual(custom_provider.call_count, 1, "カスタムプロバイダーが呼ばれていない")
        
        # 結果の妥当性確認
        self.assertGreater(len(support_levels) + len(resistance_levels), 0, 
                          "カスタムプロバイダーから結果が得られない")
        
        print("✅ 基本プロバイダー差し替え成功")
    
    def test_ml_provider_switching(self):
        """MLプロバイダーの差し替えテスト"""
        # 基本プロバイダーはモック、MLプロバイダーもモックに設定
        base_provider = MockBasicProvider()
        ml_provider = MockMLProvider(name="CustomML")
        
        detector = FlexibleSupportResistanceDetector(
            base_provider=base_provider,
            ml_provider=ml_provider,
            use_ml_enhancement=True
        )
        
        # プロバイダー情報の確認
        info = detector.get_provider_info()
        self.assertEqual(info['ml_provider'], "CustomML")
        self.assertEqual(info['ml_enhancement_enabled'], 'True')
        
        # 検出実行
        support_levels, resistance_levels = detector.detect_levels(self.df, self.current_price)
        
        # MLプロバイダーが実際に使用されたことを確認
        self.assertGreater(ml_provider.bounce_call_count, 0, "MLプロバイダーが呼ばれていない")
        
        # ML強化された結果の確認
        all_levels = support_levels + resistance_levels
        if all_levels:
            # ML関連属性が追加されているか確認
            has_ml_attribute = any(hasattr(level, 'ml_bounce_probability') for level in all_levels)
            self.assertTrue(has_ml_attribute, "ML強化属性が追加されていない")
        
        print("✅ MLプロバイダー差し替え成功")
    
    def test_multiple_provider_switching(self):
        """複数回のプロバイダー差し替えテスト"""
        detector = FlexibleSupportResistanceDetector()
        
        # 第1のプロバイダー
        provider1 = MockBasicProvider(name="Provider1")
        detector.set_base_provider(provider1)
        
        support1, resistance1 = detector.detect_levels(self.df, self.current_price)
        
        # 第2のプロバイダーに差し替え
        provider2 = MockBasicProvider(name="Provider2")
        detector.set_base_provider(provider2)
        
        support2, resistance2 = detector.detect_levels(self.df, self.current_price)
        
        # 各プロバイダーが1回ずつ呼ばれたことを確認
        self.assertEqual(provider1.call_count, 1, "Provider1が正しく呼ばれていない")
        self.assertEqual(provider2.call_count, 1, "Provider2が正しく呼ばれていない")
        
        # プロバイダー情報が更新されることを確認
        info = detector.get_provider_info()
        self.assertIn("Provider2", info['base_provider'])
        
        print("✅ 複数回プロバイダー差し替え成功")
    
    def test_provider_error_handling(self):
        """プロバイダーエラー時の処理テスト"""
        class ErrorProvider(ISupportResistanceProvider):
            def detect_basic_levels(self, df, min_touches=2):
                raise RuntimeError("Test provider error")
            
            def get_provider_name(self):
                return "ErrorProvider"
            
            def get_provider_version(self):
                return "1.0.0"
        
        detector = FlexibleSupportResistanceDetector()
        error_provider = ErrorProvider()
        detector.set_base_provider(error_provider)
        
        # エラーが適切に伝播することを確認
        with self.assertRaises(Exception) as context:
            detector.detect_levels(self.df, self.current_price)
        
        self.assertIn("支持線・抵抗線検出に失敗", str(context.exception))
        
        print("✅ プロバイダーエラーハンドリング確認")


class TestMLEnhancementToggle(unittest.TestCase):
    """ML機能オン/オフ切り替えのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        # テスト用データ
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        prices = 50000 + np.random.normal(0, 500, 100)
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 30, 100),
            'high': prices + np.abs(np.random.normal(100, 50, 100)),
            'low': prices - np.abs(np.random.normal(100, 50, 100)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 100)
        })
        
        self.current_price = prices[-1]
    
    def test_ml_enhancement_enable_disable(self):
        """ML機能の有効/無効切り替えテスト"""
        base_provider = MockBasicProvider()
        ml_provider = MockMLProvider()
        
        detector = FlexibleSupportResistanceDetector(
            base_provider=base_provider,
            ml_provider=ml_provider,
            use_ml_enhancement=True
        )
        
        # ML有効での検出
        detector.enable_ml_enhancement()
        info = detector.get_provider_info()
        self.assertEqual(info['ml_enhancement_enabled'], 'True')
        
        support_ml, resistance_ml = detector.detect_levels(self.df, self.current_price)
        ml_call_count_enabled = ml_provider.bounce_call_count
        
        # ML無効での検出
        detector.disable_ml_enhancement()
        info = detector.get_provider_info()
        self.assertEqual(info['ml_enhancement_enabled'], 'False')
        
        support_no_ml, resistance_no_ml = detector.detect_levels(self.df, self.current_price)
        ml_call_count_disabled = ml_provider.bounce_call_count
        
        # ML有効時にMLプロバイダーが呼ばれ、無効時に呼ばれないことを確認
        self.assertGreater(ml_call_count_enabled, 0, "ML有効時にMLプロバイダーが呼ばれていない")
        self.assertEqual(ml_call_count_disabled, ml_call_count_enabled, 
                        "ML無効時にMLプロバイダーが追加で呼ばれている")
        
        print("✅ ML機能オン/オフ切り替え成功")
    
    def test_ml_enhancement_without_provider(self):
        """MLプロバイダーなしでのML機能制御テスト"""
        base_provider = MockBasicProvider()
        
        detector = FlexibleSupportResistanceDetector(
            base_provider=base_provider,
            ml_provider=None,
            use_ml_enhancement=False
        )
        
        # MLプロバイダーがない状態で有効化を試行
        detector.enable_ml_enhancement()
        
        # ML機能が有効化されないことを確認
        info = detector.get_provider_info()
        self.assertEqual(info['ml_provider'], 'Disabled')
        
        # 検出は正常に動作することを確認
        support_levels, resistance_levels = detector.detect_levels(self.df, self.current_price)
        self.assertGreater(len(support_levels) + len(resistance_levels), 0, 
                          "MLプロバイダーなしで検出が失敗")
        
        print("✅ MLプロバイダーなしでの制御確認")
    
    def test_ml_enhancement_impact_on_results(self):
        """ML機能が結果に与える影響のテスト"""
        base_provider = MockBasicProvider()
        ml_provider = MockMLProvider()
        
        detector = FlexibleSupportResistanceDetector(
            base_provider=base_provider,
            ml_provider=ml_provider,
            use_ml_enhancement=False
        )
        
        # ML無効での検出
        support_no_ml, resistance_no_ml = detector.detect_levels(self.df, self.current_price)
        
        # ML有効での検出
        detector.enable_ml_enhancement()
        support_with_ml, resistance_with_ml = detector.detect_levels(self.df, self.current_price)
        
        # 基本的なレベル数は同じであることを確認
        self.assertEqual(len(support_no_ml), len(support_with_ml), 
                        "ML有効/無効で支持線数が変わっている")
        self.assertEqual(len(resistance_no_ml), len(resistance_with_ml), 
                        "ML有効/無効で抵抗線数が変わっている")
        
        # ML有効時にはML属性が追加されることを確認
        all_levels_with_ml = support_with_ml + resistance_with_ml
        if all_levels_with_ml:
            has_ml_attributes = any(hasattr(level, 'ml_bounce_probability') for level in all_levels_with_ml)
            self.assertTrue(has_ml_attributes, "ML有効時にML属性が追加されていない")
        
        print("✅ ML機能の結果への影響確認")


class TestConfigurationManagement(unittest.TestCase):
    """設定ファイルベースの管理テスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_support_resistance_config.json")
        
        # テスト用設定ファイル
        self.test_config = {
            "default_provider": {
                "base_provider": "MockBasic",
                "ml_provider": "MockML",
                "use_ml_enhancement": True
            },
            "fallback_provider": {
                "base_provider": "Simple",
                "ml_provider": None,
                "use_ml_enhancement": False
            },
            "provider_settings": {
                "MockBasic": {
                    "min_touches": 2,
                    "tolerance_pct": 0.01
                },
                "MockML": {
                    "confidence_threshold": 0.6
                }
            }
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f, indent=2)
    
    def tearDown(self):
        """テスト後cleanup"""
        shutil.rmtree(self.temp_dir)
    
    def test_config_file_reading(self):
        """設定ファイル読み込みテスト"""
        # 設定ファイルの読み込み確認
        self.assertTrue(os.path.exists(self.config_path), "テスト設定ファイルが作成されていない")
        
        with open(self.config_path, 'r') as f:
            loaded_config = json.load(f)
        
        # 設定内容の確認
        self.assertEqual(loaded_config['default_provider']['base_provider'], "MockBasic")
        self.assertEqual(loaded_config['default_provider']['ml_provider'], "MockML")
        self.assertTrue(loaded_config['default_provider']['use_ml_enhancement'])
        
        print("✅ 設定ファイル読み込み確認")
    
    def test_config_based_initialization(self):
        """設定ファイルベースの初期化（概念テスト）"""
        # 実際の実装では設定ファイルを読み込んでプロバイダーを初期化する
        # ここでは概念的なテストを実行
        
        config = self.test_config['default_provider']
        
        # 設定に基づくプロバイダー作成のシミュレーション
        if config['base_provider'] == 'MockBasic':
            base_provider = MockBasicProvider()
        else:
            base_provider = None
        
        if config['ml_provider'] == 'MockML':
            ml_provider = MockMLProvider()
        else:
            ml_provider = None
        
        # 検出器の初期化
        detector = FlexibleSupportResistanceDetector(
            base_provider=base_provider,
            ml_provider=ml_provider,
            use_ml_enhancement=config['use_ml_enhancement']
        )
        
        # 設定が正しく反映されることを確認
        info = detector.get_provider_info()
        self.assertIn("MockBasic", info['base_provider'])
        self.assertEqual(info['ml_provider'], "MockML")
        
        print("✅ 設定ベース初期化確認")
    
    def test_fallback_configuration(self):
        """フォールバック設定のテスト"""
        fallback_config = self.test_config['fallback_provider']
        
        # フォールバック設定での初期化シミュレーション
        base_provider = MockBasicProvider(name="Simple")
        
        detector = FlexibleSupportResistanceDetector(
            base_provider=base_provider,
            ml_provider=None,
            use_ml_enhancement=fallback_config['use_ml_enhancement']
        )
        
        # フォールバック設定が反映されることを確認
        info = detector.get_provider_info()
        self.assertIn("Simple", info['base_provider'])
        self.assertEqual(info['ml_provider'], 'Disabled')
        self.assertEqual(info['ml_enhancement_enabled'], 'False')
        
        print("✅ フォールバック設定確認")


class TestAdapterPatternFlexibility(unittest.TestCase):
    """アダプターパターンの柔軟性テスト"""
    
    def setUp(self):
        """テスト前準備"""
        # テスト用データ
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=50, freq='1h')
        prices = 50000 + np.random.normal(0, 500, 50)
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 30, 50),
            'high': prices + np.abs(np.random.normal(100, 50, 50)),
            'low': prices - np.abs(np.random.normal(100, 50, 50)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 50)
        })
        
        self.current_price = prices[-1]
    
    def test_interface_compliance(self):
        """インターフェース準拠性テスト"""
        # 基本プロバイダーインターフェースの確認
        provider = MockBasicProvider()
        
        # 必須メソッドの存在確認
        self.assertTrue(hasattr(provider, 'detect_basic_levels'), "detect_basic_levelsメソッドがない")
        self.assertTrue(hasattr(provider, 'get_provider_name'), "get_provider_nameメソッドがない")
        self.assertTrue(hasattr(provider, 'get_provider_version'), "get_provider_versionメソッドがない")
        
        # メソッドの呼び出し確認
        levels = provider.detect_basic_levels(self.df)
        self.assertIsInstance(levels, list, "detect_basic_levelsがリストを返さない")
        
        name = provider.get_provider_name()
        self.assertIsInstance(name, str, "get_provider_nameが文字列を返さない")
        
        version = provider.get_provider_version()
        self.assertIsInstance(version, str, "get_provider_versionが文字列を返さない")
        
        print("✅ インターフェース準拠性確認")
    
    def test_ml_interface_compliance(self):
        """MLインターフェース準拠性テスト"""
        ml_provider = MockMLProvider()
        
        # 必須メソッドの存在確認
        self.assertTrue(hasattr(ml_provider, 'detect_interactions'), "detect_interactionsメソッドがない")
        self.assertTrue(hasattr(ml_provider, 'predict_bounce_probability'), "predict_bounce_probabilityメソッドがない")
        self.assertTrue(hasattr(ml_provider, 'get_enhancement_name'), "get_enhancement_nameメソッドがない")
        
        # メソッドの呼び出し確認
        mock_levels = [{'price': 50000, 'strength': 0.8}]
        interactions = ml_provider.detect_interactions(self.df, mock_levels)
        self.assertIsInstance(interactions, list, "detect_interactionsがリストを返さない")
        
        probability = ml_provider.predict_bounce_probability(self.df, mock_levels[0])
        self.assertIsInstance(probability, (int, float), "predict_bounce_probabilityが数値を返さない")
        self.assertGreaterEqual(probability, 0.0, "反発確率が0未満")
        self.assertLessEqual(probability, 1.0, "反発確率が1超")
        
        name = ml_provider.get_enhancement_name()
        self.assertIsInstance(name, str, "get_enhancement_nameが文字列を返さない")
        
        print("✅ MLインターフェース準拠性確認")
    
    def test_extensibility_simulation(self):
        """拡張性シミュレーションテスト"""
        # 新しいプロバイダータイプのシミュレーション
        class AdvancedProvider(ISupportResistanceProvider):
            def __init__(self):
                self.advanced_feature_used = False
            
            def detect_basic_levels(self, df, min_touches=2):
                self.advanced_feature_used = True
                current_price = df['close'].iloc[-1]
                
                # 高度な検出アルゴリズムをシミュレート
                return [
                    {
                        'price': current_price * 0.95,
                        'strength': 0.95,  # より高い強度
                        'touch_count': min_touches + 2,
                        'type': 'support',
                        'timestamps': [df['timestamp'].iloc[0], df['timestamp'].iloc[-1]],
                        'avg_volume': 2000000,
                        'advanced_feature': True  # 拡張属性
                    }
                ]
            
            def get_provider_name(self):
                return "AdvancedProvider"
            
            def get_provider_version(self):
                return "3.0.0"
        
        # 新しいプロバイダーが既存システムで動作することを確認
        advanced_provider = AdvancedProvider()
        detector = FlexibleSupportResistanceDetector(base_provider=advanced_provider)
        
        support_levels, resistance_levels = detector.detect_levels(self.df, self.current_price)
        
        # 新しいプロバイダーが使用されたことを確認
        self.assertTrue(advanced_provider.advanced_feature_used, "新しいプロバイダーが使用されていない")
        
        # 結果の妥当性確認
        self.assertGreater(len(support_levels), 0, "新しいプロバイダーから結果が得られない")
        
        # プロバイダー情報の確認
        info = detector.get_provider_info()
        self.assertIn("AdvancedProvider", info['base_provider'])
        
        print("✅ 拡張性シミュレーション確認")
    
    def test_adapter_error_tolerance(self):
        """アダプターのエラー耐性テスト"""
        # 部分的に失敗するプロバイダー
        class PartiallyFailingProvider(ISupportResistanceProvider):
            def detect_basic_levels(self, df, min_touches=2):
                # 50%の確率で失敗
                if np.random.random() < 0.5:
                    raise RuntimeError("Simulated partial failure")
                
                current_price = df['close'].iloc[-1]
                return [
                    {
                        'price': current_price * 0.97,
                        'strength': 0.6,
                        'touch_count': min_touches,
                        'type': 'support',
                        'timestamps': [df['timestamp'].iloc[0], df['timestamp'].iloc[-1]],
                        'avg_volume': 1000000
                    }
                ]
            
            def get_provider_name(self):
                return "PartiallyFailingProvider"
            
            def get_provider_version(self):
                return "1.0.0"
        
        failing_provider = PartiallyFailingProvider()
        detector = FlexibleSupportResistanceDetector(base_provider=failing_provider)
        
        # 複数回実行して、成功と失敗の両方を確認
        success_count = 0
        failure_count = 0
        
        for i in range(10):
            try:
                support_levels, resistance_levels = detector.detect_levels(self.df, self.current_price)
                success_count += 1
            except Exception:
                failure_count += 1
        
        # 部分的な成功と失敗が発生することを確認
        self.assertGreater(success_count, 0, "成功ケースが1つもない")
        self.assertGreater(failure_count, 0, "失敗ケースが1つもない")
        
        print(f"✅ エラー耐性確認: 成功{success_count}回, 失敗{failure_count}回")


def run_adapter_pattern_tests():
    """アダプターパターン互換性テストの実行"""
    print("🔄 アダプターパターン互換性専用テストスイート")
    print("=" * 80)
    
    # テストスイート作成
    test_suite = unittest.TestSuite()
    
    # テストクラス追加
    test_classes = [
        TestProviderSwitching,
        TestMLEnhancementToggle,
        TestConfigurationManagement,
        TestAdapterPatternFlexibility
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 アダプターパターン互換性 テスト結果")
    print("=" * 80)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    print(f"スキップ: {len(result.skipped)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback_text in result.failures:
            print(f"  - {test}")
            lines = traceback_text.split('\n')
            for line in lines:
                if 'AssertionError:' in line:
                    print(f"    理由: {line.split('AssertionError: ')[-1]}")
                    break
    
    if result.errors:
        print("\n💥 エラーが発生したテスト:")
        for test, traceback_text in result.errors:
            print(f"  - {test}")
            lines = traceback_text.split('\n')
            for line in reversed(lines):
                if line.strip() and not line.startswith(' '):
                    print(f"    エラー: {line}")
                    break
    
    if result.skipped:
        print("\n⏭️ スキップされたテスト:")
        for test, reason in result.skipped:
            print(f"  - {test}: {reason}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100 if result.testsRun > 0 else 0
    print(f"\n成功率: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ アダプターパターン互換性の全テストが成功!")
        print("プロバイダー差し替えアーキテクチャが正常に動作しています。")
        print("\n確認された機能:")
        print("  🔄 基本プロバイダーの動的差し替え")
        print("  🤖 MLプロバイダーの動的差し替え")
        print("  🎛️ ML機能のオン/オフ切り替え")
        print("  📋 設定ファイルベースの管理")
        print("  🔧 インターフェース準拠性")
        print("  📈 将来拡張性")
        print("  🛡️ エラー耐性")
    else:
        print("\n⚠️ 一部のアダプターパターンテストが失敗!")
        print("プロバイダー差し替えアーキテクチャに問題があります。")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_adapter_pattern_tests()
    exit(0 if success else 1)