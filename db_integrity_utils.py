#!/usr/bin/env python3
"""
データベース参照整合性ユーティリティ
アプリケーションレベルでの外部キー制約実装
"""


def validate_execution_id(execution_id):
    """execution_idの有効性を検証"""
    if not execution_id:
        raise ValueError("execution_id は必須です")
    
    import sqlite3
    from pathlib import Path
    
    import os
    # 複数の可能なパスを試す
    possible_paths = [
        Path("execution_logs.db"),
        Path("../execution_logs.db"),
        Path(os.path.abspath("execution_logs.db")),
        Path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "execution_logs.db")),
    ]
    
    execution_db = None
    for path in possible_paths:
        if path.exists():
            execution_db = path
            break
    
    if not execution_db:
        # エラーメッセージに現在のディレクトリを含める
        raise FileNotFoundError(f"execution_logs.db が見つかりません (cwd: {os.getcwd()})")
    
    with sqlite3.connect(str(execution_db)) as conn:
        cursor = conn.execute(
            "SELECT execution_id FROM execution_logs WHERE execution_id = ?", 
            (execution_id,)
        )
        if not cursor.fetchone():
            raise ValueError(f"無効なexecution_id: {execution_id}")
    
    return True

def safe_insert_analysis(analysis_db_path, analysis_data):
    """安全な分析結果挿入（参照整合性チェック付き）"""
    execution_id = analysis_data.get('execution_id')
    
    # 参照整合性チェック
    validate_execution_id(execution_id)
    
    import sqlite3
    with sqlite3.connect(analysis_db_path) as conn:
        cursor = conn.execute("""
            INSERT INTO analyses 
            (symbol, timeframe, config, total_trades, win_rate, total_return, 
             sharpe_ratio, max_drawdown, avg_leverage, chart_path, compressed_path, execution_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis_data['symbol'],
            analysis_data['timeframe'], 
            analysis_data['config'],
            analysis_data.get('total_trades'),
            analysis_data.get('win_rate'),
            analysis_data.get('total_return'),
            analysis_data.get('sharpe_ratio'),
            analysis_data.get('max_drawdown'),
            analysis_data.get('avg_leverage'),
            analysis_data.get('chart_path'),
            analysis_data.get('compressed_path'),
            execution_id
        ))
        conn.commit()
        return cursor.lastrowid
