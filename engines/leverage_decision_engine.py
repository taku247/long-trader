"""
レバレッジ判定エンジン

memo記載の核心機能「ハイレバのロング何倍かけて大丈夫か判定する」を実装。
サポレジ分析、ML予測、BTC相関を統合してレバレッジを決定します。
"""

import sys
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import warnings

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interfaces import (
    ILeverageDecisionEngine, IMarketContextAnalyzer, IStopLossTakeProfitCalculator,
    SupportResistanceLevel, BreakoutPrediction, BTCCorrelationRisk,
    MarketContext, LeverageRecommendation, TechnicalIndicators
)

warnings.filterwarnings('ignore')

class CoreLeverageDecisionEngine(ILeverageDecisionEngine):
    """
    コアレバレッジ判定エンジン
    
    memo記載の要素を統合:
    - 支持線の強度と近接性
    - 抵抗線までの利益ポテンシャル  
    - BTC相関による連れ安リスク
    - 市場異常検知
    """
    
    def __init__(self, sl_tp_calculator: Optional[IStopLossTakeProfitCalculator] = None):
        self.max_leverage = 100.0
        self.min_risk_reward = 2.0
        self.btc_correlation_threshold = 0.7
        self.min_support_strength = 0.6
        self.max_drawdown_tolerance = 0.15  # 15%
        self.sl_tp_calculator = sl_tp_calculator
    
    def calculate_safe_leverage(self, 
                              symbol: str,
                              support_levels: List[SupportResistanceLevel],
                              resistance_levels: List[SupportResistanceLevel],
                              breakout_predictions: List[BreakoutPrediction],
                              btc_correlation_risk: BTCCorrelationRisk,
                              market_context: MarketContext) -> LeverageRecommendation:
        """
        安全なレバレッジを総合的に判定
        
        memo記載の判定ロジック:
        1. 下落リスク評価 → ハイレバ倍率の上限決定
        2. 上昇ポテンシャル分析 → 利益期待値算出
        3. BTC相関リスク → 市場暴落時の連動下落リスク
        4. 総合リスクリワード → 最適レバレッジ推奨
        """
        
        try:
            reasoning = []
            current_price = market_context.current_price
            
            # === 1. 下落リスク評価 ===
            downside_analysis = self._analyze_downside_risk(
                current_price, support_levels, breakout_predictions, reasoning
            )
            
            # === 2. 上昇ポテンシャル分析 ===
            upside_analysis = self._analyze_upside_potential(
                current_price, resistance_levels, breakout_predictions, reasoning
            )
            
            # === 3. BTC相関リスク評価 ===
            btc_risk_analysis = self._analyze_btc_correlation_risk(
                btc_correlation_risk, reasoning
            )
            
            # === 4. 市場コンテキスト評価 ===
            market_risk_factor = self._analyze_market_context(market_context, reasoning)
            
            # === 5. 総合レバレッジ計算 ===
            leverage_recommendation = self._calculate_final_leverage(
                downside_analysis,
                upside_analysis, 
                btc_risk_analysis,
                market_risk_factor,
                current_price,
                reasoning,
                market_context
            )
            
            # デバッグログ: leverage_recommendationがNoneかチェック
            if leverage_recommendation is None:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"🚨 leverage_recommendation is None! This will cause no signal generation.")
                logger.error(f"   Symbol being analyzed: {getattr(self, '_current_symbol', 'UNKNOWN')}")
            
            # === 6. 損切り・利確ライン設定 ===
            if self.sl_tp_calculator:
                # プラグインを使用
                sl_tp_levels = self.sl_tp_calculator.calculate_levels(
                    current_price=current_price,
                    leverage=leverage_recommendation['recommended_leverage'],
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    market_context=market_context,
                    position_direction="long"
                )
                stop_loss = sl_tp_levels.stop_loss_price
                take_profit = sl_tp_levels.take_profit_price
                reasoning.extend([f"💡 {sl_tp_levels.calculation_method}計算方式使用"] + sl_tp_levels.reasoning)
            else:
                # 既存のロジックを使用
                stop_loss, take_profit = self._calculate_stop_loss_take_profit(
                    current_price,
                    downside_analysis,
                    upside_analysis,
                    leverage_recommendation['recommended_leverage']
                )
            
            # === 7. 最終推奨結果 ===
            # デバッグログ: 最終結果の値を確認
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"🎯 最終レバレッジ推奨結果:")
            logger.error(f"   recommended_leverage: {leverage_recommendation['recommended_leverage']}")
            logger.error(f"   confidence: {leverage_recommendation['confidence']}")
            logger.error(f"   risk_reward_ratio: {leverage_recommendation['risk_reward_ratio']}")
            
            return LeverageRecommendation(
                recommended_leverage=leverage_recommendation['recommended_leverage'],
                max_safe_leverage=leverage_recommendation['max_safe_leverage'],
                risk_reward_ratio=leverage_recommendation['risk_reward_ratio'],
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
                confidence_level=leverage_recommendation['confidence'],
                reasoning=reasoning,
                market_conditions=market_context
            )
            
        except Exception as e:
            # エラー時は保守的な推奨を返す
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"🚨 レバレッジ計算エラー: {str(e)}")
            logger.error(f"   エラータイプ: {type(e).__name__}")
            import traceback
            logger.error(f"   スタックトレース: {traceback.format_exc()}")
            
            return LeverageRecommendation(
                recommended_leverage=1.0,
                max_safe_leverage=2.0,
                risk_reward_ratio=1.0,
                stop_loss_price=market_context.current_price * 0.95,
                take_profit_price=market_context.current_price * 1.05,
                confidence_level=0.1,
                reasoning=[f"エラーが発生: {str(e)}", "保守的な設定を適用"],
                market_conditions=market_context
            )
    
    def _analyze_downside_risk(self, current_price: float, 
                             support_levels: List[SupportResistanceLevel],
                             breakout_predictions: List[BreakoutPrediction],
                             reasoning: List[str]) -> Dict:
        """
        下落リスク分析
        
        memo要素:
        - どの支持線まで下がりそうか → ハイレバ倍率の上限決定
        - 強い支持線が近くにあること
        - その支持線の下にも支持線があること（多層支持構造）
        """
        
        if not support_levels:
            reasoning.append("⚠️ サポートレベルが検出されていません")
            return {
                'nearest_support_distance': 0.20,  # 20%下落を想定
                'support_strength': 0.1,
                'multi_layer_protection': False,
                'max_leverage_from_support': 2.0
            }
        
        # 最も近いサポートレベルを特定
        nearest_supports = [s for s in support_levels if s.price < current_price]
        nearest_supports.sort(key=lambda x: abs(x.price - current_price))
        
        if not nearest_supports:
            reasoning.append("⚠️ 現在価格下方にサポートレベルがありません")
            return {
                'nearest_support_distance': 0.20,
                'support_strength': 0.1,
                'multi_layer_protection': False,
                'max_leverage_from_support': 2.0
            }
        
        # 最も近いサポートレベル
        nearest_support = nearest_supports[0]
        support_distance_pct = (current_price - nearest_support.price) / current_price
        
        reasoning.append(f"📍 最近サポートレベル: {nearest_support.price:.4f} ({support_distance_pct*100:.1f}%下)")
        reasoning.append(f"💪 サポート強度: {nearest_support.strength:.2f}")
        
        # 多層サポート構造の確認
        secondary_supports = [s for s in nearest_supports[1:3] if s.price < nearest_support.price]
        multi_layer_protection = len(secondary_supports) >= 1
        
        if multi_layer_protection:
            reasoning.append(f"🛡️ 多層サポート構造: {len(secondary_supports)}層の追加サポート")
        else:
            reasoning.append("⚠️ 単層サポート: 追加のサポートレベルが不足")
        
        # サポートレベルでの反発確率を予測から取得
        support_bounce_probability = 0.5  # デフォルト
        for prediction in breakout_predictions:
            if prediction.level.price == nearest_support.price:
                support_bounce_probability = prediction.bounce_probability
                reasoning.append(f"🎯 サポート反発確率: {support_bounce_probability*100:.1f}%")
                break
        
        # サポートベースの最大レバレッジ計算
        # 強いサポートが近くにある場合はより高いレバレッジが可能
        support_factor = nearest_support.strength * support_bounce_probability
        distance_factor = max(0.3, min(1.0, support_distance_pct / 0.1))  # 10%距離を基準
        multi_layer_factor = 1.3 if multi_layer_protection else 1.0
        
        max_leverage_from_support = min(
            self.max_leverage,
            (1 / support_distance_pct) * support_factor * distance_factor * multi_layer_factor
        )
        
        return {
            'nearest_support_distance': support_distance_pct,
            'support_strength': nearest_support.strength,
            'multi_layer_protection': multi_layer_protection,
            'support_bounce_probability': support_bounce_probability,
            'max_leverage_from_support': max_leverage_from_support
        }
    
    def _analyze_upside_potential(self, current_price: float,
                                resistance_levels: List[SupportResistanceLevel],
                                breakout_predictions: List[BreakoutPrediction],
                                reasoning: List[str]) -> Dict:
        """
        上昇ポテンシャル分析
        
        memo要素:
        - どの抵抗線まで上がりそうか → 利益期待値算出
        - 到達予想期間の分析
        """
        
        if not resistance_levels:
            reasoning.append("⚠️ レジスタンスレベルが検出されていません")
            return {
                'nearest_resistance_distance': 0.05,  # 5%上昇を想定
                'resistance_strength': 0.5,
                'breakout_probability': 0.3,
                'profit_potential': 0.05
            }
        
        # 最も近いレジスタンスレベルを特定
        nearest_resistances = [r for r in resistance_levels if r.price > current_price]
        nearest_resistances.sort(key=lambda x: abs(x.price - current_price))
        
        if not nearest_resistances:
            reasoning.append("⚠️ 現在価格上方にレジスタンスレベルがありません")
            return {
                'nearest_resistance_distance': 0.10,  # 10%上昇を想定
                'resistance_strength': 0.5,
                'breakout_probability': 0.5,
                'profit_potential': 0.10
            }
        
        # 最も近いレジスタンス
        nearest_resistance = nearest_resistances[0]
        resistance_distance_pct = (nearest_resistance.price - current_price) / current_price
        
        reasoning.append(f"🎯 最近レジスタンス: {nearest_resistance.price:.4f} ({resistance_distance_pct*100:.1f}%上)")
        
        # ブレイクアウト確率を予測から取得
        breakout_probability = 0.3  # デフォルト
        for prediction in breakout_predictions:
            if prediction.level.price == nearest_resistance.price:
                breakout_probability = prediction.breakout_probability
                reasoning.append(f"🚀 ブレイクアウト確率: {breakout_probability*100:.1f}%")
                break
        
        # 次のレジスタンスレベルまでの利益ポテンシャル
        if len(nearest_resistances) > 1:
            next_resistance = nearest_resistances[1]
            extended_profit_pct = (next_resistance.price - current_price) / current_price
            reasoning.append(f"📈 次のレジスタンス: {next_resistance.price:.4f} ({extended_profit_pct*100:.1f}%上)")
        else:
            extended_profit_pct = resistance_distance_pct * 1.5  # 推定
        
        # 期待利益の計算
        immediate_profit = resistance_distance_pct * (1 - nearest_resistance.strength)
        extended_profit = extended_profit_pct * breakout_probability
        total_profit_potential = max(0.01, immediate_profit + extended_profit)  # 最低1%は確保
        
        reasoning.append(f"💰 利益ポテンシャル: {total_profit_potential*100:.1f}%")
        
        return {
            'nearest_resistance_distance': resistance_distance_pct,
            'resistance_strength': nearest_resistance.strength,
            'breakout_probability': breakout_probability,
            'immediate_profit_potential': immediate_profit,
            'extended_profit_potential': extended_profit,
            'total_profit_potential': total_profit_potential
        }
    
    def _analyze_btc_correlation_risk(self, btc_correlation_risk: BTCCorrelationRisk,
                                    reasoning: List[str]) -> Dict:
        """
        BTC相関リスク分析
        
        memo要素:
        - BTC暴落が起きた場合どれくらい値下がる可能性があるのか
        - 対象トークンの過去の似た事例から判断
        """
        
        if not btc_correlation_risk:
            reasoning.append("⚠️ BTC相関分析データがありません")
            return {
                'correlation_strength': 0.8,  # 一般的な相関を想定
                'max_correlation_downside': 0.15,
                'correlation_risk_factor': 0.3
            }
        
        correlation_strength = btc_correlation_risk.correlation_strength
        risk_level = btc_correlation_risk.risk_level
        
        reasoning.append(f"₿ BTC相関強度: {correlation_strength:.2f}")
        reasoning.append(f"⚠️ BTC相関リスクレベル: {risk_level}")
        
        # 最大予想下落幅を計算
        max_predicted_drop = 0
        if btc_correlation_risk.predicted_altcoin_drop:
            max_predicted_drop = abs(min(btc_correlation_risk.predicted_altcoin_drop.values())) / 100
            reasoning.append(f"📉 BTC暴落時最大予想下落: {max_predicted_drop*100:.1f}%")
        
        # リスクレベルに基づく調整係数
        risk_factor_map = {
            'LOW': 0.1,
            'MEDIUM': 0.3,
            'HIGH': 0.6,
            'CRITICAL': 0.9
        }
        
        correlation_risk_factor = risk_factor_map.get(risk_level, 0.3)
        
        return {
            'correlation_strength': correlation_strength,
            'max_correlation_downside': max_predicted_drop,
            'correlation_risk_factor': correlation_risk_factor,
            'risk_level': risk_level
        }
    
    def _analyze_market_context(self, market_context: MarketContext, reasoning: List[str]) -> float:
        """
        市場コンテキスト分析
        
        memo要素:
        - 異常検知(市場の)
        - ボラティリティ
        """
        
        volatility = market_context.volatility
        trend_direction = market_context.trend_direction
        market_phase = market_context.market_phase
        
        reasoning.append(f"📊 市場トレンド: {trend_direction}")
        reasoning.append(f"🔄 市場フェーズ: {market_phase}")
        reasoning.append(f"📈 ボラティリティ: {volatility:.3f}")
        
        # トレンド方向によるリスク調整
        trend_risk_factor = {
            'BULLISH': 0.8,   # 上昇トレンドはリスク低
            'SIDEWAYS': 1.0,  # 横ばいは標準
            'BEARISH': 1.3    # 下降トレンドはリスク高
        }.get(trend_direction, 1.0)
        
        # 市場フェーズによるリスク調整
        phase_risk_factor = {
            'ACCUMULATION': 0.9,  # 蓄積期は比較的安全
            'MARKUP': 1.0,        # 上昇期は標準
            'DISTRIBUTION': 1.2,  # 分散期はリスク高
            'MARKDOWN': 1.4       # 下落期は高リスク
        }.get(market_phase, 1.0)
        
        # ボラティリティによるリスク調整（高ボラはリスク高）
        volatility_risk_factor = 1.0 + min(volatility * 2, 1.0)
        
        # 総合リスクファクター
        total_risk_factor = trend_risk_factor * phase_risk_factor * volatility_risk_factor
        
        if total_risk_factor > 1.5:
            reasoning.append("⚠️ 高リスク市場環境が検出されました")
        elif total_risk_factor < 0.9:
            reasoning.append("✅ 低リスク市場環境です")
        
        return total_risk_factor
    
    def _calculate_final_leverage(self, downside_analysis: Dict, upside_analysis: Dict,
                                btc_risk_analysis: Dict, market_risk_factor: float,
                                current_price: float, reasoning: List[str],
                                market_context: MarketContext) -> Dict:
        """
        最終レバレッジ計算
        
        全ての分析結果を統合して最適なレバレッジを決定
        """
        
        # === 各要素からの制約レバレッジ ===
        
        # 1. サポートレベルからの制約
        support_max_leverage = downside_analysis['max_leverage_from_support']
        
        # 2. リスクリワード比からの制約
        profit_potential = upside_analysis['total_profit_potential']
        downside_risk = downside_analysis['nearest_support_distance']
        
        # 実際の市場データに基づく最小値を使用（ハードコード値は避ける）
        if profit_potential <= 0 or downside_risk <= 0:
            # デバッグログ追加
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"🚨 RETURN NONE TRIGGERED! profit_potential={profit_potential}, downside_risk={downside_risk}")
            logger.error(f"   upside_analysis: {upside_analysis}")
            logger.error(f"   downside_analysis: {downside_analysis}")
            logger.error(f"   current_price: {current_price}")
            
            reasoning.append("⚠️ 不正なリスク・リワードデータ - 分析をスキップ")
            return None
        
        risk_reward_ratio = profit_potential / downside_risk
        risk_reward_ratio = max(0.1, min(10.0, risk_reward_ratio))  # 0.1-10に制限
        
        reasoning.append(f"⚖️ リスクリワード比: {risk_reward_ratio:.2f}")
        
        # リスクリワード比が低い場合はレバレッジを制限
        if risk_reward_ratio >= 2.0:
            rr_max_leverage = min(self.max_leverage, risk_reward_ratio * 5)
        elif risk_reward_ratio >= 1.0:
            rr_max_leverage = min(self.max_leverage, risk_reward_ratio * 3)
        else:
            rr_max_leverage = 2.0
        
        # 3. BTC相関リスクからの制約
        btc_max_leverage = self.max_leverage
        if btc_risk_analysis['correlation_risk_factor'] > 0.5:
            btc_max_leverage = min(self.max_leverage, 1 / btc_risk_analysis['max_correlation_downside']) if btc_risk_analysis['max_correlation_downside'] > 0 else 10.0
        
        # 4. 市場リスクファクターによる調整
        market_adjusted_leverage = self.max_leverage / market_risk_factor
        
        # === 最も制限的な要素を採用 ===
        constraint_leverages = [
            support_max_leverage,
            rr_max_leverage, 
            btc_max_leverage,
            market_adjusted_leverage
        ]
        
        max_safe_leverage = min(constraint_leverages)
        
        # === 推奨レバレッジは市場条件に基づく調整 ===
        # 市場の状況に応じて保守的さを調整（固定70%ではなく）
        market_conservatism = 0.5 + (market_context.volatility * 0.3)  # 0.5-0.8の範囲
        market_conservatism = max(0.5, min(0.9, market_conservatism))
        
        recommended_leverage = max_safe_leverage * market_conservatism
        
        # === 最小・最大制限の適用 ===
        recommended_leverage = max(1.0, min(recommended_leverage, self.max_leverage))
        max_safe_leverage = max(1.0, min(max_safe_leverage, self.max_leverage))
        
        # === 信頼度計算 ===
        confidence_factors = [
            downside_analysis['support_strength'],
            upside_analysis['breakout_probability'],
            1.0 - btc_risk_analysis['correlation_risk_factor'],
            1.0 / market_risk_factor if market_risk_factor > 0 else 0.5
        ]
        
        # デバッグログ: 信頼度要素の値を確認
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"🔍 信頼度要素デバッグ:")
        logger.error(f"   support_strength: {downside_analysis.get('support_strength', 'N/A')}")
        logger.error(f"   breakout_probability: {upside_analysis.get('breakout_probability', 'N/A')}")
        logger.error(f"   btc_correlation_risk_factor: {btc_risk_analysis.get('correlation_risk_factor', 'N/A')}")
        logger.error(f"   market_risk_factor: {market_risk_factor}")
        logger.error(f"   confidence_factors: {confidence_factors}")
        
        # 各要素を0-1に正規化
        normalized_factors = [max(0.0, min(1.0, factor)) for factor in confidence_factors]
        confidence = np.mean(normalized_factors)
        confidence = max(0.0, min(1.0, confidence))  # 0-1に制限
        
        reasoning.append(f"🎯 推奨レバレッジ: {recommended_leverage:.1f}x")
        reasoning.append(f"🛡️ 最大安全レバレッジ: {max_safe_leverage:.1f}x")
        reasoning.append(f"🎪 信頼度: {confidence*100:.1f}%")
        
        return {
            'recommended_leverage': recommended_leverage,
            'max_safe_leverage': max_safe_leverage,
            'risk_reward_ratio': risk_reward_ratio,
            'confidence': confidence
        }
    
    def _calculate_stop_loss_take_profit(self, current_price: float,
                                       downside_analysis: Dict, upside_analysis: Dict,
                                       leverage: float) -> tuple:
        """
        損切り・利確ライン計算
        
        memo要素:
        - 損切りライン: 適切な損切り位置の設定
        """
        
        # 損切りライン: 最近サポートレベルの少し下
        support_distance = downside_analysis['nearest_support_distance']
        support_strength = min(1.0, downside_analysis['support_strength'])  # 1.0に制限
        
        # サポート強度が低い場合はより早めに損切り
        stop_loss_buffer = 0.02 * (1.2 - support_strength)  # 強度に応じて調整
        stop_loss_distance = support_distance + stop_loss_buffer
        
        # レバレッジを考慮した損切り（資金の10%を上限）
        max_loss_pct = 0.10 / leverage
        stop_loss_distance = min(stop_loss_distance, max_loss_pct)
        
        # 損切りラインが現在価格より下になるよう確保（ロングポジション用）
        stop_loss_distance = max(0.01, min(0.15, stop_loss_distance))  # 1%-15%の範囲に制限
        stop_loss_price = current_price * (1 - stop_loss_distance)
        
        # 利確ライン: 最近レジスタンスレベル付近
        resistance_distance = upside_analysis['nearest_resistance_distance']
        breakout_probability = upside_analysis['breakout_probability']
        
        # ブレイクアウト確率が高い場合は少し上まで狙う
        if breakout_probability > 0.6:
            take_profit_distance = resistance_distance * 1.1
        else:
            take_profit_distance = resistance_distance * 0.9
        
        take_profit_price = current_price * (1 + take_profit_distance)
        
        return stop_loss_price, take_profit_price
    
    def calculate_risk_reward(self, entry_price: float, stop_loss: float, take_profit: float) -> float:
        """リスクリワード比を計算"""
        
        if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
            return 0.0
        
        risk = abs(entry_price - stop_loss) / entry_price
        reward = abs(take_profit - entry_price) / entry_price
        
        if risk == 0:
            return 0.0
        
        return reward / risk
    
    def set_stop_loss_take_profit_calculator(self, calculator: IStopLossTakeProfitCalculator):
        """損切り・利確計算器を設定"""
        self.sl_tp_calculator = calculator

