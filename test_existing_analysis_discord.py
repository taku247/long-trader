#!/usr/bin/env python3
"""
既存分析でのDiscord通知テスト
"""

import sys
import os
from pathlib import Path

# プロジェクトパスを追加
sys.path.append('/Users/moriwakikeita/tools/long-trader')

def test_existing_analysis_discord():
    """既存分析でのDiscord通知をテスト"""
    from scalable_analysis_system import ScalableAnalysisSystem
    
    print("🔁 既存分析Discord通知テスト")
    print("=" * 50)
    
    # ScalableAnalysisSystemのインスタンス作成
    system = ScalableAnalysisSystem()
    
    # 既存の分析を再実行（Discord通知テスト用）
    test_symbol = "BTC"
    test_timeframe = "1h"
    test_config = "Conservative_ML"  # 既存の分析
    
    print(f"📊 既存分析再実行テスト: {test_symbol} {test_config} - {test_timeframe}")
    
    # 既存チェック
    analysis_id = f"{test_symbol}_{test_timeframe}_{test_config}"
    exists = system._analysis_exists(analysis_id)
    print(f"   既存分析存在: {exists}")
    
    # 既存分析の実行（Discord通知確認）
    try:
        result = system._generate_single_analysis(
            symbol=test_symbol,
            timeframe=test_timeframe, 
            config=test_config,
            execution_id=f"existing_test_{test_symbol.lower()}_004"
        )
        print(f"📋 分析結果: {result}")
        
        if result[0]:
            print("✅ 新規分析として実行された")
        else:
            print("⏩ 既存分析のためスキップされた（Discord通知は送信されたはず）")
            
    except Exception as e:
        print(f"❌ 分析エラー: {e}")
    
    print("\n📋 Discord通知ログ確認:")
    try:
        with open('/tmp/discord_notifications.log', 'r') as f:
            logs = f.read()
            lines = logs.strip().split('\n')
            for line in lines[-5:]:  # 最新5行
                if test_symbol in line:
                    print(f"   📞 {line}")
    except Exception as e:
        print(f"❌ ログ確認エラー: {e}")

if __name__ == '__main__':
    test_existing_analysis_discord()