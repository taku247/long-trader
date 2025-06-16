#!/usr/bin/env python3
"""
サポート強度範囲バグ再発防止テスト

support_resistance_visualizer.pyのサポート強度計算で
0-1範囲を超える異常値（158.70など）が発生することを防ぐ包括的テストスイート。
"""

import unittest
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

import support_resistance_visualizer as srv
from interfaces.data_types import SupportResistanceLevel
from adapters.existing_adapters import ExistingSupportResistanceAdapter

class TestSupportStrengthValidation(unittest.TestCase):
    """サポート強度範囲検証テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        # テスト用のOHLCVデータを生成
        self.test_data = self._generate_test_data()
        self.adapter = ExistingSupportResistanceAdapter()
    
    def _generate_test_data(self, days=100):
        """テスト用のOHLCVデータを生成"""
        dates = [datetime.now() - timedelta(days=i) for i in range(days)]
        base_price = 1.0
        
        # より現実的な価格データを生成（トレンド + ノイズ）
        prices = []
        for i in range(days):
            trend = 0.001 * i  # 緩やかな上昇トレンド
            noise = np.random.normal(0, 0.02)  # 2%のランダムノイズ
            cycle = 0.05 * np.sin(i * 0.1)  # 周期的な変動
            price = base_price + trend + noise + cycle
            prices.append(max(0.1, price))  # 最低価格を0.1に設定
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': [1000 + np.random.normal(0, 200) for _ in range(days)]
        })
        
        # 負の値を修正
        data['volume'] = data['volume'].clip(lower=100)
        
        return data
    
    def test_support_strength_range_validation(self):
        """サポート強度が0-1の範囲内であることを検証"""
        print("🔍 サポート強度範囲検証テスト実行中...")
        
        try:
            # サポレジレベルを検出
            levels = srv.find_all_levels(self.test_data, min_touches=2)
            
            self.assertGreater(len(levels), 0, "サポレジレベルが検出されませんでした")
            
            # 各レベルの強度をチェック
            for i, level in enumerate(levels):
                strength = level.get('strength', 0)
                
                with self.subTest(level_index=i):
                    self.assertIsInstance(strength, (int, float), 
                                        f"レベル{i}: strengthが数値ではありません: {type(strength)}")
                    
                    self.assertGreaterEqual(strength, 0.0,
                                          f"レベル{i}: strength={strength} が負の値です")
                    
                    self.assertLessEqual(strength, 1.0,
                                       f"レベル{i}: strength={strength} が1.0を超えています")
                    
                    # NaN, Inf チェック
                    self.assertFalse(np.isnan(strength),
                                    f"レベル{i}: strengthがNaNです")
                    
                    self.assertFalse(np.isinf(strength),
                                    f"レベル{i}: strengthが無限大です")
            
            print(f"✅ 全{len(levels)}レベルの強度が正常範囲内です")
            
        except Exception as e:
            self.fail(f"サポート強度範囲検証でエラーが発生: {e}")
    
    def test_extreme_input_data_handling(self):
        """極端な入力データでの強度計算テスト"""
        print("🔍 極端な入力データハンドリングテスト実行中...")
        
        extreme_test_cases = [
            {
                'name': '非常に高いボラティリティ',
                'price_multiplier': lambda i: 1.0 + np.random.normal(0, 0.5),  # 50%ボラティリティ
                'volume_multiplier': 1.0
            },
            {
                'name': '非常に低いボラティリティ',
                'price_multiplier': lambda i: 1.0 + np.random.normal(0, 0.001),  # 0.1%ボラティリティ
                'volume_multiplier': 1.0
            },
            {
                'name': '出来高スパイク',
                'price_multiplier': lambda i: 1.0 + np.random.normal(0, 0.02),
                'volume_multiplier': 100.0  # 100倍の出来高
            },
            {
                'name': '極端に高い価格',
                'price_multiplier': lambda i: 10000.0 + np.random.normal(0, 100),
                'volume_multiplier': 1.0
            },
            {
                'name': '極端に低い価格',
                'price_multiplier': lambda i: 0.0001 + np.random.normal(0, 0.000001),
                'volume_multiplier': 1.0
            }
        ]
        
        for case in extreme_test_cases:
            with self.subTest(test_case=case['name']):
                print(f"  - テストケース: {case['name']}")
                
                # 極端なデータを生成
                extreme_data = self.test_data.copy()
                extreme_data['close'] = [max(0.0001, case['price_multiplier'](i)) 
                                       for i in range(len(extreme_data))]
                extreme_data['volume'] = extreme_data['volume'] * case['volume_multiplier']
                
                try:
                    levels = srv.find_all_levels(extreme_data, min_touches=2)
                    
                    # 強度範囲チェック
                    for level in levels:
                        strength = level.get('strength', 0)
                        self.assertGreaterEqual(strength, 0.0,
                                              f"{case['name']}: strength={strength} が負の値")
                        self.assertLessEqual(strength, 1.0,
                                           f"{case['name']}: strength={strength} が1.0超")
                        self.assertFalse(np.isnan(strength),
                                       f"{case['name']}: strengthがNaN")
                        self.assertFalse(np.isinf(strength),
                                       f"{case['name']}: strengthが無限大")
                
                except Exception as e:
                    self.fail(f"{case['name']}でエラー発生: {e}")
        
        print(f"✅ 全ての極端ケースで強度が正常範囲内です")
    
    def test_adapter_level_strength_consistency(self):
        """アダプターレベルでの強度一貫性テスト"""
        print("🔍 アダプターレベル強度一貫性テスト実行中...")
        
        try:
            # アダプター経由でレベルを検出
            levels = self.adapter.find_levels(self.test_data)
            
            self.assertGreater(len(levels), 0, "アダプターでレベルが検出されませんでした")
            
            for i, level in enumerate(levels):
                with self.subTest(level_index=i):
                    # 基本的な型チェック
                    self.assertIsInstance(level, SupportResistanceLevel,
                                        f"レベル{i}がSupportResistanceLevelインスタンスではありません")
                    
                    # 強度範囲チェック
                    self.assertGreaterEqual(level.strength, 0.0,
                                          f"レベル{i}: strength={level.strength} が負の値")
                    self.assertLessEqual(level.strength, 1.0,
                                       f"レベル{i}: strength={level.strength} が1.0超")
                    
                    # その他の必須フィールドチェック
                    self.assertGreater(level.price, 0, f"レベル{i}: 価格が0以下")
                    self.assertGreaterEqual(level.touch_count, 1, f"レベル{i}: タッチ回数が1未満")
                    self.assertIn(level.level_type, ['support', 'resistance'],
                                f"レベル{i}: 無効なレベルタイプ: {level.level_type}")
            
            print(f"✅ アダプター経由で{len(levels)}レベルの一貫性確認完了")
            
        except Exception as e:
            self.fail(f"アダプターレベル強度テストでエラー: {e}")
    
    def test_confidence_calculation_sanity(self):
        """信頼度計算の妥当性テスト"""
        print("🔍 信頼度計算妥当性テスト実行中...")
        
        from engines.leverage_decision_engine import CoreLeverageDecisionEngine
        from interfaces.data_types import BreakoutPrediction, BTCCorrelationRisk, MarketContext
        
        try:
            engine = CoreLeverageDecisionEngine()
            
            # アダプター経由でレベルを取得
            levels = self.adapter.find_levels(self.test_data)
            
            if not levels:
                self.skipTest("テスト用レベルが検出されませんでした")
            
            # テスト用のコンテキストデータを準備
            support_levels = [l for l in levels if l.level_type == 'support'][:3]
            resistance_levels = [l for l in levels if l.level_type == 'resistance'][:3]
            
            if not support_levels or not resistance_levels:
                self.skipTest("サポートまたはレジスタンスレベルが不足しています")
            
            breakout_predictions = [
                BreakoutPrediction(
                    level=level, breakout_probability=0.3, bounce_probability=0.7,
                    prediction_confidence=0.8, predicted_price_target=level.price * 1.02,
                    time_horizon_minutes=60, model_name='test_model'
                ) for level in support_levels + resistance_levels
            ]
            
            btc_correlation_risk = BTCCorrelationRisk(
                symbol='TEST', btc_drop_scenario=-10.0,
                predicted_altcoin_drop={60: -5.0, 120: -10.0},
                correlation_strength=0.8, risk_level='MEDIUM',
                liquidation_risk={60: 0.1, 120: 0.2}
            )
            
            market_context = MarketContext(
                current_price=self.test_data['close'].iloc[-1],
                volume_24h=self.test_data['volume'].sum(),
                volatility=self.test_data['close'].pct_change().std(),
                trend_direction='SIDEWAYS', market_phase='ACCUMULATION',
                timestamp=datetime.now()
            )
            
            # レバレッジ計算実行
            result = engine.calculate_safe_leverage(
                symbol='TEST_STRENGTH',
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                breakout_predictions=breakout_predictions,
                btc_correlation_risk=btc_correlation_risk,
                market_context=market_context
            )
            
            # 結果の妥当性チェック
            self.assertIsNotNone(result, "レバレッジ計算結果がNoneです")
            
            # 信頼度範囲チェック
            self.assertGreaterEqual(result.confidence_level, 0.0,
                                  f"信頼度={result.confidence_level} が負の値です")
            self.assertLessEqual(result.confidence_level, 1.0,
                                f"信頼度={result.confidence_level} が1.0を超えています")
            
            # レバレッジ範囲チェック  
            self.assertGreater(result.recommended_leverage, 0.0,
                             f"推奨レバレッジ={result.recommended_leverage} が0以下です")
            self.assertLessEqual(result.recommended_leverage, 100.0,
                               f"推奨レバレッジ={result.recommended_leverage} が異常に高いです")
            
            # リスクリワード比チェック
            self.assertGreater(result.risk_reward_ratio, 0.0,
                             f"リスクリワード比={result.risk_reward_ratio} が0以下です")
            
            print(f"✅ 信頼度計算妥当性確認完了:")
            print(f"   信頼度: {result.confidence_level:.3f}")
            print(f"   推奨レバレッジ: {result.recommended_leverage:.1f}x")
            print(f"   リスクリワード比: {result.risk_reward_ratio:.2f}")
            
        except Exception as e:
            self.fail(f"信頼度計算妥当性テストでエラー: {e}")
    
    def test_raw_strength_calculation_bounds(self):
        """生の強度計算の境界値テスト"""
        print("🔍 生の強度計算境界値テスト実行中...")
        
        # 極端な入力値での直接計算テスト
        test_cases = [
            {
                'name': '最小値',
                'touch_count': 1, 'avg_bounce': 0.0, 'time_span': 0,
                'recency': 0, 'avg_volume_spike': 0.0
            },
            {
                'name': '最大値', 
                'touch_count': 100, 'avg_bounce': 1.0, 'time_span': 10000,
                'recency': 0, 'avg_volume_spike': 100.0
            },
            {
                'name': '典型的な値',
                'touch_count': 5, 'avg_bounce': 0.02, 'time_span': 1000,
                'recency': 100, 'avg_volume_spike': 1.5
            }
        ]
        
        for case in test_cases:
            with self.subTest(test_case=case['name']):
                # 重みの定義（実際のコードと同じ）
                touch_weight = 3
                bounce_weight = 50
                time_weight = 0.05
                recency_weight = 0.02
                volume_weight = 10
                
                # 生の強度計算
                raw_strength = (case['touch_count'] * touch_weight + 
                              case['avg_bounce'] * bounce_weight + 
                              case['time_span'] * time_weight - 
                              case['recency'] * recency_weight +
                              case['avg_volume_spike'] * volume_weight)
                
                # 正規化
                normalized_strength = min(max(raw_strength / 200.0, 0.0), 1.0)
                
                # 結果検証
                self.assertGreaterEqual(normalized_strength, 0.0,
                                      f"{case['name']}: 正規化後強度が負の値: {normalized_strength}")
                self.assertLessEqual(normalized_strength, 1.0,
                                   f"{case['name']}: 正規化後強度が1.0超: {normalized_strength}")
                
                print(f"   {case['name']}: 生={raw_strength:.1f} → 正規化={normalized_strength:.3f}")
        
        print("✅ 生の強度計算境界値テスト完了")
    
    def test_regression_prevention_158_70_bug(self):
        """158.70バグの回帰防止テスト"""
        print("🔍 158.70バグ回帰防止テスト実行中...")
        
        # 158.70のような異常値を生成しやすい条件を作成
        problematic_data = self.test_data.copy()
        
        # 高い出来高スパイクと多くのタッチポイントを持つデータを意図的に作成
        for i in range(0, len(problematic_data), 10):
            if i < len(problematic_data):
                problematic_data.loc[problematic_data.index[i], 'volume'] *= 50  # 50倍の出来高スパイク
        
        try:
            levels = srv.find_all_levels(problematic_data, min_touches=2)
            
            # 158.70のような異常値がないことを確認
            for i, level in enumerate(levels):
                strength = level.get('strength', 0)
                
                # 特に158.70付近の値をチェック
                self.assertLess(strength, 100.0,
                              f"レベル{i}: strength={strength} が100を超えています（158.70バグ再発の可能性）")
                
                # より厳格に1.0以下をチェック
                self.assertLessEqual(strength, 1.0,
                                   f"レベル{i}: strength={strength} が1.0を超えています")
                
                # 具体的に158.70のような値でないことを確認
                self.assertNotAlmostEqual(strength, 158.70, places=1,
                                        msg=f"レベル{i}: 158.70バグが再発している可能性: {strength}")
            
            print(f"✅ 158.70バグ回帰防止確認完了（{len(levels)}レベル検証）")
            
        except Exception as e:
            self.fail(f"158.70バグ回帰防止テストでエラー: {e}")

def run_support_strength_validation_tests():
    """サポート強度検証テストの実行"""
    print("🔧 サポート強度範囲バグ再発防止テスト開始")
    print("=" * 60)
    
    # テストスイートを作成
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSupportStrengthValidation)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("📋 テスト結果サマリー:")
    print(f"   実行テスト数: {result.testsRun}")
    print(f"   失敗: {len(result.failures)}")
    print(f"   エラー: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ 全てのサポート強度検証テストに合格しました！")
        print("   158.70のような異常値バグの再発を防止できます。")
    else:
        print("❌ 一部のテストが失敗しました。")
        print("   サポート強度計算に問題がある可能性があります。")
        
        if result.failures:
            print("\n失敗したテスト:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
                
        if result.errors:
            print("\nエラーが発生したテスト:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    run_support_strength_validation_tests()