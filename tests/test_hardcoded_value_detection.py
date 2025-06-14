#!/usr/bin/env python3
"""
ハードコード値検知専用テストスイート

目的:
1. 新しい銘柄追加時のハードコード値の自動検知
2. バックテストエンジンの価格計算ロジックの妥当性検証
3. フォールバック機構の使用検知と警告

使用タイミング:
- 銘柄追加後の自動実行
- CIパイプラインでの継続監視
- 定期的な品質チェック
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np
import pickle
import gzip
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Any, Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class HardcodedValueDetector(unittest.TestCase):
    """ハードコード値検知テスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.compressed_dir = Path("large_scale_analysis/compressed")
        self.known_hardcoded_values = [
            100.0, 105.0, 97.62, 100.00, 105.00, 97.620,
            0.04705, 0.050814, 0.044810,  # GMT検出値
            102.0, 95.0, 98.0, 103.0     # 追加の疑わしい値
        ]
        self.tolerance = 0.0001  # 許容誤差
        
    def test_no_hardcoded_entry_prices(self):
        """エントリー価格にハードコード値が使用されていないことを確認"""
        violations = self._scan_for_hardcoded_values(['entry_price'])
        
        self.assertEqual(len(violations), 0, 
                        f"エントリー価格でハードコード値を検出: {violations}")
    
    def test_no_hardcoded_tp_sl_prices(self):
        """TP/SL価格にハードコード値が使用されていないことを確認"""
        violations = self._scan_for_hardcoded_values(['take_profit_price', 'stop_loss_price'])
        
        self.assertEqual(len(violations), 0, 
                        f"TP/SL価格でハードコード値を検出: {violations}")
    
    def test_price_variation_exists(self):
        """価格に適切な変動があることを確認"""
        low_variation_cases = self._check_price_variation()
        
        self.assertEqual(len(low_variation_cases), 0,
                        f"価格変動が不足している戦略: {low_variation_cases}")
    
    def test_prices_near_current_market(self):
        """価格が現在市場価格に近いことを確認"""
        price_deviation_cases = []
        
        # 各銘柄の現在価格を取得してチェック
        symbols = self._get_available_symbols()
        
        for symbol in symbols:
            current_price = self._get_current_market_price(symbol)
            if current_price:
                deviations = self._check_price_deviation_from_market(symbol, current_price)
                price_deviation_cases.extend(deviations)
        
        self.assertEqual(len(price_deviation_cases), 0,
                        f"市場価格から大きく乖離した価格: {price_deviation_cases}")
    
    def test_no_identical_price_patterns(self):
        """同一価格パターンが存在しないことを確認"""
        identical_patterns = self._detect_identical_patterns()
        
        self.assertEqual(len(identical_patterns), 0,
                        f"同一価格パターンを検出: {identical_patterns}")
    
    def _scan_for_hardcoded_values(self, target_columns: List[str]) -> List[Dict]:
        """ハードコード値をスキャン"""
        violations = []
        
        if not self.compressed_dir.exists():
            return violations
        
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
                
                # 対象カラムをチェック
                for col in target_columns:
                    if col in df.columns:
                        violations.extend(
                            self._check_column_for_hardcoded_values(
                                df, col, symbol, timeframe, strategy
                            )
                        )
            
            except Exception as e:
                print(f"ファイル読み込みエラー {file_path}: {e}")
                continue
        
        return violations
    
    def _check_column_for_hardcoded_values(self, df: pd.DataFrame, column: str, 
                                         symbol: str, timeframe: str, strategy: str) -> List[Dict]:
        """カラム内のハードコード値をチェック"""
        violations = []
        
        values = pd.to_numeric(df[column], errors='coerce').dropna()
        if len(values) == 0:
            return violations
        
        for hardcoded_val in self.known_hardcoded_values:
            matching_count = sum(abs(val - hardcoded_val) < self.tolerance for val in values)
            
            if matching_count > 0:
                violation_percentage = matching_count / len(values) * 100
                
                violations.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'strategy': strategy,
                    'column': column,
                    'hardcoded_value': hardcoded_val,
                    'matching_count': matching_count,
                    'total_count': len(values),
                    'percentage': violation_percentage,
                    'severity': 'HIGH' if violation_percentage > 50 else 'MEDIUM'
                })
        
        return violations
    
    def _check_price_variation(self) -> List[Dict]:
        """価格変動の不足をチェック"""
        low_variation_cases = []
        
        if not self.compressed_dir.exists():
            return low_variation_cases
        
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
                
                # 価格変動をチェック
                price_columns = ['entry_price', 'take_profit_price', 'stop_loss_price']
                
                for col in price_columns:
                    if col in df.columns:
                        values = pd.to_numeric(df[col], errors='coerce').dropna()
                        
                        if len(values) > 1:
                            # 標準偏差チェック
                            std_dev = values.std()
                            mean_val = values.mean()
                            cv = std_dev / mean_val if mean_val > 0 else 0  # 変動係数
                            
                            # 固有値数チェック
                            unique_count = len(values.unique())
                            unique_ratio = unique_count / len(values)
                            
                            # 異常判定
                            if cv < 0.001 or unique_ratio < 0.1:
                                low_variation_cases.append({
                                    'symbol': symbol,
                                    'timeframe': timeframe,
                                    'strategy': strategy,
                                    'column': col,
                                    'coefficient_of_variation': cv,
                                    'unique_ratio': unique_ratio,
                                    'unique_count': unique_count,
                                    'total_count': len(values),
                                    'std_dev': std_dev,
                                    'mean': mean_val
                                })
            
            except Exception as e:
                continue
        
        return low_variation_cases
    
    def _get_current_market_price(self, symbol: str) -> Optional[float]:
        """現在の市場価格を取得"""
        try:
            from hyperliquid_api_client import MultiExchangeAPIClient
            
            async def fetch_price():
                client = MultiExchangeAPIClient()
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(hours=1)
                
                data = await client.get_ohlcv_data(symbol, '1h', start_time, end_time)
                if not data.empty:
                    return float(data['close'].iloc[-1])
                return None
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(fetch_price())
            finally:
                loop.close()
                
        except Exception as e:
            print(f"市場価格取得エラー ({symbol}): {e}")
            return None
    
    def _check_price_deviation_from_market(self, symbol: str, current_price: float) -> List[Dict]:
        """市場価格からの乖離をチェック"""
        deviations = []
        
        if not self.compressed_dir.exists():
            return deviations
        
        for file_path in self.compressed_dir.glob(f"{symbol}_*.pkl.gz"):
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
                
                # エントリー価格の乖離をチェック
                if 'entry_price' in df.columns:
                    entry_prices = pd.to_numeric(df['entry_price'], errors='coerce').dropna()
                    
                    if len(entry_prices) > 0:
                        mean_entry = entry_prices.mean()
                        deviation_pct = abs(mean_entry - current_price) / current_price * 100
                        
                        # 30%以上の乖離は異常
                        if deviation_pct > 30:
                            deviations.append({
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'strategy': strategy,
                                'current_market_price': current_price,
                                'mean_entry_price': mean_entry,
                                'deviation_percentage': deviation_pct,
                                'severity': 'HIGH' if deviation_pct > 50 else 'MEDIUM'
                            })
            
            except Exception as e:
                continue
        
        return deviations
    
    def _detect_identical_patterns(self) -> List[Dict]:
        """同一価格パターンを検出"""
        identical_patterns = []
        
        if not self.compressed_dir.exists():
            return identical_patterns
        
        # 銘柄ごとにパターンを収集
        symbol_patterns = {}
        
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
                
                # 価格パターンを作成
                if all(col in df.columns for col in ['entry_price', 'take_profit_price', 'stop_loss_price']):
                    entry = pd.to_numeric(df['entry_price'], errors='coerce').dropna()
                    tp = pd.to_numeric(df['take_profit_price'], errors='coerce').dropna()
                    sl = pd.to_numeric(df['stop_loss_price'], errors='coerce').dropna()
                    
                    if len(entry) > 0 and len(tp) > 0 and len(sl) > 0:
                        # パターンを作成（平均値の組み合わせ）
                        pattern = (
                            round(entry.mean(), 6),
                            round(tp.mean(), 6),
                            round(sl.mean(), 6)
                        )
                        
                        if symbol not in symbol_patterns:
                            symbol_patterns[symbol] = []
                        
                        symbol_patterns[symbol].append({
                            'pattern': pattern,
                            'timeframe': timeframe,
                            'strategy': strategy,
                            'file_path': str(file_path)
                        })
            
            except Exception as e:
                continue
        
        # 同一パターンを検出
        for symbol, patterns in symbol_patterns.items():
            pattern_groups = {}
            
            for item in patterns:
                pattern = item['pattern']
                if pattern not in pattern_groups:
                    pattern_groups[pattern] = []
                pattern_groups[pattern].append(item)
            
            # 同一パターンが複数戦略で使用されている場合
            for pattern, items in pattern_groups.items():
                if len(items) > 1:
                    identical_patterns.append({
                        'symbol': symbol,
                        'pattern': pattern,
                        'strategies': [f"{item['timeframe']}_{item['strategy']}" for item in items],
                        'count': len(items),
                        'severity': 'HIGH' if len(items) > 3 else 'MEDIUM'
                    })
        
        return identical_patterns
    
    def _get_available_symbols(self) -> List[str]:
        """利用可能な銘柄リストを取得"""
        symbols = set()
        
        if self.compressed_dir.exists():
            for file_path in self.compressed_dir.glob("*.pkl.gz"):
                parts = file_path.stem.replace('.pkl', '').split('_')
                if len(parts) >= 1:
                    symbols.add(parts[0])
        
        return list(symbols)

