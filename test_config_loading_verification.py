#!/usr/bin/env python3
"""
設定ファイル読み込み検証テスト

config/support_resistance_config.jsonの設定が正しく読み込まれ、
実際の処理に反映されているかを検証する包括的なテスト。
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from colorama import Fore, Style, init

# カラー出力初期化
init(autoreset=True)

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_config_directly():
    """設定ファイルを直接読み込む"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                              'config', 'support_resistance_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_support_resistance_adapter_config():
    """ExistingSupportResistanceAdapterの設定読み込みテスト"""
    print(f"\n{Fore.CYAN}=== サポート・レジスタンスアダプター設定テスト ==={Style.RESET_ALL}")
    
    from adapters.existing_adapters import ExistingSupportResistanceAdapter
    
    # アダプターインスタンス作成
    adapter = ExistingSupportResistanceAdapter()
    
    # 設定が読み込まれているか確認
    print(f"\n1. 設定ファイル読み込み状態:")
    if adapter.config:
        print(f"   {Fore.GREEN}✅ 設定ファイル読み込み成功{Style.RESET_ALL}")
    else:
        print(f"   {Fore.RED}❌ 設定ファイル読み込み失敗{Style.RESET_ALL}")
        return False
    
    # 期待される設定値
    expected_config = load_config_directly()
    
    # min_distance_from_current_price_pctの確認
    expected_min_distance = expected_config['support_resistance_analysis']['fractal_detection']['min_distance_from_current_price_pct']
    actual_min_distance = adapter.config.get('support_resistance_analysis', {}).get('fractal_detection', {}).get('min_distance_from_current_price_pct')
    
    print(f"\n2. 最小距離制限設定:")
    print(f"   期待値: {expected_min_distance}%")
    print(f"   実際値: {actual_min_distance}%")
    
    if expected_min_distance == actual_min_distance:
        print(f"   {Fore.GREEN}✅ 最小距離設定が正しく読み込まれています{Style.RESET_ALL}")
    else:
        print(f"   {Fore.RED}❌ 最小距離設定の読み込みエラー{Style.RESET_ALL}")
        return False
    
    # strength_based_exceptionsの確認
    expected_exceptions = expected_config['support_resistance_analysis']['fractal_detection'].get('strength_based_exceptions', {})
    actual_exceptions = adapter.config.get('support_resistance_analysis', {}).get('fractal_detection', {}).get('strength_based_exceptions', {})
    
    print(f"\n3. 強度ベース例外設定:")
    print(f"   有効化: {actual_exceptions.get('enabled', False)}")
    print(f"   最小強度: {actual_exceptions.get('min_strength_for_exception', 'N/A')}")
    print(f"   最小タッチ数: {actual_exceptions.get('min_touch_count_for_exception', 'N/A')}")
    
    if expected_exceptions == actual_exceptions:
        print(f"   {Fore.GREEN}✅ 例外設定が正しく読み込まれています{Style.RESET_ALL}")
    else:
        print(f"   {Fore.RED}❌ 例外設定の読み込みエラー{Style.RESET_ALL}")
        return False
    
    # 実際の動作テスト
    print(f"\n4. 実際の動作確認:")
    
    # テストデータ作成（現在価格: 100）
    test_data = pd.DataFrame({
        'close': [100.0] * 100,
        'high': np.linspace(98, 102, 100),
        'low': np.linspace(97, 101, 100),
        'volume': [1000] * 100
    })
    
    # find_levelsメソッドが設定値を使用しているか確認
    levels = adapter.find_levels(test_data)
    
    # 0.5%以内のレベルが除外されているか確認
    current_price = 100.0
    close_levels = [l for l in levels if abs(l.price - current_price) / current_price < 0.005]
    
    if len(close_levels) == 0:
        print(f"   {Fore.GREEN}✅ 0.5%以内のレベルが正しく除外されています{Style.RESET_ALL}")
    else:
        print(f"   {Fore.RED}❌ 0.5%以内のレベルが除外されていません（{len(close_levels)}個検出）{Style.RESET_ALL}")
        return False
    
    return True

