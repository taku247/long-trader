#!/usr/bin/env python3
"""
中重量フィルター（Filter 4-6）の実装

より詳細な分析を行う中重量フィルターを定義。
軽量フィルターを通過した評価時点に対して、より精密な検証を実行。
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from engines.filters.base_filter import BaseFilter, FilterResult

# ロガー設定
logger = logging.getLogger(__name__)


class DistanceAnalysisFilter(BaseFilter):
    """Filter 4: 距離・強度分析フィルター（中重量）"""
    
    def __init__(self):
        super().__init__("distance_analysis", "medium", 20)
    
    def execute(self, prepared_data, strategy, evaluation_time: datetime) -> FilterResult:
        """支持線・抵抗線からの距離と強度を分析"""
        self.execution_count += 1
        
        try:
            current_price = prepared_data.get_price_at(evaluation_time)
            
            # 支持線・抵抗線データを取得
            # TODO: 実際のデータ取得ロジックと連携
            support_levels, resistance_levels = self._get_support_resistance_levels(
                prepared_data, evaluation_time
            )
            
            # 支持線距離チェック
            support_distance_result = self._check_support_distance(
                current_price, support_levels, strategy
            )
            if not support_distance_result['passed']:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=support_distance_result['reason'],
                    metrics=support_distance_result['metrics']
                )
            
            # 抵抗線距離チェック
            resistance_distance_result = self._check_resistance_distance(
                current_price, resistance_levels, strategy
            )
            if not resistance_distance_result['passed']:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=resistance_distance_result['reason'],
                    metrics=resistance_distance_result['metrics']
                )
            
            # 強度チェック
            strength_result = self._check_level_strength(
                support_levels, resistance_levels, strategy
            )
            if not strength_result['passed']:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=strength_result['reason'],
                    metrics=strength_result['metrics']
                )
            
            self.success_count += 1
            return FilterResult(
                passed=True,
                reason="距離・強度分析チェック合格",
                metrics={
                    'support_distance': support_distance_result['metrics'],
                    'resistance_distance': resistance_distance_result['metrics'],
                    'strength_analysis': strength_result['metrics']
                }
            )
            
        except Exception as e:
            self.failure_count += 1
            return FilterResult(
                passed=False,
                reason=f"距離・強度分析中にエラー: {str(e)}",
                metrics={'error': str(e)}
            )
    
    def _get_support_resistance_levels(self, prepared_data, evaluation_time):
        """支持線・抵抗線データを取得（現在はモック実装）"""
        # TODO: 実際の支持線・抵抗線検出システムと連携
        
        current_price = prepared_data.get_price_at(evaluation_time)
        
        # 評価時点によって異なる距離の支持線・抵抗線を生成
        # 60%の確率で適切な距離になるようハッシュベースで調整
        test_hash = hash(str(evaluation_time))
        distance_modifier = (test_hash % 100) / 100.0  # 0.0-1.0
        
        if distance_modifier < 0.6:  # 60%の確率で通過
            # 適切な距離の支持線・抵抗線
            support_distance_pct = 1.0 + distance_modifier * 3.0  # 1.0-4.0%
            resistance_distance_pct = 2.0 + distance_modifier * 4.0  # 2.0-6.0%
        else:
            # 距離条件に引っかかる支持線・抵抗線
            if distance_modifier < 0.8:  # 20%は近すぎる
                support_distance_pct = 0.2  # 0.2% (閾値0.5%未満)
                resistance_distance_pct = 0.5  # 0.5% (閾値1.0%未満)
            else:  # 20%は遠すぎる
                support_distance_pct = 6.0  # 6.0% (閾値5.0%超過)
                resistance_distance_pct = 9.0  # 9.0% (閾値8.0%超過)
        
        # 支持線・抵抗線価格を計算
        support_price = current_price * (1.0 - support_distance_pct / 100.0)
        resistance_price = current_price * (1.0 + resistance_distance_pct / 100.0)
        
        # モック支持線データ
        mock_support = type('MockLevel', (), {
            'price': support_price,
            'strength': 0.8,
            'distance_from_current': support_distance_pct,
            'touch_count': 3
        })()
        
        # モック抵抗線データ
        mock_resistance = type('MockLevel', (), {
            'price': resistance_price,
            'strength': 0.75,
            'distance_from_current': resistance_distance_pct,
            'touch_count': 3
        })()
        
        return [mock_support], [mock_resistance]
    
    def _check_support_distance(self, current_price: float, support_levels: List, strategy) -> Dict:
        """支持線からの距離をチェック"""
        if not support_levels:
            return {
                'passed': False,
                'reason': '有効な支持線が見つかりません',
                'metrics': {'support_count': 0}
            }
        
        # 最も近い支持線を取得
        nearest_support = min(support_levels, key=lambda s: abs(current_price - s.price))
        # distance_from_currentプロパティがある場合はそれを使用、ない場合は計算
        if hasattr(nearest_support, 'distance_from_current'):
            distance_pct = nearest_support.distance_from_current
        else:
            distance_pct = ((current_price - nearest_support.price) / current_price) * 100
        
        # 距離チェック
        if distance_pct < strategy.min_distance_from_support:
            return {
                'passed': False,
                'reason': f'支持線に近すぎます: {distance_pct:.2f}% < {strategy.min_distance_from_support}%',
                'metrics': {
                    'distance_pct': distance_pct,
                    'min_required': strategy.min_distance_from_support,
                    'support_price': nearest_support.price
                }
            }
        
        if distance_pct > strategy.max_distance_from_support:
            return {
                'passed': False,
                'reason': f'支持線から遠すぎます: {distance_pct:.2f}% > {strategy.max_distance_from_support}%',
                'metrics': {
                    'distance_pct': distance_pct,
                    'max_allowed': strategy.max_distance_from_support,
                    'support_price': nearest_support.price
                }
            }
        
        return {
            'passed': True,
            'reason': '支持線距離チェック合格',
            'metrics': {
                'distance_pct': distance_pct,
                'support_price': nearest_support.price,
                'support_strength': nearest_support.strength
            }
        }
    
    def _check_resistance_distance(self, current_price: float, resistance_levels: List, strategy) -> Dict:
        """抵抗線からの距離をチェック"""
        if not resistance_levels:
            return {
                'passed': False,
                'reason': '有効な抵抗線が見つかりません',
                'metrics': {'resistance_count': 0}
            }
        
        # 最も近い抵抗線を取得
        nearest_resistance = min(resistance_levels, key=lambda r: abs(r.price - current_price))
        # distance_from_currentプロパティがある場合はそれを使用、ない場合は計算
        if hasattr(nearest_resistance, 'distance_from_current'):
            distance_pct = nearest_resistance.distance_from_current
        else:
            distance_pct = ((nearest_resistance.price - current_price) / current_price) * 100
        
        # 距離チェック
        if distance_pct < strategy.min_distance_from_resistance:
            return {
                'passed': False,
                'reason': f'抵抗線に近すぎます: {distance_pct:.2f}% < {strategy.min_distance_from_resistance}%',
                'metrics': {
                    'distance_pct': distance_pct,
                    'min_required': strategy.min_distance_from_resistance,
                    'resistance_price': nearest_resistance.price
                }
            }
        
        if distance_pct > strategy.max_distance_from_resistance:
            return {
                'passed': False,
                'reason': f'抵抗線から遠すぎます: {distance_pct:.2f}% > {strategy.max_distance_from_resistance}%',
                'metrics': {
                    'distance_pct': distance_pct,
                    'max_allowed': strategy.max_distance_from_resistance,
                    'resistance_price': nearest_resistance.price
                }
            }
        
        return {
            'passed': True,
            'reason': '抵抗線距離チェック合格',
            'metrics': {
                'distance_pct': distance_pct,
                'resistance_price': nearest_resistance.price,
                'resistance_strength': nearest_resistance.strength
            }
        }
    
    def _check_level_strength(self, support_levels: List, resistance_levels: List, strategy) -> Dict:
        """支持線・抵抗線の強度をチェック"""
        
        # 支持線強度チェック
        strong_supports = [s for s in support_levels if s.strength >= strategy.min_support_strength]
        if not strong_supports:
            return {
                'passed': False,
                'reason': f'十分な強度の支持線がありません（要求: {strategy.min_support_strength}）',
                'metrics': {
                    'support_count': len(support_levels),
                    'strong_support_count': len(strong_supports),
                    'min_required_strength': strategy.min_support_strength
                }
            }
        
        # 抵抗線強度チェック
        strong_resistances = [r for r in resistance_levels if r.strength >= strategy.min_resistance_strength]
        if not strong_resistances:
            return {
                'passed': False,
                'reason': f'十分な強度の抵抗線がありません（要求: {strategy.min_resistance_strength}）',
                'metrics': {
                    'resistance_count': len(resistance_levels),
                    'strong_resistance_count': len(strong_resistances),
                    'min_required_strength': strategy.min_resistance_strength
                }
            }
        
        return {
            'passed': True,
            'reason': '強度チェック合格',
            'metrics': {
                'strong_support_count': len(strong_supports),
                'strong_resistance_count': len(strong_resistances),
                'avg_support_strength': sum(s.strength for s in strong_supports) / len(strong_supports),
                'avg_resistance_strength': sum(r.strength for r in strong_resistances) / len(strong_resistances)
            }
        }


class MLConfidenceFilter(BaseFilter):
    """Filter 5: ML信頼度フィルター（中重量）"""
    
    def __init__(self):
        super().__init__("ml_confidence", "medium", 25)
    
    def execute(self, prepared_data, strategy, evaluation_time: datetime) -> FilterResult:
        """ML予測の信頼度とシグナル強度を分析"""
        self.execution_count += 1
        
        try:
            # ML予測データを取得
            ml_confidence = prepared_data.get_ml_confidence_at(evaluation_time)
            ml_prediction = prepared_data.get_ml_prediction_at(evaluation_time)
            ml_signal_strength = prepared_data.get_ml_signal_strength_at(evaluation_time)
            
            # 信頼度チェック
            if ml_confidence < strategy.min_ml_confidence:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f'ML信頼度不足: {ml_confidence:.2f} < {strategy.min_ml_confidence}',
                    metrics={
                        'ml_confidence': ml_confidence,
                        'min_required': strategy.min_ml_confidence,
                        'ml_prediction': ml_prediction
                    }
                )
            
            # シグナル方向チェック
            if ml_prediction != strategy.required_ml_signal:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f'ML予測が期待と異なります: {ml_prediction} != {strategy.required_ml_signal}',
                    metrics={
                        'ml_prediction': ml_prediction,
                        'required_signal': strategy.required_ml_signal,
                        'ml_confidence': ml_confidence
                    }
                )
            
            # シグナル強度チェック
            if ml_signal_strength < strategy.min_ml_signal_strength:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f'MLシグナル強度不足: {ml_signal_strength:.2f} < {strategy.min_ml_signal_strength}',
                    metrics={
                        'ml_signal_strength': ml_signal_strength,
                        'min_required': strategy.min_ml_signal_strength,
                        'ml_prediction': ml_prediction,
                        'ml_confidence': ml_confidence
                    }
                )
            
            self.success_count += 1
            return FilterResult(
                passed=True,
                reason="ML信頼度チェック合格",
                metrics={
                    'ml_confidence': ml_confidence,
                    'ml_prediction': ml_prediction,
                    'ml_signal_strength': ml_signal_strength,
                    'confidence_score': ml_confidence * ml_signal_strength  # 総合スコア
                }
            )
            
        except Exception as e:
            self.failure_count += 1
            return FilterResult(
                passed=False,
                reason=f"ML信頼度分析中にエラー: {str(e)}",
                metrics={'error': str(e)}
            )


class VolatilityFilter(BaseFilter):
    """Filter 6: ボラティリティフィルター（中重量）"""
    
    def __init__(self):
        super().__init__("volatility", "medium", 20)
    
    def execute(self, prepared_data, strategy, evaluation_time: datetime) -> FilterResult:
        """ボラティリティと価格安定性を分析"""
        self.execution_count += 1
        
        try:
            current_price = prepared_data.get_price_at(evaluation_time)
            volatility = prepared_data.get_volatility_at(evaluation_time)
            atr = prepared_data.get_atr_at(evaluation_time)
            price_change_volatility = prepared_data.get_price_change_volatility_at(evaluation_time)
            
            # ATR比率計算
            atr_ratio = atr / current_price if current_price > 0 else 0
            
            # 最小ボラティリティチェック
            if volatility < strategy.min_volatility:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f'ボラティリティ不足: {volatility:.3f} < {strategy.min_volatility}',
                    metrics={
                        'volatility': volatility,
                        'min_required': strategy.min_volatility,
                        'atr_ratio': atr_ratio
                    }
                )
            
            # 最大ボラティリティチェック
            if volatility > strategy.max_volatility:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f'ボラティリティ過大: {volatility:.3f} > {strategy.max_volatility}',
                    metrics={
                        'volatility': volatility,
                        'max_allowed': strategy.max_volatility,
                        'atr_ratio': atr_ratio
                    }
                )
            
            # ATR比率チェック
            if atr_ratio > strategy.max_atr_ratio:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f'ATR比率過大: {atr_ratio:.3f} > {strategy.max_atr_ratio}',
                    metrics={
                        'atr_ratio': atr_ratio,
                        'max_allowed': strategy.max_atr_ratio,
                        'atr': atr,
                        'current_price': current_price
                    }
                )
            
            # 価格変動安定性チェック（追加要件）
            stability_score = self._calculate_price_stability(
                volatility, atr_ratio, price_change_volatility
            )
            
            if stability_score < 0.5:  # 安定性スコアが0.5未満は不安定
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f'価格安定性不足: スコア {stability_score:.2f} < 0.5',
                    metrics={
                        'stability_score': stability_score,
                        'volatility': volatility,
                        'atr_ratio': atr_ratio,
                        'price_change_volatility': price_change_volatility
                    }
                )
            
            self.success_count += 1
            return FilterResult(
                passed=True,
                reason="ボラティリティチェック合格",
                metrics={
                    'volatility': volatility,
                    'atr_ratio': atr_ratio,
                    'price_change_volatility': price_change_volatility,
                    'stability_score': stability_score
                }
            )
            
        except Exception as e:
            self.failure_count += 1
            return FilterResult(
                passed=False,
                reason=f"ボラティリティ分析中にエラー: {str(e)}",
                metrics={'error': str(e)}
            )
    
    def _calculate_price_stability(self, volatility: float, atr_ratio: float, price_change_vol: float) -> float:
        """価格安定性スコアを計算（0.0-1.0）"""
        
        # 各要素を正規化（0.0-1.0の範囲に）
        vol_score = max(0.0, min(1.0, 1.0 - (volatility / 0.2)))  # 20%ボラティリティで0点
        atr_score = max(0.0, min(1.0, 1.0 - (atr_ratio / 0.1)))   # 10%ATR比率で0点
        change_score = max(0.0, min(1.0, 1.0 - (price_change_vol / 0.15)))  # 15%価格変動で0点
        
        # 重み付き平均（ボラティリティを重視）
        stability_score = (vol_score * 0.5 + atr_score * 0.3 + change_score * 0.2)
        
        return stability_score