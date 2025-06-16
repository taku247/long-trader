#!/usr/bin/env python3
"""
価格データ整合性チェックシステム

今回発見された価格参照問題 (current_price vs entry_price) を解決するための
統合的な価格検証・統一システム
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PriceInconsistencyLevel(Enum):
    """価格不整合のレベル"""
    NORMAL = "normal"           # 正常範囲（差異 < 1%）
    WARNING = "warning"         # 警告レベル（差異 1-5%）
    ERROR = "error"            # エラーレベル（差異 5-10%）
    CRITICAL = "critical"      # 重大エラー（差異 > 10%）


@dataclass
class PriceConsistencyResult:
    """価格整合性チェック結果"""
    is_consistent: bool
    inconsistency_level: PriceInconsistencyLevel
    price_difference_pct: float
    reference_price: float
    comparison_price: float
    message: str
    timestamp: datetime
    recommendations: List[str]


@dataclass
class UnifiedPriceData:
    """統一価格データ構造"""
    analysis_price: float          # 分析時の価格 (current_price)
    entry_price: float             # エントリー時の実際価格
    market_timestamp: datetime     # 市場データのタイムスタンプ
    analysis_timestamp: datetime   # 分析実行時刻
    symbol: str
    timeframe: str
    data_source: str              # データソース識別
    consistency_score: float      # 整合性スコア (0-1)


class PriceConsistencyValidator:
    """価格データ整合性検証器"""
    
    def __init__(self, warning_threshold_pct: float = 1.0, 
                 error_threshold_pct: float = 5.0,
                 critical_threshold_pct: float = 10.0):
        """
        Args:
            warning_threshold_pct: 警告レベルの閾値（%）
            error_threshold_pct: エラーレベルの閾値（%）
            critical_threshold_pct: 重大エラーレベルの閾値（%）
        """
        self.warning_threshold = warning_threshold_pct
        self.error_threshold = error_threshold_pct
        self.critical_threshold = critical_threshold_pct
        
        # 検証結果の履歴
        self.validation_history = []
    
    def validate_price_consistency(self, 
                                 analysis_price: float, 
                                 entry_price: float,
                                 symbol: str = "",
                                 context: str = "") -> PriceConsistencyResult:
        """
        分析価格とエントリー価格の整合性を検証
        
        Args:
            analysis_price: 分析時の価格 (current_price)
            entry_price: エントリー時の実際価格
            symbol: 銘柄シンボル
            context: 検証コンテキスト
            
        Returns:
            PriceConsistencyResult: 検証結果
        """
        if analysis_price <= 0 or entry_price <= 0:
            return PriceConsistencyResult(
                is_consistent=False,
                inconsistency_level=PriceInconsistencyLevel.CRITICAL,
                price_difference_pct=float('inf'),
                reference_price=analysis_price,
                comparison_price=entry_price,
                message="無効な価格データが検出されました（0以下の価格）",
                timestamp=datetime.now(),
                recommendations=["価格データの取得元を確認してください", "APIレスポンスの妥当性を検証してください"]
            )
        
        # 価格差の計算（分析価格を基準とする）
        price_diff_pct = abs(analysis_price - entry_price) / analysis_price * 100
        
        # 不整合レベルの判定
        if price_diff_pct < self.warning_threshold:
            level = PriceInconsistencyLevel.NORMAL
            is_consistent = True
            message = f"価格整合性: 正常 (差異: {price_diff_pct:.2f}%)"
            recommendations = []
        elif price_diff_pct < self.error_threshold:
            level = PriceInconsistencyLevel.WARNING
            is_consistent = True  # 警告レベルでは処理継続
            message = f"価格整合性: 警告 (差異: {price_diff_pct:.2f}%) - 軽微な不整合"
            recommendations = [
                "価格データのタイムスタンプを確認してください",
                "市場の急激な変動がないか確認してください"
            ]
        elif price_diff_pct < self.critical_threshold:
            level = PriceInconsistencyLevel.ERROR
            is_consistent = False
            message = f"価格整合性: エラー (差異: {price_diff_pct:.2f}%) - 中程度の不整合"
            recommendations = [
                "データソースの一致を確認してください",
                "タイムゾーンの設定を確認してください",
                "価格データの取得タイミングを確認してください"
            ]
        else:
            level = PriceInconsistencyLevel.CRITICAL
            is_consistent = False
            message = f"価格整合性: 重大エラー (差異: {price_diff_pct:.2f}%) - 深刻な不整合"
            recommendations = [
                "価格データの取得システムを緊急点検してください",
                "API接続状況を確認してください", 
                "データベースの破損がないか確認してください",
                "この分析結果は信頼できません - 使用を中止してください"
            ]
        
        result = PriceConsistencyResult(
            is_consistent=is_consistent,
            inconsistency_level=level,
            price_difference_pct=price_diff_pct,
            reference_price=analysis_price,
            comparison_price=entry_price,
            message=message,
            timestamp=datetime.now(),
            recommendations=recommendations
        )
        
        # 履歴に記録
        self.validation_history.append({
            'timestamp': result.timestamp,
            'symbol': symbol,
            'context': context,
            'level': level.value,
            'difference_pct': price_diff_pct,
            'analysis_price': analysis_price,
            'entry_price': entry_price
        })
        
        return result
    
    def create_unified_price_data(self,
                                analysis_price: float,
                                entry_price: float,
                                symbol: str,
                                timeframe: str,
                                market_timestamp: datetime,
                                analysis_timestamp: datetime = None,
                                data_source: str = "unknown") -> UnifiedPriceData:
        """
        統一価格データ構造を作成
        
        Args:
            analysis_price: 分析時の価格
            entry_price: エントリー時の実際価格
            symbol: 銘柄シンボル
            timeframe: 時間足
            market_timestamp: 市場データのタイムスタンプ
            analysis_timestamp: 分析実行時刻
            data_source: データソース
            
        Returns:
            UnifiedPriceData: 統一価格データ
        """
        if analysis_timestamp is None:
            analysis_timestamp = datetime.now()
        
        # 整合性スコアを計算（0-1、1が最高）
        if analysis_price <= 0 or entry_price <= 0:
            consistency_score = 0.0
        else:
            price_diff_pct = abs(analysis_price - entry_price) / analysis_price * 100
            if price_diff_pct < self.warning_threshold:
                consistency_score = 1.0
            elif price_diff_pct < self.error_threshold:
                consistency_score = 0.8
            elif price_diff_pct < self.critical_threshold:
                consistency_score = 0.5
            else:
                consistency_score = 0.0
        
        return UnifiedPriceData(
            analysis_price=analysis_price,
            entry_price=entry_price,
            market_timestamp=market_timestamp,
            analysis_timestamp=analysis_timestamp,
            symbol=symbol,
            timeframe=timeframe,
            data_source=data_source,
            consistency_score=consistency_score
        )
    
    def validate_backtest_result(self,
                               entry_price: float,
                               stop_loss_price: float,
                               take_profit_price: float,
                               exit_price: float,
                               duration_minutes: int,
                               symbol: str = "") -> Dict[str, Any]:
        """
        バックテスト結果の総合的な整合性検証
        
        Args:
            entry_price: エントリー価格
            stop_loss_price: 損切り価格
            take_profit_price: 利確価格
            exit_price: 実際のクローズ価格
            duration_minutes: 取引時間（分）
            symbol: 銘柄シンボル
            
        Returns:
            Dict[str, Any]: 検証結果
        """
        issues = []
        warnings = []
        severity_level = "normal"
        
        # 1. ロングポジションの論理検証
        if stop_loss_price >= entry_price:
            issues.append(f"損切り価格({stop_loss_price:.2f})がエントリー価格({entry_price:.2f})以上")
            severity_level = "critical"
        
        if take_profit_price <= entry_price:
            issues.append(f"利確価格({take_profit_price:.2f})がエントリー価格({entry_price:.2f})以下")
            severity_level = "critical"
        
        if stop_loss_price >= take_profit_price:
            issues.append(f"損切り価格({stop_loss_price:.2f})が利確価格({take_profit_price:.2f})以上")
            severity_level = "critical"
        
        # 2. 利益率の現実性チェック
        profit_rate = (exit_price - entry_price) / entry_price
        profit_percentage = profit_rate * 100
        
        # 年利換算
        if duration_minutes > 0:
            minutes_per_year = 365 * 24 * 60
            annual_rate_percentage = profit_percentage * (minutes_per_year / duration_minutes)
            
            # 非現実的利益率の検知
            if duration_minutes < 60 and profit_percentage > 20:
                issues.append(f"1時間未満で{profit_percentage:.1f}%の利益（非現実的）")
                severity_level = "critical"
            
            if duration_minutes < 120 and profit_percentage > 40:
                issues.append(f"2時間未満で{profit_percentage:.1f}%の利益（非現実的）")
                severity_level = "critical"
            
            if annual_rate_percentage > 1000:
                issues.append(f"年利換算{annual_rate_percentage:.0f}%（非現実的）")
                if severity_level not in ["critical"]:
                    severity_level = "error"
        
        # 3. 価格の妥当性チェック
        max_price = max(entry_price, stop_loss_price, take_profit_price, exit_price)
        min_price = min(entry_price, stop_loss_price, take_profit_price, exit_price)
        
        if max_price / min_price > 3.0:  # 300%以上の価格差
            warnings.append(f"価格レンジが異常に広い（最大{max_price:.2f}/最小{min_price:.2f}）")
            if severity_level == "normal":
                severity_level = "warning"
        
        # 4. 取引時間の妥当性
        if duration_minutes < 1:
            issues.append(f"取引時間が異常に短い（{duration_minutes}分）")
            severity_level = "critical"
        elif duration_minutes > 10080:  # 1週間超
            warnings.append(f"取引時間が異常に長い（{duration_minutes}分）")
            if severity_level == "normal":
                severity_level = "warning"
        
        return {
            'is_valid': len(issues) == 0,
            'severity_level': severity_level,
            'issues': issues,
            'warnings': warnings,
            'profit_percentage': profit_percentage,
            'annual_rate_percentage': annual_rate_percentage if duration_minutes > 0 else 0,
            'duration_minutes': duration_minutes,
            'symbol': symbol,
            'validation_timestamp': datetime.now()
        }
    
    def get_validation_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        過去指定時間の検証結果サマリーを取得
        
        Args:
            hours: 過去何時間分のデータを集計するか
            
        Returns:
            Dict[str, Any]: 検証サマリー
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_validations = [
            v for v in self.validation_history 
            if v['timestamp'] > cutoff_time
        ]
        
        if not recent_validations:
            return {
                'total_validations': 0,
                'consistent_count': 0,
                'consistency_rate': 0.0,
                'avg_difference_pct': 0.0,
                'level_counts': {},
                'period_hours': hours
            }
        
        level_counts = {}
        for level in PriceInconsistencyLevel:
            level_counts[level.value] = sum(
                1 for v in recent_validations if v['level'] == level.value
            )
        
        consistent_count = level_counts.get('normal', 0) + level_counts.get('warning', 0)
        consistency_rate = consistent_count / len(recent_validations) * 100
        avg_difference_pct = np.mean([v['difference_pct'] for v in recent_validations])
        
        return {
            'total_validations': len(recent_validations),
            'consistent_count': consistent_count,
            'consistency_rate': consistency_rate,
            'avg_difference_pct': avg_difference_pct,
            'level_counts': level_counts,
            'period_hours': hours,
            'timestamp': datetime.now()
        }


def test_price_consistency_validator():
    """価格整合性検証器のテスト"""
    print("🔧 価格データ整合性チェックシステム テスト")
    print("=" * 60)
    
    validator = PriceConsistencyValidator()
    
    # テストケース1: 正常な価格差（0.5%）
    print("\nテスト1: 正常な価格差")
    result1 = validator.validate_price_consistency(50000, 50250, "BTC", "normal_case")
    print(f"結果: {result1.message}")
    print(f"一貫性: {'✅' if result1.is_consistent else '❌'}")
    
    # テストケース2: 警告レベルの価格差（3%）
    print("\nテスト2: 警告レベルの価格差")
    result2 = validator.validate_price_consistency(50000, 51500, "ETH", "warning_case")
    print(f"結果: {result2.message}")
    print(f"一貫性: {'✅' if result2.is_consistent else '❌'}")
    print(f"推奨事項: {result2.recommendations}")
    
    # テストケース3: ETH異常ケース（重大エラー）
    print("\nテスト3: ETH異常ケース（重大エラー）")
    result3 = validator.validate_price_consistency(3950.0, 5739.36, "ETH", "eth_anomaly")
    print(f"結果: {result3.message}")
    print(f"一貫性: {'✅' if result3.is_consistent else '❌'}")
    print(f"推奨事項: {result3.recommendations}")
    
    # テストケース4: バックテスト結果の検証
    print("\nテスト4: バックテスト結果の総合検証")
    backtest_result = validator.validate_backtest_result(
        entry_price=1932.0,
        stop_loss_price=2578.0,  # エントリーより高い（異常）
        take_profit_price=2782.0,
        exit_price=2812.0,
        duration_minutes=50,     # 50分で45%利益
        symbol="ETH"
    )
    
    print(f"バックテスト妥当性: {'✅' if backtest_result['is_valid'] else '❌'}")
    print(f"深刻度: {backtest_result['severity_level']}")
    print(f"利益率: {backtest_result['profit_percentage']:.1f}%")
    print(f"年利換算: {backtest_result['annual_rate_percentage']:.0f}%")
    if backtest_result['issues']:
        print(f"問題: {backtest_result['issues']}")
    
    # 統一価格データの作成テスト
    print("\nテスト5: 統一価格データ作成")
    unified_data = validator.create_unified_price_data(
        analysis_price=50000,
        entry_price=50250,
        symbol="BTC",
        timeframe="1h",
        market_timestamp=datetime.now(),
        data_source="gate.io"
    )
    print(f"統一価格データ作成: ✅")
    print(f"整合性スコア: {unified_data.consistency_score:.2f}")
    
    # 検証サマリーの取得
    print("\nテスト6: 検証サマリー")
    summary = validator.get_validation_summary(hours=24)
    print(f"検証回数: {summary['total_validations']}")
    print(f"整合性率: {summary['consistency_rate']:.1f}%")
    print(f"平均差異: {summary['avg_difference_pct']:.2f}%")
    
    print("\n✅ 価格データ整合性チェックシステム テスト完了")
    return True


if __name__ == "__main__":
    test_price_consistency_validator()