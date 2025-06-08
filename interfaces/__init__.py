"""
インターフェースモジュール

プラグインシステムのインターフェースと標準データ型を提供します。
"""

from .base_interfaces import (
    IDataProvider,
    ISupportResistanceAnalyzer,
    IBreakoutPredictor,
    IBTCCorrelationAnalyzer,
    IMarketContextAnalyzer,
    ILeverageDecisionEngine,
    IHighLeverageBotOrchestrator,
    IStopLossTakeProfitCalculator,
    PluginRegistry
)

from .data_types import (
    SupportResistanceLevel,
    BreakoutPrediction,
    BTCCorrelationRisk,
    MarketContext,
    LeverageRecommendation,
    StopLossTakeProfitLevels,
    TechnicalIndicators,
    OHLCVData,
    AnalysisResult,
    ValidationError,
    validate_support_resistance_level,
    validate_breakout_prediction,
    validate_leverage_recommendation
)

__all__ = [
    # インターフェース
    'IDataProvider',
    'ISupportResistanceAnalyzer',
    'IBreakoutPredictor',
    'IBTCCorrelationAnalyzer',
    'IMarketContextAnalyzer',
    'ILeverageDecisionEngine',
    'IHighLeverageBotOrchestrator',
    'IStopLossTakeProfitCalculator',
    'PluginRegistry',
    
    # データ型
    'SupportResistanceLevel',
    'BreakoutPrediction',
    'BTCCorrelationRisk',
    'MarketContext',
    'LeverageRecommendation',
    'StopLossTakeProfitLevels',
    'TechnicalIndicators',
    'OHLCVData',
    'AnalysisResult',
    'ValidationError',
    
    # 検証関数
    'validate_support_resistance_level',
    'validate_breakout_prediction',
    'validate_leverage_recommendation'
]