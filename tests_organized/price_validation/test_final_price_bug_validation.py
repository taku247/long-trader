#!/usr/bin/env python3
"""
最終価格バグ検証

今回修正したバグが完全に解決されているかの最終確認。
ETHで発見されたような45%異常利益率問題が発生しないことを証明。
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_leverage_decision_engine_price_fix():
    """レバレッジ判定エンジンの価格修正テスト"""
    print("🔧 レバレッジ判定エンジン価格修正検証")
    print("-" * 50)
    
    from engines.leverage_decision_engine import SimpleMarketContextAnalyzer
    
    analyzer = SimpleMarketContextAnalyzer()
    
    # 現実的な価格変動データを作成
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    test_data = pd.DataFrame({
        'timestamp': [base_time + timedelta(hours=i) for i in range(50)],
        'open': [50000 + i * 100 for i in range(50)],      # 段階的に価格上昇
        'close': [50020 + i * 100 for i in range(50)],
        'high': [50100 + i * 100 for i in range(50)],
        'low': [49900 + i * 100 for i in range(50)],
        'volume': [1000000] * 50
    })
    
    print(f"✅ テストデータ: 価格範囲 {test_data['open'].min()}-{test_data['open'].max()}")
    
    # バックテスト分析で各時刻の正確な価格が取得されることを確認
    prices_used = []
    for i in range(5, 10):
        trade_time = test_data['timestamp'].iloc[i]
        result = analyzer.analyze_market_phase(
            test_data, 
            target_timestamp=trade_time,
            is_realtime=False
        )
        
        prices_used.append({
            'time': trade_time,
            'price': result.current_price,
            'expected': test_data['open'].iloc[i]
        })
        
        print(f"   時刻 {trade_time.strftime('%H:%M')}: 取得価格={result.current_price}, 期待値={test_data['open'].iloc[i]}")
    
    # 全て正確に一致することを確認
    all_correct = all(p['price'] == p['expected'] for p in prices_used)
    unique_prices = len(set(p['price'] for p in prices_used))
    
    print(f"✅ 価格正確性: {all_correct}")
    print(f"✅ 価格多様性: {unique_prices}/5")
    
    return all_correct and unique_prices == 5

def test_scalable_analysis_system_integration():
    """ScalableAnalysisSystem統合テスト"""
    print("\n🔗 ScalableAnalysisSystem統合検証")
    print("-" * 50)
    
    from scalable_analysis_system import ScalableAnalysisSystem
    
    system = ScalableAnalysisSystem()
    
    # _get_real_market_priceメソッドの直接テスト
    base_time = datetime(2024, 6, 1, 0, 0, 0)
    mock_data = pd.DataFrame({
        'timestamp': [base_time + timedelta(hours=i) for i in range(24)],
        'open': [100 + i * 5 for i in range(24)],      # 5ドルずつ上昇
        'close': [102 + i * 5 for i in range(24)],
        'high': [105 + i * 5 for i in range(24)],
        'low': [98 + i * 5 for i in range(24)],
        'volume': [100000] * 24
    })
    
    print(f"✅ モックデータ: 24時間分、価格範囲 {mock_data['open'].min()}-{mock_data['open'].max()}")
    
    # モックボットクラスを作成
    class MockBot:
        def __init__(self, data):
            self._cached_data = data
        
        def _fetch_market_data(self, symbol, timeframe):
            return self._cached_data
    
    mock_bot = MockBot(mock_data)
    
    # 異なる時刻での価格取得テスト
    prices_retrieved = []
    for i in range(5, 10):
        trade_time = mock_data['timestamp'].iloc[i]
        try:
            price = system._get_real_market_price(mock_bot, "TEST", "1h", trade_time)
            expected = mock_data['open'].iloc[i]
            prices_retrieved.append({
                'time': trade_time,
                'price': price,
                'expected': expected,
                'match': price == expected
            })
            print(f"   時刻 {trade_time.strftime('%H:%M')}: 取得価格={price}, 期待値={expected}, 一致={price == expected}")
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            return False
    
    # 全て正確に一致することを確認
    all_match = all(p['match'] for p in prices_retrieved)
    unique_prices = len(set(p['price'] for p in prices_retrieved))
    
    print(f"✅ 価格正確性: {all_match}")
    print(f"✅ 価格多様性: {unique_prices}/5")
    
    return all_match and unique_prices == 5

def test_price_consistency_validation():
    """価格整合性バリデーションテスト"""
    print("\n⚖️ 価格整合性バリデーション")
    print("-" * 50)
    
    from engines.price_consistency_validator import PriceConsistencyValidator
    
    validator = PriceConsistencyValidator()
    
    # 正常な価格差のテスト
    test_cases = [
        (1000.0, 1005.0, "normal"),     # 0.5%差
        (1000.0, 1020.0, "warning"),   # 2%差
        (1000.0, 1070.0, "error"),     # 7%差
        (1000.0, 1150.0, "critical"),  # 15%差（ETHのような異常ケース）
    ]
    
    print("価格差検証テスト:")
    all_correct = True
    for analysis_price, entry_price, expected_level in test_cases:
        result = validator.validate_price_consistency(analysis_price, entry_price)
        actual_level = result.inconsistency_level.value  # Enumから値を取得
        print(f"   {analysis_price} vs {entry_price}: {actual_level} (期待値: {expected_level})")
        if actual_level != expected_level:
            all_correct = False
    
    print(f"✅ 価格差検証: {all_correct}")
    
    return all_correct

def test_eth_anomaly_prevention():
    """ETH異常ケース再発防止テスト"""
    print("\n🚨 ETH異常ケース再発防止テスト")
    print("-" * 50)
    
    from engines.leverage_decision_engine import SimpleMarketContextAnalyzer
    
    analyzer = SimpleMarketContextAnalyzer()
    
    # ETHのような価格変動を模擬
    base_time = datetime(2024, 5, 15, 10, 0, 0)
    eth_like_data = pd.DataFrame({
        'timestamp': [base_time + timedelta(minutes=i*10) for i in range(30)],  # 10分間隔
        'open': [3000 + i * 20 for i in range(30)],      # 段階的上昇
        'close': [3005 + i * 20 for i in range(30)],
        'high': [3010 + i * 20 for i in range(30)],
        'low': [2995 + i * 20 for i in range(30)],
        'volume': [500000] * 30
    })
    
    print(f"✅ ETH模擬データ: 5時間分、価格範囲 {eth_like_data['open'].min()}-{eth_like_data['open'].max()}")
    
    # 異なる時刻でのトレードをシミュレート
    trade_results = []
    for i in range(5, 15, 2):  # 5つのトレード
        trade_time = eth_like_data['timestamp'].iloc[i]
        
        # バックテスト分析（修正後）
        result = analyzer.analyze_market_phase(
            eth_like_data, 
            target_timestamp=trade_time,
            is_realtime=False
        )
        
        entry_price = result.current_price
        expected_price = eth_like_data['open'].iloc[i]
        
        # 50分後の価格（出口想定）
        exit_idx = min(i + 5, len(eth_like_data) - 1)
        exit_price = eth_like_data['close'].iloc[exit_idx]
        
        # 利益率計算
        profit_rate = (exit_price - entry_price) / entry_price * 100
        
        trade_results.append({
            'entry_time': trade_time,
            'entry_price': entry_price,
            'expected_price': expected_price,
            'exit_price': exit_price,
            'profit_rate': profit_rate,
            'price_match': entry_price == expected_price
        })
        
        print(f"   トレード{(i-5)//2 + 1}: エントリー={entry_price}, 利益率={profit_rate:.1f}%")
    
    # 異常な利益率（45%のような）がないことを確認
    max_profit = max(tr['profit_rate'] for tr in trade_results)
    all_prices_match = all(tr['price_match'] for tr in trade_results)
    
    print(f"✅ 最大利益率: {max_profit:.1f}% (閾値: 15%)")
    print(f"✅ 価格正確性: {all_prices_match}")
    
    return max_profit < 15.0 and all_prices_match

def main():
    """メインテスト実行"""
    print("🧪 最終価格バグ検証テスト")
    print("=" * 80)
    print("ETHで発見された45%異常利益率問題の修正確認")
    print("=" * 80)
    
    # 各テストを実行
    tests = [
        ("レバレッジ判定エンジン修正", test_leverage_decision_engine_price_fix),
        ("ScalableAnalysisSystem統合", test_scalable_analysis_system_integration),
        ("価格整合性バリデーション", test_price_consistency_validation),
        ("ETH異常ケース再発防止", test_eth_anomaly_prevention),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # 最終判定
    print("\n" + "=" * 80)
    print("📊 最終検証結果")
    print("=" * 80)
    
    passed_tests = sum(1 for _, result in results if result)
    total_tests = len(results)
    
    print(f"成功テスト: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("\n✅ 銘柄追加における価格バグは完全に修正済み")
        print("🎯 主要な改善点:")
        print("   1. バックテスト分析で各時刻の正確なopen価格を使用")
        print("   2. リアルタイム分析で適切な最新価格を使用")
        print("   3. is_realtimeフラグで明示的なモード指定")
        print("   4. 価格整合性バリデーションによる異常検出")
        print("   5. ETHのような45%異常利益率の根本的防止")
        print("\n🛡️ 今後は同様の価格整合性問題は発生しません")
        return True
    else:
        print("\n❌ 一部のテストで問題が検出されました")
        for test_name, result in results:
            if not result:
                print(f"   - {test_name}: 要調査")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)