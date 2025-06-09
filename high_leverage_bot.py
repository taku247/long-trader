#!/usr/bin/env python3
"""
ハイレバレッジ判定Bot - メイン実行スクリプト

memo記載の核心機能「今このタイミングで対象のトークンに対してハイレバのロング何倍かけて大丈夫か判定するbot」
のメイン実行インターフェース。

使用方法:
    python high_leverage_bot.py --symbol HYPE
    python high_leverage_bot.py --symbol SOL --timeframe 15m
    python high_leverage_bot.py --check-multiple HYPE,SOL,WIF
"""

import argparse
import sys
from datetime import datetime

# プラグインシステムをインポート
from engines import HighLeverageBotOrchestrator, analyze_leverage_for_symbol, quick_leverage_check

def main():
    parser = argparse.ArgumentParser(
        description='ハイレバレッジ判定Bot - memo記載の核心機能を実装',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s --symbol HYPE                    # HYPE の1時間足でレバレッジ判定
  %(prog)s --symbol SOL --timeframe 15m     # SOL の15分足でレバレッジ判定  
  %(prog)s --check-multiple HYPE,SOL,WIF    # 複数銘柄の一括チェック
  %(prog)s --demo                           # デモ実行
        """
    )
    
    # 基本パラメータ
    parser.add_argument('--symbol', type=str, 
                       help='分析対象シンボル (例: HYPE, SOL, WIF)')
    parser.add_argument('--timeframe', type=str, default='1h',
                       choices=['1m', '3m', '5m', '15m', '30m', '1h'],
                       help='時間足 (デフォルト: 1h)')
    
    # 一括分析
    parser.add_argument('--check-multiple', type=str,
                       help='複数銘柄の一括チェック (カンマ区切り、例: HYPE,SOL,WIF)')
    
    # デモモード
    parser.add_argument('--demo', action='store_true',
                       help='デモンストレーション実行')
    
    # 詳細表示
    parser.add_argument('--verbose', action='store_true',
                       help='詳細な分析結果を表示')
    
    args = parser.parse_args()
    
    # ヘッダー表示
    print_header()
    
    try:
        if args.demo:
            # デモ実行
            run_demo()
            
        elif args.check_multiple:
            # 複数銘柄一括チェック
            symbols = [s.strip().upper() for s in args.check_multiple.split(',')]
            run_multiple_analysis(symbols, args.verbose)
            
        elif args.symbol:
            # 単一銘柄分析
            run_single_analysis(args.symbol.upper(), args.timeframe, args.verbose)
            
        else:
            # 引数が不足している場合
            parser.print_help()
            print("\n❌ --symbol または --check-multiple または --demo のいずれかを指定してください")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⛔ ユーザーによって中断されました")
        return 1
    except Exception as e:
        print(f"\n❌ 実行エラー: {e}")
        return 1
    
    return 0

def print_header():
    """ヘッダーを表示"""
    print("=" * 80)
    print("🎯 ハイレバレッジ判定Bot")
    print("=" * 80)
    print("📝 memo記載の核心機能: 「今このタイミングで対象のトークンに対して")
    print("   ハイレバのロング何倍かけて大丈夫か判定するbot」")
    print("🔧 プラグイン型アーキテクチャ実装")
    print(f"⏰ 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

def run_single_analysis(symbol: str, timeframe: str, verbose: bool = False):
    """単一銘柄の詳細分析"""
    
    print(f"\n🎯 単一銘柄分析: {symbol} ({timeframe})")
    print("-" * 50)
    
    try:
        # レバレッジ分析実行
        recommendation = analyze_leverage_for_symbol(symbol, timeframe)
        
        # 結果表示
        if verbose:
            # 詳細表示は既にanalyze_leverage_for_symbolで表示済み
            pass
        else:
            # 簡潔表示
            print_summary_result(symbol, recommendation)
        
        # 推奨アクション
        print_recommended_actions(recommendation)
        
    except Exception as e:
        print(f"❌ {symbol} の分析エラー: {e}")

def run_multiple_analysis(symbols: list, verbose: bool = False):
    """複数銘柄の一括分析"""
    
    print(f"\n🔄 複数銘柄一括分析: {', '.join(symbols)}")
    print("-" * 50)
    
    results = {}
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n📊 [{i}/{len(symbols)}] {symbol} 分析中...")
        
        try:
            if verbose:
                recommendation = analyze_leverage_for_symbol(symbol, "1h")
                results[symbol] = recommendation
            else:
                result = quick_leverage_check(symbol)
                results[symbol] = result
                print(f"   {result}")
                
        except Exception as e:
            error_msg = f"❌ エラー: {str(e)}"
            results[symbol] = error_msg
            print(f"   {error_msg}")
    
    # サマリー表示
    print("\n" + "=" * 60)
    print("📊 一括分析結果サマリー")
    print("=" * 60)
    
    for symbol, result in results.items():
        if isinstance(result, str):
            print(f"{symbol:8s}: {result}")
        else:
            leverage = result.recommended_leverage
            confidence = result.confidence_level
            status = get_leverage_status(leverage, confidence)
            print(f"{symbol:8s}: {status}")

def run_demo():
    """デモンストレーション実行"""
    
    print("\n🧪 デモンストレーション実行")
    print("-" * 50)
    
    demo_symbols = ["HYPE", "SOL", "WIF"]
    
    print("以下の機能をデモンストレーションします:")
    print("1️⃣ 単一銘柄の詳細分析")
    print("2️⃣ 複数銘柄の一括分析")
    print("3️⃣ プラグイン差し替え機能")
    
    input("\n⏸️  Enterキーを押して開始...")
    
    # デモ実行
    import plugin_system_demo
    plugin_system_demo.main()

def print_summary_result(symbol: str, recommendation):
    """簡潔な結果表示"""
    
    leverage = recommendation.recommended_leverage
    confidence = recommendation.confidence_level
    risk_reward = recommendation.risk_reward_ratio
    
    print(f"\n💰 現在価格: {recommendation.market_conditions.current_price:.4f}")
    print(f"🎪 推奨レバレッジ: {leverage:.1f}x")
    print(f"🎯 信頼度: {confidence*100:.1f}%")
    print(f"⚖️ リスクリワード比: {risk_reward:.2f}")
    
    # ステータス表示
    status = get_leverage_status(leverage, confidence)
    print(f"📊 判定: {status}")

def print_recommended_actions(recommendation):
    """推奨アクションを表示"""
    
    leverage = recommendation.recommended_leverage
    confidence = recommendation.confidence_level
    
    print("\n🎯 推奨アクション:")
    print("-" * 30)
    
    if leverage >= 10 and confidence >= 0.7:
        print("🚀 積極的なハイレバレッジ取引が推奨されます")
        print(f"📍 損切り: {recommendation.stop_loss_price:.4f}")
        print(f"🎯 利確: {recommendation.take_profit_price:.4f}")
        print("⚠️ リスク管理を徹底してください")
        
    elif leverage >= 5 and confidence >= 0.5:
        print("⚡ 中程度のレバレッジ取引が可能です")
        print(f"📍 損切り: {recommendation.stop_loss_price:.4f}")
        print(f"🎯 利確: {recommendation.take_profit_price:.4f}")
        print("💡 ポジションサイズを調整してください")
        
    elif leverage >= 2:
        print("🐌 低レバレッジでの慎重な取引を検討してください")
        print("📊 さらなる分析が推奨されます")
        
    else:
        print("🛑 現在は取引を控えることを強く推奨します")
        print("📈 市場状況の改善を待ってください")
        
    print("\n💡 この判定は参考情報です。投資判断は自己責任でお願いします。")

def get_leverage_status(leverage: float, confidence: float) -> str:
    """レバレッジステータスを取得"""
    
    if leverage >= 10 and confidence >= 0.7:
        return f"🚀 高レバ推奨: {leverage:.1f}x (信頼度: {confidence*100:.0f}%)"
    elif leverage >= 5 and confidence >= 0.5:
        return f"⚡ 中レバ推奨: {leverage:.1f}x (信頼度: {confidence*100:.0f}%)"
    elif leverage >= 2:
        return f"🐌 低レバ推奨: {leverage:.1f}x (信頼度: {confidence*100:.0f}%)"
    else:
        return f"🛑 レバレッジ非推奨: {leverage:.1f}x (信頼度: {confidence*100:.0f}%)"

if __name__ == "__main__":
    sys.exit(main())