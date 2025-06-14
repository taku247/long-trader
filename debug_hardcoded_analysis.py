#!/usr/bin/env python3
"""
ハードコード値バグの詳細デバッグ・分析スクリプト

作成したテストコードを活用して：
1. ハードコード値の具体的な発生箇所を特定
2. 問題のある戦略・銘柄・時間足の組み合わせを抽出
3. 発生パターンを分析してバグの根本原因を追跡
"""

import sys
import os
import pandas as pd
import numpy as np
import pickle
import gzip
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict, Counter

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class HardcodedValueBugDetector:
    """ハードコード値バグの詳細検知・分析クラス"""
    
    def __init__(self):
        self.compressed_dir = Path("large_scale_analysis/compressed")
        self.known_hardcoded_values = [
            100.0, 105.0, 97.62, 100.00, 105.00, 97.620,
            0.04705, 0.050814, 0.044810,  # GMT検出値
            102.0, 95.0, 98.0, 103.0,     # 追加の疑わしい値
            1000.0, 1000.00,               # 1000系ハードコード値
            840.0, 880.0, 620.0            # 新たに検出された疑わしい値
        ]
        self.tolerance = 0.0001
        
        # 分析結果を保存
        self.analysis_results = {
            'hardcoded_violations': [],
            'static_pricing_strategies': [],
            'price_inconsistencies': [],
            'summary_stats': {}
        }
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """包括的なハードコード値分析を実行"""
        print("🔍 ハードコード値バグの包括的分析開始")
        print("=" * 60)
        
        if not self.compressed_dir.exists():
            print("❌ compressed ディレクトリが存在しません")
            return self.analysis_results
        
        # 1. 全ファイルをスキャンして基本統計を収集
        print("\n📊 ステップ1: 基本統計情報の収集")
        basic_stats = self._collect_basic_statistics()
        self.analysis_results['summary_stats']['basic'] = basic_stats
        
        # 2. ハードコード値の詳細検知
        print("\n🎯 ステップ2: ハードコード値の詳細検知")
        hardcoded_violations = self._detect_hardcoded_values_detailed()
        self.analysis_results['hardcoded_violations'] = hardcoded_violations
        
        # 3. 静的価格設定戦略の分析
        print("\n⚙️ ステップ3: 静的価格設定戦略の分析")
        static_strategies = self._analyze_static_pricing_detailed()
        self.analysis_results['static_pricing_strategies'] = static_strategies
        
        # 4. 価格一貫性の分析
        print("\n🔄 ステップ4: 価格一貫性の分析")
        inconsistencies = self._analyze_price_inconsistencies()
        self.analysis_results['price_inconsistencies'] = inconsistencies
        
        # 5. パターン分析と根本原因の推定
        print("\n🧠 ステップ5: パターン分析と根本原因推定")
        pattern_analysis = self._analyze_patterns_and_root_causes()
        self.analysis_results['pattern_analysis'] = pattern_analysis
        
        # 6. 結果レポート生成
        self._generate_detailed_report()
        
        return self.analysis_results
    
    def _collect_basic_statistics(self) -> Dict[str, Any]:
        """基本統計情報を収集"""
        stats = {
            'total_files': 0,
            'symbols': set(),
            'timeframes': set(),
            'strategies': set(),
            'symbol_timeframe_combinations': set(),
            'total_trades': 0,
            'files_by_symbol': defaultdict(int),
            'files_by_timeframe': defaultdict(int),
            'files_by_strategy': defaultdict(int)
        }
        
        for file_path in self.compressed_dir.glob("*.pkl.gz"):
            stats['total_files'] += 1
            
            # ファイル名から情報を抽出
            parts = file_path.stem.replace('.pkl', '').split('_')
            if len(parts) >= 3:
                symbol = parts[0]
                timeframe = parts[1]
                strategy = '_'.join(parts[2:])
                
                stats['symbols'].add(symbol)
                stats['timeframes'].add(timeframe)
                stats['strategies'].add(strategy)
                stats['symbol_timeframe_combinations'].add(f"{symbol}_{timeframe}")
                
                stats['files_by_symbol'][symbol] += 1
                stats['files_by_timeframe'][timeframe] += 1
                stats['files_by_strategy'][strategy] += 1
                
                # トレード数を集計
                try:
                    with gzip.open(file_path, 'rb') as f:
                        trades_data = pickle.load(f)
                    
                    if isinstance(trades_data, list):
                        df = pd.DataFrame(trades_data)
                    elif isinstance(trades_data, dict):
                        df = pd.DataFrame(trades_data)
                    else:
                        df = trades_data
                    
                    if not df.empty:
                        stats['total_trades'] += len(df)
                
                except Exception as e:
                    print(f"⚠️ ファイル読み込みエラー {file_path.name}: {e}")
        
        # setをリストに変換（JSON対応）
        stats['symbols'] = sorted(list(stats['symbols']))
        stats['timeframes'] = sorted(list(stats['timeframes']))
        stats['strategies'] = sorted(list(stats['strategies']))
        stats['symbol_timeframe_combinations'] = sorted(list(stats['symbol_timeframe_combinations']))
        
        print(f"📁 ファイル数: {stats['total_files']}")
        print(f"🏷️ 銘柄数: {len(stats['symbols'])}")
        print(f"⏰ 時間足: {len(stats['timeframes'])}")
        print(f"📈 戦略数: {len(stats['strategies'])}")
        print(f"💰 総トレード数: {stats['total_trades']}")
        
        return stats
    
    def _detect_hardcoded_values_detailed(self) -> List[Dict]:
        """ハードコード値の詳細検知"""
        violations = []
        
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
                
                # ファイル情報を抽出
                parts = file_path.stem.replace('.pkl', '').split('_')
                if len(parts) >= 3:
                    symbol = parts[0]
                    timeframe = parts[1]
                    strategy = '_'.join(parts[2:])
                else:
                    continue
                
                # 価格カラムをチェック
                price_columns = ['entry_price', 'take_profit_price', 'stop_loss_price']
                for col in price_columns:
                    if col in df.columns:
                        values = pd.to_numeric(df[col], errors='coerce').dropna()
                        
                        if len(values) > 0:
                            # 各ハードコード値をチェック
                            for hardcoded_val in self.known_hardcoded_values:
                                matching_count = sum(abs(val - hardcoded_val) < self.tolerance for val in values)
                                
                                if matching_count > 0:
                                    violation_percentage = matching_count / len(values) * 100
                                    
                                    violation = {
                                        'file_path': str(file_path),
                                        'symbol': symbol,
                                        'timeframe': timeframe,
                                        'strategy': strategy,
                                        'column': col,
                                        'hardcoded_value': hardcoded_val,
                                        'matching_count': matching_count,
                                        'total_count': len(values),
                                        'percentage': violation_percentage,
                                        'severity': 'HIGH' if violation_percentage > 50 else 'MEDIUM',
                                        'sample_values': values.head(10).tolist(),
                                        'unique_values': sorted(values.unique().tolist()),
                                        'mean_value': float(values.mean()),
                                        'std_value': float(values.std()),
                                        'cv': float(values.std() / values.mean()) if values.mean() > 0 else 0.0
                                    }
                                    violations.append(violation)
            
            except Exception as e:
                print(f"⚠️ ファイル分析エラー {file_path.name}: {e}")
        
        # 重要度でソート
        violations.sort(key=lambda x: (x['severity'], -x['percentage']))
        
        print(f"🚨 ハードコード値違反: {len(violations)}件")
        
        # 上位10件を表示
        for i, violation in enumerate(violations[:10]):
            print(f"  {i+1}. {violation['symbol']}_{violation['timeframe']}_{violation['strategy']}")
            print(f"     {violation['column']}: {violation['hardcoded_value']} ({violation['percentage']:.1f}%)")
        
        return violations
    
    def _analyze_static_pricing_detailed(self) -> List[Dict]:
        """静的価格設定の詳細分析"""
        static_strategies = []
        
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
                
                # ファイル情報を抽出
                parts = file_path.stem.replace('.pkl', '').split('_')
                if len(parts) >= 3:
                    symbol = parts[0]
                    timeframe = parts[1]
                    strategy = '_'.join(parts[2:])
                else:
                    continue
                
                # エントリー価格の変動を分析
                if 'entry_price' in df.columns:
                    entry_prices = pd.to_numeric(df['entry_price'], errors='coerce').dropna()
                    
                    if len(entry_prices) > 5:  # 十分なサンプル
                        unique_count = len(entry_prices.unique())
                        cv = entry_prices.std() / entry_prices.mean() if entry_prices.mean() > 0 else 0
                        
                        # 静的価格設定の判定
                        is_static = (unique_count <= 3 or cv < 0.001)
                        
                        analysis = {
                            'file_path': str(file_path),
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'strategy': strategy,
                            'unique_prices': unique_count,
                            'coefficient_of_variation': float(cv),
                            'total_trades': len(entry_prices),
                            'mean_price': float(entry_prices.mean()),
                            'std_price': float(entry_prices.std()),
                            'price_range': float(entry_prices.max() - entry_prices.min()),
                            'is_static': is_static,
                            'unique_values': sorted(entry_prices.unique().tolist())[:20],  # 最大20件
                            'severity': 'HIGH' if unique_count == 1 else 'MEDIUM' if unique_count <= 3 else 'LOW'
                        }
                        
                        if is_static:
                            static_strategies.append(analysis)
            
            except Exception as e:
                continue
        
        # 深刻度でソート
        static_strategies.sort(key=lambda x: (x['severity'], x['unique_prices']))
        
        print(f"⚙️ 静的価格設定戦略: {len(static_strategies)}件")
        
        # 統計表示
        severity_counts = Counter(s['severity'] for s in static_strategies)
        print(f"   HIGH: {severity_counts['HIGH']}件")
        print(f"   MEDIUM: {severity_counts['MEDIUM']}件")
        print(f"   LOW: {severity_counts['LOW']}件")
        
        return static_strategies
    
    def _analyze_price_inconsistencies(self) -> List[Dict]:
        """価格一貫性の分析"""
        inconsistencies = []
        
        # 銘柄・時間足ごとにグループ化
        symbol_timeframe_groups = defaultdict(list)
        
        for file_path in self.compressed_dir.glob("*.pkl.gz"):
            parts = file_path.stem.replace('.pkl', '').split('_')
            if len(parts) >= 3:
                symbol = parts[0]
                timeframe = parts[1]
                strategy = '_'.join(parts[2:])
                
                key = f"{symbol}_{timeframe}"
                symbol_timeframe_groups[key].append({
                    'strategy': strategy,
                    'file_path': file_path
                })
        
        # 各グループで一貫性をチェック
        for key, strategies in symbol_timeframe_groups.items():
            if len(strategies) > 1:
                symbol, timeframe = key.split('_', 1)
                
                strategy_prices = {}
                strategy_details = {}
                
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
                            mean_price = entry_prices.mean()
                            strategy_prices[strategy_info['strategy']] = mean_price
                            strategy_details[strategy_info['strategy']] = {
                                'mean': float(mean_price),
                                'std': float(entry_prices.std()),
                                'count': len(entry_prices),
                                'unique_count': len(entry_prices.unique()),
                                'sample_values': entry_prices.head(5).tolist()
                            }
                    
                    except Exception:
                        continue
                
                # 戦略間の価格差をチェック
                if len(strategy_prices) > 1:
                    prices = list(strategy_prices.values())
                    price_range = max(prices) - min(prices)
                    avg_price = np.mean(prices)
                    
                    # 平均価格の10%以上の差は一貫性の問題
                    if price_range > avg_price * 0.1:
                        inconsistency = {
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'strategy_count': len(strategy_prices),
                            'price_range': float(price_range),
                            'avg_price': float(avg_price),
                            'deviation_percentage': float(price_range / avg_price * 100),
                            'strategy_prices': {k: float(v) for k, v in strategy_prices.items()},
                            'strategy_details': strategy_details,
                            'severity': 'HIGH' if price_range > avg_price * 0.5 else 'MEDIUM'
                        }
                        inconsistencies.append(inconsistency)
        
        inconsistencies.sort(key=lambda x: -x['deviation_percentage'])
        
        print(f"🔄 価格一貫性の問題: {len(inconsistencies)}件")
        
        return inconsistencies
    
    def _analyze_patterns_and_root_causes(self) -> Dict[str, Any]:
        """パターン分析と根本原因の推定"""
        patterns = {
            'most_affected_symbols': {},
            'most_affected_timeframes': {},
            'most_affected_strategies': {},
            'hardcoded_value_frequency': {},
            'probable_root_causes': []
        }
        
        # ハードコード値違反の分析
        symbol_counts = Counter()
        timeframe_counts = Counter()
        strategy_counts = Counter()
        value_counts = Counter()
        
        for violation in self.analysis_results['hardcoded_violations']:
            symbol_counts[violation['symbol']] += 1
            timeframe_counts[violation['timeframe']] += 1
            strategy_counts[violation['strategy']] += 1
            value_counts[violation['hardcoded_value']] += 1
        
        patterns['most_affected_symbols'] = dict(symbol_counts.most_common(10))
        patterns['most_affected_timeframes'] = dict(timeframe_counts.most_common())
        patterns['most_affected_strategies'] = dict(strategy_counts.most_common(10))
        patterns['hardcoded_value_frequency'] = dict(value_counts.most_common())
        
        # 根本原因の推定
        root_causes = []
        
        # 1. 100.0系ハードコード値の分析
        if 100.0 in value_counts and value_counts[100.0] > 50:
            root_causes.append({
                'type': 'DEFAULT_PLACEHOLDER_VALUES',
                'description': '100.0がデフォルト値として大量使用されている',
                'affected_count': value_counts[100.0],
                'likely_source': 'scalable_analysis_system.py, high_leverage_bot_orchestrator.py'
            })
        
        # 2. 1000.0系ハードコード値の分析
        if 1000.0 in value_counts and value_counts[1000.0] > 50:
            root_causes.append({
                'type': 'FALLBACK_MECHANISM_VALUES',
                'description': '1000.0がフォールバック値として使用されている',
                'affected_count': value_counts[1000.0],
                'likely_source': 'TestHighLeverageBotOrchestrator, fallback mechanisms'
            })
        
        # 3. 静的価格設定の分析
        static_high_severity = sum(1 for s in self.analysis_results['static_pricing_strategies'] if s['severity'] == 'HIGH')
        if static_high_severity > 100:
            root_causes.append({
                'type': 'STATIC_PRICING_GENERATION',
                'description': '価格生成ロジックが静的値を出力している',
                'affected_count': static_high_severity,
                'likely_source': 'ML prediction models, price calculation logic'
            })
        
        patterns['probable_root_causes'] = root_causes
        
        print(f"🧠 根本原因候補: {len(root_causes)}件")
        for cause in root_causes:
            print(f"   {cause['type']}: {cause['description']}")
        
        return patterns
    
    def _generate_detailed_report(self):
        """詳細レポートを生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"hardcoded_bug_analysis_{timestamp}.json"
        
        # JSON対応のためにnumpy型と他の型を変換
        def convert_numpy_types(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, bool):
                return obj
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(v) for v in obj]
            elif hasattr(obj, '__dict__'):
                return str(obj)
            return obj
        
        converted_results = convert_numpy_types(self.analysis_results)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(converted_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 詳細レポート保存: {report_file}")
        
        # サマリーレポート表示
        print("\n" + "=" * 60)
        print("📊 分析結果サマリー")
        print("=" * 60)
        
        print(f"🚨 ハードコード値違反: {len(self.analysis_results['hardcoded_violations'])}件")
        print(f"⚙️ 静的価格設定: {len(self.analysis_results['static_pricing_strategies'])}件")
        print(f"🔄 価格一貫性問題: {len(self.analysis_results['price_inconsistencies'])}件")
        
        if 'pattern_analysis' in self.analysis_results:
            patterns = self.analysis_results['pattern_analysis']
            print(f"\n🎯 最も影響を受けた銘柄:")
            for symbol, count in list(patterns['most_affected_symbols'].items())[:5]:
                print(f"   {symbol}: {count}件")
            
            print(f"\n⏰ 最も影響を受けた時間足:")
            for timeframe, count in list(patterns['most_affected_timeframes'].items())[:5]:
                print(f"   {timeframe}: {count}件")

def main():
    """メイン実行関数"""
    print("🔍 ハードコード値バグ詳細デバッグ・分析")
    print("=" * 60)
    
    detector = HardcodedValueBugDetector()
    results = detector.run_comprehensive_analysis()
    
    print("\n✅ 分析完了！詳細レポートをご確認ください。")
    
    return results

if __name__ == '__main__':
    main()