#!/usr/bin/env python3
"""
SOLの分析結果をcompressed/ファイルからデータベースに復元
"""

import os
import pickle
import gzip
import sqlite3
from pathlib import Path
import json

def restore_sol_results():
    """SOLの分析結果をデータベースに復元"""
    
    # パス設定
    base_dir = Path(__file__).parent
    compressed_dir = base_dir / "web_dashboard/large_scale_analysis/compressed"
    db_path = base_dir / "large_scale_analysis/analysis.db"
    
    print(f"🔍 SOL分析ファイルを検索中...")
    
    # SOLの圧縮ファイルを検索
    sol_files = list(compressed_dir.glob("SOL_*.pkl.gz"))
    print(f"📁 見つかったSOLファイル: {len(sol_files)}個")
    
    if not sol_files:
        print("❌ SOLの分析ファイルが見つかりません")
        return
    
    # データベース接続
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        restored_count = 0
        
        for file_path in sol_files:
            print(f"📊 処理中: {file_path.name}")
            
            try:
                # ファイル名から情報を抽出
                # 例: SOL_15m_Conservative_ML.pkl.gz
                name_parts = file_path.stem.replace('.pkl', '').split('_')
                symbol = name_parts[0]
                timeframe = name_parts[1]
                config = '_'.join(name_parts[2:])
                
                # 圧縮ファイルを展開
                with gzip.open(file_path, 'rb') as f:
                    data = pickle.load(f)
                
                # データからメトリクスを抽出
                if isinstance(data, dict):
                    sharpe_ratio = data.get('sharpe_ratio', 0)
                    win_rate = data.get('win_rate', 0)
                    total_return = data.get('total_return', 0)
                    max_drawdown = data.get('max_drawdown', 0)
                    avg_leverage = data.get('avg_leverage', 0)
                    total_trades = data.get('total_trades', 0)
                else:
                    # データが辞書でない場合はデフォルト値
                    sharpe_ratio = 0
                    win_rate = 0
                    total_return = 0
                    max_drawdown = 0
                    avg_leverage = 0
                    total_trades = 0
                
                # 既存レコードの確認
                cursor.execute("""
                    SELECT id FROM analyses 
                    WHERE symbol = ? AND timeframe = ? AND config = ?
                """, (symbol, timeframe, config))
                
                existing = cursor.fetchone()
                
                if not existing:
                    # 新規レコードとして挿入
                    cursor.execute("""
                        INSERT INTO analyses 
                        (symbol, timeframe, config, sharpe_ratio, win_rate, total_return, 
                         max_drawdown, avg_leverage, total_trades, 
                         chart_path, data_compressed_path, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
                    """, (
                        symbol, timeframe, config, sharpe_ratio, win_rate, total_return,
                        max_drawdown, avg_leverage, total_trades,
                        f"charts/{symbol}_{timeframe}_{config}_chart.html",
                        str(file_path.relative_to(Path("large_scale_analysis")))
                    ))
                    
                    restored_count += 1
                    print(f"  ✅ レコード追加: {symbol}_{timeframe}_{config}")
                else:
                    print(f"  ⚠️ 既存レコード: {symbol}_{timeframe}_{config}")
                
            except Exception as e:
                print(f"  ❌ エラー {file_path.name}: {e}")
        
        # コミット
        conn.commit()
        print(f"\n🎉 復元完了: {restored_count}件のレコードを追加しました")
        
        # 確認
        cursor.execute("SELECT COUNT(*) FROM analyses WHERE symbol = 'SOL'")
        total_sol = cursor.fetchone()[0]
        print(f"📊 SOLの分析結果総数: {total_sol}件")

if __name__ == "__main__":
    restore_sol_results()