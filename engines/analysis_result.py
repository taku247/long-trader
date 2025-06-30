"""
分析結果の詳細情報を管理するデータクラス

Early Exitの理由や各ステップの詳細情報を記録し、
ユーザーに分かりやすいメッセージを提供する。
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

class AnalysisStage(Enum):
    """分析ステージの定義"""
    DATA_FETCH = "data_fetch"
    SUPPORT_RESISTANCE = "support_resistance_analysis"
    ML_PREDICTION = "ml_prediction"
    BTC_CORRELATION = "btc_correlation_analysis"
    MARKET_CONTEXT = "market_context_analysis"
    LEVERAGE_DECISION = "leverage_decision"
    COMPLETED = "completed"

class ExitReason(Enum):
    """Early Exit理由の定義"""
    NO_SUPPORT_RESISTANCE = "no_support_resistance_levels"
    INSUFFICIENT_DATA = "insufficient_data"
    ML_PREDICTION_FAILED = "ml_prediction_failed"
    BTC_DATA_INSUFFICIENT = "btc_data_insufficient"
    MARKET_CONTEXT_FAILED = "market_context_failed"
    LEVERAGE_CONDITIONS_NOT_MET = "leverage_conditions_not_met"
    DATA_QUALITY_POOR = "data_quality_poor"
    EXECUTION_ERROR = "execution_error"

@dataclass
class StageResult:
    """各ステージの実行結果"""
    stage: AnalysisStage
    success: bool
    execution_time_ms: float
    data_processed: Optional[int] = None
    items_found: Optional[int] = None
    error_message: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AnalysisResult:
    """分析結果の詳細情報"""
    symbol: str
    timeframe: str
    strategy: str
    execution_id: Optional[str] = None
    
    # 実行状態
    completed: bool = False
    early_exit: bool = False
    exit_stage: Optional[AnalysisStage] = None
    exit_reason: Optional[ExitReason] = None
    
    # ステージ別結果
    stage_results: List[StageResult] = None
    
    # データ情報
    total_data_points: Optional[int] = None
    analysis_period_start: Optional[datetime] = None
    analysis_period_end: Optional[datetime] = None
    
    # 最終結果（成功時のみ）
    recommendation: Optional[Dict[str, Any]] = None
    
    # エラー情報
    error_details: Optional[str] = None
    
    # タイムスタンプ
    started_at: datetime = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.stage_results is None:
            self.stage_results = []
        if self.started_at is None:
            self.started_at = datetime.now()
    
    def add_stage_result(self, stage_result: StageResult):
        """ステージ結果を追加"""
        self.stage_results.append(stage_result)
    
    def mark_early_exit(self, stage: AnalysisStage, reason: ExitReason, error_message: str = None):
        """Early Exitをマーク"""
        self.early_exit = True
        self.exit_stage = stage
        self.exit_reason = reason
        self.error_details = error_message
        self.completed_at = datetime.now()
    
    def mark_completed(self, recommendation: Dict[str, Any] = None):
        """分析完了をマーク"""
        self.completed = True
        self.recommendation = recommendation
        self.completed_at = datetime.now()
    
    def get_user_friendly_message(self) -> str:
        """ユーザー向けの分かりやすいメッセージを生成"""
        if self.completed and self.recommendation:
            return f"✅ {self.symbol} {self.strategy}({self.timeframe}): 分析完了 - シグナル検出"
        
        if self.early_exit:
            stage_names = {
                AnalysisStage.DATA_FETCH: "データ取得",
                AnalysisStage.SUPPORT_RESISTANCE: "サポート・レジスタンス分析",
                AnalysisStage.ML_PREDICTION: "ML予測",
                AnalysisStage.BTC_CORRELATION: "BTC相関分析",
                AnalysisStage.MARKET_CONTEXT: "市場コンテキスト分析",
                AnalysisStage.LEVERAGE_DECISION: "レバレッジ判定"
            }
            
            reason_messages = {
                ExitReason.NO_SUPPORT_RESISTANCE: "サポート・レジスタンスレベルが検出されませんでした",
                ExitReason.INSUFFICIENT_DATA: "分析に必要な十分なデータがありません",
                ExitReason.ML_PREDICTION_FAILED: "ML予測システムでエラーが発生しました",
                ExitReason.BTC_DATA_INSUFFICIENT: "BTC相関分析用のデータが不足しています",
                ExitReason.MARKET_CONTEXT_FAILED: "市場コンテキスト分析でエラーが発生しました",
                ExitReason.LEVERAGE_CONDITIONS_NOT_MET: "レバレッジ条件を満たしませんでした",
                ExitReason.DATA_QUALITY_POOR: "データ品質が分析基準を満たしていません"
            }
            
            stage_name = stage_names.get(self.exit_stage, self.exit_stage.value)
            reason_msg = reason_messages.get(self.exit_reason, self.exit_reason.value)
            
            return f"⏭️ {self.symbol} {self.strategy}({self.timeframe}): {stage_name}で早期終了 - {reason_msg}"
        
        return f"❌ {self.symbol} {self.strategy}({self.timeframe}): 分析失敗"
    
    def get_detailed_log_message(self) -> str:
        """開発者向けの詳細ログメッセージを生成"""
        base_msg = f"{self.symbol} {self.timeframe} {self.strategy}"
        
        if self.completed and self.recommendation:
            return f"✅ {base_msg}: 分析完了 (データ:{self.total_data_points}件)"
        
        if self.early_exit:
            data_info = f"データ:{self.total_data_points}件" if self.total_data_points else "データ不明"
            return f"⏭️ {base_msg}: STEP{self._get_stage_number()}で早期終了 - {self.exit_reason.value} ({data_info})"
        
        return f"❌ {base_msg}: 分析失敗 - {self.error_details or '不明なエラー'}"
    
    def _get_stage_number(self) -> int:
        """ステージ番号を取得"""
        stage_numbers = {
            AnalysisStage.DATA_FETCH: 1,
            AnalysisStage.SUPPORT_RESISTANCE: 2,
            AnalysisStage.ML_PREDICTION: 3,
            AnalysisStage.BTC_CORRELATION: 4,
            AnalysisStage.MARKET_CONTEXT: 5,
            AnalysisStage.LEVERAGE_DECISION: 6
        }
        return stage_numbers.get(self.exit_stage, 0)
    
    def get_suggestions(self) -> List[str]:
        """改善提案を生成"""
        suggestions = []
        
        if self.exit_reason == ExitReason.NO_SUPPORT_RESISTANCE:
            suggestions.extend([
                "より長い分析期間を設定してください",
                "異なる時間足（1h→4h、15m→1hなど）を試してください",
                "別の戦略（Conservative_ML、Aggressive_MLなど）を試してください"
            ])
        elif self.exit_reason == ExitReason.INSUFFICIENT_DATA:
            suggestions.extend([
                "より長い期間のデータを取得してください",
                "データ品質を確認してください"
            ])
        elif self.exit_reason == ExitReason.ML_PREDICTION_FAILED:
            suggestions.extend([
                "データ期間を調整してください",
                "ML予測を使わない戦略を試してください"
            ])
        
        return suggestions
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（JSON出力用）"""
        result = asdict(self)
        
        # Enumを文字列に変換
        if self.exit_stage:
            result['exit_stage'] = self.exit_stage.value
        if self.exit_reason:
            result['exit_reason'] = self.exit_reason.value
        
        # datetimeを文字列に変換
        if self.started_at:
            result['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            result['completed_at'] = self.completed_at.isoformat()
        if self.analysis_period_start:
            result['analysis_period_start'] = self.analysis_period_start.isoformat()
        if self.analysis_period_end:
            result['analysis_period_end'] = self.analysis_period_end.isoformat()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """辞書から復元"""
        # Enum変換
        if 'exit_stage' in data and data['exit_stage']:
            data['exit_stage'] = AnalysisStage(data['exit_stage'])
        if 'exit_reason' in data and data['exit_reason']:
            data['exit_reason'] = ExitReason(data['exit_reason'])
        
        # datetime変換
        for field in ['started_at', 'completed_at', 'analysis_period_start', 'analysis_period_end']:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        
        # StageResult変換
        if 'stage_results' in data and data['stage_results']:
            stage_results = []
            for sr_data in data['stage_results']:
                if 'stage' in sr_data:
                    sr_data['stage'] = AnalysisStage(sr_data['stage'])
                stage_results.append(StageResult(**sr_data))
            data['stage_results'] = stage_results
        
        return cls(**data)