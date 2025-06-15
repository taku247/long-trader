#!/usr/bin/env python3
"""
VINEがHyperliquidで実際に取引可能な銘柄かどうかを検証
"""

import requests
import time
from hyperliquid.info import Info
from hyperliquid.utils import constants

def check_vine_with_api():
    """Hyperliquid APIでVINEの存在を確認"""
    
    try:
        print("=== Hyperliquid API直接確認 ===")
        
        # APIクライアント初期化
        info = Info(constants.MAINNET_API_URL)
        
        # タイムアウト設定で試行
        print("1. メタ情報取得を試行中...")
        
        try:
            meta = info.meta()
            if meta:
                universe = meta.get('universe', [])
                print(f"取得された銘柄数: {len(universe)}")
                
                # VINEを検索
                vine_found = False
                for asset in universe:
                    if asset.get('name') == 'VINE':
                        vine_found = True
                        print(f"✅ VINEが見つかりました: {asset}")
                        break
                
                if not vine_found:
                    print("❌ VINEは取引可能銘柄に含まれていません")
                    
                    # 類似する銘柄を検索
                    vine_like = [asset for asset in universe if 'VINE' in asset.get('name', '').upper()]
                    if vine_like:
                        print(f"類似銘柄: {vine_like}")
                    
                    # 最初の10銘柄を表示
                    print("\n最初の10銘柄:")
                    for i, asset in enumerate(universe[:10]):
                        print(f"  {i+1}. {asset.get('name')}: {asset.get('tradable', False)}")
                        
            else:
                print("メタ情報の取得に失敗")
                
        except Exception as e:
            print(f"メタ情報取得エラー: {e}")
        
        # 価格情報でも確認
        print("\n2. 価格情報での確認...")
        try:
            all_mids = info.all_mids()
            print(f"価格情報のある銘柄数: {len(all_mids)}")
            
            vine_price = all_mids.get('VINE')
            if vine_price is not None:
                print(f"✅ VINE価格: ${vine_price}")
            else:
                print("❌ VINEの価格情報が見つかりません")
                
                # 価格情報がある最初の10銘柄
                print("\n価格情報のある最初の10銘柄:")
                for i, (symbol, price) in enumerate(list(all_mids.items())[:10]):
                    print(f"  {i+1}. {symbol}: ${price}")
                    
        except Exception as e:
            print(f"価格情報取得エラー: {e}")
            
    except Exception as e:
        print(f"API接続エラー: {e}")

def check_vine_with_timeout():
    """タイムアウト制御でVINE確認"""
    
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("API呼び出しがタイムアウトしました")
    
    try:
        # 30秒のタイムアウト設定
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        check_vine_with_api()
        
        signal.alarm(0)  # タイムアウトをクリア
        
    except TimeoutError:
        print("⏰ API呼び出しがタイムアウトしました（30秒）")
        print("💡 VINEが実際に取引可能かどうかは不明です")
    except Exception as e:
        print(f"エラー: {e}")

def check_known_symbols():
    """既知の銘柄リストでVINEを確認"""
    
    print("\n=== 既知銘柄リストでの確認 ===")
    
    # よく知られているPerps銘柄
    known_symbols = [
        'BTC', 'ETH', 'SOL', 'AVAX', 'DOGE', 'LINK', 'UNI', 'AAVE',
        'MATIC', 'ARB', 'OP', 'ATOM', 'DOT', 'ADA', 'XRP',
        'HYPE', 'WIF', 'PEPE', 'BONK', 'SHIB', 'FLOKI',
        'JTO', 'PYTH', 'JUP', 'RAY', 'ORCA',
        'TRUMP', 'PNUT', 'GOAT', 'MOODENG', 'AI16Z'
    ]
    
    if 'VINE' in known_symbols:
        print("✅ VINEは既知の銘柄リストに含まれています")
    else:
        print("❌ VINEは既知の銘柄リストに含まれていません")
        print("💡 VINEは実際には取引できない銘柄の可能性があります")

if __name__ == "__main__":
    print("🔍 VINE銘柄検証スクリプト")
    print("=" * 50)
    
    # 既知銘柄での確認
    check_known_symbols()
    
    # API での確認（タイムアウト制御付き）
    check_vine_with_timeout()
    
    print("\n📋 結論:")
    print("VINEがHyperliquidで実際に取引可能かどうかを確認中...")
    print("APIタイムアウトの場合、VINEは存在しない可能性が高いです")