class SimpleMarketContextAnalyzer(IMarketContextAnalyzer):
    """シンプルな市場コンテキスト分析器"""
    
    def analyze_market_phase(self, data: pd.DataFrame, target_timestamp: datetime = None, is_realtime: bool = True) -> MarketContext:
        """市場フェーズを分析
        
        Args:
            data: OHLCVデータ
            target_timestamp: 分析対象の時刻（バックテストの場合必須）
            is_realtime: リアルタイム分析かどうかのフラグ
        """
        try:
            if data.empty:
                current_price = 1000.0
                volume_24h = 1000000.0
                volatility = 0.02
            else:
                # リアルタイム分析の場合
                if is_realtime:
                    # リアルタイムでは現在価格を使用
                    # TODO: 実際のAPIから現在価格を取得する実装が必要
                    # 現在は最新のclose価格を代用
                    current_price = float(data['close'].iloc[-1])
                    # 将来的には: current_price = self._fetch_realtime_price(symbol)
                    
                # バックテストの場合
                else:
                    # target_timestampが必須
                    if target_timestamp is None:
                        raise ValueError(
                            "バックテスト分析ではtarget_timestampが必須です。"
                            "is_realtime=Falseの場合は必ずtarget_timestampを指定してください。"
                        )
                    
                    # timestampカラムの確認・作成
                    if 'timestamp' not in data.columns:
                        if pd.api.types.is_datetime64_any_dtype(data.index):
                            data = data.reset_index()
                            if 'index' in data.columns:
                                data = data.rename(columns={'index': 'timestamp'})
                        else:
                            raise ValueError(
                                "バックテスト分析ではデータにtimestampカラムが必要です。"
                            )
                    
                    # タイムスタンプをdatetime型に変換
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                    
                    # 該当時刻のローソク足を探す
                    time_diff = abs(data['timestamp'] - target_timestamp)
                    nearest_idx = time_diff.idxmin()
                    
                    # 該当ローソク足のopen価格を使用（エントリー時の実際の価格）
                    current_price = float(data.loc[nearest_idx, 'open'])
                
                volume_24h = float(data['volume'].tail(24).sum()) if len(data) >= 24 else float(data['volume'].sum())
                returns = data['close'].pct_change().dropna()
                volatility = float(returns.std()) if len(returns) > 1 else 0.02
            
            # 簡易トレンド判定
            if len(data) >= 20:
                sma_20 = data['close'].rolling(20).mean().iloc[-1]
                if current_price > sma_20 * 1.02:
                    trend = 'BULLISH'
                elif current_price < sma_20 * 0.98:
                    trend = 'BEARISH'
                else:
                    trend = 'SIDEWAYS'
            else:
                trend = 'SIDEWAYS'
            
            # 簡易フェーズ判定
            if volatility < 0.01:
                phase = 'ACCUMULATION'
            elif volatility < 0.03:
                phase = 'MARKUP' if trend == 'BULLISH' else 'MARKDOWN'
            else:
                phase = 'DISTRIBUTION'
            
            return MarketContext(
                current_price=current_price,
                volume_24h=volume_24h,
                volatility=volatility,
                trend_direction=trend,
                market_phase=phase,
                timestamp=datetime.now()
            )
            
        except ValueError as e:
            # ValueErrorは再スロー（タイムスタンプ関連のエラー）
            raise
        except Exception as e:
            print(f"市場コンテキスト分析エラー: {e}")
            return MarketContext(
                current_price=1000.0,
                volume_24h=1000000.0,
                volatility=0.02,
                trend_direction='SIDEWAYS',
                market_phase='ACCUMULATION',
                timestamp=datetime.now()
            )
    
    def detect_anomalies(self, data: pd.DataFrame) -> List[Dict]:
        """市場異常を検知（簡易版）"""
        anomalies = []
        
        try:
            if len(data) < 20:
                return anomalies
            
            # 価格変動の異常検知
            returns = data['close'].pct_change().dropna()
            threshold = returns.std() * 3
            
            recent_return = returns.iloc[-1] if len(returns) > 0 else 0
            if abs(recent_return) > threshold:
                anomalies.append({
                    'type': 'price_spike',
                    'severity': 'HIGH' if abs(recent_return) > threshold * 1.5 else 'MEDIUM',
                    'description': f'異常な価格変動: {recent_return*100:.2f}%'
                })
            
            # 出来高の異常検知
            volume_ma = data['volume'].rolling(20).mean().iloc[-1]
            current_volume = data['volume'].iloc[-1]
            
            if current_volume > volume_ma * 3:
                anomalies.append({
                    'type': 'volume_spike',
                    'severity': 'MEDIUM',
                    'description': f'異常な出来高増加: {current_volume/volume_ma:.1f}倍'
                })
            
        except Exception as e:
            print(f"異常検知エラー: {e}")
        
        return anomalies