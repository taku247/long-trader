#!/usr/bin/env python3
"""
実際に存在するトークンでのDiscord通知テスト
"""

import sys
import os
from pathlib import Path

# プロジェクトパスを追加
sys.path.append('/Users/moriwakikeita/tools/long-trader')

def test_real_token_analysis_with_discord():
    """実際のトークンでDiscord通知をテスト"""
    from scalable_analysis_system import ScalableAnalysisSystem
    
    print("🧪 実トークンDiscord通知テスト開始")
    print("=" * 50)
    
    # ScalableAnalysisSystemのインスタンス作成
    system = ScalableAnalysisSystem()
    
    # 実際のトークンでテスト分析実行
    real_tokens = ["BTC", "ETH", "SOL"]
    
    for token in real_tokens:
        print(f"📊 {token} 分析実行中...")
        try:
            result = system._generate_single_analysis(
                symbol=token,
                timeframe="1h", 
                config="Conservative_ML",
                execution_id=f"real_token_test_{token.lower()}_001"
            )
            print(f"📋 {token} 分析結果: {result[0] if result else 'None'}")
            
            # 少し待機
            import time
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ {token} 分析エラー: {e}")
    
    print("✅ 実トークンDiscord通知テスト完了")
    
    # Discord通知ログを確認
    try:
        with open('/tmp/discord_notifications.log', 'r') as f:
            logs = f.read()
            print("\n📋 Discord通知ログ:")
            lines = logs.strip().split('\n')
            for line in lines[-10:]:  # 最新10行
                if any(token in line for token in real_tokens):
                    print(f"   ✅ {line}")
                elif 'TEST' in line:
                    print(f"   🧪 {line}")
    except Exception as e:
        print(f"❌ ログ確認エラー: {e}")

if __name__ == '__main__':
    test_real_token_analysis_with_discord()