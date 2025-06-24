#!/usr/bin/env python3
"""
戦略実行デバッグツール

3つの戦略選択時の失敗原因を詳細調査するためのデバッグスクリプト
"""

import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

def debug_strategy_execution(symbol: str = "DOGE", execution_id: str = None):
    """戦略実行の詳細デバッグ"""
    
    print(f"🔍 {symbol} 戦略実行デバッグ開始")
    print("=" * 60)
    
    # データベースパス
    project_root = Path(__file__).parent
    analysis_db = project_root / "large_scale_analysis" / "analysis.db"
    execution_logs_db = project_root / "execution_logs.db"
    
    # 1. execution_logs テーブルから最新の実行情報を取得
    print("📊 1. 実行ログ確認")
    with sqlite3.connect(execution_logs_db) as conn:
        if execution_id:
            cursor = conn.execute("""
                SELECT execution_id, symbol, status, selected_strategy_ids, execution_mode, 
                       estimated_patterns, timestamp_start, timestamp_end, current_operation
                FROM execution_logs 
                WHERE execution_id = ?
            """, (execution_id,))
        else:
            cursor = conn.execute("""
                SELECT execution_id, symbol, status, selected_strategy_ids, execution_mode, 
                       estimated_patterns, timestamp_start, timestamp_end, current_operation
                FROM execution_logs 
                WHERE symbol = ? 
                ORDER BY timestamp_start DESC 
                LIMIT 1
            """, (symbol,))
        
        exec_info = cursor.fetchone()
        if exec_info:
            print(f"   実行ID: {exec_info[0]}")
            print(f"   銘柄: {exec_info[1]}")
            print(f"   ステータス: {exec_info[2]}")
            print(f"   選択戦略IDs: {exec_info[3]}")
            print(f"   実行モード: {exec_info[4]}")
            print(f"   推定パターン数: {exec_info[5]}")
            print(f"   開始時刻: {exec_info[6]}")
            print(f"   終了時刻: {exec_info[7]}")
            print(f"   現在の操作: {exec_info[8]}")
            execution_id = exec_info[0]
            selected_strategy_ids = json.loads(exec_info[3]) if exec_info[3] else []
        else:
            print(f"   ❌ {symbol} の実行ログが見つかりません")
            return
    
    print()
    
    # 2. strategy_configurations テーブルから選択された戦略の詳細を取得
    print("🎯 2. 選択戦略の詳細")
    with sqlite3.connect(analysis_db) as conn:
        if selected_strategy_ids:
            placeholders = ','.join('?' for _ in selected_strategy_ids)
            cursor = conn.execute(f"""
                SELECT id, name, base_strategy, timeframe, parameters, is_active, is_default
                FROM strategy_configurations 
                WHERE id IN ({placeholders})
                ORDER BY id
            """, selected_strategy_ids)
            
            strategies = cursor.fetchall()
            for strategy in strategies:
                print(f"   戦略ID {strategy[0]}: {strategy[1]}")
                print(f"     ベース戦略: {strategy[2]}")
                print(f"     時間足: {strategy[3]}")
                print(f"     パラメータ: {strategy[4]}")
                print(f"     アクティブ: {strategy[5]}")
                print(f"     デフォルト: {strategy[6]}")
                print()
        else:
            print("   ❌ 選択戦略IDが見つかりません")
    
    # 3. analyses テーブルから実際の分析結果を確認
    print("📈 3. 分析結果確認")
    with sqlite3.connect(analysis_db) as conn:
        cursor = conn.execute("""
            SELECT symbol, timeframe, config, strategy_config_id, strategy_name, 
                   task_status, error_message, total_return, sharpe_ratio, 
                   task_created_at, task_started_at, task_completed_at, execution_id
            FROM analyses 
            WHERE symbol = ? AND execution_id = ?
            ORDER BY strategy_config_id
        """, (symbol, execution_id))
        
        analyses = cursor.fetchall()
        if analyses:
            print(f"   分析レコード数: {len(analyses)}")
            for analysis in analyses:
                print(f"   戦略ID {analysis[3]}: {analysis[4]}")
                print(f"     時間足: {analysis[1]}")
                print(f"     設定: {analysis[2]}")
                print(f"     タスクステータス: {analysis[5]}")
                print(f"     エラーメッセージ: {analysis[6]}")
                print(f"     リターン: {analysis[7]}")
                print(f"     シャープレシオ: {analysis[8]}")
                print(f"     作成時刻: {analysis[9]}")
                print(f"     開始時刻: {analysis[10]}")
                print(f"     完了時刻: {analysis[11]}")
                print(f"     実行ID: {analysis[12]}")
                print()
        else:
            print(f"   ❌ {symbol} (実行ID: {execution_id}) の分析結果が見つかりません")
    
    # 4. execution_id なしの分析結果も確認（旧システム対応）
    print("📈 4. execution_id なしの分析結果確認")
    with sqlite3.connect(analysis_db) as conn:
        cursor = conn.execute("""
            SELECT symbol, timeframe, config, strategy_config_id, strategy_name, 
                   task_status, error_message, total_return, sharpe_ratio, 
                   generated_at, execution_id
            FROM analyses 
            WHERE symbol = ? AND execution_id IS NULL
            ORDER BY generated_at DESC
            LIMIT 10
        """, (symbol,))
        
        legacy_analyses = cursor.fetchall()
        if legacy_analyses:
            print(f"   execution_id なしの分析レコード数: {len(legacy_analyses)}")
            for analysis in legacy_analyses:
                print(f"   戦略: {analysis[2]} - {analysis[1]}")
                print(f"     タスクステータス: {analysis[5]}")
                print(f"     エラーメッセージ: {analysis[6]}")
                print(f"     リターン: {analysis[7]}")
                print(f"     シャープレシオ: {analysis[8]}")
                print(f"     生成時刻: {analysis[9]}")
                print(f"     実行ID: {analysis[10]}")
                print()
        else:
            print(f"   ❌ {symbol} の execution_id なし分析結果が見つかりません")
    
    # 5. ScalableAnalysisSystem の設定確認
    print("⚙️ 5. ScalableAnalysisSystem 設定確認")
    try:
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        system = NewSymbolAdditionSystem()
        
        # 戦略設定取得のテスト
        if selected_strategy_ids:
            print("   selected_strategy_ids から戦略設定取得テスト:")
            strategy_configs = system.get_strategy_configs_for_legacy(selected_strategy_ids)
            if strategy_configs:
                print(f"   取得された戦略設定数: {len(strategy_configs)}")
                for config in strategy_configs:
                    print(f"     戦略ID {config['id']}: {config['name']}")
                    print(f"       ベース戦略: {config['base_strategy']}")
                    print(f"       時間足: {config['timeframe']}")
            else:
                print("   ❌ 戦略設定が取得できませんでした")
        
    except Exception as e:
        print(f"   ❌ システム初期化エラー: {e}")
    
    # 6. 最近のエラーログ確認
    print("🚨 6. エラーログ確認")
    with sqlite3.connect(execution_logs_db) as conn:
        cursor = conn.execute("""
            SELECT execution_id, error_type, error_message, timestamp, step
            FROM execution_errors 
            WHERE execution_id = ?
            ORDER BY timestamp DESC
        """, (execution_id,))
        
        errors = cursor.fetchall()
        if errors:
            print(f"   エラー件数: {len(errors)}")
            for error in errors:
                print(f"   実行ID: {error[0]}")
                print(f"     エラータイプ: {error[1]}")
                print(f"     エラーメッセージ: {error[2]}")
                print(f"     時刻: {error[3]}")
                print(f"     ステップ: {error[4]}")
                print()
        else:
            print("   エラーログなし")
    
    print("=" * 60)
    print("🔍 デバッグ完了")


