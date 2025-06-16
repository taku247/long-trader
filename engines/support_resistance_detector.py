"""
支持線・抵抗線検出エンジン
scalable_analysis_systemで使用するための統合インターフェース
"""

import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from typing import List, Dict, Any, Optional
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interfaces.data_types import SupportResistanceLevel


class SupportResistanceDetector:
    """
    支持線・抵抗線検出エンジン
    既存のsupport_resistance_visualizer.pyの機能を統合
    """
    
    def __init__(self, min_touches: int = 2, tolerance_pct: float = 0.01, fractal_window: int = 5):
        """
        Args:
            min_touches: 有効な支持線・抵抗線と認定するための最小タッチ回数
            tolerance_pct: 価格レベルのクラスタリング許容範囲（%）
            fractal_window: フラクタル検出のウィンドウサイズ
        """
        self.min_touches = min_touches
        self.tolerance_pct = tolerance_pct
        self.fractal_window = fractal_window
    
    def detect_levels_from_ohlcv(self, df: pd.DataFrame, current_price: float) -> tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """
        OHLCVデータから支持線・抵抗線を検出
        
        Args:
            df: OHLCVデータフレーム (columns: timestamp, open, high, low, close, volume)
            current_price: 現在価格
            
        Returns:
            tuple: (支持線リスト, 抵抗線リスト)
        """
        if len(df) < 10:
            raise ValueError(f"データが不足しています。最低10本必要ですが、{len(df)}本しかありません。")
        
        try:
            # フラクタルレベルを検出
            resistance_levels, support_levels = self._detect_fractal_levels(df)
            
            # 価格レベルをクラスタリング
            resistance_clusters = self._cluster_price_levels(resistance_levels)
            support_clusters = self._cluster_price_levels(support_levels)
            
            # 詳細な分析を実行
            resistance_objects = []
            support_objects = []
            
            # 抵抗線の処理
            for cluster in resistance_clusters:
                if len(cluster) >= self.min_touches:
                    level_info = self._calculate_level_details(cluster, df)
                    if level_info and level_info['price'] > current_price:  # 現在価格より上の抵抗線のみ
                        distance_pct = ((level_info['price'] - current_price) / current_price) * 100
                        resistance_objects.append(
                            SupportResistanceLevel(
                                price=level_info['price'],
                                strength=level_info['strength'],
                                touch_count=level_info['touch_count'],
                                level_type='resistance',
                                first_touch=pd.to_datetime(min(level_info.get('timestamps', [df['timestamp'].iloc[0]]))),
                                last_touch=pd.to_datetime(max(level_info.get('timestamps', [df['timestamp'].iloc[-1]]))),
                                volume_at_level=level_info.get('avg_volume', 0),
                                distance_from_current=distance_pct
                            )
                        )
            
            # 支持線の処理
            for cluster in support_clusters:
                if len(cluster) >= self.min_touches:
                    level_info = self._calculate_level_details(cluster, df)
                    if level_info and level_info['price'] < current_price:  # 現在価格より下の支持線のみ
                        distance_pct = ((current_price - level_info['price']) / current_price) * 100
                        support_objects.append(
                            SupportResistanceLevel(
                                price=level_info['price'],
                                strength=level_info['strength'],
                                touch_count=level_info['touch_count'],
                                level_type='support',
                                first_touch=pd.to_datetime(min(level_info.get('timestamps', [df['timestamp'].iloc[0]]))),
                                last_touch=pd.to_datetime(max(level_info.get('timestamps', [df['timestamp'].iloc[-1]]))),
                                volume_at_level=level_info.get('avg_volume', 0),
                                distance_from_current=distance_pct
                            )
                        )
            
            # 強度順でソート
            resistance_objects.sort(key=lambda x: x.strength, reverse=True)
            support_objects.sort(key=lambda x: x.strength, reverse=True)
            
            return support_objects, resistance_objects
            
        except Exception as e:
            raise Exception(f"支持線・抵抗線検出に失敗: {str(e)}")
    
    def _detect_fractal_levels(self, df: pd.DataFrame) -> tuple[List[tuple], List[tuple]]:
        """フラクタル分析による局所最高値・最安値の検出"""
        high = df['high']
        low = df['low']
        
        # 局所最高値（抵抗線候補）
        resistance_indices = argrelextrema(high.values, np.greater, order=self.fractal_window)[0]
        resistance_levels = [(df.iloc[i]['timestamp'], high.iloc[i]) for i in resistance_indices]
        
        # 局所最安値（支持線候補）
        support_indices = argrelextrema(low.values, np.less, order=self.fractal_window)[0]
        support_levels = [(df.iloc[i]['timestamp'], low.iloc[i]) for i in support_indices]
        
        return resistance_levels, support_levels
    
    def _cluster_price_levels(self, levels: List[tuple]) -> List[List[tuple]]:
        """近い価格レベルをクラスタリング"""
        if not levels:
            return []
        
        # 価格でソート
        sorted_levels = sorted(levels, key=lambda x: x[1])
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for i in range(1, len(sorted_levels)):
            current_price = sorted_levels[i][1]
            cluster_avg = np.mean([level[1] for level in current_cluster])
            
            # 許容範囲内なら同じクラスタに追加
            if abs(current_price - cluster_avg) / cluster_avg <= self.tolerance_pct:
                current_cluster.append(sorted_levels[i])
            else:
                # 新しいクラスタを開始
                clusters.append(current_cluster)
                current_cluster = [sorted_levels[i]]
        
        clusters.append(current_cluster)
        return clusters
    
    def _calculate_level_details(self, cluster: List[tuple], df: pd.DataFrame, window: int = 10) -> Optional[Dict[str, Any]]:
        """各レベルの詳細情報を計算"""
        if len(cluster) < 1:
            return None
        
        touch_count = len(cluster)
        level_price = np.mean([level[1] for level in cluster])
        timestamps = [level[0] for level in cluster]
        
        # 反発の強さと出来高を計算
        bounce_strengths = []
        volume_spikes = []
        
        for timestamp in timestamps:
            try:
                idx = df[df['timestamp'] == timestamp].index[0]
                start_idx = max(0, idx - window//2)
                end_idx = min(len(df), idx + window//2 + 1)
                
                local_data = df.iloc[start_idx:end_idx]
                if len(local_data) > 0:
                    # 反発強度計算
                    high_range = local_data['high'].max() - local_data['high'].min()
                    low_range = local_data['low'].max() - local_data['low'].min()
                    price_range = max(high_range, low_range)
                    bounce_strength = price_range / level_price if level_price > 0 else 0
                    bounce_strengths.append(bounce_strength)
                    
                    # 出来高スパイク計算
                    touch_volume = df.iloc[idx]['volume']
                    avg_volume = df['volume'].rolling(window=20).mean().iloc[idx]
                    volume_spike = touch_volume / avg_volume if avg_volume > 0 else 1
                    volume_spikes.append(volume_spike)
            except:
                continue
        
        avg_bounce = np.mean(bounce_strengths) if bounce_strengths else 0
        avg_volume_spike = np.mean(volume_spikes) if volume_spikes else 1
        
        # 時間的要素
        if len(timestamps) > 1:
            time_span = (pd.to_datetime(max(timestamps)) - pd.to_datetime(min(timestamps))).total_seconds() / 3600
            recency = (df['timestamp'].max() - pd.to_datetime(max(timestamps))).total_seconds() / 3600
        else:
            time_span = 0
            recency = float('inf')
        
        # 総合強度スコア計算
        touch_weight = 3
        bounce_weight = 50
        time_weight = 0.05
        recency_weight = 0.02
        volume_weight = 10
        
        raw_strength = (touch_count * touch_weight + 
                       avg_bounce * bounce_weight + 
                       time_span * time_weight - 
                       recency * recency_weight +
                       avg_volume_spike * volume_weight)
        
        # 0.0-1.0の範囲に正規化
        strength = min(max(raw_strength / 200.0, 0.0), 1.0)
        
        return {
            'price': level_price,
            'strength': strength,
            'touch_count': touch_count,
            'avg_bounce': avg_bounce,
            'time_span': time_span,
            'recency': recency,
            'timestamps': timestamps,
            'avg_volume': np.mean([df.iloc[df[df['timestamp'] == ts].index[0]]['volume'] for ts in timestamps if len(df[df['timestamp'] == ts]) > 0]) if timestamps else 0
        }
    
    def get_nearest_levels(self, support_levels: List[SupportResistanceLevel], 
                          resistance_levels: List[SupportResistanceLevel], 
                          current_price: float, max_count: int = 3) -> tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """
        現在価格に最も近い支持線・抵抗線を取得
        
        Args:
            support_levels: 支持線リスト
            resistance_levels: 抵抗線リスト
            current_price: 現在価格
            max_count: 最大取得数
            
        Returns:
            tuple: (最寄り支持線リスト, 最寄り抵抗線リスト)
        """
        # 現在価格より下の支持線（価格の近い順）
        valid_supports = [s for s in support_levels if s.price < current_price]
        valid_supports.sort(key=lambda x: abs(current_price - x.price))
        nearest_supports = valid_supports[:max_count]
        
        # 現在価格より上の抵抗線（価格の近い順）
        valid_resistances = [r for r in resistance_levels if r.price > current_price]
        valid_resistances.sort(key=lambda x: abs(x.price - current_price))
        nearest_resistances = valid_resistances[:max_count]
        
        return nearest_supports, nearest_resistances


def test_support_resistance_detector():
    """支持線・抵抗線検出のテスト関数"""
    print("=== 支持線・抵抗線検出テスト ===")
    
    # サンプルOHLCVデータを生成
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=1000, freq='1h')
    
    # トレンドのある価格データを生成
    base_price = 50000
    trend = np.linspace(0, 5000, 1000)  # 上昇トレンド
    noise = np.random.normal(0, 1000, 1000)  # ノイズ
    prices = base_price + trend + noise
    
    # OHLCV データフレーム作成
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.normal(0, 100, 1000),
        'high': prices + np.abs(np.random.normal(500, 200, 1000)),
        'low': prices - np.abs(np.random.normal(500, 200, 1000)),
        'close': prices,
        'volume': np.random.uniform(1000000, 5000000, 1000)
    })
    
    current_price = prices[-1]
    print(f"現在価格: {current_price:.2f}")
    
    # 検出器を初期化
    detector = SupportResistanceDetector(min_touches=2, tolerance_pct=0.01)
    
    try:
        # 支持線・抵抗線を検出
        support_levels, resistance_levels = detector.detect_levels_from_ohlcv(df, current_price)
        
        print(f"検出された支持線: {len(support_levels)}個")
        for i, level in enumerate(support_levels[:5]):  # 上位5個表示
            print(f"  {i+1}. 価格: {level.price:.2f}, 強度: {level.strength:.3f}, タッチ数: {level.touch_count}")
        
        print(f"検出された抵抗線: {len(resistance_levels)}個")
        for i, level in enumerate(resistance_levels[:5]):  # 上位5個表示
            print(f"  {i+1}. 価格: {level.price:.2f}, 強度: {level.strength:.3f}, タッチ数: {level.touch_count}")
        
        # 最寄りレベルを取得
        nearest_supports, nearest_resistances = detector.get_nearest_levels(
            support_levels, resistance_levels, current_price, max_count=3
        )
        
        print(f"\n最寄り支持線 (上位3個):")
        for i, level in enumerate(nearest_supports):
            distance_pct = ((current_price - level.price) / current_price) * 100
            print(f"  {i+1}. 価格: {level.price:.2f} ({distance_pct:.1f}%下), 強度: {level.strength:.3f}")
        
        print(f"最寄り抵抗線 (上位3個):")
        for i, level in enumerate(nearest_resistances):
            distance_pct = ((level.price - current_price) / current_price) * 100
            print(f"  {i+1}. 価格: {level.price:.2f} ({distance_pct:.1f}%上), 強度: {level.strength:.3f}")
        
        print("\n✅ 支持線・抵抗線検出テスト成功!")
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {str(e)}")
        return False


if __name__ == "__main__":
    test_support_resistance_detector()