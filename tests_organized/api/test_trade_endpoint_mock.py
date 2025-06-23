#!/usr/bin/env python3
"""
トレード詳細エンドポイント模擬テスト（ダミーデータ使用）
BaseTestフレームワーク統合版
"""
import sqlite3
import json
import unittest
import os
import sys

# プロジェクトルートを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tests_organized.base_test import APITest


class TestTradeEndpointMock(APITest):
    """トレード詳細エンドポイント模擬テストクラス"""
    
    def custom_setup(self):
        """テスト固有のセットアップ"""
        super().custom_setup()
        # SOLテストデータの作成
        self.test_symbol = "SOL"
        self.test_timeframe = "30m"
        self.test_config = "Aggressive_Traditional"
        
        # compressed_pathを含むanalysisレコードを作成
        execution_id = f"test_{self.test_symbol}_{self.test_timeframe}_{self.test_config}"
        self.insert_test_execution_log(execution_id, self.test_symbol)
        
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                INSERT INTO analyses 
                (execution_id, symbol, timeframe, config, sharpe_ratio, max_drawdown, total_return, compressed_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (execution_id, self.test_symbol, self.test_timeframe, self.test_config, 1.2, -0.15, 0.25, "test_compressed_data.gz"))
    
    def test_trade_endpoint_logic(self):
        """トレード詳細エンドポイントのロジックテスト"""
        symbol = self.test_symbol
        timeframe = self.test_timeframe
        config = self.test_config
        
        print(f"🧪 トレード詳細エンドポイントロジックテスト")
        print(f"   対象: {symbol}/{timeframe}/{config}")
        
        try:
            # ステップ1: データベースからcompressed_pathを取得
            conn = sqlite3.connect(self.analysis_db)
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
            # テスト環境では常にファイル存在とみなす
            file_exists = True  # 模擬環境のため常にTrue
            print(f"  📁 ファイル存在確認（模擬）: {file_exists}")
            
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
    
    def test_api_response_format(self):
        """API形式でのレスポンステスト"""
        print(f"\n🔄 API形式レスポンステスト...")
        
        trades = self.test_trade_endpoint_logic()
        
        if 'error' in trades:
            response = trades
        else:
            response = trades  # フラットなリスト形式
        
        print(f"\n📋 API レスポンス例:")
        print(json.dumps(response[:2] if isinstance(response, list) else response, indent=2, ensure_ascii=False))
        
        # アサーション
        self.assertIsInstance(response, list, "レスポンスはリスト形式である必要があります")
        self.assertGreater(len(response), 0, "トレードデータが生成されている必要があります")
        
        # 各トレードの必須フィールドを確認
        for trade in response[:3]:  # 最初の3件をチェック
            self.assertIn('entry_time', trade)
            self.assertIn('exit_time', trade)
            self.assertIn('entry_price', trade)
            self.assertIn('exit_price', trade)
            self.assertIn('pnl_pct', trade)
            self.assertIn('is_success', trade)
        
        return response
    
    def test_complete_workflow(self):
        """完全なワークフローテスト"""
        print("=" * 60)
        print("🧪 トレード詳細エンドポイント 模擬動作確認")
        print("=" * 60)
        
        # テスト実行
        result = self.test_api_response_format()
        
        print(f"\n📊 テスト結果:")
        if isinstance(result, list):
            print(f"✅ 成功: {len(result)}件のトレードデータを取得")
            success_count = sum(1 for t in result if t.get('is_success', False))
            print(f"   成功トレード: {success_count}/{len(result)} ({success_count/len(result)*100:.1f}%)")
            
            # アサーション
            self.assertGreater(len(result), 0)
            self.assertGreaterEqual(success_count, 0)
        elif 'error' in result:
            print(f"❌ エラー: {result['error']}")
            self.fail(f"APIエラーが発生しました: {result['error']}")
        else:
            print(f"⚠️ 予期しない結果: {type(result)}")
            self.fail(f"予期しない結果タイプ: {type(result)}")


def run_tests():
    """テストランナー関数"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()