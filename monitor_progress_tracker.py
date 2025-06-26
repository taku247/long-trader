#!/usr/bin/env python3
"""
progress_tracker リアルタイム監視ツール
実際の分析中にprogress_trackerの更新をリアルタイムで監視
"""

import sys
import os
import time
import json
from datetime import datetime

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from web_dashboard.analysis_progress import progress_tracker
    print("✅ progress_tracker インポート成功")
except ImportError as e:
    print(f"❌ progress_tracker インポートエラー: {e}")
    sys.exit(1)

def monitor_progress():
    """progress_trackerの変化をリアルタイム監視"""
    print("🔍 progress_tracker リアルタイム監視開始")
    print("Ctrl+C で停止")
    print("=" * 80)
    
    previous_data = {}
    
    try:
        while True:
            # 最新データ取得
            recent = progress_tracker.get_all_recent(1)
            
            current_time = datetime.now().strftime("%H:%M:%S")
            
            if recent:
                latest = recent[0]
                execution_id = latest.execution_id
                
                # 変化があった場合のみ表示
                current_data = {
                    'symbol': latest.symbol,
                    'execution_id': execution_id,
                    'current_stage': latest.current_stage,
                    'overall_status': latest.overall_status,
                    'support_resistance_status': latest.support_resistance.status,
                    'support_resistance_count': f"{latest.support_resistance.supports_count}S, {latest.support_resistance.resistances_count}R",
                    'ml_prediction_status': latest.ml_prediction.status,
                    'market_context_status': latest.market_context.status,
                    'leverage_decision_status': latest.leverage_decision.status,
                    'final_signal': latest.final_signal
                }
                
                if execution_id not in previous_data or previous_data[execution_id] != current_data:
                    print(f"\n[{current_time}] 🔄 変化検出: {execution_id[:20]}...")
                    print(f"  Symbol: {current_data['symbol']}")
                    print(f"  Stage: {current_data['current_stage']} | Status: {current_data['overall_status']} | Signal: {current_data['final_signal']}")
                    print(f"  🔍 S/R: {current_data['support_resistance_status']} ({current_data['support_resistance_count']})")
                    print(f"  🤖 ML: {current_data['ml_prediction_status']}")
                    print(f"  📈 Market: {current_data['market_context_status']}")
                    print(f"  ⚖️  Leverage: {current_data['leverage_decision_status']}")
                    
                    previous_data[execution_id] = current_data
                else:
                    # 変化なしの場合は短い表示
                    print(f"[{current_time}] ⏳ 監視中: {latest.symbol} - {latest.current_stage}", end='\r')
            else:
                print(f"[{current_time}] 📭 データなし", end='\r')
            
            time.sleep(2)  # 2秒間隔で監視
            
    except KeyboardInterrupt:
        print("\n\n🛑 監視停止")

if __name__ == "__main__":
    monitor_progress()