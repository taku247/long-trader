#!/usr/bin/env python3
"""
SOL APIエンドポイント両方のテスト（依存関係なし）
"""
import sqlite3
import json
import os
import gzip
import pickle

def test_strategy_results_endpoint(symbol="SOL"):
    """戦略結果エンドポイントのテスト"""
    print(f"🧪 テスト1: /api/strategy-results/{symbol}")
    
    try:
        # ScalableAnalysisSystemのクエリロジック模擬
        db_path = 'large_scale_analysis/analysis.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # execution_logs.dbアタッチ
        exec_db_path = 'execution_logs.db'
        query = "SELECT * FROM analyses WHERE 1=1"
        params = []
        
        if os.path.exists(exec_db_path):
            conn.execute(f"ATTACH DATABASE '{exec_db_path}' AS exec_db")
            
            # manual_レコード数確認
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE execution_id LIKE 'manual_%'")
            manual_count = cursor.fetchone()[0]
            
            if manual_count > 0:
                # フォールバック: シンプルクエリ
                query = "SELECT * FROM analyses WHERE 1=1"
                print("  ✅ manual_レコード検出 - フォールバッククエリ使用")
        
        # フィルター追加
        query += " AND symbol = ?"
        params.append(symbol)
        query += " ORDER BY sharpe_ratio DESC LIMIT 50"
        
        cursor.execute(query, params)
        
        # カラム名取得
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        # 辞書形式に変換
        formatted_results = []
        for row in results:
            row_dict = dict(zip(columns, row))
            formatted_results.append({
                'symbol': row_dict['symbol'],
                'timeframe': row_dict['timeframe'],
                'config': row_dict['config'],
                'sharpe_ratio': float(row_dict['sharpe_ratio']) if row_dict['sharpe_ratio'] else 0,
                'win_rate': float(row_dict['win_rate']) if row_dict['win_rate'] else 0,
                'total_return': float(row_dict['total_return']) if row_dict['total_return'] else 0
            })
        
        conn.close()
        
        response = {
            'symbol': symbol,
            'results': formatted_results,
            'total_patterns': len(formatted_results)
        }
        
        print(f"  ✅ 成功: {len(formatted_results)}件の結果を取得")
        return response
        
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return {'error': str(e)}

def test_trade_details_endpoint(symbol="SOL", timeframe="30m", config="Aggressive_Traditional"):
    """トレード詳細エンドポイントのテスト"""
    print(f"🧪 テスト2: /api/strategy-results/{symbol}/{timeframe}/{config}/trades")
    
    try:
        # データベースからcompressed_pathを取得
        db_path = 'large_scale_analysis/analysis.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT compressed_path FROM analyses WHERE symbol=? AND timeframe=? AND config=?",
            (symbol, timeframe, config)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            print(f"  ❌ 圧縮データが見つかりません: {symbol}_{timeframe}_{config}")
            return {'error': f'No trade data found for {symbol} {timeframe} {config}'}
        
        compressed_path = result[0]
        print(f"  📁 圧縮ファイルパス: {compressed_path}")
        
        # 実際のファイルパスを構築
        if not compressed_path.startswith('/'):
            # 相対パスの場合
            full_path = os.path.join('large_scale_analysis', compressed_path)
        else:
            full_path = compressed_path
        
        # ファイル存在確認
        if not os.path.exists(full_path):
            # web_dashboard内のパスも試す
            alt_path = os.path.join('web_dashboard', 'large_scale_analysis', compressed_path)
            if os.path.exists(alt_path):
                full_path = alt_path
            else:
                print(f"  ❌ ファイルが見つかりません: {full_path}")
                print(f"  📁 代替パス確認: {alt_path}")
                return {'error': f'Compressed file not found: {compressed_path}'}
        
        print(f"  ✅ ファイル発見: {full_path}")
        
        # 圧縮データを読み込み
        try:
            with gzip.open(full_path, 'rb') as f:
                trades_data = pickle.load(f)
            
            print(f"  ✅ データ読み込み成功: {type(trades_data)}")
            
            # データ形式確認
            if hasattr(trades_data, 'to_dict'):
                # DataFrameの場合
                trades = trades_data.to_dict('records')
                print(f"  📊 DataFrame -> {len(trades)}件のトレード")
            elif isinstance(trades_data, list):
                trades = trades_data
                print(f"  📊 List -> {len(trades)}件のトレード")
            else:
                print(f"  ⚠️ 不明なデータ形式: {type(trades_data)}")
                return {'error': f'Unexpected data format: {type(trades_data)}'}
            
            # サンプルデータ表示
            if trades and len(trades) > 0:
                sample = trades[0]
                print(f"  📝 サンプルトレード: {list(sample.keys()) if isinstance(sample, dict) else type(sample)}")
                
                # 基本的なトレード情報をフォーマット
                formatted_trades = []
                for i, trade in enumerate(trades[:5]):  # 最初の5件のみ
                    if isinstance(trade, dict):
                        formatted_trade = {
                            'entry_time': trade.get('entry_time', 'N/A'),
                            'exit_time': trade.get('exit_time', 'N/A'),
                            'entry_price': float(trade.get('entry_price', 0)),
                            'exit_price': float(trade.get('exit_price', 0)),
                            'leverage': float(trade.get('leverage', 0)),
                            'pnl_pct': float(trade.get('pnl_pct', 0)),
                            'is_success': bool(trade.get('is_success', trade.get('is_win', False)))
                        }
                        formatted_trades.append(formatted_trade)
                
                print(f"  ✅ {len(formatted_trades)}件のトレードをフォーマット")
                return formatted_trades
            else:
                print("  ❌ トレードデータが空です")
                return {'error': 'No trades found in data'}
        
        except Exception as e:
            print(f"  ❌ データ読み込みエラー: {e}")
            return {'error': f'Failed to load trade data: {e}'}
        
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return {'error': str(e)}

def main():
    """両方のエンドポイントをテスト"""
    print("=" * 60)
    print("🚀 SOL APIエンドポイント 両方動作確認テスト")
    print("=" * 60)
    
    # テスト1: 戦略結果一覧
    result1 = test_strategy_results_endpoint("SOL")
    
    print()
    
    # テスト2: トレード詳細（SOL 30m Aggressive_Traditional）
    result2 = test_trade_details_endpoint("SOL", "30m", "Aggressive_Traditional")
    
    print()
    print("=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)
    
    if 'error' not in result1:
        print(f"✅ 戦略結果API: {result1.get('total_patterns', 0)}件取得成功")
    else:
        print(f"❌ 戦略結果API: {result1['error']}")
    
    if 'error' not in result2:
        print(f"✅ トレード詳細API: {len(result2)}件取得成功")
    else:
        print(f"❌ トレード詳細API: {result2['error']}")

if __name__ == '__main__':
    main()