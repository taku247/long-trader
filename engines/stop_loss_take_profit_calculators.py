"""
損切り・利確価格計算プラグイン

プラグイン化可能な損切り・利確価格計算ロジックを提供。
異なる戦略（保守的、積極的、バランス型）を実装。
"""

import sys
import os
from typing import List
import numpy as np


class CriticalAnalysisError(Exception):
    """重要な分析データが不足している場合の例外"""
    pass

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interfaces import (
    IStopLossTakeProfitCalculator, SupportResistanceLevel, 
    MarketContext, StopLossTakeProfitLevels
)


class DefaultSLTPCalculator(IStopLossTakeProfitCalculator):
    """
    デフォルト損切り・利確計算器
    
    既存のロジックを移植した標準的な計算方法
    """
    
    def __init__(self):
        self.name = "Default"
        self.max_loss_pct_base = 0.10  # 資金の10%を上限
        self.min_stop_loss_distance = 0.01  # 1%
        self.max_stop_loss_distance = 0.15  # 15%
    
    def calculate_levels(self,
                        current_price: float,
                        leverage: float,
                        support_levels: List[SupportResistanceLevel],
                        resistance_levels: List[SupportResistanceLevel],
                        market_context: MarketContext,
                        position_direction: str = "long") -> StopLossTakeProfitLevels:
        """既存ロジックベースの損切り・利確計算"""
        
        reasoning = []
        
        # === 損切りライン計算 ===
        stop_loss_price = self._calculate_stop_loss(
            current_price, leverage, support_levels, market_context, reasoning
        )
        
        # === 利確ライン計算 ===
        take_profit_price = self._calculate_take_profit(
            current_price, resistance_levels, market_context, reasoning
        )
        
        # === リスクリワード比計算 ===
        stop_loss_distance_pct = abs(current_price - stop_loss_price) / current_price
        take_profit_distance_pct = abs(take_profit_price - current_price) / current_price
        
        if stop_loss_distance_pct > 0:
            risk_reward_ratio = take_profit_distance_pct / stop_loss_distance_pct
        else:
            risk_reward_ratio = 1.0
        
        return StopLossTakeProfitLevels(
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_reward_ratio=risk_reward_ratio,
            stop_loss_distance_pct=stop_loss_distance_pct,
            take_profit_distance_pct=take_profit_distance_pct,
            calculation_method=self.name,
            confidence_level=0.7,
            reasoning=reasoning
        )
    
    def _calculate_stop_loss(self, current_price: float, leverage: float,
                           support_levels: List[SupportResistanceLevel],
                           market_context: MarketContext, reasoning: List[str]) -> float:
        """損切りライン計算（既存ロジック移植）"""
        
        if not support_levels:
            # Level 1 厳格検証: サポートレベルが必須
            raise CriticalAnalysisError("支持線データが不足しています。適切な損切りラインを計算できません。")
        else:
            # 最も近いサポートレベルを基準
            nearest_supports = [s for s in support_levels if s.price < current_price]
            if nearest_supports:
                nearest_support = min(nearest_supports, key=lambda x: abs(x.price - current_price))
                support_distance = (current_price - nearest_support.price) / current_price
                support_strength = nearest_support.strength
                
                # サポート強度が低い場合はより早めに損切り
                stop_loss_buffer = 0.02 * (1.2 - support_strength)
                stop_loss_distance = support_distance + stop_loss_buffer
                
                reasoning.append(f"📍 最近サポート: {nearest_support.price:.4f} ({support_distance*100:.1f}%下)")
                reasoning.append(f"💪 サポート強度: {support_strength:.2f}")
            else:
                # Level 1 厳格検証: 下方サポートが必須
                raise CriticalAnalysisError("現在価格より下の支持線データが不足しています。適切な損切りラインを計算できません。")
        
        # レバレッジを考慮した損切り（資金の10%を上限）
        max_loss_pct = self.max_loss_pct_base / leverage
        stop_loss_distance = min(stop_loss_distance, max_loss_pct)
        
        # 制限の適用
        stop_loss_distance = max(self.min_stop_loss_distance, 
                               min(self.max_stop_loss_distance, stop_loss_distance))
        
        stop_loss_price = current_price * (1 - stop_loss_distance)
        
        reasoning.append(f"🛑 損切り: {stop_loss_price:.4f} ({stop_loss_distance*100:.1f}%下)")
        
        return stop_loss_price
    
    def _calculate_take_profit(self, current_price: float,
                             resistance_levels: List[SupportResistanceLevel],
                             market_context: MarketContext, reasoning: List[str]) -> float:
        """利確ライン計算（既存ロジック移植）"""
        
        if not resistance_levels:
            # Level 1 厳格検証: レジスタンスレベルが必須
            raise CriticalAnalysisError("抵抗線データが不足しています。適切な利確ラインを計算できません。")
        else:
            # 最も近いレジスタンスレベルを基準
            nearest_resistances = [r for r in resistance_levels if r.price > current_price]
            if nearest_resistances:
                nearest_resistance = min(nearest_resistances, key=lambda x: abs(x.price - current_price))
                resistance_distance = (nearest_resistance.price - current_price) / current_price
                
                # ブレイクアウトの可能性を簡易判定
                # ボラティリティが高い場合は突破可能性あり
                volatility = market_context.volatility
                if volatility > 0.03:  # 高ボラティリティ
                    take_profit_distance = resistance_distance * 1.1  # レジスタンス少し上
                    reasoning.append(f"🚀 高ボラ環境: レジスタンス突破狙い")
                else:
                    take_profit_distance = resistance_distance * 0.9  # レジスタンス手前
                    reasoning.append(f"📈 通常環境: レジスタンス手前で利確")
                
                reasoning.append(f"🎯 最近レジスタンス: {nearest_resistance.price:.4f} ({resistance_distance*100:.1f}%上)")
            else:
                # Level 1 厳格検証: 上方レジスタンスが必須
                raise CriticalAnalysisError("現在価格より上の抵抗線データが不足しています。適切な利確ラインを計算できません。")
        
        take_profit_price = current_price * (1 + take_profit_distance)
        
        reasoning.append(f"💰 利確: {take_profit_price:.4f} ({take_profit_distance*100:.1f}%上)")
        
        return take_profit_price


