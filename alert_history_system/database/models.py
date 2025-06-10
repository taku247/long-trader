"""
データベースモデル定義
アラート履歴、価格追跡、パフォーマンス統計のテーブル
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()


class Alert(Base):
    """アラート情報テーブル"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(255), unique=True, nullable=False)
    symbol = Column(String(10), nullable=False)
    alert_type = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    leverage = Column(Float)
    confidence = Column(Float)
    strategy = Column(String(50))
    timeframe = Column(String(10))
    entry_price = Column(Float)
    target_price = Column(Float)
    stop_loss = Column(Float)
    extra_data = Column(Text)  # JSON形式
    
    # リレーション
    price_tracking = relationship("PriceTracking", back_populates="alert", cascade="all, delete-orphan")
    performance = relationship("PerformanceSummary", back_populates="alert", uselist=False, cascade="all, delete-orphan")
    
    def set_extra_data(self, data_dict):
        """追加データをJSON文字列として保存"""
        self.extra_data = json.dumps(data_dict, ensure_ascii=False)
    
    def get_extra_data(self):
        """追加データをディクショナリとして取得"""
        if self.extra_data:
            return json.loads(self.extra_data)
        return {}
    
    def __repr__(self):
        return f"<Alert(id={self.id}, symbol={self.symbol}, leverage={self.leverage}, timestamp={self.timestamp})>"


class PriceTracking(Base):
    """価格追跡テーブル"""
    __tablename__ = 'price_tracking'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(255), ForeignKey('alerts.alert_id'), nullable=False)
    symbol = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    price = Column(Float, nullable=False)
    time_elapsed_hours = Column(Integer, nullable=False)  # アラートからの経過時間
    percentage_change = Column(Float, nullable=False)  # アラート時からの変動率
    
    # リレーション
    alert = relationship("Alert", back_populates="price_tracking")
    
    def __repr__(self):
        return f"<PriceTracking(alert_id={self.alert_id}, price={self.price}, change={self.percentage_change}%)>"


class PerformanceSummary(Base):
    """パフォーマンス統計テーブル"""
    __tablename__ = 'performance_summary'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(255), ForeignKey('alerts.alert_id'), nullable=False)
    symbol = Column(String(10), nullable=False)
    is_success = Column(Boolean)  # 成功/失敗判定
    max_gain = Column(Float)  # 最大利益率
    max_loss = Column(Float)  # 最大損失率
    final_return_24h = Column(Float)  # 24時間後リターン
    final_return_72h = Column(Float)  # 72時間後リターン
    evaluation_note = Column(Text)  # 評価コメント
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # リレーション
    alert = relationship("Alert", back_populates="performance")
    
    def calculate_success(self):
        """成功判定ロジック"""
        # 24時間後に+5%以上、または72時間後に+10%以上で成功とする
        if self.final_return_24h and self.final_return_24h >= 5.0:
            return True
        if self.final_return_72h and self.final_return_72h >= 10.0:
            return True
        return False
    
    def update_success_status(self):
        """成功状態を更新"""
        self.is_success = self.calculate_success()
    
    def __repr__(self):
        return f"<PerformanceSummary(alert_id={self.alert_id}, success={self.is_success}, 24h={self.final_return_24h}%)>"


