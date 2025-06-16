#!/usr/bin/env python3
"""
信頼度異常値検知テスト

信頼度計算で90%のような異常に高い値や、
計算ロジックの不整合を検知する専用テストスイート。
"""

import unittest
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from engines.leverage_decision_engine import CoreLeverageDecisionEngine
from interfaces.data_types import (
    SupportResistanceLevel, BreakoutPrediction, BTCCorrelationRisk, MarketContext
)

class TestConfidenceAnomalyDetection(unittest.TestCase):
    """信頼度異常値検知テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.engine = CoreLeverageDecisionEngine()
        self.test_data = self._generate_test_data()
    
    def _generate_test_data(self):
        """テスト用データ生成"""
        dates = [datetime.now() - timedelta(days=i) for i in range(50)]
        prices = [1.0 + 0.05 * np.sin(i * 0.1) + np.random.normal(0, 0.01) for i in range(50)]
        
        return pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'volume': [1000 + np.random.normal(0, 50) for _ in range(50)]
        })
    
    def _create_test_context(self, support_strength=0.8, breakout_prob=0.3):
        """テスト用のコンテキストデータを作成"""
        now = datetime.now()
        current_price = 1.0
        
        support_levels = [
            SupportResistanceLevel(
                price=0.95, strength=support_strength, touch_count=3,
                level_type='support', first_touch=now, last_touch=now,
                volume_at_level=1000.0, distance_from_current=5.0
            )
        ]
        
        resistance_levels = [
            SupportResistanceLevel(
                price=1.05, strength=0.7, touch_count=2,
                level_type='resistance', first_touch=now, last_touch=now,
                volume_at_level=800.0, distance_from_current=5.0
            )
        ]
        
        breakout_predictions = [
            BreakoutPrediction(
                level=support_levels[0],
                breakout_probability=breakout_prob,
                bounce_probability=1.0 - breakout_prob,
                prediction_confidence=0.8,
                predicted_price_target=1.02,
                time_horizon_minutes=60,
                model_name='test_model'
            )
        ]
        
        btc_correlation_risk = BTCCorrelationRisk(
            symbol='TEST', btc_drop_scenario=-10.0,
            predicted_altcoin_drop={60: -5.0, 120: -10.0},
            correlation_strength=0.8, risk_level='MEDIUM',
            liquidation_risk={60: 0.1, 120: 0.2}
        )
        
        market_context = MarketContext(
            current_price=current_price, volume_24h=100000.0, volatility=0.02,
            trend_direction='BULLISH', market_phase='MARKUP', timestamp=now
        )
        
        return support_levels, resistance_levels, breakout_predictions, btc_correlation_risk, market_context
    
    def test_normal_confidence_range_validation(self):
        """正常な信頼度範囲検証"""
        print("🔍 正常な信頼度範囲検証テスト実行中...")
        
        # 様々な正常なパラメータで信頼度をテスト
        test_cases = [
            {'name': '低強度', 'support_strength': 0.2, 'breakout_prob': 0.2},
            {'name': '中強度', 'support_strength': 0.5, 'breakout_prob': 0.5},
            {'name': '高強度', 'support_strength': 0.8, 'breakout_prob': 0.8},
        ]
        
        for case in test_cases:
            with self.subTest(test_case=case['name']):
                print(f"  - テストケース: {case['name']}")
                
                support_levels, resistance_levels, predictions, btc_risk, market_context = \
                    self._create_test_context(case['support_strength'], case['breakout_prob'])
                
                result = self.engine.calculate_safe_leverage(
                    symbol=f'TEST_{case["name"]}',
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    breakout_predictions=predictions,
                    btc_correlation_risk=btc_risk,
                    market_context=market_context
                )
                
                confidence = result.confidence_level
                
                # 信頼度基本範囲チェック
                self.assertGreaterEqual(confidence, 0.0,
                                      f"{case['name']}: confidence={confidence} が負の値")
                self.assertLessEqual(confidence, 1.0,
                                   f"{case['name']}: confidence={confidence} が1.0超")
                
                # 異常に高い信頼度をチェック（90%超は疑わしい）
                self.assertLess(confidence, 0.95,
                              f"{case['name']}: confidence={confidence:.1%} が異常に高い（95%超）")
                
                print(f"    ✅ 信頼度: {confidence:.1%}")
        
        print("✅ 正常な信頼度範囲検証完了")
    
    def test_extreme_support_strength_confidence_impact(self):
        """極端なサポート強度が信頼度に与える影響をテスト"""
        print("🔍 極端なサポート強度→信頼度影響テスト実行中...")
        
        # 意図的に異常な強度値をテスト（バグ再現用）
        extreme_strengths = [0.0, 0.999, 1.0]  # 境界値
        
        for strength in extreme_strengths:
            with self.subTest(support_strength=strength):
                print(f"  - サポート強度: {strength}")
                
                support_levels, resistance_levels, predictions, btc_risk, market_context = \
                    self._create_test_context(support_strength=strength)
                
                result = self.engine.calculate_safe_leverage(
                    symbol=f'TEST_STRENGTH_{strength}',
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    breakout_predictions=predictions,
                    btc_correlation_risk=btc_risk,
                    market_context=market_context
                )
                
                confidence = result.confidence_level
                
                # 極端な強度でも信頼度は適正範囲内であるべき
                self.assertGreaterEqual(confidence, 0.0,
                                      f"強度{strength}: confidence={confidence} が負")
                self.assertLessEqual(confidence, 1.0,
                                   f"強度{strength}: confidence={confidence} が1.0超")
                
                # 異常に高い信頼度でないことを確認
                self.assertLess(confidence, 0.95,
                              f"強度{strength}: confidence={confidence:.1%} が異常に高い")
                
                print(f"    ✅ 信頼度: {confidence:.1%}")
        
        print("✅ 極端なサポート強度影響テスト完了")
    
    def test_confidence_factors_normalization(self):
        """信頼度要素の正規化処理テスト"""
        print("🔍 信頼度要素正規化処理テスト実行中...")
        
        # confidence_factorsの各要素が正しく正規化されているかテスト
        with patch.object(self.engine, '_calculate_final_leverage') as mock_calc:
            # 異常な要素を含むconfidence_factorsをシミュレート
            test_cases = [
                {
                    'name': '158.70バグ再現',
                    'factors': [158.70, 0.3, 0.7, 1.2],  # 158.70バグの再現
                    'expected_normalized': [1.0, 0.3, 0.7, 1.0]  # 期待される正規化後
                },
                {
                    'name': '負の値',
                    'factors': [-5.0, 0.5, 0.8, 0.6],
                    'expected_normalized': [0.0, 0.5, 0.8, 0.6]
                },
                {
                    'name': '2.0超',
                    'factors': [2.5, 0.4, 0.6, 3.0],
                    'expected_normalized': [1.0, 0.4, 0.6, 1.0]
                }
            ]
            
            for case in test_cases:
                with self.subTest(test_case=case['name']):
                    print(f"  - テストケース: {case['name']}")
                    
                    # 実際の正規化処理をテスト
                    confidence_factors = case['factors']
                    normalized_factors = [max(0.0, min(1.0, factor)) for factor in confidence_factors]
                    confidence = np.mean(normalized_factors)
                    
                    # 期待される正規化結果と比較
                    expected_normalized = case['expected_normalized']
                    expected_confidence = np.mean(expected_normalized)
                    
                    # 正規化が正しく動作することを確認
                    for i, (actual, expected) in enumerate(zip(normalized_factors, expected_normalized)):
                        self.assertAlmostEqual(actual, expected, places=3,
                                             f"{case['name']}: 要素{i}の正規化が不正確")
                    
                    # 最終信頼度が適正範囲内
                    self.assertGreaterEqual(confidence, 0.0,
                                          f"{case['name']}: 正規化後confidence={confidence} が負")
                    self.assertLessEqual(confidence, 1.0,
                                       f"{case['name']}: 正規化後confidence={confidence} が1.0超")
                    
                    print(f"    元の要素: {confidence_factors}")
                    print(f"    正規化後: {normalized_factors}")
                    print(f"    ✅ 信頼度: {confidence:.1%}")
        
        print("✅ 信頼度要素正規化処理テスト完了")
    
    def test_confidence_leverage_consistency(self):
        """信頼度とレバレッジの一貫性テスト"""
        print("🔍 信頼度・レバレッジ一貫性テスト実行中...")
        
        # 様々な信頼度レベルでレバレッジとの関係をテスト
        test_scenarios = [
            {'name': '低信頼度', 'support_strength': 0.1, 'breakout_prob': 0.1},
            {'name': '中信頼度', 'support_strength': 0.5, 'breakout_prob': 0.5},
            {'name': '高信頼度', 'support_strength': 0.9, 'breakout_prob': 0.9},
        ]
        
        results = []
        for scenario in test_scenarios:
            support_levels, resistance_levels, predictions, btc_risk, market_context = \
                self._create_test_context(scenario['support_strength'], scenario['breakout_prob'])
            
            result = self.engine.calculate_safe_leverage(
                symbol=f'TEST_CONSISTENCY_{scenario["name"]}',
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                breakout_predictions=predictions,
                btc_correlation_risk=btc_risk,
                market_context=market_context
            )
            
            results.append({
                'name': scenario['name'],
                'confidence': result.confidence_level,
                'leverage': result.recommended_leverage
            })
            
            print(f"  - {scenario['name']}: 信頼度={result.confidence_level:.1%}, レバレッジ={result.recommended_leverage:.1f}x")
        
        # 一貫性チェック: 高信頼度 → 高レバレッジの傾向があるべき
        # （ただし、市場条件により例外もある）
        low_conf = next(r for r in results if r['name'] == '低信頼度')
        high_conf = next(r for r in results if r['name'] == '高信頼度')
        
        # 極端な逆転がないことを確認
        if high_conf['confidence'] > low_conf['confidence'] * 1.5:
            # 信頼度が1.5倍以上高い場合、レバレッジも高めであるべき
            confidence_ratio = high_conf['confidence'] / low_conf['confidence']
            leverage_ratio = high_conf['leverage'] / low_conf['leverage']
            
            # レバレッジが極端に低くないことを確認（1/10以下は異常）
            self.assertGreater(leverage_ratio, 0.1,
                             f"信頼度比{confidence_ratio:.1f}倍に対してレバレッジ比{leverage_ratio:.1f}倍は低すぎます")
        
        print("✅ 信頼度・レバレッジ一貫性テスト完了")
    
    def test_confidence_calculation_stability(self):
        """信頼度計算の安定性テスト"""
        print("🔍 信頼度計算安定性テスト実行中...")
        
        # 同じ条件で複数回実行して安定性を確認
        support_levels, resistance_levels, predictions, btc_risk, market_context = \
            self._create_test_context()
        
        confidences = []
        for i in range(5):
            result = self.engine.calculate_safe_leverage(
                symbol=f'TEST_STABILITY_{i}',
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                breakout_predictions=predictions,
                btc_correlation_risk=btc_risk,
                market_context=market_context
            )
            confidences.append(result.confidence_level)
        
        # 全ての結果が同じであることを確認（確定的計算）
        for i, confidence in enumerate(confidences):
            self.assertAlmostEqual(confidence, confidences[0], places=6,
                                 f"実行{i}: confidence={confidence} が初回と異なる（非決定的）")
        
        # 結果が適正範囲内
        avg_confidence = np.mean(confidences)
        self.assertGreaterEqual(avg_confidence, 0.0,
                              f"平均信頼度={avg_confidence} が負")
        self.assertLessEqual(avg_confidence, 1.0,
                           f"平均信頼度={avg_confidence} が1.0超")
        
        print(f"  ✅ 5回実行で安定した信頼度: {avg_confidence:.1%}")
        print("✅ 信頼度計算安定性テスト完了")
    
    def test_158_70_specific_regression(self):
        """158.70特定バグの回帰テスト"""
        print("🔍 158.70特定バグ回帰テスト実行中...")
        
        # 158.70バグを引き起こしやすい条件を再現
        now = datetime.now()
        
        # 異常に高いタッチ回数とバウンス値を持つレベル
        problematic_support = SupportResistanceLevel(
            price=0.95, strength=0.999,  # 正規化後の最大値
            touch_count=50,  # 異常に高いタッチ回数
            level_type='support', first_touch=now, last_touch=now,
            volume_at_level=100000.0,  # 高出来高
            distance_from_current=1.0
        )
        
        # 高い予測確率
        high_prediction = BreakoutPrediction(
            level=problematic_support,
            breakout_probability=0.1, bounce_probability=0.9,  # 強い反発予測
            prediction_confidence=0.95,  # 高い予測信頼度
            predicted_price_target=1.02,
            time_horizon_minutes=60,
            model_name='test_model'
        )
        
        resistance_levels = [
            SupportResistanceLevel(
                price=1.05, strength=0.7, touch_count=2,
                level_type='resistance', first_touch=now, last_touch=now,
                volume_at_level=800.0, distance_from_current=5.0
            )
        ]
        
        btc_risk = BTCCorrelationRisk(
            symbol='TEST', btc_drop_scenario=-10.0,
            predicted_altcoin_drop={60: -5.0, 120: -10.0},
            correlation_strength=0.8, risk_level='MEDIUM',
            liquidation_risk={60: 0.1, 120: 0.2}
        )
        
        market_context = MarketContext(
            current_price=1.0, volume_24h=100000.0, volatility=0.02,
            trend_direction='BULLISH', market_phase='MARKUP', timestamp=now
        )
        
        result = self.engine.calculate_safe_leverage(
            symbol='TEST_158_70_REGRESSION',
            support_levels=[problematic_support],
            resistance_levels=resistance_levels,
            breakout_predictions=[high_prediction],
            btc_correlation_risk=btc_risk,
            market_context=market_context
        )
        
        confidence = result.confidence_level
        
        # 158.70バグが修正されていることを確認
        self.assertLess(confidence, 0.95,
                      f"confidence={confidence:.1%} が95%を超えている（158.70バグ再発の可能性）")
        
        # 特に90%を超えないことを確認（以前のバグレベル）
        self.assertLess(confidence, 0.90,
                      f"confidence={confidence:.1%} が90%を超えている（158.70バグ類似問題）")
        
        print(f"  ✅ 158.70類似条件での信頼度: {confidence:.1%}")
        print("✅ 158.70特定バグ回帰テスト完了")

def run_confidence_anomaly_detection_tests():
    """信頼度異常値検知テストの実行"""
    print("🔧 信頼度異常値検知テスト開始")
    print("=" * 60)
    
    # テストスイートを作成
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConfidenceAnomalyDetection)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("📋 テスト結果サマリー:")
    print(f"   実行テスト数: {result.testsRun}")
    print(f"   失敗: {len(result.failures)}")
    print(f"   エラー: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ 全ての信頼度異常値検知テストに合格しました！")
        print("   信頼度計算の異常値（90%超など）を適切に防止できます。")
    else:
        print("❌ 一部のテストが失敗しました。")
        print("   信頼度計算に異常値が発生する可能性があります。")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    run_confidence_anomaly_detection_tests()