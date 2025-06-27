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
    """Filter 3: 支持線・抵抗線存在チェック（実装版）"""
    
    def __init__(self):
        super().__init__("support_resistance", "light", 15)
        self._load_config()
    
    def _load_config(self):
        """設定ファイルおよび環境変数からパラメータを読み込み"""
        try:
            import json
            import os
            
            # まず環境変数からフィルターパラメータを確認
            filter_params_env = os.getenv('FILTER_PARAMS')
            if filter_params_env:
                try:
                    filter_params = json.loads(filter_params_env)
                    sr_params = filter_params.get('support_resistance', {})
                    
                    if sr_params:
                        # 環境変数のパラメータを優先使用
                        self.min_support_strength = sr_params.get('min_support_strength', 0.6)
                        self.min_resistance_strength = sr_params.get('min_resistance_strength', 0.6)
                        self.min_touch_count = sr_params.get('min_touch_count', 2)
                        self.max_distance_pct = sr_params.get('max_distance_pct', 0.1)
                        self.tolerance_pct = sr_params.get('tolerance_pct', 0.02)
                        self.fractal_window = sr_params.get('fractal_window', 5)
                        
                        print(f"🔧 フィルターパラメータを環境変数から適用: {sr_params}")
                        return
                except Exception as e:
                    print(f"⚠️ 環境変数のフィルターパラメータ解析エラー: {e}")
            
            # 環境変数がない場合は設定ファイルから読み込み
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                     'config', 'leverage_engine_config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            criteria = config.get('leverage_engine_constants', {}).get('support_resistance_criteria', {})
            self.min_support_strength = criteria.get('min_support_strength', 0.6)
            self.min_resistance_strength = criteria.get('min_resistance_strength', 0.6)
            self.min_touch_count = criteria.get('min_touch_count', 2)
            self.max_distance_pct = criteria.get('max_distance_pct', 0.1)
            
            # support_resistance_config.jsonから追加パラメータ
            sr_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        'config', 'support_resistance_config.json')
            if os.path.exists(sr_config_path):
                with open(sr_config_path, 'r', encoding='utf-8') as f:
                    sr_config = json.load(f)
                
                provider_settings = sr_config.get('provider_settings', {}).get('SupportResistanceVisualizer', {})
                self.tolerance_pct = provider_settings.get('tolerance_pct', 0.02)
                self.fractal_window = provider_settings.get('fractal_window', 5)
            else:
                self.tolerance_pct = 0.02
                self.fractal_window = 5
            
        except Exception as e:
            # デフォルト値を使用
            self.min_support_strength = 0.6
            self.min_resistance_strength = 0.6
            self.min_touch_count = 2
            self.max_distance_pct = 0.1
            self.tolerance_pct = 0.02
            self.fractal_window = 5
    
    def execute(self, prepared_data, strategy, evaluation_time: datetime) -> FilterResult:
        """支持線・抵抗線の存在をチェック（実装版）"""
        self.execution_count += 1
        
        try:
            # SupportResistanceDetectorを使用した実際の検出
            from engines.support_resistance_detector import SupportResistanceDetector
            
            # OHLCVデータと現在価格を取得
            ohlcv_data = prepared_data.get_ohlcv_until(evaluation_time, lookback_periods=200)
            current_price = prepared_data.get_price_at(evaluation_time)
            
            # データフレームに変換
            import pandas as pd
            df = pd.DataFrame(ohlcv_data)
            
            if len(df) < 10:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f"データ不足: {len(df)}本（最低10本必要）",
                    metrics={'data_count': len(df)}
                )
            
            # 支持線・抵抗線検出
            detector = SupportResistanceDetector(
                min_touches=self.min_touch_count,
                tolerance_pct=self.tolerance_pct,
                fractal_window=self.fractal_window
            )
            
            supports, resistances = detector.detect_levels_from_ohlcv(df, current_price)
            
            # 強度基準でフィルタリング
            valid_supports = [s for s in supports if s.strength >= self.min_support_strength]
            valid_resistances = [r for r in resistances if r.strength >= self.min_resistance_strength]
            
            # 通過判定
            has_valid_levels = len(valid_supports) > 0 or len(valid_resistances) > 0
            
            if not has_valid_levels:
                self.failure_count += 1
                return FilterResult(
                    passed=False,
                    reason=f"有効な支持線・抵抗線なし (支持線{len(supports)}→{len(valid_supports)}, 抵抗線{len(resistances)}→{len(valid_resistances)})",
                    metrics={
                        'support_count': len(supports),
                        'resistance_count': len(resistances),
                        'valid_support_count': len(valid_supports),
                        'valid_resistance_count': len(valid_resistances),
                        'min_support_strength': self.min_support_strength,
                        'min_resistance_strength': self.min_resistance_strength
                    }
                )
            
            self.success_count += 1
            return FilterResult(
                passed=True,
                reason=f"支持線・抵抗線チェック合格 (有効支持線{len(valid_supports)}, 有効抵抗線{len(valid_resistances)})",
                metrics={
                    'support_count': len(supports),
                    'resistance_count': len(resistances),
                    'valid_support_count': len(valid_supports),
                    'valid_resistance_count': len(valid_resistances),
                    'strongest_support': max([s.strength for s in valid_supports], default=0),
                    'strongest_resistance': max([r.strength for r in valid_resistances], default=0)
                }
            )
            
        except Exception as e:
            self.failure_count += 1
            return FilterResult(
                passed=False,
                reason=f"支持線・抵抗線チェック中にエラー: {str(e)}",
                metrics={'error': str(e)}
            )