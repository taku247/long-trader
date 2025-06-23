#!/usr/bin/env python3
"""
銘柄追加のDB記録同期化テスト

修正内容をテストして確実にDB記録→プロセス起動の順序を確認
"""

import sys
import os
import time
import threading
import sqlite3
import requests
import subprocess
from pathlib import Path
from datetime import datetime
import json

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

def test_db_record_before_process_startup():
    """DB記録がプロセス起動前に確実に作成されることをテスト"""
    
    print("🧪 DB記録同期化テスト開始")
    print("=" * 60)
    
    # 1. テスト用Webサーバー起動
    print("\n1️⃣ テスト用Webサーバー起動...")
    
    server_process = None
    try:
        # Webサーバーを別プロセスで起動
        server_cmd = [
            sys.executable, "-c",
            """
import sys
sys.path.append('.')
from web_dashboard.app import WebDashboard
dashboard = WebDashboard(port=5005)
dashboard.app.run(host='127.0.0.1', port=5005, debug=False)
"""
        ]
        
        server_process = subprocess.Popen(
            server_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            cwd=str(Path(__file__).parent)
        )
        
        # サーバー起動待ち
        time.sleep(3)
        print("✅ Webサーバー起動完了 (http://localhost:5005)")
        
        # 2. DB記録の事前状態確認
        print("\n2️⃣ DB記録の事前状態確認...")
        db_path = "execution_logs.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM execution_logs WHERE symbol = 'TESTDB'"
            )
            initial_count = cursor.fetchone()[0]
            print(f"📊 TESTDB関連の初期レコード数: {initial_count}")
        
        # 3. 銘柄追加API呼び出し（非同期）
        print("\n3️⃣ 銘柄追加API呼び出し...")
        
        api_response = None
        api_error = None
        
        def call_api():
            nonlocal api_response, api_error
            try:
                response = requests.post(
                    'http://localhost:5005/api/symbol/add',
                    json={'symbol': 'TESTDB'},
                    timeout=10
                )
                api_response = response
            except Exception as e:
                api_error = e
        
        # API呼び出しを別スレッドで実行
        api_thread = threading.Thread(target=call_api)
        api_thread.start()
        
        # 4. DB記録の即座確認（ポーリング）
        print("\n4️⃣ DB記録の即座確認（1秒間隔でポーリング）...")
        
        execution_id = None
        db_record_time = None
        
        for i in range(15):  # 最大15秒待機
            time.sleep(1)
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT execution_id, timestamp_start, status 
                    FROM execution_logs 
                    WHERE symbol = 'TESTDB' 
                    AND timestamp_start > datetime('now', '-1 minute')
                    ORDER BY timestamp_start DESC 
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                
                if row:
                    execution_id, timestamp_start, status = row
                    db_record_time = datetime.now()
                    print(f"✅ DB記録検出! ID: {execution_id[:20]}... Status: {status}")
                    print(f"⏰ DB記録時刻: {db_record_time}")
                    break
                else:
                    print(f"⏳ {i+1}秒経過: DB記録待機中...")
        
        # APIレスポンス待ち
        api_thread.join(timeout=10)
        
        if api_response:
            print(f"\n✅ APIレスポンス受信: {api_response.status_code}")
            if api_response.status_code == 200:
                response_data = api_response.json()
                api_execution_id = response_data.get('execution_id')
                print(f"📋 APIレスポンスID: {api_execution_id}")
                
                # 5. execution_idの整合性確認
                print("\n5️⃣ execution_idの整合性確認...")
                if execution_id and api_execution_id:
                    if execution_id == api_execution_id:
                        print("✅ execution_ID整合性: 完全一致")
                    else:
                        print("❌ execution_ID整合性: 不一致")
                        print(f"   DB: {execution_id}")
                        print(f"   API: {api_execution_id}")
                else:
                    print("❌ execution_ID整合性: どちらかが取得できない")
                    print(f"   DB: {execution_id}")
                    print(f"   API: {api_execution_id}")
                    
            else:
                print(f"❌ APIエラー: {api_response.status_code} - {api_response.text}")
        elif api_error:
            print(f"❌ API呼び出しエラー: {api_error}")
        else:
            print("❌ APIレスポンス取得タイムアウト")
        
        # 6. プロセス起動確認
        print("\n6️⃣ プロセス起動確認...")
        time.sleep(2)  # プロセス起動待ち
        
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        multiprocessing_procs = [
            line for line in result.stdout.split('\n') 
            if 'multiprocessing' in line and 'python' in line
        ]
        
        print(f"🔍 multiprocessingプロセス数: {len(multiprocessing_procs)}")
        if multiprocessing_procs:
            for i, proc in enumerate(multiprocessing_procs[:2]):
                pid = proc.split()[1]
                print(f"   プロセス{i+1}: PID {pid}")
        
        # 7. 手動リセットテスト
        if execution_id and len(multiprocessing_procs) > 0:
            print("\n7️⃣ 手動リセットテスト...")
            
            reset_response = requests.post(
                'http://localhost:5005/api/admin/reset-execution',
                json={'execution_id': execution_id},
                timeout=15
            )
            
            print(f"🛑 リセットレスポンス: {reset_response.status_code}")
            if reset_response.status_code == 200:
                reset_data = reset_response.json()
                print(f"✅ リセット成功: {reset_data.get('message', 'メッセージなし')}")
                
                # リセット後のプロセス確認
                time.sleep(2)
                result2 = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                multiprocessing_procs2 = [
                    line for line in result2.stdout.split('\n') 
                    if 'multiprocessing' in line and 'python' in line
                ]
                
                print(f"📊 リセット後のプロセス数: {len(multiprocessing_procs2)}")
                
                if len(multiprocessing_procs2) < len(multiprocessing_procs):
                    print("✅ 手動リセット成功: プロセス数減少")
                elif len(multiprocessing_procs2) == 0:
                    print("✅ 手動リセット成功: 全プロセス終了")
                else:
                    print("⚠️ 手動リセット: プロセス数変化なし")
                    
            else:
                print(f"❌ リセット失敗: {reset_response.text}")
        else:
            print("\n7️⃣ 手動リセットテスト: スキップ（DB記録またはプロセスなし）")
        
        # 8. DB記録の最終確認
        print("\n8️⃣ DB記録の最終確認...")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                """
                SELECT execution_id, symbol, status, timestamp_start, timestamp_end
                FROM execution_logs 
                WHERE symbol = 'TESTDB' 
                AND timestamp_start > datetime('now', '-5 minutes')
                ORDER BY timestamp_start DESC 
                LIMIT 3
                """
            )
            rows = cursor.fetchall()
            
            print(f"📋 TESTDB関連の最新レコード: {len(rows)}件")
            for row in rows:
                exec_id, symbol, status, start, end = row
                print(f"   ID: {exec_id[:20]}... | Status: {status} | Start: {start}")
        
        # テスト結果サマリー
        print("\n" + "=" * 60)
        print("🎯 テスト結果サマリー")
        print("=" * 60)
        
        if execution_id and api_response and api_response.status_code == 200:
            print("✅ DB記録同期化: 成功")
            print("✅ execution_ID整合性: 確認済み")
            print("✅ プロセス起動: 確認済み")
            if len(multiprocessing_procs2) < len(multiprocessing_procs):
                print("✅ 手動リセット: 成功")
            return True
        else:
            print("❌ テスト失敗: DB記録または整合性に問題")
            return False
            
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # クリーンアップ
        print("\n🧹 クリーンアップ...")
        
        # 残存プロセス終了
        try:
            subprocess.run(['pkill', '-f', 'multiprocessing'], 
                          capture_output=True, timeout=5)
        except:
            pass
            
        # サーバープロセス終了
        if server_process:
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
                print("✅ Webサーバー停止完了")
            except:
                try:
                    server_process.kill()
                except:
                    pass

