#!/usr/bin/env python3
"""
条件厳しさレベル管理システム

development, testing, conservative, standard, strict の5段階で
エントリー条件の厳しさを動的に調整するシステム。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import copy

class StrictnessManager:
    """条件厳しさレベル管理クラス"""
    
    def __init__(self, strictness_config_file: Optional[str] = None):
        """
        初期化
        
        Args:
            strictness_config_file: 厳しさレベル設定ファイルパス
        """
        self.config_file = strictness_config_file or self._get_default_config_path()
        self.config_data = {}
        self.load_config()
    
    def _get_default_config_path(self) -> str:
        """デフォルト設定ファイルパスを取得"""
        current_dir = Path(__file__).parent
        return str(current_dir / "condition_strictness_levels.json")
    
    def load_config(self) -> None:
        """設定ファイルを読み込み"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            print(f"✅ 厳しさレベル設定を読み込み: {self.config_file}")
        except Exception as e:
            print(f"❌ 厳しさレベル設定読み込みエラー: {e}")
            raise
    
    def get_current_level(self) -> str:
        """現在の厳しさレベルを取得"""
        return self.config_data.get('current_level', 'standard')
    
    def set_current_level(self, level: str) -> None:
        """
        現在の厳しさレベルを設定
        
        Args:
            level: 設定する厳しさレベル
        """
        available_levels = list(self.config_data.get('strictness_levels', {}).keys())
        
        if level not in available_levels:
            raise ValueError(f"無効な厳しさレベル: {level}. 利用可能: {available_levels}")
        
        self.config_data['current_level'] = level
        self.save_config()
        
        level_info = self.config_data['strictness_levels'][level]
        print(f"🎯 厳しさレベルを {level_info['color']} {level} に設定: {level_info['description']}")
    
    def get_adjusted_conditions(self, timeframe: str, level: Optional[str] = None) -> Dict[str, Any]:
        """
        指定された厳しさレベルで調整された条件を取得
        
        Args:
            timeframe: 時間足
            level: 厳しさレベル（指定なしの場合は現在のレベル）
            
        Returns:
            調整された条件辞書
        """
        if level is None:
            level = self.get_current_level()
        
        # 基準条件を取得
        base_conditions = self.config_data.get('base_conditions_by_timeframe', {}).get(timeframe)
        if not base_conditions:
            raise ValueError(f"未定義の時間足: {timeframe}")
        
        # 厳しさレベルの調整係数を取得
        level_config = self.config_data.get('strictness_levels', {}).get(level)
        if not level_config:
            raise ValueError(f"未定義の厳しさレベル: {level}")
        
        multipliers = level_config['multipliers']
        
        # 条件を調整
        adjusted_conditions = copy.deepcopy(base_conditions)
        
        # レバレッジ条件調整（係数が小さいほど緩い）
        adjusted_conditions['min_leverage'] = max(
            1.0, 
            base_conditions['base_min_leverage'] * multipliers['leverage_factor']
        )
        
        # 信頼度条件調整（係数が小さいほど緩い）
        adjusted_conditions['min_confidence'] = max(
            0.1, 
            min(1.0, base_conditions['base_min_confidence'] * multipliers['confidence_factor'])
        )
        
        # リスクリワード条件調整（係数が小さいほど緩い）
        adjusted_conditions['min_risk_reward'] = max(
            0.5,
            base_conditions['base_min_risk_reward'] * multipliers['risk_reward_factor']
        )
        
        # メタデータ追加
        adjusted_conditions['strictness_level'] = level
        adjusted_conditions['level_description'] = level_config['description']
        adjusted_conditions['level_color'] = level_config['color']
        
        return adjusted_conditions
    
    def get_all_levels_comparison(self, timeframe: str) -> Dict[str, Dict[str, Any]]:
        """
        指定時間足での全レベル比較を取得
        
        Args:
            timeframe: 時間足
            
        Returns:
            全レベルの条件比較辞書
        """
        comparison = {}
        
        for level in self.config_data.get('strictness_levels', {}).keys():
            try:
                conditions = self.get_adjusted_conditions(timeframe, level)
                comparison[level] = conditions
            except Exception as e:
                print(f"⚠️ レベル {level} の条件取得エラー: {e}")
        
        return comparison
    
    def save_config(self) -> None:
        """設定ファイルを保存"""
        self.config_data['last_updated'] = datetime.now().isoformat()
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 厳しさレベル設定を保存: {self.config_file}")
    
    def print_current_status(self) -> None:
        """現在の設定状況を表示"""
        current_level = self.get_current_level()
        level_config = self.config_data['strictness_levels'][current_level]
        
        print(f"\n📊 現在の厳しさレベル設定")
        print("=" * 60)
        print(f"レベル: {level_config['color']} {current_level}")
        print(f"説明: {level_config['description']}")
        print(f"用途: {level_config['usage']}")
        
        print(f"\n📋 調整係数:")
        multipliers = level_config['multipliers']
        print(f"   レバレッジ係数: {multipliers['leverage_factor']}")
        print(f"   信頼度係数: {multipliers['confidence_factor']}")
        print(f"   RR比係数: {multipliers['risk_reward_factor']}")
    
    def print_levels_comparison(self, timeframe: str = "15m") -> None:
        """レベル別比較を表示"""
        print(f"\n📊 厳しさレベル別条件比較 ({timeframe})")
        print("=" * 80)
        
        comparison = self.get_all_levels_comparison(timeframe)
        
        for level, conditions in comparison.items():
            level_config = self.config_data['strictness_levels'][level]
            print(f"\n{level_config['color']} {level.upper()}: {level_config['description']}")
            print(f"   最小レバレッジ: {conditions['min_leverage']:.1f}x")
            print(f"   最小信頼度: {conditions['min_confidence'] * 100:.0f}%")
            print(f"   最小RR比: {conditions['min_risk_reward']:.1f}")
    
    def recommend_level_for_situation(self, situation: str) -> str:
        """
        状況に応じた推奨レベルを返す
        
        Args:
            situation: 状況 (development, testing, production, etc.)
            
        Returns:
            推奨厳しさレベル
        """
        recommendations = {
            'development': 'development',
            'testing': 'testing',
            'symbol_addition': 'testing',
            'debug': 'development',
            'production': 'standard',
            'high_volatility': 'strict',
            'stable_market': 'conservative'
        }
        
        return recommendations.get(situation, 'standard')


