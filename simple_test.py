"""
シンプルな動作確認
"""
from hyperliquid.info import Info
from hyperliquid.utils import constants
import pandas as pd
import numpy as np

def test_hyperliquid_connection():
    """Hyperliquid接続テスト"""
    print("Hyperliquid接続テスト...")
    
    try:
        # Hyperliquid APIインスタンス作成
        info = Info(constants.MAINNET_API_URL)
        
        # メタ情報を取得してみる
        meta_info = info.all_mids()
        
        print(f"✓ 接続成功！")
        print(f"  利用可能な通貨ペア数: {len(meta_info)}")
        
        # HYPEが存在するか確認
        if 'HYPE' in meta_info:
            print(f"  HYPE現在価格: ${meta_info['HYPE']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 接続エラー: {e}")
        return False

def test_data_fetch():
    """小規模データ取得テスト"""
    print("\n小規模データ取得テスト（HYPE 1時間足 24時間）...")
    
    try:
        info = Info(constants.MAINNET_API_URL)
        
        # 1日分のデータを取得
        ohlcv_data = info.candles_snapshot(
            "HYPE",
            "1h",
            int((pd.Timestamp.now() - pd.Timedelta(days=1)).timestamp() * 1000),
            int(pd.Timestamp.now().timestamp() * 1000)
        )
        
        if ohlcv_data and len(ohlcv_data) > 0:
            print(f"✓ データ取得成功！")
            print(f"  取得データ数: {len(ohlcv_data)}")
            print(f"  最新価格: ${ohlcv_data[-1]['c']}")
            
            # データフレームに変換
            df = pd.DataFrame(ohlcv_data)
            print(f"  カラム: {df.columns.tolist()}")
            
            return True
        else:
            print("✗ データが取得できませんでした")
            return False
            
    except Exception as e:
        print(f"✗ データ取得エラー: {e}")
        return False

def main():
    """メインテスト"""
    print("=" * 60)
    print("Hyperliquid動作確認")
    print("=" * 60)
    
    # 接続テスト
    if test_hyperliquid_connection():
        # データ取得テスト
        if test_data_fetch():
            print("\n✅ 基本動作確認OK！")
            print("→ 実際のデータ取得・分析に進むことができます。")
        else:
            print("\n⚠️ データ取得に問題があります")
    else:
        print("\n❌ Hyperliquid APIへの接続に失敗しました")
        print("インターネット接続を確認してください")

if __name__ == "__main__":
    main()