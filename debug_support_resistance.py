#!/usr/bin/env python3
"""
支持線・抵抗線検出デバッグツール

DOGEの支持線・抵抗線検出が失敗する原因を詳細調査
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import asyncio

async def debug_support_resistance_doge():
    """DOGE の支持線・抵抗線検出テスト"""
    
    print("📊 DOGE 支持線・抵抗線検出デバッグ")
    print("=" * 60)
    
    symbol = "DOGE"
    timeframes = ['15m', '30m']
    
    for timeframe in timeframes:
        print(f"\n🔍 {timeframe} 時間足の検証:")
        
        try:
            # 1. データ取得
            print("  1. データ取得テスト:")
            
            from hyperliquid_api_client import MultiExchangeAPIClient
            api_client = MultiExchangeAPIClient(exchange_type='hyperliquid')
            
            ohlcv_data = await api_client.get_ohlcv_data_with_period(symbol, timeframe, days=30)
            print(f"     ✅ データ取得成功: {len(ohlcv_data)}件")
            print(f"     期間: {ohlcv_data['timestamp'].min()} - {ohlcv_data['timestamp'].max()}")
            print(f"     価格範囲: {ohlcv_data['low'].min():.6f} - {ohlcv_data['high'].max():.6f}")
            
            # 価格変動の統計
            price_range = ohlcv_data['high'].max() - ohlcv_data['low'].min()
            price_volatility = price_range / ohlcv_data['low'].min() * 100
            print(f"     価格変動率: {price_volatility:.2f}%")
            
            # 2. 支持線・抵抗線検出
            print("  2. 支持線・抵抗線検出テスト:")
            
            from engines.support_resistance_detector import SupportResistanceDetector
            sr_engine = SupportResistanceDetector()
            
            current_price = ohlcv_data['close'].iloc[-1]
            support_levels, resistance_levels = sr_engine.detect_levels_from_ohlcv(ohlcv_data, current_price)
            
            print(f"     支持線数: {len(support_levels)}")
            print(f"     抵抗線数: {len(resistance_levels)}")
            
            if len(support_levels) > 0:
                print(f"     支持線例: {support_levels[:3]}")
            
            if len(resistance_levels) > 0:
                print(f"     抵抗線例: {resistance_levels[:3]}")
            
            # 3. 支持線・抵抗線が検出されない場合の詳細分析
            if len(support_levels) == 0 and len(resistance_levels) == 0:
                print("     ❌ 支持線・抵抗線が検出されません")
                
                # データの詳細分析
                print("     📈 データ詳細分析:")
                
                # 価格統計
                close_prices = ohlcv_data['close']
                print(f"       平均価格: {close_prices.mean():.6f}")
                print(f"       標準偏差: {close_prices.std():.6f}")
                print(f"       変動係数: {close_prices.std() / close_prices.mean():.4f}")
                
                # ボリューム統計
                volumes = ohlcv_data['volume']
                print(f"       平均ボリューム: {volumes.mean():.2f}")
                print(f"       ボリューム変動: {volumes.std() / volumes.mean():.4f}")
                
                # ローソク足の分析
                high_low_ranges = ohlcv_data['high'] - ohlcv_data['low']
                print(f"       平均レンジ: {high_low_ranges.mean():.6f}")
                print(f"       最大レンジ: {high_low_ranges.max():.6f}")
                
                # トレンド分析
                price_changes = close_prices.pct_change().dropna()
                positive_changes = (price_changes > 0).sum()
                negative_changes = (price_changes < 0).sum()
                print(f"       上昇回数: {positive_changes}")
                print(f"       下降回数: {negative_changes}")
                print(f"       トレンド: {'上昇傾向' if positive_changes > negative_changes else '下降傾向' if negative_changes > positive_changes else '横ばい'}")
                
                # 移動平均との乖離
                sma_20 = close_prices.rolling(20).mean()
                deviation_from_sma = abs(close_prices - sma_20) / sma_20 * 100
                print(f"       SMA20からの平均乖離: {deviation_from_sma.mean():.2f}%")
                
                # 支持線・抵抗線エンジンのパラメータ確認
                print("     ⚙️ SupportResistanceEngine パラメータ:")
                print(f"       min_touches: {getattr(sr_engine, 'min_touches', 'N/A')}")
                print(f"       tolerance: {getattr(sr_engine, 'tolerance', 'N/A')}")
                print(f"       lookback_period: {getattr(sr_engine, 'lookback_period', 'N/A')}")
            
            else:
                print("     ✅ 支持線・抵抗線が検出されました")
            
            # 4. レバレッジ分析エンジンでのテスト
            print("  3. レバレッジ分析エンジンテスト:")
            
            try:
                from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
                
                orchestrator = HighLeverageBotOrchestrator()
                
                # 分析実行
                result = orchestrator.run_analysis(
                    symbol=symbol,
                    timeframe=timeframe,
                    strategy_type='Balanced'
                )
                
                print(f"     ✅ レバレッジ分析成功")
                print(f"     結果概要: {type(result)}")
                
                if hasattr(result, '__dict__'):
                    print(f"     詳細: {result.__dict__}")
                else:
                    print(f"     詳細: {result}")
                
            except Exception as leverage_error:
                print(f"     ❌ レバレッジ分析失敗: {leverage_error}")
                
                # エラーの詳細分析
                error_message = str(leverage_error)
                if "支持線" in error_message or "抵抗線" in error_message:
                    print(f"     🔍 支持線・抵抗線関連のエラー")
                elif "データ" in error_message:
                    print(f"     🔍 データ関連のエラー")
                elif "設定" in error_message:
                    print(f"     🔍 設定関連のエラー")
                
                import traceback
                print(f"     📝 エラートレースバック:")
                traceback.print_exc()
                
        except Exception as e:
            print(f"  ❌ {timeframe} 検証エラー: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_support_resistance_doge())