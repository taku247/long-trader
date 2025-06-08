"""
戦略再現システム - 良い戦略を実際に再現するためのツール
"""
from scalable_analysis_system import ScalableAnalysisSystem
import json
import pandas as pd
from pathlib import Path

class StrategyReproducer:
    def __init__(self):
        self.system = ScalableAnalysisSystem()
        self.config_mapping = self._load_config_mapping()
    
    def _load_config_mapping(self):
        """設定名からパラメータへのマッピング"""
        # 実際の戦略パラメータ（現在はサンプル）
        return {
            'Config_01': {
                'name': 'Conservative_ML',
                'downside_evaluator': 'MultiLayerRiskEvaluator',
                'upside_calculator': 'MLBreakoutPredictor',
                'leverage_calculator': 'FixedFractionalCalculator',
                'max_leverage': 3.0,
                'risk_tolerance': 0.02
            },
            'Config_02': {
                'name': 'Aggressive_Traditional',
                'downside_evaluator': 'SimpleDistanceRiskEvaluator',
                'upside_calculator': 'LinearProjectionCalculator',
                'leverage_calculator': 'KellyLeverageCalculator',
                'max_leverage': 8.0,
                'risk_tolerance': 0.05
            },
            # ... 他の設定
        }
    
    def find_best_strategies(self, criteria=None):
        """最良の戦略を検索"""
        if criteria is None:
            criteria = {'min_sharpe': 1.5}
        
        strategies = self.system.query_analyses(
            filters=criteria,
            order_by='sharpe_ratio',
            limit=20
        )
        
        return strategies
    
    def get_strategy_config(self, symbol, timeframe, config_name):
        """戦略の設定パラメータを取得"""
        if config_name not in self.config_mapping:
            return None
        
        base_config = self.config_mapping[config_name].copy()
        
        # 戦略の詳細情報
        details = self.system.get_analysis_details(symbol, timeframe, config_name)
        if details:
            base_config.update({
                'symbol': symbol,
                'timeframe': timeframe,
                'performance': {
                    'sharpe_ratio': details['info']['sharpe_ratio'],
                    'total_return': details['info']['total_return'],
                    'win_rate': details['info']['win_rate'],
                    'max_drawdown': details['info']['max_drawdown']
                }
            })
        
        return base_config
    
    def export_strategy_config(self, symbol, timeframe, config_name, output_file=None):
        """戦略設定をJSONファイルにエクスポート"""
        config = self.get_strategy_config(symbol, timeframe, config_name)
        
        if config is None:
            print(f"戦略が見つかりません: {symbol}_{timeframe}_{config_name}")
            return False
        
        if output_file is None:
            output_file = f"strategy_{symbol}_{timeframe}_{config_name}.json"
        
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        
        print(f"戦略設定をエクスポート: {output_file}")
        return True
    
    def create_reproduction_script(self, symbol, timeframe, config_name):
        """戦略を再現するスクリプトを生成"""
        config = self.get_strategy_config(symbol, timeframe, config_name)
        
        if config is None:
            return None
        
        script_content = f'''"""
戦略再現スクリプト: {symbol} {timeframe} {config_name}
生成日時: {pd.Timestamp.now()}

パフォーマンス:
- Sharpe Ratio: {config.get('performance', {}).get('sharpe_ratio', 'N/A')}
- Total Return: {config.get('performance', {}).get('total_return', 'N/A')}
- Win Rate: {config.get('performance', {}).get('win_rate', 'N/A')}
"""

# 設定パラメータ
CONFIG = {{
    'symbol': '{symbol}',
    'timeframe': '{timeframe}',
    'strategy_name': '{config.get('name', config_name)}',
    'max_leverage': {config.get('max_leverage', 5.0)},
    'risk_tolerance': {config.get('risk_tolerance', 0.03)},
    'modules': {{
        'downside_evaluator': '{config.get('downside_evaluator', '')}',
        'upside_calculator': '{config.get('upside_calculator', '')}',
        'leverage_calculator': '{config.get('leverage_calculator', '')}'
    }}
}}

def run_strategy():
    """実際の戦略実行（要実装）"""
    print("戦略設定:")
    for key, value in CONFIG.items():
        print(f"  {{key}}: {{value}}")
    
    # TODO: 実際のバックテスト・ライブトレード実装
    print("\\n注意: 実際の取引ロジックは未実装です")
    print("この設定を使って実際のシステムを構築してください")

if __name__ == "__main__":
    run_strategy()
'''
        
        script_file = f"reproduce_{symbol}_{timeframe}_{config_name}.py"
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        print(f"再現スクリプト生成: {script_file}")
        return script_file
    
    def interactive_strategy_selection(self):
        """インタラクティブな戦略選択"""
        print("=" * 60)
        print("戦略再現システム")
        print("=" * 60)
        
        # 最良の戦略を表示
        print("\n🏆 高性能戦略 TOP 10:")
        strategies = self.find_best_strategies()
        
        for i, (_, strategy) in enumerate(strategies.iterrows()):
            print(f"{i+1:2d}. {strategy['symbol']} ({strategy['timeframe']}) - {strategy['config']}")
            print(f"    Sharpe: {strategy['sharpe_ratio']:.2f} | Return: {strategy['total_return']:.1f}% | Win: {strategy['win_rate']:.1%}")
        
        # ユーザー選択
        try:
            choice = int(input(f"\n再現したい戦略を選択 (1-{len(strategies)}): ")) - 1
            if 0 <= choice < len(strategies):
                selected = strategies.iloc[choice]
                
                symbol = selected['symbol']
                timeframe = selected['timeframe']
                config = selected['config']
                
                print(f"\n選択された戦略: {symbol} {timeframe} {config}")
                
                # 詳細表示
                details = self.system.get_analysis_details(symbol, timeframe, config)
                if details:
                    print(f"詳細:")
                    print(f"  - Total Trades: {details['info']['total_trades']}")
                    print(f"  - Avg Leverage: {details['info']['avg_leverage']:.1f}x")
                    print(f"  - Max Drawdown: {details['info']['max_drawdown']:.1%}")
                
                # エクスポート
                self.export_strategy_config(symbol, timeframe, config)
                self.create_reproduction_script(symbol, timeframe, config)
                
                return (symbol, timeframe, config)
            else:
                print("無効な選択です")
                return None
        except (ValueError, KeyboardInterrupt):
            print("キャンセルされました")
            return None

def main():
    """メイン実行"""
    reproducer = StrategyReproducer()
    reproducer.interactive_strategy_selection()

if __name__ == "__main__":
    main()