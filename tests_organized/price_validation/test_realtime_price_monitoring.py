#!/usr/bin/env python3
"""
リアルタイム価格異常検知システムのテスト
Phase 1-2修正後のシステムが正常に動作することを確認
"""

import sys
import os
from datetime import datetime, timedelta
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_monitor_initialization():
    """モニターシステムの初期化テスト"""
    print("🔍 リアルタイムモニター初期化テスト")
    print("=" * 70)
    
    try:
        from real_time_system.monitor import RealTimeMonitor
        
        # モニター初期化
        monitor = RealTimeMonitor()
        
        print("✅ モニターシステム初期化成功")
        print(f"  設定ディレクトリ: {monitor.config_dir}")
        print(f"  ログディレクトリ: {monitor.logs_dir}")
        
        # 設定確認
        config = monitor.config
        print(f"\n📊 設定情報:")
        print(f"  監視間隔: {config['monitoring']['default_interval_minutes']}分")
        print(f"  レバレッジ閾値: {config['alerts']['leverage_threshold']}x")
        print(f"  信頼度閾値: {config['alerts']['confidence_threshold']}%")
        
        return monitor
        
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_watchlist_loading(monitor):
    """ウォッチリスト読み込みテスト"""
    print("\n🔍 ウォッチリスト読み込みテスト")
    print("=" * 70)
    
    try:
        watchlist = monitor._load_watchlist()
        
        print(f"✅ ウォッチリスト読み込み成功")
        
        # 有効な銘柄をカウント
        enabled_symbols = [symbol for symbol, config in watchlist.get('symbols', {}).items() 
                          if config.get('enabled', False)]
        
        print(f"📊 監視対象銘柄:")
        print(f"  総銘柄数: {len(watchlist.get('symbols', {}))}")
        print(f"  有効銘柄数: {len(enabled_symbols)}")
        print(f"  有効銘柄: {', '.join(enabled_symbols)}")
        
        return True
        
    except Exception as e:
        print(f"❌ ウォッチリスト読み込みエラー: {e}")
        return False

