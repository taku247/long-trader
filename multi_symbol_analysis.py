"""
Multi-Symbol Real Market Analysis System
複数銘柄でのシステム堅牢性とML性能を評価
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

class MultiSymbolAnalysisSystem:
    def __init__(self, base_dir="real_market_analysis"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # ディレクトリ構造
        self.db_path = self.base_dir / "market_analysis.db"
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # 利用可能銘柄の確認
        self.available_symbols = self.detect_available_symbols()
        
        # データベース初期化
        self.init_database()
    
    def detect_available_symbols(self):
        """利用可能な銘柄を検出"""
        available = []
        symbols_to_check = ['HYPE', 'SOL', 'PEPE', 'WIF', 'BONK']
        
        for symbol in symbols_to_check:
            reduced_features_file = f"{symbol.lower()}_1h_90days_reduced_features.csv"
            if os.path.exists(reduced_features_file):
                available.append(symbol)
                logger.info(f"利用可能な銘柄: {symbol}")
            else:
                logger.warning(f"データなし: {symbol}")
        
        return available
    
    def init_database(self):
        """SQLiteデータベースを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # マルチシンボル分析結果テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS multi_symbol_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    data_quality_score REAL,
                    ml_accuracy REAL,
                    pipeline_success BOOLEAN,
                    records_count INTEGER,
                    features_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def analyze_existing_data(self, symbol, timeframe):
        """既存データの分析"""
        reduced_features_file = f"{symbol.lower()}_{timeframe}_90days_reduced_features.csv"
        
        if not os.path.exists(reduced_features_file):
            return None
        
        try:
            df = pd.read_csv(reduced_features_file)
            quality_score = 1.0 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'success',
                'records': len(df),
                'features': len(df.columns) - 1,
                'quality_score': quality_score,
                'file_path': reduced_features_file
            }
        except Exception as e:
            logger.error(f"データ分析エラー {symbol}: {e}")
            return None
    
    def run_support_resistance_analysis(self, symbol, timeframe):
        """サポート・レジスタンス分析を実行"""
        logger.info(f"サポレジ分析: {symbol} {timeframe}")
        
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
    
    def run_ml_training(self, symbol, timeframe):
        """機械学習モデルを訓練"""
        logger.info(f"ML訓練: {symbol} {timeframe}")
        
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
                    # 精度を抽出
                    accuracy = 0.0
                    if "精度:" in result.stdout:
                        import re
                        match = re.search(r'精度:\s*(\d+\.\d+)', result.stdout)
                        if match:
                            accuracy = float(match.group(1))
                    elif "平均精度:" in result.stdout:
                        match = re.search(r'平均精度:\s*(\d+\.\d+)', result.stdout)
                        if match:
                            accuracy = float(match.group(1))
                    
                    return {'status': 'success', 'accuracy': accuracy, 'output': result.stdout}
                    
            return {'status': 'failed', 'error': 'モデル生成失敗', 'output': result.stdout}
            
        except Exception as e:
            return {'status': 'failed', 'error': str(e)}
    
    def run_comprehensive_analysis(self):
        """包括的な分析を実行"""
        timeframe = '1h'
        analysis_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        logger.info(f"マルチシンボル分析開始: {self.available_symbols}")
        
        results = {
            'analysis_id': analysis_id,
            'symbols_analyzed': self.available_symbols,
            'data_analysis': [],
            'support_resistance': [],
            'ml_training': [],
            'performance_comparison': {},
            'summary': {}
        }
        
        # 1. 既存データ分析
        logger.info("=== ステップ1: データ品質分析 ===")
        for symbol in self.available_symbols:
            data_result = self.analyze_existing_data(symbol, timeframe)
            if data_result:
                results['data_analysis'].append(data_result)
        
        # 成功したシンボルのみで次のステップを実行
        successful_symbols = [r['symbol'] for r in results['data_analysis'] if r['status'] == 'success']
        
        # 2. サポート・レジスタンス分析
        logger.info("=== ステップ2: サポート・レジスタンス分析 ===")
        for symbol in successful_symbols:
            sr_result = self.run_support_resistance_analysis(symbol, timeframe)
            sr_result.update({'symbol': symbol, 'timeframe': timeframe})
            results['support_resistance'].append(sr_result)
        
        # 3. 機械学習モデル訓練
        logger.info("=== ステップ3: 機械学習モデル訓練 ===")
        for symbol in successful_symbols:
            ml_result = self.run_ml_training(symbol, timeframe)
            ml_result.update({'symbol': symbol, 'timeframe': timeframe})
            results['ml_training'].append(ml_result)
        
        # 4. 性能比較
        results['performance_comparison'] = self.generate_performance_comparison(results)
        
        # 5. サマリー生成
        results['summary'] = self.generate_summary(results)
        
        # 6. データベースに記録
        self.save_to_database(analysis_id, results)
        
        # 7. 結果をJSONで保存
        results_file = self.results_dir / f"multi_symbol_analysis_{analysis_id}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"分析完了: {results_file}")
        return results
    
    def generate_performance_comparison(self, results):
        """性能比較を生成"""
        comparison = {}
        
        # 各銘柄の総合性能
        for symbol in self.available_symbols:
            comparison[symbol] = {
                'data_quality': None,
                'sr_success': False,
                'ml_accuracy': None,
                'pipeline_success': False
            }
            
            # データ品質
            data_info = next((r for r in results['data_analysis'] if r['symbol'] == symbol), None)
            if data_info:
                comparison[symbol]['data_quality'] = data_info['quality_score']
            
            # サポレジ成功
            sr_info = next((r for r in results['support_resistance'] if r['symbol'] == symbol), None)
            if sr_info:
                comparison[symbol]['sr_success'] = sr_info['status'] == 'success'
            
            # ML精度
            ml_info = next((r for r in results['ml_training'] if r['symbol'] == symbol), None)
            if ml_info and ml_info['status'] == 'success':
                comparison[symbol]['ml_accuracy'] = ml_info.get('accuracy', 0)
            
            # パイプライン全体の成功
            comparison[symbol]['pipeline_success'] = all([
                comparison[symbol]['data_quality'] is not None,
                comparison[symbol]['sr_success'],
                comparison[symbol]['ml_accuracy'] is not None
            ])
        
        return comparison
    
    def generate_summary(self, results):
        """サマリーを生成"""
        successful_pipelines = sum(1 for perf in results['performance_comparison'].values() if perf['pipeline_success'])
        
        ml_accuracies = [perf['ml_accuracy'] for perf in results['performance_comparison'].values() 
                        if perf['ml_accuracy'] is not None]
        avg_ml_accuracy = np.mean(ml_accuracies) if ml_accuracies else 0
        
        data_qualities = [perf['data_quality'] for perf in results['performance_comparison'].values() 
                         if perf['data_quality'] is not None]
        avg_data_quality = np.mean(data_qualities) if data_qualities else 0
        
        return {
            'symbols_tested': len(self.available_symbols),
            'successful_pipelines': successful_pipelines,
            'pipeline_success_rate': successful_pipelines / len(self.available_symbols) if self.available_symbols else 0,
            'avg_ml_accuracy': avg_ml_accuracy,
            'avg_data_quality': avg_data_quality,
            'ml_accuracy_range': {
                'min': min(ml_accuracies) if ml_accuracies else 0,
                'max': max(ml_accuracies) if ml_accuracies else 0,
                'std': np.std(ml_accuracies) if ml_accuracies else 0
            }
        }
    
    def save_to_database(self, analysis_id, results):
        """データベースに結果を保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for symbol in self.available_symbols:
                perf = results['performance_comparison'][symbol]
                data_info = next((r for r in results['data_analysis'] if r['symbol'] == symbol), {})
                
                cursor.execute('''
                    INSERT INTO multi_symbol_results 
                    (analysis_id, symbol, timeframe, data_quality_score, ml_accuracy, 
                     pipeline_success, records_count, features_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    analysis_id, symbol, '1h',
                    perf['data_quality'],
                    perf['ml_accuracy'],
                    perf['pipeline_success'],
                    data_info.get('records', 0),
                    data_info.get('features', 0)
                ))
            
            conn.commit()
    
    def display_results(self, results):
        """結果を表示"""
        print("=" * 80)
        print("マルチシンボル実市場分析結果")
        print("=" * 80)
        
        # サマリー
        summary = results['summary']
        print(f"\n=== 分析サマリー ===")
        print(f"テスト銘柄数: {summary['symbols_tested']}")
        print(f"成功パイプライン: {summary['successful_pipelines']}")
        print(f"成功率: {summary['pipeline_success_rate']:.1%}")
        print(f"平均ML精度: {summary['avg_ml_accuracy']:.3f}")
        print(f"平均データ品質: {summary['avg_data_quality']:.3f}")
        print(f"ML精度範囲: {summary['ml_accuracy_range']['min']:.3f} - {summary['ml_accuracy_range']['max']:.3f}")
        print(f"ML精度標準偏差: {summary['ml_accuracy_range']['std']:.3f}")
        
        # 銘柄別詳細
        print(f"\n=== 銘柄別詳細結果 ===")
        for symbol in self.available_symbols:
            perf = results['performance_comparison'][symbol]
            print(f"\n{symbol}:")
            
            data_quality_str = f"{perf['data_quality']:.3f}" if perf['data_quality'] is not None else "N/A"
            print(f"  データ品質: {data_quality_str}")
            print(f"  サポレジ分析: {'✓' if perf['sr_success'] else '✗'}")
            
            ml_accuracy_str = f"{perf['ml_accuracy']:.3f}" if perf['ml_accuracy'] is not None else "N/A"
            print(f"  ML精度: {ml_accuracy_str}")
            print(f"  パイプライン: {'🟢 成功' if perf['pipeline_success'] else '🔴 失敗'}")
        
        # ML精度ランキング
        print(f"\n=== ML精度ランキング ===")
        ml_ranking = [(symbol, perf['ml_accuracy']) for symbol, perf in results['performance_comparison'].items() 
                     if perf['ml_accuracy'] is not None]
        ml_ranking.sort(key=lambda x: x[1], reverse=True)
        
        for i, (symbol, accuracy) in enumerate(ml_ranking, 1):
            print(f"{i}. {symbol}: {accuracy:.3f}")
        
        print(f"\n✅ マルチシンボル分析完了")

def main():
    """メイン実行関数"""
    print("マルチシンボル実市場分析システム")
    print("複数銘柄でのシステム堅牢性とML性能を評価")
    
    # システム初期化
    system = MultiSymbolAnalysisSystem()
    
    if not system.available_symbols:
        print("❌ 利用可能な銘柄データが見つかりません")
        return
    
    # 分析実行
    results = system.run_comprehensive_analysis()
    
    # 結果表示
    system.display_results(results)

if __name__ == "__main__":
    main()