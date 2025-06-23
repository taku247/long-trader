#!/usr/bin/env python3
"""
トレード詳細エンドポイント模擬テスト（ダミーデータ使用）
"""
import sqlite3
import json

def test_trade_endpoint_logic(symbol="SOL", timeframe="30m", config="Aggressive_Traditional"):
    """トレード詳細エンドポイントのロジックテスト"""
    print(f"🧪 トレード詳細エンドポイントロジックテスト")
    print(f"   対象: {symbol}/{timeframe}/{config}")
    
    try:
        # ステップ1: データベースからcompressed_pathを取得
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
            print(f"  ❌ レコードが見つかりません")
            return {'error': f'No analysis found for {symbol} {timeframe} {config}'}
        
        compressed_path = result[0]
        print(f"  ✅ compressed_path取得: {compressed_path}")
        
        # ステップ2: ファイル存在確認（模擬）
        import os
        full_path = os.path.join('web_dashboard', 'large_scale_analysis', compressed_path)
        file_exists = os.path.exists(full_path)
        print(f"  📁 ファイル存在確認: {file_exists} ({full_path})")
        
        if not file_exists:
            return {'error': f'Compressed file not found: {compressed_path}'}
        
        # ステップ3: データ読み込み（ダミーデータで模擬）
        print(f"  🔄 データ読み込み模擬...")
        
        # ダミートレードデータ生成
        dummy_trades = []
        for i in range(10):  # 10トレードのダミーデータ
            trade = {
                'entry_time': f'2025-03-{20+i} 1{i}:30:00',
                'exit_time': f'2025-03-{20+i} 1{i}:45:00',
                'entry_price': 100.0 + i * 2.5,
                'exit_price': 102.0 + i * 2.8,
                'leverage': 5.0,
                'pnl_pct': 0.02 + i * 0.001,
                'is_success': i % 3 != 0,  # 2/3成功率
                'confidence': 0.75 + i * 0.02,
                'strategy': config
            }
            dummy_trades.append(trade)
        
        print(f"  ✅ ダミートレードデータ生成: {len(dummy_trades)}件")
        
        # ステップ4: フォーマット
        formatted_trades = []
        for trade in dummy_trades:
            formatted_trade = {
                'entry_time': trade['entry_time'],
                'exit_time': trade['exit_time'],
                'entry_price': float(trade['entry_price']),
                'exit_price': float(trade['exit_price']),
                'leverage': float(trade['leverage']),
                'pnl_pct': float(trade['pnl_pct']),
                'is_success': bool(trade['is_success']),
                'confidence': float(trade['confidence']),
                'strategy': trade['strategy']
            }
            formatted_trades.append(formatted_trade)
        
        print(f"  ✅ トレードデータフォーマット完了: {len(formatted_trades)}件")
        
        # サンプル表示
        print(f"  📊 サンプルトレード:")
        for i, trade in enumerate(formatted_trades[:3]):
            status = "成功" if trade['is_success'] else "失敗"
            print(f"    {i+1}. {trade['entry_time']} | {trade['entry_price']:.1f} -> {trade['exit_price']:.1f} | PnL: {trade['pnl_pct']:.3f} | {status}")
        
        return formatted_trades
        
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return {'error': str(e)}

def test_api_response_format():
    """API形式でのレスポンステスト"""
    print(f"\n🔄 API形式レスポンステスト...")
    
    trades = test_trade_endpoint_logic()
    
    if 'error' in trades:
        response = trades
    else:
        response = trades  # フラットなリスト形式
    
    print(f"\n📋 API レスポンス例:")
    print(json.dumps(response[:2] if isinstance(response, list) else response, indent=2, ensure_ascii=False))
    
    return response

def main():
    """メインテスト"""
    print("=" * 60)
    print("🧪 トレード詳細エンドポイント 模擬動作確認")
    print("=" * 60)
    
    # テスト実行
    result = test_api_response_format()
    
    print(f"\n📊 テスト結果:")
    if isinstance(result, list):
        print(f"✅ 成功: {len(result)}件のトレードデータを取得")
        success_count = sum(1 for t in result if t.get('is_success', False))
        print(f"   成功トレード: {success_count}/{len(result)} ({success_count/len(result)*100:.1f}%)")
    elif 'error' in result:
        print(f"❌ エラー: {result['error']}")
    else:
        print(f"⚠️ 予期しない結果: {type(result)}")

if __name__ == '__main__':
    main()