class ConservativeSLTPCalculator(IStopLossTakeProfitCalculator):
    """
    保守的損切り・利確計算器
    
    リスクを最小化する保守的なアプローチ
    """
    
    def __init__(self):
        self.name = "Conservative"
        self.max_loss_pct_base = 0.05  # 資金の5%を上限（より保守的）
        self.min_stop_loss_distance = 0.015  # 1.5%
        self.max_stop_loss_distance = 0.08  # 8%（タイトな損切り）
        self.conservative_take_profit_ratio = 0.7  # レジスタンスの70%で利確
    
    def calculate_levels(self,
                        current_price: float,
                        leverage: float,
                        support_levels: List[SupportResistanceLevel],
                        resistance_levels: List[SupportResistanceLevel],
                        market_context: MarketContext,
                        position_direction: str = "long") -> StopLossTakeProfitLevels:
        """保守的な損切り・利確計算"""
        
        reasoning = ["🛡️ 保守的戦略を適用"]
        
        # === タイトな損切り ===
        stop_loss_price = self._calculate_conservative_stop_loss(
            current_price, leverage, support_levels, market_context, reasoning
        )
        
        # === 早めの利確 ===
        take_profit_price = self._calculate_conservative_take_profit(
            current_price, resistance_levels, market_context, reasoning
        )
        
        # === リスクリワード比計算 ===
        stop_loss_distance_pct = abs(current_price - stop_loss_price) / current_price
        take_profit_distance_pct = abs(take_profit_price - current_price) / current_price
        
        risk_reward_ratio = take_profit_distance_pct / stop_loss_distance_pct if stop_loss_distance_pct > 0 else 1.0
        
        return StopLossTakeProfitLevels(
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_reward_ratio=risk_reward_ratio,
            stop_loss_distance_pct=stop_loss_distance_pct,
            take_profit_distance_pct=take_profit_distance_pct,
            calculation_method=self.name,
            confidence_level=0.9,  # 保守的戦略は高信頼度
            reasoning=reasoning
        )
    
    def _calculate_conservative_stop_loss(self, current_price: float, leverage: float,
                                        support_levels: List[SupportResistanceLevel],
                                        market_context: MarketContext, reasoning: List[str]) -> float:
        """保守的損切り計算"""
        
        # 基本的に近いサポートよりもタイトに設定
        if support_levels:
            nearest_supports = [s for s in support_levels if s.price < current_price]
            if nearest_supports:
                nearest_support = min(nearest_supports, key=lambda x: abs(x.price - current_price))
                support_distance = (current_price - nearest_support.price) / current_price
                
                # サポートよりもかなり手前で損切り（50%の距離）
                stop_loss_distance = support_distance * 0.5
                reasoning.append(f"🛡️ サポート手前早期損切り: {support_distance*100:.1f}% → {stop_loss_distance*100:.1f}%")
            else:
                stop_loss_distance = 0.03  # 3%
                # Level 1 厳格検証: 下方サポートが必須
                raise CriticalAnalysisError("現在価格より下の支持線データが不足しています。保守的戦略での適切な損切りラインを計算できません。")
        else:
            # Level 1 厳格検証: サポートデータが必須
            raise CriticalAnalysisError("支持線データが不足しています。保守的戦略での適切な損切りラインを計算できません。")
        
        # レバレッジ考慮（より保守的）
        max_loss_pct = self.max_loss_pct_base / leverage
        stop_loss_distance = min(stop_loss_distance, max_loss_pct)
        
        # 制限の適用
        stop_loss_distance = max(self.min_stop_loss_distance, 
                               min(self.max_stop_loss_distance, stop_loss_distance))
        
        return current_price * (1 - stop_loss_distance)
    
    def _calculate_conservative_take_profit(self, current_price: float,
                                          resistance_levels: List[SupportResistanceLevel],
                                          market_context: MarketContext, reasoning: List[str]) -> float:
        """保守的利確計算"""
        
        if resistance_levels:
            nearest_resistances = [r for r in resistance_levels if r.price > current_price]
            if nearest_resistances:
                nearest_resistance = min(nearest_resistances, key=lambda x: abs(x.price - current_price))
                resistance_distance = (nearest_resistance.price - current_price) / current_price
                
                # レジスタンスの70%地点で確実に利確
                take_profit_distance = resistance_distance * self.conservative_take_profit_ratio
                reasoning.append(f"🛡️ レジスタンス手前確実利確: {resistance_distance*100:.1f}% → {take_profit_distance*100:.1f}%")
            else:
                take_profit_distance = 0.05  # 5%
                # Level 1 厳格検証: 上方レジスタンスが必須
                raise CriticalAnalysisError("現在価格より上の抵抗線データが不足しています。保守的戦略での適切な利確ラインを計算できません。")
        else:
            # Level 1 厳格検証: レジスタンスデータが必須
            raise CriticalAnalysisError("抵抗線データが不足しています。保守的戦略での適切な利確ラインを計算できません。")
        
        return current_price * (1 + take_profit_distance)


