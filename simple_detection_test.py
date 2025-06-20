#!/usr/bin/env python3
"""
実際のresource_trackerプロセスの検出テスト
"""

import psutil

def test_current_processes():
    """現在実行中のプロセスで検出ロジックをテスト"""
    print("🔍 Scanning current processes for multiprocessing related...")
    
    found_processes = []
    
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
                found_processes.append({
                    'pid': proc_info['pid'],
                    'name': proc_info['name'],
                    'reason': reason,
                    'cmdline': cmdline
                })
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    print(f"\n🎯 Found {len(found_processes)} multiprocessing-related processes:")
    
    for i, proc in enumerate(found_processes, 1):
        print(f"\n{i}. PID {proc['pid']} ({proc['name']}) - {proc['reason']}")
        print(f"   Command: {proc['cmdline'][:100]}...")
    
    return found_processes

if __name__ == "__main__":
    processes = test_current_processes()
    print(f"\n✅ Detection test completed. Found {len(processes)} processes.")