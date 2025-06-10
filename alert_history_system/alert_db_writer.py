"""
アラートデータベース書き込みクラス
Alert Managerからのフックを受けてデータベースに保存
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# パス追加
sys.path.append(str(Path(__file__).parent.parent))

from alert_history_system.database.models import AlertHistoryDatabase
from real_time_system.utils.colored_log import get_colored_logger


class AlertDBWriter:
    """アラートデータベース書き込みクラス"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "alert_history.db"
            
        # データディレクトリ作成
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self.db = AlertHistoryDatabase(str(db_path))
        self.logger = get_colored_logger(__name__)
        
        self.logger.info(f"Alert DB Writer initialized: {db_path}")
    
    def save_trading_opportunity_alert(self, alert_data: Dict[str, Any]) -> bool:
        """取引機会アラートを保存"""
        try:
            # アラートデータの変換
            db_alert_data = {
                'alert_id': alert_data.get('alert_id'),
                'symbol': alert_data.get('symbol'),
                'alert_type': 'trading_opportunity',
                'priority': alert_data.get('priority', {}).value if hasattr(alert_data.get('priority'), 'value') else str(alert_data.get('priority')),
                'timestamp': alert_data.get('timestamp') or datetime.now(),
                'leverage': alert_data.get('leverage'),
                'confidence': alert_data.get('confidence'),
                'strategy': alert_data.get('strategy'),
                'timeframe': alert_data.get('timeframe'),
                'entry_price': self._extract_price_from_metadata(alert_data.get('metadata', {}), 'entry_price'),
                'target_price': self._extract_price_from_metadata(alert_data.get('metadata', {}), 'target_price'),
                'stop_loss': self._extract_price_from_metadata(alert_data.get('metadata', {}), 'stop_loss'),
                'metadata': alert_data.get('metadata', {})
            }
            
            # データベースに保存
            alert = self.db.add_alert(db_alert_data)
            
            self.logger.success(f"Alert saved to DB: {alert.symbol} - {alert.leverage}x leverage")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save alert to DB: {e}")
            return False
    
    def _extract_price_from_metadata(self, metadata: Dict[str, Any], key: str) -> float:
        """メタデータから価格情報を抽出"""
        try:
            # メタデータから直接取得
            if key in metadata:
                return float(metadata[key])
            
            # 一般的なキー名で検索
            price_keys = {
                'entry_price': ['current_price', 'price', 'entry'],
                'target_price': ['target', 'target_price', 'take_profit'],
                'stop_loss': ['stop_loss', 'sl', 'stop']
            }
            
            for alt_key in price_keys.get(key, []):
                if alt_key in metadata:
                    return float(metadata[alt_key])
            
            return None
            
        except (ValueError, TypeError):
            return None
    
    def get_active_alerts_for_tracking(self):
        """価格追跡対象のアクティブアラート取得"""
        try:
            # 過去72時間以内のアラートを取得
            from datetime import timedelta
            
            session = self.db.get_session()
            try:
                from alert_history_system.database.models import Alert, PriceTracking
                
                # 72時間以内のアラートで、まだ完全な追跡が終わっていないもの
                cutoff_time = datetime.now() - timedelta(hours=72)
                
                alerts = session.query(Alert).filter(
                    Alert.timestamp >= cutoff_time,
                    Alert.alert_type == 'trading_opportunity'
                ).all()
                
                active_alerts = []
                for alert in alerts:
                    # 追跡データの確認
                    tracking_count = session.query(PriceTracking).filter_by(alert_id=alert.alert_id).count()
                    
                    # 追跡が不完全な場合（72時間分の追跡がない）
                    if tracking_count < 4:  # 1h, 3h, 24h, 72h
                        active_alerts.append({
                            'alert_id': alert.alert_id,
                            'symbol': alert.symbol,
                            'entry_price': alert.entry_price,
                            'timestamp': alert.timestamp
                        })
                
                return active_alerts
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to get active alerts: {e}")
            return []
    
    def save_price_tracking(self, alert_id: str, symbol: str, price: float, 
                          time_elapsed_hours: int, entry_price: float) -> bool:
        """価格追跡データ保存"""
        try:
            tracking = self.db.add_price_tracking(
                alert_id=alert_id,
                symbol=symbol,
                price=price,
                time_elapsed_hours=time_elapsed_hours,
                entry_price=entry_price
            )
            
            self.logger.info(f"Price tracking saved: {symbol} - {time_elapsed_hours}h - {tracking.percentage_change:.2f}%")
            
            # パフォーマンス統計更新
            self.db.update_performance_summary(alert_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save price tracking: {e}")
            return False
    
    def get_statistics(self, symbol: str = None):
        """統計情報取得"""
        try:
            return self.db.get_alert_statistics(symbol)
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def get_chart_data(self, symbol: str, days: int = 30):
        """チャート表示用データ取得"""
        try:
            return self.db.get_chart_data(symbol, days)
        except Exception as e:
            self.logger.error(f"Failed to get chart data: {e}")
            return []
    
    def test_connection(self) -> bool:
        """データベース接続テスト"""
        try:
            session = self.db.get_session()
            session.close()
            self.logger.success("Database connection test passed")
            return True
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")
            return False


# 使用例
if __name__ == "__main__":
    # テスト実行
    writer = AlertDBWriter()
    
    # 接続テスト
    if writer.test_connection():
        print("✅ Database connection successful")
        
        # テストアラート作成
        test_alert = {
            'alert_id': f'test_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'symbol': 'HYPE',
            'leverage': 15.2,
            'confidence': 82.1,
            'strategy': 'Conservative_ML',
            'timeframe': '1h',
            'metadata': {
                'entry_price': 25.50,
                'target_price': 29.40,
                'stop_loss': 23.20
            }
        }
        
        # 保存テスト
        if writer.save_trading_opportunity_alert(test_alert):
            print("✅ Test alert saved successfully")
            
            # 統計テスト
            stats = writer.get_statistics('HYPE')
            print(f"📊 Statistics: {stats}")
        else:
            print("❌ Failed to save test alert")
    else:
        print("❌ Database connection failed")