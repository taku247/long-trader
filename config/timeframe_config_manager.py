#!/usr/bin/env python3
"""
時間足設定管理システム

TIMEFRAME_CONFIGSを外部JSONファイルから読み込み、
動的な設定変更と検証を提供します。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import copy
from .defaults_manager import defaults_manager

class TimeframeConfigManager:
    """時間足設定管理クラス"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初期化
        
        Args:
            config_file: 設定ファイルパス (None の場合はデフォルト)
        """
        self.config_file = config_file or self._get_default_config_path()
        self.config_data = {}
        self.load_config()
    
    def _get_default_config_path(self) -> str:
        """デフォルト設定ファイルパスを取得"""
        current_dir = Path(__file__).parent
        return str(current_dir / "timeframe_conditions.json")
    
    def load_config(self) -> None:
        """設定ファイルを読み込み"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            print(f"✅ 時間足設定を読み込み: {self.config_file}")
            self._validate_config()
        except FileNotFoundError:
            print(f"⚠️ 設定ファイルが見つかりません: {self.config_file}")
            self._create_default_config()
        except json.JSONDecodeError as e:
            print(f"❌ 設定ファイルのJSON形式が不正: {e}")
            raise
        except Exception as e:
            print(f"❌ 設定ファイル読み込みエラー: {e}")
            raise
    
    def save_config(self) -> None:
        """設定ファイルを保存"""
        try:
            # バックアップ作成
            backup_file = f"{self.config_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(self.config_file):
                os.copy(self.config_file, backup_file)
                print(f"📁 バックアップ作成: {backup_file}")
            
            # 設定保存
            self.config_data['last_updated'] = datetime.now().isoformat()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 設定ファイルを保存: {self.config_file}")
            
        except Exception as e:
            print(f"❌ 設定ファイル保存エラー: {e}")
            raise
    
    def get_timeframe_config(self, timeframe: str) -> Dict[str, Any]:
        """
        指定時間足の設定を取得
        
        Args:
            timeframe: 時間足 ('1m', '5m', '15m', '30m', '1h' など)
            
        Returns:
            時間足設定辞書
        """
        timeframe_configs = self.config_data.get('timeframe_configs', {})
        
        if timeframe not in timeframe_configs:
            print(f"⚠️ 未定義の時間足: {timeframe}, デフォルト(1h)を使用")
            timeframe = '1h'
        
        # 設定をコピーして返す（元データ保護）
        config = copy.deepcopy(timeframe_configs[timeframe])
        
        # デフォルト値を動的解決
        config = defaults_manager.resolve_defaults_in_config(config)
        
        # entry_conditions を展開（後方互換性）
        if 'entry_conditions' in config:
            config.update(config['entry_conditions'])
        
        return config
    
    def get_all_timeframes(self) -> List[str]:
        """利用可能な全時間足を取得"""
        return list(self.config_data.get('timeframe_configs', {}).keys())
    
    def update_timeframe_config(self, timeframe: str, updates: Dict[str, Any]) -> None:
        """
        時間足設定を更新
        
        Args:
            timeframe: 更新対象の時間足
            updates: 更新内容辞書
        """
        if 'timeframe_configs' not in self.config_data:
            self.config_data['timeframe_configs'] = {}
        
        if timeframe not in self.config_data['timeframe_configs']:
            print(f"⚠️ 新規時間足設定を作成: {timeframe}")
            self.config_data['timeframe_configs'][timeframe] = {}
        
        # 更新適用
        self.config_data['timeframe_configs'][timeframe].update(updates)
        
        # 検証
        self._validate_timeframe_config(timeframe, self.config_data['timeframe_configs'][timeframe])
        
        print(f"✅ {timeframe} 設定を更新: {list(updates.keys())}")
    
    def get_global_settings(self) -> Dict[str, Any]:
        """グローバル設定を取得"""
        return self.config_data.get('global_settings', {})
    
    def _validate_config(self) -> None:
        """設定全体の妥当性検証"""
        required_sections = ['timeframe_configs', 'global_settings', 'validation_rules']
        
        for section in required_sections:
            if section not in self.config_data:
                print(f"⚠️ 必須セクションが不足: {section}")
        
        # 各時間足設定の検証
        for timeframe, config in self.config_data.get('timeframe_configs', {}).items():
            self._validate_timeframe_config(timeframe, config)
    
    def _validate_timeframe_config(self, timeframe: str, config: Dict[str, Any]) -> None:
        """個別時間足設定の妥当性検証"""
        validation_rules = self.config_data.get('validation_rules', {})
        
        # 必須フィールドチェック
        required_fields = [
            'data_days', 'evaluation_interval_minutes', 'max_evaluations', 'min_train_samples',
            'train_ratio', 'val_ratio', 'test_ratio'
        ]
        
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            print(f"⚠️ {timeframe}: 必須フィールドが不足: {missing_fields}")
        
        # 値の範囲チェック
        if 'entry_conditions' in config:
            entry_conditions = config['entry_conditions']
            
            # use_defaultマーカーを解決してから検証
            resolved_conditions = defaults_manager.resolve_defaults_in_config(entry_conditions)
            
            # 信頼度範囲チェック
            confidence = resolved_conditions.get('min_confidence', 0)
            conf_range = validation_rules.get('min_confidence_range', [0.1, 1.0])
            if isinstance(confidence, (int, float)) and not (conf_range[0] <= confidence <= conf_range[1]):
                print(f"⚠️ {timeframe}: min_confidence が範囲外: {confidence}")
            
            # レバレッジ範囲チェック
            leverage = resolved_conditions.get('min_leverage', 1)
            lev_range = validation_rules.get('min_leverage_range', [1.0, 50.0])
            if isinstance(leverage, (int, float)) and not (lev_range[0] <= leverage <= lev_range[1]):
                print(f"⚠️ {timeframe}: min_leverage が範囲外: {leverage}")
            
            # リスクリワード範囲チェック
            risk_reward = resolved_conditions.get('min_risk_reward', 1.0)
            rr_range = validation_rules.get('min_risk_reward_range', [0.5, 10.0])
            if isinstance(risk_reward, (int, float)) and not (rr_range[0] <= risk_reward <= rr_range[1]):
                print(f"⚠️ {timeframe}: min_risk_reward が範囲外: {risk_reward}")
        
        # 評価間隔チェック
        interval = config.get('evaluation_interval_minutes', 0)
        interval_range = [
            validation_rules.get('min_evaluation_interval', 1),
            validation_rules.get('max_evaluation_interval', 1440)
        ]
        if not (interval_range[0] <= interval <= interval_range[1]):
            print(f"⚠️ {timeframe}: evaluation_interval_minutes が範囲外: {interval}")
        
        # 最大評価回数チェック
        max_evals = config.get('max_evaluations', 50)
        eval_range = validation_rules.get('max_evaluations_range', [10, 500])
        if not (eval_range[0] <= max_evals <= eval_range[1]):
            print(f"⚠️ {timeframe}: max_evaluations が範囲外: {max_evals}")
    
    def _create_default_config(self) -> None:
        """デフォルト設定を作成"""
        print("📝 デフォルト設定ファイルを作成中...")
        
        # デフォルト設定（現在のTIMEFRAME_CONFIGSベース）
        self.config_data = {
            "description": "時間足別の条件ベースシグナル生成設定（自動生成）",
            "last_updated": datetime.now().isoformat(),
            "version": "1.0.0",
            "timeframe_configs": {
                "1h": {
                    "description": "1時間足 - デフォルト設定",
                    "data_days": 180,
                    "evaluation_interval_minutes": 240,
                    "max_evaluations": 100,
                    "min_train_samples": 500,
                    "train_ratio": 0.6,
                    "val_ratio": 0.2,
                    "test_ratio": 0.2,
                    "entry_conditions": {
                        "min_leverage": 3.0,
                        "min_confidence": 0.50,
                        "min_risk_reward": 1.2
                    },
                    "active_hours_range": [9, 22]
                }
            },
            "global_settings": {
                "timezone": "JST",
                "weekend_trading": False
            },
            "validation_rules": {
                "min_evaluation_interval": 1,
                "max_evaluation_interval": 1440,
                "min_confidence_range": [0.1, 1.0],
                "min_leverage_range": [1.0, 50.0],
                "min_risk_reward_range": [0.5, 10.0],
                "max_evaluations_range": [10, 500]
            }
        }
        
        # ディレクトリ作成
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # 保存
        self.save_config()
    
    def export_current_config(self, output_file: str) -> None:
        """現在の設定を指定ファイルにエクスポート"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            print(f"📤 設定をエクスポート: {output_file}")
        except Exception as e:
            print(f"❌ エクスポートエラー: {e}")
            raise
    
    def import_config(self, input_file: str) -> None:
        """指定ファイルから設定をインポート"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # バックアップ作成
            self.save_config()
            
            # インポート適用
            self.config_data = imported_config
            self._validate_config()
            self.save_config()
            
            print(f"📥 設定をインポート: {input_file}")
            
        except Exception as e:
            print(f"❌ インポートエラー: {e}")
            raise
    
    def print_config_summary(self) -> None:
        """設定サマリーを表示"""
        print("\n📊 時間足設定サマリー")
        print("=" * 60)
        
        for timeframe, config in self.config_data.get('timeframe_configs', {}).items():
            print(f"\n🕐 {timeframe}:")
            print(f"   📅 データ期間: {config.get('data_days', 'N/A')}日")
            print(f"   ⏰ 評価間隔: {config.get('evaluation_interval_minutes', 'N/A')}分")
            
            if 'entry_conditions' in config:
                ec = config['entry_conditions']
                print(f"   🎯 エントリー条件:")
                print(f"      💪 最小レバレッジ: {ec.get('min_leverage', 'N/A')}x")
                print(f"      🎪 最小信頼度: {ec.get('min_confidence', 'N/A'):.0%}")
                print(f"      ⚖️ 最小RR比: {ec.get('min_risk_reward', 'N/A')}")
            
            print(f"   🔄 最大評価回数: {config.get('max_evaluations', 'N/A')}回")


def main():
    """設定管理システムのデモ"""
    print("時間足設定管理システム")
    print("=" * 50)
    
    # 設定管理インスタンス作成
    config_manager = TimeframeConfigManager()
    
    # 設定サマリー表示
    config_manager.print_config_summary()
    
    # 使用例: 5分足設定の更新
    print(f"\n🔧 5分足設定を更新...")
    config_manager.update_timeframe_config('5m', {
        'entry_conditions': {
            'min_leverage': 6.5,  # レバレッジ要件を緩和
            'min_confidence': 0.62  # 信頼度要件を微調整
        }
    })
    
    # 設定取得例
    config_5m = config_manager.get_timeframe_config('5m')
    print(f"📊 5分足設定: min_leverage={config_5m.get('min_leverage')}")
    
    print(f"\n✅ 設定管理システムの動作確認完了")


if __name__ == "__main__":
    main()