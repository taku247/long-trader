#!/usr/bin/env python3
"""
Test the trade details API directly
"""
import sys
sys.path.append('.')

from scalable_analysis_system import ScalableAnalysisSystem
import json

def test_trade_details():
    """Test loading and formatting trade details"""
    system = ScalableAnalysisSystem()
    
    # Load trade data
    trades_data = system.load_compressed_trades('SOL', '3m', 'Aggressive_Traditional')
    
    if not trades_data:
        print("❌ No trade data found")
        return
    
    print(f"✅ Loaded {len(trades_data)} trades")
    
    # Format trade details like the API would
    formatted_trades = []
    for i, trade in enumerate(trades_data):
        entry_price = trade.get('entry_price')
        exit_price = trade.get('exit_price')
        leverage = float(trade.get('leverage', 0))
        
        # Calculate take profit and stop loss based on strategy
        take_profit_price = None
        stop_loss_price = None
        
        if entry_price is not None:
            entry_price = float(entry_price)
            
            # Aggressive strategy: 3% target, 1.5% stop
            tp_pct = 0.03 * leverage
            sl_pct = 0.015 * leverage
            
            take_profit_price = entry_price * (1 + tp_pct)
            stop_loss_price = entry_price * (1 - sl_pct)
        
        formatted_trade = {
            'entry_time': trade.get('entry_time', 'N/A'),
            'exit_time': trade.get('exit_time', 'N/A'),
            'entry_price': entry_price,
            'exit_price': float(exit_price) if exit_price is not None else None,
            'take_profit_price': take_profit_price,
            'stop_loss_price': stop_loss_price,
            'leverage': leverage,
            'pnl_pct': float(trade.get('pnl_pct', 0)),
            'is_success': bool(trade.get('is_success', trade.get('is_win', False))),
            'confidence': float(trade.get('confidence', 0)),
            'strategy': trade.get('strategy', 'Aggressive_Traditional')
        }
        formatted_trades.append(formatted_trade)
        
        if i < 3:  # Show first 3 trades
            print(f"\n📊 Trade {i+1}:")
            for key, value in formatted_trade.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
    
    # Save as JSON for testing
    with open('test_trades.json', 'w') as f:
        json.dump(formatted_trades, f, indent=2, default=str)
    
    print(f"\n✅ Saved {len(formatted_trades)} formatted trades to test_trades.json")

if __name__ == '__main__':
    test_trade_details()