class ContinuousMonitoringTest(unittest.TestCase):
    """継続監視用テスト"""
    
    def test_latest_symbol_additions(self):
        """最新の銘柄追加でハードコード値が使用されていないことを確認"""
        # 過去24時間以内に作成されたファイルをチェック
        recent_files = self._get_recent_files(hours=24)
        
        if not recent_files:
            self.skipTest("24時間以内に新しいファイルが作成されていません")
        
        detector = HardcodedValueDetector()
        detector.setUp()
        
        violations = []
        for file_path in recent_files:
            # 個別ファイルチェック
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
                
                # 価格カラムをチェック
                price_columns = ['entry_price', 'take_profit_price', 'stop_loss_price']
                for col in price_columns:
                    if col in df.columns:
                        violations.extend(
                            detector._check_column_for_hardcoded_values(
                                df, col, "RECENT", "RECENT", str(file_path.name)
                            )
                        )
            
            except Exception as e:
                continue
        
        self.assertEqual(len(violations), 0,
                        f"最新ファイルでハードコード値を検出: {violations}")
    
    def _get_recent_files(self, hours: int = 24) -> List[Path]:
        """指定時間以内に作成されたファイルを取得"""
        recent_files = []
        compressed_dir = Path("large_scale_analysis/compressed")
        
        if not compressed_dir.exists():
            return recent_files
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for file_path in compressed_dir.glob("*.pkl.gz"):
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime > cutoff_time:
                    recent_files.append(file_path)
            except Exception:
                continue
        
        return recent_files

def create_monitoring_suite():
    """監視用テストスイートを作成"""
    suite = unittest.TestSuite()
    
    # ハードコード値検知テスト
    suite.addTest(unittest.makeSuite(HardcodedValueDetector))
    
    # 継続監視テスト
    suite.addTest(unittest.makeSuite(ContinuousMonitoringTest))
    
    return suite

if __name__ == '__main__':
    print("🔍 ハードコード値検知テストスイート")
    print("=" * 60)
    
    # テストスイート実行
    runner = unittest.TextTestRunner(verbosity=2)
    suite = create_monitoring_suite()
    result = runner.run(suite)
    
    # 結果レポート
    print("\n" + "=" * 60)
    print("📊 ハードコード値検知結果")
    print("=" * 60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 検出された問題:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n💥 テスト実行エラー:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    if not result.failures and not result.errors:
        print("\n✅ ハードコード値は検出されませんでした！")
    
    # 終了コード
    exit_code = 1 if (result.failures or result.errors) else 0
    exit(exit_code)