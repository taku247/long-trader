#!/usr/bin/env python3
"""
統合設定管理システム

trading_conditions.jsonとtimeframe_conditions.jsonを統合管理し、
トレーディング戦略の全ての設定を一元管理します。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import copy

class UnifiedConfigManager:
    """統合設定管理クラス"""
    
    def __init__(self, trading_config_file: Optional[str] = None, 
                 timeframe_config_file: Optional[str] = None):
        """
        初期化
        
        Args:
            trading_config_file: トレーディング条件設定ファイルパス
            timeframe_config_file: 時間足設定ファイルパス
        """
        self.trading_config_file = trading_config_file or self._get_default_trading_config_path()
        self.timeframe_config_file = timeframe_config_file or self._get_default_timeframe_config_path()
        
        self.trading_config = {}
        self.timeframe_config = {}
        
        self.load_configs()
    
    def _get_default_trading_config_path(self) -> str:
        """デフォルトトレーディング設定ファイルパスを取得"""
        current_dir = Path(__file__).parent
        return str(current_dir / "trading_conditions.json")
    
    def _get_default_timeframe_config_path(self) -> str:
        """デフォルト時間足設定ファイルパスを取得"""
        current_dir = Path(__file__).parent
        return str(current_dir / "timeframe_conditions.json")
    
    def load_configs(self) -> None:
        """両方の設定ファイルを読み込み"""
        # トレーディング条件を読み込み
        try:
            with open(self.trading_config_file, 'r', encoding='utf-8') as f:
                self.trading_config = json.load(f)
            print(f"✅ トレーディング条件を読み込み: {self.trading_config_file}")
        except Exception as e:
            print(f"❌ トレーディング条件読み込みエラー: {e}")
            self.trading_config = {}
        
        # 時間足設定を読み込み
        try:
            with open(self.timeframe_config_file, 'r', encoding='utf-8') as f:
                self.timeframe_config = json.load(f)
            print(f"✅ 時間足設定を読み込み: {self.timeframe_config_file}")
        except Exception as e:
            print(f"❌ 時間足設定読み込みエラー: {e}")
            self.timeframe_config = {}
    
    def get_strategy_config(self, strategy: str) -> Dict[str, Any]:
        """
        戦略別設定を取得
        
        Args:
            strategy: 戦略名 (Conservative_ML, Aggressive_ML, Balanced)
            
        Returns:
            戦略設定辞書
        """
        strategies = self.trading_config.get('strategy_configs', {})
        
        if strategy not in strategies:
            print(f"⚠️ 未定義の戦略: {strategy}, デフォルト(Balanced)を使用")
            strategy = 'Balanced'
        
        return copy.deepcopy(strategies.get(strategy, {}))
    
    def get_entry_conditions(self, timeframe: str, strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        エントリー条件を取得（時間足と戦略を考慮）
        
        Args:
            timeframe: 時間足
            strategy: 戦略名（オプション）
            
        Returns:
            エントリー条件辞書
        """
        # 基本条件を時間足設定から取得
        tf_config = self.timeframe_config.get('timeframe_configs', {}).get(timeframe, {})
        base_conditions = tf_config.get('entry_conditions', {})
        
        # trading_conditions.jsonからも取得
        trading_conditions = self.trading_config.get('entry_conditions_by_timeframe', {}).get(timeframe, {})
        
        # 統合（trading_conditions.jsonを優先）
        merged_conditions = copy.deepcopy(base_conditions)
        merged_conditions.update(trading_conditions)
        
        # 戦略による調整を適用
        if strategy:
            strategy_config = self.get_strategy_config(strategy)
            
            # 信頼度ブースト適用
            if 'confidence_boost' in strategy_config and 'min_confidence' in merged_conditions:
                merged_conditions['min_confidence'] += strategy_config['confidence_boost']
                merged_conditions['min_confidence'] = max(0.1, min(1.0, merged_conditions['min_confidence']))
            
            # リスク乗数適用
            if 'risk_multiplier' in strategy_config and 'min_risk_reward' in merged_conditions:
                merged_conditions['min_risk_reward'] *= strategy_config['risk_multiplier']
            
            # レバレッジキャップ適用
            if 'leverage_cap' in strategy_config:
                merged_conditions['max_leverage'] = strategy_config['leverage_cap']
        
        return merged_conditions
    
    def get_all_conditions(self, timeframe: str, strategy: str) -> Dict[str, Any]:
        """
        指定された時間足と戦略の全条件を取得
        
        Args:
            timeframe: 時間足
            strategy: 戦略名
            
        Returns:
            全条件を含む辞書
        """
        result = {
            'timeframe': timeframe,
            'strategy': strategy,
            'entry_conditions': self.get_entry_conditions(timeframe, strategy),
            'strategy_config': self.get_strategy_config(strategy),
            'timeframe_config': self.get_timeframe_settings(timeframe),
            'leverage_engine': self.get_leverage_engine_config(),
            'risk_management': self.get_risk_management_config()
        }
        
        return result
    
    def get_timeframe_settings(self, timeframe: str) -> Dict[str, Any]:
        """時間足の全設定を取得"""
        return copy.deepcopy(
            self.timeframe_config.get('timeframe_configs', {}).get(timeframe, {})
        )
    
    def get_leverage_engine_config(self) -> Dict[str, Any]:
        """レバレッジエンジン設定を取得"""
        return copy.deepcopy(
            self.trading_config.get('leverage_engine_constants', {})
        )
    
    def get_risk_management_config(self) -> Dict[str, Any]:
        """リスク管理設定を取得"""
        return copy.deepcopy(
            self.trading_config.get('risk_management', {})
        )
    
    def get_ml_parameters(self, timeframe: str) -> Dict[str, Any]:
        """機械学習パラメータを取得"""
        ml_config = copy.deepcopy(self.trading_config.get('ml_model_parameters', {}))
        
        # 時間足固有のlookback_period適用
        if 'training_parameters' in ml_config:
            lookback = ml_config['training_parameters'].get('lookback_periods', {}).get(timeframe)
            if lookback:
                ml_config['training_parameters']['lookback_period'] = lookback
        
        return ml_config
    
    def update_entry_condition(self, timeframe: str, condition: str, value: Any) -> None:
        """
        エントリー条件を更新
        
        Args:
            timeframe: 時間足
            condition: 条件名 (min_leverage, min_confidence, etc.)
            value: 新しい値
        """
        if 'entry_conditions_by_timeframe' not in self.trading_config:
            self.trading_config['entry_conditions_by_timeframe'] = {}
        
        if timeframe not in self.trading_config['entry_conditions_by_timeframe']:
            self.trading_config['entry_conditions_by_timeframe'][timeframe] = {}
        
        self.trading_config['entry_conditions_by_timeframe'][timeframe][condition] = value
        
        print(f"✅ {timeframe} の {condition} を {value} に更新")
        self.save_trading_config()
    
    def save_trading_config(self) -> None:
        """トレーディング設定を保存"""
        self.trading_config['last_updated'] = datetime.now().isoformat()
        
        with open(self.trading_config_file, 'w', encoding='utf-8') as f:
            json.dump(self.trading_config, f, indent=2, ensure_ascii=False)
        
        print(f"💾 トレーディング設定を保存: {self.trading_config_file}")
    
    def print_condition_summary(self, timeframe: str = None, strategy: str = None) -> None:
        """条件サマリーを表示"""
        print("\n📊 統合条件サマリー")
        print("=" * 80)
        
        timeframes = [timeframe] if timeframe else ['1m', '3m', '5m', '15m', '30m', '1h']
        strategies = [strategy] if strategy else ['Conservative_ML', 'Aggressive_ML', 'Balanced']
        
        for tf in timeframes:
            print(f"\n⏰ {tf}:")
            for strat in strategies:
                conditions = self.get_entry_conditions(tf, strat)
                print(f"  📌 {strat}:")
                print(f"     最小レバレッジ: {conditions.get('min_leverage', 'N/A')}x")
                print(f"     最小信頼度: {conditions.get('min_confidence', 0) * 100:.0f}%")
                print(f"     最小RR比: {conditions.get('min_risk_reward', 'N/A')}")
                
                if 'max_leverage' in conditions:
                    print(f"     最大レバレッジ: {conditions.get('max_leverage')}x")


def main():
    """統合設定管理システムのデモ"""
    print("統合設定管理システム")
    print("=" * 50)
    
    # 設定管理インスタンス作成
    config_manager = UnifiedConfigManager()
    
    # 設定サマリー表示
    config_manager.print_condition_summary()
    
    # 使用例
    print("\n\n📊 使用例:")
    print("-" * 50)
    
    # 1. 特定の時間足・戦略の条件取得
    conditions = config_manager.get_entry_conditions('5m', 'Aggressive_ML')
    print(f"\n5分足 Aggressive_ML のエントリー条件:")
    for key, value in conditions.items():
        print(f"  {key}: {value}")
    
    # 2. 全条件取得
    all_conditions = config_manager.get_all_conditions('1h', 'Conservative_ML')
    print(f"\n1時間足 Conservative_ML の全条件:")
    print(f"  エントリー条件: {all_conditions['entry_conditions']}")
    print(f"  戦略設定: {all_conditions['strategy_config']}")
    
    print(f"\n✅ 統合設定管理システムの動作確認完了")


if __name__ == "__main__":
    main()