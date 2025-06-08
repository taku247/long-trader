#!/usr/bin/env python3
"""
BTC-アルトコイン連れ安予測システム - 統合実行スクリプト

【使用方法】
# バックテスト実行
python run_correlation_analysis.py --mode backtest --symbols ETH,SOL,HYPE

# モデル訓練
python run_correlation_analysis.py --mode train --symbol ETH

# 予測実行
python run_correlation_analysis.py --mode predict --symbol ETH --btc-drop -5.0 --leverage 10
"""

import argparse
import sys
import asyncio
from btc_altcoin_correlation_predictor import BTCAltcoinCorrelationPredictor
from btc_altcoin_backtester import BTCAltcoinBacktester

def main():
    parser = argparse.ArgumentParser(description='BTC-アルトコイン連れ安予測システム')
    parser.add_argument('--mode', type=str, required=True,
                       choices=['train', 'predict', 'backtest'],
                       help='実行モード')
    
    # 共通パラメータ
    parser.add_argument('--symbol', type=str, help='アルトコインシンボル（単一）')
    parser.add_argument('--symbols', type=str, help='アルトコインシンボル（複数、カンマ区切り）')
    
    # 予測モード用
    parser.add_argument('--btc-drop', type=float, help='BTC下落率%')
    parser.add_argument('--leverage', type=float, default=10.0, help='レバレッジ倍率')
    
    # バックテストモード用
    parser.add_argument('--backtest-days', type=int, default=365, help='バックテスト期間（日数）')
    parser.add_argument('--btc-threshold', type=float, default=-3.0, help='BTC急落検知閾値')
    
    args = parser.parse_args()
    
    if args.mode == 'train':
        # モデル訓練モード
        if not args.symbol:
            print("訓練モードでは --symbol が必要です")
            return 1
        
        predictor = BTCAltcoinCorrelationPredictor()
        success = predictor.train_prediction_model(args.symbol.upper())
        
        if success:
            predictor.save_model(args.symbol.upper())
            print("✅ モデル訓練完了")
        else:
            print("❌ モデル訓練失敗")
            return 1
    
    elif args.mode == 'predict':
        # 予測モード
        if not args.symbol or args.btc_drop is None:
            print("予測モードでは --symbol と --btc-drop が必要です")
            return 1
        
        predictor = BTCAltcoinCorrelationPredictor()
        symbol = args.symbol.upper()
        
        # モデル読み込み
        if not predictor.load_model(symbol):
            print(f"{symbol}のモデルが見つかりません。先に訓練してください。")
            return 1
        
        # 予測実行
        predictions = predictor.predict_altcoin_drop(symbol, args.btc_drop)
        
        if predictions:
            print(f"\n🔍 BTC{args.btc_drop}%下落時の{symbol}連れ安予測")
            print("=" * 50)
            
            print(f"\n📊 予測結果:")
            for horizon, pred_drop in predictions.items():
                print(f"  {horizon:3d}分後: {pred_drop:+6.2f}%")
            
            # リスク評価
            risk_assessment = predictor.calculate_liquidation_risk(symbol, predictions, args.leverage)
            print(f"\n⚠️  清算リスク評価 (レバレッジ: {args.leverage}x)")
            
            for horizon, risk in risk_assessment['risk_levels'].items():
                risk_icon = {
                    'LOW': '🟢',
                    'MEDIUM': '🔶', 
                    'HIGH': '🔴',
                    'CRITICAL': '❌'
                }.get(risk['risk_level'], '⚪')
                
                print(f"  {horizon:3d}分: {risk_icon} {risk['risk_level']} "
                      f"(PnL: {risk['leveraged_pnl_pct']:+6.2f}%, "
                      f"清算まで: {risk['margin_to_liquidation']:.1f}%)")
            
            print(f"\n💡 清算閾値: {risk_assessment['liquidation_threshold_pct']:.1f}%")
        else:
            print("予測に失敗しました")
            return 1
    
    elif args.mode == 'backtest':
        # バックテストモード
        if not args.symbols:
            print("バックテストモードでは --symbols が必要です")
            return 1
        
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
        
        print(f"🧪 バックテスト開始")
        print(f"対象銘柄: {', '.join(symbols)}")
        print(f"期間: {args.backtest_days}日間")
        print(f"BTC閾値: {args.btc_threshold}%")
        
        # バックテスター初期化
        backtester = BTCAltcoinBacktester(btc_drop_threshold=args.btc_threshold)
        
        # 急落イベント抽出
        btc_events = backtester.extract_btc_drop_events(args.backtest_days)
        
        if len(btc_events) < 10:
            print("❌ 急落イベントが少なすぎます。閾値を調整してください。")
            return 1
        
        # バックテスト実行
        results = {}
        for symbol in symbols:
            print(f"\n{'='*50}")
            print(f"{symbol} バックテスト")
            print(f"{'='*50}")
            
            result = backtester.run_backtest(symbol, btc_events)
            if result:
                results[symbol] = result
                
                # 結果表示
                print(f"\n{symbol} 結果サマリー:")
                print(f"  総イベント数: {result.total_events}")
                
                if result.prediction_accuracy:
                    avg_mae = sum(result.prediction_accuracy.values()) / len(result.prediction_accuracy)
                    print(f"  平均予測精度 (MAE): {avg_mae:.3f}%")
                
                if result.direction_accuracy:
                    avg_dir = sum(result.direction_accuracy.values()) / len(result.direction_accuracy)
                    print(f"  平均方向性精度: {avg_dir:.1f}%")
                
                if result.liquidation_avoidance:
                    avg_avoid = sum(result.liquidation_avoidance.values()) / len(result.liquidation_avoidance)
                    print(f"  平均清算回避率: {avg_avoid:.1f}%")
        
        if results:
            # 結果可視化・保存
            backtester.visualize_results(results)
            backtester.save_results(results)
            
            print(f"\n🎉 バックテスト完了!")
            print("📊 詳細結果: backtest_results.png")
            print("💾 データ: backtest_results.json")
        else:
            print("❌ バックテストに失敗しました")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())