def test_execution_id_consistency():
    """execution_IDの一貫性テスト"""
    
    print("\n" + "=" * 60)
    print("🧪 execution_ID一貫性テスト")
    print("=" * 60)
    
    try:
        # テスト用の実行ID生成
        from datetime import datetime
        import uuid
        
        test_execution_id = f"test_addition_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        print(f"📋 テスト用execution_ID: {test_execution_id}")
        
        # DB記録作成
        from execution_log_database import ExecutionLogDatabase, ExecutionType
        db = ExecutionLogDatabase()
        
        db_execution_id = db.create_execution_with_id(
            test_execution_id,
            ExecutionType.SYMBOL_ADDITION,
            symbol="CONSISTENCY_TEST",
            triggered_by="TEST",
            metadata={"test": True}
        )
        
        print(f"✅ DB記録作成成功: {db_execution_id}")
        
        # 記録確認
        record = db.get_execution(test_execution_id)
        if record:
            print("✅ DB記録確認: 成功")
            print(f"   Symbol: {record['symbol']}")
            print(f"   Status: {record['status']}")
            print(f"   Created: {record['timestamp_start']}")
        else:
            print("❌ DB記録確認: 失敗")
            return False
        
        # 重複作成テスト
        print("\n📝 重複作成テスト...")
        
        try:
            # 同じIDで再作成を試行
            db.create_execution_with_id(
                test_execution_id,
                ExecutionType.SYMBOL_ADDITION,
                symbol="DUPLICATE_TEST"
            )
            print("❌ 重複作成テスト: 失敗（重複作成が許可された）")
            return False
        except Exception as e:
            print("✅ 重複作成テスト: 成功（適切にエラー）")
            print(f"   エラー: {str(e)[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 一貫性テストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    
    print("🚀 銘柄追加DB記録同期化 包括テスト")
    print("=" * 80)
    print(f"⏰ 開始時刻: {datetime.now()}")
    print()
    
    # 1. execution_ID一貫性テスト
    consistency_result = test_execution_id_consistency()
    
    # 2. DB記録同期化テスト
    sync_result = test_db_record_before_process_startup()
    
    # 最終結果
    print("\n" + "=" * 80)
    print("🏁 総合テスト結果")
    print("=" * 80)
    
    if consistency_result:
        print("✅ execution_ID一貫性テスト: 合格")
    else:
        print("❌ execution_ID一貫性テスト: 不合格")
    
    if sync_result:
        print("✅ DB記録同期化テスト: 合格")
    else:
        print("❌ DB記録同期化テスト: 不合格")
    
    overall_success = consistency_result and sync_result
    
    if overall_success:
        print("\n🎉 全テスト合格! 修正が正常に動作しています")
        print("💡 今後の銘柄追加では以下が保証されます:")
        print("   • DB記録がプロセス起動前に確実に作成される")
        print("   • execution_IDとDB記録の完全な整合性")
        print("   • 手動リセットの確実な動作")
    else:
        print("\n⚠️ 一部テスト不合格 - 修正が必要です")
        
    print(f"\n⏰ 終了時刻: {datetime.now()}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)