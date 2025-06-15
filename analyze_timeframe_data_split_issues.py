#!/usr/bin/env python3
"""
時間足別のデータ分割・学習・バックテスト問題の詳細調査スクリプト

各時間足（1m, 3m, 5m, 15m, 30m, 1h）でのデータ処理状況を分析：
1. 90日間データでの実際のデータポイント数
2. 学習・バックテスト分割の実装状況
3. 1.8日間隔問題の発生状況
4. 時間足に応じた適切なデータ分割設計
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import asyncio
from collections import defaultdict

# システムモジュールのインポート
from hyperliquid_api_client import MultiExchangeAPIClient
from extended_data_fetcher import ExtendedDataFetcher
from scalable_analysis_system import ScalableAnalysisSystem


class TimeframeDataSplitAnalyzer:
    """時間足別データ分割問題の分析器"""
    
    def __init__(self):
        self.api_client = MultiExchangeAPIClient()
        self.data_fetcher = ExtendedDataFetcher()
        self.analysis_system = ScalableAnalysisSystem()
        
        # 時間足設定
        self.timeframes = ['1m', '3m', '5m', '15m', '30m', '1h']
        self.test_symbol = 'HYPE'  # テスト用シンボル
        
        # 分析結果格納
        self.results = defaultdict(dict)
        
    async def analyze_all_timeframes(self):
        """全時間足の分析を実行"""
        print("=" * 80)
        print("時間足別データ分割・学習・バックテスト問題の詳細調査")
        print("=" * 80)
        
        for timeframe in self.timeframes:
            print(f"\n{'='*60}")
            print(f"時間足: {timeframe}")
            print(f"{'='*60}")
            
            await self.analyze_timeframe(timeframe)
            
        # 総合分析
        self.generate_comprehensive_report()
        
    async def analyze_timeframe(self, timeframe: str):
        """特定時間足の詳細分析"""
        
        # 1. データ取得状況の分析
        data_stats = await self.analyze_data_acquisition(timeframe)
        self.results[timeframe]['data_stats'] = data_stats
        
        # 2. トレード生成パターンの分析
        trade_pattern = self.analyze_trade_generation_pattern(timeframe)
        self.results[timeframe]['trade_pattern'] = trade_pattern
        
        # 3. 学習・バックテスト分割の分析
        split_analysis = self.analyze_train_test_split(timeframe, data_stats)
        self.results[timeframe]['split_analysis'] = split_analysis
        
        # 4. 1.8日間隔問題の検証
        interval_issue = self.check_interval_issue(timeframe, data_stats)
        self.results[timeframe]['interval_issue'] = interval_issue
        
        # 5. 推奨設定の計算
        recommendations = self.calculate_recommendations(timeframe, data_stats)
        self.results[timeframe]['recommendations'] = recommendations
        
    async def analyze_data_acquisition(self, timeframe: str) -> Dict:
        """データ取得状況の分析"""
        print(f"\n1. データ取得分析 ({timeframe})")
        print("-" * 40)
        
        # 90日間のデータを取得
        end_time = datetime.now()
        start_time = end_time - timedelta(days=90)
        
        try:
            # 実際のデータ取得
            df = await self.api_client.get_ohlcv_data(
                self.test_symbol, timeframe, start_time, end_time
            )
            
            # 統計情報の計算
            actual_days = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / (24 * 3600)
            
            # 理論値の計算
            intervals_per_minute = {
                '1m': 1, '3m': 1/3, '5m': 1/5, 
                '15m': 1/15, '30m': 1/30, '1h': 1/60
            }
            expected_points = 90 * 24 * 60 * intervals_per_minute[timeframe]
            
            stats = {
                'timeframe': timeframe,
                'requested_days': 90,
                'actual_days': actual_days,
                'data_points': len(df),
                'expected_points': int(expected_points),
                'coverage_rate': len(df) / expected_points * 100,
                'start_date': df['timestamp'].min(),
                'end_date': df['timestamp'].max(),
                'missing_ratio': 1 - (len(df) / expected_points),
                'data_density': len(df) / actual_days  # データポイント/日
            }
            
            # 結果表示
            print(f"  要求日数: 90日")
            print(f"  実際の日数: {actual_days:.1f}日")
            print(f"  データポイント数: {stats['data_points']:,}")
            print(f"  理論上の期待値: {stats['expected_points']:,}")
            print(f"  カバー率: {stats['coverage_rate']:.1f}%")
            print(f"  データ密度: {stats['data_density']:.1f} points/day")
            
            return stats
            
        except Exception as e:
            print(f"  エラー: {e}")
            return {
                'timeframe': timeframe,
                'error': str(e),
                'data_points': 0
            }
    
    def analyze_trade_generation_pattern(self, timeframe: str) -> Dict:
        """トレード生成パターンの分析"""
        print(f"\n2. トレード生成パターン分析 ({timeframe})")
        print("-" * 40)
        
        # scalable_analysis_systemの設定を確認
        num_trades = 50  # デフォルトのトレード数
        period_days = 90  # 90日間
        
        # トレード間隔の計算
        total_seconds = period_days * 24 * 3600
        interval_seconds = total_seconds / num_trades
        interval_days = interval_seconds / (24 * 3600)
        
        analysis = {
            'num_trades': num_trades,
            'period_days': period_days,
            'interval_seconds': interval_seconds,
            'interval_days': interval_days,
            'interval_hours': interval_seconds / 3600,
            'trades_per_day': num_trades / period_days,
            'is_uniform_distribution': True,  # 現在の実装は均等分散
            'issue': interval_days > 1.5  # 1.5日以上の間隔は問題
        }
        
        print(f"  トレード数: {num_trades}")
        print(f"  期間: {period_days}日")
        print(f"  トレード間隔: {interval_days:.2f}日 ({interval_seconds/3600:.1f}時間)")
        print(f"  1日あたりトレード数: {analysis['trades_per_day']:.2f}")
        print(f"  問題あり: {'はい' if analysis['issue'] else 'いいえ'}")
        
        return analysis
    
    def analyze_train_test_split(self, timeframe: str, data_stats: Dict) -> Dict:
        """学習・バックテスト分割の分析"""
        print(f"\n3. 学習・バックテスト分割分析 ({timeframe})")
        print("-" * 40)
        
        if 'data_points' not in data_stats or data_stats['data_points'] == 0:
            print("  データなし")
            return {'error': 'No data available'}
        
        # 現在の実装の分割比率
        train_ratio = 0.6
        val_ratio = 0.2
        test_ratio = 0.2
        
        total_points = data_stats['data_points']
        
        # 分割後のサンプル数
        train_samples = int(total_points * train_ratio)
        val_samples = int(total_points * val_ratio)
        test_samples = int(total_points * test_ratio)
        
        # 時間軸での期間計算
        if 'actual_days' in data_stats:
            train_days = data_stats['actual_days'] * train_ratio
            val_days = data_stats['actual_days'] * val_ratio
            test_days = data_stats['actual_days'] * test_ratio
        else:
            train_days = val_days = test_days = 0
        
        analysis = {
            'train_ratio': train_ratio,
            'val_ratio': val_ratio,
            'test_ratio': test_ratio,
            'train_samples': train_samples,
            'val_samples': val_samples,
            'test_samples': test_samples,
            'train_days': train_days,
            'val_days': val_days,
            'test_days': test_days,
            'min_recommended_train': 1000,  # 推奨最小学習サンプル数
            'is_sufficient': train_samples >= 1000
        }
        
        print(f"  分割比率: Train={train_ratio:.0%}, Val={val_ratio:.0%}, Test={test_ratio:.0%}")
        print(f"  学習サンプル数: {train_samples:,} ({train_days:.1f}日分)")
        print(f"  検証サンプル数: {val_samples:,} ({val_days:.1f}日分)")
        print(f"  テストサンプル数: {test_samples:,} ({test_days:.1f}日分)")
        print(f"  学習データ十分: {'はい' if analysis['is_sufficient'] else 'いいえ'}")
        
        return analysis
    
    def check_interval_issue(self, timeframe: str, data_stats: Dict) -> Dict:
        """1.8日間隔問題の検証"""
        print(f"\n4. 1.8日間隔問題の検証 ({timeframe})")
        print("-" * 40)
        
        # 現在の実装での問題
        num_trades = 50
        period_days = 90
        interval_days = period_days / num_trades
        
        # 時間足ごとの適切なトレード頻度
        recommended_trades_per_day = {
            '1m': 20,    # 1分足: 1日20回程度
            '3m': 10,    # 3分足: 1日10回程度
            '5m': 8,     # 5分足: 1日8回程度
            '15m': 4,    # 15分足: 1日4回程度
            '30m': 2,    # 30分足: 1日2回程度
            '1h': 1      # 1時間足: 1日1回程度
        }
        
        recommended_freq = recommended_trades_per_day.get(timeframe, 1)
        recommended_total = recommended_freq * period_days
        
        issue_analysis = {
            'current_interval_days': interval_days,
            'current_trades_per_day': num_trades / period_days,
            'recommended_trades_per_day': recommended_freq,
            'recommended_total_trades': recommended_total,
            'gap_ratio': (recommended_freq - (num_trades / period_days)) / recommended_freq,
            'severity': 'high' if interval_days > 1 else 'medium' if interval_days > 0.5 else 'low'
        }
        
        print(f"  現在のトレード間隔: {interval_days:.2f}日")
        print(f"  現在の1日あたりトレード数: {issue_analysis['current_trades_per_day']:.2f}")
        print(f"  推奨1日あたりトレード数: {recommended_freq}")
        print(f"  推奨総トレード数: {recommended_total}")
        print(f"  乖離率: {issue_analysis['gap_ratio']*100:.1f}%")
        print(f"  問題の深刻度: {issue_analysis['severity']}")
        
        return issue_analysis
    
    def calculate_recommendations(self, timeframe: str, data_stats: Dict) -> Dict:
        """時間足に応じた推奨設定の計算"""
        print(f"\n5. 推奨設定 ({timeframe})")
        print("-" * 40)
        
        # 時間足別の推奨設定
        timeframe_configs = {
            '1m': {
                'min_days': 7,
                'recommended_days': 14,
                'trades_per_day': 20,
                'min_train_samples': 2000,
                'train_ratio': 0.7,
                'val_ratio': 0.15,
                'test_ratio': 0.15
            },
            '3m': {
                'min_days': 14,
                'recommended_days': 30,
                'trades_per_day': 10,
                'min_train_samples': 1500,
                'train_ratio': 0.7,
                'val_ratio': 0.15,
                'test_ratio': 0.15
            },
            '5m': {
                'min_days': 30,
                'recommended_days': 60,
                'trades_per_day': 8,
                'min_train_samples': 1000,
                'train_ratio': 0.6,
                'val_ratio': 0.2,
                'test_ratio': 0.2
            },
            '15m': {
                'min_days': 60,
                'recommended_days': 90,
                'trades_per_day': 4,
                'min_train_samples': 800,
                'train_ratio': 0.6,
                'val_ratio': 0.2,
                'test_ratio': 0.2
            },
            '30m': {
                'min_days': 90,
                'recommended_days': 120,
                'trades_per_day': 2,
                'min_train_samples': 600,
                'train_ratio': 0.6,
                'val_ratio': 0.2,
                'test_ratio': 0.2
            },
            '1h': {
                'min_days': 120,
                'recommended_days': 180,
                'trades_per_day': 1,
                'min_train_samples': 500,
                'train_ratio': 0.6,
                'val_ratio': 0.2,
                'test_ratio': 0.2
            }
        }
        
        config = timeframe_configs.get(timeframe, timeframe_configs['1h'])
        
        # 実データに基づく調整
        if 'data_density' in data_stats:
            # データ密度に基づいてトレード頻度を調整
            actual_density = data_stats['data_density']
            expected_density = {
                '1m': 1440, '3m': 480, '5m': 288,
                '15m': 96, '30m': 48, '1h': 24
            }.get(timeframe, 24)
            
            density_ratio = actual_density / expected_density
            adjusted_trades_per_day = config['trades_per_day'] * min(density_ratio, 1.0)
        else:
            adjusted_trades_per_day = config['trades_per_day']
        
        recommendations = {
            'timeframe': timeframe,
            'min_days': config['min_days'],
            'recommended_days': config['recommended_days'],
            'trades_per_day': adjusted_trades_per_day,
            'total_trades': int(adjusted_trades_per_day * config['recommended_days']),
            'min_train_samples': config['min_train_samples'],
            'train_ratio': config['train_ratio'],
            'val_ratio': config['val_ratio'],
            'test_ratio': config['test_ratio'],
            'data_collection_strategy': self.get_data_collection_strategy(timeframe)
        }
        
        print(f"  推奨データ期間: {config['recommended_days']}日 (最小: {config['min_days']}日)")
        print(f"  推奨トレード頻度: {adjusted_trades_per_day:.1f}回/日")
        print(f"  推奨総トレード数: {recommendations['total_trades']}")
        print(f"  推奨分割比: Train={config['train_ratio']:.0%}, Val={config['val_ratio']:.0%}, Test={config['test_ratio']:.0%}")
        print(f"  最小学習サンプル数: {config['min_train_samples']}")
        
        return recommendations
    
    def get_data_collection_strategy(self, timeframe: str) -> str:
        """時間足に応じたデータ収集戦略"""
        strategies = {
            '1m': "高頻度取引向け: 直近2週間のデータで短期パターンを学習",
            '3m': "デイトレード向け: 1ヶ月のデータで日中の値動きパターンを学習",
            '5m': "スイング向け: 2ヶ月のデータで短期トレンドを学習",
            '15m': "ポジション向け: 3ヶ月のデータで中期パターンを学習",
            '30m': "中期投資向け: 4ヶ月のデータでトレンド転換を学習",
            '1h': "長期投資向け: 6ヶ月のデータで大局的な動きを学習"
        }
        return strategies.get(timeframe, "標準的なデータ収集")
    
    def generate_comprehensive_report(self):
        """総合レポートの生成"""
        print("\n" + "=" * 80)
        print("総合分析レポート")
        print("=" * 80)
        
        # 問題サマリー
        print("\n【発見された問題】")
        problems = []
        
        for timeframe, result in self.results.items():
            if 'interval_issue' in result and result['interval_issue'].get('severity') in ['high', 'medium']:
                problems.append(f"- {timeframe}: トレード間隔が{result['interval_issue']['current_interval_days']:.1f}日と過大")
            
            if 'split_analysis' in result and not result['split_analysis'].get('is_sufficient', True):
                problems.append(f"- {timeframe}: 学習データ不足 ({result['split_analysis'].get('train_samples', 0)}サンプル)")
        
        if problems:
            for problem in problems:
                print(problem)
        else:
            print("- 重大な問題は検出されませんでした")
        
        # 改善提案
        print("\n【改善提案】")
        print("1. 時間足別のトレード生成ロジックの実装")
        print("   - 短期時間足（1m-5m）: 高頻度トレード生成")
        print("   - 中期時間足（15m-30m）: 中頻度トレード生成")
        print("   - 長期時間足（1h）: 低頻度トレード生成")
        
        print("\n2. データ期間の動的調整")
        print("   - 時間足に応じて適切なデータ取得期間を設定")
        print("   - データ密度を考慮したサンプル数の確保")
        
        print("\n3. 学習・検証・テスト分割の最適化")
        print("   - 時間足別の最適な分割比率の適用")
        print("   - 最小サンプル数の保証")
        
        # 実装コード例
        print("\n【実装例】")
        print("```python")
        print("# scalable_analysis_system.pyの改善案")
        print("def _generate_real_analysis(self, symbol, timeframe, config, num_trades=None):")
        print("    # 時間足に応じたトレード数の動的設定")
        print("    if num_trades is None:")
        print("        trades_per_day = {")
        print("            '1m': 20, '3m': 10, '5m': 8,")
        print("            '15m': 4, '30m': 2, '1h': 1")
        print("        }.get(timeframe, 1)")
        print("        num_trades = int(trades_per_day * 90)  # 90日分")
        print("    ...")
        print("```")
        
        # 結果をファイルに保存
        self.save_results()
    
    def save_results(self):
        """分析結果をファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"timeframe_data_split_analysis_{timestamp}.json"
        
        # 結果を整形
        output_data = {
            'analysis_time': datetime.now().isoformat(),
            'timeframe_results': dict(self.results),
            'summary': {
                'total_timeframes_analyzed': len(self.results),
                'issues_found': sum(1 for r in self.results.values() 
                                  if r.get('interval_issue', {}).get('severity') in ['high', 'medium']),
                'recommendations_generated': len(self.results)
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n分析結果を保存: {filename}")


async def main():
    """メイン実行関数"""
    analyzer = TimeframeDataSplitAnalyzer()
    await analyzer.analyze_all_timeframes()


if __name__ == "__main__":
    asyncio.run(main())