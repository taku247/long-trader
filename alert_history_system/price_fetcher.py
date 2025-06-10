"""
価格取得・パフォーマンス計算クラス
チャート表示時にリアルタイム価格を取得してパフォーマンスを計算
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# パス追加
sys.path.append(str(Path(__file__).parent.parent))

from real_time_system.utils.colored_log import get_colored_logger


class PriceFetcher:
    """価格取得・パフォーマンス計算クラス"""
    
    def __init__(self):
        self.logger = get_colored_logger(__name__)
        
        # 既存のデータフェッチャーを使用（import）
        try:
            from test_data_fetch import fetch_ohlcv_data_hyperliquid
            self.fetch_function = fetch_ohlcv_data_hyperliquid
            self.logger.success("Using Hyperliquid data fetcher")
        except ImportError:
            self.logger.warning("Could not import Hyperliquid fetcher, using mock data")
            self.fetch_function = self._mock_price_fetcher
    
    def _mock_price_fetcher(self, symbol: str, timeframe: str = '1h', limit: int = 100):
        """モック価格データ生成"""
        import random
        from datetime import datetime, timedelta
        
        base_prices = {
            'HYPE': 25.50,
            'SOL': 145.20,
            'WIF': 2.85,
            'BONK': 0.000024,
            'PEPE': 0.000012
        }
        
        base_price = base_prices.get(symbol, 100.0)
        data = []
        
        for i in range(limit):
            timestamp = datetime.now() - timedelta(hours=limit-i)
            # ランダムな価格変動
            price_change = random.uniform(-0.05, 0.05)  # ±5%
            price = base_price * (1 + price_change)
            
            data.append({
                'timestamp': timestamp,
                'open': price * 0.99,
                'high': price * 1.02,
                'low': price * 0.98,
                'close': price,
                'volume': random.uniform(1000000, 5000000)
            })
        
        return data
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """現在価格取得"""
        try:
            # 最新の1時間足データを取得
            data = self.fetch_function(symbol, '1h', 1)
            if data and len(data) > 0:
                return float(data[-1]['close'])
            return None
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {e}")
            return None
    
    def get_price_at_time(self, symbol: str, target_time: datetime) -> Optional[float]:
        """指定時刻の価格取得（近似）"""
        try:
            # 指定時刻前後のデータを取得
            hours_diff = int((datetime.now() - target_time).total_seconds() / 3600)
            limit = min(max(hours_diff + 24, 24), 168)  # 24時間〜1週間
            
            data = self.fetch_function(symbol, '1h', limit)
            if not data:
                return None
            
            # 指定時刻に最も近いデータを検索
            closest_price = None
            min_diff = float('inf')
            
            for candle in data:
                candle_time = candle['timestamp']
                if isinstance(candle_time, str):
                    candle_time = datetime.fromisoformat(candle_time.replace('Z', '+00:00'))
                
                diff = abs((candle_time - target_time).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_price = float(candle['close'])
            
            return closest_price
        except Exception as e:
            self.logger.error(f"Failed to get price at time for {symbol}: {e}")
            return None
    
    def calculate_performance(self, entry_price: float, entry_time: datetime, symbol: str) -> Dict[str, Any]:
        """パフォーマンス計算"""
        try:
            current_price = self.get_current_price(symbol)
            if not current_price:
                return {'error': 'Could not get current price'}
            
            # 現在までの変動率
            current_change = ((current_price - entry_price) / entry_price) * 100
            
            # 経過時間
            elapsed = datetime.now() - entry_time
            elapsed_hours = elapsed.total_seconds() / 3600
            
            # 特定時点でのパフォーマンス（1時間後、3時間後、24時間後、72時間後）
            checkpoints = {}
            for hours in [1, 3, 24, 72]:
                if elapsed_hours >= hours:
                    checkpoint_time = entry_time + timedelta(hours=hours)
                    checkpoint_price = self.get_price_at_time(symbol, checkpoint_time)
                    if checkpoint_price:
                        checkpoint_change = ((checkpoint_price - entry_price) / entry_price) * 100
                        checkpoints[f'{hours}h'] = {
                            'price': checkpoint_price,
                            'change_percent': round(checkpoint_change, 2),
                            'timestamp': checkpoint_time.isoformat()
                        }
            
            # 成功判定
            is_success = False
            success_reason = ""
            
            if '24h' in checkpoints and checkpoints['24h']['change_percent'] >= 5.0:
                is_success = True
                success_reason = "24時間後に+5%達成"
            elif '72h' in checkpoints and checkpoints['72h']['change_percent'] >= 10.0:
                is_success = True
                success_reason = "72時間後に+10%達成"
            elif current_change >= 15.0:
                is_success = True
                success_reason = "現在+15%以上"
            
            return {
                'entry_price': entry_price,
                'current_price': current_price,
                'current_change_percent': round(current_change, 2),
                'elapsed_hours': round(elapsed_hours, 1),
                'checkpoints': checkpoints,
                'is_success': is_success,
                'success_reason': success_reason,
                'max_gain': round(max([cp['change_percent'] for cp in checkpoints.values()] + [current_change], default=current_change), 2),
                'min_loss': round(min([cp['change_percent'] for cp in checkpoints.values()] + [current_change], default=current_change), 2)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate performance: {e}")
            return {'error': str(e)}
    
    def get_chart_data_with_prices(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """チャート表示用の価格データ取得"""
        try:
            # 指定期間の価格データを取得
            limit = days * 24  # 1時間足×24×日数
            data = self.fetch_function(symbol, '1h', limit)
            
            if not data:
                return []
            
            chart_data = []
            for candle in data:
                chart_data.append({
                    'timestamp': candle['timestamp'].isoformat() if isinstance(candle['timestamp'], datetime) else candle['timestamp'],
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': float(candle['volume'])
                })
            
            return chart_data
            
        except Exception as e:
            self.logger.error(f"Failed to get chart data: {e}")
            return []


# 使用例
if __name__ == "__main__":
    fetcher = PriceFetcher()
    
    # 現在価格テスト
    current_price = fetcher.get_current_price('HYPE')
    print(f"Current HYPE price: ${current_price}")
    
    # パフォーマンス計算テスト
    entry_time = datetime.now() - timedelta(hours=25)  # 25時間前
    performance = fetcher.calculate_performance(25.50, entry_time, 'HYPE')
    print(f"Performance: {json.dumps(performance, indent=2)}")
    
    # チャートデータテスト
    chart_data = fetcher.get_chart_data_with_prices('HYPE', 7)
    print(f"Chart data points: {len(chart_data)}")