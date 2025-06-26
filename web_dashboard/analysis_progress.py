"""
Real-time analysis progress tracking for web dashboard
"""
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json

@dataclass
class SupportResistanceResult:
    """支持線・抵抗線検出結果"""
    status: str  # 'success', 'failed', 'running'
    supports_count: int = 0
    resistances_count: int = 0
    supports: List[Dict] = None
    resistances: List[Dict] = None
    error_message: str = ""
    
    def __post_init__(self):
        if self.supports is None:
            self.supports = []
        if self.resistances is None:
            self.resistances = []

@dataclass
class MLPredictionResult:
    """ML予測結果"""
    status: str  # 'success', 'failed', 'running'
    predictions_count: int = 0
    confidence: float = 0.0
    error_message: str = ""

@dataclass
class MarketContextResult:
    """市場コンテキスト分析結果"""
    status: str  # 'success', 'failed', 'running'
    trend_direction: str = ""
    market_phase: str = ""
    error_message: str = ""

@dataclass
class LeverageDecisionResult:
    """レバレッジ判定結果"""
    status: str  # 'success', 'failed', 'running'
    recommended_leverage: float = 0.0
    confidence_level: float = 0.0
    risk_reward_ratio: float = 0.0
    error_message: str = ""

@dataclass
class AnalysisProgress:
    """分析進捗の全体状況"""
    symbol: str
    execution_id: str
    start_time: datetime
    current_stage: str = "initializing"  # initializing, data_fetch, support_resistance, ml_prediction, market_context, leverage_decision, completed, failed
    overall_status: str = "running"  # running, success, failed
    
    # 各段階の結果
    support_resistance: SupportResistanceResult = None
    ml_prediction: MLPredictionResult = None
    market_context: MarketContextResult = None
    leverage_decision: LeverageDecisionResult = None
    
    # 最終結果
    final_signal: str = "analyzing"  # analyzing, signal_detected, no_signal
    failure_stage: str = ""
    final_message: str = ""
    
    def __post_init__(self):
        if self.support_resistance is None:
            self.support_resistance = SupportResistanceResult(status="pending")
        if self.ml_prediction is None:
            self.ml_prediction = MLPredictionResult(status="pending")
        if self.market_context is None:
            self.market_context = MarketContextResult(status="pending")
        if self.leverage_decision is None:
            self.leverage_decision = LeverageDecisionResult(status="pending")
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（JSON用）"""
        return {
            'symbol': self.symbol,
            'execution_id': self.execution_id,
            'start_time': self.start_time.isoformat(),
            'current_stage': self.current_stage,
            'overall_status': self.overall_status,
            'support_resistance': asdict(self.support_resistance),
            'ml_prediction': asdict(self.ml_prediction),
            'market_context': asdict(self.market_context),
            'leverage_decision': asdict(self.leverage_decision),
            'final_signal': self.final_signal,
            'failure_stage': self.failure_stage,
            'final_message': self.final_message
        }

class AnalysisProgressTracker:
    """分析進捗を追跡するシングルトンクラス"""
    
    _instance = None
    _progress_data: Dict[str, AnalysisProgress] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._progress_data = {}
        return cls._instance
    
    def start_analysis(self, symbol: str, execution_id: str) -> AnalysisProgress:
        """分析開始"""
        progress = AnalysisProgress(
            symbol=symbol,
            execution_id=execution_id,
            start_time=datetime.now()
        )
        self._progress_data[execution_id] = progress
        return progress
    
    def get_progress(self, execution_id: str) -> Optional[AnalysisProgress]:
        """進捗取得"""
        return self._progress_data.get(execution_id)
    
    def update_stage(self, execution_id: str, stage: str):
        """現在の段階を更新"""
        if execution_id in self._progress_data:
            self._progress_data[execution_id].current_stage = stage
    
    def update_support_resistance(self, execution_id: str, result: SupportResistanceResult):
        """支持線・抵抗線結果を更新"""
        if execution_id in self._progress_data:
            self._progress_data[execution_id].support_resistance = result
    
    def update_ml_prediction(self, execution_id: str, result: MLPredictionResult):
        """ML予測結果を更新"""
        if execution_id in self._progress_data:
            self._progress_data[execution_id].ml_prediction = result
    
    def update_market_context(self, execution_id: str, result: MarketContextResult):
        """市場コンテキスト結果を更新"""
        if execution_id in self._progress_data:
            self._progress_data[execution_id].market_context = result
    
    def update_leverage_decision(self, execution_id: str, result: LeverageDecisionResult):
        """レバレッジ判定結果を更新"""
        if execution_id in self._progress_data:
            self._progress_data[execution_id].leverage_decision = result
    
    def complete_analysis(self, execution_id: str, signal: str, message: str = ""):
        """分析完了"""
        if execution_id in self._progress_data:
            progress = self._progress_data[execution_id]
            progress.overall_status = "success"
            progress.current_stage = "completed"
            progress.final_signal = signal
            progress.final_message = message
    
    def fail_analysis(self, execution_id: str, stage: str, message: str):
        """分析失敗"""
        if execution_id in self._progress_data:
            progress = self._progress_data[execution_id]
            progress.overall_status = "failed"
            progress.failure_stage = stage
            progress.final_signal = "no_signal"
            progress.final_message = message
    
    def get_all_recent(self, hours: int = 1) -> List[AnalysisProgress]:
        """最近の分析結果を取得"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        return [
            progress for progress in self._progress_data.values()
            if progress.start_time.timestamp() > cutoff_time
        ]
    
    def cleanup_old(self, hours: int = 24):
        """古い分析結果をクリーンアップ"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        to_remove = [
            execution_id for execution_id, progress in self._progress_data.items()
            if progress.start_time.timestamp() <= cutoff_time
        ]
        for execution_id in to_remove:
            del self._progress_data[execution_id]

# グローバルインスタンス
progress_tracker = AnalysisProgressTracker()