class AggressiveSLTPCalculator(IStopLossTakeProfitCalculator):
    """
    積極的損切り・利確計算器
    
    高リスク・高リターンを狙う積極的なアプローチ
    """
    
    def __init__(self):
        self.name = "Aggressive"
        self.max_loss_pct_base = 0.20  # 資金の20%まで許容（より積極的）
        self.min_stop_loss_distance = 0.005  # 0.5%
        self.max_stop_loss_distance = 0.25  # 25%（ワイドな損切り）
        self.aggressive_take_profit_ratio = 1.3  # レジスタンス130%で利確
    
    def calculate_levels(self,
                        current_price: float,
                        leverage: float,
                        support_levels: List[SupportResistanceLevel],
                        resistance_levels: List[SupportResistanceLevel],
                        market_context: MarketContext,
                        position_direction: str = "long") -> StopLossTakeProfitLevels:
        """積極的な損切り・利確計算"""
        
        reasoning = ["🚀 積極的戦略を適用"]
        
        # === ワイドな損切り ===
        stop_loss_price = self._calculate_aggressive_stop_loss(
            current_price, leverage, support_levels, market_context, reasoning
        )
        
        # === ブレイクアウト狙いの利確 ===
        take_profit_price = self._calculate_aggressive_take_profit(
            current_price, resistance_levels, market_context, reasoning
        )
        
        # === リスクリワード比計算 ===
        stop_loss_distance_pct = abs(current_price - stop_loss_price) / current_price
        take_profit_distance_pct = abs(take_profit_price - current_price) / current_price
        
        risk_reward_ratio = take_profit_distance_pct / stop_loss_distance_pct if stop_loss_distance_pct > 0 else 1.0
        
        return StopLossTakeProfitLevels(
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_reward_ratio=risk_reward_ratio,
            stop_loss_distance_pct=stop_loss_distance_pct,
            take_profit_distance_pct=take_profit_distance_pct,
            calculation_method=self.name,
            confidence_level=0.5,  # 積極的戦略は中程度の信頼度
            reasoning=reasoning
        )
    
    def _calculate_aggressive_stop_loss(self, current_price: float, leverage: float,
                                      support_levels: List[SupportResistanceLevel],
                                      market_context: MarketContext, reasoning: List[str]) -> float:
        """積極的損切り計算"""
        
        # 強いサポートを見つけてそのさらに下に設定
        if support_levels:
            # 強度でソートして最も強いサポートを選択
            strong_supports = [s for s in support_levels if s.price < current_price and s.strength > 0.6]
            if strong_supports:
                strongest_support = max(strong_supports, key=lambda x: x.strength)
                support_distance = (current_price - strongest_support.price) / current_price
                
                # 強いサポートの更に下（バッファを追加）
                stop_loss_distance = support_distance + 0.03  # 3%バッファ
                reasoning.append(f"🚀 強サポート下抜け想定: {strongest_support.price:.4f} (強度{strongest_support.strength:.2f})")
            else:
                # 強いサポートがない場合は最近サポートの下
                nearest_supports = [s for s in support_levels if s.price < current_price]
                if nearest_supports:
                    nearest_support = min(nearest_supports, key=lambda x: abs(x.price - current_price))
                    support_distance = (current_price - nearest_support.price) / current_price
                    stop_loss_distance = support_distance + 0.05  # 5%バッファ
                    reasoning.append(f"🚀 サポート下抜け想定: {nearest_support.price:.4f}")
                else:
                    stop_loss_distance = 0.10  # 10%
                    # Level 1 厳格検証: 下方サポートが必須
                    raise CriticalAnalysisError("現在価格より下の支持線データが不足しています。積極的戦略での適切な損切りラインを計算できません。")
        else:
            # Level 1 厳格検証: サポートデータが必須
            raise CriticalAnalysisError("支持線データが不足しています。積極的戦略での適切な損切りラインを計算できません。")
        
        # レバレッジ考慮（積極的）
        max_loss_pct = self.max_loss_pct_base / leverage
        stop_loss_distance = min(stop_loss_distance, max_loss_pct)
        
        # 制限の適用
        stop_loss_distance = max(self.min_stop_loss_distance, 
                               min(self.max_stop_loss_distance, stop_loss_distance))
        
        return current_price * (1 - stop_loss_distance)
    
    def _calculate_aggressive_take_profit(self, current_price: float,
                                        resistance_levels: List[SupportResistanceLevel],
                                        market_context: MarketContext, reasoning: List[str]) -> float:
        """積極的利確計算"""
        
        if resistance_levels:
            # 複数のレジスタンスを考慮してブレイクアウト先を狙う
            nearest_resistances = sorted(
                [r for r in resistance_levels if r.price > current_price],
                key=lambda x: x.price
            )
            
            if len(nearest_resistances) >= 2:
                # 2つ目のレジスタンスを突破することを狙う
                second_resistance = nearest_resistances[1]
                resistance_distance = (second_resistance.price - current_price) / current_price
                take_profit_distance = resistance_distance
                reasoning.append(f"🚀 2段階ブレイクアウト狙い: {second_resistance.price:.4f}")
            elif len(nearest_resistances) == 1:
                # 1つ目のレジスタンスを大きく突破することを狙う
                first_resistance = nearest_resistances[0]
                resistance_distance = (first_resistance.price - current_price) / current_price
                take_profit_distance = resistance_distance * self.aggressive_take_profit_ratio
                reasoning.append(f"🚀 大幅ブレイクアウト狙い: {first_resistance.price:.4f} x{self.aggressive_take_profit_ratio}")
            else:
                take_profit_distance = 0.15  # 15%
                # Level 1 厳格検証: 上方レジスタンスが必須
                raise CriticalAnalysisError("現在価格より上の抵抗線データが不足しています。積極的戦略での適切な利確ラインを計算できません。")
        else:
            # Level 1 厳格検証: レジスタンスデータが必須
            raise CriticalAnalysisError("抵抗線データが不足しています。積極的戦略での適切な利確ラインを計算できません。")
        
        # ボラティリティが高い場合はさらに上を狙う
        if market_context.volatility > 0.05:
            take_profit_distance *= 1.2
            reasoning.append(f"🚀 高ボラ環境: 利確目標を20%拡張")
        
        return current_price * (1 + take_profit_distance)


