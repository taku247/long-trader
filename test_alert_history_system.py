#!/usr/bin/env python3
"""
アラート履歴システムのテストスクリプト
サンプルデータを生成してシステムの動作確認を行う
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from alert_history_system.alert_db_writer import AlertDBWriter
from alert_history_system.price_fetcher import PriceFetcher
from real_time_system.utils.colored_log import get_colored_logger, print_banner, print_success, print_info


def generate_sample_alerts(db_writer: AlertDBWriter, count: int = 20):
    """サンプルアラートデータ生成"""
    logger = get_colored_logger("sample_generator")
    
    symbols = ['HYPE', 'SOL', 'PEPE', 'WIF', 'BONK']
    strategies = ['Conservative_ML', 'Aggressive_Traditional', 'Full_ML']
    timeframes = ['1h', '3h', '15m', '30m']
    
    base_prices = {
        'HYPE': 25.50,
        'SOL': 145.20,
        'PEPE': 0.000012,
        'WIF': 2.85,
        'BONK': 0.000024
    }
    
    logger.info(f"Generating {count} sample alerts...")
    
    for i in range(count):
        symbol = random.choice(symbols)
        strategy = random.choice(strategies)
        timeframe = random.choice(timeframes)
        
        # ランダムな過去の日時（過去30日以内）
        days_ago = random.randint(1, 30)
        hours_ago = random.randint(0, 23)
        timestamp = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
        
        # レバレッジと信頼度の生成
        leverage = random.uniform(5.0, 30.0)
        confidence = random.uniform(60.0, 95.0)
        
        # 価格情報
        base_price = base_prices[symbol]
        price_variation = random.uniform(0.8, 1.2)
        entry_price = base_price * price_variation
        target_price = entry_price * random.uniform(1.05, 1.25)
        stop_loss = entry_price * random.uniform(0.85, 0.95)
        
        alert_data = {
            'alert_id': f'test_{symbol}_{strategy}_{timestamp.strftime("%Y%m%d_%H%M%S")}_{i:03d}',
            'symbol': symbol,
            'leverage': round(leverage, 1),
            'confidence': round(confidence, 1),
            'strategy': strategy,
            'timeframe': timeframe,
            'timestamp': timestamp,
            'metadata': {
                'entry_price': round(entry_price, 6),
                'target_price': round(target_price, 6),
                'stop_loss': round(stop_loss, 6),
                'test_data': True,
                'generation_time': datetime.now().isoformat()
            }
        }
        
        success = db_writer.save_trading_opportunity_alert(alert_data)
        if success:
            logger.success(f"Sample alert {i+1}/{count} saved: {symbol} - {leverage:.1f}x")
        else:
            logger.error(f"Failed to save sample alert {i+1}")
    
    logger.info("Sample alert generation completed")


def test_price_fetcher():
    """価格取得機能のテスト"""
    logger = get_colored_logger("price_test")
    
    logger.info("Testing price fetcher...")
    fetcher = PriceFetcher()
    
    symbols = ['HYPE', 'SOL']
    for symbol in symbols:
        current_price = fetcher.get_current_price(symbol)
        logger.info(f"{symbol} current price: ${current_price}")
        
        # パフォーマンス計算テスト
        entry_time = datetime.now() - timedelta(hours=25)
        entry_price = current_price * 0.95 if current_price else 100.0
        
        performance = fetcher.calculate_performance(entry_price, entry_time, symbol)
        if 'error' not in performance:
            logger.success(f"{symbol} performance test passed: {performance['current_change_percent']}%")
        else:
            logger.warning(f"{symbol} performance test failed: {performance['error']}")


def test_database_queries(db_writer: AlertDBWriter):
    """データベースクエリのテスト"""
    logger = get_colored_logger("db_test")
    
    logger.info("Testing database queries...")
    
    # 銘柄別アラート取得
    for symbol in ['HYPE', 'SOL']:
        alerts = db_writer.db.get_alerts_by_symbol(symbol, 5)
        logger.info(f"{symbol} alerts count: {len(alerts)}")
    
    # 統計情報取得
    stats = db_writer.get_statistics()
    logger.info(f"Overall statistics: {stats}")
    
    # HYPE専用統計
    hype_stats = db_writer.get_statistics('HYPE')
    logger.info(f"HYPE statistics: {hype_stats}")
    
    # チャートデータ取得
    chart_data = db_writer.get_chart_data('HYPE', 7)
    logger.info(f"HYPE chart data points: {len(chart_data)}")


def test_web_endpoints():
    """Web API エンドポイントのテスト"""
    logger = get_colored_logger("web_test")
    
    try:
        import requests
        
        base_url = "http://localhost:5001"
        endpoints = [
            "/api/analysis/chart-data?symbol=HYPE&days=30",
            "/api/analysis/alerts?symbol=HYPE&days=30",
            "/api/analysis/statistics?symbol=HYPE"
        ]
        
        logger.info("Testing web endpoints...")
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    logger.success(f"✅ {endpoint}: {len(data) if isinstance(data, list) else 'OK'}")
                else:
                    logger.warning(f"⚠️ {endpoint}: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"❌ {endpoint}: Connection failed - {e}")
    
    except ImportError:
        logger.warning("requests library not available, skipping web endpoint tests")


def main():
    """メインテスト実行"""
    print_banner("ALERT HISTORY SYSTEM TEST", "Testing Database Integration and Analysis Features")
    
    logger = get_colored_logger("main_test")
    
    try:
        # データベース初期化
        logger.info("Initializing database...")
        db_writer = AlertDBWriter()
        
        # 接続テスト
        if not db_writer.test_connection():
            logger.error("Database connection test failed")
            return
        
        print_success("Database connection successful")
        
        # サンプルデータ生成
        print_info("Generating sample data...")
        generate_sample_alerts(db_writer, 25)
        
        # 価格取得テスト
        print_info("Testing price fetcher...")
        test_price_fetcher()
        
        # データベースクエリテスト
        print_info("Testing database queries...")
        test_database_queries(db_writer)
        
        # Web エンドポイントテスト
        print_info("Testing web endpoints...")
        test_web_endpoints()
        
        print_success("All tests completed!")
        
        print_info("Next steps:")
        print("  1. Start web dashboard: python demo_dashboard.py")
        print("  2. Visit analysis page: http://localhost:5001/analysis")
        print("  3. Check generated sample data in charts")
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        raise


if __name__ == "__main__":
    main()