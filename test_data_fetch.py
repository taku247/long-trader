"""
既存ファイルの動作確認用テストスクリプト
"""
import sys
import subprocess
import os

def test_ohlcv_fetch():
    """OHLCVデータ取得のテスト"""
    print("=" * 60)
    print("1. OHLCVデータ取得テスト")
    print("=" * 60)
    
    # HYPEトークンで15分足、7日分のみ（テスト用に短期間）
    cmd = [
        sys.executable,
        "ohlcv_by_claude.py",
        "--symbol", "HYPE",
        "--timeframe", "15m",
        "--days", "7"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("エラー:", result.stderr)
        
        # 生成されたファイルの確認
        expected_files = [
            "hype_15m_7days.csv",
            "hype_15m_7days_with_indicators.csv", 
            "hype_15m_7days_reduced_features.csv",
            "hype_removed_features.json"
        ]
        
        found_files = []
        for f in expected_files:
            if os.path.exists(f):
                found_files.append(f)
                size = os.path.getsize(f) / 1024  # KB
                print(f"✓ {f} ({size:.1f} KB)")
            else:
                print(f"✗ {f} が見つかりません")
        
        return len(found_files) == len(expected_files)
        
    except Exception as e:
        print(f"エラー発生: {e}")
        return False

def test_support_resistance():
    """サポレジ分析のテスト"""
    print("\n" + "=" * 60)
    print("2. サポート・レジスタンス分析テスト")
    print("=" * 60)
    
    # まずデータが存在するか確認
    if not os.path.exists("hype_15m_7days_with_indicators.csv"):
        print("前のステップでデータ生成に失敗しています")
        return False
    
    cmd = [
        sys.executable,
        "support_resistance_visualizer.py",
        "--symbol", "HYPE",
        "--timeframe", "15m",
        "--min-touches", "2"  # テスト用に低めに設定
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("エラー:", result.stderr)
        
        # 出力ファイルの確認
        output_file = "hype_15m_support_resistance_analysis.png"
        if os.path.exists(output_file):
            size = os.path.getsize(output_file) / 1024
            print(f"✓ {output_file} ({size:.1f} KB)")
            return True
        else:
            print(f"✗ {output_file} が生成されませんでした")
            return False
            
    except Exception as e:
        print(f"エラー発生: {e}")
        return False

def test_ml_analysis():
    """ML分析のテスト"""
    print("\n" + "=" * 60)
    print("3. 機械学習分析テスト")
    print("=" * 60)
    
    cmd = [
        sys.executable,
        "support_resistance_ml.py",
        "--symbol", "HYPE",
        "--timeframe", "15m",
        "--min-touches", "2"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("エラー:", result.stderr)
        
        # 出力ファイルの確認
        expected_outputs = [
            "hype_15m_sr_breakout_model.pkl",
            "hype_15m_sr_breakout_scaler.pkl",
            "hype_15m_sr_interactions.csv",
            "model_performance_comparison.png",
            "feature_importance.png"
        ]
        
        found = 0
        for f in expected_outputs:
            if os.path.exists(f):
                found += 1
                size = os.path.getsize(f) / 1024
                print(f"✓ {f} ({size:.1f} KB)")
        
        return found > 0
        
    except Exception as e:
        print(f"エラー発生: {e}")
        return False

def main():
    """メイン実行"""
    print("既存ファイルの動作確認を開始します...")
    print("（HYPEトークン、15分足、7日間でテスト）\n")
    
    results = {
        "OHLCVデータ取得": test_ohlcv_fetch(),
        "サポレジ分析": test_support_resistance(),
        "ML分析": test_ml_analysis()
    }
    
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✓ 成功" if result else "✗ 失敗"
        print(f"{name}: {status}")
    
    if all(results.values()):
        print("\n🎉 すべてのテストが成功しました！")
        print("実際の市場データとML分析が正常に動作しています。")
    else:
        print("\n⚠️ 一部のテストが失敗しました。")
        print("エラーメッセージを確認してください。")

if __name__ == "__main__":
    main()