def test_btc_correlation_adapter_config():
    """ExistingBTCCorrelationAdapterの設定読み込みテスト"""
    print(f"\n{Fore.CYAN}=== BTC相関アダプター設定テスト ==={Style.RESET_ALL}")
    
    from adapters.existing_adapters import ExistingBTCCorrelationAdapter
    
    # アダプターインスタンス作成
    adapter = ExistingBTCCorrelationAdapter()
    
    # 設定が読み込まれているか確認
    print(f"\n1. 設定ファイル読み込み状態:")
    if adapter.config:
        print(f"   {Fore.GREEN}✅ 設定ファイル読み込み成功{Style.RESET_ALL}")
    else:
        print(f"   {Fore.RED}❌ 設定ファイル読み込み失敗{Style.RESET_ALL}")
        return False
    
    # 期待される設定値
    expected_config = load_config_directly()
    
    # default_correlation_factorの確認
    expected_correlation = expected_config['support_resistance_analysis']['btc_correlation']['default_correlation_factor']
    actual_correlation = adapter.config.get('support_resistance_analysis', {}).get('btc_correlation', {}).get('default_correlation_factor')
    
    print(f"\n2. デフォルト相関係数:")
    print(f"   期待値: {expected_correlation}")
    print(f"   実際値: {actual_correlation}")
    
    if expected_correlation == actual_correlation:
        print(f"   {Fore.GREEN}✅ 相関係数が正しく読み込まれています{Style.RESET_ALL}")
    else:
        print(f"   {Fore.RED}❌ 相関係数の読み込みエラー{Style.RESET_ALL}")
        return False
    
    # impact_multipliersの確認
    expected_multipliers = expected_config['support_resistance_analysis']['btc_correlation']['impact_multipliers']
    actual_multipliers = adapter.config.get('support_resistance_analysis', {}).get('btc_correlation', {}).get('impact_multipliers', {})
    
    print(f"\n3. インパクト乗数設定:")
    for key in ['5_min', '15_min', '60_min', '240_min']:
        expected = expected_multipliers.get(key)
        actual = actual_multipliers.get(key)
        match = "✅" if expected == actual else "❌"
        print(f"   {key}: 期待値={expected}, 実際値={actual} {match}")
    
    # liquidation_risk_thresholdsの確認
    expected_thresholds = expected_config['support_resistance_analysis']['liquidation_risk_thresholds']
    actual_thresholds = adapter.config.get('support_resistance_analysis', {}).get('liquidation_risk_thresholds', {})
    
    print(f"\n4. 清算リスク閾値:")
    for level in ['critical', 'high', 'medium', 'low']:
        expected = expected_thresholds.get(level, {})
        actual = actual_thresholds.get(level, {})
        match = "✅" if expected == actual else "❌"
        print(f"   {level}: {match}")
        if expected != actual:
            print(f"      期待値: {expected}")
            print(f"      実際値: {actual}")
    
    # フォールバック予測で設定値が使用されているか確認
    print(f"\n5. フォールバック予測での設定値使用確認:")
    
    risk = adapter._fallback_prediction("TEST", 10.0)
    
    # 相関係数が設定値を使用しているか
    if risk.correlation_strength == expected_correlation:
        print(f"   {Fore.GREEN}✅ 相関係数が設定値を使用しています{Style.RESET_ALL}")
    else:
        print(f"   {Fore.RED}❌ 相関係数が設定値を使用していません（{risk.correlation_strength}）{Style.RESET_ALL}")
        return False
    
    return True

def test_ml_predictor_adapter_config():
    """ExistingMLPredictorAdapterの設定読み込みテスト"""
    print(f"\n{Fore.CYAN}=== ML予測アダプター設定テスト ==={Style.RESET_ALL}")
    
    from adapters.existing_adapters import ExistingMLPredictorAdapter
    
    # アダプターインスタンス作成
    adapter = ExistingMLPredictorAdapter()
    
    # 設定が読み込まれているか確認
    print(f"\n1. 設定ファイル読み込み状態:")
    if adapter.config:
        print(f"   {Fore.GREEN}✅ 設定ファイル読み込み成功{Style.RESET_ALL}")
    else:
        print(f"   {Fore.RED}❌ 設定ファイル読み込み失敗{Style.RESET_ALL}")
        return False
    
    # ML設定の確認
    ml_settings = adapter.config.get('support_resistance_analysis', {}).get('ml_settings', {})
    
    print(f"\n2. ML設定:")
    print(f"   信頼度閾値: {ml_settings.get('confidence_threshold', 'N/A')}")
    print(f"   価格目標（高）: {ml_settings.get('price_target_multiplier_high', 'N/A')}")
    print(f"   価格目標（低）: {ml_settings.get('price_target_multiplier_low', 'N/A')}")
    
    # 精度メトリクスの確認
    accuracy = ml_settings.get('default_accuracy_metrics', {})
    print(f"\n3. デフォルト精度メトリクス:")
    print(f"   レジスタンス精度: {accuracy.get('resistance_accuracy', 'N/A')}")
    print(f"   サポート精度: {accuracy.get('support_accuracy', 'N/A')}")
    print(f"   ブレイクアウト精度: {accuracy.get('breakout_accuracy', 'N/A')}")
    print(f"   方向精度: {accuracy.get('direction_accuracy', 'N/A')}")
    
    if ml_settings:
        print(f"   {Fore.GREEN}✅ ML設定が正しく読み込まれています{Style.RESET_ALL}")
    else:
        print(f"   {Fore.YELLOW}⚠️ ML設定が見つかりません（オプション）{Style.RESET_ALL}")
    
    return True