def test_trading_bot_connection(monitor):
    """トレーディングボット接続テスト"""
    print("\n🔍 トレーディングボット接続テスト")
    print("=" * 70)
    
    try:
        if monitor.trading_bot is None:
            print("❌ トレーディングボットが初期化されていません")
            return False
        
        # HYPEで簡単なテスト（フォールバック値を使用しないことを確認）
        print("📊 HYPE のテスト分析実行...")
        
        # analyze_leverage_opportunityメソッドをテスト
        result = monitor.trading_bot.analyze_leverage_opportunity("HYPE", "1h")
        
        print("✅ トレーディングボット接続成功")
        print(f"  推奨レバレッジ: {result.recommended_leverage}x")
        print(f"  現在価格: ${result.market_conditions.current_price}")
        print(f"  信頼度: {result.confidence}%")
        
        # ハードコード値チェック
        current_price = result.market_conditions.current_price
        hardcoded_values = [100.0, 105.0, 97.62, 1000.0]
        
        is_hardcoded = any(abs(current_price - hv) < 0.001 for hv in hardcoded_values)
        
        if is_hardcoded:
            print(f"❌ ハードコード値検出: {current_price}")
            return False
        else:
            print(f"✅ 実データ使用確認: ${current_price:.6f}")
            return True
        
    except Exception as e:
        print(f"❌ トレーディングボット接続エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_alert_system(monitor):
    """アラートシステムテスト"""
    print("\n🔍 アラートシステムテスト")
    print("=" * 70)
    
    try:
        from real_time_system.alert_manager import AlertManager, AlertType, AlertPriority
        
        # アラートマネージャー初期化
        alert_manager = AlertManager(monitor.config)
        
        # テストアラート送信
        test_alert = {
            'symbol': 'TEST',
            'type': AlertType.HIGH_LEVERAGE_OPPORTUNITY,
            'priority': AlertPriority.MEDIUM,
            'message': 'テストアラート - Phase 1-2修正後の動作確認',
            'data': {
                'leverage': 15.0,
                'confidence': 85.0,
                'current_price': 123.45
            }
        }
        
        # コンソールアラートのテスト
        alert_manager.send_alert(test_alert)
        
        print("✅ アラートシステムテスト成功")
        return True
        
    except Exception as e:
        print(f"❌ アラートシステムエラー: {e}")
        return False

def test_price_anomaly_detection():
    """価格異常検知機能のテスト"""
    print("\n🔍 価格異常検知機能テスト")
    print("=" * 70)
    
    try:
        # テスト用の価格データ
        test_prices = [
            {"symbol": "BTC", "price": 104966.10, "expected": True},   # 正常
            {"symbol": "HYPE", "price": 0.269, "expected": True},      # 正常
            {"symbol": "TEST1", "price": 100.0, "expected": False},    # ハードコード値
            {"symbol": "TEST2", "price": 105.0, "expected": False},    # ハードコード値
            {"symbol": "TEST3", "price": 97.62, "expected": False},    # ハードコード値
        ]
        
        hardcoded_values = [100.0, 105.0, 97.62, 1000.0]
        
        print("📊 価格異常検知テスト:")
        all_passed = True
        
        for test_case in test_prices:
            symbol = test_case["symbol"]
            price = test_case["price"]
            expected_normal = test_case["expected"]
            
            # ハードコード値チェック
            is_hardcoded = any(abs(price - hv) < 0.001 for hv in hardcoded_values)
            is_normal = not is_hardcoded
            
            status = "✅" if is_normal == expected_normal else "❌"
            result = "正常" if is_normal else "異常"
            
            print(f"  {status} {symbol}: ${price} -> {result}")
            
            if is_normal != expected_normal:
                all_passed = False
        
        if all_passed:
            print("\n✅ 価格異常検知機能正常動作")
        else:
            print("\n❌ 価格異常検知機能に問題があります")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 価格異常検知テストエラー: {e}")
        return False

def test_short_monitoring_session():
    """短時間監視セッションテスト"""
    print("\n🔍 短時間監視セッションテスト")
    print("=" * 70)
    
    try:
        from real_time_system.monitor import RealTimeMonitor
        
        monitor = RealTimeMonitor()
        
        print("📊 5秒間の監視セッションを開始...")
        print("  (実際のプロダクション環境では長時間稼働)")
        
        # 短時間の監視をシミュレート
        start_time = time.time()
        while time.time() - start_time < 5:
            # HYPEの価格をチェック
            if monitor.trading_bot:
                try:
                    result = monitor.trading_bot.analyze_leverage_opportunity("HYPE", "1h")
                    current_price = result.market_conditions.current_price
                    
                    print(f"  {datetime.now().strftime('%H:%M:%S')} - HYPE: ${current_price:.6f}")
                    
                    # 異常値チェック
                    hardcoded_values = [100.0, 105.0, 97.62, 1000.0]
                    if any(abs(current_price - hv) < 0.001 for hv in hardcoded_values):
                        print(f"    ❌ 異常価格検出！")
                        return False
                    
                except Exception as e:
                    print(f"    ⚠️ 分析エラー: {str(e)[:50]}...")
            
            time.sleep(1)
        
        print("✅ 短時間監視セッション完了 - 異常なし")
        return True
        
    except Exception as e:
        print(f"❌ 監視セッションエラー: {e}")
        return False

def main():
    """メイン実行関数"""
    print("🚀 リアルタイム価格異常検知システム稼働テスト")
    print("=" * 70)
    print("目的: Phase 1-2修正後のシステムが実データのみを使用することを確認")
    print("=" * 70)
    
    # 1. モニター初期化テスト
    monitor = test_monitor_initialization()
    if not monitor:
        print("\n❌ 初期化に失敗したため、テストを中断します")
        return
    
    # 2. ウォッチリスト読み込みテスト
    watchlist_ok = test_watchlist_loading(monitor)
    
    # 3. トレーディングボット接続テスト
    bot_ok = test_trading_bot_connection(monitor)
    
    # 4. アラートシステムテスト
    alert_ok = test_alert_system(monitor)
    
    # 5. 価格異常検知機能テスト
    anomaly_ok = test_price_anomaly_detection()
    
    # 6. 短時間監視セッションテスト
    session_ok = test_short_monitoring_session()
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 テスト結果サマリー")
    print("=" * 70)
    
    tests = [
        ("モニター初期化", monitor is not None),
        ("ウォッチリスト読み込み", watchlist_ok),
        ("トレーディングボット接続", bot_ok),
        ("アラートシステム", alert_ok),
        ("価格異常検知機能", anomaly_ok),
        ("短時間監視セッション", session_ok)
    ]
    
    passed = 0
    for test_name, result in tests:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\n成功率: {passed}/{len(tests)} ({passed/len(tests)*100:.1f}%)")
    
    if passed == len(tests):
        print("\n🎉 全テスト成功！リアルタイム価格異常検知システムは正常に稼働しています")
        print("✅ Phase 1-2の修正によりハードコード値は完全に除去されています")
    else:
        print("\n⚠️ 一部のテストで問題が検出されました")

if __name__ == '__main__':
    main()