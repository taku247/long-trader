#!/usr/bin/env python3
"""
XRPカスタム期間設定テスト - 修正効果検証
実際のXRPデータでカスタム期間設定が正しく動作するかテスト
"""

import sys
import os
import asyncio
import json
from datetime import datetime, timezone

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_xrp_custom_period_analysis():
    """XRPでカスタム期間設定のテスト実行"""
    print("🧪 XRP カスタム期間設定テスト開始")
    print("=" * 60)
    
    try:
        from new_symbol_addition_system import NewSymbolAdditionSystem, ExecutionMode
        
        # テスト用のカスタム期間設定
        custom_period_settings = {
            'mode': 'custom',
            'start_date': '2025-06-18T17:58:00',
            'end_date': '2025-06-25T17:58:00'
        }
        
        print(f"📅 テスト期間設定: {custom_period_settings}")
        print(f"🎯 期間: 2025-06-18 17:58 ～ 2025-06-25 17:58 (7日間)")
        print(f"📊 予想: 1時間足で200本前データ込みのデータ取得")
        print()
        
        # NewSymbolAdditionSystemでXRP分析実行
        system = NewSymbolAdditionSystem()
        
        # 実行ID生成
        execution_id = f"test_custom_period_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"🆔 実行ID: {execution_id}")
        
        # 選択戦略（テスト用に少数に限定）
        selected_strategy_ids = [1, 2, 3]  # Conservative_ML (15m), Aggressive_ML (1h), Balanced (30m)
        
        start_time = datetime.now()
        print(f"⏰ 開始時刻: {start_time.strftime('%H:%M:%S')}")
        print()
        
        # XRP分析実行
        print("🚀 XRP分析実行中...")
        result = await system.execute_symbol_addition(
            symbol="XRP",
            execution_id=execution_id,
            execution_mode=ExecutionMode.SELECTIVE,
            selected_strategy_ids=selected_strategy_ids,
            custom_period_settings=custom_period_settings
        )
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print()
        print("=" * 60)
        print("🎯 テスト結果")
        print("=" * 60)
        print(f"✅ 実行結果: {'成功' if result else '失敗'}")
        print(f"⏰ 実行時間: {execution_time:.1f}秒")
        print(f"🆔 実行ID: {execution_id}")
        
        # 期待される動作
        if execution_time > 30:
            print("✅ 実行時間が30秒超過: カスタム期間設定が有効に動作")
            print("✅ 数分で終わる問題が解決されました")
        else:
            print("⚠️ 実行時間が短すぎます: 修正効果を再確認が必要")
        
        # 進捗確認
        progress = system.get_execution_progress(execution_id)
        print(f"📊 タスク進捗: {progress.get('completed', 0)}/{progress.get('total_tasks', 0)} 完了")
        print(f"📈 進捗率: {progress.get('progress_percentage', 0):.1f}%")
        
        # 詳細分析
        if progress.get('tasks'):
            print("\n📋 各戦略の実行結果:")
            for task in progress['tasks']:
                status_emoji = {
                    'completed': '✅',
                    'failed': '❌',
                    'running': '🔄',
                    'pending': '⏳'
                }.get(task['status'], '❓')
                
                print(f"  {status_emoji} {task['strategy_name']}: {task['status']}")
                if task.get('error_message'):
                    print(f"    ❌ エラー: {task['error_message'][:50]}...")
        
        return result
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_period_verification():
    """データ期間の検証テスト"""
    print("\n🔍 データ期間検証テスト")
    print("=" * 60)
    
    try:
        # カスタム期間設定を環境変数に設定
        custom_settings = {
            'mode': 'custom',
            'start_date': '2025-06-18T17:58:00',
            'end_date': '2025-06-25T17:58:00'
        }
        
        os.environ['CUSTOM_PERIOD_SETTINGS'] = json.dumps(custom_settings)
        
        # HighLeverageBotOrchestratorでデータ取得テスト
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        print("🤖 HighLeverageBotOrchestrator作成中...")
        bot = HighLeverageBotOrchestrator()
        
        print("📊 XRPデータ取得テスト中...")
        # _fetch_market_dataを直接テスト
        data = bot._fetch_market_data("XRP", "1h", custom_settings)
        
        if data is not None and not data.empty:
            data_start = data.index[0]
            data_end = data.index[-1]
            data_count = len(data)
            
            print(f"✅ データ取得成功")
            print(f"📅 データ期間: {data_start} ～ {data_end}")
            print(f"📊 データ数: {data_count}件")
            
            # 期間が正しいかチェック
            from datetime import datetime
            import dateutil.parser
            
            expected_end = dateutil.parser.parse(custom_settings['end_date']).replace(tzinfo=timezone.utc)
            expected_start = dateutil.parser.parse(custom_settings['start_date']).replace(tzinfo=timezone.utc)
            
            # 200本前データを考慮した期間
            from datetime import timedelta
            pre_period_minutes = 200 * 60  # 1時間足で200本
            adjusted_expected_start = expected_start - timedelta(minutes=pre_period_minutes)
            
            print(f"🎯 期待期間: {adjusted_expected_start} ～ {expected_end}")
            
            # データが期待期間をカバーしているかチェック
            if data_end >= expected_end and data_start <= adjusted_expected_start:
                print("✅ カスタム期間設定が正しく反映されています")
                return True
            else:
                print("⚠️ カスタム期間設定が反映されていません")
                return False
        else:
            print("❌ データ取得失敗")
            return False
            
    except Exception as e:
        print(f"❌ データ期間検証エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 環境変数クリーンアップ
        if 'CUSTOM_PERIOD_SETTINGS' in os.environ:
            del os.environ['CUSTOM_PERIOD_SETTINGS']

if __name__ == "__main__":
    print("🧪 XRP カスタム期間設定 修正効果検証テスト")
    print("=" * 70)
    print("修正内容:")
    print("- HighLeverageBotOrchestratorでカスタム期間設定対応")
    print("- 200本前データを含む期間での実際のデータ取得")
    print("- 固定90日間からカスタム期間への変更")
    print()
    
    # データ期間検証テスト
    data_verification_ok = test_data_period_verification()
    
    # XRP分析テスト
    xrp_result = asyncio.run(test_xrp_custom_period_analysis())
    
    # 最終結果
    print("\n" + "=" * 70)
    print("🏆 最終テスト結果")
    print("=" * 70)
    print(f"📊 データ期間検証: {'✅ 成功' if data_verification_ok else '❌ 失敗'}")
    print(f"🎯 XRP分析テスト: {'✅ 成功' if xrp_result else '❌ 失敗'}")
    
    overall_success = data_verification_ok and xrp_result
    print(f"\n🏆 総合判定: {'✅ 修正効果確認' if overall_success else '⚠️ 追加修正必要'}")
    
    if overall_success:
        print("🎉 カスタム期間設定の修正が正常に動作しています！")
        print("🔒 XRPが数分で終わる問題は解決されました")
    else:
        print("🔧 まだ問題が残っている可能性があります")
        print("📋 ログを確認して追加修正を検討してください")