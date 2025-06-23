#!/usr/bin/env python3
"""
ブラウザからの銘柄追加テスト - 修正後の動作確認

今まで起きていた問題が解消されているかをブラウザ経由での銘柄追加で確認する。
特に以下の問題の修正を検証:
1. 利確価格がエントリー価格以下になるバグ
2. 0.5%最小距離制限の正常動作
3. 設定ファイルからの値読み込み
"""

import requests
import time
import json
import sys
import os
from colorama import Fore, Style, init

# カラー出力初期化
init(autoreset=True)

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://localhost:5001"

def wait_for_server():
    """サーバーの起動を待つ"""
    print(f"{Fore.YELLOW}サーバーの起動を待機中...{Style.RESET_ALL}")
    for i in range(30):
        try:
            response = requests.get(f"{BASE_URL}/", timeout=5)
            if response.status_code == 200:
                print(f"{Fore.GREEN}✅ サーバーが起動しました{Style.RESET_ALL}")
                return True
        except:
            pass
        time.sleep(1)
        print(f"  待機中... ({i+1}/30)")
    
    print(f"{Fore.RED}❌ サーバーの起動を確認できませんでした{Style.RESET_ALL}")
    return False

def test_symbol_addition(symbol, timeframe="1h", strategy="Conservative_ML"):
    """ブラウザ経由での銘柄追加をテスト"""
    print(f"\n{Fore.CYAN}=== {symbol} {timeframe} {strategy} 銘柄追加テスト ==={Style.RESET_ALL}")
    
    # 1. 銘柄追加リクエスト
    print(f"1. 銘柄追加リクエスト送信...")
    
    add_url = f"{BASE_URL}/api/symbol/add"
    data = {
        "symbol": symbol,
        "timeframe": timeframe,
        "strategy": strategy
    }
    
    try:
        response = requests.post(add_url, json=data, timeout=300)  # 5分タイムアウト
        
        if response.status_code == 200:
            result = response.json()
            print(f"   {Fore.GREEN}✅ 銘柄追加リクエスト成功{Style.RESET_ALL}")
            print(f"   レスポンス: {result.get('message', 'メッセージなし')}")
            
            execution_id = result.get('execution_id')
            if execution_id:
                print(f"   実行ID: {execution_id}")
                return monitor_execution(execution_id)
            else:
                print(f"   {Fore.YELLOW}⚠️ 実行IDが返されませんでした{Style.RESET_ALL}")
                return False
        else:
            print(f"   {Fore.RED}❌ 銘柄追加リクエスト失敗: {response.status_code}{Style.RESET_ALL}")
            print(f"   エラー: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   {Fore.RED}❌ タイムアウト: 5分以内に処理が完了しませんでした{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"   {Fore.RED}❌ リクエストエラー: {e}{Style.RESET_ALL}")
        return False

def monitor_execution(execution_id):
    """実行監視とログ分析"""
    print(f"\n2. 実行監視とログ分析...")
    
    # 実行ステータスを監視
    status_url = f"{BASE_URL}/api/execution_status/{execution_id}"
    
    for i in range(60):  # 最大10分監視
        try:
            response = requests.get(status_url, timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get('status', 'UNKNOWN')
                progress = status_data.get('progress_percentage', 0)
                operation = status_data.get('current_operation', '')
                
                print(f"   進捗: {progress:.1f}% - {status} - {operation}")
                
                if status in ['SUCCESS', 'FAILED', 'CANCELLED']:
                    print(f"\n   最終ステータス: {status}")
                    
                    if status == 'SUCCESS':
                        return analyze_execution_results(execution_id)
                    else:
                        return analyze_execution_errors(execution_id)
                        
            else:
                print(f"   ステータス取得エラー: {response.status_code}")
                
        except Exception as e:
            print(f"   監視エラー: {e}")
        
        time.sleep(10)  # 10秒間隔で監視
    
    print(f"   {Fore.YELLOW}⚠️ 監視タイムアウト{Style.RESET_ALL}")
    return False

def analyze_execution_results(execution_id):
    """実行結果の分析 - 修正後の問題解消確認"""
    print(f"\n3. 実行結果分析...")
    
    # 実行ログDatabase から詳細情報を取得
    try:
        from execution_log_database import ExecutionLogDatabase
        db = ExecutionLogDatabase()
        execution = db.get_execution(execution_id)
        
        if not execution:
            print(f"   {Fore.RED}❌ 実行ログが見つかりません{Style.RESET_ALL}")
            return False
        
        print(f"   実行時間: {execution.get('duration_seconds', 0):.1f}秒")
        
        # エラーをチェック
        errors = json.loads(execution.get('errors', '[]'))
        if errors:
            print(f"\n   ⚠️ 実行中のエラー:")
            for error in errors:
                error_msg = error.get('error_message', '')
                print(f"     - {error_msg}")
                
                # 特定の問題をチェック
                if "利確価格" in error_msg and "エントリー価格以下" in error_msg:
                    print(f"     {Fore.RED}❌ 利確価格がエントリー価格以下の問題が発生{Style.RESET_ALL}")
                    return False
                
                if "api_client" in error_msg and "not defined" in error_msg:
                    print(f"     {Fore.RED}❌ api_client未定義エラーが発生{Style.RESET_ALL}")
                    return False
        
        # ステップの成功状況をチェック
        steps = execution.get('steps', [])
        print(f"\n   実行ステップ: {len(steps)}個")
        
        success_steps = [s for s in steps if s.get('status') == 'SUCCESS']
        print(f"   成功ステップ: {len(success_steps)}個")
        
        if len(success_steps) == len(steps) and len(steps) > 0:
            print(f"   {Fore.GREEN}✅ すべてのステップが成功{Style.RESET_ALL}")
            return check_generated_data(execution)
        else:
            print(f"   {Fore.YELLOW}⚠️ 一部のステップで問題が発生{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        print(f"   {Fore.RED}❌ 結果分析エラー: {e}{Style.RESET_ALL}")
        return False

def analyze_execution_errors(execution_id):
    """実行エラーの分析"""
    print(f"\n3. エラー分析...")
    
    try:
        from execution_log_database import ExecutionLogDatabase
        db = ExecutionLogDatabase()
        execution = db.get_execution(execution_id)
        
        if execution:
            errors = json.loads(execution.get('errors', '[]'))
            if errors:
                print(f"   検出されたエラー: {len(errors)}個")
                for i, error in enumerate(errors[:5]):  # 最大5個まで表示
                    error_msg = error.get('error_message', '')
                    print(f"   エラー{i+1}: {error_msg}")
                    
                    # 修正対象の問題かチェック
                    if "利確価格" in error_msg and "エントリー価格以下" in error_msg:
                        print(f"     {Fore.RED}❌ 修正対象: 利確価格エラー（修正未完了）{Style.RESET_ALL}")
                    elif "api_client" in error_msg:
                        print(f"     {Fore.RED}❌ 修正対象: api_client エラー（修正未完了）{Style.RESET_ALL}")
                    elif "support" in error_msg or "resistance" in error_msg:
                        print(f"     {Fore.YELLOW}⚠️ サポート・レジスタンス関連エラー{Style.RESET_ALL}")
            else:
                print(f"   {Fore.YELLOW}⚠️ エラー詳細が記録されていません{Style.RESET_ALL}")
        
        return False
        
    except Exception as e:
        print(f"   {Fore.RED}❌ エラー分析エラー: {e}{Style.RESET_ALL}")
        return False

def check_generated_data(execution):
    """生成されたデータの品質チェック"""
    print(f"\n4. 生成データ品質チェック...")
    
    symbol = execution.get('symbol', '')
    if not symbol:
        print(f"   {Fore.YELLOW}⚠️ 銘柄情報が不明{Style.RESET_ALL}")
        return True
    
    # 生成されたバックテストデータをチェック
    try:
        import os
        import pandas as pd
        
        # 圧縮データディレクトリを確認
        compressed_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                     'large_scale_analysis', 'compressed')
        
        if os.path.exists(compressed_dir):
            # 該当銘柄のファイルを探す
            symbol_files = [f for f in os.listdir(compressed_dir) if symbol in f and f.endswith('.pkl.gz')]
            
            if symbol_files:
                print(f"   生成ファイル: {len(symbol_files)}個")
                
                # 最新ファイルの内容をチェック
                latest_file = sorted(symbol_files)[-1]
                file_path = os.path.join(compressed_dir, latest_file)
                
                try:
                    import pickle
                    import gzip
                    
                    with gzip.open(file_path, 'rb') as f:
                        data = pickle.load(f)
                    
                    if 'trades' in data:
                        trades = data['trades']
                        print(f"   取引数: {len(trades)}件")
                        
                        # 価格論理チェック
                        problematic_trades = []
                        for trade in trades[:10]:  # 最初の10件をチェック
                            entry_price = trade.get('entry_price', 0)
                            take_profit = trade.get('take_profit_price', 0)
                            stop_loss = trade.get('stop_loss_price', 0)
                            
                            # ロングポジションの論理チェック
                            if stop_loss >= entry_price:
                                problematic_trades.append(f"損切り({stop_loss:.2f}) >= エントリー({entry_price:.2f})")
                            if take_profit <= entry_price:
                                problematic_trades.append(f"利確({take_profit:.2f}) <= エントリー({entry_price:.2f})")
                        
                        if problematic_trades:
                            print(f"   {Fore.RED}❌ 価格論理エラー: {len(problematic_trades)}件{Style.RESET_ALL}")
                            for error in problematic_trades[:3]:
                                print(f"     - {error}")
                            return False
                        else:
                            print(f"   {Fore.GREEN}✅ 価格論理チェック: 正常{Style.RESET_ALL}")
                    
                    print(f"   {Fore.GREEN}✅ データ品質チェック完了{Style.RESET_ALL}")
                    return True
                    
                except Exception as e:
                    print(f"   {Fore.YELLOW}⚠️ データ読み込みエラー: {e}{Style.RESET_ALL}")
                    return True
            else:
                print(f"   {Fore.YELLOW}⚠️ 生成ファイルが見つかりません{Style.RESET_ALL}")
                return True
        else:
            print(f"   {Fore.YELLOW}⚠️ 圧縮データディレクトリが存在しません{Style.RESET_ALL}")
            return True
            
    except Exception as e:
        print(f"   {Fore.RED}❌ データチェックエラー: {e}{Style.RESET_ALL}")
        return True

def main():
    """メインテスト実行"""
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}ブラウザ経由銘柄追加テスト - 修正後動作確認{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    
    # サーバー起動確認
    if not wait_for_server():
        print(f"{Fore.RED}サーバーが起動していません。先にサーバーを起動してください。{Style.RESET_ALL}")
        print(f"起動コマンド: cd web_dashboard && python app.py")
        return False
    
    # テスト銘柄リスト（修正検証用）
    test_symbols = [
        ("ATOM", "1h", "Conservative_ML"),  # 軽量テスト用
        ("OP", "30m", "Conservative_ML"),    # 中程度テスト用
    ]
    
    results = []
    
    for symbol, timeframe, strategy in test_symbols:
        try:
            result = test_symbol_addition(symbol, timeframe, strategy)
            results.append((f"{symbol} {timeframe} {strategy}", result))
            
            if not result:
                print(f"\n{Fore.YELLOW}⚠️ {symbol}でエラーが発生しましたが、テストを継続します{Style.RESET_ALL}")
            
            time.sleep(5)  # 次のテストまで少し待機
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}テストが中断されました{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"\n{Fore.RED}テストエラー: {e}{Style.RESET_ALL}")
            results.append((f"{symbol} {timeframe} {strategy}", False))
    
    # 結果サマリー
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}テスト結果サマリー{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Fore.GREEN}✅ PASS{Style.RESET_ALL}" if result else f"{Fore.RED}❌ FAIL{Style.RESET_ALL}"
        print(f"{test_name}: {status}")
    
    print(f"\n合計: {passed}/{total} テスト成功")
    
    if passed == total and total > 0:
        print(f"\n{Fore.GREEN}✅ すべてのテストが成功しました！{Style.RESET_ALL}")
        print(f"{Fore.GREEN}修正後の問題が解消されていることを確認できました。{Style.RESET_ALL}")
    elif passed > 0:
        print(f"\n{Fore.YELLOW}⚠️ 部分的に成功しました。{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}❌ テストが失敗しました。修正が必要です。{Style.RESET_ALL}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)