class AlertHistoryDatabase:
    """アラート履歴データベース管理クラス"""
    
    def __init__(self, db_path: str = "alert_history.db"):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.create_tables()
    
    def create_tables(self):
        """テーブル作成"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """セッション取得"""
        return self.SessionLocal()
    
    def add_alert(self, alert_data: dict) -> Alert:
        """アラート追加"""
        session = self.get_session()
        try:
            alert = Alert(
                alert_id=alert_data.get('alert_id'),
                symbol=alert_data.get('symbol'),
                alert_type=alert_data.get('alert_type'),
                priority=alert_data.get('priority'),
                timestamp=alert_data.get('timestamp', datetime.now()),
                leverage=alert_data.get('leverage'),
                confidence=alert_data.get('confidence'),
                strategy=alert_data.get('strategy'),
                timeframe=alert_data.get('timeframe'),
                entry_price=alert_data.get('entry_price'),
                target_price=alert_data.get('target_price'),
                stop_loss=alert_data.get('stop_loss')
            )
            
            if alert_data.get('metadata'):
                alert.set_extra_data(alert_data['metadata'])
            
            session.add(alert)
            session.commit()
            session.refresh(alert)
            return alert
        finally:
            session.close()
    
    def add_price_tracking(self, alert_id: str, symbol: str, price: float, 
                          time_elapsed_hours: int, entry_price: float) -> PriceTracking:
        """価格追跡データ追加"""
        session = self.get_session()
        try:
            percentage_change = ((price - entry_price) / entry_price) * 100
            
            tracking = PriceTracking(
                alert_id=alert_id,
                symbol=symbol,
                price=price,
                time_elapsed_hours=time_elapsed_hours,
                percentage_change=percentage_change
            )
            
            session.add(tracking)
            session.commit()
            session.refresh(tracking)
            return tracking
        finally:
            session.close()
    
    def update_performance_summary(self, alert_id: str) -> PerformanceSummary:
        """パフォーマンス統計更新"""
        session = self.get_session()
        try:
            # 既存のパフォーマンス統計取得または作成
            performance = session.query(PerformanceSummary).filter_by(alert_id=alert_id).first()
            if not performance:
                alert = session.query(Alert).filter_by(alert_id=alert_id).first()
                if not alert:
                    raise ValueError(f"Alert {alert_id} not found")
                
                performance = PerformanceSummary(
                    alert_id=alert_id,
                    symbol=alert.symbol
                )
                session.add(performance)
            
            # 価格追跡データから統計計算
            tracking_data = session.query(PriceTracking).filter_by(alert_id=alert_id).all()
            
            if tracking_data:
                changes = [t.percentage_change for t in tracking_data]
                performance.max_gain = max(changes) if changes else 0
                performance.max_loss = min(changes) if changes else 0
                
                # 24時間後と72時間後のリターン
                for track in tracking_data:
                    if track.time_elapsed_hours == 24:
                        performance.final_return_24h = track.percentage_change
                    elif track.time_elapsed_hours == 72:
                        performance.final_return_72h = track.percentage_change
                
                # 成功判定
                performance.update_success_status()
            
            session.commit()
            session.refresh(performance)
            return performance
        finally:
            session.close()
    
    def get_alerts_by_symbol(self, symbol: str, limit: int = 100):
        """銘柄別アラート取得"""
        session = self.get_session()
        try:
            return session.query(Alert).filter_by(symbol=symbol).order_by(Alert.timestamp.desc()).limit(limit).all()
        finally:
            session.close()
    
    def get_alert_statistics(self, symbol: str = None):
        """統計情報取得"""
        session = self.get_session()
        try:
            query = session.query(PerformanceSummary)
            if symbol:
                query = query.filter_by(symbol=symbol)
            
            summaries = query.all()
            
            if not summaries:
                return {
                    'total_alerts': 0,
                    'success_rate': 0,
                    'average_return_24h': 0,
                    'average_return_72h': 0,
                    'max_gain': 0,
                    'max_loss': 0
                }
            
            total = len(summaries)
            successes = len([s for s in summaries if s.is_success])
            
            returns_24h = [s.final_return_24h for s in summaries if s.final_return_24h is not None]
            returns_72h = [s.final_return_72h for s in summaries if s.final_return_72h is not None]
            
            return {
                'total_alerts': total,
                'success_rate': (successes / total * 100) if total > 0 else 0,
                'average_return_24h': sum(returns_24h) / len(returns_24h) if returns_24h else 0,
                'average_return_72h': sum(returns_72h) / len(returns_72h) if returns_72h else 0,
                'max_gain': max([s.max_gain for s in summaries if s.max_gain]) if summaries else 0,
                'max_loss': min([s.max_loss for s in summaries if s.max_loss]) if summaries else 0
            }
        finally:
            session.close()
    
    def get_chart_data(self, symbol: str, days: int = 30):
        """チャート表示用データ取得"""
        session = self.get_session()
        try:
            from datetime import timedelta
            start_date = datetime.now() - timedelta(days=days)
            
            alerts = session.query(Alert).filter(
                Alert.symbol == symbol,
                Alert.timestamp >= start_date
            ).order_by(Alert.timestamp).all()
            
            chart_data = []
            for alert in alerts:
                chart_data.append({
                    'alert_id': alert.alert_id,
                    'timestamp': alert.timestamp.isoformat(),
                    'price': alert.entry_price,
                    'leverage': alert.leverage,
                    'confidence': alert.confidence,
                    'strategy': alert.strategy,
                    'performance': alert.performance.final_return_72h if alert.performance else None,
                    'is_success': alert.performance.is_success if alert.performance else None
                })
            
            return chart_data
        finally:
            session.close()