def debug_support_resistance_detection(symbol: str = "DOGE"):
    """支持線・抵抗線検出の詳細デバッグ"""
    
    print(f"📊 {symbol} 支持線・抵抗線検出デバッグ")
    print("=" * 60)
    
    try:
        # データ取得テスト
        from hyperliquid_api_client import MultiExchangeAPIClient
        
        # 取引所設定確認
        import json
        import os
        
        exchange = 'hyperliquid'  # デフォルト
        if os.path.exists('exchange_config.json'):
            with open('exchange_config.json', 'r') as f:
                config = json.load(f)
                exchange = config.get('default_exchange', 'hyperliquid').lower()
        
        print(f"使用取引所: {exchange}")
        
        # APIクライアント初期化
        api_client = MultiExchangeAPIClient(exchange_type=exchange)
        
        # データ取得テスト
        print("データ取得テスト:")
        ohlcv_data = api_client.get_ohlcv_data_with_period(symbol, '15m', days=30)
        print(f"  取得データ数: {len(ohlcv_data)}")
        print(f"  データ期間: {ohlcv_data['timestamp'].min()} - {ohlcv_data['timestamp'].max()}")
        print(f"  価格範囲: {ohlcv_data['low'].min():.4f} - {ohlcv_data['high'].max():.4f}")
        
        # 支持線・抵抗線検出テスト
        print("\n支持線・抵抗線検出テスト:")
        from engines.support_resistance_engine import SupportResistanceEngine
        
        sr_engine = SupportResistanceEngine()
        support_levels, resistance_levels = sr_engine.calculate_support_resistance(ohlcv_data)
        
        print(f"  検出された支持線数: {len(support_levels)}")
        print(f"  検出された抵抗線数: {len(resistance_levels)}")
        
        if len(support_levels) == 0 and len(resistance_levels) == 0:
            print("  ❌ 支持線・抵抗線が検出されませんでした")
            print("  原因の可能性:")
            print("    - データの変動が少ない")
            print("    - 価格レンジが狭い")
            print("    - 検出アルゴリズムの閾値が厳しい")
        else:
            print("  ✅ 支持線・抵抗線が検出されました")
            if support_levels:
                print(f"    支持線: {support_levels[:3]}...")  # 最初の3つ表示
            if resistance_levels:
                print(f"    抵抗線: {resistance_levels[:3]}...")  # 最初の3つ表示
        
    except Exception as e:
        print(f"❌ 支持線・抵抗線検出テストエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
    else:
        symbol = "DOGE"
    
    if len(sys.argv) > 2:
        execution_id = sys.argv[2]
    else:
        execution_id = None
    
    # 戦略実行デバッグ
    debug_strategy_execution(symbol, execution_id)
    
    print("\n" + "=" * 80 + "\n")
    
    # 支持線・抵抗線検出デバッグ
    debug_support_resistance_detection(symbol)