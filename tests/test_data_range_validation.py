#!/usr/bin/env python3
"""
データ型範囲検証テスト

システム全体でデータ型が期待される範囲内にあることを確認し、
158.70のような範囲外異常値バグを包括的に防止するテストスイート。
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

from interfaces.data_types import (
    SupportResistanceLevel, BreakoutPrediction, BTCCorrelationRisk,
    MarketContext, LeverageRecommendation
)
from engines.leverage_decision_engine import CoreLeverageDecisionEngine
from adapters.existing_adapters import (
    ExistingSupportResistanceAdapter, ExistingBreakoutPredictor,
    ExistingBTCCorrelationAnalyzer, ExistingMarketContextAnalyzer
)

class TestDataRangeValidation(unittest.TestCase):
    """データ型範囲検証テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_data = self._generate_test_data()
        self.adapters = {
            'support_resistance': ExistingSupportResistanceAdapter(),
            'breakout': ExistingBreakoutPredictor(),
            'btc_correlation': ExistingBTCCorrelationAnalyzer(),
            'market_context': ExistingMarketContextAnalyzer()
        }
        self.engine = CoreLeverageDecisionEngine()
    
    def _generate_test_data(self, days=50):
        """テスト用データ生成"""
        dates = [datetime.now() - timedelta(days=i) for i in range(days)]
        prices = [1.0 + 0.1 * np.sin(i * 0.1) + np.random.normal(0, 0.02) for i in range(days)]
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * 1.02 for p in prices],
            'low': [p * 0.98 for p in prices],
            'close': prices,
            'volume': [1000 + np.random.normal(0, 100) for _ in range(days)]
        })
    
    def test_support_resistance_level_range_validation(self):
        """SupportResistanceLevelの範囲検証"""
        print("🔍 SupportResistanceLevel範囲検証テスト実行中...")
        
        levels = self.adapters['support_resistance'].find_levels(self.test_data)
        
        self.assertGreater(len(levels), 0, "サポレジレベルが検出されませんでした")
        
        for i, level in enumerate(levels):
            with self.subTest(level_index=i):
                # 強度範囲検証（最重要）
                self.assertGreaterEqual(level.strength, 0.0,
                                      f"レベル{i}: strength={level.strength} が負の値")
                self.assertLessEqual(level.strength, 1.0,
                                   f"レベル{i}: strength={level.strength} が1.0超（158.70バグ再発）")
                
                # 価格範囲検証
                self.assertGreater(level.price, 0.0,
                                 f"レベル{i}: price={level.price} が0以下")
                self.assertLess(level.price, 1000000.0,
                              f"レベル{i}: price={level.price} が異常に高い")
                
                # タッチ回数検証
                self.assertGreaterEqual(level.touch_count, 1,
                                      f"レベル{i}: touch_count={level.touch_count} が1未満")
                self.assertLessEqual(level.touch_count, 1000,
                                   f"レベル{i}: touch_count={level.touch_count} が異常に高い")
                
                # 距離検証
                self.assertGreaterEqual(level.distance_from_current, 0.0,
                                      f"レベル{i}: distance_from_current={level.distance_from_current} が負")
                self.assertLessEqual(level.distance_from_current, 100.0,
                                   f"レベル{i}: distance_from_current={level.distance_from_current} が100%超")
                
                # 出来高検証
                self.assertGreaterEqual(level.volume_at_level, 0.0,
                                      f"レベル{i}: volume_at_level={level.volume_at_level} が負")
                
                # NaN/Inf検証
                for field_name in ['strength', 'price', 'touch_count', 'distance_from_current', 'volume_at_level']:
                    field_value = getattr(level, field_name)
                    self.assertFalse(np.isnan(field_value),
                                   f"レベル{i}: {field_name}={field_value} がNaN")
                    self.assertFalse(np.isinf(field_value),
                                   f"レベル{i}: {field_name}={field_value} が無限大")
        
        print(f"✅ {len(levels)}個のSupportResistanceLevelの範囲検証完了")
    
    def test_breakout_prediction_range_validation(self):
        """BreakoutPredictionの範囲検証"""
        print("🔍 BreakoutPrediction範囲検証テスト実行中...")
        
        # サポレジレベルを取得
        levels = self.adapters['support_resistance'].find_levels(self.test_data)
        
        if not levels:
            self.skipTest("テスト用レベルが検出されませんでした")
        
        for i, level in enumerate(levels[:5]):  # 最初の5個をテスト
            with self.subTest(level_index=i):
                prediction = self.adapters['breakout'].predict_breakout(level, self.test_data)
                
                # 確率範囲検証（0-1）
                self.assertGreaterEqual(prediction.breakout_probability, 0.0,
                                      f"予測{i}: breakout_probability={prediction.breakout_probability} が負")
                self.assertLessEqual(prediction.breakout_probability, 1.0,
                                   f"予測{i}: breakout_probability={prediction.breakout_probability} が1.0超")
                
                self.assertGreaterEqual(prediction.bounce_probability, 0.0,
                                      f"予測{i}: bounce_probability={prediction.bounce_probability} が負")
                self.assertLessEqual(prediction.bounce_probability, 1.0,
                                   f"予測{i}: bounce_probability={prediction.bounce_probability} が1.0超")
                
                self.assertGreaterEqual(prediction.prediction_confidence, 0.0,
                                      f"予測{i}: prediction_confidence={prediction.prediction_confidence} が負")
                self.assertLessEqual(prediction.prediction_confidence, 1.0,
                                   f"予測{i}: prediction_confidence={prediction.prediction_confidence} が1.0超")
                
                # 確率の合計が1.0に近いことを確認
                prob_sum = prediction.breakout_probability + prediction.bounce_probability
                self.assertAlmostEqual(prob_sum, 1.0, places=2,
                                     f"予測{i}: 確率の合計={prob_sum} が1.0から離れすぎ")
                
                # 時間範囲検証
                self.assertGreater(prediction.time_horizon_minutes, 0,
                                 f"予測{i}: time_horizon_minutes={prediction.time_horizon_minutes} が0以下")
                self.assertLess(prediction.time_horizon_minutes, 10080,  # 1週間
                              f"予測{i}: time_horizon_minutes={prediction.time_horizon_minutes} が異常に長い")
                
                # 価格ターゲット検証（存在する場合）
                if prediction.predicted_price_target is not None:
                    self.assertGreater(prediction.predicted_price_target, 0.0,
                                     f"予測{i}: predicted_price_target={prediction.predicted_price_target} が0以下")
        
        print(f"✅ BreakoutPrediction範囲検証完了")
    
    def test_btc_correlation_risk_range_validation(self):
        """BTCCorrelationRiskの範囲検証"""
        print("🔍 BTCCorrelationRisk範囲検証テスト実行中...")
        
        risk = self.adapters['btc_correlation'].analyze_correlation('TEST', self.test_data)
        
        # 相関強度検証（0-1）
        self.assertGreaterEqual(risk.correlation_strength, 0.0,
                              f"correlation_strength={risk.correlation_strength} が負")
        self.assertLessEqual(risk.correlation_strength, 1.0,
                           f"correlation_strength={risk.correlation_strength} が1.0超")
        
        # リスクレベル検証
        valid_risk_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        self.assertIn(risk.risk_level, valid_risk_levels,
                     f"risk_level={risk.risk_level} が無効な値")
        
        # BTC下落シナリオ検証
        self.assertLessEqual(risk.btc_drop_scenario, 0.0,
                           f"btc_drop_scenario={risk.btc_drop_scenario} が正の値（下落なのに上昇）")
        self.assertGreaterEqual(risk.btc_drop_scenario, -100.0,
                              f"btc_drop_scenario={risk.btc_drop_scenario} が-100%未満（非現実的）")
        
        # 予測下落率検証
        for timeframe, drop_rate in risk.predicted_altcoin_drop.items():
            self.assertIsInstance(timeframe, int,
                                f"予測時間枠 {timeframe} が整数ではない")
            self.assertGreater(timeframe, 0,
                             f"予測時間枠 {timeframe} が0以下")
            self.assertLessEqual(drop_rate, 0.0,
                               f"予測下落率 {drop_rate} が正の値")
            self.assertGreaterEqual(drop_rate, -100.0,
                                  f"予測下落率 {drop_rate} が-100%未満")
        
        # 清算リスク検証（0-1）
        for timeframe, liquidation_risk in risk.liquidation_risk.items():
            self.assertGreaterEqual(liquidation_risk, 0.0,
                                  f"清算リスク {liquidation_risk} が負")
            self.assertLessEqual(liquidation_risk, 1.0,
                               f"清算リスク {liquidation_risk} が1.0超")
        
        print(f"✅ BTCCorrelationRisk範囲検証完了")
    
    def test_market_context_range_validation(self):
        """MarketContextの範囲検証"""
        print("🔍 MarketContext範囲検証テスト実行中...")
        
        context = self.adapters['market_context'].analyze_market_phase(self.test_data)
        
        # 価格検証
        self.assertGreater(context.current_price, 0.0,
                         f"current_price={context.current_price} が0以下")
        
        # 出来高検証
        self.assertGreaterEqual(context.volume_24h, 0.0,
                              f"volume_24h={context.volume_24h} が負")
        
        # ボラティリティ検証（0以上、通常は1.0未満）
        self.assertGreaterEqual(context.volatility, 0.0,
                              f"volatility={context.volatility} が負")
        self.assertLess(context.volatility, 10.0,
                      f"volatility={context.volatility} が異常に高い（1000%超）")
        
        # トレンド方向検証
        valid_trends = ['BULLISH', 'BEARISH', 'SIDEWAYS']
        self.assertIn(context.trend_direction, valid_trends,
                     f"trend_direction={context.trend_direction} が無効な値")
        
        # 市場フェーズ検証
        valid_phases = ['ACCUMULATION', 'MARKUP', 'DISTRIBUTION', 'MARKDOWN']
        self.assertIn(context.market_phase, valid_phases,
                     f"market_phase={context.market_phase} が無効な値")
        
        # タイムスタンプ検証
        self.assertIsInstance(context.timestamp, datetime,
                            f"timestamp={context.timestamp} がdatetimeインスタンスではない")
        
        print(f"✅ MarketContext範囲検証完了")
    
    def test_leverage_recommendation_range_validation(self):
        """LeverageRecommendationの範囲検証"""
        print("🔍 LeverageRecommendation範囲検証テスト実行中...")
        
        # 必要なデータを準備
        levels = self.adapters['support_resistance'].find_levels(self.test_data)
        
        if not levels:
            self.skipTest("テスト用レベルが検出されませんでした")
        
        support_levels = [l for l in levels if l.level_type == 'support'][:3]
        resistance_levels = [l for l in levels if l.level_type == 'resistance'][:3]
        
        if not support_levels or not resistance_levels:
            self.skipTest("サポートまたはレジスタンスレベルが不足")
        
        # 予測とコンテキストを準備
        predictions = [self.adapters['breakout'].predict_breakout(level, self.test_data) 
                      for level in support_levels + resistance_levels]
        btc_risk = self.adapters['btc_correlation'].analyze_correlation('TEST', self.test_data)
        market_context = self.adapters['market_context'].analyze_market_phase(self.test_data)
        
        # レバレッジ計算実行
        recommendation = self.engine.calculate_safe_leverage(
            symbol='TEST_RANGE',
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            breakout_predictions=predictions,
            btc_correlation_risk=btc_risk,
            market_context=market_context
        )
        
        # 推奨レバレッジ検証
        self.assertGreater(recommendation.recommended_leverage, 0.0,
                         f"recommended_leverage={recommendation.recommended_leverage} が0以下")
        self.assertLessEqual(recommendation.recommended_leverage, 100.0,
                           f"recommended_leverage={recommendation.recommended_leverage} が100倍超（異常）")
        
        # 最大安全レバレッジ検証
        self.assertGreater(recommendation.max_safe_leverage, 0.0,
                         f"max_safe_leverage={recommendation.max_safe_leverage} が0以下")
        self.assertLessEqual(recommendation.max_safe_leverage, 100.0,
                           f"max_safe_leverage={recommendation.max_safe_leverage} が100倍超")
        
        # レバレッジの論理的整合性
        self.assertLessEqual(recommendation.recommended_leverage, recommendation.max_safe_leverage,
                           "推奨レバレッジが最大安全レバレッジを超えています")
        
        # リスクリワード比検証
        self.assertGreater(recommendation.risk_reward_ratio, 0.0,
                         f"risk_reward_ratio={recommendation.risk_reward_ratio} が0以下")
        self.assertLess(recommendation.risk_reward_ratio, 100.0,
                      f"risk_reward_ratio={recommendation.risk_reward_ratio} が異常に高い")
        
        # 信頼度検証（0-1）
        self.assertGreaterEqual(recommendation.confidence_level, 0.0,
                              f"confidence_level={recommendation.confidence_level} が負")
        self.assertLessEqual(recommendation.confidence_level, 1.0,
                           f"confidence_level={recommendation.confidence_level} が1.0超")
        
        # 価格検証
        self.assertGreater(recommendation.stop_loss_price, 0.0,
                         f"stop_loss_price={recommendation.stop_loss_price} が0以下")
        self.assertGreater(recommendation.take_profit_price, 0.0,
                         f"take_profit_price={recommendation.take_profit_price} が0以下")
        
        # 損切り・利確の論理的整合性
        current_price = market_context.current_price
        self.assertLess(recommendation.stop_loss_price, current_price,
                      "損切り価格が現在価格以上（ロング想定で不適切）")
        self.assertGreater(recommendation.take_profit_price, current_price,
                         "利確価格が現在価格以下（ロング想定で不適切）")
        
        print(f"✅ LeverageRecommendation範囲検証完了")
        print(f"   推奨レバレッジ: {recommendation.recommended_leverage:.1f}x")
        print(f"   信頼度: {recommendation.confidence_level:.1%}")
        print(f"   リスクリワード比: {recommendation.risk_reward_ratio:.2f}")
    
    def test_comprehensive_pipeline_range_validation(self):
        """包括的パイプライン範囲検証"""
        print("🔍 包括的パイプライン範囲検証テスト実行中...")
        
        # 複数の異なる条件でパイプライン全体をテスト
        test_conditions = [
            {'name': '通常条件', 'volatility_mult': 1.0, 'volume_mult': 1.0},
            {'name': '高ボラティリティ', 'volatility_mult': 5.0, 'volume_mult': 1.0},
            {'name': '高出来高', 'volatility_mult': 1.0, 'volume_mult': 10.0},
            {'name': '低ボラティリティ', 'volatility_mult': 0.1, 'volume_mult': 1.0}
        ]
        
        for condition in test_conditions:
            with self.subTest(condition=condition['name']):
                print(f"  - 条件: {condition['name']}")
                
                # 条件に応じたテストデータを生成
                test_data = self.test_data.copy()
                
                if condition['volatility_mult'] != 1.0:
                    # ボラティリティを調整
                    returns = test_data['close'].pct_change().fillna(0)
                    adjusted_returns = returns * condition['volatility_mult']
                    test_data['close'] = test_data['close'].iloc[0] * (1 + adjusted_returns).cumprod()
                
                if condition['volume_mult'] != 1.0:
                    test_data['volume'] *= condition['volume_mult']
                
                try:
                    # パイプライン全体を実行
                    levels = self.adapters['support_resistance'].find_levels(test_data)
                    
                    if not levels:
                        continue  # レベルが検出されない場合はスキップ
                    
                    # 各レベルで強度が範囲内であることを確認
                    for level in levels:
                        self.assertGreaterEqual(level.strength, 0.0,
                                              f"{condition['name']}: strength={level.strength} が負")
                        self.assertLessEqual(level.strength, 1.0,
                                           f"{condition['name']}: strength={level.strength} が1.0超")
                    
                    print(f"    ✅ {len(levels)}レベルの範囲検証完了")
                    
                except Exception as e:
                    self.fail(f"{condition['name']}でパイプライン実行エラー: {e}")
        
        print(f"✅ 包括的パイプライン範囲検証完了")

def run_data_range_validation_tests():
    """データ範囲検証テストの実行"""
    print("🔧 データ型範囲検証テスト開始")
    print("=" * 60)
    
    # テストスイートを作成
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDataRangeValidation)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("📋 テスト結果サマリー:")
    print(f"   実行テスト数: {result.testsRun}")
    print(f"   失敗: {len(result.failures)}")
    print(f"   エラー: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ 全てのデータ範囲検証テストに合格しました！")
        print("   システム全体でデータが期待範囲内にあります。")
    else:
        print("❌ 一部のテストが失敗しました。")
        print("   データ範囲に問題がある可能性があります。")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    run_data_range_validation_tests()