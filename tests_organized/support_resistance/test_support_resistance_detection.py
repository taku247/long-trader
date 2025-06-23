#!/usr/bin/env python3
"""
支持線・抵抗線検出システム専用テストスイート

今回統合した支持線・抵抗線検出システムの徹底的なテスト:
1. 基本検出エンジンの動作確認
2. 高度検出エンジンの動作確認
3. 既存モジュールとの統合確認
4. データ品質の検証
5. エラーハンドリングの確認
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import traceback

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.support_resistance_detector import SupportResistanceDetector
from engines.advanced_support_resistance_detector import AdvancedSupportResistanceDetector
from interfaces.data_types import SupportResistanceLevel


class TestBasicSupportResistanceDetection(unittest.TestCase):
    """基本支持線・抵抗線検出エンジンのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.detector = SupportResistanceDetector()
        
        # 明確なサポート・レジスタンスパターンを持つOHLCVデータを生成
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=500, freq='1h')
        
        # ベース価格とトレンド
        base_price = 50000
        trend = np.linspace(0, 2000, 500)
        noise = np.random.normal(0, 300, 500)
        prices = base_price + trend + noise
        
        # 明確なサポート・レジスタンスレベルを強制的に作成
        support_level = 51000
        resistance_level = 54000
        
        for i in range(len(prices)):
            # サポートレベルでの反発を強制
            if prices[i] < support_level and np.random.random() < 0.8:
                prices[i] = support_level + np.random.uniform(0, 100)
            # レジスタンスレベルでの反落を強制
            elif prices[i] > resistance_level and np.random.random() < 0.8:
                prices[i] = resistance_level - np.random.uniform(0, 100)
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 50, 500),
            'high': prices + np.abs(np.random.normal(150, 80, 500)),
            'low': prices - np.abs(np.random.normal(150, 80, 500)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 500)
        })
        
        self.current_price = prices[-1]
        self.expected_support_level = support_level
        self.expected_resistance_level = resistance_level
    
    def test_basic_detector_initialization(self):
        """基本検出器の初期化テスト"""
        detector = SupportResistanceDetector()
        self.assertIsNotNone(detector)
        
        # デフォルトパラメータの確認
        self.assertEqual(detector.min_touches, 2)
        self.assertEqual(detector.tolerance_pct, 0.01)
        
        print("✅ 基本検出器の初期化確認")
    
    def test_basic_detection_returns_valid_levels(self):
        """基本検出が有効な支持線・抵抗線を返すことを確認"""
        try:
            support_levels, resistance_levels = self.detector.detect_levels_from_ohlcv(
                self.df, self.current_price
            )
            
            # 基本的な検証
            self.assertIsInstance(support_levels, list, "支持線が列形式でない")
            self.assertIsInstance(resistance_levels, list, "抵抗線がリスト形式でない")
            
            total_levels = len(support_levels) + len(resistance_levels)
            self.assertGreater(total_levels, 0, "支持線・抵抗線が1つも検出されませんでした")
            
            print(f"✅ 基本検出結果: 支持線{len(support_levels)}個, 抵抗線{len(resistance_levels)}個")
            
            # 各レベルの妥当性確認
            for i, level in enumerate(support_levels):
                with self.subTest(support_level=i):
                    self.assertIsInstance(level, SupportResistanceLevel, f"支持線{i}がSupportResistanceLevelでない")
                    self.assertLess(level.price, self.current_price, f"支持線{i}が現在価格より高い")
                    self.assertGreater(level.strength, 0, f"支持線{i}の強度が0以下")
                    self.assertGreaterEqual(level.touch_count, self.detector.min_touches, f"支持線{i}のタッチ回数が不足")
            
            for i, level in enumerate(resistance_levels):
                with self.subTest(resistance_level=i):
                    self.assertIsInstance(level, SupportResistanceLevel, f"抵抗線{i}がSupportResistanceLevelでない")
                    self.assertGreater(level.price, self.current_price, f"抵抗線{i}が現在価格より低い")
                    self.assertGreater(level.strength, 0, f"抵抗線{i}の強度が0以下")
                    self.assertGreaterEqual(level.touch_count, self.detector.min_touches, f"抵抗線{i}のタッチ回数が不足")
            
        except Exception as e:
            self.fail(f"基本検出でエラーが発生: {str(e)}")
    
    def test_detection_with_different_parameters(self):
        """異なるパラメータでの検出テスト"""
        test_cases = [
            {'min_touches': 2, 'tolerance_pct': 0.01},
            {'min_touches': 3, 'tolerance_pct': 0.02},
            {'min_touches': 1, 'tolerance_pct': 0.005}
        ]
        
        for i, params in enumerate(test_cases):
            with self.subTest(case=i):
                detector = SupportResistanceDetector(**params)
                
                try:
                    support_levels, resistance_levels = detector.detect_levels_from_ohlcv(
                        self.df, self.current_price
                    )
                    
                    # パラメータに応じた結果の妥当性確認
                    for level in support_levels + resistance_levels:
                        self.assertGreaterEqual(level.touch_count, params['min_touches'], 
                                              f"ケース{i}: タッチ回数が設定値未満")
                    
                    print(f"✅ パラメータケース{i}: min_touches={params['min_touches']}, tolerance={params['tolerance_pct']}")
                    
                except Exception as e:
                    self.fail(f"パラメータケース{i}でエラー: {str(e)}")
    
    def test_insufficient_data_handling(self):
        """データ不足時の適切なエラーハンドリング"""
        # 不十分なデータ（10本のみ）
        insufficient_df = self.df.head(10)
        
        with self.assertRaises(ValueError) as context:
            self.detector.detect_levels_from_ohlcv(insufficient_df, self.current_price)
        
        error_msg = str(context.exception)
        self.assertIn("データが不足", error_msg, "データ不足エラーメッセージが不適切")
        
        print("✅ データ不足時のエラーハンドリング確認")
    
    def test_empty_dataframe_handling(self):
        """空のデータフレーム処理"""
        empty_df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        with self.assertRaises((ValueError, IndexError)) as context:
            self.detector.detect_levels_from_ohlcv(empty_df, self.current_price)
        
        print("✅ 空データフレームのエラーハンドリング確認")
    
    def test_level_object_attributes(self):
        """検出されたレベルオブジェクトの属性確認"""
        support_levels, resistance_levels = self.detector.detect_levels_from_ohlcv(
            self.df, self.current_price
        )
        
        all_levels = support_levels + resistance_levels
        self.assertGreater(len(all_levels), 0, "テスト用にレベルが必要")
        
        for i, level in enumerate(all_levels):
            with self.subTest(level=i):
                # 必須属性の存在確認
                self.assertTrue(hasattr(level, 'price'), f"レベル{i}: price属性がない")
                self.assertTrue(hasattr(level, 'strength'), f"レベル{i}: strength属性がない")
                self.assertTrue(hasattr(level, 'touch_count'), f"レベル{i}: touch_count属性がない")
                self.assertTrue(hasattr(level, 'level_type'), f"レベル{i}: level_type属性がない")
                self.assertTrue(hasattr(level, 'first_touch'), f"レベル{i}: first_touch属性がない")
                self.assertTrue(hasattr(level, 'last_touch'), f"レベル{i}: last_touch属性がない")
                self.assertTrue(hasattr(level, 'volume_at_level'), f"レベル{i}: volume_at_level属性がない")
                self.assertTrue(hasattr(level, 'distance_from_current'), f"レベル{i}: distance_from_current属性がない")
                
                # 属性値の妥当性確認
                self.assertIsInstance(level.price, (int, float), f"レベル{i}: priceが数値でない")
                self.assertIsInstance(level.strength, (int, float), f"レベル{i}: strengthが数値でない")
                self.assertIsInstance(level.touch_count, int, f"レベル{i}: touch_countが整数でない")
                self.assertIn(level.level_type, ['support', 'resistance'], f"レベル{i}: level_typeが不正")
                
        print("✅ レベルオブジェクトの属性確認")


