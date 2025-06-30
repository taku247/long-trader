#!/usr/bin/env python3
"""
単一分析でのDiscord通知テスト
"""

import sys
import os
from pathlib import Path

# プロジェクトパスを追加
sys.path.append('/Users/moriwakikeita/tools/long-trader')

def test_single_analysis_with_discord():
    """単一分析でDiscord通知をテスト"""
    from scalable_analysis_system import ScalableAnalysisSystem
    
    print("🧪 単一分析Discord通知テスト開始")
    print("=" * 50)
    
    # ScalableAnalysisSystemのインスタンス作成
    system = ScalableAnalysisSystem()
    
    # テスト用の分析実行
    print("📊 テスト分析実行中...")
    result = system._generate_single_analysis(
        symbol="DISCORD_TEST",
        timeframe="1h", 
        config="Conservative_ML",
        execution_id="discord_test_single_001"
    )
    
    print(f"📋 分析結果: {result}")
    print("✅ 単一分析Discord通知テスト完了")
    
    # Discord通知ログを確認
    try:
        with open('/tmp/discord_notifications.log', 'r') as f:
            logs = f.read()
            if 'DISCORD_TEST' in logs:
                print("🎉 Discord通知ログに記録されました！")
                # 最新のログを表示
                lines = logs.strip().split('\n')
                for line in lines[-5:]:
                    if 'DISCORD_TEST' in line:
                        print(f"   {line}")
            else:
                print("⚠️ Discord通知ログが見つかりません")
    except Exception as e:
        print(f"❌ ログ確認エラー: {e}")

if __name__ == '__main__':
    test_single_analysis_with_discord()