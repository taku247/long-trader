"""
システム全体のデフォルト値管理

全戦略・全時間足で使用するデフォルト値を1箇所で管理し、
設定値の統一性を保つためのクラス。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


class DefaultsManager:
    """システムデフォルト値管理クラス"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """シングルトンパターン"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初期化（シングルトン）"""
        if DefaultsManager._initialized:
            return
        
        self.config_file = self._get_default_config_path()
        self.defaults = {}
        self.load_defaults()
        DefaultsManager._initialized = True
    
    def _get_default_config_path(self) -> str:
        """デフォルト設定ファイルパスを取得"""
        current_dir = Path(__file__).parent
        return str(current_dir / "defaults.json")
    
    def load_defaults(self) -> None:
        """デフォルト値を読み込み"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.defaults = json.load(f)
            print(f"✅ システムデフォルト値を読み込み: {self.config_file}")
        except FileNotFoundError:
            print(f"❌ デフォルト設定ファイルが見つかりません: {self.config_file}")
            self._create_fallback_defaults()
        except json.JSONDecodeError as e:
            print(f"❌ デフォルト設定ファイルのJSON形式が不正: {e}")
            self._create_fallback_defaults()
        except Exception as e:
            print(f"❌ デフォルト設定読み込みエラー: {e}")
            self._create_fallback_defaults()
    
    def _create_fallback_defaults(self) -> None:
        """フォールバックデフォルト値を作成"""
        self.defaults = {
            "entry_conditions": {
                "min_risk_reward": 1.2,
                "min_leverage": 3.0,
                "min_confidence": 0.5
            }
        }
        print("⚠️ フォールバックデフォルト値を使用")
    
    def get_min_risk_reward(self) -> float:
        """min_risk_rewardのデフォルト値を取得"""
        return self.defaults.get('entry_conditions', {}).get('min_risk_reward', 1.2)
    
    def get_min_leverage(self) -> float:
        """min_leverageのデフォルト値を取得"""
        return self.defaults.get('entry_conditions', {}).get('min_leverage', 3.0)
    
    def get_min_confidence(self) -> float:
        """min_confidenceのデフォルト値を取得"""
        return self.defaults.get('entry_conditions', {}).get('min_confidence', 0.5)
    
    def get_entry_conditions_defaults(self) -> Dict[str, float]:
        """エントリー条件のデフォルト値辞書を取得"""
        return {
            'min_risk_reward': self.get_min_risk_reward(),
            'min_leverage': self.get_min_leverage(),
            'min_confidence': self.get_min_confidence()
        }
    
    def resolve_defaults_in_config(self, config: Dict) -> Dict:
        """
        設定辞書内の"use_default"マーカーを実際のデフォルト値に解決
        
        Args:
            config: 設定辞書（"use_default"文字列を含む可能性）
            
        Returns:
            解決済み設定辞書
        """
        import copy
        resolved_config = copy.deepcopy(config)
        
        def resolve_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if value == "use_default":
                        if key == "min_risk_reward":
                            obj[key] = self.get_min_risk_reward()
                        elif key == "min_leverage":
                            obj[key] = self.get_min_leverage()
                        elif key == "min_confidence":
                            obj[key] = self.get_min_confidence()
                    else:
                        resolve_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    resolve_recursive(item)
        
        resolve_recursive(resolved_config)
        return resolved_config
    
    def print_defaults_summary(self) -> None:
        """デフォルト値サマリーを表示"""
        print("\n📊 システムデフォルト値")
        print("=" * 40)
        print(f"🎯 エントリー条件:")
        print(f"   💪 最小レバレッジ: {self.get_min_leverage()}x")
        print(f"   🎪 最小信頼度: {self.get_min_confidence() * 100:.0f}%")
        print(f"   ⚖️ 最小RR比: {self.get_min_risk_reward()}")
        print("=" * 40)


# グローバルインスタンス（シングルトン）
defaults_manager = DefaultsManager()


def get_default_min_risk_reward() -> float:
    """グローバル関数：min_risk_rewardデフォルト値取得"""
    return defaults_manager.get_min_risk_reward()


def get_default_min_leverage() -> float:
    """グローバル関数：min_leverageデフォルト値取得"""
    return defaults_manager.get_min_leverage()


def get_default_min_confidence() -> float:
    """グローバル関数：min_confidenceデフォルト値取得"""
    return defaults_manager.get_min_confidence()


def get_default_entry_conditions() -> Dict[str, float]:
    """グローバル関数：エントリー条件デフォルト値辞書取得"""
    return defaults_manager.get_entry_conditions_defaults()


if __name__ == "__main__":
    # テスト実行
    defaults_manager.print_defaults_summary()