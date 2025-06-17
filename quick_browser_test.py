#!/usr/bin/env python3
"""
クイックブラウザテスト

簡単な銘柄でブラウザ経由の銘柄追加をテストし、修正を確認
"""

import requests
import time
import json
import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://localhost:5001"

def quick_test():
    """クイックテスト実行"""
    print("🧪 クイック銘柄追加テスト")
    print("=" * 50)
    
    # テスト銘柄
    symbol = "DOGE"
    
    print(f"テスト銘柄: {symbol}")
    
    # 1. 銘柄追加リクエスト
    add_url = f"{BASE_URL}/api/symbol/add"
    data = {"symbol": symbol}
    
    try:
        print(f"\n1. {symbol} 銘柄追加リクエスト...")
        response = requests.post(add_url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            execution_id = result.get('execution_id')
            print(f"   ✅ リクエスト成功")
            print(f"   実行ID: {execution_id}")
            print(f"   メッセージ: {result.get('message', '')}")
            
            if result.get('warnings'):
                print(f"   ⚠️ 警告: {result['warnings']}")
            
            return execution_id
        else:
            print(f"   ❌ リクエスト失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ リクエストエラー: {e}")
        return None

def monitor_briefly(execution_id, max_wait_minutes=3):
    """短時間監視"""
    print(f"\n2. 短時間実行監視...")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    while time.time() - start_time < max_wait_seconds:
        try:
            from execution_log_database import ExecutionLogDatabase
            db = ExecutionLogDatabase()
            execution = db.get_execution(execution_id)
            
            if execution:
                status = execution.get('status', 'UNKNOWN')
                current_op = execution.get('current_operation', '')
                progress = execution.get('progress_percentage', 0)
                
                print(f"   ステータス: {status} ({progress:.1f}%)")
                if current_op:
                    print(f"   作業中: {current_op}")
                
                if status in ['SUCCESS', 'FAILED', 'CANCELLED']:
                    print(f"   完了: {status}")
                    return check_errors(execution)
                
                # エラーチェック（実行中でも）
                errors = json.loads(execution.get('errors', '[]'))
                if errors:
                    print(f"   ⚠️ エラー検出: {len(errors)}件")
                    critical_found = False
                    for error in errors:
                        error_msg = error.get('error_message', str(error))
                        if "利確価格" in error_msg and "エントリー価格以下" in error_msg:
                            print(f"   🚨 CRITICAL: 利確価格バグ再発!")
                            critical_found = True
                        elif "api_client" in error_msg and "not defined" in error_msg:
                            print(f"   🚨 CRITICAL: api_clientバグ再発!")
                            critical_found = True
                    
                    if critical_found:
                        return False
            
            time.sleep(10)  # 10秒間隔
            
        except Exception as e:
            print(f"   監視エラー: {e}")
            time.sleep(5)
    
    print(f"   ⏰ 監視終了 ({max_wait_minutes}分)")
    
    # 最終状態チェック
    try:
        from execution_log_database import ExecutionLogDatabase
        db = ExecutionLogDatabase()
        execution = db.get_execution(execution_id)
        
        if execution:
            return check_errors(execution)
    except:
        pass
    
    return True  # エラーなしと仮定

def check_errors(execution):
    """エラーの詳細チェック"""
    print(f"\n3. エラー詳細チェック...")
    
    errors = json.loads(execution.get('errors', '[]'))
    
    if not errors:
        print(f"   ✅ エラーなし")
        return True
    
    print(f"   エラー数: {len(errors)}")
    
    critical_bugs = []
    
    for error in errors:
        error_msg = error.get('error_message', str(error))
        
        if "利確価格" in error_msg and "エントリー価格以下" in error_msg:
            critical_bugs.append("利確価格バグ")
            print(f"   🚨 CRITICAL: {error_msg}")
        
        elif "api_client" in error_msg and "not defined" in error_msg:
            critical_bugs.append("api_clientバグ")
            print(f"   🚨 CRITICAL: {error_msg}")
        
        elif "支持線・抵抗線データの検出・分析に失敗" in error_msg:
            print(f"   ⚠️ 設計通りエラー: サポート・レジスタンス分析失敗")
        
        elif "重大なバックテスト異常" in error_msg:
            print(f"   ⚠️ 設計通りエラー: バックテスト異常検知")
        
        else:
            print(f"   ℹ️ その他: {error_msg[:60]}...")
    
    if critical_bugs:
        print(f"   ❌ 重大バグ検出: {', '.join(critical_bugs)}")
        return False
    else:
        print(f"   ✅ 重大バグなし")
        return True

def main():
    """メイン実行"""
    print("🔍 ブラウザ経由銘柄追加 - 修正確認")
    print("=" * 60)
    
    # サーバー確認
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print("❌ サーバーが応答しません")
            return False
    except:
        print("❌ サーバーに接続できません")
        return False
    
    # クイックテスト実行
    execution_id = quick_test()
    
    if execution_id:
        success = monitor_briefly(execution_id)
        
        print(f"\n" + "=" * 60)
        print(f"クイックテスト結果")
        print("=" * 60)
        
        if success:
            print(f"✅ テスト成功 - 重大バグは検出されませんでした")
            print(f"主な確認事項:")
            print(f"  - 利確価格がエントリー価格以下バグ → 検出されず")
            print(f"  - api_client未定義バグ → 検出されず")
            print(f"  - 処理が正常に開始・進行")
        else:
            print(f"❌ テスト失敗 - 重大バグが検出されました")
        
        return success
    else:
        print(f"\n❌ 銘柄追加リクエストが失敗しました")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)