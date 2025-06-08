"""
標準データ型定義 - プラグインシステム用

このモジュールは全てのプラグインが使用する標準データ型を定義します。
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Union
from datetime import datetime
import pandas as pd

@dataclass
class SupportResistanceLevel:
    """サポート・レジスタンスレベル"""
    price: float
    strength: float  # 0.0-1.0
    touch_count: int
    level_type: str  # 'support' or 'resistance'
    first_touch: datetime
    last_touch: datetime
    volume_at_level: float
    distance_from_current: float  # 現在価格からの距離（%）

@dataclass
class BreakoutPrediction:
    """ブレイクアウト予測結果"""
    level: SupportResistanceLevel
    breakout_probability: float  # 0.0-1.0
    bounce_probability: float    # 0.0-1.0
    prediction_confidence: float # 0.0-1.0
    predicted_price_target: Optional[float]
    time_horizon_minutes: int
    model_name: str

@dataclass
class BTCCorrelationRisk:
    """BTC相関リスク評価"""
    symbol: str
    btc_drop_scenario: float  # BTC下落率（%）
    predicted_altcoin_drop: Dict[int, float]  # {時間幅(分): 予測下落率(%)}
    correlation_strength: float  # 0.0-1.0
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    liquidation_risk: Dict[int, float]  # {時間幅(分): 清算リスク確率}

@dataclass
class MarketContext:
    """市場コンテキスト"""
    current_price: float
    volume_24h: float
    volatility: float
    trend_direction: str  # 'BULLISH', 'BEARISH', 'SIDEWAYS'
    market_phase: str     # 'ACCUMULATION', 'MARKUP', 'DISTRIBUTION', 'MARKDOWN'
    timestamp: datetime

@dataclass
class StopLossTakeProfitLevels:
    """損切り・利確レベル"""
    stop_loss_price: float
    take_profit_price: float
    risk_reward_ratio: float
    stop_loss_distance_pct: float  # 現在価格からの距離（%）
    take_profit_distance_pct: float  # 現在価格からの距離（%）
    calculation_method: str  # 計算手法名
    confidence_level: float  # 0.0-1.0
    reasoning: List[str]     # 判定理由のリスト

@dataclass
class LeverageRecommendation:
    """レバレッジ推奨結果"""
    recommended_leverage: float
    max_safe_leverage: float
    risk_reward_ratio: float
    stop_loss_price: float
    take_profit_price: float
    confidence_level: float  # 0.0-1.0
    reasoning: List[str]     # 判定理由のリスト
    market_conditions: MarketContext

@dataclass
class TechnicalIndicators:
    """技術指標データ"""
    rsi: float
    macd: float
    macd_signal: float
    bollinger_upper: float
    bollinger_lower: float
    volume_sma: float
    price_sma_20: float
    price_sma_50: float
    atr: float

@dataclass
class OHLCVData:
    """OHLCV標準データ"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    technical_indicators: Optional[TechnicalIndicators] = None

class AnalysisResult:
    """分析結果の基底クラス"""
    def __init__(self, success: bool, message: str = "", data: Dict = None):
        self.success = success
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.now()

class ValidationError(Exception):
    """データ検証エラー"""
    pass

def validate_support_resistance_level(level: SupportResistanceLevel) -> bool:
    """サポレジレベルデータの検証"""
    if level.strength < 0.0 or level.strength > 1.0:
        raise ValidationError(f"強度は0.0-1.0の範囲である必要があります: {level.strength}")
    
    if level.touch_count < 1:
        raise ValidationError(f"タッチ回数は1以上である必要があります: {level.touch_count}")
    
    if level.level_type not in ['support', 'resistance']:
        raise ValidationError(f"レベルタイプは'support'または'resistance'である必要があります: {level.level_type}")
    
    return True

def validate_breakout_prediction(prediction: BreakoutPrediction) -> bool:
    """ブレイクアウト予測データの検証"""
    if not (0.0 <= prediction.breakout_probability <= 1.0):
        raise ValidationError(f"ブレイクアウト確率は0.0-1.0の範囲である必要があります: {prediction.breakout_probability}")
    
    if not (0.0 <= prediction.bounce_probability <= 1.0):
        raise ValidationError(f"反発確率は0.0-1.0の範囲である必要があります: {prediction.bounce_probability}")
    
    # 確率の合計チェック（多少の誤差は許容）
    total_prob = prediction.breakout_probability + prediction.bounce_probability
    if not (0.95 <= total_prob <= 1.05):
        raise ValidationError(f"ブレイクアウト確率と反発確率の合計が1.0に近い必要があります: {total_prob}")
    
    return True

def validate_leverage_recommendation(recommendation: LeverageRecommendation) -> bool:
    """レバレッジ推奨データの検証"""
    if recommendation.recommended_leverage <= 0:
        raise ValidationError(f"推奨レバレッジは正の値である必要があります: {recommendation.recommended_leverage}")
    
    if recommendation.max_safe_leverage < recommendation.recommended_leverage:
        raise ValidationError("最大安全レバレッジは推奨レバレッジ以上である必要があります")
    
    if not (0.0 <= recommendation.confidence_level <= 1.0):
        raise ValidationError(f"信頼度は0.0-1.0の範囲である必要があります: {recommendation.confidence_level}")
    
    return True