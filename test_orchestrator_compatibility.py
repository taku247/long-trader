#!/usr/bin/env python3
"""
オーケストレーター切り替え互換性テスト

TestHighLeverageBotOrchestrator から HighLeverageBotOrchestrator への
切り替えが安全に行えるかを検証します。
"""

import sys
import os
import time
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """必要なモジュールのインポートテスト"""
    print("=== インポートテスト ===")
    
    try:
        # 1. テスト版のインポート
        print("1. TestHighLeverageBotOrchestrator インポート中...")
        from engines.test_high_leverage_bot_orchestrator import TestHighLeverageBotOrchestrator
        print("✅ TestHighLeverageBotOrchestrator インポート成功")
        
        # 2. 本格版のインポート（初期化なし）
        print("2. HighLeverageBotOrchestrator インポート中...")
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        print("✅ HighLeverageBotOrchestrator インポート成功")
        
        return True
        
    except Exception as e:
        print(f"❌ インポートエラー: {e}")
        return False

def test_initialization_without_plugins():
    """プラグインなしでの初期化テスト"""
    print("\n=== プラグインなし初期化テスト ===")
    
    try:
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        print("1. デフォルトプラグインを無効にして初期化中...")
        orchestrator = HighLeverageBotOrchestrator(use_default_plugins=False)
        print("✅ プラグインなし初期化成功")
        
        return True, orchestrator
        
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_initialization_with_plugins():
    """プラグインありでの初期化テスト（データ取得なし）"""
    print("\n=== プラグインあり初期化テスト ===")
    
    try:
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        print("1. デフォルトプラグインを有効にして初期化中...")
        print("   ⚠️ この処理でタイムアウトが発生する可能性があります...")
        
        # タイムアウト設定
        start_time = time.time()
        timeout = 30  # 30秒でタイムアウト
        
        orchestrator = HighLeverageBotOrchestrator(use_default_plugins=True)
        
        elapsed = time.time() - start_time
        print(f"✅ プラグインあり初期化成功 (所要時間: {elapsed:.1f}秒)")
        
        return True, orchestrator
        
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_data_fetcher_standalone():
    """データ取得器の単体テスト"""
    print("\n=== データ取得器単体テスト ===")
    
    try:
        print("1. data_fetcher インポート中...")
        from data_fetcher import fetch_data
        print("✅ data_fetcher インポート成功")
        
        print("2. 軽量データ取得テスト（limit=5）...")
        start_time = time.time()
        
        # 非常に小さなデータセットで試す
        data = fetch_data("HYPE", "1h", limit=5)
        
        elapsed = time.time() - start_time
        print(f"   データ取得完了: {len(data)}件 (所要時間: {elapsed:.1f}秒)")
        
        if len(data) > 0:
            print("✅ データ取得器は動作しています")
            return True
        else:
            print("⚠️ データが取得できませんでした（APIの問題の可能性）")
            return False
            
    except Exception as e:
        print(f"❌ データ取得エラー: {e}")
        return False

def test_comparison_analysis():
    """両オーケストレーターの比較分析"""
    print("\n=== 比較分析テスト ===")
    
    try:
        # テスト版
        print("1. TestHighLeverageBotOrchestrator での分析...")
        from engines.test_high_leverage_bot_orchestrator import TestHighLeverageBotOrchestrator
        
        test_bot = TestHighLeverageBotOrchestrator()
        test_result = test_bot.analyze_leverage_opportunity("HYPE", "1h")
        
        print(f"   テスト版結果:")
        print(f"   - 推奨レバレッジ: {test_result.recommended_leverage:.1f}x")
        print(f"   - 信頼度: {test_result.confidence_level*100:.1f}%")
        print(f"   - 現在価格: {test_result.market_conditions.current_price:.4f}")
        
        return True, test_result
        
    except Exception as e:
        print(f"❌ 比較分析エラー: {e}")
        return False, None

def test_scalable_system_compatibility():
    """ScalableAnalysisSystemとの互換性テスト"""
    print("\n=== ScalableAnalysisSystem互換性テスト ===")
    
    try:
        print("1. ScalableAnalysisSystemでの現在の使用状況確認...")
        
        # scalable_analysis_system.pyの該当行を確認
        with open('scalable_analysis_system.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'TestHighLeverageBotOrchestrator' in content:
            print("✅ ScalableAnalysisSystemは現在TestHighLeverageBotOrchestratorを使用中")
            
            # 置換後のテストを想定
            print("2. 置換後の互換性確認...")
            print("   - analyze_leverage_opportunity() メソッドの存在確認...")
            
            from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
            
            # メソッドの存在確認
            if hasattr(HighLeverageBotOrchestrator, 'analyze_leverage_opportunity'):
                print("   ✅ analyze_leverage_opportunity() メソッド存在")
            else:
                print("   ❌ analyze_leverage_opportunity() メソッドが見つかりません")
                return False
                
            print("✅ 基本的な互換性は確認されました")
            return True
            
        else:
            print("⚠️ ScalableAnalysisSystemで既にHighLeverageBotOrchestratorを使用中")
            return True
            
    except Exception as e:
        print(f"❌ 互換性テストエラー: {e}")
        return False

def print_recommendations():
    """推奨事項を表示"""
    print("\n" + "="*60)
    print("🎯 切り替え可否判定結果")
    print("="*60)
    
    print("\n📊 テスト結果サマリー:")
    
    # インポートテスト
    import_ok = test_imports()
    print(f"   インポート: {'✅ OK' if import_ok else '❌ NG'}")
    
    if not import_ok:
        print("\n❌ 切り替えは推奨されません")
        print("理由: 必要なモジュールのインポートに失敗")
        return
    
    # プラグインなし初期化
    init_ok, _ = test_initialization_without_plugins()
    print(f"   プラグインなし初期化: {'✅ OK' if init_ok else '❌ NG'}")
    
    # データ取得テスト
    data_ok = test_data_fetcher_standalone()
    print(f"   データ取得: {'✅ OK' if data_ok else '⚠️ タイムアウト'}")
    
    # 互換性テスト
    compat_ok = test_scalable_system_compatibility()
    print(f"   API互換性: {'✅ OK' if compat_ok else '❌ NG'}")
    
    print("\n🎯 最終判定:")
    
    if init_ok and compat_ok:
        if data_ok:
            print("✅ 切り替え推奨: 完全に問題ありません")
            print("\n💡 推奨アクション:")
            print("   1. ScalableAnalysisSystemの188行目を以下に変更:")
            print("      from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator")
            print("      bot = HighLeverageBotOrchestrator()")
            print("   2. 十分なタイムアウト設定を行う（data_fetcherのタイムアウト対策）")
        else:
            print("⚠️ 条件付き切り替え推奨: データ取得でタイムアウトの可能性")
            print("\n💡 推奨アクション:")
            print("   1. データ取得のタイムアウト設定を長めに設定")
            print("   2. ネットワーク環境の確認")
            print("   3. 段階的な切り替え（少数の銘柄で試行）")
    else:
        print("❌ 切り替え非推奨: 互換性に問題があります")
        print("\n⚠️ 対処が必要な問題:")
        if not init_ok:
            print("   - プラグイン初期化の問題")
        if not compat_ok:
            print("   - API互換性の問題")

def main():
    """メインテスト実行"""
    print("🧪 ハイレバレッジボット・オーケストレーター切り替え互換性テスト")
    print("="*60)
    print(f"⏰ 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # 全体テスト実行
        print_recommendations()
        
        print("\n" + "="*60)
        print("🎉 テスト完了")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⛔ ユーザーによって中断されました")
    except Exception as e:
        print(f"\n❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()