def main():
    """厳しさレベル管理システムのデモ"""
    print("条件厳しさレベル管理システム")
    print("=" * 50)
    
    # 厳しさ管理インスタンス作成
    strictness_manager = StrictnessManager()
    
    # 現在の状況表示
    strictness_manager.print_current_status()
    
    # レベル別比較表示
    strictness_manager.print_levels_comparison("15m")
    
    # 使用例
    print(f"\n\n🧪 使用例:")
    print("-" * 50)
    
    # 1. テスト用にレベル変更
    print(f"\n1. テスト用レベルに変更:")
    strictness_manager.set_current_level('testing')
    
    # 2. 調整された条件を取得
    test_conditions = strictness_manager.get_adjusted_conditions('15m', 'testing')
    print(f"\nテスト用 15分足条件:")
    print(f"   最小レバレッジ: {test_conditions['min_leverage']:.1f}x")
    print(f"   最小信頼度: {test_conditions['min_confidence'] * 100:.0f}%")
    print(f"   最小RR比: {test_conditions['min_risk_reward']:.1f}")
    
    # 3. 開発用レベルに変更
    print(f"\n2. 開発用レベルに変更:")
    strictness_manager.set_current_level('development')
    
    dev_conditions = strictness_manager.get_adjusted_conditions('15m', 'development')
    print(f"\n開発用 15分足条件:")
    print(f"   最小レバレッジ: {dev_conditions['min_leverage']:.1f}x")
    print(f"   最小信頼度: {dev_conditions['min_confidence'] * 100:.0f}%")
    print(f"   最小RR比: {dev_conditions['min_risk_reward']:.1f}")
    
    # 4. 標準レベルに戻す
    strictness_manager.set_current_level('standard')
    
    print(f"\n✅ 厳しさレベル管理システムの動作確認完了")


if __name__ == "__main__":
    main()