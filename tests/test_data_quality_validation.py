#!/usr/bin/env python3
"""
データ品質検証テスト
トレードデータの異常を自動検知するテストスイート
"""

import unittest
import sys
import os
from pathlib import Path
import numpy as np
from typing import Dict, List, Any

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from scalable_analysis_system import ScalableAnalysisSystem


class TestDataQualityValidation(unittest.TestCase):
    """データ品質検証テスト"""
    
    def setUp(self):
        """テスト準備"""
        self.system = ScalableAnalysisSystem()
        self.max_acceptable_duplicates_ratio = 0.05  # 5%以下の重複は許容
        self.min_leverage_diversity_threshold = 0.1  # レバレッジ多様性の最小閾値
        self.min_price_diversity_threshold = 0.05   # 価格多様性の最小閾値
        self.max_acceptable_win_rate = 0.85          # 85%以上の勝率は異常
        self.min_acceptable_win_rate = 0.15          # 15%以下の勝率は異常
    
    def get_trade_data_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """指定銘柄の全トレードデータを取得"""
        results_df = self.system.query_analyses(filters={'symbol': symbol})
        if results_df.empty:
            return []
        
        all_trades = []
        for _, row in results_df.iterrows():
            trades_df = self.system.load_compressed_trades(
                row['symbol'], row['timeframe'], row['config']
            )
            if trades_df is not None and not (hasattr(trades_df, 'empty') and trades_df.empty):
                if hasattr(trades_df, 'to_dict'):
                    trades = trades_df.to_dict('records')
                else:
                    trades = trades_df if isinstance(trades_df, list) else []
                all_trades.extend(trades)
        
        return all_trades
    
    def test_leverage_diversity(self):
        """レバレッジの多様性をテスト"""
        print("\n🔍 レバレッジ多様性テスト実行中...")
        
        # 全銘柄の分析結果を取得
        all_results = self.system.query_analyses()
        if all_results.empty:
            self.skipTest("分析データが存在しません")
        
        symbols = all_results['symbol'].unique()
        failed_symbols = []
        
        for symbol in symbols:
            trades = self.get_trade_data_for_symbol(symbol)
            if len(trades) < 10:  # 10取引未満はスキップ
                continue
            
            leverages = [float(t.get('leverage', 0)) for t in trades]
            leverage_unique = len(set(leverages))
            leverage_std = np.std(leverages) if leverages else 0
            
            # レバレッジが完全に固定されている場合
            if leverage_unique == 1 and len(trades) > 10:
                failed_symbols.append({
                    'symbol': symbol,
                    'issue': 'レバレッジ完全固定',
                    'details': f'全{len(trades)}取引で同一レバレッジ({leverages[0]:.1f}x)',
                    'total_trades': len(trades)
                })
            
            # レバレッジの標準偏差が極めて小さい場合
            elif leverage_std < self.min_leverage_diversity_threshold and len(trades) > 10:
                failed_symbols.append({
                    'symbol': symbol,
                    'issue': 'レバレッジ分散不足',
                    'details': f'標準偏差: {leverage_std:.6f} (閾値: {self.min_leverage_diversity_threshold})',
                    'total_trades': len(trades)
                })
        
        if failed_symbols:
            error_msg = "🚨 レバレッジ多様性テスト失敗:\n"
            for failure in failed_symbols:
                error_msg += f"  - {failure['symbol']}: {failure['issue']} ({failure['details']})\n"
            self.fail(error_msg)
        
        print(f"✅ レバレッジ多様性テスト合格 ({len(symbols)}銘柄検証)")
    
    def test_entry_price_diversity(self):
        """エントリー価格の多様性をテスト"""
        print("\n🔍 エントリー価格多様性テスト実行中...")
        
        all_results = self.system.query_analyses()
        if all_results.empty:
            self.skipTest("分析データが存在しません")
        
        symbols = all_results['symbol'].unique()
        failed_symbols = []
        
        for symbol in symbols:
            trades = self.get_trade_data_for_symbol(symbol)
            if len(trades) < 10:
                continue
            
            entry_prices = [float(t.get('entry_price', 0)) for t in trades if t.get('entry_price')]
            if not entry_prices:
                continue
            
            entry_price_unique = len(set(entry_prices))
            diversity_ratio = entry_price_unique / len(entry_prices)
            
            # エントリー価格が完全に固定されている場合
            if entry_price_unique == 1 and len(entry_prices) > 10:
                failed_symbols.append({
                    'symbol': symbol,
                    'issue': 'エントリー価格完全固定',
                    'details': f'全{len(entry_prices)}取引で同一価格({entry_prices[0]:.2f})',
                    'total_trades': len(trades)
                })
            
            # エントリー価格の多様性が不足している場合
            elif diversity_ratio < self.min_price_diversity_threshold and len(entry_prices) > 20:
                failed_symbols.append({
                    'symbol': symbol,
                    'issue': 'エントリー価格多様性不足',
                    'details': f'多様性比率: {diversity_ratio:.1%} (閾値: {self.min_price_diversity_threshold:.1%})',
                    'total_trades': len(trades)
                })
        
        if failed_symbols:
            error_msg = "🚨 エントリー価格多様性テスト失敗:\n"
            for failure in failed_symbols:
                error_msg += f"  - {failure['symbol']}: {failure['issue']} ({failure['details']})\n"
            self.fail(error_msg)
        
        print(f"✅ エントリー価格多様性テスト合格 ({len(symbols)}銘柄検証)")
    
    def test_entry_time_uniqueness(self):
        """エントリー時刻の一意性をテスト"""
        print("\n🔍 エントリー時刻一意性テスト実行中...")
        
        all_results = self.system.query_analyses()
        if all_results.empty:
            self.skipTest("分析データが存在しません")
        
        symbols = all_results['symbol'].unique()
        failed_symbols = []
        
        for symbol in symbols:
            trades = self.get_trade_data_for_symbol(symbol)
            if len(trades) < 10:
                continue
            
            entry_times = [t.get('entry_time', 'N/A') for t in trades]
            entry_time_unique = len(set(entry_times))
            duplicates = len(entry_times) - entry_time_unique
            duplicate_ratio = duplicates / len(entry_times)
            
            # 重複が多すぎる場合
            if duplicate_ratio > self.max_acceptable_duplicates_ratio:
                # 重複詳細を取得
                time_counts = {}
                for t in entry_times:
                    time_counts[t] = time_counts.get(t, 0) + 1
                
                duplicate_details = {k: v for k, v in time_counts.items() if v > 1}
                max_duplicates = max(duplicate_details.values()) if duplicate_details else 0
                
                failed_symbols.append({
                    'symbol': symbol,
                    'issue': 'エントリー時刻重複過多',
                    'details': f'{duplicates}件重複 ({duplicate_ratio:.1%}), 最大{max_duplicates}回重複',
                    'total_trades': len(trades)
                })
        
        if failed_symbols:
            error_msg = "🚨 エントリー時刻一意性テスト失敗:\n"
            for failure in failed_symbols:
                error_msg += f"  - {failure['symbol']}: {failure['issue']} ({failure['details']})\n"
            self.fail(error_msg)
        
        print(f"✅ エントリー時刻一意性テスト合格 ({len(symbols)}銘柄検証)")
    
    def test_win_rate_realism(self):
        """勝率の現実性をテスト"""
        print("\n🔍 勝率現実性テスト実行中...")
        
        all_results = self.system.query_analyses()
        if all_results.empty:
            self.skipTest("分析データが存在しません")
        
        symbols = all_results['symbol'].unique()
        failed_symbols = []
        
        for symbol in symbols:
            trades = self.get_trade_data_for_symbol(symbol)
            if len(trades) < 50:  # 50取引未満はスキップ
                continue
            
            win_count = sum(1 for t in trades if t.get('is_success', t.get('is_win', False)))
            win_rate = win_count / len(trades)
            
            # 勝率が異常に高い場合
            if win_rate > self.max_acceptable_win_rate:
                failed_symbols.append({
                    'symbol': symbol,
                    'issue': '勝率異常に高い',
                    'details': f'勝率: {win_rate:.1%} (上限: {self.max_acceptable_win_rate:.1%})',
                    'total_trades': len(trades)
                })
            
            # 勝率が異常に低い場合
            elif win_rate < self.min_acceptable_win_rate:
                failed_symbols.append({
                    'symbol': symbol,
                    'issue': '勝率異常に低い',
                    'details': f'勝率: {win_rate:.1%} (下限: {self.min_acceptable_win_rate:.1%})',
                    'total_trades': len(trades)
                })
        
        if failed_symbols:
            error_msg = "🚨 勝率現実性テスト失敗:\n"
            for failure in failed_symbols:
                error_msg += f"  - {failure['symbol']}: {failure['issue']} ({failure['details']})\n"
            self.fail(error_msg)
        
        print(f"✅ 勝率現実性テスト合格 ({len(symbols)}銘柄検証)")
    
    def test_test_orchestrator_not_used_in_production(self):
        """本番環境でテスト用Orchestratorが使用されていないことをテスト"""
        print("\n🔍 本番環境テスト用Orchestrator使用チェック...")
        
        # 最近の実行ログをチェック
        try:
            from execution_log_database import ExecutionLogDatabase
            exec_db = ExecutionLogDatabase()
            
            recent_executions = exec_db.list_executions(limit=10)
            
            for execution in recent_executions:
                # 実行ログにテスト用の文言やパターンがないかチェック
                details = execution.get('details', '')
                orchestrator_type = execution.get('orchestrator_type', '')
                
                # テスト用Orchestratorの使用を示す文言をチェック
                test_indicators = [
                    'TestHighLeverageBotOrchestrator',
                    'test_high_leverage_bot_orchestrator',
                    'Using test orchestrator',
                    'Test mode',
                    'Sample data generation'
                ]
                
                for indicator in test_indicators:
                    if indicator.lower() in details.lower() or indicator.lower() in orchestrator_type.lower():
                        self.fail(f"🚨 本番環境でテスト用Orchestratorが使用されています: {execution.get('execution_id', 'Unknown')} - {indicator}")
            
            print("✅ 本番環境テスト用Orchestrator使用チェック合格")
            
        except ImportError:
            print("⚠️ ExecutionLogDatabase import失敗 - スキップ")
        except Exception as e:
            print(f"⚠️ 実行ログチェック失敗: {e} - スキップ")
    
    def test_hardcoded_values_detection(self):
        """ハードコードされた値の検出テスト"""
        print("\n🔍 ハードコード値検出テスト実行中...")
        
        all_results = self.system.query_analyses()
        if all_results.empty:
            self.skipTest("分析データが存在しません")
        
        symbols = all_results['symbol'].unique()
        suspicious_patterns = []
        
        for symbol in symbols:
            trades = self.get_trade_data_for_symbol(symbol)
            if len(trades) < 20:
                continue
            
            # 疑わしい固定値パターンを検出
            leverages = [float(t.get('leverage', 0)) for t in trades]
            entry_prices = [float(t.get('entry_price', 0)) for t in trades if t.get('entry_price')]
            
            # 特定の値（18.91, 2.1など）が大量に出現するかチェック
            if leverages:
                most_common_leverage = max(set(leverages), key=leverages.count)
                leverage_count = leverages.count(most_common_leverage)
                
                # 特定のレバレッジが80%以上使用されている場合
                if leverage_count / len(leverages) > 0.8:
                    suspicious_patterns.append({
                        'symbol': symbol,
                        'issue': 'レバレッジ偏重使用',
                        'details': f'レバレッジ{most_common_leverage}が{leverage_count}/{len(leverages)}回使用',
                        'value': most_common_leverage
                    })
            
            if entry_prices:
                most_common_price = max(set(entry_prices), key=entry_prices.count)
                price_count = entry_prices.count(most_common_price)
                
                # 特定の価格が80%以上使用されている場合
                if price_count / len(entry_prices) > 0.8:
                    suspicious_patterns.append({
                        'symbol': symbol,
                        'issue': 'エントリー価格偏重使用',
                        'details': f'価格{most_common_price}が{price_count}/{len(entry_prices)}回使用',
                        'value': most_common_price
                    })
        
        if suspicious_patterns:
            error_msg = "🚨 ハードコード値検出テスト失敗 - 疑わしいパターン:\n"
            for pattern in suspicious_patterns:
                error_msg += f"  - {pattern['symbol']}: {pattern['issue']} ({pattern['details']})\n"
            self.fail(error_msg)
        
        print(f"✅ ハードコード値検出テスト合格 ({len(symbols)}銘柄検証)")
    
    def run_comprehensive_data_quality_check(self):
        """包括的なデータ品質チェックを実行"""
        print("\n" + "="*60)
        print("🔍 包括的データ品質チェック開始")
        print("="*60)
        
        test_methods = [
            self.test_leverage_diversity,
            self.test_entry_price_diversity,
            self.test_entry_time_uniqueness,
            self.test_win_rate_realism,
            self.test_test_orchestrator_not_used_in_production,
            self.test_hardcoded_values_detection
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for test_method in test_methods:
            try:
                test_method()
                passed_tests += 1
            except Exception as e:
                print(f"❌ {test_method.__name__} 失敗: {e}")
                failed_tests += 1
        
        print("\n" + "="*60)
        print(f"📊 データ品質チェック結果: 合格 {passed_tests}/{len(test_methods)} (失敗: {failed_tests})")
        print("="*60)
        
        return failed_tests == 0


if __name__ == '__main__':
    # 包括的なデータ品質チェックを実行
    test_suite = TestDataQualityValidation()
    test_suite.setUp()
    
    success = test_suite.run_comprehensive_data_quality_check()
    
    if not success:
        print("\n🚨 データ品質に問題があります。修正が必要です。")
        sys.exit(1)
    else:
        print("\n✅ 全データ品質チェックが合格しました。")
        sys.exit(0)