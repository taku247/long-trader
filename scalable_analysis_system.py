"""
大規模バックテスト分析システム
数千パターンに対応したスケーラブルな分析・可視化システム
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
from datetime import datetime
import logging
from pathlib import Path

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScalableAnalysisSystem:
    def __init__(self, base_dir="large_scale_analysis"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # ディレクトリ構造
        self.db_path = self.base_dir / "analysis.db"
        self.charts_dir = self.base_dir / "charts"
        self.data_dir = self.base_dir / "data"
        self.compressed_dir = self.base_dir / "compressed"
        
        for dir_path in [self.charts_dir, self.data_dir, self.compressed_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # データベース初期化
        self.init_database()
    
    def init_database(self):
        """SQLiteデータベースを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 分析メタデータテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    config TEXT NOT NULL,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_trades INTEGER,
                    win_rate REAL,
                    total_return REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    avg_leverage REAL,
                    chart_path TEXT,
                    data_compressed_path TEXT,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            
            # バックテスト結果サマリー
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtest_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER,
                    metric_name TEXT,
                    metric_value REAL,
                    FOREIGN KEY (analysis_id) REFERENCES analyses (id)
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timeframe ON analyses (symbol, timeframe)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_config ON analyses (config)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sharpe ON analyses (sharpe_ratio)')
            
            conn.commit()
    
    def generate_batch_analysis(self, batch_configs, max_workers=None):
        """
        バッチで大量の分析を並列生成
        
        Args:
            batch_configs: [{'symbol': 'BTC', 'timeframe': '1h', 'config': 'ML'}, ...]
            max_workers: 並列数（デフォルト: CPU数）
        """
        if max_workers is None:
            max_workers = min(cpu_count(), 8)  # 最大8並列
        
        logger.info(f"バッチ分析開始: {len(batch_configs)}パターン, {max_workers}並列")
        
        # バッチをチャンクに分割
        chunk_size = max(1, len(batch_configs) // max_workers)
        chunks = [batch_configs[i:i + chunk_size] for i in range(0, len(batch_configs), chunk_size)]
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i, chunk in enumerate(chunks):
                future = executor.submit(self._process_chunk, chunk, i)
                futures.append(future)
            
            # 結果収集
            total_processed = 0
            for future in futures:
                processed_count = future.result()
                total_processed += processed_count
        
        logger.info(f"バッチ分析完了: {total_processed}パターン処理完了")
        return total_processed
    
    def _process_chunk(self, configs_chunk, chunk_id):
        """チャンクを処理（プロセス内で実行）"""
        processed = 0
        for config in configs_chunk:
            try:
                result = self._generate_single_analysis(
                    config['symbol'], 
                    config['timeframe'], 
                    config['config']
                )
                if result:
                    processed += 1
                    if processed % 10 == 0:
                        logger.info(f"Chunk {chunk_id}: {processed}/{len(configs_chunk)} 完了")
            except Exception as e:
                logger.error(f"分析エラー {config}: {e}")
        
        return processed
    
    def _generate_single_analysis(self, symbol, timeframe, config):
        """単一の分析を生成（軽量版）"""
        analysis_id = f"{symbol}_{timeframe}_{config}"
        
        # 既存チェック
        if self._analysis_exists(analysis_id):
            return False
        
        # サンプルデータ生成（実際はここで本当のバックテストを実行）
        trades_data = self._generate_sample_trades(symbol, timeframe, config)
        
        # メトリクス計算
        metrics = self._calculate_metrics(trades_data)
        
        # データ圧縮保存
        compressed_path = self._save_compressed_data(analysis_id, trades_data)
        
        # チャート生成（必要時のみ）
        chart_path = None
        if self._should_generate_chart(metrics):
            chart_path = self._generate_lightweight_chart(analysis_id, trades_data, metrics)
        
        # データベース保存
        self._save_to_database(symbol, timeframe, config, metrics, chart_path, compressed_path)
        
        return True
    
    def _analysis_exists(self, analysis_id):
        """分析が既に存在するかチェック"""
        symbol, timeframe, config = analysis_id.split('_', 2)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM analyses WHERE symbol=? AND timeframe=? AND config=?',
                (symbol, timeframe, config)
            )
            return cursor.fetchone()[0] > 0
    
    def _generate_sample_trades(self, symbol, timeframe, config, num_trades=100):
        """サンプルトレードデータ生成（軽量版）"""
        np.random.seed(hash(f"{symbol}_{timeframe}_{config}") % 2**32)
        
        # 基本性能設定
        base_performance = {
            'Conservative_ML': {'sharpe': 1.2, 'win_rate': 0.65},
            'Aggressive_Traditional': {'sharpe': 1.8, 'win_rate': 0.55},
            'Full_ML': {'sharpe': 2.1, 'win_rate': 0.62}
        }.get(config, {'sharpe': 1.5, 'win_rate': 0.58})
        
        trades = []
        cumulative_return = 0
        
        for i in range(num_trades):
            # ランダムトレード生成
            is_win = np.random.random() < base_performance['win_rate']
            
            if is_win:
                pnl_pct = np.random.exponential(0.03)
            else:
                pnl_pct = -np.random.exponential(0.015)
            
            leverage = np.random.uniform(2.0, 8.0)
            leveraged_pnl = pnl_pct * leverage
            cumulative_return += leveraged_pnl
            
            trades.append({
                'trade_id': i,
                'pnl_pct': leveraged_pnl,
                'leverage': leverage,
                'is_win': is_win,
                'cumulative_return': cumulative_return
            })
        
        return pd.DataFrame(trades)
    
    def _calculate_metrics(self, trades_df):
        """メトリクス計算"""
        total_return = trades_df['cumulative_return'].iloc[-1] if len(trades_df) > 0 else 0
        win_rate = trades_df['is_win'].mean() if len(trades_df) > 0 else 0
        
        # Sharpe比の簡易計算
        returns = trades_df['pnl_pct'].values
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # 最大ドローダウン
        cum_returns = trades_df['cumulative_return'].values
        peak = np.maximum.accumulate(cum_returns)
        drawdown = (cum_returns - peak) / peak
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        return {
            'total_trades': len(trades_df),
            'total_return': total_return,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_leverage': trades_df['leverage'].mean() if len(trades_df) > 0 else 0
        }
    
    def _save_compressed_data(self, analysis_id, trades_df):
        """データを圧縮して保存"""
        compressed_path = self.compressed_dir / f"{analysis_id}.pkl.gz"
        
        with gzip.open(compressed_path, 'wb') as f:
            pickle.dump(trades_df, f)
        
        return str(compressed_path)
    
    def _should_generate_chart(self, metrics):
        """チャート生成が必要かどうか判定（上位パフォーマーのみ）"""
        return metrics['sharpe_ratio'] > 1.5  # Sharpe > 1.5のみチャート生成
    
    def _generate_lightweight_chart(self, analysis_id, trades_df, metrics):
        """軽量版チャート生成"""
        # 実装は省略（必要に応じて実装）
        chart_path = self.charts_dir / f"{analysis_id}_chart.html"
        
        # 簡易HTML作成
        html_content = f"""
        <html>
        <head><title>{analysis_id} Analysis</title></head>
        <body>
        <h1>{analysis_id}</h1>
        <p>Sharpe Ratio: {metrics['sharpe_ratio']:.2f}</p>
        <p>Win Rate: {metrics['win_rate']:.1%}</p>
        <p>Total Return: {metrics['total_return']:.1%}</p>
        </body>
        </html>
        """
        
        with open(chart_path, 'w') as f:
            f.write(html_content)
        
        return str(chart_path)
    
    def _save_to_database(self, symbol, timeframe, config, metrics, chart_path, compressed_path):
        """データベースに保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analyses 
                (symbol, timeframe, config, total_trades, win_rate, total_return, 
                 sharpe_ratio, max_drawdown, avg_leverage, chart_path, data_compressed_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
            ''', (
                symbol, timeframe, config,
                metrics['total_trades'], metrics['win_rate'], metrics['total_return'],
                metrics['sharpe_ratio'], metrics['max_drawdown'], metrics['avg_leverage'],
                chart_path, compressed_path
            ))
            
            conn.commit()
    
    def query_analyses(self, filters=None, order_by='sharpe_ratio', limit=100):
        """分析結果をクエリ"""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM analyses WHERE status='completed'"
            params = []
            
            if filters:
                if 'symbol' in filters:
                    query += " AND symbol IN ({})".format(','.join(['?' for _ in filters['symbol']]))
                    params.extend(filters['symbol'])
                
                if 'min_sharpe' in filters:
                    query += " AND sharpe_ratio >= ?"
                    params.append(filters['min_sharpe'])
            
            query += f" ORDER BY {order_by} DESC LIMIT ?"
            params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def get_statistics(self):
        """システム統計を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 基本統計
            cursor.execute("SELECT COUNT(*) as total, status FROM analyses GROUP BY status")
            status_counts = cursor.fetchall()
            
            # 性能統計
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_analyses,
                    AVG(sharpe_ratio) as avg_sharpe,
                    MAX(sharpe_ratio) as max_sharpe,
                    AVG(total_return) as avg_return,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    COUNT(DISTINCT config) as unique_configs
                FROM analyses WHERE status='completed'
            """)
            perf_stats = cursor.fetchone()
            
            return {
                'status_counts': dict(status_counts),
                'performance': {
                    'total_analyses': perf_stats[0],
                    'avg_sharpe': perf_stats[1],
                    'max_sharpe': perf_stats[2],
                    'avg_return': perf_stats[3],
                    'unique_symbols': perf_stats[4],
                    'unique_configs': perf_stats[5]
                }
            }
    
    def load_compressed_trades(self, symbol, timeframe, config):
        """圧縮されたトレードデータを読み込み"""
        analysis_id = f"{symbol}_{timeframe}_{config}"
        
        # データベースからパスを取得
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data_compressed_path FROM analyses WHERE symbol=? AND timeframe=? AND config=?",
                (symbol, timeframe, config)
            )
            result = cursor.fetchone()
            
            if not result or not result[0]:
                logger.warning(f"圧縮データが見つかりません: {analysis_id}")
                return None
            
            compressed_path = result[0]
        
        # 圧縮データを読み込み
        try:
            with gzip.open(compressed_path, 'rb') as f:
                trades_df = pickle.load(f)
            logger.info(f"トレードデータ読み込み完了: {analysis_id} ({len(trades_df)}トレード)")
            return trades_df
        except Exception as e:
            logger.error(f"データ読み込みエラー {analysis_id}: {e}")
            return None
    
    def load_multiple_trades(self, criteria=None):
        """複数の圧縮トレードデータを一括読み込み"""
        # クエリ条件に基づいて分析を取得
        analyses_df = self.query_analyses(filters=criteria)
        
        all_trades = {}
        for _, analysis in analyses_df.iterrows():
            trades_df = self.load_compressed_trades(
                analysis['symbol'], 
                analysis['timeframe'], 
                analysis['config']
            )
            if trades_df is not None:
                key = f"{analysis['symbol']}_{analysis['timeframe']}_{analysis['config']}"
                all_trades[key] = trades_df
        
        logger.info(f"読み込み完了: {len(all_trades)}件のトレードデータ")
        return all_trades
    
    def export_to_csv(self, symbol, timeframe, config, output_path=None):
        """圧縮データをCSVにエクスポート"""
        trades_df = self.load_compressed_trades(symbol, timeframe, config)
        
        if trades_df is None:
            return False
        
        if output_path is None:
            output_path = f"{symbol}_{timeframe}_{config}_trades_export.csv"
        
        trades_df.to_csv(output_path, index=False)
        logger.info(f"CSVエクスポート完了: {output_path}")
        return True
    
    def get_analysis_details(self, symbol, timeframe, config):
        """分析の詳細情報を取得（データベース + トレードデータ）"""
        # データベースから基本情報取得
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM analyses 
                WHERE symbol=? AND timeframe=? AND config=?
            """
            analysis_info = pd.read_sql_query(query, conn, params=[symbol, timeframe, config])
        
        if analysis_info.empty:
            return None
        
        # トレードデータも読み込み
        trades_df = self.load_compressed_trades(symbol, timeframe, config)
        
        return {
            'info': analysis_info.iloc[0].to_dict(),
            'trades': trades_df
        }
    
    def cleanup_low_performers(self, min_sharpe=0.5):
        """低パフォーマンス分析のクリーンアップ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 削除対象を取得
            cursor.execute(
                "SELECT chart_path, data_compressed_path FROM analyses WHERE sharpe_ratio < ?",
                (min_sharpe,)
            )
            to_delete = cursor.fetchall()
            
            # ファイル削除
            deleted_files = 0
            for chart_path, data_path in to_delete:
                for file_path in [chart_path, data_path]:
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_files += 1
            
            # データベースからも削除
            cursor.execute("DELETE FROM analyses WHERE sharpe_ratio < ?", (min_sharpe,))
            deleted_records = cursor.rowcount
            conn.commit()
            
            logger.info(f"クリーンアップ完了: {deleted_records}レコード, {deleted_files}ファイル削除")
            return deleted_records, deleted_files

def generate_large_scale_configs(symbols_count=20, timeframes=4, configs=10):
    """大規模設定を生成"""
    symbols = [f"TOKEN{i:03d}" for i in range(1, symbols_count + 1)]
    timeframes_list = ['1m', '3m', '5m', '15m', '30m', '1h'][:timeframes]
    configs_list = [f"Config_{i:02d}" for i in range(1, configs + 1)]
    
    batch_configs = []
    for symbol in symbols:
        for timeframe in timeframes_list:
            for config in configs_list:
                batch_configs.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'config': config
                })
    
    return batch_configs

def main():
    """大規模分析のデモ"""
    system = ScalableAnalysisSystem()
    
    # 1000パターンの設定生成
    configs = generate_large_scale_configs(symbols_count=10, timeframes=4, configs=25)
    print(f"生成された設定数: {len(configs)}")
    
    # バッチ分析実行
    processed = system.generate_batch_analysis(configs, max_workers=4)
    print(f"処理完了: {processed}パターン")
    
    # 統計表示
    stats = system.get_statistics()
    print("\n統計:")
    print(f"  総分析数: {stats['performance']['total_analyses']}")
    print(f"  平均Sharpe: {stats['performance']['avg_sharpe']:.2f}")
    print(f"  最高Sharpe: {stats['performance']['max_sharpe']:.2f}")
    print(f"  ユニーク銘柄数: {stats['performance']['unique_symbols']}")
    
    # 上位結果表示
    top_results = system.query_analyses(
        filters={'min_sharpe': 1.5},
        order_by='sharpe_ratio',
        limit=10
    )
    print(f"\n上位10結果:")
    print(top_results[['symbol', 'timeframe', 'config', 'sharpe_ratio', 'total_return']].to_string())

if __name__ == "__main__":
    main()