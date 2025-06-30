#!/usr/bin/env python3
"""
実際トークンの詳細分析テスト
"""

import sys
import os
from pathlib import Path

# プロジェクトパスを追加
sys.path.append('/Users/moriwakikeita/tools/long-trader')

def test_real_token_detailed():
    """実際のトークンで詳細分析"""
    from scalable_analysis_system import ScalableAnalysisSystem
    
    print("🔍 実トークン詳細分析テスト")
    print("=" * 50)
    
    # ScalableAnalysisSystemのインスタンス作成
    system = ScalableAnalysisSystem()
    
    # 存在チェック用の一意な戦略名
    test_symbol = "BTC"
    test_timeframe = "1h"
    test_config = "Test_Unique_Config_001"
    
    print(f"📊 {test_symbol} 詳細分析中...")
    print(f"   戦略: {test_config}")
    print(f"   時間足: {test_timeframe}")
    
    # 既存チェックの結果を確認
    analysis_id = f"{test_symbol}_{test_timeframe}_{test_config}"
    exists = system._analysis_exists(analysis_id)
    print(f"   既存分析存在: {exists}")
    
    if exists:
        print("   → 既存分析があるため、Discord通知はスキップされる")
    else:
        print("   → 新規分析として実行される")
    
    # 実際の分析実行（詳細ログ付き）
    try:
        print("\n🎯 分析実行開始...")
        result = system._generate_single_analysis(
            symbol=test_symbol,
            timeframe=test_timeframe, 
            config=test_config,
            execution_id=f"detailed_test_{test_symbol.lower()}_002"
        )
        print(f"📋 分析結果: {result}")
        
        if result[0]:
            print("✅ 分析成功 - Discord通知が送信されるはず")
        else:
            print("❌ 分析失敗または既存 - Discord通知なし")
            
    except Exception as e:
        print(f"❌ 分析エラー: {e}")
        import traceback
        traceback.print_exc()
    
    # 新しいトークンでのテスト
    print(f"\n🆕 新しいトークンでのテスト...")
    new_token = "DISCORD_REAL_TEST"
    try:
        result2 = system._generate_single_analysis(
            symbol=new_token,
            timeframe="1h", 
            config="Conservative_ML",
            execution_id=f"new_token_test_003"
        )
        print(f"📋 {new_token} 分析結果: {result2}")
    except Exception as e:
        print(f"❌ {new_token} 分析エラー: {e}")

if __name__ == '__main__':
    test_real_token_detailed()