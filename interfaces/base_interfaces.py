"""
抽象基底クラス定義 - プラグインシステムの核心

このモジュールは全てのプラグインが実装すべきインターフェースを定義します。
依存性注入とプラグイン交換を可能にします。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
import pandas as pd
from datetime import datetime
from .data_types import (
    SupportResistanceLevel, BreakoutPrediction, BTCCorrelationRisk,
    MarketContext, LeverageRecommendation, StopLossTakeProfitLevels, 
    OHLCVData, AnalysisResult
)

class IDataProvider(ABC):
    """データ取得インターフェース"""
    
    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """OHLCV データを取得"""
        pass
    
    @abstractmethod
    def fetch_current_price(self, symbol: str) -> float:
        """現在価格を取得"""
        pass
    
    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """利用可能なシンボル一覧を取得"""
        pass

class ISupportResistanceAnalyzer(ABC):
    """サポート・レジスタンス分析インターフェース"""
    
    @abstractmethod
    def find_levels(self, data: pd.DataFrame, **kwargs) -> List[SupportResistanceLevel]:
        """
        サポート・レジスタンスレベルを検出
        
        Args:
            data: OHLCV データ
            **kwargs: 分析パラメータ
            
        Returns:
            検出されたレベルのリスト
        """
        pass
    
    @abstractmethod
    def calculate_level_strength(self, level: SupportResistanceLevel, data: pd.DataFrame) -> float:
        """
        レベルの強度を計算
        
        Args:
            level: 分析対象のレベル
            data: OHLCV データ
            
        Returns:
            強度スコア (0.0-1.0)
        """
        pass
    
    @abstractmethod
    def get_nearest_levels(self, current_price: float, levels: List[SupportResistanceLevel],
                          count: int = 5) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """
        現在価格に最も近いサポート・レジスタンスレベルを取得
        
        Args:
            current_price: 現在価格
            levels: 全レベル
            count: 取得する最大数
            
        Returns:
            (サポートレベル, レジスタンスレベル) のタプル
        """
        pass

class IBreakoutPredictor(ABC):
    """ブレイクアウト予測インターフェース"""
    
    @abstractmethod
    def train_model(self, data: pd.DataFrame, levels: List[SupportResistanceLevel]) -> bool:
        """
        予測モデルを訓練
        
        Args:
            data: 訓練用OHLCV データ
            levels: サポレジレベル
            
        Returns:
            訓練成功フラグ
        """
        pass
    
    @abstractmethod
    def predict_breakout(self, current_data: pd.DataFrame, level: SupportResistanceLevel) -> BreakoutPrediction:
        """
        ブレイクアウト確率を予測
        
        Args:
            current_data: 現在の市場データ
            level: 予測対象のレベル
            
        Returns:
            ブレイクアウト予測結果
        """
        pass
    
    @abstractmethod
    def get_model_accuracy(self) -> Dict[str, float]:
        """
        モデルの精度指標を取得
        
        Returns:
            精度指標の辞書
        """
        pass
    
    @abstractmethod
    def save_model(self, filepath: str) -> bool:
        """モデルを保存"""
        pass
    
    @abstractmethod
    def load_model(self, filepath: str) -> bool:
        """モデルを読み込み"""
        pass

class IBTCCorrelationAnalyzer(ABC):
    """BTC相関分析インターフェース"""
    
    @abstractmethod
    def analyze_correlation(self, btc_data: pd.DataFrame, alt_data: pd.DataFrame) -> float:
        """
        BTC-アルトコイン相関を分析
        
        Args:
            btc_data: BTC OHLCV データ
            alt_data: アルトコイン OHLCV データ
            
        Returns:
            相関係数 (-1.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def predict_altcoin_impact(self, symbol: str, btc_drop_pct: float) -> BTCCorrelationRisk:
        """
        BTC下落時のアルトコイン影響を予測
        
        Args:
            symbol: アルトコインシンボル
            btc_drop_pct: BTC下落率（%）
            
        Returns:
            相関リスク評価
        """
        pass
    
    @abstractmethod
    def train_correlation_model(self, symbol: str) -> bool:
        """相関予測モデルを訓練"""
        pass

class IMarketContextAnalyzer(ABC):
    """市場コンテキスト分析インターフェース"""
    
    @abstractmethod
    def analyze_market_phase(self, data: pd.DataFrame, target_timestamp: datetime = None, is_realtime: bool = True) -> MarketContext:
        """
        現在の市場フェーズを分析
        
        Args:
            data: OHLCV データ
            target_timestamp: 分析対象の時刻（バックテストの場合必須）
            is_realtime: リアルタイム分析かどうかのフラグ
            
        Returns:
            市場コンテキスト
        """
        pass
    
    @abstractmethod
    def detect_anomalies(self, data: pd.DataFrame) -> List[Dict]:
        """
        市場異常を検知
        
        Args:
            data: OHLCV データ
            
        Returns:
            異常検知結果のリスト
        """
        pass

class ILeverageDecisionEngine(ABC):
    """レバレッジ判定エンジンインターフェース"""
    
    @abstractmethod
    def calculate_safe_leverage(self, 
                              symbol: str,
                              support_levels: List[SupportResistanceLevel],
                              resistance_levels: List[SupportResistanceLevel],
                              breakout_predictions: List[BreakoutPrediction],
                              btc_correlation_risk: BTCCorrelationRisk,
                              market_context: MarketContext) -> LeverageRecommendation:
        """
        安全なレバレッジを計算
        
        Args:
            symbol: 取引対象シンボル
            support_levels: サポートレベル
            resistance_levels: レジスタンスレベル
            breakout_predictions: ブレイクアウト予測
            btc_correlation_risk: BTC相関リスク
            market_context: 市場コンテキスト
            
        Returns:
            レバレッジ推奨結果
        """
        pass
    
    @abstractmethod
    def calculate_risk_reward(self, entry_price: float, stop_loss: float, take_profit: float) -> float:
        """
        リスクリワード比を計算
        
        Args:
            entry_price: エントリー価格
            stop_loss: 損切り価格
            take_profit: 利確価格
            
        Returns:
            リスクリワード比
        """
        pass

class IHighLeverageBotOrchestrator(ABC):
    """ハイレバボット統括インターフェース"""
    
    @abstractmethod
    def analyze_leverage_opportunity(self, symbol: str, timeframe: str = "1h") -> LeverageRecommendation:
        """
        ハイレバレッジ機会を総合分析
        
        Args:
            symbol: 分析対象シンボル
            timeframe: 時間足
            
        Returns:
            レバレッジ推奨結果
        """
        pass
    
    @abstractmethod
    def set_support_resistance_analyzer(self, analyzer: ISupportResistanceAnalyzer):
        """サポレジ分析器を設定"""
        pass
    
    @abstractmethod
    def set_breakout_predictor(self, predictor: IBreakoutPredictor):
        """ブレイクアウト予測器を設定"""
        pass
    
    @abstractmethod
    def set_btc_correlation_analyzer(self, analyzer: IBTCCorrelationAnalyzer):
        """BTC相関分析器を設定"""
        pass
    
    @abstractmethod
    def set_market_context_analyzer(self, analyzer: IMarketContextAnalyzer):
        """市場コンテキスト分析器を設定"""
        pass
    
    @abstractmethod
    def set_leverage_decision_engine(self, engine: ILeverageDecisionEngine):
        """レバレッジ判定エンジンを設定"""
        pass
    
    @abstractmethod
    def set_stop_loss_take_profit_calculator(self, calculator: 'IStopLossTakeProfitCalculator'):
        """損切り・利確計算器を設定"""
        pass

class IStopLossTakeProfitCalculator(ABC):
    """損切り・利確価格計算インターフェース"""
    
    @abstractmethod
    def calculate_levels(self,
                        current_price: float,
                        leverage: float,
                        support_levels: List[SupportResistanceLevel],
                        resistance_levels: List[SupportResistanceLevel],
                        market_context: MarketContext,
                        position_direction: str = "long") -> StopLossTakeProfitLevels:
        """
        損切り・利確価格を計算
        
        Args:
            current_price: 現在価格
            leverage: レバレッジ倍率
            support_levels: サポートレベル
            resistance_levels: レジスタンスレベル
            market_context: 市場コンテキスト
            position_direction: ポジション方向 ("long" または "short")
            
        Returns:
            損切り・利確レベル
        """
        pass

class PluginRegistry:
    """プラグイン登録管理"""
    
    def __init__(self):
        self._plugins = {}
    
    def register(self, interface_type: type, implementation: object, name: str = "default"):
        """プラグインを登録"""
        if interface_type not in self._plugins:
            self._plugins[interface_type] = {}
        self._plugins[interface_type][name] = implementation
    
    def get(self, interface_type: type, name: str = "default"):
        """プラグインを取得"""
        return self._plugins.get(interface_type, {}).get(name)
    
    def list_plugins(self, interface_type: type) -> List[str]:
        """利用可能なプラグインを一覧表示"""
        return list(self._plugins.get(interface_type, {}).keys())
    
    def unregister(self, interface_type: type, name: str = "default"):
        """プラグインの登録を解除"""
        if interface_type in self._plugins and name in self._plugins[interface_type]:
            del self._plugins[interface_type][name]