"""
高度な支持線・抵抗線検出エンジン
既存のsupport_resistance_visualizer.pyとsupport_resistance_ml.pyを活用
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interfaces.data_types import SupportResistanceLevel
from support_resistance_visualizer import find_all_levels, calculate_level_details
from support_resistance_ml import detect_level_interactions, calculate_approach_features, prepare_training_data, train_models


class AdvancedSupportResistanceDetector:
    """
    高度な支持線・抵抗線検出エンジン
    ML予測とビジュアライゼーション機能を統合
    """
    
    def __init__(self, min_touches: int = 2, tolerance_pct: float = 0.01, 
                 use_ml_prediction: bool = True, prediction_confidence_threshold: float = 0.6):
        """
        Args:
            min_touches: 有効な支持線・抵抗線と認定するための最小タッチ回数
            tolerance_pct: 価格レベルのクラスタリング許容範囲（%）
            use_ml_prediction: ML予測を使用するかどうか
            prediction_confidence_threshold: 予測の信頼度閾値
        """
        self.min_touches = min_touches
        self.tolerance_pct = tolerance_pct
        self.use_ml_prediction = use_ml_prediction
        self.prediction_confidence_threshold = prediction_confidence_threshold
        
        # MLモデルのキャッシュ
        self._ml_models = {}
    
    def detect_advanced_levels(self, df: pd.DataFrame, current_price: float) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """
        高度な支持線・抵抗線検出
        既存のsupport_resistance_visualizer.pyの機能を活用
        
        Args:
            df: OHLCVデータフレーム (columns: timestamp, open, high, low, close, volume)
            current_price: 現在価格
            
        Returns:
            tuple: (支持線リスト, 抵抗線リスト)
        """
        if len(df) < 20:
            raise ValueError(f"データが不足しています。最低20本必要ですが、{len(df)}本しかありません。")
        
        try:
            print(f"  🔍 高度な支持線・抵抗線検出を開始...")
            
            # 1. 既存のfind_all_levels関数を使用してレベル検出
            all_levels = find_all_levels(df, min_touches=self.min_touches)
            
            if not all_levels:
                raise Exception("有効な支持線・抵抗線が検出されませんでした。")
            
            print(f"  📊 初期検出: {len(all_levels)}個のレベル")
            
            # 2. 現在価格で支持線・抵抗線を分類
            support_objects = []
            resistance_objects = []
            
            for level in all_levels:
                level_price = level['price']
                
                # SupportResistanceLevelオブジェクトに変換
                level_obj = self._convert_to_level_object(level, df, current_price)
                
                if level_obj:
                    if level['type'] == 'support' and level_price < current_price:
                        support_objects.append(level_obj)
                    elif level['type'] == 'resistance' and level_price > current_price:
                        resistance_objects.append(level_obj)
            
            print(f"  📊 分類完了: 支持線{len(support_objects)}個, 抵抗線{len(resistance_objects)}個")
            
            # 3. ML予測による強度調整（オプション）
            if self.use_ml_prediction and len(df) > 50:
                try:
                    support_objects = self._enhance_with_ml_predictions(df, support_objects, 'support')
                    resistance_objects = self._enhance_with_ml_predictions(df, resistance_objects, 'resistance')
                    print(f"  🤖 ML予測による強度調整完了")
                except Exception as ml_error:
                    print(f"  ⚠️  ML予測スキップ: {str(ml_error)}")
            
            # 4. 強度とML予測スコアで最終ソート
            support_objects.sort(key=lambda x: (x.strength, getattr(x, 'ml_bounce_probability', 0)), reverse=True)
            resistance_objects.sort(key=lambda x: (x.strength, getattr(x, 'ml_bounce_probability', 0)), reverse=True)
            
            # 5. 最も重要なレベルのみ選択（上位5個まで）
            support_objects = support_objects[:5]
            resistance_objects = resistance_objects[:5]
            
            print(f"  ✅ 最終選択: 支持線{len(support_objects)}個, 抵抗線{len(resistance_objects)}個")
            
            return support_objects, resistance_objects
            
        except Exception as e:
            raise Exception(f"高度な支持線・抵抗線検出に失敗: {str(e)}")
    
    def _convert_to_level_object(self, level_dict: Dict[str, Any], df: pd.DataFrame, current_price: float) -> Optional[SupportResistanceLevel]:
        """レベル辞書をSupportResistanceLevelオブジェクトに変換"""
        try:
            level_price = level_dict['price']
            timestamps = level_dict.get('timestamps', [])
            
            if not timestamps:
                return None
            
            # 距離の計算
            if level_dict['type'] == 'support':
                distance_pct = ((current_price - level_price) / current_price) * 100
            else:
                distance_pct = ((level_price - current_price) / current_price) * 100
            
            # タイムスタンプの処理
            first_touch = pd.to_datetime(min(timestamps)) if timestamps else df['timestamp'].iloc[0]
            last_touch = pd.to_datetime(max(timestamps)) if timestamps else df['timestamp'].iloc[-1]
            
            # 出来高の計算
            volume_at_level = level_dict.get('avg_volume', 0)
            if volume_at_level == 0 and timestamps:
                # 出来高を再計算
                volumes = []
                for ts in timestamps:
                    matching_rows = df[df['timestamp'] == ts]
                    if not matching_rows.empty:
                        volumes.append(matching_rows.iloc[0]['volume'])
                volume_at_level = np.mean(volumes) if volumes else 0
            
            return SupportResistanceLevel(
                price=level_price,
                strength=level_dict['strength'],
                touch_count=level_dict['touch_count'],
                level_type=level_dict['type'],
                first_touch=first_touch,
                last_touch=last_touch,
                volume_at_level=volume_at_level,
                distance_from_current=distance_pct
            )
            
        except Exception as e:
            print(f"  ⚠️  レベル変換エラー: {str(e)}")
            return None
    
    def _enhance_with_ml_predictions(self, df: pd.DataFrame, levels: List[SupportResistanceLevel], level_type: str) -> List[SupportResistanceLevel]:
        """
        ML予測による支持線・抵抗線の強度調整
        support_resistance_ml.pyの機能を活用
        """
        try:
            # レベル間の相互作用を検出
            level_dicts = []
            for level in levels:
                level_dicts.append({
                    'price': level.price,
                    'strength': level.strength,
                    'touch_count': level.touch_count,
                    'type': level.level_type
                })
            
            # 相互作用の履歴を取得
            interactions = detect_level_interactions(df, level_dicts, distance_threshold=0.02)
            
            if not interactions:
                return levels
            
            # 各レベルにML予測スコアを追加
            enhanced_levels = []
            for level in levels:
                # このレベルに関連する相互作用を抽出
                level_interactions = [
                    interaction for interaction in interactions 
                    if abs(interaction['level_price'] - level.price) / level.price < 0.01
                ]
                
                if level_interactions:
                    # 反発確率を計算
                    bounce_count = sum(1 for i in level_interactions if i['outcome'] == 'bounce')
                    total_interactions = len(level_interactions)
                    bounce_probability = bounce_count / total_interactions if total_interactions > 0 else 0.5
                    
                    # 強度調整
                    ml_adjusted_strength = level.strength * (0.5 + 0.5 * bounce_probability)
                    
                    # オブジェクトに追加属性を設定
                    enhanced_level = level
                    enhanced_level.strength = ml_adjusted_strength
                    setattr(enhanced_level, 'ml_bounce_probability', bounce_probability)
                    setattr(enhanced_level, 'ml_interaction_count', total_interactions)
                    
                    enhanced_levels.append(enhanced_level)
                else:
                    enhanced_levels.append(level)
            
            return enhanced_levels
            
        except Exception as e:
            print(f"  ⚠️  ML予測エラー: {str(e)}")
            return levels
    
    def get_critical_levels(self, support_levels: List[SupportResistanceLevel], 
                           resistance_levels: List[SupportResistanceLevel], 
                           current_price: float, max_count: int = 2) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """
        最も重要な支持線・抵抗線を取得
        距離と強度の両方を考慮した選択
        
        Args:
            support_levels: 支持線リスト
            resistance_levels: 抵抗線リスト
            current_price: 現在価格
            max_count: 最大取得数
            
        Returns:
            tuple: (重要支持線リスト, 重要抵抗線リスト)
        """
        def calculate_importance_score(level: SupportResistanceLevel, current_price: float) -> float:
            """重要度スコアを計算（強度と距離の組み合わせ）"""
            # 距離スコア（近いほど高い、ただし5%以内）
            distance_pct = abs(level.price - current_price) / current_price
            if distance_pct > 0.05:  # 5%以上離れている場合は重要度下げる
                distance_score = 0.1
            else:
                distance_score = 1.0 - (distance_pct / 0.05)  # 0.0-1.0
            
            # 強度スコア
            strength_score = level.strength
            
            # ML予測スコア（ある場合）
            ml_score = getattr(level, 'ml_bounce_probability', 0.5)
            
            # 総合スコア
            importance = (strength_score * 0.4 + 
                         distance_score * 0.4 + 
                         ml_score * 0.2)
            
            return importance
        
        # 重要度スコアで選択
        critical_supports = []
        for level in support_levels:
            if level.price < current_price:
                score = calculate_importance_score(level, current_price)
                setattr(level, 'importance_score', score)
                critical_supports.append(level)
        
        critical_resistances = []
        for level in resistance_levels:
            if level.price > current_price:
                score = calculate_importance_score(level, current_price)
                setattr(level, 'importance_score', score)
                critical_resistances.append(level)
        
        # 重要度順でソートして上位を選択
        critical_supports.sort(key=lambda x: getattr(x, 'importance_score', 0), reverse=True)
        critical_resistances.sort(key=lambda x: getattr(x, 'importance_score', 0), reverse=True)
        
        return critical_supports[:max_count], critical_resistances[:max_count]


def test_advanced_support_resistance_detector():
    """高度な支持線・抵抗線検出のテスト"""
    print("=== 高度な支持線・抵抗線検出テスト ===")
    
    # サンプルOHLCVデータを生成
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=1000, freq='1h')
    
    # 明確なサポート・レジスタンスパターンを作成
    base_price = 50000
    trend = np.linspace(0, 3000, 1000)
    noise = np.random.normal(0, 500, 1000)
    prices = base_price + trend + noise
    
    # 特定レベルでの反発を強制
    support_level = 51000
    resistance_level = 54000
    
    for i in range(len(prices)):
        if prices[i] < support_level and np.random.random() < 0.7:
            prices[i] = support_level + np.random.uniform(0, 100)
        elif prices[i] > resistance_level and np.random.random() < 0.7:
            prices[i] = resistance_level - np.random.uniform(0, 100)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.normal(0, 50, 1000),
        'high': prices + np.abs(np.random.normal(200, 100, 1000)),
        'low': prices - np.abs(np.random.normal(200, 100, 1000)),
        'close': prices,
        'volume': np.random.uniform(1000000, 3000000, 1000)
    })
    
    current_price = prices[-1]
    print(f"現在価格: {current_price:.2f}")
    
    try:
        # 高度な検出器を初期化
        detector = AdvancedSupportResistanceDetector(
            min_touches=2, 
            tolerance_pct=0.01, 
            use_ml_prediction=True,
            prediction_confidence_threshold=0.6
        )
        
        # 支持線・抵抗線を検出
        support_levels, resistance_levels = detector.detect_advanced_levels(df, current_price)
        
        print(f"\n検出された支持線: {len(support_levels)}個")
        for i, level in enumerate(support_levels):
            ml_prob = getattr(level, 'ml_bounce_probability', 0)
            print(f"  {i+1}. 価格: {level.price:.2f}, 強度: {level.strength:.3f}, ML反発確率: {ml_prob:.3f}")
        
        print(f"検出された抵抗線: {len(resistance_levels)}個")
        for i, level in enumerate(resistance_levels):
            ml_prob = getattr(level, 'ml_bounce_probability', 0)
            print(f"  {i+1}. 価格: {level.price:.2f}, 強度: {level.strength:.3f}, ML反発確率: {ml_prob:.3f}")
        
        # 重要レベルを取得
        critical_supports, critical_resistances = detector.get_critical_levels(
            support_levels, resistance_levels, current_price, max_count=2
        )
        
        print(f"\n最重要支持線:")
        for i, level in enumerate(critical_supports):
            importance = getattr(level, 'importance_score', 0)
            distance_pct = ((current_price - level.price) / current_price) * 100
            print(f"  {i+1}. 価格: {level.price:.2f} ({distance_pct:.1f}%下), 重要度: {importance:.3f}")
        
        print(f"最重要抵抗線:")
        for i, level in enumerate(critical_resistances):
            importance = getattr(level, 'importance_score', 0)
            distance_pct = ((level.price - current_price) / current_price) * 100
            print(f"  {i+1}. 価格: {level.price:.2f} ({distance_pct:.1f}%上), 重要度: {importance:.3f}")
        
        print("\n✅ 高度な支持線・抵抗線検出テスト成功!")
        print("機能:")
        print("  - 既存のsupport_resistance_visualizer.pyを活用")
        print("  - support_resistance_ml.pyのML予測を統合")
        print("  - 重要度スコアによる自動選択")
        print("  - ML反発確率による強度調整")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_advanced_support_resistance_detector()