class TraditionalSLTPCalculator(IStopLossTakeProfitCalculator):
    """
    従来型損切り・利確計算器
    
    技術指標ベースの従来手法による損切り・利確計算
    Aggressive_Traditional戦略で使用
    """
    
    def __init__(self):
        self.name = "Traditional"
        self.max_loss_pct_base = 0.12  # 12%を上限（積極的）
        self.min_stop_loss_distance = 0.015  # 1.5%
        self.max_stop_loss_distance = 0.20  # 20%（より広い）
    
    def calculate_levels(self,
                        current_price: float,
                        leverage: float,
                        support_levels: List[SupportResistanceLevel],
                        resistance_levels: List[SupportResistanceLevel],
                        market_context: MarketContext,
                        position_direction: str = "long") -> StopLossTakeProfitLevels:
        """従来型手法による損切り・利確計算"""
        
        reasoning = []
        
        # 従来型（技術指標重視）の損切り計算
        stop_loss_price = self._calculate_traditional_stop_loss(
            current_price, leverage, support_levels, market_context, reasoning
        )
        
        # 従来型の利確計算（より積極的）
        take_profit_price = self._calculate_traditional_take_profit(
            current_price, resistance_levels, market_context, reasoning
        )
        
        # 距離計算
        stop_loss_distance_pct = abs(current_price - stop_loss_price) / current_price
        take_profit_distance_pct = abs(take_profit_price - current_price) / current_price
        
        # リスクリワード比率
        risk_reward_ratio = take_profit_distance_pct / stop_loss_distance_pct if stop_loss_distance_pct > 0 else 0
        
        reasoning.append(f"🎯 従来型R/R比率: {risk_reward_ratio:.2f}")
        
        return StopLossTakeProfitLevels(
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_reward_ratio=risk_reward_ratio,
            stop_loss_distance_pct=stop_loss_distance_pct,
            take_profit_distance_pct=take_profit_distance_pct,
            calculation_method=self.name,
            confidence_level=0.7,  # 従来型は中程度の信頼度
            reasoning=reasoning
        )
    
    def _calculate_traditional_stop_loss(self, current_price: float, leverage: float,
                                       support_levels: List[SupportResistanceLevel],
                                       market_context: MarketContext, reasoning: List[str]) -> float:
        """従来型損切り計算（技術指標重視）"""
        
        # サポートベースの損切り（従来手法）
        if support_levels:
            nearest_supports = [s for s in support_levels if s.price < current_price]
            if nearest_supports:
                nearest_support = min(nearest_supports, key=lambda x: abs(x.price - current_price))
                support_distance = (current_price - nearest_support.price) / current_price
                
                # 従来型はサポートをそのまま使用（より積極的）
                stop_loss_distance = support_distance * 0.9  # サポートの90%位置
                reasoning.append(f"📊 従来型サポートベース: {support_distance*100:.1f}% → {stop_loss_distance*100:.1f}%")
            else:
                stop_loss_distance = 0.05  # 5%（デフォルト）
                reasoning.append(f"📊 従来型デフォルト損切り: {stop_loss_distance*100:.1f}%")
        else:
            stop_loss_distance = 0.04  # 4%
            reasoning.append(f"📊 従来型固定損切り: {stop_loss_distance*100:.1f}%")
        
        # レバレッジ考慮（従来型は緩め）
        max_loss_pct = self.max_loss_pct_base / leverage
        stop_loss_distance = min(stop_loss_distance, max_loss_pct)
        
        # 制限適用
        stop_loss_distance = max(self.min_stop_loss_distance, 
                               min(self.max_stop_loss_distance, stop_loss_distance))
        
        return current_price * (1 - stop_loss_distance)
    
    def _calculate_traditional_take_profit(self, current_price: float,
                                         resistance_levels: List[SupportResistanceLevel],
                                         market_context: MarketContext, reasoning: List[str]) -> float:
        """従来型利確計算（積極的）"""
        
        if resistance_levels:
            nearest_resistances = [r for r in resistance_levels if r.price > current_price]
            if nearest_resistances:
                # 従来型は最初のレジスタンスを積極的に狙う
                target_resistance = min(nearest_resistances, key=lambda x: abs(x.price - current_price))
                resistance_distance = (target_resistance.price - current_price) / current_price
                
                # より積極的（レジスタンスの95%まで）
                take_profit_distance = resistance_distance * 0.95
                reasoning.append(f"🎯 従来型レジスタンス狙い: {resistance_distance*100:.1f}% → {take_profit_distance*100:.1f}%")
            else:
                take_profit_distance = 0.08  # 8%（積極的デフォルト）
                reasoning.append(f"🎯 従来型積極利確: {take_profit_distance*100:.1f}%")
        else:
            take_profit_distance = 0.06  # 6%
            reasoning.append(f"🎯 従来型固定利確: {take_profit_distance*100:.1f}%")
        
        return current_price * (1 + take_profit_distance)


