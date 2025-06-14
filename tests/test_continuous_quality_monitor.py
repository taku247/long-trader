#!/usr/bin/env python3
"""
継続的品質監視テストスイート

目的:
1. 銘柄追加後のトレード結果品質を自動チェック
2. 異常なバックテスト結果の早期検知
3. CI/CDパイプラインでの品質ゲート

特徴:
- 新規銘柄追加時の自動実行
- Slack/メール通知連携
- 品質メトリクスのトレンド監視
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np
import pickle
import gzip
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Any, Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TradeResultQualityMonitor(unittest.TestCase):
    """トレード結果品質監視"""
    
    def setUp(self):
        """テスト前準備"""
        self.compressed_dir = Path("large_scale_analysis/compressed")
        self.quality_thresholds = {
            'min_unique_entry_prices': 5,      # 最小固有エントリー価格数
            'min_price_variation_cv': 0.01,    # 最小変動係数
            'max_market_deviation_pct': 25,    # 最大市場価格乖離率
            'min_trades_per_strategy': 10,     # 戦略あたり最小トレード数
            'max_identical_price_ratio': 0.5   # 同一価格の最大比率
        }
        
    def test_new_symbols_have_valid_price_distribution(self):
        """新規銘柄の価格分布が妥当であることを確認"""
        recent_symbols = self._get_recently_added_symbols(days=7)
        
        if not recent_symbols:
            self.skipTest("過去7日間に追加された新規銘柄がありません")
        
        quality_issues = []
        
        for symbol in recent_symbols:
            issues = self._analyze_symbol_price_quality(symbol)
            if issues:
                quality_issues.extend(issues)
        
        self.assertEqual(len(quality_issues), 0,
                        f"新規銘柄で品質問題を検出: {quality_issues}")
    
    def test_all_strategies_use_dynamic_pricing(self):
        """全戦略が動的価格設定を使用していることを確認"""
        static_pricing_strategies = self._detect_static_pricing_strategies()
        
        self.assertEqual(len(static_pricing_strategies), 0,
                        f"静的価格設定を使用している戦略: {static_pricing_strategies}")
    
    def test_backtest_results_are_realistic(self):
        """バックテスト結果が現実的であることを確認"""
        unrealistic_results = self._detect_unrealistic_backtest_results()
        
        self.assertEqual(len(unrealistic_results), 0,
                        f"非現実的なバックテスト結果: {unrealistic_results}")
    
    def test_price_calculation_consistency(self):
        """価格計算の一貫性を確認"""
        inconsistencies = self._check_price_calculation_consistency()
        
        self.assertEqual(len(inconsistencies), 0,
                        f"価格計算の一貫性違反: {inconsistencies}")
    
    def _get_recently_added_symbols(self, days: int = 7) -> List[str]:
        """最近追加された銘柄を取得"""
        recent_symbols = set()
        
        if not self.compressed_dir.exists():
            return list(recent_symbols)
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for file_path in self.compressed_dir.glob("*.pkl.gz"):
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime > cutoff_time:
                    parts = file_path.stem.replace('.pkl', '').split('_')
                    if len(parts) >= 1:
                        recent_symbols.add(parts[0])
            except Exception:
                continue
        
        return list(recent_symbols)
    
    def _analyze_symbol_price_quality(self, symbol: str) -> List[Dict]:
        """銘柄の価格品質を分析"""
        issues = []
        
        symbol_files = list(self.compressed_dir.glob(f"{symbol}_*.pkl.gz"))
        
        for file_path in symbol_files:
            try:
                with gzip.open(file_path, 'rb') as f:
                    trades_data = pickle.load(f)
                
                if isinstance(trades_data, list):
                    df = pd.DataFrame(trades_data)
                elif isinstance(trades_data, dict):
                    df = pd.DataFrame(trades_data)
                else:
                    df = trades_data
                
                if df.empty:
                    continue
                
                # 戦略情報を抽出
                parts = file_path.stem.replace('.pkl', '').split('_')
                if len(parts) >= 3:
                    timeframe = parts[1]
                    strategy = '_'.join(parts[2:])
                else:
                    continue
                
                # 品質チェック
                strategy_issues = self._check_strategy_quality(
                    df, symbol, timeframe, strategy
                )
                issues.extend(strategy_issues)
            
            except Exception as e:
                issues.append({
                    'symbol': symbol,
                    'file': str(file_path),
                    'issue_type': 'FILE_READ_ERROR',
                    'description': f"ファイル読み込みエラー: {e}",
                    'severity': 'HIGH'
                })
        
        return issues
    
    def _check_strategy_quality(self, df: pd.DataFrame, symbol: str, 
                              timeframe: str, strategy: str) -> List[Dict]:
        """戦略の品質をチェック"""
        issues = []
        
        # 1. トレード数チェック
        if len(df) < self.quality_thresholds['min_trades_per_strategy']:
            issues.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy': strategy,
                'issue_type': 'INSUFFICIENT_TRADES',
                'description': f"トレード数不足: {len(df)}件",
                'severity': 'MEDIUM'
            })
        
        # 2. エントリー価格の品質チェック
        if 'entry_price' in df.columns:
            entry_issues = self._check_price_column_quality(
                df, 'entry_price', symbol, timeframe, strategy
            )
            issues.extend(entry_issues)
        
        # 3. TP/SL価格の品質チェック
        for price_col in ['take_profit_price', 'stop_loss_price']:
            if price_col in df.columns:
                price_issues = self._check_price_column_quality(
                    df, price_col, symbol, timeframe, strategy
                )
                issues.extend(price_issues)
        
        # 4. 価格関係の論理チェック
        logic_issues = self._check_price_logic(df, symbol, timeframe, strategy)
        issues.extend(logic_issues)
        
        return issues
    
    def _check_price_column_quality(self, df: pd.DataFrame, column: str,
                                   symbol: str, timeframe: str, strategy: str) -> List[Dict]:
        """価格カラムの品質をチェック"""
        issues = []
        
        values = pd.to_numeric(df[column], errors='coerce').dropna()
        if len(values) == 0:
            return issues
        
        # 1. 固有値数チェック
        unique_count = len(values.unique())
        if unique_count < self.quality_thresholds['min_unique_entry_prices']:
            issues.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy': strategy,
                'column': column,
                'issue_type': 'LOW_PRICE_DIVERSITY',
                'description': f"固有価格数不足: {unique_count}種類",
                'severity': 'HIGH'
            })
        
        # 2. 変動係数チェック
        if len(values) > 1:
            cv = values.std() / values.mean() if values.mean() > 0 else 0
            if cv < self.quality_thresholds['min_price_variation_cv']:
                issues.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'strategy': strategy,
                    'column': column,
                    'issue_type': 'LOW_PRICE_VARIATION',
                    'description': f"価格変動不足: CV={cv:.6f}",
                    'severity': 'HIGH'
                })
        
        # 3. 同一値比率チェック
        value_counts = values.value_counts()
        if len(value_counts) > 0:
            most_common_ratio = value_counts.iloc[0] / len(values)
            if most_common_ratio > self.quality_thresholds['max_identical_price_ratio']:
                issues.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'strategy': strategy,
                    'column': column,
                    'issue_type': 'HIGH_IDENTICAL_PRICE_RATIO',
                    'description': f"同一価格比率: {most_common_ratio:.1%}",
                    'severity': 'HIGH'
                })
        
        return issues
    
    def _check_price_logic(self, df: pd.DataFrame, symbol: str,
                          timeframe: str, strategy: str) -> List[Dict]:
        """価格の論理的妥当性をチェック"""
        issues = []
        
        required_cols = ['entry_price', 'take_profit_price', 'stop_loss_price']
        if not all(col in df.columns for col in required_cols):
            return issues
        
        entry_prices = pd.to_numeric(df['entry_price'], errors='coerce').dropna()
        tp_prices = pd.to_numeric(df['take_profit_price'], errors='coerce').dropna()
        sl_prices = pd.to_numeric(df['stop_loss_price'], errors='coerce').dropna()
        
        if len(entry_prices) == 0 or len(tp_prices) == 0 or len(sl_prices) == 0:
            return issues
        
        # ロングポジション前提でのチェック
        min_length = min(len(entry_prices), len(tp_prices), len(sl_prices))
        
        # TP > Entry チェック
        invalid_tp = sum(tp <= entry for tp, entry in 
                        zip(tp_prices[:min_length], entry_prices[:min_length]))
        if invalid_tp > 0:
            issues.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy': strategy,
                'issue_type': 'INVALID_TP_LOGIC',
                'description': f"利確価格がエントリー以下: {invalid_tp}件",
                'severity': 'HIGH'
            })
        
        # SL < Entry チェック
        invalid_sl = sum(sl >= entry for sl, entry in 
                        zip(sl_prices[:min_length], entry_prices[:min_length]))
        if invalid_sl > 0:
            issues.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy': strategy,
                'issue_type': 'INVALID_SL_LOGIC',
                'description': f"損切価格がエントリー以上: {invalid_sl}件",
                'severity': 'HIGH'
            })
        
        return issues
    
    def _detect_static_pricing_strategies(self) -> List[Dict]:
        """静的価格設定を使用している戦略を検出"""
        static_strategies = []
        
        if not self.compressed_dir.exists():
            return static_strategies
        
        for file_path in self.compressed_dir.glob("*.pkl.gz"):
            try:
                with gzip.open(file_path, 'rb') as f:
                    trades_data = pickle.load(f)
                
                if isinstance(trades_data, list):
                    df = pd.DataFrame(trades_data)
                elif isinstance(trades_data, dict):
                    df = pd.DataFrame(trades_data)
                else:
                    df = trades_data
                
                if df.empty:
                    continue
                
                # 戦略情報を抽出
                parts = file_path.stem.replace('.pkl', '').split('_')
                if len(parts) >= 3:
                    symbol = parts[0]
                    timeframe = parts[1]
                    strategy = '_'.join(parts[2:])
                else:
                    continue
                
                # 静的価格設定をチェック
                if 'entry_price' in df.columns:
                    entry_prices = pd.to_numeric(df['entry_price'], errors='coerce').dropna()
                    
                    if len(entry_prices) > 5:  # 十分なサンプル
                        unique_count = len(entry_prices.unique())
                        cv = entry_prices.std() / entry_prices.mean() if entry_prices.mean() > 0 else 0
                        
                        # 静的価格設定の疑い
                        if unique_count <= 2 or cv < 0.001:
                            static_strategies.append({
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'strategy': strategy,
                                'unique_prices': unique_count,
                                'coefficient_of_variation': cv,
                                'total_trades': len(entry_prices)
                            })
            
            except Exception:
                continue
        
        return static_strategies
    
    def _detect_unrealistic_backtest_results(self) -> List[Dict]:
        """非現実的なバックテスト結果を検出"""
        unrealistic_results = []
        
        if not self.compressed_dir.exists():
            return unrealistic_results
        
        for file_path in self.compressed_dir.glob("*.pkl.gz"):
            try:
                with gzip.open(file_path, 'rb') as f:
                    trades_data = pickle.load(f)
                
                if isinstance(trades_data, list):
                    df = pd.DataFrame(trades_data)
                elif isinstance(trades_data, dict):
                    df = pd.DataFrame(trades_data)
                else:
                    df = trades_data
                
                if df.empty or len(df) < 10:
                    continue
                
                # 戦略情報を抽出
                parts = file_path.stem.replace('.pkl', '').split('_')
                if len(parts) >= 3:
                    symbol = parts[0]
                    timeframe = parts[1]
                    strategy = '_'.join(parts[2:])
                else:
                    continue
                
                # 非現実的な結果をチェック
                unrealistic_checks = self._check_unrealistic_metrics(df, symbol, timeframe, strategy)
                unrealistic_results.extend(unrealistic_checks)
            
            except Exception:
                continue
        
        return unrealistic_results
    
    def _check_unrealistic_metrics(self, df: pd.DataFrame, symbol: str, 
                                  timeframe: str, strategy: str) -> List[Dict]:
        """非現実的なメトリクスをチェック"""
        issues = []
        
        # PnL関連チェック
        if 'pnl' in df.columns:
            pnl_values = pd.to_numeric(df['pnl'], errors='coerce').dropna()
            
            if len(pnl_values) > 0:
                # 勝率チェック
                win_rate = (pnl_values > 0).mean()
                if win_rate > 0.95:  # 95%以上の勝率は非現実的
                    issues.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'strategy': strategy,
                        'issue_type': 'UNREALISTIC_WIN_RATE',
                        'description': f"勝率が非現実的: {win_rate:.1%}",
                        'severity': 'HIGH'
                    })
                
                # 平均利益チェック
                avg_profit = pnl_values.mean()
                if avg_profit > 50:  # 平均50%以上の利益は非現実的
                    issues.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'strategy': strategy,
                        'issue_type': 'UNREALISTIC_AVG_PROFIT',
                        'description': f"平均利益が非現実的: {avg_profit:.1f}%",
                        'severity': 'HIGH'
                    })
        
        return issues
    
    def _check_price_calculation_consistency(self) -> List[Dict]:
        """価格計算の一貫性をチェック"""
        inconsistencies = []
        
        # 同一銘柄・同一時間足での戦略間価格差をチェック
        symbol_timeframe_groups = {}
        
        if not self.compressed_dir.exists():
            return inconsistencies
        
        for file_path in self.compressed_dir.glob("*.pkl.gz"):
            try:
                parts = file_path.stem.replace('.pkl', '').split('_')
                if len(parts) >= 3:
                    symbol = parts[0]
                    timeframe = parts[1]
                    strategy = '_'.join(parts[2:])
                    
                    key = f"{symbol}_{timeframe}"
                    if key not in symbol_timeframe_groups:
                        symbol_timeframe_groups[key] = []
                    
                    symbol_timeframe_groups[key].append({
                        'strategy': strategy,
                        'file_path': file_path
                    })
            except Exception:
                continue
        
        # 各グループで一貫性をチェック
        for key, strategies in symbol_timeframe_groups.items():
            if len(strategies) > 1:
                symbol, timeframe = key.split('_', 1)
                consistency_issues = self._check_strategy_group_consistency(
                    symbol, timeframe, strategies
                )
                inconsistencies.extend(consistency_issues)
        
        return inconsistencies
    
    def _check_strategy_group_consistency(self, symbol: str, timeframe: str, 
                                        strategies: List[Dict]) -> List[Dict]:
        """戦略グループの一貫性をチェック"""
        issues = []
        
        strategy_prices = {}
        
        for strategy_info in strategies:
            try:
                with gzip.open(strategy_info['file_path'], 'rb') as f:
                    trades_data = pickle.load(f)
                
                if isinstance(trades_data, list):
                    df = pd.DataFrame(trades_data)
                elif isinstance(trades_data, dict):
                    df = pd.DataFrame(trades_data)
                else:
                    df = trades_data
                
                if df.empty or 'entry_price' not in df.columns:
                    continue
                
                entry_prices = pd.to_numeric(df['entry_price'], errors='coerce').dropna()
                if len(entry_prices) > 0:
                    strategy_prices[strategy_info['strategy']] = entry_prices.mean()
            
            except Exception:
                continue
        
        # 戦略間の価格差をチェック
        if len(strategy_prices) > 1:
            prices = list(strategy_prices.values())
            price_range = max(prices) - min(prices)
            avg_price = np.mean(prices)
            
            # 平均価格の10%以上の差は一貫性の問題
            if price_range > avg_price * 0.1:
                issues.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'issue_type': 'PRICE_INCONSISTENCY_BETWEEN_STRATEGIES',
                    'description': f"戦略間価格差: {price_range:.6f} (平均の{price_range/avg_price:.1%})",
                    'strategy_prices': strategy_prices,
                    'severity': 'MEDIUM'
                })
        
        return issues

class QualityMetricsReporter:
    """品質メトリクスレポーター"""
    
    @staticmethod
    def generate_quality_report(test_result: unittest.TestResult) -> Dict[str, Any]:
        """品質レポートを生成"""
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'PASS' if test_result.wasSuccessful() else 'FAIL',
            'tests_run': test_result.testsRun,
            'failures': len(test_result.failures),
            'errors': len(test_result.errors),
            'issues_detected': [],
            'recommendations': []
        }
        
        # 失敗したテストからの問題抽出
        for test, traceback in test_result.failures:
            if 'ハードコード値を検出' in traceback:
                report['issues_detected'].append({
                    'type': 'HARDCODED_VALUES',
                    'severity': 'HIGH',
                    'description': 'ハードコード値が検出されました'
                })
                report['recommendations'].append(
                    'scalable_analysis_system.pyとhigh_leverage_bot_orchestrator.pyのハードコード値を除去してください'
                )
            
            if '品質問題を検出' in traceback:
                report['issues_detected'].append({
                    'type': 'QUALITY_ISSUES',
                    'severity': 'HIGH',
                    'description': '新規銘柄で品質問題が検出されました'
                })
                report['recommendations'].append(
                    '価格計算ロジックを見直し、動的価格生成を確保してください'
                )
        
        return report
    
    @staticmethod
    def save_report(report: Dict[str, Any], filename: str = None):
        """レポートを保存"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"quality_report_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return filename

if __name__ == '__main__':
    print("🎯 継続的品質監視テストスイート")
    print("=" * 60)
    
    # テストスイート実行
    suite = unittest.TestLoader().loadTestsFromTestCase(TradeResultQualityMonitor)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 品質レポート生成
    reporter = QualityMetricsReporter()
    quality_report = reporter.generate_quality_report(result)
    report_file = reporter.save_report(quality_report)
    
    print("\n" + "=" * 60)
    print("📊 品質監視結果")
    print("=" * 60)
    print(f"全体ステータス: {quality_report['overall_status']}")
    print(f"実行テスト数: {quality_report['tests_run']}")
    print(f"失敗: {quality_report['failures']}")
    print(f"エラー: {quality_report['errors']}")
    print(f"品質レポート: {report_file}")
    
    if quality_report['issues_detected']:
        print("\n⚠️  検出された問題:")
        for issue in quality_report['issues_detected']:
            print(f"  - {issue['type']}: {issue['description']}")
    
    if quality_report['recommendations']:
        print("\n💡 推奨事項:")
        for rec in quality_report['recommendations']:
            print(f"  - {rec}")
    
    # CI/CD用終了コード
    exit_code = 1 if not result.wasSuccessful() else 0
    exit(exit_code)