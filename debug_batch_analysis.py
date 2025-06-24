#!/usr/bin/env python3
"""
バッチ分析デバッグツール

ScalableAnalysisSystem.generate_batch_analysis の詳細動作を調査
"""

import sys
from pathlib import Path

# プロジェクトルートを追加
sys.path.append(str(Path(__file__).parent))

from scalable_analysis_system import ScalableAnalysisSystem
from real_time_system.utils.colored_log import get_colored_logger

def debug_batch_analysis():
    """バッチ分析の詳細デバッグ"""
    
    logger = get_colored_logger(__name__)
    
    print("🔍 ScalableAnalysisSystem バッチ分析デバッグ")
    print("=" * 60)
    
    # DOGEで失敗した設定を再現
    symbol = "DOGE"
    configs = [
        {
            'symbol': symbol,
            'timeframe': '15m',
            'strategy': 'Aggressive_ML',
            'strategy_config_id': 4,
            'strategy_name': 'Aggressive ML - 15m',
            'custom_parameters': {"risk_multiplier": 1.2, "confidence_boost": -0.05}
        },
        {
            'symbol': symbol,
            'timeframe': '30m',
            'strategy': 'Balanced',
            'strategy_config_id': 7,
            'strategy_name': 'Balanced - 30m',
            'custom_parameters': {"risk_multiplier": 1.0, "confidence_boost": 0.0}
        },
        {
            'symbol': symbol,
            'timeframe': '15m',
            'strategy': 'Balanced',
            'strategy_config_id': 23,
            'strategy_name': 'Balanced - 15m',
            'custom_parameters': {"risk_multiplier": 1.0, "confidence_threshold": 0.65}
        }
    ]
    
    print(f"📊 テスト設定:")
    for i, config in enumerate(configs, 1):
        print(f"  {i}. {config['strategy_name']} ({config['timeframe']})")
        print(f"     戦略: {config['strategy']}")
        print(f"     カスタムパラメータ: {config.get('custom_parameters', {})}")
    
    print()
    
    try:
        # ScalableAnalysisSystemの初期化
        print("🚀 ScalableAnalysisSystem 初期化")
        analysis_system = ScalableAnalysisSystem("large_scale_analysis")
        
        # バッチ分析実行（詳細ログ付き）
        print(f"\n📈 {symbol} バッチ分析開始")
        execution_id = "debug_test_execution"
        
        # バッチ分析実行
        processed_count = analysis_system.generate_batch_analysis(
            configs, 
            symbol=symbol, 
            execution_id=execution_id
        )
        
        print(f"\n✅ バッチ分析完了")
        print(f"   処理された設定数: {processed_count}")
        
        # 分析結果の確認
        print(f"\n📊 分析結果確認:")
        for config in configs:
            results = analysis_system.query_analyses(
                filters={
                    'symbol': config['symbol'],
                    'timeframe': config['timeframe'], 
                    'config': config['strategy']
                },
                limit=1
            )
            
            print(f"  {config['strategy_name']}:")
            if results and len(results) > 0:
                result = results[0] if isinstance(results, list) else results.iloc[0].to_dict()
                print(f"    ✅ 結果あり")
                print(f"    リターン: {result.get('total_return', 'N/A')}")
                print(f"    シャープレシオ: {result.get('sharpe_ratio', 'N/A')}")
                print(f"    ステータス: {result.get('status', 'N/A')}")
            else:
                print(f"    ❌ 結果なし")
        
    except Exception as e:
        print(f"❌ バッチ分析エラー: {e}")
        import traceback
        traceback.print_exc()
        
        # 個別に戦略を実行してより詳細なデバッグ
        print(f"\n🔍 個別戦略デバッグ:")
        for config in configs:
            try:
                print(f"\n  {config['strategy_name']} の個別実行:")
                
                # 個別分析実行
                from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
                
                engine = HighLeverageBotOrchestrator()
                
                # パラメータの準備
                timeframe = config['timeframe']
                strategy_type = config['strategy']
                
                print(f"    時間足: {timeframe}")
                print(f"    戦略タイプ: {strategy_type}")
                
                # 分析実行
                try:
                    result = engine.run_analysis(
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy_type=strategy_type,
                        custom_parameters=config.get('custom_parameters')
                    )
                    
                    print(f"    ✅ 個別分析成功")
                    print(f"    結果: {result}")
                    
                except Exception as individual_error:
                    print(f"    ❌ 個別分析失敗: {individual_error}")
                    
                    # さらに詳細なエラー解析
                    if "支持線" in str(individual_error) or "抵抗線" in str(individual_error):
                        print(f"    📊 支持線・抵抗線検出の問題")
                        
                        # データ取得確認
                        try:
                            from hyperliquid_api_client import MultiExchangeAPIClient
                            api_client = MultiExchangeAPIClient(exchange_type='hyperliquid')
                            ohlcv_data = api_client.get_ohlcv_data_with_period(symbol, timeframe, days=30)
                            print(f"    データ取得: ✅ ({len(ohlcv_data)}件)")
                            
                            # 支持線・抵抗線検出テスト
                            from engines.support_resistance_engine import SupportResistanceEngine
                            sr_engine = SupportResistanceEngine()
                            support_levels, resistance_levels = sr_engine.calculate_support_resistance(ohlcv_data)
                            
                            print(f"    支持線数: {len(support_levels)}")
                            print(f"    抵抗線数: {len(resistance_levels)}")
                            
                            if len(support_levels) == 0 and len(resistance_levels) == 0:
                                print(f"    ❌ 支持線・抵抗線が検出されない")
                                
                                # データの統計情報
                                print(f"    価格統計:")
                                print(f"      最低価格: {ohlcv_data['low'].min():.6f}")
                                print(f"      最高価格: {ohlcv_data['high'].max():.6f}")
                                print(f"      価格変動幅: {(ohlcv_data['high'].max() - ohlcv_data['low'].min()) / ohlcv_data['low'].min() * 100:.2f}%")
                                print(f"      平均ボリューム: {ohlcv_data['volume'].mean():.2f}")
                            
                        except Exception as data_error:
                            print(f"    ❌ データ取得エラー: {data_error}")
                    
            except Exception as config_error:
                print(f"  ❌ {config['strategy_name']} エラー: {config_error}")

if __name__ == "__main__":
    debug_batch_analysis()