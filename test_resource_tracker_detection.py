#!/usr/bin/env python3
"""
Resource tracker検出テスト
手動リセット時の積極的クリーンアップの改善版をテスト
"""

import subprocess
import sys
import time
import psutil
from pathlib import Path

def create_fake_resource_tracker():
    """偽のresource_trackerプロセスを作成"""
    script = """
import time
import sys
import os

# resource_trackerプロセスをシミュレート
print(f"🧟 Fake resource_tracker started (PID: {os.getpid()})")
print(f"Command line: {' '.join(sys.argv)}")

# main(22)の形式をシミュレート
time.sleep(30)  # 30秒間実行
print(f"🧟 Fake resource_tracker finished")
"""
    
    # resource_trackerの典型的なコマンドライン形式
    cmd = [
        sys.executable, '-c', 
        'from multiprocessing.resource_tracker import main;main(22)'
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    return process

def test_detection_logic():
    """検出ロジックのテスト"""
    print("🧪 Testing resource_tracker detection logic...")
    
    # テスト用プロセスを作成
    fake_proc = create_fake_resource_tracker()
    print(f"Created fake resource_tracker: PID {fake_proc.pid}")
    
    # 少し待ってプロセスが起動するまで待機
    time.sleep(2)
    
    # 実際のプロセス情報を確認
    try:
        actual_proc = psutil.Process(fake_proc.pid)
        actual_cmdline = ' '.join(actual_proc.cmdline())
        print(f"Actual process cmdline: {actual_cmdline}")
    except:
        print(f"Could not access process {fake_proc.pid}")
    
    # 検出ロジックをテスト
    detected_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
        try:
            proc_info = proc.info
            if not proc_info['cmdline']:
                continue
            
            cmdline_list = proc_info.get('cmdline', [])
            if cmdline_list is None:
                cmdline_list = []
            cmdline = ' '.join(str(x) for x in cmdline_list)
            
            # 改善版検出ロジック
            is_target = False
            reason = ""
            
            if 'python' in proc_info['name'].lower():
                # 1. multiprocessing関連キーワード検出
                mp_keywords = [
                    'multiprocessing', 'spawn_main', 'resource_tracker',
                    'Pool', 'Process-', 'ProcessPoolExecutor'
                ]
                
                for keyword in mp_keywords:
                    if keyword in cmdline:
                        is_target = True
                        reason = f"keyword:{keyword}"
                        break
                
                # 2. 特定のコマンドパターン検出
                if not is_target:
                    target_patterns = [
                        'from multiprocessing.spawn import spawn_main',
                        'from multiprocessing.resource_tracker import main',
                        '--multiprocessing-fork'
                    ]
                    
                    for pattern in target_patterns:
                        if pattern in cmdline:
                            is_target = True
                            reason = f"pattern:{pattern[:20]}..."
                            break
                
                # 3. 引数による検出（main関数の数字引数）
                if not is_target and 'main(' in cmdline and any(c.isdigit() for c in cmdline):
                    is_target = True
                    reason = "main_with_args"
            
            if is_target:
                detected_processes.append({
                    'pid': proc_info['pid'],
                    'reason': reason,
                    'cmdline': cmdline
                })
                print(f"✅ Detected: PID {proc_info['pid']} ({reason})")
                print(f"   Command: {cmdline}")
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # テストプロセスを終了
    fake_proc.terminate()
    fake_proc.wait(timeout=5)
    
    print(f"\n🎯 Detection Results:")
    print(f"   Total detected processes: {len(detected_processes)}")
    
    # fake_procが検出されたかチェック
    fake_detected = any(p['pid'] == fake_proc.pid for p in detected_processes)
    
    if fake_detected:
        print("✅ Fake resource_tracker was successfully detected!")
        return True
    else:
        print("❌ Fake resource_tracker was NOT detected!")
        return False

if __name__ == "__main__":
    success = test_detection_logic()
    
    if success:
        print("\n🎉 Detection logic test passed!")
        sys.exit(0)
    else:
        print("\n💥 Detection logic test failed!")
        sys.exit(1)