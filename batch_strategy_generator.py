"""
バッチ戦略設定生成ツール
新しいシンボルに対して既存の全戦略設定を一括生成
"""
import json
import pandas as pd
from pathlib import Path

class BatchStrategyGenerator:
    def __init__(self):
        # 既存システムから抽出した戦略設定
        self.strategy_configs = {
            'timeframes': ['1m', '3m', '5m', '15m', '30m', '1h'],
            'strategies': [
                'Conservative_ML',
                'Aggressive_Traditional', 
                'Full_ML',
                'Hybrid_Strategy',
                'Risk_Optimized'
            ]
        }
        
        # 現在のシステムで使用されているシンボル
        self.existing_symbols = ['HYPE', 'SOL', 'PEPE', 'WIF', 'BONK']
    
    def generate_configs_for_symbol(self, symbol):
        """指定されたシンボルに対する全戦略設定を生成"""
        configs = []
        
        for timeframe in self.strategy_configs['timeframes']:
            for strategy in self.strategy_configs['strategies']:
                config = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'config': strategy
                }
                configs.append(config)
        
        return configs
    
    def generate_configs_for_multiple_symbols(self, symbols):
        """複数のシンボルに対する全戦略設定を生成"""
        all_configs = []
        
        for symbol in symbols:
            symbol_configs = self.generate_configs_for_symbol(symbol)
            all_configs.extend(symbol_configs)
        
        return all_configs
    
    def get_missing_symbol_configs(self, target_symbols):
        """新しいシンボルのうち、まだテストされていないものの設定を生成"""
        missing_symbols = []
        
        for symbol in target_symbols:
            if symbol not in self.existing_symbols:
                missing_symbols.append(symbol)
        
        if missing_symbols:
            return self.generate_configs_for_multiple_symbols(missing_symbols)
        else:
            return []
    
    def save_configs_to_json(self, configs, filename=None):
        """設定をJSONファイルに保存"""
        if filename is None:
            filename = f"batch_strategy_configs_{len(configs)}_configs.json"
        
        with open(filename, 'w') as f:
            json.dump(configs, f, indent=2)
        
        print(f"設定ファイル保存: {filename} ({len(configs)}設定)")
        return filename
    
    def create_summary_table(self, configs):
        """設定のサマリーテーブルを作成"""
        df = pd.DataFrame(configs)
        
        print("\n=== バッチ設定サマリー ===")
        print(f"総設定数: {len(configs)}")
        print(f"シンボル数: {len(df['symbol'].unique())}")
        print(f"タイムフレーム数: {len(df['timeframe'].unique())}")
        print(f"戦略数: {len(df['config'].unique())}")
        
        print(f"\nシンボル別設定数:")
        symbol_counts = df['symbol'].value_counts()
        for symbol, count in symbol_counts.items():
            print(f"  {symbol}: {count}設定")
        
        print(f"\n戦略別設定数:")
        strategy_counts = df['config'].value_counts()
        for strategy, count in strategy_counts.items():
            print(f"  {strategy}: {count}設定")
        
        return df

# 便利な関数
def quick_generate_for_symbol(symbol):
    """シンボル指定での簡単設定生成"""
    generator = BatchStrategyGenerator()
    configs = generator.generate_configs_for_symbol(symbol)
    
    print(f"{symbol} の戦略設定を生成:")
    generator.create_summary_table(configs)
    
    return configs

def quick_generate_for_multiple_symbols(symbols):
    """複数シンボルでの簡単設定生成"""
    generator = BatchStrategyGenerator()
    configs = generator.generate_configs_for_multiple_symbols(symbols)
    
    print(f"複数シンボル ({', '.join(symbols)}) の戦略設定を生成:")
    generator.create_summary_table(configs)
    
    return configs

