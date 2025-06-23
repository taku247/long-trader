#!/usr/bin/env python3
"""
価格データ検証テストスイート
トレードデータの価格整合性をチェックし、ハードコード値やテストデータ使用を検出

機能:
1. 全銘柄のトレードデータ価格検証
2. ハードコード値検出 (100.0, 105.0, 97.62等)
3. 価格変動の異常検出
4. 実際のAPI価格との比較
5. エントリー/TP/SL価格の論理性チェック
"""

import pickle
import gzip
import pandas as pd
import numpy as np
from pathlib import Path
import json
import asyncio
from datetime import datetime, timezone, timedelta
import argparse
from typing import Dict, List, Tuple, Any, Optional

class PriceDataValidator:
    """価格データ検証クラス"""
    
    def __init__(self):
        self.compressed_dir = Path("large_scale_analysis/compressed")
        self.known_hardcoded_values = [100.0, 105.0, 97.62, 100.00, 105.00, 97.620]
        self.tolerance_pct = 0.001  # 0.1% - ハードコード値検出の許容範囲
        self.test_results = []
        
    def load_all_symbol_data(self) -> Dict[str, List[Tuple[str, str, str]]]:
        """全銘柄のトレードデータファイルを検索"""
        symbol_files = {}
        
        if not self.compressed_dir.exists():
            print(f"⚠️  圧縮データディレクトリが見つかりません: {self.compressed_dir}")
            return symbol_files
        
        for file_path in self.compressed_dir.glob("*.pkl.gz"):
            parts = file_path.stem.replace('.pkl', '').split('_')
            if len(parts) >= 3:
                symbol = parts[0]
                timeframe = parts[1]
                config = '_'.join(parts[2:])
                
                if symbol not in symbol_files:
                    symbol_files[symbol] = []
                symbol_files[symbol].append((timeframe, config, str(file_path)))
        
        return symbol_files
    
    def load_trade_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """トレードデータを読み込み"""
        try:
            with gzip.open(file_path, 'rb') as f:
                trades_data = pickle.load(f)
            
            if isinstance(trades_data, list):
                return pd.DataFrame(trades_data)
            elif isinstance(trades_data, dict):
                return pd.DataFrame(trades_data)
            else:
                return trades_data
                
        except Exception as e:
            print(f"❌ データ読み込みエラー {file_path}: {e}")
            return None
    
    def detect_hardcoded_values(self, df: pd.DataFrame, column: str) -> Dict[str, Any]:
        """ハードコード値を検出"""
        if column not in df.columns:
            return {'detected': False, 'reason': f'Column {column} not found'}
        
        values = pd.to_numeric(df[column], errors='coerce').dropna()
        if len(values) == 0:
            return {'detected': False, 'reason': 'No numeric values'}
        
        # 既知のハードコード値をチェック
        hardcoded_detections = []
        for hardcoded_val in self.known_hardcoded_values:
            matching_count = sum(abs(val - hardcoded_val) / hardcoded_val < self.tolerance_pct for val in values)
            if matching_count > 0:
                hardcoded_detections.append({
                    'value': hardcoded_val,
                    'count': matching_count,
                    'percentage': matching_count / len(values) * 100
                })
        
        # 統計的異常検出
        unique_count = len(values.unique())
        std_dev = values.std()
        mean_val = values.mean()
        
        anomalies = []
        
        # 1. 固有値が極端に少ない
        if unique_count <= 3 and len(values) > 10:
            anomalies.append(f"固有値が{unique_count}個のみ ({len(values)}個中)")
        
        # 2. 標準偏差が極端に小さい
        if std_dev < mean_val * 0.001:  # 0.1%未満の変動
            anomalies.append(f"変動が極小 (std={std_dev:.6f}, mean={mean_val:.6f})")
        
        # 3. 同一値が50%以上
        value_counts = values.value_counts()
        most_common_pct = value_counts.iloc[0] / len(values) * 100
        if most_common_pct > 50:
            anomalies.append(f"同一値が{most_common_pct:.1f}%を占める (値: {value_counts.index[0]})")
        
        return {
            'detected': len(hardcoded_detections) > 0 or len(anomalies) > 0,
            'hardcoded_values': hardcoded_detections,
            'statistical_anomalies': anomalies,
            'stats': {
                'count': len(values),
                'unique_count': unique_count,
                'mean': float(mean_val),
                'std': float(std_dev),
                'min': float(values.min()),
                'max': float(values.max()),
                'sample_values': values.head(10).tolist()
            }
        }
    
    def validate_price_logic(self, df: pd.DataFrame) -> List[str]:
        """価格の論理性をチェック"""
        issues = []
        
        # エントリー価格がある場合のチェック
        if 'entry_price' in df.columns and 'take_profit_price' in df.columns and 'stop_loss_price' in df.columns:
            entry_prices = pd.to_numeric(df['entry_price'], errors='coerce').dropna()
            tp_prices = pd.to_numeric(df['take_profit_price'], errors='coerce').dropna()
            sl_prices = pd.to_numeric(df['stop_loss_price'], errors='coerce').dropna()
            
            if len(entry_prices) > 0 and len(tp_prices) > 0 and len(sl_prices) > 0:
                # ロングポジションの論理チェック
                invalid_tp = sum(tp <= entry for tp, entry in zip(tp_prices, entry_prices))
                invalid_sl = sum(sl >= entry for sl, entry in zip(sl_prices, entry_prices))
                
                if invalid_tp > 0:
                    issues.append(f"利確価格がエントリー価格以下: {invalid_tp}件")
                
                if invalid_sl > 0:
                    issues.append(f"損切価格がエントリー価格以上: {invalid_sl}件")
                
                # リスクリワード比の異常
                rr_ratios = [(tp - entry) / (entry - sl) for tp, entry, sl in zip(tp_prices, entry_prices, sl_prices) if entry > sl]
                if rr_ratios:
                    avg_rr = np.mean(rr_ratios)
                    if avg_rr < 0.5:
                        issues.append(f"リスクリワード比が低い (平均: {avg_rr:.2f})")
                    elif avg_rr > 10:
                        issues.append(f"リスクリワード比が異常に高い (平均: {avg_rr:.2f})")
        
        return issues
    
    async def get_current_market_price(self, symbol: str) -> Optional[float]:
        """現在の市場価格を取得"""
        try:
            from hyperliquid_api_client import MultiExchangeAPIClient
            
            client = MultiExchangeAPIClient()
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            data = await client.get_ohlcv_data(symbol, '1h', start_time, end_time)
            if not data.empty:
                return float(data['close'].iloc[-1])
        except Exception as e:
            print(f"市場価格取得エラー ({symbol}): {e}")
        
        return None
    
    def validate_symbol_data(self, symbol: str, file_configs: List[Tuple[str, str, str]]) -> Dict[str, Any]:
        """銘柄のデータを検証"""
        print(f"\n🔍 {symbol} の検証開始...")
        
        symbol_result = {
            'symbol': symbol,
            'total_configs': len(file_configs),
            'config_results': [],
            'overall_issues': [],
            'current_price': None
        }
        
        # 現在価格を取得
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            current_price = loop.run_until_complete(self.get_current_market_price(symbol))
            symbol_result['current_price'] = current_price
            loop.close()
            
            if current_price:
                print(f"  📊 現在価格: {current_price:.6f}")
        except Exception as e:
            print(f"  ⚠️  現在価格取得失敗: {e}")
        
        total_anomalies = 0
        
        for timeframe, config, file_path in file_configs:
            print(f"  📁 {timeframe}_{config} を検証中...")
            
            df = self.load_trade_data(file_path)
            if df is None or df.empty:
                symbol_result['config_results'].append({
                    'timeframe': timeframe,
                    'config': config,
                    'status': 'failed',
                    'error': 'データ読み込み失敗'
                })
                continue
            
            config_result = {
                'timeframe': timeframe,
                'config': config,
                'total_trades': len(df),
                'price_validations': {},
                'logic_issues': [],
                'status': 'checked'
            }
            
            # 価格関連のカラムを検証
            price_columns = [col for col in df.columns 
                           if any(keyword in col.lower() for keyword in 
                                  ['price', 'entry', 'exit', 'profit', 'loss', 'target', 'stop'])]
            
            for col in price_columns:
                validation = self.detect_hardcoded_values(df, col)
                config_result['price_validations'][col] = validation
                
                if validation['detected']:
                    total_anomalies += 1
                    print(f"    ⚠️  {col}: 異常検出")
                    
                    if validation['hardcoded_values']:
                        for hv in validation['hardcoded_values']:
                            print(f"      - ハードコード値 {hv['value']}: {hv['count']}件 ({hv['percentage']:.1f}%)")
                    
                    for anomaly in validation['statistical_anomalies']:
                        print(f"      - {anomaly}")
                
                # 現在価格との比較
                if current_price and validation.get('stats', {}).get('count', 0) > 0:
                    mean_price = validation['stats']['mean']
                    price_diff_pct = abs(mean_price - current_price) / current_price * 100
                    if price_diff_pct > 20:  # 20%以上の差
                        print(f"    📈 {col}: 現在価格との乖離 {price_diff_pct:.1f}% (平均: {mean_price:.6f})")
            
            # 価格論理チェック
            logic_issues = self.validate_price_logic(df)
            config_result['logic_issues'] = logic_issues
            
            for issue in logic_issues:
                print(f"    ❌ 論理エラー: {issue}")
            
            symbol_result['config_results'].append(config_result)
        
        # 全体的な問題をまとめ
        if total_anomalies > 0:
            symbol_result['overall_issues'].append(f"価格異常を{total_anomalies}件検出")
        
        print(f"  ✅ {symbol} 検証完了: {total_anomalies}件の異常")
        return symbol_result
    
    def run_comprehensive_validation(self, target_symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """包括的な価格データ検証を実行"""
        print("🔍 Long Trader 価格データ検証スイート")
        print("=" * 60)
        
        all_symbol_files = self.load_all_symbol_data()
        
        if not all_symbol_files:
            return {'error': '検証対象データが見つかりません'}
        
        # 対象銘柄をフィルタ
        if target_symbols:
            all_symbol_files = {s: f for s, f in all_symbol_files.items() 
                              if s.upper() in [t.upper() for t in target_symbols]}
        
        print(f"📊 検証対象: {len(all_symbol_files)}銘柄")
        for symbol, configs in all_symbol_files.items():
            print(f"  - {symbol}: {len(configs)}設定")
        
        validation_results = {
            'validation_timestamp': datetime.now(timezone.utc).isoformat(),
            'total_symbols': len(all_symbol_files),
            'symbol_results': [],
            'summary': {
                'symbols_with_issues': 0,
                'total_anomalies': 0,
                'critical_issues': []
            }
        }
        
        # 各銘柄を検証
        for symbol, file_configs in all_symbol_files.items():
            symbol_result = self.validate_symbol_data(symbol, file_configs)
            validation_results['symbol_results'].append(symbol_result)
            
            # サマリー更新
            if symbol_result['overall_issues']:
                validation_results['summary']['symbols_with_issues'] += 1
            
            # 各設定の異常をカウント
            for config_result in symbol_result['config_results']:
                for col, validation in config_result.get('price_validations', {}).items():
                    if validation['detected']:
                        validation_results['summary']['total_anomalies'] += 1
                        
                        # 重要な異常を記録
                        if validation['hardcoded_values']:
                            for hv in validation['hardcoded_values']:
                                if hv['percentage'] > 50:  # 50%以上がハードコード値
                                    validation_results['summary']['critical_issues'].append({
                                        'symbol': symbol,
                                        'timeframe': config_result['timeframe'],
                                        'config': config_result['config'],
                                        'column': col,
                                        'issue': f"ハードコード値{hv['value']}が{hv['percentage']:.1f}%"
                                    })
        
        return validation_results
    
    def generate_validation_report(self, results: Dict[str, Any]) -> str:
        """検証レポートを生成"""
        report = []
        report.append("=" * 80)
        report.append("🔍 Long Trader 価格データ検証レポート")
        report.append("=" * 80)
        report.append(f"検証日時: {results['validation_timestamp']}")
        report.append(f"対象銘柄数: {results['total_symbols']}")
        report.append("")
        
        # サマリー
        summary = results['summary']
        report.append("📊 検証サマリー")
        report.append("-" * 40)
        report.append(f"問題のある銘柄: {summary['symbols_with_issues']}/{results['total_symbols']}")
        report.append(f"検出された異常: {summary['total_anomalies']}件")
        report.append(f"重要な問題: {len(summary['critical_issues'])}件")
        report.append("")
        
        # 重要な問題の詳細
        if summary['critical_issues']:
            report.append("🚨 重要な問題")
            report.append("-" * 40)
            for issue in summary['critical_issues']:
                report.append(f"❌ {issue['symbol']} {issue['timeframe']}_{issue['config']}")
                report.append(f"   {issue['column']}: {issue['issue']}")
            report.append("")
        
        # 銘柄別詳細
        report.append("📋 銘柄別詳細")
        report.append("-" * 40)
        
        for symbol_result in results['symbol_results']:
            symbol = symbol_result['symbol']
            issues = len(symbol_result['overall_issues'])
            current_price = symbol_result.get('current_price')
            
            status_icon = "✅" if issues == 0 else "⚠️" 
            report.append(f"{status_icon} {symbol}")
            
            if current_price:
                report.append(f"   現在価格: {current_price:.6f}")
            
            if symbol_result['overall_issues']:
                for issue in symbol_result['overall_issues']:
                    report.append(f"   問題: {issue}")
            
            # 各設定の詳細
            for config_result in symbol_result['config_results']:
                config_name = f"{config_result['timeframe']}_{config_result['config']}"
                total_issues = sum(1 for v in config_result.get('price_validations', {}).values() if v['detected'])
                total_issues += len(config_result.get('logic_issues', []))
                
                if total_issues > 0:
                    report.append(f"   📁 {config_name}: {total_issues}件の問題")
                    
                    # 価格検証結果
                    for col, validation in config_result.get('price_validations', {}).items():
                        if validation['detected']:
                            report.append(f"     - {col}:")
                            for hv in validation.get('hardcoded_values', []):
                                report.append(f"       ハードコード値{hv['value']}: {hv['count']}件")
                            for anomaly in validation.get('statistical_anomalies', []):
                                report.append(f"       {anomaly}")
                    
                    # 論理エラー
                    for logic_issue in config_result.get('logic_issues', []):
                        report.append(f"     - 論理エラー: {logic_issue}")
            
            report.append("")
        
        # 推奨事項
        report.append("💡 推奨事項")
        report.append("-" * 40)
        
        if summary['total_anomalies'] > 0:
            report.append("1. ハードコード値を使用している箇所を特定し、実データに置き換え")
            report.append("2. フォールバック機構を削除し、実データ取得失敗時は例外を発生")
            report.append("3. 価格計算ロジックを見直し、動的な価格生成を確保")
            report.append("4. エントリー/TP/SL価格の計算式を現在価格ベースに修正")
        else:
            report.append("✅ 価格データに問題は検出されませんでした")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='Long Trader 価格データ検証')
    parser.add_argument('--symbols', nargs='*', help='検証対象銘柄 (指定なしで全銘柄)')
    parser.add_argument('--output', help='結果出力ファイル名')
    parser.add_argument('--report-only', action='store_true', help='レポートのみ生成')
    
    args = parser.parse_args()
    
    validator = PriceDataValidator()
    
    # 検証実行
    print("🚀 価格データ検証開始...")
    results = validator.run_comprehensive_validation(args.symbols)
    
    if 'error' in results:
        print(f"❌ 検証エラー: {results['error']}")
        return 1
    
    # レポート生成
    report = validator.generate_validation_report(results)
    print("\n" + report)
    
    # 結果保存
    output_file = args.output or f"price_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    report_file = output_file.replace('.json', '_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 詳細結果: {output_file}")
    print(f"📄 レポート: {report_file}")
    
    # 終了コード
    critical_issues = len(results['summary']['critical_issues'])
    if critical_issues > 0:
        print(f"\n⚠️  {critical_issues}件の重要な問題が検出されました")
        return 1
    else:
        print(f"\n✅ 検証完了")
        return 0

if __name__ == "__main__":
    exit(main())