class TestAdvancedSupportResistanceDetection(unittest.TestCase):
    """高度支持線・抵抗線検出エンジンのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        # MLなしでの高度検出器（既存モジュールの依存を避ける）
        self.detector_no_ml = AdvancedSupportResistanceDetector(use_ml_prediction=False)
        
        # サンプルOHLCVデータ生成（基本検出器と同じパターン）
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=300, freq='1h')
        base_price = 50000
        trend = np.linspace(0, 1500, 300)
        noise = np.random.normal(0, 250, 300)
        prices = base_price + trend + noise
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 40, 300),
            'high': prices + np.abs(np.random.normal(120, 60, 300)),
            'low': prices - np.abs(np.random.normal(120, 60, 300)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 300)
        })
        
        self.current_price = prices[-1]
    
    def test_advanced_detector_initialization(self):
        """高度検出器の初期化テスト"""
        # MLなしでの初期化
        detector_no_ml = AdvancedSupportResistanceDetector(use_ml_prediction=False)
        self.assertIsNotNone(detector_no_ml)
        self.assertFalse(detector_no_ml.use_ml_prediction)
        
        # MLありでの初期化（モジュールがない場合は失敗する可能性あり）
        try:
            detector_with_ml = AdvancedSupportResistanceDetector(use_ml_prediction=True)
            self.assertIsNotNone(detector_with_ml)
            print("✅ ML付き高度検出器の初期化確認")
        except Exception as e:
            print(f"ℹ️ ML付き高度検出器はスキップ（既存モジュールなし）: {str(e)}")
        
        print("✅ 高度検出器の初期化確認")
    
    def test_advanced_detection_without_ml(self):
        """ML機能なしでの高度検出テスト"""
        try:
            support_levels, resistance_levels = self.detector_no_ml.detect_advanced_levels(
                self.df, self.current_price
            )
            
            # 基本的な検証
            self.assertIsInstance(support_levels, list, "支持線がリスト形式でない")
            self.assertIsInstance(resistance_levels, list, "抵抗線がリスト形式でない")
            
            total_levels = len(support_levels) + len(resistance_levels)
            self.assertGreater(total_levels, 0, "高度検出で支持線・抵抗線が1つも検出されませんでした")
            
            print(f"✅ 高度検出（MLなし）結果: 支持線{len(support_levels)}個, 抵抗線{len(resistance_levels)}個")
            
            # レベルの妥当性確認
            for level in support_levels:
                self.assertIsInstance(level, SupportResistanceLevel)
                self.assertLess(level.price, self.current_price)
            
            for level in resistance_levels:
                self.assertIsInstance(level, SupportResistanceLevel)
                self.assertGreater(level.price, self.current_price)
            
        except Exception as e:
            # 既存モジュールがない場合は条件付きスキップ
            if "support_resistance_visualizer" in str(e) or "find_all_levels" in str(e):
                self.skipTest(f"既存のsupport_resistance_visualizer.pyが利用できません: {str(e)}")
            else:
                self.fail(f"高度検出（MLなし）でエラー: {str(e)}")
    
    @patch('engines.advanced_support_resistance_detector.find_all_levels')
    def test_advanced_detection_with_mock_visualizer(self, mock_find_levels):
        """モックを使用した高度検出テスト"""
        # モックのfind_all_levels関数の戻り値設定
        mock_find_levels.return_value = [
            {
                'price': 49000.0,
                'strength': 0.8,
                'touch_count': 3,
                'type': 'support',
                'timestamps': [self.df['timestamp'].iloc[0], self.df['timestamp'].iloc[50]],
                'avg_volume': 1500000
            },
            {
                'price': 52000.0,
                'strength': 0.7,
                'touch_count': 2,
                'type': 'resistance',
                'timestamps': [self.df['timestamp'].iloc[100], self.df['timestamp'].iloc[150]],
                'avg_volume': 1300000
            }
        ]
        
        detector = AdvancedSupportResistanceDetector(use_ml_prediction=False)
        
        try:
            support_levels, resistance_levels = detector.detect_advanced_levels(
                self.df, self.current_price
            )
            
            # モックデータに基づく結果確認
            self.assertGreater(len(support_levels), 0, "モックデータから支持線が検出されない")
            self.assertGreater(len(resistance_levels), 0, "モックデータから抵抗線が検出されない")
            
            # モック関数が呼ばれたことを確認
            mock_find_levels.assert_called_once()
            
            print("✅ モックを使用した高度検出テスト成功")
            
        except Exception as e:
            self.fail(f"モック使用高度検出でエラー: {str(e)}")
    
    def test_critical_levels_selection(self):
        """重要レベル選択機能のテスト"""
        # モック支持線・抵抗線を作成
        mock_support_levels = [
            SupportResistanceLevel(
                price=48000.0, strength=0.9, touch_count=4, level_type='support',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=2000000, distance_from_current=-4.0
            ),
            SupportResistanceLevel(
                price=47000.0, strength=0.6, touch_count=2, level_type='support',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1000000, distance_from_current=-6.0
            )
        ]
        
        mock_resistance_levels = [
            SupportResistanceLevel(
                price=52000.0, strength=0.8, touch_count=3, level_type='resistance',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=1800000, distance_from_current=4.0
            ),
            SupportResistanceLevel(
                price=55000.0, strength=0.5, touch_count=2, level_type='resistance',
                first_touch=datetime.now(), last_touch=datetime.now(),
                volume_at_level=900000, distance_from_current=10.0
            )
        ]
        
        detector = AdvancedSupportResistanceDetector(use_ml_prediction=False)
        
        critical_supports, critical_resistances = detector.get_critical_levels(
            mock_support_levels, mock_resistance_levels, self.current_price, max_count=1
        )
        
        # 最も重要なレベルが選択されることを確認
        self.assertEqual(len(critical_supports), 1, "重要支持線が1つ選択されていない")
        self.assertEqual(len(critical_resistances), 1, "重要抵抗線が1つ選択されていない")
        
        # より強度が高く、距離が近いレベルが選択されることを確認
        self.assertEqual(critical_supports[0].price, 48000.0, "より重要な支持線が選択されていない")
        self.assertEqual(critical_resistances[0].price, 52000.0, "より重要な抵抗線が選択されていない")
        
        print("✅ 重要レベル選択機能確認")
    
    def test_advanced_detection_error_handling(self):
        """高度検出のエラーハンドリング確認"""
        detector = AdvancedSupportResistanceDetector(use_ml_prediction=False)
        
        # データ不足のケース
        insufficient_df = self.df.head(10)
        
        with self.assertRaises(ValueError) as context:
            detector.detect_advanced_levels(insufficient_df, self.current_price)
        
        error_msg = str(context.exception)
        self.assertIn("データが不足", error_msg, "高度検出のデータ不足エラーメッセージが不適切")
        
        print("✅ 高度検出のエラーハンドリング確認")


class TestSupportResistanceIntegration(unittest.TestCase):
    """支持線・抵抗線検出システムの統合テスト"""
    
    def setUp(self):
        """テスト前準備"""
        # 豊富なデータセット
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=1000, freq='1h')
        base_price = 50000
        trend = np.linspace(0, 3000, 1000)
        noise = np.random.normal(0, 400, 1000)
        prices = base_price + trend + noise
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 50, 1000),
            'high': prices + np.abs(np.random.normal(200, 100, 1000)),
            'low': prices - np.abs(np.random.normal(200, 100, 1000)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 1000)
        })
        
        self.current_price = prices[-1]
    
    def test_basic_vs_advanced_detection_consistency(self):
        """基本検出と高度検出の一貫性テスト"""
        basic_detector = SupportResistanceDetector()
        advanced_detector = AdvancedSupportResistanceDetector(use_ml_prediction=False)
        
        try:
            # 基本検出
            basic_support, basic_resistance = basic_detector.detect_levels_from_ohlcv(
                self.df, self.current_price
            )
            
            # 高度検出
            advanced_support, advanced_resistance = advanced_detector.detect_advanced_levels(
                self.df, self.current_price
            )
            
            # 両方で何らかのレベルが検出されることを確認
            self.assertGreater(len(basic_support) + len(basic_resistance), 0, "基本検出でレベルが検出されない")
            self.assertGreater(len(advanced_support) + len(advanced_resistance), 0, "高度検出でレベルが検出されない")
            
            # 検出されたレベルの品質比較
            basic_total = len(basic_support) + len(basic_resistance)
            advanced_total = len(advanced_support) + len(advanced_resistance)
            
            print(f"✅ 基本検出: {basic_total}個, 高度検出: {advanced_total}個のレベル")
            
            # 高度検出が基本検出より良い（またはレベルが多い）結果を期待
            # ただし、これは保証されないため情報として記録のみ
            if advanced_total >= basic_total:
                print("✅ 高度検出が基本検出以上のレベル数を検出")
            else:
                print("ℹ️ 基本検出の方が多くのレベルを検出")
            
        except Exception as e:
            if "support_resistance_visualizer" in str(e):
                self.skipTest(f"既存モジュールが利用できません: {str(e)}")
            else:
                self.fail(f"検出器一貫性テストでエラー: {str(e)}")
    
    def test_detection_performance_with_large_dataset(self):
        """大規模データセットでの検出性能テスト"""
        # 大規模データセット（5000本）
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=5000, freq='1h')
        base_price = 50000
        prices = base_price + np.random.normal(0, 500, 5000)
        
        large_df = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 50, 5000),
            'high': prices + np.abs(np.random.normal(200, 100, 5000)),
            'low': prices - np.abs(np.random.normal(200, 100, 5000)),
            'close': prices,
            'volume': np.random.uniform(1000000, 3000000, 5000)
        })
        
        current_price = prices[-1]
        
        detector = SupportResistanceDetector()
        
        import time
        start_time = time.time()
        
        try:
            support_levels, resistance_levels = detector.detect_levels_from_ohlcv(
                large_df, current_price
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 処理時間が合理的な範囲内（30秒以内）であることを確認
            self.assertLess(processing_time, 30.0, f"処理時間が長すぎます: {processing_time:.2f}秒")
            
            # 結果の妥当性確認
            total_levels = len(support_levels) + len(resistance_levels)
            self.assertGreater(total_levels, 0, "大規模データセットでレベルが検出されない")
            
            print(f"✅ 大規模データセット（5000本）処理: {processing_time:.2f}秒, {total_levels}レベル")
            
        except Exception as e:
            self.fail(f"大規模データセット処理でエラー: {str(e)}")
    
    def test_detection_with_edge_cases(self):
        """エッジケースでの検出テスト"""
        edge_cases = [
            {
                'name': '単調増加データ',
                'prices': np.linspace(50000, 55000, 200)
            },
            {
                'name': '単調減少データ',
                'prices': np.linspace(55000, 50000, 200)
            },
            {
                'name': '横ばいデータ',
                'prices': np.full(200, 52000) + np.random.normal(0, 50, 200)
            },
            {
                'name': '高ボラティリティデータ',
                'prices': 52000 + np.random.normal(0, 2000, 200)
            }
        ]
        
        detector = SupportResistanceDetector(min_touches=1)  # より緩い条件
        
        for case in edge_cases:
            with self.subTest(case=case['name']):
                dates = pd.date_range('2024-01-01', periods=len(case['prices']), freq='1h')
                prices = case['prices']
                
                edge_df = pd.DataFrame({
                    'timestamp': dates,
                    'open': prices + np.random.normal(0, 30, len(prices)),
                    'high': prices + np.abs(np.random.normal(100, 50, len(prices))),
                    'low': prices - np.abs(np.random.normal(100, 50, len(prices))),
                    'close': prices,
                    'volume': np.random.uniform(1000000, 3000000, len(prices))
                })
                
                current_price = prices[-1]
                
                try:
                    support_levels, resistance_levels = detector.detect_levels_from_ohlcv(
                        edge_df, current_price
                    )
                    
                    # エラーが発生しないことが重要（結果の有無は問わない）
                    total_levels = len(support_levels) + len(resistance_levels)
                    print(f"✅ {case['name']}: {total_levels}レベル検出")
                    
                except Exception as e:
                    self.fail(f"{case['name']}でエラー: {str(e)}")


def run_support_resistance_detection_tests():
    """支持線・抵抗線検出システムテストの実行"""
    print("📊 支持線・抵抗線検出システム専用テストスイート")
    print("=" * 80)
    
    # テストスイート作成
    test_suite = unittest.TestSuite()
    
    # テストクラス追加
    test_classes = [
        TestBasicSupportResistanceDetection,
        TestAdvancedSupportResistanceDetection,
        TestSupportResistanceIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 支持線・抵抗線検出システム テスト結果")
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
            # エラーの要約を抽出
            lines = traceback_text.split('\n')
            for line in lines:
                if 'AssertionError:' in line:
                    print(f"    理由: {line.split('AssertionError: ')[-1]}")
                    break
    
    if result.errors:
        print("\n💥 エラーが発生したテスト:")
        for test, traceback_text in result.errors:
            print(f"  - {test}")
            # エラーの要約を抽出
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
        print("\n✅ 支持線・抵抗線検出システムの全テストが成功!")
        print("検出システムが正常に動作しています。")
        print("\n確認された機能:")
        print("  📊 基本検出エンジンの正常動作")
        print("  🧠 高度検出エンジンの正常動作")
        print("  🔗 既存モジュールとの統合")
        print("  🎯 レベルオブジェクトの品質")
        print("  ⚡ 大規模データセット対応")
        print("  🛡️ エッジケース処理")
    else:
        print("\n⚠️ 一部の支持線・抵抗線検出テストが失敗!")
        print("検出システムに問題があります。")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_support_resistance_detection_tests()
    exit(0 if success else 1)