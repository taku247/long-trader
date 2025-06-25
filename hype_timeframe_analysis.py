#!/usr/bin/env python3
"""
HYPEシンボルの時間足別データ状況調査
"""
import asyncio
from hyperliquid_api_client import MultiExchangeAPIClient
from datetime import datetime, timedelta
import json

async def investigate_hype_timeframes():
    # Exchange設定の確認
    try:
        with open('exchange_config.json', 'r') as f:
            config = json.load(f)
            exchange = config.get('default_exchange', 'hyperliquid')
    except:
        exchange = 'hyperliquid'
    
    print(f'📊 HYPE時間足別データ調査開始 (取引所: {exchange})')
    print('=' * 50)
    
    api_client = MultiExchangeAPIClient(exchange_type=exchange)
    timeframes = ['1m', '3m', '5m', '15m', '30m', '1h']
    symbol = 'HYPE'
    
    results = {}
    
    for timeframe in timeframes:
        try:
            print(f'\n🔍 {timeframe}足の調査...')
            
            # 90日分のデータ取得
            ohlcv_data = await api_client.get_ohlcv_data_with_period(symbol, timeframe, days=90)
            
            if not ohlcv_data.empty:
                data_points = len(ohlcv_data)
                start_date = ohlcv_data['timestamp'].min()
                end_date = ohlcv_data['timestamp'].max()
                actual_days = (end_date - start_date).days
                
                print(f'  ✅ データポイント数: {data_points}')
                print(f'  📅 期間: {start_date.strftime("%Y-%m-%d %H:%M")} ~ {end_date.strftime("%Y-%m-%d %H:%M")}')
                print(f'  📊 実際の日数: {actual_days}日')
                
                # 時間足別の期待値計算
                minutes_per_candle = {
                    '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30, '1h': 60
                }
                
                if timeframe in minutes_per_candle:
                    expected_per_day = 1440 / minutes_per_candle[timeframe]  # 1日のキャンドル数
                    expected_90_days = int(expected_per_day * 90)
                    coverage = (data_points / expected_90_days) * 100 if expected_90_days > 0 else 0
                    
                    print(f'  🎯 90日期待値: {expected_90_days}本 (カバレッジ: {coverage:.1f}%)')
                
                # データ品質チェック
                sufficient_data = data_points >= 1000
                if sufficient_data:
                    print(f'  ✅ 分析可能 (最低1000本クリア)')
                else:
                    print(f'  ❌ データ不足 (最低1000本必要)')
                    
                # 価格範囲とボラティリティ
                low_col = ohlcv_data['low']
                high_col = ohlcv_data['high']
                close_col = ohlcv_data['close']
                
                price_range = high_col.max() - low_col.min()
                avg_price = close_col.mean()
                volatility = (price_range / avg_price) * 100
                
                print(f'  💰 価格範囲: ${low_col.min():.4f} - ${high_col.max():.4f}')
                print(f'  📈 ボラティリティ: {volatility:.2f}%')
                
                # 支持線・抵抗線検出に必要なデータ数チェック
                sr_sufficient = data_points >= 50
                print(f'  🎯 支持線・抵抗線分析: {"✅ 可能" if sr_sufficient else "❌ データ不足"}')
                
                results[timeframe] = {
                    'data_points': data_points,
                    'actual_days': actual_days,
                    'sufficient_for_analysis': sufficient_data,
                    'sufficient_for_sr': sr_sufficient,
                    'volatility': volatility,
                    'price_range': {
                        'min': float(low_col.min()),
                        'max': float(high_col.max()),
                        'avg': float(avg_price)
                    }
                }
                
            else:
                print(f'  ❌ データなし')
                results[timeframe] = {
                    'data_points': 0,
                    'sufficient_for_analysis': False,
                    'sufficient_for_sr': False
                }
                
        except Exception as e:
            print(f'  ❌ エラー: {str(e)[:100]}')
            results[timeframe] = {
                'error': str(e),
                'data_points': 0,
                'sufficient_for_analysis': False,
                'sufficient_for_sr': False
            }
    
    # サマリー表示
    print('\n' + '=' * 50)
    print('📊 HYPE データ状況サマリー')
    print('=' * 50)
    
    for timeframe, data in results.items():
        if 'error' in data:
            print(f'{timeframe:>4}: ❌ エラー')
        else:
            status = "✅" if data['sufficient_for_analysis'] else "❌"
            sr_status = "✅" if data['sufficient_for_sr'] else "❌"
            print(f'{timeframe:>4}: {status} {data["data_points"]:>6}本 | SR分析: {sr_status} | ボラ: {data.get("volatility", 0):.1f}%')
    
    return results

if __name__ == "__main__":
    asyncio.run(investigate_hype_timeframes())