class MLSLTPCalculator(IStopLossTakeProfitCalculator):
    """
    機械学習型損切り・利確計算器
    
    機械学習予測に完全依存した損切り・利確計算
    Full_ML戦略で使用
    """
    
    def __init__(self):
        self.name = "ML"
        self.max_loss_pct_base = 0.15  # 15%を上限（最積極的）
        self.min_stop_loss_distance = 0.02  # 2%
        self.max_stop_loss_distance = 0.25  # 25%（最も広い）
    
    def calculate_levels(self,
                        current_price: float,
                        leverage: float,
                        support_levels: List[SupportResistanceLevel],
                        resistance_levels: List[SupportResistanceLevel],
                        market_context: MarketContext,
                        position_direction: str = "long") -> StopLossTakeProfitLevels:
        """機械学習型損切り・利確計算"""
        
        reasoning = []
        
        # ML予測ベースの損切り計算
        stop_loss_price = self._calculate_ml_stop_loss(
            current_price, leverage, support_levels, market_context, reasoning
        )
        
        # ML予測ベースの利確計算（最積極的）
        take_profit_price = self._calculate_ml_take_profit(
            current_price, resistance_levels, market_context, reasoning
        )
        
        # 距離計算
        stop_loss_distance_pct = abs(current_price - stop_loss_price) / current_price
        take_profit_distance_pct = abs(take_profit_price - current_price) / current_price
        
        # リスクリワード比率
        risk_reward_ratio = take_profit_distance_pct / stop_loss_distance_pct if stop_loss_distance_pct > 0 else 0
        
        reasoning.append(f"🤖 ML予測R/R比率: {risk_reward_ratio:.2f}")
        
        return StopLossTakeProfitLevels(
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_reward_ratio=risk_reward_ratio,
            stop_loss_distance_pct=stop_loss_distance_pct,
            take_profit_distance_pct=take_profit_distance_pct,
            calculation_method=self.name,
            confidence_level=0.85,  # ML戦略は高信頼度
            reasoning=reasoning
        )
    
    def _calculate_ml_stop_loss(self, current_price: float, leverage: float,
                              support_levels: List[SupportResistanceLevel],
                              market_context: MarketContext, reasoning: List[str]) -> float:
        """ML予測ベース損切り計算"""
        
        # ML予測を模擬（実際にはMLモデルから予測値を取得）
        if support_levels:
            nearest_supports = [s for s in support_levels if s.price < current_price]
            if nearest_supports:
                # ML予測: サポート強度を重み付け
                weighted_support = min(nearest_supports, key=lambda x: abs(x.price - current_price))
                support_distance = (current_price - weighted_support.price) / current_price
                
                # ML予測による動的調整（サポート強度に応じて）
                strength_multiplier = min(weighted_support.strength, 1.0) if hasattr(weighted_support, 'strength') else 0.8
                stop_loss_distance = support_distance * (1.2 - strength_multiplier * 0.4)  # 0.8-1.2の範囲
                
                reasoning.append(f"🤖 ML動的損切り: 強度{strength_multiplier:.2f} → {stop_loss_distance*100:.1f}%")
            else:
                stop_loss_distance = 0.06  # 6%（ML推奨）
                reasoning.append(f"🤖 ML推奨損切り: {stop_loss_distance*100:.1f}%")
        else:
            stop_loss_distance = 0.05  # 5%
            reasoning.append(f"🤖 MLデフォルト損切り: {stop_loss_distance*100:.1f}%")
        
        # レバレッジ考慮（MLは最も柔軟）
        max_loss_pct = self.max_loss_pct_base / leverage
        stop_loss_distance = min(stop_loss_distance, max_loss_pct)
        
        # 制限適用
        stop_loss_distance = max(self.min_stop_loss_distance, 
                               min(self.max_stop_loss_distance, stop_loss_distance))
        
        return current_price * (1 - stop_loss_distance)
    
    def _calculate_ml_take_profit(self, current_price: float,
                                resistance_levels: List[SupportResistanceLevel],
                                market_context: MarketContext, reasoning: List[str]) -> float:
        """ML予測ベース利確計算（最積極的）"""
        
        if resistance_levels:
            # ML予測: 複数レジスタンスの動的分析
            resistances_above = [r for r in resistance_levels if r.price > current_price]
            if resistances_above:
                # ML戦略は最も遠いレジスタンスも狙える
                if len(resistances_above) >= 2:
                    # 2番目のレジスタンスを狙う（最積極的）
                    sorted_resistances = sorted(resistances_above, key=lambda x: x.price)
                    target_resistance = sorted_resistances[1]
                    reasoning.append("🤖 ML予測: 第2レジスタンス突破狙い")
                else:
                    target_resistance = resistances_above[0]
                    reasoning.append("🤖 ML予測: 第1レジスタンス突破狙い")
                
                resistance_distance = (target_resistance.price - current_price) / current_price
                
                # ML予測による利確最適化（99%まで積極的に）
                take_profit_distance = resistance_distance * 0.99
                reasoning.append(f"🤖 ML最適利確: {resistance_distance*100:.1f}% → {take_profit_distance*100:.1f}%")
            else:
                take_profit_distance = 0.12  # 12%（最積極的デフォルト）
                reasoning.append(f"🤖 ML積極利確: {take_profit_distance*100:.1f}%")
        else:
            take_profit_distance = 0.10  # 10%
            reasoning.append(f"🤖 ML推奨利確: {take_profit_distance*100:.1f}%")
        
        return current_price * (1 + take_profit_distance)