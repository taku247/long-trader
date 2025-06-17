#!/usr/bin/env python3
"""
進捗ログ表示システム - 段階別詳細表示

銘柄追加の進捗を見やすくリアルタイム表示
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict


class SymbolProgressLogger:
    """銘柄追加進捗の段階別詳細表示ロガー"""
    
    def __init__(self, symbol: str, execution_id: str, total_patterns: int):
        self.symbol = symbol
        self.execution_id = execution_id[:8]
        self.total_patterns = total_patterns
        self.start_time = datetime.now()
        
        # 進捗追跡
        self.completed_by_timeframe = defaultdict(lambda: {"completed": 0, "total": 0})
        self.completed_strategies = []
        self.current_phase = "初期化"
        self.phase_start_times = {}
        
        # ログ設定（メインプロセス用）
        self.logger = logging.getLogger(__name__)
        
        # 直接print出力も使用（multiprocessing対応）
        self.use_print = True
        
        # タイムフレーム群の設定
        self.timeframe_groups = {
            "1h足戦略群": ["1h"],
            "30m足戦略群": ["30m"],
            "15m足戦略群": ["15m"],
            "5m足戦略群": ["5m"],
            "3m足戦略群": ["3m"],
            "短期足戦略群": ["1m"]
        }
        
        # 各グループの戦略数を計算（通常各タイムフレームで3戦略: Conservative_ML, Aggressive_Traditional, Full_ML）
        self.strategies_per_timeframe = 3
        
        # 初期化ログ
        self._log_initialization()
    
    def _log_initialization(self):
        """初期化ログ"""
        self._log("=" * 70)
        self._log(f"🚀 {self.symbol} 銘柄追加開始 [実行ID: {self.execution_id}]")
        self._log("=" * 70)
    
    def _log(self, message):
        """ログ出力（multiprocessing対応）"""
        if self.use_print:
            print(message)
        self.logger.info(message)
    
    def log_phase_start(self, phase: str, details: str = ""):
        """フェーズ開始ログ"""
        self.current_phase = phase
        self.phase_start_times[phase] = datetime.now()
        
        self._log(f"📋 フェーズ開始: {phase}")
        if details:
            self._log(f"   詳細: {details}")
        
        self._render_progress_box()
    
    def log_phase_complete(self, phase: str, duration_seconds: Optional[float] = None):
        """フェーズ完了ログ"""
        if duration_seconds is None and phase in self.phase_start_times:
            duration = datetime.now() - self.phase_start_times[phase]
            duration_seconds = duration.total_seconds()
        
        duration_str = f"({duration_seconds:.1f}s)" if duration_seconds else ""
        self._log(f"✅ フェーズ完了: {phase} {duration_str}")
        
        self._render_progress_box()
    
    def log_strategy_complete(self, timeframe: str, strategy: str, results: Dict):
        """個別戦略完了ログ"""
        strategy_name = f"{self.symbol}_{timeframe}_{strategy}"
        self.completed_strategies.append(strategy_name)
        
        # タイムフレーム別カウント更新
        self.completed_by_timeframe[timeframe]["completed"] += 1
        if self.completed_by_timeframe[timeframe]["total"] == 0:
            self.completed_by_timeframe[timeframe]["total"] = self.strategies_per_timeframe
        
        # 詳細結果表示
        self._log_strategy_details(strategy_name, results)
        
        # 進捗ボックス更新
        self._render_progress_box()
    
    def _log_strategy_details(self, strategy_name: str, results: Dict):
        """戦略完了の詳細ログ"""
        self._log("=" * 60)
        self._log(f"🎉 完了: {strategy_name}")
        
        # 結果データの解析
        trade_count = results.get('total_trades', 0)
        win_rate = results.get('win_rate', 0) * 100 if results.get('win_rate') else 0
        total_return = results.get('total_return_pct', 0)
        max_drawdown = results.get('max_drawdown_pct', 0)
        sharpe_ratio = results.get('sharpe_ratio', 0)
        max_consecutive_wins = results.get('max_consecutive_wins', 0)
        execution_time = results.get('execution_time_seconds', 0)
        
        self._log(f"   📊 結果: 取引数 {trade_count}, 勝率 {win_rate:.1f}%, 収益率 {total_return:+.1f}%")
        self._log(f"   💰 最大DD: {max_drawdown:.1f}%, Sharpe: {sharpe_ratio:.2f}, 最大連勝: {max_consecutive_wins}回")
        self._log(f"   ⏱️  実行時間: {execution_time:.0f}秒")
        self._log("=" * 60)
    
    def _render_progress_box(self):
        """美しいボックス形式の進捗表示"""
        # 実行時間計算
        elapsed = datetime.now() - self.start_time
        elapsed_str = self._format_duration(elapsed)
        
        # 全体進捗計算
        total_completed = len(self.completed_strategies)
        overall_progress = (total_completed / self.total_patterns * 100) if self.total_patterns > 0 else 0
        
        # フェーズ状況
        completed_phases = set()
        for phase in self.phase_start_times.keys():
            if phase != self.current_phase:
                completed_phases.add(phase)
                
        phase_icons = {
            "データ取得": "✅" if "データ取得" in completed_phases else ("🔄" if self.current_phase == "データ取得" else "⏳"),
            "バックテスト": "🔄" if self.current_phase == "バックテスト" else ("✅" if total_completed == self.total_patterns else "⏳"),
            "最適化・保存": "✅" if self.current_phase == "最適化・保存" else "⏳"
        }
        
        # ボックス描画
        self._log("")
        self._log(f"🚀 {self.symbol} 銘柄追加進捗 [実行ID: {self.execution_id}]")
        self._log("┌─────────────────────────────────────────────────────┐")
        
        # フェーズ1: データ取得
        data_phase_str = f"│ フェーズ1: データ取得 {phase_icons['データ取得']} "
        if phase_icons['データ取得'] == "✅":
            data_duration = self._get_phase_duration("データ取得")
            data_phase_str += f"完了 ({data_duration})"
        else:
            data_phase_str += "進行中"
        data_phase_str = data_phase_str.ljust(53) + "│"
        self._log(data_phase_str)
        
        # フェーズ2: バックテスト
        backtest_phase_str = f"│ フェーズ2: バックテスト {phase_icons['バックテスト']} "
        if phase_icons['バックテスト'] == "🔄":
            backtest_phase_str += f"進行中 ({elapsed_str}経過)"
        elif phase_icons['バックテスト'] == "✅":
            backtest_duration = self._get_phase_duration("バックテスト")
            backtest_phase_str += f"完了 ({backtest_duration})"
        else:
            backtest_phase_str += "待機中"
        backtest_phase_str = backtest_phase_str.ljust(53) + "│"
        self._log(backtest_phase_str)
        
        # タイムフレーム別進捗
        for group_name, timeframes in self.timeframe_groups.items():
            group_completed = sum(self.completed_by_timeframe[tf]["completed"] for tf in timeframes)
            group_total = sum(self.completed_by_timeframe[tf]["total"] for tf in timeframes)
            
            if group_total == 0:
                group_total = len(timeframes) * self.strategies_per_timeframe
            
            progress_pct = (group_completed / group_total * 100) if group_total > 0 else 0
            progress_bar = self._create_progress_bar(progress_pct)
            
            group_str = f"│   ├─ {group_name}   [{group_completed}/{group_total}完了] {progress_bar} {progress_pct:3.0f}%"
            group_str = group_str.ljust(53) + "│"
            self._log(group_str)
        
        # フェーズ3: 最適化・保存
        optimization_phase_str = f"│ フェーズ3: 最適化・保存 {phase_icons['最適化・保存']} "
        if phase_icons['最適化・保存'] == "✅":
            opt_duration = self._get_phase_duration("最適化・保存")
            optimization_phase_str += f"完了 ({opt_duration})"
        else:
            optimization_phase_str += "待機中"
        optimization_phase_str = optimization_phase_str.ljust(53) + "│"
        self._log(optimization_phase_str)
        
        self._log("└─────────────────────────────────────────────────────┘")
        
        # 全体進捗
        overall_bar = self._create_progress_bar(overall_progress, width=20)
        self._log(f"📈 全体進捗: {overall_bar} {overall_progress:.0f}% ({total_completed}/{self.total_patterns})")
        self._log("")
    
    def _create_progress_bar(self, percentage: float, width: int = 6) -> str:
        """プログレスバーを作成"""
        filled = int(percentage / 100 * width)
        empty = width - filled
        return "█" * filled + "░" * empty
    
    def _format_duration(self, duration: timedelta) -> str:
        """継続時間をフォーマット"""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}時間{minutes}分{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分{seconds}秒"
        else:
            return f"{seconds}秒"
    
    def _get_phase_duration(self, phase: str) -> str:
        """特定フェーズの実行時間を取得"""
        if phase in self.phase_start_times:
            duration = datetime.now() - self.phase_start_times[phase]
            return self._format_duration(duration)
        return "不明"
    
    def log_final_summary(self, success: bool, total_duration: Optional[float] = None):
        """最終サマリーログ"""
        if total_duration is None:
            total_duration = (datetime.now() - self.start_time).total_seconds()
        
        duration_str = self._format_duration(timedelta(seconds=total_duration))
        
        self._log("=" * 70)
        if success:
            self._log(f"🎉 {self.symbol} 銘柄追加完了！")
            self._log(f"   📊 総処理時間: {duration_str}")
            self._log(f"   ✅ 完了戦略数: {len(self.completed_strategies)}/{self.total_patterns}")
        else:
            self._log(f"❌ {self.symbol} 銘柄追加失敗")
            self._log(f"   ⏱️ 処理時間: {duration_str}")
            self._log(f"   📊 完了戦略数: {len(self.completed_strategies)}/{self.total_patterns}")
        
        self._log("=" * 70)
    
    def log_error(self, error_message: str, phase: Optional[str] = None):
        """エラーログ"""
        self._log("=" * 60)
        self._log(f"❌ エラー発生: {self.symbol}")
        if phase:
            self._log(f"   フェーズ: {phase}")
        self._log(f"   詳細: {error_message}")
        self._log("=" * 60)


def create_progress_logger(symbol: str, execution_id: str, total_patterns: int) -> SymbolProgressLogger:
    """進捗ロガーのファクトリー関数"""
    return SymbolProgressLogger(symbol, execution_id, total_patterns)