#!/usr/bin/env python3
"""
Web API経由での銘柄追加スクリプト
ブラウザからの銘柄追加と同じエンドポイント /api/symbol/add を使用
"""

import sys
import requests
import json
import time
import argparse
from typing import Optional, Dict, Any
from pathlib import Path

class SymbolAdditionAPI:
    """Web API経由での銘柄追加クライアント"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        """
        Args:
            base_url: Web dashboardのベースURL
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def check_server_status(self) -> bool:
        """サーバーが起動しているかチェック"""
        try:
            response = self.session.get(f"{self.base_url}/api/status", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def add_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        銘柄追加APIを呼び出し
        
        Args:
            symbol: 追加する銘柄名 (例: "GMT", "CAKE")
            
        Returns:
            APIレスポンス
        """
        url = f"{self.base_url}/api/symbol/add"
        payload = {"symbol": symbol.upper().strip()}
        
        try:
            print(f"🚀 銘柄追加リクエスト送信: {symbol}")
            print(f"📡 エンドポイント: {url}")
            print(f"📦 ペイロード: {json.dumps(payload, ensure_ascii=False)}")
            
            response = self.session.post(url, json=payload, timeout=30)
            
            print(f"📈 レスポンスコード: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 銘柄追加開始: {result}")
                return result
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {'error': response.text}
                print(f"❌ エラー: {error_data}")
                return error_data
                
        except requests.exceptions.Timeout:
            error = {'error': 'リクエストタイムアウト - サーバーが応答しません'}
            print(f"⏰ タイムアウト: {error}")
            return error
        except requests.exceptions.ConnectionError:
            error = {'error': 'サーバーに接続できません - Web dashboardが起動していない可能性があります'}
            print(f"🔌 接続エラー: {error}")
            return error
        except Exception as e:
            error = {'error': f'予期しないエラー: {str(e)}'}
            print(f"💥 エラー: {error}")
            return error
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """実行状態を取得"""
        try:
            url = f"{self.base_url}/api/execution/{execution_id}/status"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {'status': 'not_found'}
            else:
                return {'error': f'Status check failed: {response.status_code}'}
                
        except Exception as e:
            return {'error': f'Status check error: {str(e)}'}
    
    def monitor_execution(self, execution_id: str, max_wait_minutes: int = 30) -> None:
        """実行状況を監視"""
        print(f"\n📊 実行状況監視開始: {execution_id}")
        print(f"⏱️  最大待機時間: {max_wait_minutes}分")
        
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        check_interval = 10  # 10秒間隔でチェック
        
        while time.time() - start_time < max_wait_seconds:
            status = self.get_execution_status(execution_id)
            
            if not status:
                print("⚠️  ステータス取得失敗")
                time.sleep(check_interval)
                continue
            
            if 'error' in status:
                print(f"❌ ステータス取得エラー: {status['error']}")
                time.sleep(check_interval)
                continue
            
            # 実行状況表示
            execution_status = status.get('status', 'unknown')
            symbol = status.get('symbol', 'N/A')
            progress = status.get('progress', {})
            
            elapsed_minutes = (time.time() - start_time) / 60
            
            print(f"📈 [{elapsed_minutes:.1f}分経過] {symbol}: {execution_status}")
            
            if progress:
                completed = progress.get('completed_patterns', 0)
                total = progress.get('total_patterns', 18)
                completion_rate = (completed / total * 100) if total > 0 else 0
                print(f"   進捗: {completed}/{total} パターン完了 ({completion_rate:.1f}%)")
                
                # 現在処理中のパターン情報
                current_operation = progress.get('current_operation', '')
                if current_operation:
                    print(f"   現在: {current_operation}")
            
            # 完了チェック
            if execution_status in ['COMPLETED', 'SUCCESS']:
                print(f"🎉 実行完了!")
                
                # 結果情報があれば表示
                if 'results' in status:
                    results = status['results']
                    print(f"📊 結果:")
                    print(f"   - 最高Sharpe比: {results.get('best_sharpe', 'N/A')}")
                    print(f"   - 推奨戦略: {results.get('best_strategy', 'N/A')}")
                    print(f"   - 総パターン数: {results.get('total_patterns', 'N/A')}")
                
                return
            
            elif execution_status in ['FAILED', 'ERROR']:
                print(f"💥 実行失敗: {status.get('error_message', '詳細不明')}")
                return
            
            time.sleep(check_interval)
        
        print(f"⏰ 監視タイムアウト ({max_wait_minutes}分)")
        print(f"   最後のステータス: {execution_status}")
    
    def list_recent_executions(self, limit: int = 10) -> Optional[list]:
        """最近の実行履歴を取得"""
        try:
            url = f"{self.base_url}/api/executions?limit={limit}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"履歴取得失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"履歴取得エラー: {e}")
            return None
    
    def get_symbol_analysis_status(self, symbol: str) -> Optional[Dict[str, Any]]:
        """銘柄の分析状況を取得"""
        try:
            url = f"{self.base_url}/api/strategy-results/{symbol}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            print(f"分析状況取得エラー: {e}")
            return None

def print_banner():
    """バナー表示"""
    print("=" * 60)
    print("🚀 Long Trader - Web API銘柄追加ツール")
    print("=" * 60)
    print("ブラウザと同じエンドポイント (/api/symbol/add) を使用")
    print("実際のAPIデータで学習・バックテストを実行")
    print()

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='Web API経由での銘柄追加')
    parser.add_argument('symbols', nargs='+', help='追加する銘柄名 (例: GMT CAKE ARB)')
    parser.add_argument('--url', default='http://localhost:5001', help='Web dashboardのURL')
    parser.add_argument('--no-monitor', action='store_true', help='実行監視をスキップ')
    parser.add_argument('--max-wait', type=int, default=30, help='最大待機時間(分)')
    
    args = parser.parse_args()
    
    print_banner()
    
    # API クライアント初期化
    client = SymbolAdditionAPI(args.url)
    
    # サーバー接続チェック
    print(f"🔍 サーバー接続チェック: {args.url}")
    if not client.check_server_status():
        print("❌ Web dashboardに接続できません")
        print("以下を確認してください:")
        print("1. Web dashboardが起動している (python web_dashboard/app.py)")
        print(f"2. URLが正しい ({args.url})")
        print("3. ポート5001が開放されている")
        return 1
    
    print("✅ サーバー接続成功")
    
    # 実行結果を保存
    execution_results = []
    
    # 各銘柄を順次処理
    for i, symbol in enumerate(args.symbols, 1):
        print(f"\n{'='*40}")
        print(f"📊 銘柄追加 ({i}/{len(args.symbols)}): {symbol}")
        print(f"{'='*40}")
        
        # 銘柄追加実行
        result = client.add_symbol(symbol)
        
        if 'error' in result:
            print(f"❌ {symbol} の追加に失敗: {result['error']}")
            execution_results.append({
                'symbol': symbol,
                'status': 'failed',
                'error': result['error']
            })
            continue
        
        execution_id = result.get('execution_id')
        if not execution_id:
            print(f"⚠️  {symbol} の実行IDが取得できませんでした")
            execution_results.append({
                'symbol': symbol,
                'status': 'unknown'
            })
            continue
        
        print(f"🆔 実行ID: {execution_id}")
        
        execution_results.append({
            'symbol': symbol,
            'status': 'started',
            'execution_id': execution_id
        })
        
        # 実行監視
        if not args.no_monitor:
            client.monitor_execution(execution_id, args.max_wait)
        
        # 複数銘柄の場合は少し待機
        if i < len(args.symbols):
            print("\n⏱️  次の銘柄まで5秒待機...")
            time.sleep(5)
    
    # 最終結果サマリー
    print(f"\n{'='*60}")
    print("📈 実行結果サマリー")
    print(f"{'='*60}")
    
    for result in execution_results:
        symbol = result['symbol']
        status = result['status']
        
        if status == 'failed':
            print(f"❌ {symbol}: 失敗 - {result.get('error', '詳細不明')}")
        elif status == 'started':
            print(f"🚀 {symbol}: 開始済み (ID: {result.get('execution_id', 'N/A')})")
        else:
            print(f"⚠️  {symbol}: {status}")
    
    # 次のステップ案内
    print(f"\n💡 次のステップ:")
    print(f"1. Web Dashboard で進捗確認: {args.url}")
    print(f"2. 戦略結果ページで詳細確認: {args.url}/strategy-results")
    print(f"3. 実行履歴確認:")
    
    # 最近の実行履歴を表示
    recent_executions = client.list_recent_executions(5)
    if recent_executions:
        print(f"   最近の実行:")
        for exec_item in recent_executions[:3]:
            exec_id = exec_item.get('execution_id', 'N/A')[:16]
            symbol = exec_item.get('symbol', 'N/A')
            status = exec_item.get('status', 'N/A')
            print(f"   - {symbol}: {status} (ID: {exec_id}...)")
    
    print(f"\n✅ スクリプト実行完了")
    return 0

if __name__ == "__main__":
    sys.exit(main())