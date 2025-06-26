#!/usr/bin/env python3
"""
フィルタリングシステムの基底クラス

9段階早期フィルタリングシステムの基盤となるクラス群を定義。
TDD アプローチで段階的に実装する。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class FilterResult:
    """フィルター実行結果を格納するクラス"""
    
    def __init__(self, passed: bool, reason: str, metrics: dict = None, timestamp: datetime = None):
        self.passed = passed
        self.reason = reason
        self.metrics = metrics if metrics is not None else {}
        self.timestamp = timestamp if timestamp is not None else datetime.now()
    
    def __repr__(self):
        return f"FilterResult(passed={self.passed}, reason='{self.reason}', timestamp={self.timestamp})"


class BaseFilter(ABC):
    """
    フィルターの基底クラス
    
    全てのフィルターが継承する抽象基底クラス。
    一つの責務に特化したフィルター処理を定義する。
    """
    
    def __init__(self, name: str, weight: str = "medium", max_execution_time: int = 30):
        """
        Args:
            name: フィルター名（識別用）
            weight: 処理重量（"light", "medium", "heavy"）
            max_execution_time: 最大実行時間（秒）
        """
        self.name = name
        self.weight = weight
        self.max_execution_time = max_execution_time
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
    
    @abstractmethod
    def execute(self, prepared_data, strategy, evaluation_time: datetime) -> FilterResult:
        """
        フィルター処理を実行
        
        Args:
            prepared_data: 事前準備された分析データ
            strategy: 実行戦略
            evaluation_time: 評価時点
            
        Returns:
            FilterResult: フィルター実行結果
        """
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """フィルターの実行統計を取得"""
        return {
            'name': self.name,
            'weight': self.weight,
            'execution_count': self.execution_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': self.success_count / self.execution_count if self.execution_count > 0 else 0
        }
    
    def reset_statistics(self):
        """統計をリセット"""
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
    
    def _update_statistics(self, passed: bool, execution_time: float = 0):
        """統計を更新"""
        self.execution_count += 1
        if passed:
            self.success_count += 1
        else:
            self.failure_count += 1


class DataQualityFilter(BaseFilter):
    """Filter 1: データ品質チェック（軽量）"""
    
    def __init__(self):
        super().__init__("data_quality", "light", 5)
    
    def execute(self, prepared_data, strategy, evaluation_time: datetime) -> FilterResult:
        """データ品質をチェック"""
        self.execution_count += 1
        
        try:
            # データ欠損チェック
            if prepared_data.has_missing_data_around(evaluation_time):
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason="データ欠損が検出されました",
                    metrics={'has_missing_data': True}
                )
            
            # 価格異常チェック
            if prepared_data.has_price_anomaly_at(evaluation_time):
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason="価格データに異常が検出されました",
                    metrics={'has_price_anomaly': True}
                )
            
            # データ有効性チェック
            if not prepared_data.is_valid():
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason="データが無効です",
                    metrics={'data_valid': False}
                )
            
            self.success_count += 1
            return FilterResult(
                passed=True,
                reason="データ品質チェック合格",
                metrics={'data_quality_score': 1.0}
            )
            
        except Exception as e:
            self.failure_count += 1
            return FilterResult(
                passed=False,
                reason=f"データ品質チェック中にエラー: {str(e)}",
                metrics={'error': str(e)}
            )


class MarketConditionFilter(BaseFilter):
    """Filter 2: 基本市場条件チェック（軽量）"""
    
    def __init__(self):
        super().__init__("market_condition", "light", 10)
    
    def execute(self, prepared_data, strategy, evaluation_time: datetime) -> FilterResult:
        """基本的な市場条件をチェック"""
        self.execution_count += 1
        
        try:
            # 取引量チェック
            volume = prepared_data.get_volume_at(evaluation_time)
            if volume < strategy.min_volume_threshold:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f"取引量不足: {volume} < {strategy.min_volume_threshold}",
                    metrics={'volume': volume, 'min_required': strategy.min_volume_threshold}
                )
            
            # スプレッドチェック
            spread = prepared_data.get_spread_at(evaluation_time)
            if spread > strategy.max_spread_threshold:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f"スプレッド過大: {spread} > {strategy.max_spread_threshold}",
                    metrics={'spread': spread, 'max_allowed': strategy.max_spread_threshold}
                )
            
            # 流動性スコアチェック
            liquidity_score = prepared_data.get_liquidity_score_at(evaluation_time)
            if liquidity_score < strategy.min_liquidity_score:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f"流動性不足: {liquidity_score} < {strategy.min_liquidity_score}",
                    metrics={'liquidity_score': liquidity_score, 'min_required': strategy.min_liquidity_score}
                )
            
            self.success_count += 1
            return FilterResult(
                passed=True,
                reason="市場条件チェック合格",
                metrics={
                    'volume': volume,
                    'spread': spread,
                    'liquidity_score': liquidity_score
                }
            )
            
        except Exception as e:
            self.failure_count += 1
            return FilterResult(
                passed=False,
                reason=f"市場条件チェック中にエラー: {str(e)}",
                metrics={'error': str(e)}
            )


class SupportResistanceFilter(BaseFilter):
    """Filter 3: 支持線・抵抗線存在チェック（軽量）"""
    
    def __init__(self):
        super().__init__("support_resistance", "light", 15)
    
    def execute(self, prepared_data, strategy, evaluation_time: datetime) -> FilterResult:
        """支持線・抵抗線の存在をチェック"""
        self.execution_count += 1
        
        try:
            # 支持線・抵抗線データを取得（テスト段階では30%の確率で通過）
            # TODO: 実際の支持線・抵抗線検出ロジックと連携
            test_hash = hash(str(evaluation_time))
            has_support_resistance = (test_hash % 10) < 3  # 30%の確率で支持線・抵抗線あり
            
            if not has_support_resistance:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason="有効な支持線・抵抗線が検出されませんでした",
                    metrics={'support_count': 0, 'resistance_count': 0}
                )
            
            # モック支持線・抵抗線データ
            mock_support_count = 2
            mock_resistance_count = 1
            mock_valid_supports = 1
            mock_valid_resistances = 1
            
            self.success_count += 1
            return FilterResult(
                passed=True,
                reason="支持線・抵抗線チェック合格",
                metrics={
                    'support_count': mock_support_count,
                    'resistance_count': mock_resistance_count,
                    'valid_support_count': mock_valid_supports,
                    'valid_resistance_count': mock_valid_resistances
                }
            )
            
        except Exception as e:
            self.failure_count += 1
            return FilterResult(
                passed=False,
                reason=f"支持線・抵抗線チェック中にエラー: {str(e)}",
                metrics={'error': str(e)}
            )