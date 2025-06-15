#!/usr/bin/env python3
"""
エントリー価格統一問題の修正
proper_backtesting_engine.pyの修正箇所と実装提案
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def analyze_current_issue():
    """現在の問題を詳細分析"""
    print("🔍 エントリー価格統一問題 - 詳細分析")
    print("=" * 70)
    
    print("❌ 現在の問題:")
    print("  1. proper_backtesting_engine.py:546行目")
    print("     entry_price = row['close']  # 全て同じ現在価格")
    print("  2. 全トレードで同一の現在価格をエントリー価格として使用")
    print("  3. TP/SL計算も同一のエントリー価格ベースで計算")
    print("  4. レバレッジ計算も同一条件で実行")
    
    print("\n✅ 正常な部分:")
    print("  1. exit_price（クローズ価格）は実際の市場価格を使用")
    print("  2. ハードコード値（100.0, 105.0, 97.62）は完全除去済み")
    print("  3. 実データ取得は正常に機能")

def identify_root_causes():
    """根本原因の特定"""
    print("\n🎯 根本原因の特定")
    print("=" * 70)
    
    causes = [
        {
            "file": "proper_backtesting_engine.py",
            "line": 546,
            "issue": "entry_price = row['close']",
            "description": "全てのエントリーで同じ現在価格を使用",
            "severity": "HIGH"
        },
        {
            "file": "proper_backtesting_engine.py", 
            "line": "549-552",
            "issue": "leverage計算ロジック",
            "description": "同一条件でレバレッジ計算",
            "severity": "MEDIUM"
        },
        {
            "file": "proper_backtesting_engine.py",
            "line": "559-561", 
            "issue": "TP/SL計算",
            "description": "固定比率でTP/SL計算",
            "severity": "MEDIUM"
        },
        {
            "file": "ScalableAnalysisSystem",
            "line": "全体",
            "issue": "バックテスト実行フロー",
            "description": "時系列データの処理方法",
            "severity": "MEDIUM"
        }
    ]
    
    for i, cause in enumerate(causes, 1):
        print(f"{i}. 📁 {cause['file']}:{cause['line']}")
        print(f"   ❌ 問題: {cause['issue']}")
        print(f"   📝 説明: {cause['description']}")
        print(f"   🚨 重要度: {cause['severity']}")
        print()

def propose_fixes():
    """修正提案"""
    print("💡 修正提案")
    print("=" * 70)
    
    print("🎯 主要修正:")
    print("1. **エントリー価格の多様化**")
    print("   - 現在: entry_price = row['close'] (同一値)")
    print("   - 修正: entry_price = get_realistic_entry_price(row, signal_type)")
    print("   - 実装: 次の足のopen価格 + スリッページを使用")
    print()
    
    print("2. **時系列シミュレーション**")
    print("   - 現在: 全トレードが同時実行")
    print("   - 修正: 実際の時系列順序でシミュレーション")
    print("   - 実装: Look-ahead bias防止")
    print()
    
    print("3. **リアルなTP/SL計算**")
    print("   - 現在: 固定比率計算")
    print("   - 修正: 市場状況に応じた動的計算")
    print("   - 実装: サポート/レジスタンスレベル活用")
    print()
    
    print("4. **レバレッジ多様化**")
    print("   - 現在: 同一条件でレバレッジ決定")
    print("   - 修正: 市場状況と時間に応じた動的レバレッジ")
    print("   - 実装: ボラティリティベースの調整")

def create_fix_implementation():
    """修正実装の作成"""
    print("\n🛠️ 修正実装コード")
    print("=" * 70)
    
    fix_code = '''
# proper_backtesting_engine.py の修正

def get_realistic_entry_price(self, current_row, next_row, signal_type, slippage_pct=0.001):
    """
    リアルなエントリー価格を計算
    
    Args:
        current_row: 現在の価格データ
        next_row: 次の足の価格データ  
        signal_type: シグナルタイプ (1: buy, -1: sell)
        slippage_pct: スリッページ率
    
    Returns:
        realistic_entry_price: リアルなエントリー価格
    """
    if next_row is None:
        # 最後の足の場合は現在のclose価格を使用
        base_price = current_row['close']
    else:
        # 次の足のopen価格を使用（より現実的）
        base_price = next_row['open']
    
    # スリッページを考慮
    if signal_type > 0:  # Buy signal
        slippage = base_price * slippage_pct
    else:  # Sell signal  
        slippage = -base_price * slippage_pct
        
    return base_price + slippage

def calculate_dynamic_tp_sl(self, entry_price, signal_type, market_conditions, strategy_config):
    """
    市場状況に応じた動的TP/SL計算
    
    Args:
        entry_price: エントリー価格
        signal_type: シグナルタイプ
        market_conditions: 市場状況データ
        strategy_config: 戦略設定
    
    Returns:
        (take_profit_price, stop_loss_price): TP/SL価格
    """
    base_tp_pct = strategy_config.get('take_profit', 0.10)
    base_sl_pct = strategy_config.get('stop_loss', 0.05)
    
    # ボラティリティ調整
    volatility = market_conditions.get('volatility', 1.0)
    volatility_adj = min(max(volatility / 0.02, 0.5), 2.0)  # 0.5x - 2.0x
    
    adjusted_tp_pct = base_tp_pct * volatility_adj
    adjusted_sl_pct = base_sl_pct * volatility_adj
    
    if signal_type > 0:  # Long position
        take_profit_price = entry_price * (1 + adjusted_tp_pct)
        stop_loss_price = entry_price * (1 - adjusted_sl_pct)
    else:  # Short position
        take_profit_price = entry_price * (1 - adjusted_tp_pct)
        stop_loss_price = entry_price * (1 + adjusted_sl_pct)
    
    return take_profit_price, stop_loss_price

def calculate_dynamic_leverage(self, confidence, market_conditions, strategy_config):
    """
    市場状況と信頼度に応じた動的レバレッジ計算
    
    Args:
        confidence: ML予測の信頼度
        market_conditions: 市場状況
        strategy_config: 戦略設定
    
    Returns:
        dynamic_leverage: 動的レバレッジ
    """
    base_leverage = strategy_config.get('base_leverage', 2.0)
    max_leverage = strategy_config.get('max_leverage', 5.0)
    
    # 信頼度調整
    confidence_multiplier = 1.0 + (confidence - 0.5) * 2.0  # 0.5信頼度で1.0x, 1.0信頼度で3.0x
    
    # ボラティリティ調整
    volatility = market_conditions.get('volatility', 1.0)
    volatility_penalty = max(0.5, 1.0 - (volatility - 0.02) * 10)  # 高ボラでレバレッジ減少
    
    # 時間帯調整（例：深夜は低レバレッジ）
    time_of_day = market_conditions.get('hour', 12)
    if 0 <= time_of_day <= 6 or 22 <= time_of_day <= 23:
        time_penalty = 0.7  # 深夜は30%減
    else:
        time_penalty = 1.0
    
    dynamic_leverage = base_leverage * confidence_multiplier * volatility_penalty * time_penalty
    return min(max(dynamic_leverage, 1.0), max_leverage)

# メインロジックの修正 (line 532-594)
def _convert_predictions_to_trades_fixed(self, predictions_df, strategy_config, original_data):
    """
    修正版: リアルなエントリー価格とTP/SLを使用
    """
    # ... 既存のsetup code ...
    
    for i, row in merged.iterrows():
        # ... signal generation logic ...
        
        # Position management (修正版)
        if position == 0 and signal != 0:
            # Enter position with realistic entry price
            position = signal
            
            # 次の足のデータを取得（look-ahead bias防止）
            next_row = merged.iloc[i + 1] if i + 1 < len(merged) else None
            entry_price = self.get_realistic_entry_price(row, next_row, signal)
            entry_date = row['date']
            
            # 市場状況データ準備
            market_conditions = {
                'volatility': self._calculate_volatility(merged, i),
                'hour': row['date'].hour if hasattr(row['date'], 'hour') else 12
            }
            
            # 動的レバレッジ計算
            leverage = self.calculate_dynamic_leverage(confidence, market_conditions, strategy_config)
            
            # 動的TP/SL計算
            take_profit_price, stop_loss_price = self.calculate_dynamic_tp_sl(
                entry_price, signal, market_conditions, strategy_config
            )
            
        elif position != 0:
            # Exit logic with dynamic TP/SL
            current_price = row['close']
            
            exit_signal = False
            exit_reason = ""
            
            # Dynamic TP/SL check
            if position > 0:  # Long position
                if current_price >= take_profit_price:
                    exit_signal = True
                    exit_reason = "take_profit"
                elif current_price <= stop_loss_price:
                    exit_signal = True
                    exit_reason = "stop_loss"
            else:  # Short position
                if current_price <= take_profit_price:
                    exit_signal = True
                    exit_reason = "take_profit"
                elif current_price >= stop_loss_price:
                    exit_signal = True
                    exit_reason = "stop_loss"
            
            if exit_signal:
                # Record realistic trade
                position_return = position * (current_price - entry_price) / entry_price * leverage
                
                trade = {
                    'entry_date': entry_date,
                    'exit_date': row['date'],
                    'entry_price': entry_price,  # ← リアルなエントリー価格
                    'exit_price': current_price,
                    'take_profit_price': take_profit_price,  # ← 動的TP価格
                    'stop_loss_price': stop_loss_price,      # ← 動的SL価格
                    'position': position,
                    'leverage': leverage,  # ← 動的レバレッジ
                    'return': position_return,
                    'exit_reason': exit_reason,
                    'confidence': confidence
                }
                trades.append(trade)
                
                # Reset position
                position = 0
                entry_price = 0
'''
    
    print(fix_code)

def main():
    """メイン実行関数"""
    print("🚀 エントリー価格統一問題 - 修正分析・提案")
    print("=" * 70)
    print("目的: DOTトレード結果の価格統一問題の具体的修正箇所と実装方法")
    print("=" * 70)
    
    # 1. 現在の問題分析
    analyze_current_issue()
    
    # 2. 根本原因特定
    identify_root_causes()
    
    # 3. 修正提案
    propose_fixes()
    
    # 4. 修正実装
    create_fix_implementation()
    
    # まとめ
    print("\n" + "=" * 70)
    print("📊 修正必要箇所サマリー")
    print("=" * 70)
    
    print("🎯 最優先修正:")
    print("1. proper_backtesting_engine.py:546行目")
    print("   entry_price = row['close'] → get_realistic_entry_price()")
    print()
    print("2. proper_backtesting_engine.py:549-561行目")  
    print("   固定TP/SL → 動的TP/SL計算")
    print()
    print("3. proper_backtesting_engine.py:全体")
    print("   時系列シミュレーション強化")
    
    print("\n🔧 実装アクション:")
    print("1. get_realistic_entry_price()メソッド追加")
    print("2. calculate_dynamic_tp_sl()メソッド追加") 
    print("3. calculate_dynamic_leverage()メソッド追加")
    print("4. _convert_predictions_to_trades()メソッド修正")
    print("5. 包括的テスト実装")

if __name__ == '__main__':
    main()