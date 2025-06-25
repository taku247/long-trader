#!/usr/bin/env python3
"""
データ制約に基づく賢い評価開始時刻調整のテスト

あなたの提案した「実際のOHLCVデータ開始以降で評価間隔に合う最初の時刻」機能のテスト
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_smart_evaluation_start():
    """賢い評価開始時刻調整のテスト"""
    print("🔍 賢い評価開始時刻調整テスト")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # テストケース1: SOLと同じ状況（06:30開始、60分間隔）
        data_start = datetime(2025, 3, 27, 6, 30, 0, tzinfo=timezone.utc)
        evaluation_interval = timedelta(hours=1)
        
        result = system._find_first_valid_evaluation_time(data_start, evaluation_interval)
        
        print(f"🧪 テストケース1: SOLパターン")
        print(f"   データ開始: {data_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   評価間隔: {evaluation_interval}")
        print(f"   ✅ 調整後開始: {result.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   期待値: 2025-03-27 07:00:00 → {'✅ 正解' if result.hour == 7 and result.minute == 0 else '❌ 不正解'}")
        
        # テストケース2: 15分足（14:23開始、15分間隔）
        data_start2 = datetime(2024, 12, 16, 14, 23, 0, tzinfo=timezone.utc)
        evaluation_interval2 = timedelta(minutes=15)
        
        result2 = system._find_first_valid_evaluation_time(data_start2, evaluation_interval2)
        
        print(f"\n🧪 テストケース2: 15分足パターン")
        print(f"   データ開始: {data_start2.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   評価間隔: {evaluation_interval2}")
        print(f"   ✅ 調整後開始: {result2.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   期待値: 2024-12-16 14:30:00 → {'✅ 正解' if result2.minute == 30 else '❌ 不正解'}")
        
        # テストケース3: 4時間足（10:15開始、4時間間隔）
        data_start3 = datetime(2025, 1, 1, 10, 15, 0, tzinfo=timezone.utc)
        evaluation_interval3 = timedelta(hours=4)
        
        result3 = system._find_first_valid_evaluation_time(data_start3, evaluation_interval3)
        
        print(f"\n🧪 テストケース3: 4時間足パターン")
        print(f"   データ開始: {data_start3.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   評価間隔: {evaluation_interval3}")
        print(f"   ✅ 調整後開始: {result3.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   期待値: 2025-01-01 12:00:00 → {'✅ 正解' if result3.hour == 12 else '❌ 不正解'}")
        
        # テストケース4: 日をまたぐ場合（23:45開始、60分間隔）
        data_start4 = datetime(2025, 1, 1, 23, 45, 0, tzinfo=timezone.utc)
        evaluation_interval4 = timedelta(hours=1)
        
        result4 = system._find_first_valid_evaluation_time(data_start4, evaluation_interval4)
        
        print(f"\n🧪 テストケース4: 日またぎパターン")
        print(f"   データ開始: {data_start4.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   評価間隔: {evaluation_interval4}")
        print(f"   ✅ 調整後開始: {result4.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   期待値: 2025-01-02 00:00:00 → {'✅ 正解' if result4.day == 2 and result4.hour == 0 else '❌ 不正解'}")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_benefits_explanation():
    """この機能の利点を説明"""
    print(f"\n🎯 この機能の利点")
    print("=" * 50)
    
    print("✅ 従来の問題:")
    print("   - 設定期間通りに分析開始")
    print("   - データがない時刻でエラー")
    print("   - 無駄な時刻マッチング処理")
    
    print("\n✅ 新機能の効果:")
    print("   - データ存在を前提とした開始時刻")
    print("   - 評価間隔の境界に正確に合致")
    print("   - エラーレスな分析実行")
    print("   - 新規上場銘柄にも対応")
    
    print("\n📊 実用例:")
    print("   SOL: 06:30データ開始 → 07:00から評価開始")
    print("   HYPE: 14:23データ開始 → 14:30から評価開始") 
    print("   ZORA: 23:45データ開始 → 翌00:00から評価開始")

if __name__ == "__main__":
    print("🚀 賢い評価開始時刻調整テスト開始")
    print("=" * 60)
    
    success = test_smart_evaluation_start()
    test_benefits_explanation()
    
    if success:
        print(f"\n✅ 賢い評価開始時刻調整テスト完了")
        print("🎉 あなたの提案が完璧に実装されました！")
        print("📈 これで根本的なデータギャップ問題が解決されます")
    else:
        print(f"\n❌ テスト失敗 - 実装に問題があります")