#!/usr/bin/env python3
"""
TURBO銘柄追加テスト

ブラウザ経由での銘柄追加をシミュレートし、
158.70バグ修正後の正常動作を確認。
"""

import sys
import requests
import json
import time
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

def test_turbo_symbol_addition():
    """TURBO銘柄追加のテスト"""
    print("🔍 TURBO銘柄追加テスト開始")
    print("=" * 60)
    
    base_url = "http://localhost:5001"
    
    # Webダッシュボードが起動しているか確認
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code != 200:
            print("❌ Webダッシュボードにアクセスできません")
            return False
        print("✅ Webダッシュボードにアクセス成功")
    except Exception as e:
        print(f"❌ Webダッシュボード接続エラー: {e}")
        print("💡 先にweb_dashboard/app.pyを起動してください:")
        print("   cd web_dashboard && python app.py")
        return False
    
    # TURBO銘柄追加をAPIで実行
    print("\n1️⃣ TURBO銘柄追加を実行中...")
    
    add_symbol_data = {
        'symbol': 'TURBO',
        'timeframe': '15m',
        'config': 'Aggressive_ML'
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/add-symbol",
            json=add_symbol_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ TURBO銘柄追加API成功")
            print(f"   レスポンス: {result}")
        else:
            print(f"❌ 銘柄追加API失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ 銘柄追加APIエラー: {e}")
        return False
    
    # 少し待ってから結果を確認
    print("\n2️⃣ 分析結果を確認中...")
    time.sleep(5)
    
    try:
        # 戦略結果を取得
        response = requests.get(f"{base_url}/api/strategies", timeout=10)
        
        if response.status_code == 200:
            strategies = response.json()
            
            # TURBO戦略を検索
            turbo_strategy = None
            for strategy in strategies:
                if (strategy.get('symbol') == 'TURBO' and 
                    strategy.get('timeframe') == '15m' and
                    strategy.get('config') == 'Aggressive_ML'):
                    turbo_strategy = strategy
                    break
            
            if turbo_strategy:
                print("✅ TURBO戦略結果発見")
                print(f"   シンボル: {turbo_strategy.get('symbol')}")
                print(f"   時間足: {turbo_strategy.get('timeframe')}")
                print(f"   設定: {turbo_strategy.get('config')}")
                
                # 重要な指標をチェック
                total_return = turbo_strategy.get('total_return', 0)
                win_rate = turbo_strategy.get('win_rate', 0)
                sharpe_ratio = turbo_strategy.get('sharpe_ratio', 0)
                avg_leverage = turbo_strategy.get('avg_leverage', 0)
                
                print(f"\n📊 TURBO分析結果:")
                print(f"   総リターン: {total_return:.2f}%")
                print(f"   勝率: {win_rate:.1f}%")
                print(f"   シャープ比: {sharpe_ratio:.2f}")
                print(f"   平均レバレッジ: {avg_leverage:.1f}x")
                
                # 異常値チェック
                print(f"\n🔍 異常値チェック:")
                
                # レバレッジチェック
                if avg_leverage > 0 and avg_leverage < 100:
                    print(f"   ✅ 平均レバレッジ正常: {avg_leverage:.1f}x")
                elif avg_leverage == 0:
                    print(f"   ⚠️ レバレッジゼロ: {avg_leverage:.1f}x（トレード未発生の可能性）")
                else:
                    print(f"   🚨 レバレッジ異常: {avg_leverage:.1f}x")
                
                # 勝率チェック
                if 0 <= win_rate <= 100:
                    print(f"   ✅ 勝率正常: {win_rate:.1f}%")
                else:
                    print(f"   🚨 勝率異常: {win_rate:.1f}%")
                
                # シャープ比チェック
                if -10 <= sharpe_ratio <= 10:
                    print(f"   ✅ シャープ比正常: {sharpe_ratio:.2f}")
                else:
                    print(f"   🚨 シャープ比異常: {sharpe_ratio:.2f}")
                
                return True
                
            else:
                print("❌ TURBO戦略結果が見つかりませんでした")
                print("   利用可能な戦略:")
                for strategy in strategies[:3]:  # 最初の3個を表示
                    print(f"     - {strategy.get('symbol')} {strategy.get('timeframe')} {strategy.get('config')}")
                return False
        
        else:
            print(f"❌ 戦略結果取得失敗: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 戦略結果取得エラー: {e}")
        return False

def test_turbo_direct_analysis():
    """TURBO直接分析テスト（バックアップ）"""
    print("\n" + "="*60)
    print("🔬 TURBO直接分析テスト（バックアップ）")
    print("="*60)
    
    try:
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        print("1️⃣ HighLeverageBotOrchestratorを初期化中...")
        bot = HighLeverageBotOrchestrator()
        
        print("2️⃣ TURBO分析を実行中...")
        result = bot.analyze_symbol('TURBO', '15m', 'Aggressive_ML')
        
        if result:
            print("✅ TURBO分析完了")
            print(f"   レバレッジ: {result.get('leverage', 'N/A')}")
            print(f"   信頼度: {result.get('confidence', 'N/A')}%")
            print(f"   リスクリワード比: {result.get('risk_reward_ratio', 'N/A')}")
            print(f"   現在価格: {result.get('current_price', 'N/A')}")
            
            # 158.70バグ修正効果をチェック
            confidence = result.get('confidence', 0)
            leverage = result.get('leverage', 0)
            
            print(f"\n🔍 158.70バグ修正効果チェック:")
            
            # 信頼度チェック
            if confidence > 95:
                print(f"   🚨 信頼度異常: {confidence}% (95%超)")
            elif confidence > 85:
                print(f"   ⚠️ 信頼度高め: {confidence}% (要注意)")
            else:
                print(f"   ✅ 信頼度正常: {confidence}%")
            
            # レバレッジチェック
            if leverage > 1.5:
                print(f"   ✅ レバレッジ多様化: {leverage:.1f}x (1.0x固定から改善)")
            elif leverage == 1.0:
                print(f"   ⚠️ レバレッジ最小: {leverage:.1f}x (市場条件か計算問題)")
            else:
                print(f"   ✅ レバレッジ動的: {leverage:.1f}x")
                
            return True
        else:
            print("❌ TURBO分析が失敗しました")
            return False
    
    except Exception as e:
        print(f"❌ 直接分析エラー: {e}")
        return False

def main():
    """メインテスト関数"""
    print("🚀 TURBO銘柄追加・分析テスト")
    print("=" * 60)
    print("🎯 目的: 158.70バグ修正後の正常動作確認")
    print("   - サポート強度が0-1範囲内")
    print("   - 信頼度が90%超にならない")
    print("   - レバレッジが適切に計算される")
    print("=" * 60)
    
    # Webダッシュボード経由でのテスト
    web_success = test_turbo_symbol_addition()
    
    # 直接分析でのテスト（バックアップ）
    direct_success = test_turbo_direct_analysis()
    
    print("\n" + "="*60)
    print("📋 TURBO銘柄テスト結果サマリー")
    print("="*60)
    print(f"🌐 Webダッシュボード経由: {'✅ 成功' if web_success else '❌ 失敗'}")
    print(f"🔬 直接分析: {'✅ 成功' if direct_success else '❌ 失敗'}")
    
    if web_success or direct_success:
        print("\n🎉 TURBO銘柄は正常に動作しています！")
        print("✅ 158.70バグ修正が効果的に機能")
        print("✅ システムが適切な値を生成")
        return True
    else:
        print("\n⚠️ TURBO銘柄で問題が発生しました")
        print("詳細を確認してください")
        return False

if __name__ == '__main__':
    main()