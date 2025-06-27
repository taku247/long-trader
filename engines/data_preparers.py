#!/usr/bin/env python3
"""
データ準備クラス群

実際のOHLCVデータを使用したPreparedDataクラスの実装
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)


class RealPreparedData:
    """
    実際のOHLCVデータを使用したPreparedDataクラス
    
    FilteringFrameworkで使用するため、必要なメソッドを実装
    """
    
    def __init__(self, ohlcv_data: pd.DataFrame):
        """
        初期化
        
        Args:
            ohlcv_data: OHLCVデータのDataFrame
                       必須カラム: timestamp, open, high, low, close, volume
        """
        # データ検証
        self._validate_data(ohlcv_data)
        
        # データのコピーを保持（元データの変更を防ぐ）
        self.ohlcv_data = ohlcv_data.copy()
        
        # タイムスタンプでソート（昇順）
        if not self.ohlcv_data['timestamp'].is_monotonic_increasing:
            self.ohlcv_data = self.ohlcv_data.sort_values('timestamp').reset_index(drop=True)
        
        # インデックス作成（高速アクセス用）
        self._create_timestamp_index()
        
        # キャッシュ（計算済み指標を保存）
        self._cache = {}
    
    def _validate_data(self, ohlcv_data: pd.DataFrame):
        """データ検証"""
        if ohlcv_data.empty:
            raise ValueError("OHLCVデータが空です")
        
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = set(required_columns) - set(ohlcv_data.columns)
        
        if missing_columns:
            raise ValueError(f"必須カラムが不足しています: {missing_columns}")
    
    def _create_timestamp_index(self):
        """高速アクセス用のタイムスタンプインデックス作成"""
        self.timestamp_index = pd.DatetimeIndex(self.ohlcv_data['timestamp'])
    
    def get_price_at(self, eval_time: datetime) -> float:
        """
        指定時点の価格（開始価格）を取得
        
        Args:
            eval_time: 評価時点
            
        Returns:
            開始価格（open価格）
        """
        # 範囲チェック
        if eval_time < self.ohlcv_data['timestamp'].iloc[0]:
            raise ValueError(f"評価時点がデータ範囲より前です: {eval_time}")
        if eval_time > self.ohlcv_data['timestamp'].iloc[-1]:
            raise ValueError(f"評価時点がデータ範囲より後です: {eval_time}")
        
        # 最も近い時点のインデックスを検索
        idx = self.timestamp_index.get_indexer([eval_time], method='ffill')[0]
        
        # 開始価格を返す（その時点で実際に利用可能な価格）
        return float(self.ohlcv_data.iloc[idx]['open'])
    
    def get_close_price_at(self, eval_time: datetime) -> float:
        """
        指定時点の終値を取得（過去データ分析用）
        
        Args:
            eval_time: 評価時点
            
        Returns:
            終値（close価格）
            
        Note:
            バックテストでは基本的にget_price_at()（open価格）を使用し、
            このメソッドは過去データの分析や支持線・抵抗線計算に使用
        """
        idx = self.timestamp_index.get_indexer([eval_time], method='ffill')[0]
        return float(self.ohlcv_data.iloc[idx]['close'])
    
    def get_volume_at(self, eval_time: datetime) -> float:
        """
        指定時点のボリュームを取得
        
        Args:
            eval_time: 評価時点
            
        Returns:
            ボリューム
        """
        idx = self.timestamp_index.get_indexer([eval_time], method='ffill')[0]
        return float(self.ohlcv_data.iloc[idx]['volume'])
    
    def get_ohlc_at(self, eval_time: datetime) -> Dict[str, float]:
        """
        指定時点のOHLC価格を取得
        
        Args:
            eval_time: 評価時点
            
        Returns:
            OHLC価格の辞書
        """
        idx = self.timestamp_index.get_indexer([eval_time], method='ffill')[0]
        row = self.ohlcv_data.iloc[idx]
        
        return {
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'timestamp': row['timestamp']
        }
    
    def get_ohlcv_until(self, eval_time: datetime, lookback_periods: int = 100) -> List[Dict]:
        """
        指定時点までの過去N期間のOHLCV一覧を取得
        
        Args:
            eval_time: 評価時点
            lookback_periods: 取得する期間数
            
        Returns:
            OHLCV辞書のリスト
        """
        # 評価時点以前のデータをフィルター
        past_data = self.ohlcv_data[self.ohlcv_data['timestamp'] <= eval_time]
        
        # 最新lookback_periods個を取得
        recent_data = past_data.tail(lookback_periods)
        
        # 辞書形式で返す
        return recent_data.to_dict('records')
    
    def get_ohlcv_range(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        指定期間範囲のOHLCV一覧を取得
        
        Args:
            start_time: 開始時点
            end_time: 終了時点
            
        Returns:
            OHLCV辞書のリスト
        """
        mask = (self.ohlcv_data['timestamp'] >= start_time) & (self.ohlcv_data['timestamp'] <= end_time)
        range_data = self.ohlcv_data[mask]
        
        return range_data.to_dict('records')
    
    def get_recent_ohlcv(self, eval_time: datetime, minutes: int = 60) -> List[Dict]:
        """
        評価時点から過去N分間のOHLCV一覧を取得
        
        Args:
            eval_time: 評価時点
            minutes: 取得する分数
            
        Returns:
            OHLCV辞書のリスト
        """
        start_time = eval_time - timedelta(minutes=minutes)
        return self.get_ohlcv_range(start_time, eval_time)
    
    def get_spread_at(self, eval_time: datetime) -> float:
        """
        指定時点のスプレッドを取得（簡易計算）
        
        Args:
            eval_time: 評価時点
            
        Returns:
            スプレッド（比率）
        """
        idx = self.timestamp_index.get_indexer([eval_time], method='ffill')[0]
        row = self.ohlcv_data.iloc[idx]
        
        # High-Lowからスプレッドを推定
        spread = (row['high'] - row['low']) / row['close'] * 0.1  # 10%に調整
        
        return float(spread)
    
    def get_liquidity_score_at(self, eval_time: datetime) -> float:
        """
        指定時点の流動性スコアを取得
        
        Args:
            eval_time: 評価時点
            
        Returns:
            流動性スコア（0-1）
        """
        # 過去1時間のボリュームから流動性を推定
        recent_data = self.get_recent_ohlcv(eval_time, minutes=60)
        
        if not recent_data:
            return 0.5
        
        volumes = [d['volume'] for d in recent_data]
        avg_volume = np.mean(volumes)
        
        # ボリュームベースのスコア計算（正規化）
        # 1M以上で高流動性とみなす
        score = min(avg_volume / 1000000, 1.0)
        
        return float(score)
    
    def get_volatility_at(self, eval_time: datetime, period: int = 20) -> float:
        """
        指定時点のボラティリティを取得
        
        Args:
            eval_time: 評価時点
            period: 計算期間
            
        Returns:
            ボラティリティ（標準偏差）
        """
        # キャッシュチェック
        cache_key = f"volatility_{eval_time}_{period}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 過去N期間のデータ取得
        historical_data = self.get_ohlcv_until(eval_time, period)
        
        if len(historical_data) < 2:
            return 0.01  # デフォルト値
        
        # リターンの計算
        closes = [d['close'] for d in historical_data]
        returns = np.diff(np.log(closes))
        
        # 標準偏差（年率換算）
        volatility = np.std(returns) * np.sqrt(252)  # 日次換算
        
        # キャッシュに保存
        self._cache[cache_key] = float(volatility)
        
        return float(volatility)
    
    def get_atr_at(self, eval_time: datetime, period: int = 14) -> float:
        """
        指定時点のATR（Average True Range）を取得
        
        Args:
            eval_time: 評価時点
            period: 計算期間
            
        Returns:
            ATR値
        """
        # 過去N期間のデータ取得
        historical_data = self.get_ohlcv_until(eval_time, period + 1)
        
        if len(historical_data) < 2:
            return 100.0  # デフォルト値
        
        # True Range計算
        true_ranges = []
        for i in range(1, len(historical_data)):
            high = historical_data[i]['high']
            low = historical_data[i]['low']
            prev_close = historical_data[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        # ATR（単純移動平均）
        atr = np.mean(true_ranges[-period:]) if len(true_ranges) >= period else np.mean(true_ranges)
        
        return float(atr)
    
    def get_moving_average(self, eval_time: datetime, period: int = 20) -> float:
        """
        指定時点の移動平均を取得
        
        Args:
            eval_time: 評価時点
            period: 計算期間
            
        Returns:
            移動平均値
        """
        historical_data = self.get_ohlcv_until(eval_time, period)
        
        if not historical_data:
            return self.get_price_at(eval_time)
        
        closes = [d['close'] for d in historical_data]
        return float(np.mean(closes))
    
    def get_rsi(self, eval_time: datetime, period: int = 14) -> float:
        """
        指定時点のRSIを取得
        
        Args:
            eval_time: 評価時点
            period: 計算期間
            
        Returns:
            RSI値（0-100）
        """
        historical_data = self.get_ohlcv_until(eval_time, period + 1)
        
        if len(historical_data) < period + 1:
            return 50.0  # デフォルト値
        
        # 価格変化の計算
        closes = [d['close'] for d in historical_data]
        deltas = np.diff(closes)
        
        # 上昇・下降の分離
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # 平均利得・平均損失
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        # RSI計算
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def get_vwap(self, eval_time: datetime, period: int = 20) -> float:
        """
        指定時点のVWAP（ボリューム加重平均価格）を取得
        
        Args:
            eval_time: 評価時点
            period: 計算期間
            
        Returns:
            VWAP値
        """
        historical_data = self.get_ohlcv_until(eval_time, period)
        
        if not historical_data:
            return self.get_price_at(eval_time)
        
        # 典型価格 × ボリューム
        pv_sum = 0
        volume_sum = 0
        
        for d in historical_data:
            typical_price = (d['high'] + d['low'] + d['close']) / 3
            pv_sum += typical_price * d['volume']
            volume_sum += d['volume']
        
        if volume_sum == 0:
            return self.get_price_at(eval_time)
        
        vwap = pv_sum / volume_sum
        return float(vwap)
    
    def has_missing_data_around(self, eval_time: datetime, window_minutes: int = 60) -> bool:
        """
        指定時点周辺に欠損データがあるかチェック
        
        Args:
            eval_time: 評価時点
            window_minutes: チェック範囲（分）
            
        Returns:
            欠損データがある場合True
        """
        start_time = eval_time - timedelta(minutes=window_minutes)
        end_time = eval_time + timedelta(minutes=window_minutes)
        
        # 期待されるデータ数（1分足の場合）
        expected_count = window_minutes * 2
        
        # 実際のデータ数
        range_data = self.get_ohlcv_range(start_time, end_time)
        actual_count = len(range_data)
        
        # 80%未満なら欠損ありとみなす
        return actual_count < expected_count * 0.8
    
    def has_price_anomaly_at(self, eval_time: datetime, threshold: float = 0.1) -> bool:
        """
        指定時点で価格異常があるかチェック
        
        Args:
            eval_time: 評価時点
            threshold: 異常判定閾値（10%）
            
        Returns:
            価格異常がある場合True
        """
        # 前後5分のデータを取得
        recent_data = self.get_recent_ohlcv(eval_time, minutes=10)
        
        if len(recent_data) < 2:
            return False
        
        # 急激な価格変動をチェック
        for i in range(1, len(recent_data)):
            price_change = abs(recent_data[i]['close'] - recent_data[i-1]['close']) / recent_data[i-1]['close']
            if price_change > threshold:
                return True
        
        return False
    
    def is_valid(self) -> bool:
        """
        データ全体の有効性チェック
        
        Returns:
            有効な場合True
        """
        # 最小データ数チェック
        if len(self.ohlcv_data) < 100:
            return False
        
        # NULL値チェック
        if self.ohlcv_data.isnull().any().any():
            return False
        
        # 価格の妥当性チェック
        if (self.ohlcv_data['close'] <= 0).any():
            return False
        
        return True
    
    def get_price_change_volatility_at(self, eval_time: datetime) -> float:
        """
        価格変動のボラティリティを取得（Filter用）
        
        Args:
            eval_time: 評価時点
            
        Returns:
            価格変動ボラティリティ
        """
        return self.get_volatility_at(eval_time) * 0.6  # 調整済み値
    
    # ML関連のダミーメソッド（FilteringFramework互換性のため）
    def get_ml_confidence_at(self, eval_time: datetime) -> float:
        """ML信頼度（ダミー）"""
        # 実際のML実装時に置き換え
        return 0.75
    
    def get_ml_prediction_at(self, eval_time: datetime) -> str:
        """ML予測（ダミー）"""
        # 実際のML実装時に置き換え
        return "BUY"
    
    def get_ml_signal_strength_at(self, eval_time: datetime) -> float:
        """MLシグナル強度（ダミー）"""
        # 実際のML実装時に置き換え
        return 0.8