def add_new_crypto_symbols(new_symbols):
    """新しい暗号通貨シンボルを追加してテスト設定を生成"""
    generator = BatchStrategyGenerator()
    
    print(f"新しいシンボルを追加: {', '.join(new_symbols)}")
    
    # 新規シンボルの設定生成
    configs = generator.generate_configs_for_multiple_symbols(new_symbols)
    
    # サマリー表示
    summary_df = generator.create_summary_table(configs)
    
    # JSONファイル保存
    filename = generator.save_configs_to_json(configs, f"new_symbols_configs.json")
    
    print(f"\n次のステップ:")
    print(f"1. スケーラブルシステムでテスト: scalable_analysis_system.py")
    print(f"2. または新シンボルテスターでテスト: new_symbol_strategy_tester.py")
    print(f"3. 設定ファイル: {filename}")
    
    return configs, summary_df

def main():
    """デモとインタラクティブな使用"""
    print("=" * 60)
    print("バッチ戦略設定生成ツール")
    print("=" * 60)
    
    generator = BatchStrategyGenerator()
    
    print("\n現在サポートされている戦略:")
    for i, strategy in enumerate(generator.strategy_configs['strategies'], 1):
        print(f"{i}. {strategy}")
    
    print(f"\nタイムフレーム: {', '.join(generator.strategy_configs['timeframes'])}")
    print(f"既存シンボル: {', '.join(generator.existing_symbols)}")
    
    # ユーザー入力
    print(f"\n使用例:")
    print(f"1. 単一シンボル: BTC")
    print(f"2. 複数シンボル: BTC,ETH,ADA")
    print(f"3. メジャー暗号通貨: BTC,ETH,BNB,XRP,ADA,DOGE,MATIC,DOT,AVAX,SHIB")
    
    user_input = input(f"\nテストしたいシンボルを入力 (カンマ区切り): ").strip()
    
    if not user_input:
        # デフォルト例
        symbols = ['BTC', 'ETH']
        print(f"デフォルト例を使用: {', '.join(symbols)}")
    else:
        symbols = [s.strip().upper() for s in user_input.split(',')]
    
    # 設定生成
    configs, summary_df = add_new_crypto_symbols(symbols)
    
    # 実行オプション表示
    print(f"\n即座にテストを実行しますか？")
    print(f"1. はい - new_symbol_strategy_tester.py を使用")
    print(f"2. いいえ - 設定ファイルのみ生成")
    
    choice = input("選択 (1 or 2): ").strip()
    
    if choice == '1':
        try:
            print("⚠️ 警告: new_symbol_strategy_tester.py はレガシーファイルです")
            print("   ランダムデータ生成により実際の市場データとは無関係な結果が表示されます")
            print("✅ 推奨: web_dashboard/app.py のWebインターフェースを使用してください")
            print()
            
            from new_symbol_strategy_tester import NewSymbolStrategyTester
            
            tester = NewSymbolStrategyTester()
            
            for symbol in symbols:
                print(f"\n{symbol} のテスト開始...")
                results_df = tester.test_all_strategies_on_symbol(symbol)
                tester.update_main_results_csv(results_df)
                tester.generate_summary_report(symbol, results_df)
                
                # 推奨戦略
                recommendations = tester.get_recommended_strategies(symbol, results_df, top_n=2)
                print(f"\n{symbol} 推奨戦略:")
                for rec in recommendations:
                    print(f"  {rec['rank']}. {rec['timeframe']} {rec['strategy']} (Sharpe: {rec['sharpe_ratio']:.2f})")
            
            print(f"\n✅ 全シンボルのテスト完了")
            print(f"📊 結果確認: python dashboard.py")
            
        except ImportError:
            print("new_symbol_strategy_tester.py が見つかりません")
            print("設定ファイルが生成されました。手動でテストを実行してください")
    else:
        print(f"\n設定ファイルが生成されました")
        print(f"手動でテストを実行するには:")
        print(f"  python new_symbol_strategy_tester.py")

if __name__ == "__main__":
    main()