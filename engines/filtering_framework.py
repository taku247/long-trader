#!/usr/bin/env python3
"""
フィルタリングフレームワーク

9段階早期フィルタリングシステムの中心となるフレームワーク。
フィルターチェーンの管理と実行統計の追跡を行う。
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from engines.filters.base_filter import BaseFilter, FilterResult, DataQualityFilter, MarketConditionFilter, SupportResistanceFilter
from engines.filters.medium_weight_filters import DistanceAnalysisFilter, MLConfidenceFilter, VolatilityFilter
from engines.filters.heavy_weight_filters import LeverageFilter, RiskRewardFilter, StrategySpecificFilter
from real_time_system.utils.colored_log import get_colored_logger


@dataclass
class FilteringStatistics:
    """フィルタリング統計情報"""
    total_evaluations: int = 0
    valid_trades: int = 0
    filtering_stats: Dict[str, int] = None
    execution_time: float = 0.0
    
    def __post_init__(self):
        if self.filtering_stats is None:
            self.filtering_stats = {f"filter_{i}": 0 for i in range(1, 10)}
    
    def get_efficiency_metrics(self) -> Dict[str, float]:
        """効率指標を計算"""
        if self.total_evaluations == 0:
            return {}
        
        return {
            'pass_rate': (self.valid_trades / self.total_evaluations) * 100,
            'total_excluded': self.total_evaluations - self.valid_trades,
            'exclusion_rate': ((self.total_evaluations - self.valid_trades) / self.total_evaluations) * 100,
            'avg_evaluation_time': self.execution_time / self.total_evaluations if self.total_evaluations > 0 else 0
        }


class FilteringFramework:
    """
    フィルタリングフレームワーク
    
    9段階早期フィルタリングシステムの中心クラス。
    フィルターチェーンの構築、実行、統計管理を行う。
    """
    
    def __init__(self, prepared_data_factory: Optional[Callable] = None, 
                 strategy_factory: Optional[Callable] = None,
                 progress_callback: Optional[Callable] = None,
                 strategy=None, prepared_data=None):
        """
        Args:
            prepared_data_factory: PreparedDataインスタンスを返すファクトリー関数
            strategy_factory: 戦略インスタンスを返すファクトリー関数
            progress_callback: 進捗更新コールバック関数
            strategy: 実行戦略（後方互換性のため）
            prepared_data: 事前準備された分析データ（後方互換性のため）
        """
        # ファクトリー形式と旧形式の両方をサポート
        if prepared_data_factory is not None:
            self.prepared_data = prepared_data_factory()
        else:
            self.prepared_data = prepared_data
            
        if strategy_factory is not None:
            self.strategy = strategy_factory()
        else:
            self.strategy = strategy
            
        self.progress_callback = progress_callback
        self.logger = get_colored_logger(__name__)
        
        # フィルターチェーンの構築
        self.filter_chain = self._build_filter_chain()
        
        # 統計情報の初期化
        self.statistics = FilteringStatistics()
    
    def _build_filter_chain(self) -> List[BaseFilter]:
        """戦略に応じたフィルターチェーンを構築"""
        filters = [
            # 軽量フィルター（Light Weight）
            DataQualityFilter(),           # Filter 1
            MarketConditionFilter(),       # Filter 2
            SupportResistanceFilter(),     # Filter 3
            
            # 中重量フィルター（Medium Weight）
            DistanceAnalysisFilter(),      # Filter 4
            MLConfidenceFilter(),          # Filter 5
            VolatilityFilter(),            # Filter 6
            
            # 重量フィルター（Heavy Weight）
            LeverageFilter(),              # Filter 7
            RiskRewardFilter(),            # Filter 8
            StrategySpecificFilter(),      # Filter 9
        ]
        
        self.logger.info(f"🔗 フィルターチェーン構築完了: {len(filters)}個のフィルター")
        for i, f in enumerate(filters, 1):
            self.logger.info(f"   Filter {i}: {f.name} ({f.weight})")
        
        return filters
    
    def execute_filtering(self, evaluation_times: List[datetime]) -> List[Dict[str, Any]]:
        """
        9段階フィルタリング実行
        
        Args:
            evaluation_times: 評価時点のリスト
            
        Returns:
            List[Dict]: 有効な取引機会のリスト
        """
        self.logger.info(f"🚀 フィルタリング開始: {len(evaluation_times)}個の評価時点")
        start_time = time.time()
        
        valid_trades = []
        self.statistics.total_evaluations = len(evaluation_times)
        
        for idx, evaluation_time in enumerate(evaluation_times):
            # 各評価時点でフィルターチェーンを実行
            filter_result = self._execute_filter_chain(evaluation_time)
            
            if filter_result.passed:
                # フィルターを通過した場合、取引シミュレーションを実行
                trade = self._execute_trade_simulation(evaluation_time)
                if trade:
                    valid_trades.append(trade)
            else:
                # どのフィルターで除外されたかを記録
                self._record_filter_exclusion(idx + 1)
            
            # 進捗更新
            if idx % 100 == 0 or idx == len(evaluation_times) - 1:
                self._update_progress(idx + 1, len(evaluation_times), len(valid_trades))
        
        # 統計情報の更新
        self.statistics.valid_trades = len(valid_trades)
        self.statistics.execution_time = time.time() - start_time
        
        # 結果のログ出力
        self._log_filtering_results(len(evaluation_times), len(valid_trades))
        
        return valid_trades
    
    def _execute_filter_chain(self, evaluation_time: datetime) -> FilterResult:
        """
        各フィルターを順次実行、いずれかで除外されれば即座に停止
        
        Args:
            evaluation_time: 評価時点
            
        Returns:
            FilterResult: 最終的なフィルター結果
        """
        for i, filter_obj in enumerate(self.filter_chain, 1):
            try:
                filter_start = time.time()
                result = filter_obj.execute(self.prepared_data, self.strategy, evaluation_time)
                filter_duration = time.time() - filter_start
                
                # タイムアウトチェック
                if filter_duration > filter_obj.max_execution_time:
                    self.logger.warning(f"⏰ Filter {i} ({filter_obj.name}) タイムアウト: {filter_duration:.2f}s")
                
                # フィルターで除外された場合は即座に停止
                if not result.passed:
                    self.statistics.filtering_stats[f"filter_{i}"] += 1
                    return FilterResult(
                        passed=False,
                        reason=f"Filter {i} ({filter_obj.name}): {result.reason}",
                        metrics={
                            'failed_at_filter': i,
                            'filter_name': filter_obj.name,
                            'filter_reason': result.reason,
                            'filter_metrics': result.metrics
                        }
                    )
                
            except Exception as e:
                self.logger.error(f"❌ Filter {i} ({filter_obj.name}) 実行エラー: {str(e)}")
                self.statistics.filtering_stats[f"filter_{i}"] += 1
                return FilterResult(
                    passed=False,
                    reason=f"Filter {i} ({filter_obj.name}): 実行エラー - {str(e)}",
                    metrics={'failed_at_filter': i, 'error': str(e)}
                )
        
        # 全てのフィルターを通過
        return FilterResult(
            passed=True,
            reason="全フィルターを通過",
            metrics={'filters_passed': len(self.filter_chain)}
        )
    
    def _execute_trade_simulation(self, evaluation_time: datetime) -> Optional[Dict[str, Any]]:
        """
        取引シミュレーションを実行（まだモック実装）
        
        Args:
            evaluation_time: 評価時点
            
        Returns:
            Optional[Dict]: 取引結果（None=無効な取引）
        """
        # TODO: 実際の取引シミュレーションロジックを実装
        try:
            # 現在価格を取得
            current_price = self.prepared_data.get_price_at(evaluation_time)
            
            # 簡単な取引シミュレーション（モック）
            mock_trade = {
                'evaluation_time': evaluation_time,
                'entry_price': current_price,
                'strategy': self.strategy.name,
                'leverage': 2.0,  # モック値
                'profit_potential': 0.05,  # モック値（5%）
                'downside_risk': 0.03,  # モック値（3%）
                'risk_reward_ratio': 0.05 / 0.03,  # 約1.67
                'confidence_score': 0.75  # モック値
            }
            
            return mock_trade
            
        except Exception as e:
            self.logger.error(f"❌ 取引シミュレーション実行エラー: {str(e)}")
            return None
    
    def _record_filter_exclusion(self, filter_number: int):
        """フィルター除外を記録"""
        # この実装では _execute_filter_chain 内で既に記録済み
        pass
    
    def _update_progress(self, current: int, total: int, valid_count: int):
        """進捗を更新"""
        progress_pct = (current / total) * 100
        
        if self.progress_callback:
            self.progress_callback({
                'stage': 'filtering',
                'progress': progress_pct,
                'current': current,
                'total': total,
                'valid_trades': valid_count,
                'message': f"フィルタリング進行中: {current}/{total} ({progress_pct:.1f}%) - 有効: {valid_count}"
            })
        
        # 定期的なログ出力
        if current % 500 == 0 or current == total:
            self.logger.info(f"📊 フィルタリング進捗: {current}/{total} ({progress_pct:.1f}%) - 有効取引: {valid_count}")
    
    def _log_filtering_results(self, total_evaluations: int, valid_trades: int):
        """フィルタリング結果をログ出力"""
        efficiency = self.statistics.get_efficiency_metrics()
        
        self.logger.info("=" * 60)
        self.logger.info("🎯 フィルタリング結果サマリー")
        self.logger.info("=" * 60)
        self.logger.info(f"📊 総評価時点数: {total_evaluations}")
        self.logger.info(f"✅ 有効取引数: {valid_trades}")
        self.logger.info(f"❌ 除外数: {total_evaluations - valid_trades}")
        self.logger.info(f"📈 通過率: {efficiency.get('pass_rate', 0):.2f}%")
        self.logger.info(f"⏱️  実行時間: {self.statistics.execution_time:.2f}秒")
        self.logger.info(f"⚡ 平均評価時間: {efficiency.get('avg_evaluation_time', 0):.4f}秒/回")
        
        # フィルター別除外統計
        self.logger.info("\n🔍 フィルター別除外統計:")
        for filter_name, count in self.statistics.filtering_stats.items():
            if count > 0:
                percentage = (count / total_evaluations) * 100
                self.logger.info(f"   {filter_name}: {count}回 ({percentage:.1f}%)")
        
        # フィルター個別統計
        self.logger.info("\n📋 フィルター個別統計:")
        for i, filter_obj in enumerate(self.filter_chain, 1):
            stats = filter_obj.get_statistics()
            self.logger.info(f"   Filter {i} ({stats['name']}): "
                           f"実行{stats['execution_count']}回, "
                           f"成功{stats['success_count']}回, "
                           f"成功率{stats['success_rate']:.1%}")
    
    def get_statistics(self) -> FilteringStatistics:
        """統計情報を取得"""
        return self.statistics
    
    def reset_statistics(self):
        """統計情報をリセット"""
        self.statistics = FilteringStatistics()
        for filter_obj in self.filter_chain:
            filter_obj.reset_statistics()