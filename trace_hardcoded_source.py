#!/usr/bin/env python3
"""
ハードコード値（1000.0）の発生源をトレースするスクリプト

目的：
1. 1000.0が生成される具体的なコード箇所を特定
2. どの関数・クラスが原因かを特定
3. 修正すべき箇所を明確化
"""

import sys
import os
import pandas as pd
import pickle
import gzip
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def analyze_specific_problematic_file():
    """問題のあるファイルの詳細分析"""
    print("🔍 問題ファイルの詳細分析")
    print("=" * 50)
    
    # 分析で特定された問題ファイルを確認
    problematic_files = [
        "large_scale_analysis/compressed/TOKEN001_1m_Config_19.pkl.gz",
        "large_scale_analysis/compressed/TOKEN006_1m_Config_17.pkl.gz",
        "large_scale_analysis/compressed/TOKEN010_15m_Config_01.pkl.gz"
    ]
    
    for file_path in problematic_files:
        if os.path.exists(file_path):
            print(f"\n📁 分析対象: {file_path}")
            
            try:
                with gzip.open(file_path, 'rb') as f:
                    trades_data = pickle.load(f)
                
                if isinstance(trades_data, list):
                    df = pd.DataFrame(trades_data)
                elif isinstance(trades_data, dict):
                    df = pd.DataFrame(trades_data)
                else:
                    df = trades_data
                
                print(f"   データ型: {type(trades_data)}")
                print(f"   レコード数: {len(df)}")
                print(f"   カラム数: {len(df.columns)}")
                print(f"   カラム: {list(df.columns)}")
                
                # エントリー価格の分析
                if 'entry_price' in df.columns:
                    entry_prices = df['entry_price']
                    print(f"   エントリー価格:")
                    print(f"     ユニーク値: {entry_prices.unique()}")
                    print(f"     平均: {entry_prices.mean()}")
                    print(f"     標準偏差: {entry_prices.std()}")
                    print(f"     最初の10件: {entry_prices.head(10).tolist()}")
                
                # TP/SL価格の分析
                for col in ['take_profit_price', 'stop_loss_price']:
                    if col in df.columns:
                        values = df[col]
                        print(f"   {col}:")
                        print(f"     ユニーク値: {values.unique()}")
                        print(f"     平均: {values.mean()}")
                        print(f"     最初の5件: {values.head(5).tolist()}")
                
                # レバレッジの分析
                if 'leverage' in df.columns:
                    leverage = df['leverage']
                    print(f"   レバレッジ:")
                    print(f"     ユニーク値: {leverage.unique()}")
                    print(f"     平均: {leverage.mean()}")
                
                # その他の重要なフィールド
                for col in ['timestamp', 'pnl', 'confidence']:
                    if col in df.columns:
                        values = df[col]
                        if col == 'timestamp':
                            print(f"   {col}: {values.head(3).tolist()}")
                        else:
                            print(f"   {col}: unique={len(values.unique())}, mean={values.mean():.4f}")
                        
            except Exception as e:
                print(f"   ❌ エラー: {e}")
        else:
            print(f"   ❌ ファイルが存在しません: {file_path}")

def trace_generation_source():
    """1000.0生成源のトレース"""
    print("\n🔍 1000.0生成源のコードトレース")
    print("=" * 50)
    
    # 重要なソースファイルをグループして検索
    source_files = [
        # メインの分析システム
        "scalable_analysis_system.py",
        # バックテストエンジン
        "engines/high_leverage_bot_orchestrator.py",
        # 設定生成
        "auto_symbol_training.py",
        # 価格計算
        "hyperliquid_validator.py",
        # APIクライアント
        "hyperliquid_api_client.py"
    ]
    
    search_patterns = [
        "1000.0", "1000", "entry_price", "take_profit_price", "stop_loss_price",
        "current_price = ", "entry =", "tp =", "sl =", "fallback", "default"
    ]
    
    for file_path in source_files:
        if os.path.exists(file_path):
            print(f"\n📁 検索対象: {file_path}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                found_patterns = []
                for i, line in enumerate(lines, 1):
                    for pattern in search_patterns:
                        if pattern in line and not line.strip().startswith('#'):
                            found_patterns.append(f"   行{i}: {line.strip()}")
                
                if found_patterns:
                    print("   🎯 発見されたパターン:")
                    for pattern in found_patterns[:10]:  # 最大10件表示
                        print(pattern)
                else:
                    print("   ✅ 疑わしいパターンなし")
                    
            except Exception as e:
                print(f"   ❌ ファイル読み込みエラー: {e}")
        else:
            print(f"   ❌ ファイルが存在しません: {file_path}")

def check_configuration_files():
    """設定ファイルの確認"""
    print("\n🔍 設定ファイルの確認")
    print("=" * 50)
    
    config_files = [
        "config.json",
        "exchange_config.json",
        "settings.json",
        "bot_config.json"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"\n📁 設定ファイル: {config_file}")
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "1000" in content or "100.0" in content:
                        print("   🚨 ハードコード値らしき数値を発見!")
                        print(f"   内容: {content[:500]}...")
                    else:
                        print("   ✅ ハードコード値なし")
            except Exception as e:
                print(f"   ❌ 読み込みエラー: {e}")
        else:
            print(f"   ❓ {config_file} は存在しません")

def check_test_data_generation():
    """テストデータ生成の確認"""
    print("\n🔍 テストデータ生成関数の確認")
    print("=" * 50)
    
    # TestHighLeverageBotOrchestratorを検索
    patterns_to_find = [
        "TestHighLeverageBotOrchestrator",
        "_generate_sample_data",
        "sample_trades",
        "test_data",
        "mock_data",
        "dummy_data"
    ]
    
    python_files = []
    for ext in ['py']:
        python_files.extend(Path('.').rglob(f'*.{ext}'))
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            found_patterns = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                for pattern in patterns_to_find:
                    if pattern in line:
                        found_patterns.append(f"   行{i}: {line.strip()}")
            
            if found_patterns:
                print(f"\n📁 {file_path}")
                for pattern in found_patterns[:5]:  # 最大5件表示
                    print(pattern)
                    
        except Exception:
            continue

def main():
    """メイン実行関数"""
    print("🔍 ハードコード値（1000.0）発生源トレース")
    print("=" * 60)
    
    # 1. 問題ファイルの詳細分析
    analyze_specific_problematic_file()
    
    # 2. ソースコードの検索
    trace_generation_source()
    
    # 3. 設定ファイルの確認
    check_configuration_files()
    
    # 4. テストデータ生成の確認
    check_test_data_generation()
    
    print("\n" + "=" * 60)
    print("✅ トレース完了")
    print("=" * 60)

if __name__ == '__main__':
    main()