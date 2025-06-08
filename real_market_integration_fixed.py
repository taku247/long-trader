"""
実市場データ統合システム
既存のOHLCVシステムとMLシステムを統合した実用的な分析エンジン
"""
import pandas as pd
import numpy as np
import os
import json
import sqlite3
from datetime import datetime
import logging
import subprocess
import sys
from pathlib import Path

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealMarketAnalysisSystem:
    def __init__(self, base_dir="real_market_analysis"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # ディレクトリ構造
        self.db_path = self.base_dir / "market_analysis.db"
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # データベース初期化
        self.init_database()
    
    def init_database(self):
        """SQLiteデータベースを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 市場データテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    records_count INTEGER,
                    features_count INTEGER,
                    data_quality_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe)
                )
            ''')
            conn.commit()
    
    def fetch_market_data(self, symbols, timeframes):
        """指定したシンボル・タイムフレームの市場データを取得"""
        results = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                logger.info(f"市場データ確認中: {symbol} {timeframe}")
                
                # まず既存ファイルをチェック
                reduced_features_file = f"{symbol.lower()}_{timeframe}_90days_reduced_features.csv"
                
                if os.path.exists(reduced_features_file):
                    logger.info(f"既存データを使用: {reduced_features_file}")
                    try:
                        # データを読み込んで品質チェック
                        df = pd.read_csv(reduced_features_file)
                        quality_score = 1.0 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
                        
                        # データベースに記録
                        with sqlite3.connect(self.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT OR REPLACE INTO market_data_status 
                                (symbol, timeframe, records_count, features_count, data_quality_score)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (symbol, timeframe, len(df), len(df.columns) - 1, quality_score))
                            conn.commit()
                        
                        results.append({
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'status': 'success',
                            'records': len(df),
                            'features': len(df.columns) - 1,
                            'quality_score': quality_score
                        })
                        
                        logger.info(f"✓ {symbol} {timeframe}: {len(df)}件, {len(df.columns)-1}特徴量")
                        
                    except Exception as e:
                        logger.error(f"既存データ読み込みエラー: {e}")
                        results.append({
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'status': 'failed',
                            'error': f'既存データ読み込みエラー: {e}'
                        })
                else:
                    # データが存在しない場合は新規取得
                    logger.info(f"新規データ取得: {symbol} {timeframe}")
                    try:
                        cmd = [
                            sys.executable,
                            "ohlcv_by_claude.py",
                            "--symbol", symbol,
                            "--timeframe", timeframe
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                        
                        if result.returncode == 0 and os.path.exists(reduced_features_file):
                            # 新しく生成されたファイルを処理
                            df = pd.read_csv(reduced_features_file)
                            quality_score = 1.0 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
                            
                            with sqlite3.connect(self.db_path) as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    INSERT OR REPLACE INTO market_data_status 
                                    (symbol, timeframe, records_count, features_count, data_quality_score)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (symbol, timeframe, len(df), len(df.columns) - 1, quality_score))
                                conn.commit()
                            
                            results.append({
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'status': 'success',
                                'records': len(df),
                                'features': len(df.columns) - 1,
                                'quality_score': quality_score
                            })
                            
                            logger.info(f"✓ {symbol} {timeframe}: {len(df)}件, {len(df.columns)-1}特徴量")
                        else:
                            results.append({
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'status': 'failed',
                                'error': 'データ取得/ファイル生成失敗'
                            })
                    except subprocess.TimeoutExpired:
                        results.append({
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'status': 'failed',
                            'error': 'タイムアウト'
                        })
                    except Exception as e:
                        results.append({
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'status': 'failed',
                            'error': str(e)
                        })
        
        return results
    
    def analyze_support_resistance(self, symbol, timeframe):
        """サポート・レジスタンス分析を実行"""
        logger.info(f"サポレジ分析開始: {symbol} {timeframe}")
        
        try:
            cmd = [
                sys.executable,
                "support_resistance_visualizer.py",
                "--symbol", symbol,
                "--timeframe", timeframe,
                "--min-touches", "2"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                chart_file = f"{symbol.lower()}_{timeframe}_support_resistance_analysis.png"
                if os.path.exists(chart_file):
                    return {'status': 'success', 'chart_path': chart_file}
                    
            return {'status': 'failed', 'error': 'チャート生成失敗'}
            
        except Exception as e:
            return {'status': 'failed', 'error': str(e)}
    
    def train_ml_models(self, symbol, timeframe):
        """機械学習モデルを訓練"""
        logger.info(f"ML訓練開始: {symbol} {timeframe}")
        
        try:
            cmd = [
                sys.executable,
                "support_resistance_ml.py",
                "--symbol", symbol,
                "--timeframe", timeframe,
                "--min-touches", "2"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                model_file = f"{symbol.lower()}_{timeframe}_sr_breakout_model.pkl"
                if os.path.exists(model_file):
                    # 精度を抽出（改良版）
                    accuracy = 0.0
                    if "精度:" in result.stdout:
                        import re
                        # "精度: 0.570" のような形式を探す
                        match = re.search(r'精度:\s*(\d+\.\d+)', result.stdout)
                        if match:
                            accuracy = float(match.group(1))
                    elif "平均精度:" in result.stdout:
                        # "平均精度: 0.5696" のような形式も探す
                        match = re.search(r'平均精度:\s*(\d+\.\d+)', result.stdout)
                        if match:
                            accuracy = float(match.group(1))
                    
                    return {'status': 'success', 'accuracy': accuracy}
                    
            return {'status': 'failed', 'error': 'モデル生成失敗'}
            
        except Exception as e:
            return {'status': 'failed', 'error': str(e)}
    
    def generate_comprehensive_analysis(self, symbols=None, timeframes=None):
        """包括的な分析を実行"""
        if symbols is None:
            symbols = ['HYPE']  # 1銘柄でテスト
        if timeframes is None:
            timeframes = ['1h']
        
        logger.info(f"包括分析開始: {symbols} x {timeframes}")
        
        results = {
            'data_fetch': [],
            'support_resistance': [],
            'ml_training': [],
            'summary': {}
        }
        
        # 1. データ取得
        logger.info("=== ステップ1: 市場データ取得 ===")
        data_results = self.fetch_market_data(symbols, timeframes)
        results['data_fetch'] = data_results
        
        # 成功したデータのみで次のステップを実行
        successful_pairs = [(r['symbol'], r['timeframe']) for r in data_results if r['status'] == 'success']
        
        # 2. サポート・レジスタンス分析
        logger.info("=== ステップ2: サポート・レジスタンス分析 ===")
        for symbol, timeframe in successful_pairs:
            sr_result = self.analyze_support_resistance(symbol, timeframe)
            sr_result.update({'symbol': symbol, 'timeframe': timeframe})
            results['support_resistance'].append(sr_result)
        
        # 3. 機械学習モデル訓練
        logger.info("=== ステップ3: 機械学習モデル訓練 ===")
        for symbol, timeframe in successful_pairs:
            ml_result = self.train_ml_models(symbol, timeframe)
            ml_result.update({'symbol': symbol, 'timeframe': timeframe})
            results['ml_training'].append(ml_result)
        
        # 4. 結果サマリー
        results['summary'] = self.generate_analysis_summary(results)
        
        # 5. 結果をJSONで保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = self.results_dir / f"comprehensive_analysis_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"分析完了: {results_file}")
        return results
    
    def generate_analysis_summary(self, results):
        """分析結果のサマリーを生成"""
        data_success = len([r for r in results['data_fetch'] if r['status'] == 'success'])
        sr_success = len([r for r in results['support_resistance'] if r['status'] == 'success'])
        ml_success = len([r for r in results['ml_training'] if r['status'] == 'success'])
        
        total_features = sum([r.get('features', 0) for r in results['data_fetch'] if r['status'] == 'success'])
        avg_quality = np.mean([r.get('quality_score', 0) for r in results['data_fetch'] if r['status'] == 'success']) if data_success > 0 else 0
        
        ml_accuracies = [r.get('accuracy', 0) for r in results['ml_training'] if r['status'] == 'success' and r.get('accuracy', 0) > 0]
        avg_accuracy = np.mean(ml_accuracies) if ml_accuracies else 0
        
        return {
            'total_pairs_attempted': len(results['data_fetch']),
            'data_fetch_success': data_success,
            'support_resistance_success': sr_success,
            'ml_training_success': ml_success,
            'total_features_generated': total_features,
            'avg_data_quality': avg_quality,
            'avg_ml_accuracy': avg_accuracy,
            'pipeline_success_rate': ml_success / len(results['data_fetch']) if results['data_fetch'] else 0
        }

def main():
    """メイン実行関数"""
    print("=" * 60)
    print("実市場データ統合システム - 複数銘柄分析")
    print("=" * 60)
    
    # システム初期化
    system = RealMarketAnalysisSystem()
    
    # 複数銘柄での堅牢性テスト
    symbols = ['HYPE', 'SOL', 'PEPE', 'WIF', 'BONK']
    print(f"\n複数銘柄分析実行中...")
    print(f"対象: {', '.join(symbols)}, 1時間足")
    print(f"各銘柄のML性能とシステム堅牢性を評価")
    
    results = system.generate_comprehensive_analysis(
        symbols=symbols,
        timeframes=['1h']
    )
    
    # 結果表示
    print("\n=== 分析結果サマリー ===")
    summary = results['summary']
    print(f"対象ペア数: {summary['total_pairs_attempted']}")
    print(f"データ取得成功: {summary['data_fetch_success']}")
    print(f"サポレジ分析成功: {summary['support_resistance_success']}")
    print(f"ML訓練成功: {summary['ml_training_success']}")
    print(f"生成特徴量数: {summary['total_features_generated']}")
    print(f"データ品質平均: {summary['avg_data_quality']:.3f}")
    print(f"ML精度平均: {summary['avg_ml_accuracy']:.3f}")
    print(f"パイプライン成功率: {summary['pipeline_success_rate']:.1%}")
    
    # 銘柄別性能比較
    print("\n=== 銘柄別性能比較 ===")
    symbol_performance = {}
    
    for result in results['data_fetch']:
        symbol = result['symbol']
        if symbol not in symbol_performance:
            symbol_performance[symbol] = {'data': None, 'sr': None, 'ml': None}
        symbol_performance[symbol]['data'] = result
    
    for result in results['support_resistance']:
        symbol = result['symbol']
        if symbol in symbol_performance:
            symbol_performance[symbol]['sr'] = result
    
    for result in results['ml_training']:
        symbol = result['symbol']
        if symbol in symbol_performance:
            symbol_performance[symbol]['ml'] = result
    
    # 各銘柄の詳細表示
    for symbol, perf in symbol_performance.items():
        print(f"\n{symbol}:")
        
        # データ取得
        data_status = "✓" if perf['data'] and perf['data']['status'] == 'success' else "✗"
        print(f"  データ取得: {data_status}")
        if perf['data'] and perf['data']['status'] == 'success':
            print(f"    {perf['data']['records']}件, {perf['data']['features']}特徴量, 品質{perf['data']['quality_score']:.3f}")
        
        # サポレジ分析
        sr_status = "✓" if perf['sr'] and perf['sr']['status'] == 'success' else "✗"
        print(f"  サポレジ分析: {sr_status}")
        
        # ML訓練
        ml_status = "✓" if perf['ml'] and perf['ml']['status'] == 'success' else "✗"
        print(f"  ML訓練: {ml_status}")
        if perf['ml'] and perf['ml']['status'] == 'success' and perf['ml'].get('accuracy', 0) > 0:
            print(f"    精度: {perf['ml']['accuracy']:.3f}")
        
        # 総合評価
        pipeline_success = all([
            perf['data'] and perf['data']['status'] == 'success',
            perf['sr'] and perf['sr']['status'] == 'success',
            perf['ml'] and perf['ml']['status'] == 'success'
        ])
        status_emoji = "🟢" if pipeline_success else "🔴"
        print(f"  総合: {status_emoji} {'完全成功' if pipeline_success else '部分的失敗'}")
    
    # ML精度ランキング
    print("\n=== ML精度ランキング ===")
    ml_accuracies = []
    for symbol, perf in symbol_performance.items():
        if perf['ml'] and perf['ml']['status'] == 'success' and perf['ml'].get('accuracy', 0) > 0:
            ml_accuracies.append((symbol, perf['ml']['accuracy']))
    
    ml_accuracies.sort(key=lambda x: x[1], reverse=True)
    for i, (symbol, accuracy) in enumerate(ml_accuracies, 1):
        print(f"{i}. {symbol}: {accuracy:.3f}")
    
    print("\n✅ 複数銘柄実市場データ統合テスト完了")

if __name__ == "__main__":
    main()