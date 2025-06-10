#!/usr/bin/env python3
"""
ウォークフォワード分析システム
時系列データの正しい学習・バックテスト手法
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import sys
import os

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from real_time_system.utils.colored_log import get_colored_logger


@dataclass
class DataWindow:
    """データウィンドウ"""
    start_date: datetime
    end_date: datetime
    window_type: str  # 'training', 'validation', 'backtest'
    data_points: int
    

@dataclass
class WalkForwardConfig:
    """ウォークフォワード設定"""
    training_window_days: int = 180     # 学習期間（6ヶ月）
    validation_window_days: int = 30    # 検証期間（1ヶ月）
    backtest_window_days: int = 30      # バックテスト期間（1ヶ月）
    step_forward_days: int = 7          # 前進ステップ（1週間）
    min_training_points: int = 1000     # 最小学習データ数
    retrain_frequency_days: int = 30    # 再学習頻度（1ヶ月）


class WalkForwardSystem:
    """ウォークフォワード分析システム"""
    
    def __init__(self, symbol: str, config: WalkForwardConfig = None):
        self.symbol = symbol
        self.config = config or WalkForwardConfig()
        self.logger = get_colored_logger(__name__)
        
        # データ管理
        self.data_history: Optional[pd.DataFrame] = None
        self.last_training_date: Optional[datetime] = None
        self.last_backtest_date: Optional[datetime] = None
        
        # ウィンドウ追跡
        self.training_windows: List[DataWindow] = []
        self.backtest_windows: List[DataWindow] = []
        
        # 状態ファイル
        self.state_file = Path(f"walk_forward_state_{symbol}.json")
        self._load_state()
    
    def _load_state(self):
        """状態ファイルから前回の実行状況を読み込み"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                if state.get('last_training_date'):
                    self.last_training_date = datetime.fromisoformat(state['last_training_date'])
                if state.get('last_backtest_date'):
                    self.last_backtest_date = datetime.fromisoformat(state['last_backtest_date'])
                
                self.logger.info(f"📚 Loaded state for {self.symbol}")
                self.logger.info(f"  Last training: {self.last_training_date}")
                self.logger.info(f"  Last backtest: {self.last_backtest_date}")
        
        except Exception as e:
            self.logger.warning(f"Failed to load state: {e}")
    
    def _save_state(self):
        """状態ファイルに現在の実行状況を保存"""
        try:
            state = {
                'symbol': self.symbol,
                'last_training_date': self.last_training_date.isoformat() if self.last_training_date else None,
                'last_backtest_date': self.last_backtest_date.isoformat() if self.last_backtest_date else None,
                'updated_at': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def should_retrain(self, current_date: datetime = None) -> bool:
        """再学習が必要かどうかを判定"""
        current_date = current_date or datetime.now()
        
        if not self.last_training_date:
            self.logger.info(f"🎯 {self.symbol}: First training required")
            return True
        
        days_since_training = (current_date - self.last_training_date).days
        
        if days_since_training >= self.config.retrain_frequency_days:
            self.logger.info(f"🎯 {self.symbol}: Retrain required ({days_since_training} days since last training)")
            return True
        
        return False
    
    def should_backtest(self, current_date: datetime = None) -> bool:
        """バックテストが必要かどうかを判定"""
        current_date = current_date or datetime.now()
        
        if not self.last_backtest_date:
            return True
        
        days_since_backtest = (current_date - self.last_backtest_date).days
        
        # バックテストはより頻繁に実行（1週間毎）
        if days_since_backtest >= self.config.step_forward_days:
            return True
        
        return False
    
    def get_training_window(self, end_date: datetime) -> DataWindow:
        """学習用データウィンドウの取得"""
        start_date = end_date - timedelta(days=self.config.training_window_days)
        
        return DataWindow(
            start_date=start_date,
            end_date=end_date,
            window_type='training',
            data_points=0  # 実際のデータ取得時に設定
        )
    
    def get_validation_window(self, training_end_date: datetime) -> DataWindow:
        """検証用データウィンドウの取得"""
        start_date = training_end_date
        end_date = start_date + timedelta(days=self.config.validation_window_days)
        
        return DataWindow(
            start_date=start_date,
            end_date=end_date,
            window_type='validation',
            data_points=0
        )
    
    def get_backtest_window(self, current_date: datetime) -> DataWindow:
        """バックテスト用データウィンドウの取得"""
        start_date = current_date - timedelta(days=self.config.backtest_window_days)
        end_date = current_date
        
        return DataWindow(
            start_date=start_date,
            end_date=end_date,
            window_type='backtest',
            data_points=0
        )
    
    def is_data_overlap(self, window1: DataWindow, window2: DataWindow) -> bool:
        """データウィンドウの重複チェック"""
        return not (window1.end_date <= window2.start_date or window2.end_date <= window1.start_date)
    
    def validate_data_integrity(self, training_window: DataWindow, backtest_window: DataWindow) -> bool:
        """データ整合性の検証"""
        # 1. 学習データはバックテストデータより過去でなければならない
        if training_window.end_date > backtest_window.start_date:
            self.logger.error(f"❌ Data leakage detected!")
            self.logger.error(f"   Training ends: {training_window.end_date}")
            self.logger.error(f"   Backtest starts: {backtest_window.start_date}")
            return False
        
        # 2. 十分なギャップがあることを確認
        gap_days = (backtest_window.start_date - training_window.end_date).days
        min_gap_days = 1  # 最低1日のギャップ
        
        if gap_days < min_gap_days:
            self.logger.warning(f"⚠️ Insufficient gap between training and backtest: {gap_days} days")
            return False
        
        # 3. 学習データが十分あることを確認
        if training_window.data_points < self.config.min_training_points:
            self.logger.warning(f"⚠️ Insufficient training data: {training_window.data_points} points")
            return False
        
        return True
    
    async def execute_walk_forward_training(self, target_date: datetime = None) -> Dict:
        """ウォークフォワード学習の実行"""
        target_date = target_date or datetime.now()
        
        self.logger.info(f"🎓 Starting walk-forward training for {self.symbol}")
        
        # 学習ウィンドウの設定
        training_window = self.get_training_window(target_date)
        validation_window = self.get_validation_window(training_window.end_date)
        
        self.logger.info(f"📊 Training window: {training_window.start_date} to {training_window.end_date}")
        self.logger.info(f"🔍 Validation window: {validation_window.start_date} to {validation_window.end_date}")
        
        try:
            # データ取得
            training_data = await self._fetch_data(training_window)
            validation_data = await self._fetch_data(validation_window)
            
            if len(training_data) < self.config.min_training_points:
                raise ValueError(f"Insufficient training data: {len(training_data)} < {self.config.min_training_points}")
            
            training_window.data_points = len(training_data)
            validation_window.data_points = len(validation_data)
            
            # モデル学習
            model_results = await self._train_models(training_data, validation_data)
            
            # 学習日時を更新
            self.last_training_date = target_date
            self.training_windows.append(training_window)
            self._save_state()
            
            self.logger.success(f"✅ Training completed for {self.symbol}")
            
            return {
                'status': 'success',
                'training_window': training_window,
                'validation_window': validation_window,
                'model_results': model_results,
                'training_points': len(training_data),
                'validation_points': len(validation_data)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Training failed for {self.symbol}: {e}")
            raise
    
    async def execute_walk_forward_backtest(self, target_date: datetime = None) -> Dict:
        """ウォークフォワードバックテストの実行"""
        target_date = target_date or datetime.now()
        
        self.logger.info(f"📈 Starting walk-forward backtest for {self.symbol}")
        
        # バックテストウィンドウの設定
        backtest_window = self.get_backtest_window(target_date)
        
        # 最新の学習ウィンドウを取得
        if not self.training_windows:
            raise ValueError("No training data available. Run training first.")
        
        latest_training_window = self.training_windows[-1]
        
        # データ整合性チェック
        if not self.validate_data_integrity(latest_training_window, backtest_window):
            raise ValueError("Data integrity validation failed")
        
        self.logger.info(f"📊 Backtest window: {backtest_window.start_date} to {backtest_window.end_date}")
        self.logger.info(f"🎓 Using training data up to: {latest_training_window.end_date}")
        
        try:
            # バックテストデータ取得
            backtest_data = await self._fetch_data(backtest_window)
            backtest_window.data_points = len(backtest_data)
            
            # バックテスト実行
            backtest_results = await self._run_backtest(backtest_data, latest_training_window)
            
            # バックテスト日時を更新
            self.last_backtest_date = target_date
            self.backtest_windows.append(backtest_window)
            self._save_state()
            
            self.logger.success(f"✅ Backtest completed for {self.symbol}")
            
            return {
                'status': 'success',
                'backtest_window': backtest_window,
                'training_window_used': latest_training_window,
                'backtest_results': backtest_results,
                'backtest_points': len(backtest_data)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Backtest failed for {self.symbol}: {e}")
            raise
    
    async def _fetch_data(self, window: DataWindow) -> pd.DataFrame:
        """指定期間のデータを取得"""
        # TODO: 実際のデータ取得実装
        # ScalableAnalysisSystemとの統合
        
        # サンプル実装
        self.logger.info(f"📥 Fetching data for {window.window_type}: {window.start_date} to {window.end_date}")
        
        # サンプルデータ生成
        date_range = pd.date_range(window.start_date, window.end_date, freq='1H')
        data = pd.DataFrame({
            'timestamp': date_range,
            'open': np.random.uniform(100, 200, len(date_range)),
            'high': np.random.uniform(100, 200, len(date_range)),
            'low': np.random.uniform(100, 200, len(date_range)),
            'close': np.random.uniform(100, 200, len(date_range)),
            'volume': np.random.uniform(1000, 10000, len(date_range))
        })
        
        return data
    
    async def _train_models(self, training_data: pd.DataFrame, validation_data: pd.DataFrame) -> Dict:
        """モデル学習の実行"""
        # TODO: 実際のML学習実装
        
        self.logger.info(f"🤖 Training models with {len(training_data)} training points")
        self.logger.info(f"🔍 Validating with {len(validation_data)} validation points")
        
        # サンプル結果
        return {
            'model_accuracy': 0.72,
            'validation_accuracy': 0.68,
            'feature_importance': {'price_momentum': 0.3, 'volume_spike': 0.25},
            'training_time_seconds': 45
        }
    
    async def _run_backtest(self, backtest_data: pd.DataFrame, training_window: DataWindow) -> Dict:
        """バックテストの実行"""
        # TODO: 実際のバックテスト実装
        
        self.logger.info(f"📊 Running backtest with {len(backtest_data)} data points")
        self.logger.info(f"🎓 Using model trained up to {training_window.end_date}")
        
        # サンプル結果
        return {
            'total_trades': 15,
            'winning_trades': 9,
            'win_rate': 0.6,
            'total_return': 0.12,
            'sharpe_ratio': 1.8,
            'max_drawdown': 0.05
        }
    
    def get_system_status(self) -> Dict:
        """システム状況の取得"""
        return {
            'symbol': self.symbol,
            'last_training_date': self.last_training_date.isoformat() if self.last_training_date else None,
            'last_backtest_date': self.last_backtest_date.isoformat() if self.last_backtest_date else None,
            'should_retrain': self.should_retrain(),
            'should_backtest': self.should_backtest(),
            'training_windows_count': len(self.training_windows),
            'backtest_windows_count': len(self.backtest_windows),
            'config': {
                'training_window_days': self.config.training_window_days,
                'retrain_frequency_days': self.config.retrain_frequency_days,
                'step_forward_days': self.config.step_forward_days
            }
        }


def main():
    """テスト実行"""
    import asyncio
    
    async def test_walk_forward():
        # システム初期化
        wf_system = WalkForwardSystem("HYPE")
        
        print("=== ウォークフォワード分析システム ===")
        print(f"銘柄: {wf_system.symbol}")
        
        # 現在の状況確認
        status = wf_system.get_system_status()
        print(f"\n📊 現在の状況:")
        print(f"  学習が必要: {status['should_retrain']}")
        print(f"  バックテストが必要: {status['should_backtest']}")
        
        # 学習実行
        if status['should_retrain']:
            print(f"\n🎓 学習実行中...")
            train_result = await wf_system.execute_walk_forward_training()
            print(f"✅ 学習完了: 精度 {train_result['model_results']['model_accuracy']:.2%}")
        
        # バックテスト実行
        if status['should_backtest']:
            print(f"\n📈 バックテスト実行中...")
            backtest_result = await wf_system.execute_walk_forward_backtest()
            print(f"✅ バックテスト完了: リターン {backtest_result['backtest_results']['total_return']:.2%}")
        
        # 最終状況
        final_status = wf_system.get_system_status()
        print(f"\n📊 最終状況:")
        print(f"  学習実行回数: {final_status['training_windows_count']}")
        print(f"  バックテスト実行回数: {final_status['backtest_windows_count']}")
    
    asyncio.run(test_walk_forward())


if __name__ == "__main__":
    main()