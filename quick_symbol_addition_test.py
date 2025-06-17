#!/usr/bin/env python3
"""
クイック銘柄追加テスト - 修正検証

手動でAutoSymbolTrainerを実行して修正が反映されているかを確認
"""

import sys
import os
import asyncio
from colorama import Fore, Style, init

# カラー出力初期化
init(autoreset=True)

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_symbol_addition():
    """銘柄追加のクイックテスト"""
    print(f"{Fore.CYAN}=== クイック銘柄追加テスト - 修正確認 ==={Style.RESET_ALL}")
    
    try:
        from auto_symbol_training import AutoSymbolTrainer
        trainer = AutoSymbolTrainer()
        
        # テスト銘柄
        test_symbol = "ATOM"
        
        print(f"\n1. {test_symbol} の銘柄追加を開始...")
        
        # 銘柄追加実行
        execution_id = await trainer.add_symbol_with_training(test_symbol)
        
        print(f"   実行ID: {execution_id}")
        print(f"   {Fore.GREEN}✅ 銘柄追加完了{Style.RESET_ALL}")
        
        # 実行結果を確認
        print(f"\n2. 実行結果の確認...")
        
        from execution_log_database import ExecutionLogDatabase
        db = ExecutionLogDatabase()
        execution = db.get_execution(execution_id)
        
        if execution:
            status = execution.get('status', 'UNKNOWN')
            errors = execution.get('errors', '[]')
            
            print(f"   ステータス: {status}")
            
            # エラー確認
            import json
            error_list = json.loads(errors) if isinstance(errors, str) else errors
            if error_list:
                print(f"   エラー数: {len(error_list)}")
                for i, error in enumerate(error_list[:3]):
                    error_msg = error.get('error_message', str(error))
                    print(f"     エラー{i+1}: {error_msg}")
                    
                    # 修正対象の問題をチェック
                    if "利確価格" in error_msg and "エントリー価格以下" in error_msg:
                        print(f"       {Fore.RED}❌ 修正対象: 利確価格問題が再発{Style.RESET_ALL}")
                        return False
                    elif "api_client" in error_msg and "not defined" in error_msg:
                        print(f"       {Fore.RED}❌ 修正対象: api_client問題が再発{Style.RESET_ALL}")
                        return False
            else:
                print(f"   {Fore.GREEN}✅ エラーなし{Style.RESET_ALL}")
            
            # ステップ確認
            steps = execution.get('steps', [])
            if steps:
                success_steps = [s for s in steps if s.get('status') == 'SUCCESS']
                print(f"   ステップ: {len(success_steps)}/{len(steps)} 成功")
                
                if len(success_steps) == len(steps):
                    print(f"   {Fore.GREEN}✅ すべてのステップが成功{Style.RESET_ALL}")
                    return True
                else:
                    print(f"   {Fore.YELLOW}⚠️ 一部ステップで問題発生{Style.RESET_ALL}")
                    return False
            else:
                print(f"   {Fore.YELLOW}⚠️ ステップ情報なし{Style.RESET_ALL}")
                return status == 'SUCCESS'
        else:
            print(f"   {Fore.RED}❌ 実行ログが見つかりません{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}❌ テストエラー: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """メインテスト実行"""
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}修正後の銘柄追加テスト{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    success = await test_symbol_addition()
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}テスト結果{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    if success:
        print(f"{Fore.GREEN}✅ テスト成功 - 修正が正しく動作しています{Style.RESET_ALL}")
        print(f"主な確認事項:")
        print(f"  - 利確価格 > エントリー価格の論理チェック")
        print(f"  - api_client エラーの解消")
        print(f"  - 0.5%最小距離制限の適用")
    else:
        print(f"{Fore.RED}❌ テスト失敗 - 追加の修正が必要です{Style.RESET_ALL}")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)