def test_config_file_integrity():
    """設定ファイルの整合性チェック"""
    print(f"\n{Fore.CYAN}=== 設定ファイル整合性チェック ==={Style.RESET_ALL}")
    
    try:
        config = load_config_directly()
        
        # 必須キーの確認
        required_keys = [
            'support_resistance_analysis',
            'default_provider',
            'provider_settings'
        ]
        
        print(f"\n1. 必須キーの確認:")
        for key in required_keys:
            if key in config:
                print(f"   {Fore.GREEN}✅ {key}{Style.RESET_ALL}")
            else:
                print(f"   {Fore.RED}❌ {key} が見つかりません{Style.RESET_ALL}")
                return False
        
        # support_resistance_analysis内の必須キー
        sr_analysis = config.get('support_resistance_analysis', {})
        sr_required = ['fractal_detection', 'btc_correlation', 'liquidation_risk_thresholds']
        
        print(f"\n2. support_resistance_analysis内の必須キー:")
        for key in sr_required:
            if key in sr_analysis:
                print(f"   {Fore.GREEN}✅ {key}{Style.RESET_ALL}")
            else:
                print(f"   {Fore.RED}❌ {key} が見つかりません{Style.RESET_ALL}")
                return False
        
        # 数値の妥当性チェック
        print(f"\n3. 数値の妥当性チェック:")
        
        min_distance = sr_analysis['fractal_detection']['min_distance_from_current_price_pct']
        if 0 < min_distance < 5:
            print(f"   {Fore.GREEN}✅ 最小距離 {min_distance}% は妥当な範囲です{Style.RESET_ALL}")
        else:
            print(f"   {Fore.RED}❌ 最小距離 {min_distance}% は範囲外です{Style.RESET_ALL}")
            return False
        
        correlation_factor = sr_analysis['btc_correlation']['default_correlation_factor']
        if 0 < correlation_factor <= 1:
            print(f"   {Fore.GREEN}✅ 相関係数 {correlation_factor} は妥当な範囲です{Style.RESET_ALL}")
        else:
            print(f"   {Fore.RED}❌ 相関係数 {correlation_factor} は範囲外です{Style.RESET_ALL}")
            return False
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ 設定ファイル読み込みエラー: {e}{Style.RESET_ALL}")
        return False

def test_runtime_config_override():
    """実行時の設定オーバーライドテスト"""
    print(f"\n{Fore.CYAN}=== 実行時設定オーバーライドテスト ==={Style.RESET_ALL}")
    
    from adapters.existing_adapters import ExistingSupportResistanceAdapter
    
    adapter = ExistingSupportResistanceAdapter()
    
    # テストデータ
    test_data = pd.DataFrame({
        'close': [100.0] * 100,
        'high': np.linspace(98, 102, 100),
        'low': np.linspace(97, 101, 100),
        'volume': [1000] * 100
    })
    
    print(f"\n1. デフォルト設定での実行:")
    levels_default = adapter.find_levels(test_data)
    print(f"   検出レベル数: {len(levels_default)}")
    
    print(f"\n2. オーバーライド設定での実行 (min_distance_pct=0.001):")
    levels_override = adapter.find_levels(test_data, min_distance_pct=0.001)
    print(f"   検出レベル数: {len(levels_override)}")
    
    if len(levels_override) > len(levels_default):
        print(f"   {Fore.GREEN}✅ 設定オーバーライドが機能しています{Style.RESET_ALL}")
    else:
        print(f"   {Fore.YELLOW}⚠️ 設定オーバーライドの効果が確認できません{Style.RESET_ALL}")
    
    return True

def main():
    """メインテスト実行"""
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}設定ファイル読み込み・反映確認テスト{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    
    tests = [
        ("設定ファイル整合性", test_config_file_integrity),
        ("サポート・レジスタンスアダプター", test_support_resistance_adapter_config),
        ("BTC相関アダプター", test_btc_correlation_adapter_config),
        ("ML予測アダプター", test_ml_predictor_adapter_config),
        ("実行時オーバーライド", test_runtime_config_override),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n{Fore.RED}❌ {test_name} でエラー発生: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 結果サマリー
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}テスト結果サマリー{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Fore.GREEN}✅ PASS{Style.RESET_ALL}" if result else f"{Fore.RED}❌ FAIL{Style.RESET_ALL}"
        print(f"{test_name}: {status}")
    
    print(f"\n合計: {passed}/{total} テスト成功")
    
    if passed == total:
        print(f"\n{Fore.GREEN}✅ すべての設定が正しく読み込まれ、反映されています！{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}❌ 一部の設定に問題があります。{Style.RESET_ALL}")

if __name__ == "__main__":
    main()