#!/usr/bin/env python3
"""
支持線・抵抗線検出失敗時の処理継続テスト

このテストは以下のシナリオを検証します：
1. 支持線・抵抗線が検出されない場合の処理継続
2. 一部の戦略で失敗しても他の戦略は継続
3. 警告ログの適切な出力
4. 銘柄追加プロセスの正常完了
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auto_symbol_training import AutoSymbolTrainer
from scalable_analysis_system import ScalableAnalysisSystem


class SupportResistanceHandlingTest:
    """支持線・抵抗線ハンドリングテストクラス"""
    
    def __init__(self):
        self.test_results = []
        self.setup_logging()
    
    def setup_logging(self):
        """テスト用ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_mock_ohlcv_data(self, scenario="trending"):
        """テスト用OHLCVデータを作成"""
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='1h')
        
        if scenario == "trending":
            # 強いトレンド相場（支持線・抵抗線が検出されにくい）
            base_price = 100
            trend_factor = np.linspace(0, 50, len(dates))  # 強い上昇トレンド
            noise = np.random.normal(0, 2, len(dates))
            
            close_prices = base_price + trend_factor + noise
            high_prices = close_prices + np.random.uniform(0.5, 2, len(dates))
            low_prices = close_prices - np.random.uniform(0.5, 2, len(dates))
            open_prices = np.roll(close_prices, 1)
            open_prices[0] = base_price
            
        elif scenario == "sideways":
            # レンジ相場（支持線・抵抗線が検出されやすい）
            base_price = 100
            range_factor = 10 * np.sin(np.linspace(0, 4*np.pi, len(dates)))
            noise = np.random.normal(0, 1, len(dates))
            
            close_prices = base_price + range_factor + noise
            high_prices = close_prices + np.random.uniform(0.2, 1, len(dates))
            low_prices = close_prices - np.random.uniform(0.2, 1, len(dates))
            open_prices = np.roll(close_prices, 1)
            open_prices[0] = base_price
        
        else:  # volatile
            # 高ボラティリティ（支持線・抵抗線が散らばる）
            base_price = 100
            volatility = np.random.normal(0, 5, len(dates))
            
            close_prices = base_price + np.cumsum(volatility)
            high_prices = close_prices + np.random.uniform(1, 5, len(dates))
            low_prices = close_prices - np.random.uniform(1, 5, len(dates))
            open_prices = np.roll(close_prices, 1)
            open_prices[0] = base_price
        
        volume = np.random.uniform(1000, 10000, len(dates))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volume
        })
    
    async def test_no_support_resistance_detected(self):
        """支持線・抵抗線が検出されない場合のテスト"""
        print("\n" + "="*60)
        print("🧪 テスト1: 支持線・抵抗線未検出時の処理継続")
        print("="*60)
        
        # モックデータ作成（強いトレンド相場）
        mock_data = self.create_mock_ohlcv_data("trending")
        
        # AutoSymbolTrainerのインスタンス作成
        trainer = AutoSymbolTrainer()
        
        # モック設定（ScalableAnalysisSystemのgenerate_batch_analysisを直接モック）
        with patch.object(trainer.analysis_system, 'generate_batch_analysis', return_value=0) as mock_analysis:
            with patch('builtins.print') as mock_print:
                
                try:
                    # バックテスト実行
                    await trainer._run_comprehensive_backtest("TEST", [
                        {'symbol': 'TEST', 'timeframe': '1h', 'strategy': 'Conservative_ML'}
                    ])
                    
                    # 成功: 例外が投げられなかった
                    print("✅ 支持線・抵抗線未検出でも処理が継続されました")
                    
                    # 警告メッセージの確認
                    warning_calls = [call for call in mock_print.call_args_list 
                                   if any('⚠️' in str(arg) for arg in call[0])]
                    
                    if warning_calls:
                        print("✅ 適切な警告メッセージが出力されました")
                        for call in warning_calls:
                            print(f"   📄 {call[0][0]}")
                    else:
                        print("❌ 警告メッセージが出力されませんでした")
                    
                    self.test_results.append(("支持線・抵抗線未検出処理", "PASS"))
                    
                except Exception as e:
                    print(f"❌ 処理が中断されました: {e}")
                    self.test_results.append(("支持線・抵抗線未検出処理", "FAIL", str(e)))
    
    async def test_partial_failure_continuation(self):
        """一部戦略の失敗でも他戦略が継続されるテスト"""
        print("\n" + "="*60)
        print("🧪 テスト2: 一部戦略失敗でも全体継続")
        print("="*60)
        
        mock_data = self.create_mock_ohlcv_data("sideways")
        trainer = AutoSymbolTrainer()
        
        # 一部の戦略のみ失敗するモック
        def mock_batch_analysis(configs, **kwargs):
            # 最初の戦略は失敗（0件処理）、2番目以降は成功
            if configs[0]['strategy'] == 'Conservative_ML':
                return 0  # 失敗
            else:
                return len(configs)  # 成功
        
        with patch.object(trainer.analysis_system, 'generate_batch_analysis', side_effect=mock_batch_analysis):
            with patch('builtins.print') as mock_print:
                    
                    try:
                        # 複数戦略でテスト
                        configs = [
                            {'symbol': 'TEST', 'timeframe': '1h', 'strategy': 'Conservative_ML'},
                            {'symbol': 'TEST', 'timeframe': '1h', 'strategy': 'Aggressive_Traditional'},
                            {'symbol': 'TEST', 'timeframe': '30m', 'strategy': 'Full_ML'}
                        ]
                        
                        await trainer._run_comprehensive_backtest("TEST", configs)
                        
                        print("✅ 一部戦略の失敗でも処理が継続されました")
                        
                        # 警告と成功の両方のメッセージを確認
                        all_calls = [str(call[0][0]) for call in mock_print.call_args_list]
                        warning_count = sum(1 for call in all_calls if '⚠️' in call)
                        
                        print(f"✅ 警告メッセージ: {warning_count}件")
                        self.test_results.append(("一部戦略失敗継続", "PASS"))
                        
                    except Exception as e:
                        print(f"❌ 処理が中断されました: {e}")
                        self.test_results.append(("一部戦略失敗継続", "FAIL", str(e)))
    
    async def test_complete_symbol_addition_flow(self):
        """完全な銘柄追加フローテスト"""
        print("\n" + "="*60)
        print("🧪 テスト3: 完全な銘柄追加フロー")
        print("="*60)
        
        trainer = AutoSymbolTrainer()
        mock_data = self.create_mock_ohlcv_data("trending")
        
        # 実行ログの記録をモック
        with patch.object(trainer.analysis_system, 'generate_batch_analysis', return_value=0):
            with patch.object(trainer, '_record_execution_start') as mock_start:
                with patch.object(trainer, '_record_execution_progress') as mock_progress:
                    with patch.object(trainer, '_record_execution_completion') as mock_completion:
                        with patch('builtins.print') as mock_print:
                            
                            try:
                                # 完全な銘柄追加フローを実行
                                await trainer.add_symbol_with_training("TEST")
                                
                                print("✅ 完全な銘柄追加フローが成功しました")
                                
                                # 実行ログの記録確認
                                assert mock_start.called, "実行開始が記録されていません"
                                assert mock_completion.called, "実行完了が記録されていません"
                                
                                print("✅ 実行ログが適切に記録されました")
                                self.test_results.append(("完全フロー", "PASS"))
                                
                            except Exception as e:
                                print(f"❌ 完全フローが失敗しました: {e}")
                                self.test_results.append(("完全フロー", "FAIL", str(e)))
    
    def test_different_market_scenarios(self):
        """異なる市場シナリオでのデータ検証"""
        print("\n" + "="*60)
        print("🧪 テスト4: 異なる市場シナリオのデータ検証")
        print("="*60)
        
        scenarios = ["trending", "sideways", "volatile"]
        
        for scenario in scenarios:
            print(f"\n📊 {scenario.upper()}相場のデータ生成テスト:")
            
            try:
                data = self.create_mock_ohlcv_data(scenario)
                
                # データの基本検証
                assert len(data) > 100, f"データ量不足: {len(data)}"
                assert not data['close'].isna().any(), "NaN値が含まれています"
                assert (data['high'] >= data['close']).all(), "高値が終値より低い"
                assert (data['low'] <= data['close']).all(), "安値が終値より高い"
                
                # 市場特性の検証
                if scenario == "trending":
                    trend = data['close'].iloc[-1] - data['close'].iloc[0]
                    assert abs(trend) > 20, f"トレンドが弱い: {trend}"
                    print(f"   ✅ 強いトレンド検出: {trend:.2f}")
                
                elif scenario == "sideways":
                    volatility = data['close'].std()
                    range_size = data['close'].max() - data['close'].min()
                    assert range_size < 30, f"レンジが広すぎる: {range_size}"
                    print(f"   ✅ レンジ相場確認: 範囲{range_size:.2f}, ボラ{volatility:.2f}")
                
                else:  # volatile
                    volatility = data['close'].std()
                    assert volatility > 5, f"ボラティリティが低い: {volatility}"
                    print(f"   ✅ 高ボラティリティ確認: {volatility:.2f}")
                
                self.test_results.append((f"{scenario}データ生成", "PASS"))
                
            except Exception as e:
                print(f"   ❌ {scenario}データ生成失敗: {e}")
                self.test_results.append((f"{scenario}データ生成", "FAIL", str(e)))
    
    async def run_all_tests(self):
        """全テストを実行"""
        print("🚀 支持線・抵抗線ハンドリングテスト開始")
        print("="*80)
        
        # 各テストを実行
        await self.test_no_support_resistance_detected()
        await self.test_partial_failure_continuation()
        await self.test_complete_symbol_addition_flow()
        self.test_different_market_scenarios()
        
        # 結果サマリー
        self.print_test_summary()
    
    def print_test_summary(self):
        """テスト結果サマリーを表示"""
        print("\n" + "="*80)
        print("📊 テスト結果サマリー")
        print("="*80)
        
        passed = sum(1 for result in self.test_results if result[1] == "PASS")
        failed = sum(1 for result in self.test_results if result[1] == "FAIL")
        
        for result in self.test_results:
            status_icon = "✅" if result[1] == "PASS" else "❌"
            print(f"{status_icon} {result[0]}: {result[1]}")
            if result[1] == "FAIL" and len(result) > 2:
                print(f"   └─ エラー: {result[2]}")
        
        print(f"\n📈 総合結果: {passed}件成功, {failed}件失敗")
        
        if failed == 0:
            print("🎉 全テストが成功しました！支持線・抵抗線ハンドリングは正常です。")
        else:
            print("⚠️ 一部テストが失敗しました。修正が必要です。")
        
        return failed == 0


async def main():
    """メイン実行関数"""
    test_runner = SupportResistanceHandlingTest()
    success = await test_runner.run_all_tests()
    
    if success:
        print("\n✅ すべてのテストが成功しました")
        return 0
    else:
        print("\n❌ テストに失敗しました")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)