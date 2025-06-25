#!/usr/bin/env python3
"""
レバレッジエンジン設定管理システム

leverage_engine_config.jsonを読み込んで、レバレッジ判定エンジンに
設定値を提供するクラス。設定の変更を容易にし、時間足や銘柄カテゴリに
応じた調整も可能。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import copy

class LeverageConfigManager:
    """レバレッジエンジン設定管理クラス（シングルトン）"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初期化（シングルトン）
        
        Args:
            config_file: 設定ファイルパス（オプション）
        """
        # 既に初期化済みの場合はスキップ
        if LeverageConfigManager._initialized:
            return
        
        self.config_file = config_file or self._get_default_config_path()
        self.config_data = {}
        
        self.load_config()
        LeverageConfigManager._initialized = True
    
    def _get_default_config_path(self) -> str:
        """デフォルト設定ファイルパスを取得"""
        current_dir = Path(__file__).parent
        return str(current_dir / "leverage_engine_config.json")
    
    def load_config(self) -> None:
        """設定ファイルを読み込み"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            print(f"✅ レバレッジエンジン設定を読み込み: {self.config_file}")
        except Exception as e:
            print(f"❌ レバレッジエンジン設定読み込みエラー: {e}")
            # フォールバックではなくエラーを発生させる
            from engines.leverage_decision_engine import InsufficientConfigurationError
            raise InsufficientConfigurationError(
                message=f"レバレッジエンジン設定ファイルの読み込みに失敗: {e}",
                error_type="config_load_failed",
                missing_config="leverage_engine_config.json"
            )
    
    def get_core_constants(self) -> Dict[str, float]:
        """コア定数を取得"""
        core_limits = self.config_data.get('leverage_engine_constants', {}).get('core_limits', {})
        correlation_thresholds = self.config_data.get('leverage_engine_constants', {}).get('correlation_thresholds', {})
        support_resistance = self.config_data.get('leverage_engine_constants', {}).get('support_resistance_criteria', {})
        
        return {
            'max_leverage': core_limits.get('max_leverage', 100.0),
            'min_risk_reward': core_limits.get('min_risk_reward', 0.4),
            'max_drawdown_tolerance': core_limits.get('max_drawdown_tolerance', 0.15),
            'btc_correlation_threshold': correlation_thresholds.get('btc_correlation_threshold', 0.7),
            'min_support_strength': support_resistance.get('min_support_strength', 0.6)
        }
    
    def get_risk_calculation_constants(self) -> Dict[str, float]:
        """リスク計算定数を取得"""
        return copy.deepcopy(
            self.config_data.get('leverage_engine_constants', {}).get('risk_calculation', {})
        )
    
    def get_leverage_scaling_constants(self) -> Dict[str, float]:
        """レバレッジスケーリング定数を取得"""
        return copy.deepcopy(
            self.config_data.get('leverage_engine_constants', {}).get('leverage_scaling', {})
        )
    
    def get_stop_loss_take_profit_constants(self) -> Dict[str, float]:
        """損切り・利確定数を取得"""
        return copy.deepcopy(
            self.config_data.get('leverage_engine_constants', {}).get('stop_loss_take_profit', {})
        )
    
    def get_market_context_constants(self) -> Dict[str, float]:
        """市場コンテキスト定数を取得"""
        return copy.deepcopy(
            self.config_data.get('leverage_engine_constants', {}).get('market_context', {})
        )
    
    def get_data_validation_constants(self) -> Dict[str, float]:
        """データ検証定数を取得"""
        return copy.deepcopy(
            self.config_data.get('leverage_engine_constants', {}).get('data_validation', {})
        )
    
    def get_timeframe_adjustments(self, timeframe: str) -> Dict[str, float]:
        """時間足固有の調整値を取得"""
        adjustments = self.config_data.get('timeframe_specific_adjustments', {}).get(timeframe, {})
        return copy.deepcopy(adjustments)
    
    def get_symbol_category_adjustments(self, category: str) -> Dict[str, float]:
        """銘柄カテゴリ固有の調整値を取得"""
        adjustments = self.config_data.get('symbol_category_adjustments', {}).get(category, {})
        return copy.deepcopy(adjustments)
    
    def get_emergency_limits(self) -> Dict[str, float]:
        """緊急時制限値を取得"""
        return copy.deepcopy(
            self.config_data.get('emergency_limits', {})
        )
    
    def get_adjusted_constants(self, timeframe: str = None, symbol_category: str = None) -> Dict[str, Any]:
        """
        時間足と銘柄カテゴリに応じて調整された定数を取得
        
        Args:
            timeframe: 時間足（例: '1h', '15m'）
            symbol_category: 銘柄カテゴリ（例: 'large_cap', 'small_cap'）
            
        Returns:
            調整済み定数辞書
        """
        # ベース定数を取得
        constants = {
            'core': self.get_core_constants(),
            'risk_calculation': self.get_risk_calculation_constants(),
            'leverage_scaling': self.get_leverage_scaling_constants(),
            'stop_loss_take_profit': self.get_stop_loss_take_profit_constants(),
            'market_context': self.get_market_context_constants(),
            'data_validation': self.get_data_validation_constants(),
            'emergency_limits': self.get_emergency_limits()
        }
        
        # 時間足調整
        if timeframe:
            tf_adjustments = self.get_timeframe_adjustments(timeframe)
            if tf_adjustments:
                # ボラティリティ乗数を適用
                if 'volatility_multiplier' in tf_adjustments:
                    constants['risk_calculation']['volatility_risk_multiplier'] *= tf_adjustments['volatility_multiplier']
                
                # 最大レバレッジ減少を適用
                if 'max_leverage_reduction' in tf_adjustments:
                    reduction = tf_adjustments['max_leverage_reduction']
                    constants['core']['max_leverage'] *= (1.0 + reduction)
                    constants['core']['max_leverage'] = max(1.0, constants['core']['max_leverage'])
        
        # 銘柄カテゴリ調整
        if symbol_category:
            cat_adjustments = self.get_symbol_category_adjustments(symbol_category)
            if cat_adjustments:
                # レバレッジ乗数を適用
                if 'leverage_multiplier' in cat_adjustments:
                    constants['core']['max_leverage'] *= cat_adjustments['leverage_multiplier']
                
                # リスク増加を適用
                if 'risk_reduction' in cat_adjustments:
                    risk_increase = cat_adjustments['risk_reduction']
                    constants['core']['min_risk_reward'] *= (1.0 + risk_increase)
        
        # 緊急時制限の適用
        emergency_limits = constants['emergency_limits']
        constants['core']['max_leverage'] = min(
            constants['core']['max_leverage'],
            emergency_limits.get('absolute_max_leverage', 50.0)
        )
        
        # メタデータ追加
        constants['metadata'] = {
            'timeframe': timeframe,
            'symbol_category': symbol_category,
            'config_file': self.config_file,
            'last_loaded': datetime.now().isoformat()
        }
        
        return constants
    
    def update_constant(self, section: str, key: str, value: Any) -> None:
        """
        設定値を更新
        
        Args:
            section: セクション名（例: 'core_limits'）
            key: キー名（例: 'max_leverage'）
            value: 新しい値
        """
        if 'leverage_engine_constants' not in self.config_data:
            self.config_data['leverage_engine_constants'] = {}
        
        if section not in self.config_data['leverage_engine_constants']:
            self.config_data['leverage_engine_constants'][section] = {}
        
        self.config_data['leverage_engine_constants'][section][key] = value
        
        print(f"✅ {section}.{key} を {value} に更新")
        self.save_config()
    
    def save_config(self) -> None:
        """設定をファイルに保存"""
        self.config_data['leverage_engine_constants']['last_updated'] = datetime.now().isoformat()
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 レバレッジエンジン設定を保存: {self.config_file}")
    
    def print_config_summary(self) -> None:
        """設定サマリーを表示"""
        print("\n📊 レバレッジエンジン設定サマリー")
        print("=" * 80)
        
        core_constants = self.get_core_constants()
        print(f"\n⚙️ コア定数:")
        for key, value in core_constants.items():
            print(f"  {key}: {value}")
        
        print(f"\n⏰ 時間足調整:")
        timeframes = ['1m', '15m', '1h', '4h']
        for tf in timeframes:
            adjustments = self.get_timeframe_adjustments(tf)
            if adjustments:
                print(f"  {tf}: {adjustments}")
        
        print(f"\n📈 銘柄カテゴリ調整:")
        categories = ['large_cap', 'mid_cap', 'small_cap', 'meme_coin']
        for cat in categories:
            adjustments = self.get_symbol_category_adjustments(cat)
            if adjustments:
                print(f"  {cat}: {adjustments}")
        
        emergency_limits = self.get_emergency_limits()
        print(f"\n🚨 緊急時制限:")
        for key, value in emergency_limits.items():
            print(f"  {key}: {value}")
    
    def validate_config(self) -> bool:
        """設定の妥当性を検証"""
        try:
            core = self.get_core_constants()
            
            # 基本的な妥当性チェック
            if core['max_leverage'] <= 0 or core['max_leverage'] > 1000:
                print(f"❌ max_leverage値が無効: {core['max_leverage']}")
                return False
            
            if core['min_risk_reward'] <= 0:
                print(f"❌ min_risk_reward値が無効: {core['min_risk_reward']}")
                return False
            
            if not (0 <= core['btc_correlation_threshold'] <= 1):
                print(f"❌ btc_correlation_threshold値が無効: {core['btc_correlation_threshold']}")
                return False
            
            print("✅ 設定の妥当性検証に合格")
            return True
            
        except Exception as e:
            print(f"❌ 設定検証エラー: {e}")
            return False


def main():
    """設定管理システムのデモ"""
    print("レバレッジエンジン設定管理システム")
    print("=" * 50)
    
    # 設定管理インスタンス作成
    config_manager = LeverageConfigManager()
    
    # 設定サマリー表示
    config_manager.print_config_summary()
    
    # 設定検証
    config_manager.validate_config()
    
    # 使用例
    print("\n\n📊 使用例:")
    print("-" * 50)
    
    # 1. 基本定数取得
    core_constants = config_manager.get_core_constants()
    print(f"\n基本定数: {core_constants}")
    
    # 2. 時間足・銘柄カテゴリ調整済み定数取得
    adjusted_constants = config_manager.get_adjusted_constants('15m', 'small_cap')
    print(f"\n調整済み定数 (15m, small_cap): {adjusted_constants['core']}")
    
    print(f"\n✅ レバレッジエンジン設定管理システムの動作確認完了")


if __name__ == "__main__":
    main()