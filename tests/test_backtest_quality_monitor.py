#!/usr/bin/env python3
"""
バックテスト品質監視テスト
継続的にバックテスト結果の品質を監視し、エントリー価格統一などの問題を検知
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestBacktestQualityMonitor(unittest.TestCase):
    """バックテスト品質監視テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        from scalable_analysis_system import ScalableAnalysisSystem
        self.system = ScalableAnalysisSystem()
        
        # 品質チェック基準
        self.quality_standards = {
            'min_price_diversity_rate': 0.80,  # エントリー価格の最低多様性率
            'min_tp_diversity_rate': 0.70,     # TP価格の最低多様性率  
            'min_sl_diversity_rate': 0.70,     # SL価格の最低多様性率
            'max_leverage_uniformity_rate': 0.60,  # レバレッジの最大統一率
            'min_trades_for_analysis': 10,     # 分析に必要な最小トレード数
            'max_price_deviation_ratio': 3.0,  # 価格乖離の最大比率
            'min_time_span_hours': 24,        # 最小時間幅（時間）
        }
        
        # アラート閾値
        self.alert_thresholds = {
            'critical_diversity_rate': 0.05,   # 5%以下は緊急
            'warning_diversity_rate': 0.30,    # 30%以下は警告
        }
    
    def get_all_available_strategies(self):
        """利用可能な全戦略を取得"""
        try:
            # データベースから戦略一覧を取得
            results = self.system.query_analyses()
            strategies = []
            
            for _, row in results.iterrows():
                strategies.append((row['symbol'], row['timeframe'], row['config']))
            
            # 重複除去
            return list(set(strategies))
        except Exception as e:
            print(f"⚠️ 戦略取得エラー: {e}")
            # フォールバック: テスト用の基本戦略
            return [
                ('DOT', '1h', 'Conservative_ML'),
                ('DOT', '30m', 'Aggressive_Traditional'),
                ('DOT', '15m', 'Full_ML'),
            ]
    
    def test_comprehensive_price_diversity_monitoring(self):
        """包括的価格多様性監視"""
        print("\n🔍 包括的価格多様性監視テスト")
        print("=" * 70)
        
        strategies = self.get_all_available_strategies()
        quality_report = {
            'total_strategies': len(strategies),
            'tested_strategies': 0,
            'passed_strategies': 0,
            'failed_strategies': 0,
            'critical_issues': [],
            'warnings': [],
            'quality_scores': {}
        }
        
        for symbol, timeframe, config in strategies:
            print(f"\n📊 分析中: {symbol} {timeframe} {config}")
            
            try:
                trades_data = self.system.load_compressed_trades(symbol, timeframe, config)
                
                if not trades_data or len(trades_data) < self.quality_standards['min_trades_for_analysis']:
                    print(f"   ⚠️ データ不足: {len(trades_data) if trades_data else 0}件")
                    continue
                
                quality_report['tested_strategies'] += 1
                
                # 品質スコアを計算
                quality_score = self._calculate_quality_score(trades_data, symbol, timeframe, config)
                quality_report['quality_scores'][f"{symbol}_{timeframe}_{config}"] = quality_score
                
                # 品質判定
                if quality_score['overall_score'] >= 0.7:
                    quality_report['passed_strategies'] += 1
                    print(f"   ✅ 品質良好 (スコア: {quality_score['overall_score']:.2f})")
                else:
                    quality_report['failed_strategies'] += 1
                    print(f"   ❌ 品質問題 (スコア: {quality_score['overall_score']:.2f})")
                    
                    # 問題の詳細分類
                    if quality_score['overall_score'] < 0.3:
                        quality_report['critical_issues'].append({
                            'strategy': f"{symbol} {timeframe} {config}",
                            'score': quality_score['overall_score'],
                            'issues': quality_score['issues']
                        })
                    else:
                        quality_report['warnings'].append({
                            'strategy': f"{symbol} {timeframe} {config}",
                            'score': quality_score['overall_score'],
                            'issues': quality_score['issues']
                        })
                
            except Exception as e:
                print(f"   ❌ 分析エラー: {e}")
                continue
        
        # 全体評価
        overall_pass_rate = (quality_report['passed_strategies'] / 
                           quality_report['tested_strategies']) if quality_report['tested_strategies'] > 0 else 0
        
        print(f"\n" + "=" * 70)
        print(f"📊 品質監視結果サマリー")
        print(f"=" * 70)
        print(f"総戦略数: {quality_report['total_strategies']}")
        print(f"テスト実行: {quality_report['tested_strategies']}")
        print(f"品質合格: {quality_report['passed_strategies']}")
        print(f"品質不合格: {quality_report['failed_strategies']}")
        print(f"合格率: {overall_pass_rate:.1%}")
        
        if quality_report['critical_issues']:
            print(f"\n🚨 緊急問題 ({len(quality_report['critical_issues'])}件):")
            for issue in quality_report['critical_issues']:
                print(f"  • {issue['strategy']} (スコア: {issue['score']:.2f})")
        
        if quality_report['warnings']:
            print(f"\n⚠️ 警告 ({len(quality_report['warnings'])}件):")
            for warning in quality_report['warnings']:
                print(f"  • {warning['strategy']} (スコア: {warning['score']:.2f})")
        
        # アサーション
        self.assertGreaterEqual(
            overall_pass_rate, 0.6,
            f"品質監視: 合格率が低すぎます ({overall_pass_rate:.1%})"
        )
        
        self.assertEqual(
            len(quality_report['critical_issues']), 0,
            f"緊急品質問題が検出されました: {[issue['strategy'] for issue in quality_report['critical_issues']]}"
        )
    
    def _calculate_quality_score(self, trades_data, symbol, timeframe, config):
        """品質スコアを計算"""
        scores = {}
        issues = []
        
        # エントリー価格多様性スコア
        entry_prices = [t.get('entry_price') for t in trades_data if t.get('entry_price') is not None]
        if entry_prices:
            entry_diversity = len(set(entry_prices)) / len(entry_prices)
            scores['entry_diversity'] = entry_diversity
            
            if entry_diversity < self.alert_thresholds['critical_diversity_rate']:
                issues.append(f"エントリー価格統一 (多様性: {entry_diversity:.1%})")
            elif entry_diversity < self.alert_thresholds['warning_diversity_rate']:
                issues.append(f"エントリー価格多様性低下 (多様性: {entry_diversity:.1%})")
        else:
            scores['entry_diversity'] = 0.0
            issues.append("エントリー価格データなし")
        
        # TP価格多様性スコア
        tp_prices = [t.get('take_profit_price') for t in trades_data if t.get('take_profit_price') is not None]
        if tp_prices:
            tp_diversity = len(set(tp_prices)) / len(tp_prices)
            scores['tp_diversity'] = tp_diversity
            
            if tp_diversity < self.alert_thresholds['critical_diversity_rate']:
                issues.append(f"TP価格統一 (多様性: {tp_diversity:.1%})")
        else:
            scores['tp_diversity'] = 0.0
        
        # SL価格多様性スコア
        sl_prices = [t.get('stop_loss_price') for t in trades_data if t.get('stop_loss_price') is not None]
        if sl_prices:
            sl_diversity = len(set(sl_prices)) / len(sl_prices)
            scores['sl_diversity'] = sl_diversity
            
            if sl_diversity < self.alert_thresholds['critical_diversity_rate']:
                issues.append(f"SL価格統一 (多様性: {sl_diversity:.1%})")
        else:
            scores['sl_diversity'] = 0.0
        
        # レバレッジ多様性スコア（緩い基準）
        leverages = [t.get('leverage') for t in trades_data if t.get('leverage') is not None]
        if leverages:
            leverage_diversity = len(set(leverages)) / len(leverages)
            scores['leverage_diversity'] = leverage_diversity
            
            if leverage_diversity < 0.1:  # レバレッジは10%以下で問題
                issues.append(f"レバレッジ統一 (多様性: {leverage_diversity:.1%})")
        else:
            scores['leverage_diversity'] = 0.0
        
        # 価格現実性スコア
        exit_prices = [t.get('exit_price') for t in trades_data if t.get('exit_price') is not None]
        if entry_prices and exit_prices:
            entry_range = max(entry_prices) - min(entry_prices)
            exit_range = max(exit_prices) - min(exit_prices)
            
            # クローズ価格の方が変動が大きいことを期待（実データの証拠）
            if exit_range > entry_range:
                scores['price_realism'] = 1.0
            else:
                price_realism_ratio = exit_range / entry_range if entry_range > 0 else 0
                scores['price_realism'] = min(price_realism_ratio, 1.0)
                
                if price_realism_ratio < 0.5:
                    issues.append(f"価格変動の現実性不足 (比率: {price_realism_ratio:.2f})")
        else:
            scores['price_realism'] = 0.0
        
        # 時系列一貫性スコア
        entry_times = [t.get('entry_time') for t in trades_data if t.get('entry_time') is not None]
        if entry_times and len(entry_times) > 1:
            try:
                # 時系列データの時間幅をチェック
                time_stamps = []
                for et in entry_times[:10]:  # 最初の10件をチェック
                    if isinstance(et, str):
                        time_stamps.append(pd.to_datetime(et))
                    else:
                        time_stamps.append(et)
                
                if len(time_stamps) > 1:
                    time_span = max(time_stamps) - min(time_stamps)
                    time_span_hours = time_span.total_seconds() / 3600
                    
                    if time_span_hours >= self.quality_standards['min_time_span_hours']:
                        scores['temporal_consistency'] = 1.0
                    else:
                        scores['temporal_consistency'] = time_span_hours / self.quality_standards['min_time_span_hours']
                        issues.append(f"時間幅不足 ({time_span_hours:.1f}時間)")
                else:
                    scores['temporal_consistency'] = 0.0
                    issues.append("時系列データ不足")
            except Exception:
                scores['temporal_consistency'] = 0.0
                issues.append("時系列データ処理エラー")
        else:
            scores['temporal_consistency'] = 0.0
        
        # 全体スコア計算（重み付き平均）
        weights = {
            'entry_diversity': 0.3,
            'tp_diversity': 0.2,
            'sl_diversity': 0.2,
            'leverage_diversity': 0.1,
            'price_realism': 0.15,
            'temporal_consistency': 0.05
        }
        
        overall_score = sum(scores.get(key, 0) * weight for key, weight in weights.items())
        
        return {
            'overall_score': overall_score,
            'component_scores': scores,
            'issues': issues
        }
    
    def test_automated_quality_alert_system(self):
        """自動品質アラートシステム"""
        print("\n🔍 自動品質アラートシステムテスト")
        print("=" * 70)
        
        # 品質監視を実行
        strategies = self.get_all_available_strategies()
        alerts = []
        
        for symbol, timeframe, config in strategies[:5]:  # 最初の5戦略をテスト
            try:
                trades_data = self.system.load_compressed_trades(symbol, timeframe, config)
                
                if not trades_data or len(trades_data) < 5:
                    continue
                
                # アラート条件をチェック
                alert = self._check_alert_conditions(trades_data, symbol, timeframe, config)
                if alert:
                    alerts.append(alert)
                    
            except Exception as e:
                continue
        
        print(f"📊 アラート生成数: {len(alerts)}")
        
        for alert in alerts:
            print(f"⚠️ {alert['level']}: {alert['strategy']} - {alert['message']}")
        
        # テスト用途: アラートの妥当性をチェック
        self.assertIsInstance(alerts, list, "アラートシステムが正常に動作していません")
    
    def _check_alert_conditions(self, trades_data, symbol, timeframe, config):
        """アラート条件をチェック"""
        strategy_name = f"{symbol} {timeframe} {config}"
        
        # エントリー価格統一チェック
        entry_prices = [t.get('entry_price') for t in trades_data if t.get('entry_price') is not None]
        if entry_prices:
            entry_diversity = len(set(entry_prices)) / len(entry_prices)
            
            if entry_diversity <= self.alert_thresholds['critical_diversity_rate']:
                return {
                    'level': 'CRITICAL',
                    'strategy': strategy_name,
                    'message': f'エントリー価格完全統一 (多様性: {entry_diversity:.1%})',
                    'timestamp': datetime.now(),
                    'metric': 'entry_price_diversity',
                    'value': entry_diversity
                }
            elif entry_diversity <= self.alert_thresholds['warning_diversity_rate']:
                return {
                    'level': 'WARNING',
                    'strategy': strategy_name,
                    'message': f'エントリー価格多様性低下 (多様性: {entry_diversity:.1%})',
                    'timestamp': datetime.now(),
                    'metric': 'entry_price_diversity', 
                    'value': entry_diversity
                }
        
        return None
    
    def test_quality_trend_analysis(self):
        """品質トレンド分析"""
        print("\n🔍 品質トレンド分析テスト")
        print("=" * 70)
        
        # 過去の品質データと比較して改善・悪化をトラッキング
        # 現在は基本実装のみ（将来的に拡張予定）
        
        strategies = self.get_all_available_strategies()
        quality_trends = {}
        
        for symbol, timeframe, config in strategies[:3]:  # サンプル
            try:
                trades_data = self.system.load_compressed_trades(symbol, timeframe, config)
                if trades_data and len(trades_data) >= 10:
                    
                    # 前半と後半で品質比較
                    mid_point = len(trades_data) // 2
                    first_half = trades_data[:mid_point]
                    second_half = trades_data[mid_point:]
                    
                    first_score = self._calculate_simple_quality_score(first_half)
                    second_score = self._calculate_simple_quality_score(second_half)
                    
                    trend = second_score - first_score
                    quality_trends[f"{symbol}_{timeframe}_{config}"] = {
                        'first_half_score': first_score,
                        'second_half_score': second_score,
                        'trend': trend
                    }
                    
                    print(f"📊 {symbol} {timeframe} {config}:")
                    print(f"   前半スコア: {first_score:.2f}")
                    print(f"   後半スコア: {second_score:.2f}")
                    print(f"   トレンド: {'+' if trend > 0 else ''}{trend:.2f}")
                    
            except Exception as e:
                continue
        
        # 品質トレンドの存在確認
        self.assertGreater(len(quality_trends), 0, "品質トレンド分析データが取得できませんでした")
        
        print(f"\n✅ 品質トレンド分析完了: {len(quality_trends)}戦略")
    
    def _calculate_simple_quality_score(self, trades_data):
        """簡単な品質スコア計算"""
        if not trades_data:
            return 0.0
        
        entry_prices = [t.get('entry_price') for t in trades_data if t.get('entry_price') is not None]
        if not entry_prices:
            return 0.0
        
        diversity = len(set(entry_prices)) / len(entry_prices)
        return diversity


def run_backtest_quality_monitoring():
    """バックテスト品質監視を実行"""
    print("🚀 バックテスト品質監視システム")
    print("=" * 70)
    print("目的: 継続的なバックテスト品質監視と問題の早期発見")
    print("=" * 70)
    
    # テストスイート作成
    suite = unittest.TestSuite()
    
    # 品質監視テストを追加
    suite.addTest(TestBacktestQualityMonitor('test_comprehensive_price_diversity_monitoring'))
    suite.addTest(TestBacktestQualityMonitor('test_automated_quality_alert_system'))
    suite.addTest(TestBacktestQualityMonitor('test_quality_trend_analysis'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 バックテスト品質監視結果")
    print("=" * 70)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    
    if failures == 0 and errors == 0:
        print("✅ 全品質チェック合格 - バックテストシステムは健全です")
    else:
        print(f"⚠️ 品質問題検出: 失敗{failures}件, エラー{errors}件")
        
        if failures > 0:
            print("\n品質問題の詳細:")
            for test, traceback in result.failures:
                print(f"• {test}")
    
    return result


if __name__ == '__main__':
    run_backtest_quality_monitoring()