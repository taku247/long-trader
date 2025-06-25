#!/usr/bin/env python3
"""
XRP分析テスト

設定調整後のXRP支持線・抵抗線検出をテスト
"""

import sys
import os
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ログレベルを設定してエラー詳細を確認
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def test_xrp_analysis():
    """XRP分析テスト"""
    print("🔍 XRP分析テスト開始")
    print("=" * 50)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # XRPで単発分析テスト
        print(f"\n🧪 XRP 15m Conservative_ML 分析テスト")
        
        try:
            result = system._generate_single_analysis("XRP", "15m", "Conservative_ML")
            
            print(f"✅ XRP分析成功:")
            print(f"   結果の型: {type(result)}")
            
            if isinstance(result, tuple) and len(result) >= 2:
                trades, metrics = result
                print(f"   トレード数: {len(trades) if trades else 0}")
                print(f"   メトリクス: {metrics}")
            elif isinstance(result, list):
                print(f"   トレード数: {len(result)}")
                if result:
                    first_trade = result[0]
                    print(f"   最初のトレード: {first_trade}")
            else:
                print(f"   結果: {result}")
                
        except Exception as e:
            print(f"❌ XRP分析エラー: {e}")
            print(f"   エラータイプ: {type(e)}")
            
            # エラー詳細がログに出力されているはず
            print(f"\n📝 詳細ログをご確認ください（ERROR レベル）")
        
        # 設定確認
        print(f"\n🔧 現在の支持線・抵抗線検出設定確認:")
        try:
            import json
            with open('config/support_resistance_config.json', 'r') as f:
                config = json.load(f)
                
            provider_settings = config.get('provider_settings', {})
            visualizer_settings = provider_settings.get('SupportResistanceVisualizer', {})
            simple_settings = provider_settings.get('Simple', {})
            default_provider = config.get('default_provider', {})
            
            print(f"   デフォルトプロバイダー: {default_provider.get('base_provider', 'N/A')}")
            print(f"   ML強化: {default_provider.get('use_ml_enhancement', 'N/A')}")
            print(f"   Visualizer設定: min_touches={visualizer_settings.get('min_touches', 'N/A')}, tolerance={visualizer_settings.get('tolerance_pct', 'N/A')}")
            print(f"   Simple設定: min_touches={simple_settings.get('min_touches', 'N/A')}, tolerance={simple_settings.get('tolerance_pct', 'N/A')}")
            
        except Exception as e:
            print(f"   設定読み込みエラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ システム初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_xrp_data_availability():
    """XRPのデータ可用性テスト"""
    print(f"\n🔍 XRPデータ可用性テスト")
    print("=" * 40)
    
    try:
        from data_utils.multi_exchange_api_client import MultiExchangeAPIClient
        from datetime import datetime, timezone, timedelta
        
        # XRPのOHLCVデータ取得テスト
        client = MultiExchangeAPIClient()
        
        # 15分足で90日間のデータ取得
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=90)
        
        print(f"   データ取得期間: {start_time.strftime('%Y-%m-%d')} ～ {end_time.strftime('%Y-%m-%d')}")
        
        try:
            ohlcv_data = client.fetch_ohlcv("XRP", "15m", 90)
            
            if ohlcv_data is not None and not ohlcv_data.empty:
                print(f"   ✅ XRP OHLCVデータ取得成功:")
                print(f"      データ件数: {len(ohlcv_data)}")
                print(f"      期間: {ohlcv_data.index[0]} ～ {ohlcv_data.index[-1]}")
                print(f"      価格範囲: {ohlcv_data['low'].min():.4f} - {ohlcv_data['high'].max():.4f}")
                print(f"      平均ボラティリティ: {((ohlcv_data['high'] - ohlcv_data['low']) / ohlcv_data['close']).mean():.4f}")
                
                # データ密度確認
                expected_points = 90 * 24 * 4  # 90日 * 24時間 * 4回(15分毎)
                actual_points = len(ohlcv_data)
                density = (actual_points / expected_points) * 100
                print(f"      データ密度: {density:.1f}% ({actual_points}/{expected_points})")
                
                return True
            else:
                print(f"   ❌ XRP OHLCVデータ取得失敗: データなし")
                return False
                
        except Exception as e:
            print(f"   ❌ XRP OHLCVデータ取得失敗: {e}")
            return False
            
    except Exception as e:
        print(f"❌ データ可用性テストエラー: {e}")
        return False

if __name__ == "__main__":
    print("🚀 XRP問題診断テスト開始")
    print("=" * 60)
    
    # データ可用性テスト
    data_success = test_xrp_data_availability()
    
    # 分析テスト
    analysis_success = test_xrp_analysis()
    
    # 結果サマリー
    print(f"\n🎯 XRP問題診断テスト結果")
    print("=" * 50)
    print(f"📊 データ可用性: {'✅ 正常' if data_success else '❌ 問題あり'}")
    print(f"📈 分析機能: {'✅ 正常' if analysis_success else '❌ 問題あり'}")
    
    if data_success and analysis_success:
        print(f"\n🎉 XRP問題が改善された可能性があります")
        print(f"🔄 XRPの銘柄追加を再試行してみてください")
    else:
        print(f"\n🔧 XRP問題が継続しています")
        print(f"📝 上記のエラーログを確認して追加調整が必要です")
    
    sys.exit(0 if (data_success and analysis_success) else 1)