"""
支持線・抵抗線検出のアダプターパターン実装
既存システムの差し替えを容易にするためのインターフェース層
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import sys
import os
import importlib
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interfaces.data_types import SupportResistanceLevel


class ISupportResistanceProvider(ABC):
    """支持線・抵抗線検出プロバイダーの抽象インターフェース"""
    
    @abstractmethod
    def detect_basic_levels(self, df: pd.DataFrame, min_touches: int = 2) -> List[Dict[str, Any]]:
        """基本的な支持線・抵抗線検出"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """プロバイダー名を取得"""
        pass
    
    @abstractmethod
    def get_provider_version(self) -> str:
        """プロバイダーバージョンを取得"""
        pass


class IMLEnhancementProvider(ABC):
    """ML予測強化プロバイダーの抽象インターフェース"""
    
    @abstractmethod
    def detect_interactions(self, df: pd.DataFrame, levels: List[Dict], distance_threshold: float = 0.02) -> List[Dict]:
        """レベル相互作用の検出"""
        pass
    
    @abstractmethod
    def predict_bounce_probability(self, df: pd.DataFrame, level: Dict) -> float:
        """反発確率の予測"""
        pass
    
    @abstractmethod
    def get_enhancement_name(self) -> str:
        """拡張機能名を取得"""
        pass


class SupportResistanceVisualizerAdapter(ISupportResistanceProvider):
    """support_resistance_visualizer.pyのアダプター"""
    
    def __init__(self):
        self._module = None
        self._load_module()
    
    def _load_module(self):
        """モジュールを動的にロード"""
        try:
            import support_resistance_visualizer as srv
            self._module = srv
        except ImportError as e:
            raise ImportError(f"support_resistance_visualizer.pyの読み込みに失敗: {e}")
    
    def detect_basic_levels(self, df: pd.DataFrame, min_touches: int = 2) -> List[Dict[str, Any]]:
        """基本的な支持線・抵抗線検出"""
        if not self._module:
            raise RuntimeError("support_resistance_visualizer module not loaded")
        
        try:
            levels = self._module.find_all_levels(df, min_touches=min_touches)
            return levels
        except Exception as e:
            raise RuntimeError(f"レベル検出に失敗: {e}")
    
    def get_provider_name(self) -> str:
        return "SupportResistanceVisualizer"
    
    def get_provider_version(self) -> str:
        return "1.0.0"


class SupportResistanceMLAdapter(IMLEnhancementProvider):
    """support_resistance_ml.pyのアダプター"""
    
    def __init__(self):
        self._module = None
        self._load_module()
    
    def _load_module(self):
        """モジュールを動的にロード"""
        try:
            import support_resistance_ml as srml
            self._module = srml
        except ImportError as e:
            raise ImportError(f"support_resistance_ml.pyの読み込みに失敗: {e}")
    
    def detect_interactions(self, df: pd.DataFrame, levels: List[Dict], distance_threshold: float = 0.02) -> List[Dict]:
        """レベル相互作用の検出"""
        if not self._module:
            raise RuntimeError("support_resistance_ml module not loaded")
        
        try:
            interactions = self._module.detect_level_interactions(df, levels, distance_threshold)
            return interactions
        except Exception as e:
            print(f"Warning: ML相互作用検出に失敗: {e}")
            return []
    
    def predict_bounce_probability(self, df: pd.DataFrame, level: Dict) -> float:
        """反発確率の予測"""
        # 簡易実装：過去の相互作用から確率を計算
        try:
            interactions = self.detect_interactions(df, [level])
            if not interactions:
                return 0.5  # デフォルト値
            
            bounce_count = sum(1 for i in interactions if i.get('outcome') == 'bounce')
            total_interactions = len(interactions)
            
            return bounce_count / total_interactions if total_interactions > 0 else 0.5
        except:
            return 0.5
    
    def get_enhancement_name(self) -> str:
        return "SupportResistanceML"


class FlexibleSupportResistanceDetector:
    """
    柔軟な支持線・抵抗線検出器
    プロバイダーの差し替えが容易な設計
    """
    
    def __init__(self, 
                 base_provider: Optional[ISupportResistanceProvider] = None,
                 ml_provider: Optional[IMLEnhancementProvider] = None,
                 min_touches: int = 2, 
                 tolerance_pct: float = 0.01,
                 use_ml_enhancement: bool = True):
        """
        Args:
            base_provider: 基本検出プロバイダー（Noneの場合はデフォルト使用）
            ml_provider: ML強化プロバイダー（Noneの場合はデフォルト使用）
            min_touches: 最小タッチ回数
            tolerance_pct: 許容範囲
            use_ml_enhancement: ML強化を使用するかどうか
        """
        self.min_touches = min_touches
        self.tolerance_pct = tolerance_pct
        self.use_ml_enhancement = use_ml_enhancement
        
        # プロバイダーの初期化
        self._init_providers(base_provider, ml_provider)
    
    def _init_providers(self, base_provider: Optional[ISupportResistanceProvider], 
                       ml_provider: Optional[IMLEnhancementProvider]):
        """プロバイダーを初期化"""
        # 基本プロバイダーの設定
        if base_provider is None:
            try:
                self.base_provider = SupportResistanceVisualizerAdapter()
            except ImportError as e:
                print(f"Warning: デフォルト基本プロバイダーの初期化に失敗: {e}")
                self.base_provider = None
        else:
            self.base_provider = base_provider
        
        # ML強化プロバイダーの設定
        if ml_provider is None and self.use_ml_enhancement:
            try:
                self.ml_provider = SupportResistanceMLAdapter()
            except ImportError as e:
                print(f"Warning: デフォルトML強化プロバイダーの初期化に失敗: {e}")
                self.ml_provider = None
                self.use_ml_enhancement = False
        else:
            self.ml_provider = ml_provider
    
    def set_base_provider(self, provider: ISupportResistanceProvider):
        """基本プロバイダーを変更"""
        self.base_provider = provider
        print(f"基本プロバイダーを変更: {provider.get_provider_name()} v{provider.get_provider_version()}")
    
    def set_ml_provider(self, provider: IMLEnhancementProvider):
        """ML強化プロバイダーを変更"""
        self.ml_provider = provider
        self.use_ml_enhancement = True
        print(f"ML強化プロバイダーを変更: {provider.get_enhancement_name()}")
    
    def disable_ml_enhancement(self):
        """ML強化を無効化"""
        self.use_ml_enhancement = False
        print("ML強化を無効化しました")
    
    def enable_ml_enhancement(self):
        """ML強化を有効化"""
        if self.ml_provider:
            self.use_ml_enhancement = True
            print("ML強化を有効化しました")
        else:
            print("Warning: ML強化プロバイダーが設定されていません")
    
    def detect_levels(self, df: pd.DataFrame, current_price: float) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """
        支持線・抵抗線を検出
        
        Args:
            df: OHLCVデータフレーム
            current_price: 現在価格
            
        Returns:
            tuple: (支持線リスト, 抵抗線リスト)
        """
        if not self.base_provider:
            raise RuntimeError("基本プロバイダーが設定されていません")
        
        try:
            # 1. 基本検出
            print(f"  🔍 基本検出開始: {self.base_provider.get_provider_name()}")
            raw_levels = self.base_provider.detect_basic_levels(df, self.min_touches)
            
            if not raw_levels:
                raise Exception("基本検出で有効なレベルが見つかりませんでした")
            
            print(f"  📊 基本検出完了: {len(raw_levels)}個のレベル")
            
            # 2. ML強化（オプション）
            enhanced_levels = raw_levels
            if self.use_ml_enhancement and self.ml_provider:
                try:
                    print(f"  🤖 ML強化開始: {self.ml_provider.get_enhancement_name()}")
                    enhanced_levels = self._apply_ml_enhancement(df, raw_levels)
                    print(f"  🤖 ML強化完了")
                except Exception as e:
                    print(f"  ⚠️  ML強化失敗、基本検出結果を使用: {e}")
                    enhanced_levels = raw_levels
            
            # 3. SupportResistanceLevelオブジェクトに変換
            support_objects, resistance_objects = self._convert_to_level_objects(
                enhanced_levels, df, current_price
            )
            
            print(f"  ✅ 検出完了: 支持線{len(support_objects)}個, 抵抗線{len(resistance_objects)}個")
            
            return support_objects, resistance_objects
            
        except Exception as e:
            raise Exception(f"支持線・抵抗線検出に失敗: {str(e)}")
    
    def _apply_ml_enhancement(self, df: pd.DataFrame, levels: List[Dict]) -> List[Dict]:
        """ML強化を適用"""
        enhanced_levels = []
        
        for level in levels:
            try:
                # ML予測を追加
                bounce_probability = self.ml_provider.predict_bounce_probability(df, level)
                
                # レベル情報を拡張
                enhanced_level = level.copy()
                enhanced_level['ml_bounce_probability'] = bounce_probability
                enhanced_level['ml_enhanced'] = True
                
                # 強度をML予測で調整
                if 'strength' in enhanced_level:
                    original_strength = enhanced_level['strength']
                    ml_adjusted_strength = original_strength * (0.5 + 0.5 * bounce_probability)
                    enhanced_level['ml_adjusted_strength'] = ml_adjusted_strength
                
                enhanced_levels.append(enhanced_level)
                
            except Exception as e:
                print(f"  ⚠️  レベル {level.get('price', 'N/A')} のML強化失敗: {e}")
                enhanced_levels.append(level)  # 元のレベルを使用
        
        return enhanced_levels
    
    def _convert_to_level_objects(self, levels: List[Dict], df: pd.DataFrame, current_price: float) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """レベル辞書をSupportResistanceLevelオブジェクトに変換"""
        support_objects = []
        resistance_objects = []
        
        for level in levels:
            try:
                level_obj = self._create_level_object(level, df, current_price)
                if level_obj:
                    if level['type'] == 'support' and level_obj.price < current_price:
                        support_objects.append(level_obj)
                    elif level['type'] == 'resistance' and level_obj.price > current_price:
                        resistance_objects.append(level_obj)
            except Exception as e:
                print(f"  ⚠️  レベル変換エラー: {e}")
                continue
        
        # 強度順でソート
        support_objects.sort(key=lambda x: getattr(x, 'ml_adjusted_strength', x.strength), reverse=True)
        resistance_objects.sort(key=lambda x: getattr(x, 'ml_adjusted_strength', x.strength), reverse=True)
        
        return support_objects, resistance_objects
    
    def _create_level_object(self, level_dict: Dict, df: pd.DataFrame, current_price: float) -> Optional[SupportResistanceLevel]:
        """レベル辞書からSupportResistanceLevelオブジェクトを作成"""
        try:
            level_price = level_dict['price']
            timestamps = level_dict.get('timestamps', [])
            
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
            
            # 強度の決定（ML調整済みがあればそれを使用）
            strength = level_dict.get('ml_adjusted_strength', level_dict.get('strength', 0.5))
            
            level_obj = SupportResistanceLevel(
                price=level_price,
                strength=strength,
                touch_count=level_dict.get('touch_count', 1),
                level_type=level_dict['type'],
                first_touch=first_touch,
                last_touch=last_touch,
                volume_at_level=volume_at_level,
                distance_from_current=distance_pct
            )
            
            # ML関連の追加属性を設定
            if 'ml_bounce_probability' in level_dict:
                setattr(level_obj, 'ml_bounce_probability', level_dict['ml_bounce_probability'])
            if 'ml_enhanced' in level_dict:
                setattr(level_obj, 'ml_enhanced', level_dict['ml_enhanced'])
            
            return level_obj
            
        except Exception as e:
            print(f"  ⚠️  レベルオブジェクト作成エラー: {e}")
            return None
    
    def get_provider_info(self) -> Dict[str, str]:
        """現在のプロバイダー情報を取得"""
        info = {}
        
        if self.base_provider:
            info['base_provider'] = f"{self.base_provider.get_provider_name()} v{self.base_provider.get_provider_version()}"
        else:
            info['base_provider'] = "None"
        
        if self.use_ml_enhancement and self.ml_provider:
            info['ml_provider'] = self.ml_provider.get_enhancement_name()
        else:
            info['ml_provider'] = "Disabled"
        
        info['ml_enhancement_enabled'] = str(self.use_ml_enhancement)
        
        return info


def test_flexible_detector():
    """柔軟な検出器のテスト"""
    print("=== 柔軟な支持線・抵抗線検出器テスト ===")
    
    # サンプルOHLCVデータを生成
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=500, freq='1h')
    
    base_price = 50000
    trend = np.linspace(0, 3000, 500)
    noise = np.random.normal(0, 500, 500)
    prices = base_price + trend + noise
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.normal(0, 50, 500),
        'high': prices + np.abs(np.random.normal(150, 80, 500)),
        'low': prices - np.abs(np.random.normal(150, 80, 500)),
        'close': prices,
        'volume': np.random.uniform(1000000, 3000000, 500)
    })
    
    current_price = prices[-1]
    print(f"現在価格: {current_price:.2f}")
    
    try:
        # 1. デフォルト設定でのテスト
        print("\n1. デフォルト設定での検出テスト:")
        detector = FlexibleSupportResistanceDetector()
        
        provider_info = detector.get_provider_info()
        print(f"   基本プロバイダー: {provider_info['base_provider']}")
        print(f"   MLプロバイダー: {provider_info['ml_provider']}")
        print(f"   ML強化: {provider_info['ml_enhancement_enabled']}")
        
        support_levels, resistance_levels = detector.detect_levels(df, current_price)
        
        print(f"   支持線: {len(support_levels)}個")
        for i, level in enumerate(support_levels[:2]):
            ml_prob = getattr(level, 'ml_bounce_probability', 0)
            print(f"     {i+1}. 価格: {level.price:.2f}, 強度: {level.strength:.3f}, ML: {ml_prob:.3f}")
        
        print(f"   抵抗線: {len(resistance_levels)}個")
        for i, level in enumerate(resistance_levels[:2]):
            ml_prob = getattr(level, 'ml_bounce_probability', 0)
            print(f"     {i+1}. 価格: {level.price:.2f}, 強度: {level.strength:.3f}, ML: {ml_prob:.3f}")
        
        # 2. ML強化無効化テスト
        print("\n2. ML強化無効化テスト:")
        detector.disable_ml_enhancement()
        
        support_levels_no_ml, resistance_levels_no_ml = detector.detect_levels(df, current_price)
        
        print(f"   ML無し - 支持線: {len(support_levels_no_ml)}個, 抵抗線: {len(resistance_levels_no_ml)}個")
        
        # 3. ML強化再有効化テスト
        print("\n3. ML強化再有効化テスト:")
        detector.enable_ml_enhancement()
        
        print("✅ 柔軟な検出器テスト成功!")
        print("\n実装の特徴:")
        print("  🔄 プロバイダーの動的差し替えが可能")
        print("  🎛️ ML強化のオン/オフ切り替えが可能")
        print("  📦 既存モジュールのアダプターパターン実装")
        print("  🛡️ エラー耐性（一部プロバイダーが失敗しても継続）")
        print("  📊 プロバイダー情報の透明性")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_flexible_detector()