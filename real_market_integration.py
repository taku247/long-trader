"""
実市場データ統合システム
既存のOHLCVシステムとMLシステムを統合した実用的な分析エンジン
"""
import pandas as pd
import numpy as np
import os
import json
import sqlite3
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import cpu_count
import shutil
import gzip
import pickle
from datetime import datetime, timedelta
import logging
from pathlib import Path
import subprocess
import sys

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealMarketAnalysisSystem:
    def __init__(self, base_dir="real_market_analysis"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # ディレクトリ構造
        self.db_path = self.base_dir / "market_analysis.db"
        self.charts_dir = self.base_dir / "charts"
        self.data_dir = self.base_dir / "market_data"
        self.models_dir = self.base_dir / "models"
        self.results_dir = self.base_dir / "results"
        
        for dir_path in [self.charts_dir, self.data_dir, self.models_dir, self.results_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # データベース初期化
        self.init_database()
        
        # 利用可能なシンボルとタイムフレーム
        self.available_symbols = ['HYPE', 'BTC', 'ETH', 'SOL', 'ARB', 'OP', 'AVAX', 'MATIC', 'DOT', 'ADA']
        self.available_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h']
    
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
                    data_path TEXT,
                    features_path TEXT,
                    indicators_count INTEGER,
                    final_features_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_quality_score REAL,
                    UNIQUE(symbol, timeframe)
                )
            ''')
            
            # 分析結果テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_config TEXT NOT NULL,
                    support_resistance_count INTEGER,
                    ml_model_accuracy REAL,
                    backtest_total_return REAL,
                    backtest_sharpe_ratio REAL,
                    backtest_max_drawdown REAL,
                    avg_leverage_used REAL,
                    risk_reward_ratio REAL,
                    total_trades INTEGER,
                    win_rate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model_path TEXT,
                    chart_path TEXT
                )
            ''')
            
            # レバレッジ推奨結果テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leverage_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    current_price REAL,
                    nearest_support REAL,
                    nearest_resistance REAL,
                    support_strength REAL,
                    resistance_strength REAL,
                    ml_breakout_probability REAL,
                    recommended_leverage REAL,
                    max_safe_leverage REAL,
                    risk_score REAL,
                    confidence_score REAL,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def fetch_market_data(self, symbols, timeframes, days=30):
        """
        指定したシンボル・タイムフレームの市場データを取得
        
        Args:
            symbols: ['HYPE', 'BTC', 'ETH'] など
            timeframes: ['15m', '1h', '4h'] など  
            days: 取得日数 (デフォルト30日)
        """
        results = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                logger.info(f"市場データ取得開始: {symbol} {timeframe}")
                
                try:
                    # ohlcv_by_claude.py を呼び出してデータ取得
                    cmd = [
                        sys.executable,
                        "ohlcv_by_claude.py",
                        "--symbol", symbol,
                        "--timeframe", timeframe
                    ]
                    
                    # 短期間の場合は日数を調整
                    if days < 90:
                        # 時間足に応じた適切な期間を設定
                        if timeframe == '15m':
                            adjusted_days = min(days, 30)
                        elif timeframe == '1h':
                            adjusted_days = min(days, 60)
                        else:
                            adjusted_days = days
                    else:
                        adjusted_days = days
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                    
                    if result.returncode == 0:
                        # 生成されたファイルパスを確認\n                        base_filename = f\"{symbol.lower()}_{timeframe}_{adjusted_days if days < 90 else 90}days\"\n                        \n                        data_files = {\n                            'raw': f\"{base_filename}.csv\",\n                            'with_indicators': f\"{base_filename}_with_indicators.csv\",\n                            'reduced_features': f\"{base_filename}_reduced_features.csv\",\n                            'removed_features': f\"{symbol.lower()}_{timeframe}_removed_features.json\"\n                        }\n                        \n                        # ファイル存在確認\n                        if os.path.exists(data_files['reduced_features']):\n                            # データベースに記録\n                            df = pd.read_csv(data_files['reduced_features'])\n                            \n                            # データ品質スコア計算 (欠損値の少なさ)\n                            quality_score = 1.0 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))\n                            \n                            with sqlite3.connect(self.db_path) as conn:\n                                cursor = conn.cursor()\n                                cursor.execute('''\n                                    INSERT OR REPLACE INTO market_data_status \n                                    (symbol, timeframe, data_path, features_path, \n                                     indicators_count, final_features_count, data_quality_score)\n                                    VALUES (?, ?, ?, ?, ?, ?, ?)\n                                ''', (\n                                    symbol, timeframe, \n                                    data_files['with_indicators'],\n                                    data_files['reduced_features'],\n                                    0,  # indicators_count は後で計算\n                                    len(df.columns) - 1,  # timestampを除く\n                                    quality_score\n                                ))\n                                conn.commit()\n                            \n                            results.append({\n                                'symbol': symbol,\n                                'timeframe': timeframe,\n                                'status': 'success',\n                                'files': data_files,\n                                'records': len(df),\n                                'features': len(df.columns) - 1,\n                                'quality_score': quality_score\n                            })\n                            \n                            logger.info(f\"✓ {symbol} {timeframe}: {len(df)}件, {len(df.columns)-1}特徴量\")\n                        else:\n                            logger.error(f\"✗ {symbol} {timeframe}: ファイル生成失敗\")\n                            results.append({\n                                'symbol': symbol,\n                                'timeframe': timeframe,\n                                'status': 'failed',\n                                'error': 'ファイル生成失敗'\n                            })\n                    else:\n                        logger.error(f\"✗ {symbol} {timeframe}: データ取得エラー\\n{result.stderr}\")\n                        results.append({\n                            'symbol': symbol,\n                            'timeframe': timeframe,\n                            'status': 'failed',\n                            'error': result.stderr\n                        })\n                        \n                except subprocess.TimeoutExpired:\n                    logger.error(f\"✗ {symbol} {timeframe}: タイムアウト\")\n                    results.append({\n                        'symbol': symbol,\n                        'timeframe': timeframe,\n                        'status': 'failed',\n                        'error': 'タイムアウト'\n                    })\n                except Exception as e:\n                    logger.error(f\"✗ {symbol} {timeframe}: {e}\")\n                    results.append({\n                        'symbol': symbol,\n                        'timeframe': timeframe,\n                        'status': 'failed',\n                        'error': str(e)\n                    })\n        \n        return results\n    \n    def analyze_support_resistance(self, symbol, timeframe):\n        \"\"\"\n        サポート・レジスタンス分析を実行\n        \"\"\"\n        logger.info(f\"サポレジ分析開始: {symbol} {timeframe}\")\n        \n        try:\n            cmd = [\n                sys.executable,\n                \"support_resistance_visualizer.py\",\n                \"--symbol\", symbol,\n                \"--timeframe\", timeframe,\n                \"--min-touches\", \"2\"\n            ]\n            \n            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)\n            \n            if result.returncode == 0:\n                chart_file = f\"{symbol.lower()}_{timeframe}_support_resistance_analysis.png\"\n                if os.path.exists(chart_file):\n                    return {\n                        'status': 'success',\n                        'chart_path': chart_file,\n                        'output': result.stdout\n                    }\n                    \n            return {\n                'status': 'failed',\n                'error': result.stderr\n            }\n            \n        except Exception as e:\n            return {\n                'status': 'failed',\n                'error': str(e)\n            }\n    \n    def train_ml_models(self, symbol, timeframe):\n        \"\"\"\n        機械学習モデルを訓練\n        \"\"\"\n        logger.info(f\"ML訓練開始: {symbol} {timeframe}\")\n        \n        try:\n            cmd = [\n                sys.executable,\n                \"support_resistance_ml.py\",\n                \"--symbol\", symbol,\n                \"--timeframe\", timeframe,\n                \"--min-touches\", \"2\"\n            ]\n            \n            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)\n            \n            if result.returncode == 0:\n                # 生成されたモデルファイルを確認\n                model_files = {\n                    'model': f\"{symbol.lower()}_{timeframe}_sr_breakout_model.pkl\",\n                    'scaler': f\"{symbol.lower()}_{timeframe}_sr_breakout_scaler.pkl\",\n                    'interactions': f\"{symbol.lower()}_{timeframe}_sr_interactions.csv\"\n                }\n                \n                accuracy = self.extract_model_accuracy(result.stdout)\n                \n                return {\n                    'status': 'success',\n                    'model_files': model_files,\n                    'accuracy': accuracy,\n                    'output': result.stdout\n                }\n                    \n            return {\n                'status': 'failed',\n                'error': result.stderr\n            }\n            \n        except Exception as e:\n            return {\n                'status': 'failed',\n                'error': str(e)\n            }\n    \n    def extract_model_accuracy(self, output_text):\n        \"\"\"出力テキストからモデル精度を抽出\"\"\"\n        import re\n        # 精度情報を正規表現で抽出\n        accuracy_match = re.search(r'テストセット精度[:：]\\s*(\\d+\\.\\d+)', output_text)\n        if accuracy_match:\n            return float(accuracy_match.group(1))\n        return 0.0\n    \n    def generate_comprehensive_analysis(self, symbols=None, timeframes=None, max_workers=2):\n        \"\"\"\n        包括的な分析を実行（データ取得→サポレジ→ML）\n        \n        Args:\n            symbols: 分析対象シンボル（デフォルト: ['HYPE', 'BTC']）\n            timeframes: 分析対象タイムフレーム（デフォルト: ['1h']）\n            max_workers: 並列実行数\n        \"\"\"\n        if symbols is None:\n            symbols = ['HYPE', 'BTC']  # テスト用に2銘柄\n        if timeframes is None:\n            timeframes = ['1h']\n        \n        logger.info(f\"包括分析開始: {symbols} x {timeframes}\")\n        \n        results = {\n            'data_fetch': [],\n            'support_resistance': [],\n            'ml_training': [],\n            'summary': {}\n        }\n        \n        # 1. データ取得\n        logger.info(\"=== ステップ1: 市場データ取得 ===\")\n        data_results = self.fetch_market_data(symbols, timeframes, days=60)\n        results['data_fetch'] = data_results\n        \n        # 成功したデータのみで次のステップを実行\n        successful_pairs = [(r['symbol'], r['timeframe']) for r in data_results if r['status'] == 'success']\n        \n        # 2. サポート・レジスタンス分析\n        logger.info(\"=== ステップ2: サポート・レジスタンス分析 ===\")\n        for symbol, timeframe in successful_pairs:\n            sr_result = self.analyze_support_resistance(symbol, timeframe)\n            sr_result.update({'symbol': symbol, 'timeframe': timeframe})\n            results['support_resistance'].append(sr_result)\n        \n        # 3. 機械学習モデル訓練\n        logger.info(\"=== ステップ3: 機械学習モデル訓練 ===\")\n        for symbol, timeframe in successful_pairs:\n            ml_result = self.train_ml_models(symbol, timeframe)\n            ml_result.update({'symbol': symbol, 'timeframe': timeframe})\n            results['ml_training'].append(ml_result)\n        \n        # 4. 結果サマリー\n        results['summary'] = self.generate_analysis_summary(results)\n        \n        # 5. 結果をJSONで保存\n        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')\n        results_file = self.results_dir / f\"comprehensive_analysis_{timestamp}.json\"\n        \n        with open(results_file, 'w', encoding='utf-8') as f:\n            json.dump(results, f, ensure_ascii=False, indent=2, default=str)\n        \n        logger.info(f\"分析完了: {results_file}\")\n        return results\n    \n    def generate_analysis_summary(self, results):\n        \"\"\"分析結果のサマリーを生成\"\"\"\n        data_success = len([r for r in results['data_fetch'] if r['status'] == 'success'])\n        sr_success = len([r for r in results['support_resistance'] if r['status'] == 'success'])\n        ml_success = len([r for r in results['ml_training'] if r['status'] == 'success'])\n        \n        total_features = sum([r.get('features', 0) for r in results['data_fetch'] if r['status'] == 'success'])\n        avg_quality = np.mean([r.get('quality_score', 0) for r in results['data_fetch'] if r['status'] == 'success']) if data_success > 0 else 0\n        \n        ml_accuracies = [r.get('accuracy', 0) for r in results['ml_training'] if r['status'] == 'success' and r.get('accuracy', 0) > 0]\n        avg_accuracy = np.mean(ml_accuracies) if ml_accuracies else 0\n        \n        return {\n            'total_pairs_attempted': len(results['data_fetch']),\n            'data_fetch_success': data_success,\n            'support_resistance_success': sr_success,\n            'ml_training_success': ml_success,\n            'total_features_generated': total_features,\n            'avg_data_quality': avg_quality,\n            'avg_ml_accuracy': avg_accuracy,\n            'pipeline_success_rate': ml_success / len(results['data_fetch']) if results['data_fetch'] else 0\n        }\n    \n    def get_analysis_status(self):\n        \"\"\"現在の分析状況を取得\"\"\"\n        with sqlite3.connect(self.db_path) as conn:\n            # 市場データ状況\n            market_data_df = pd.read_sql_query(\n                \"SELECT * FROM market_data_status ORDER BY created_at DESC\", \n                conn\n            )\n            \n            # 分析結果状況\n            analysis_df = pd.read_sql_query(\n                \"SELECT * FROM strategy_analysis ORDER BY created_at DESC LIMIT 10\", \n                conn\n            )\n            \n            return {\n                'market_data_count': len(market_data_df),\n                'latest_market_data': market_data_df.head().to_dict('records'),\n                'latest_analyses': analysis_df.to_dict('records')\n            }\n\ndef main():\n    \"\"\"メイン実行関数\"\"\"\n    print(\"=\" * 60)\n    print(\"実市場データ統合システム\")\n    print(\"=\" * 60)\n    \n    # システム初期化\n    system = RealMarketAnalysisSystem()\n    \n    # 小規模テスト実行\n    print(\"\\n小規模テスト実行中...\")\n    print(\"対象: HYPE + BTC, 1時間足\")\n    \n    results = system.generate_comprehensive_analysis(\n        symbols=['HYPE', 'BTC'],\n        timeframes=['1h']\n    )\n    \n    # 結果表示\n    print(\"\\n=== 分析結果サマリー ===\")\n    summary = results['summary']\n    print(f\"対象ペア数: {summary['total_pairs_attempted']}\")\n    print(f\"データ取得成功: {summary['data_fetch_success']}\")\n    print(f\"サポレジ分析成功: {summary['support_resistance_success']}\")\n    print(f\"ML訓練成功: {summary['ml_training_success']}\")\n    print(f\"生成特徴量数: {summary['total_features_generated']}\")\n    print(f\"データ品質平均: {summary['avg_data_quality']:.3f}\")\n    print(f\"ML精度平均: {summary['avg_ml_accuracy']:.3f}\")\n    print(f\"パイプライン成功率: {summary['pipeline_success_rate']:.1%}\")\n    \n    # 詳細結果\n    print(\"\\n=== 詳細結果 ===\")\n    for result in results['data_fetch']:\n        status = \"✓\" if result['status'] == 'success' else \"✗\"\n        print(f\"{status} データ取得: {result['symbol']} {result['timeframe']}\")\n        if result['status'] == 'success':\n            print(f\"   {result['records']}件, {result['features']}特徴量, 品質{result['quality_score']:.3f}\")\n    \n    for result in results['support_resistance']:\n        status = \"✓\" if result['status'] == 'success' else \"✗\"\n        print(f\"{status} サポレジ: {result['symbol']} {result['timeframe']}\")\n    \n    for result in results['ml_training']:\n        status = \"✓\" if result['status'] == 'success' else \"✗\"\n        print(f\"{status} ML訓練: {result['symbol']} {result['timeframe']}\")\n        if result['status'] == 'success' and result.get('accuracy', 0) > 0:\n            print(f\"   精度: {result['accuracy']:.3f}\")\n    \n    print(\"\\n✅ 実市場データ統合テスト完了\")\n\nif __name__ == \"__main__\":\n    main()"