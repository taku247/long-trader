#!/usr/bin/env python3
"""
継続的データ品質監視システム
定期的にデータ品質をチェックし、問題を早期発見
"""

import sys
import os
import time
import schedule
from datetime import datetime, timedelta
from pathlib import Path
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

from tests.test_data_quality_validation import TestDataQualityValidation
from scalable_analysis_system import ScalableAnalysisSystem


class ContinuousQualityMonitor:
    """継続的品質監視システム"""
    
    def __init__(self, config_path='quality_monitor_config.json'):
        self.config_path = config_path
        self.config = self.load_config()
        self.system = ScalableAnalysisSystem()
        self.test_suite = TestDataQualityValidation()
        self.test_suite.setUp()
        
        # 品質履歴ログ
        self.quality_log_path = 'quality_check_history.json'
        
    def load_config(self):
        """設定ファイルを読み込み"""
        default_config = {
            'check_interval_hours': 6,  # 6時間ごとにチェック
            'alert_email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'to_addresses': []
            },
            'quality_thresholds': {
                'max_acceptable_duplicates_ratio': 0.05,
                'min_leverage_diversity_threshold': 0.1,
                'min_price_diversity_threshold': 0.05,
                'max_acceptable_win_rate': 0.85,
                'min_acceptable_win_rate': 0.15
            },
            'auto_cleanup': {
                'enabled': True,
                'backup_before_cleanup': True
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                default_config.update(loaded_config)
            except Exception as e:
                print(f"⚠️ 設定ファイル読み込みエラー: {e}")
        
        return default_config
    
    def save_config(self):
        """設定ファイルを保存"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def run_quality_check(self):
        """品質チェックを実行"""
        timestamp = datetime.now()
        print(f"\n{'='*60}")
        print(f"🔍 定期品質チェック実行: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        try:
            # 包括的品質チェック実行
            success = self.test_suite.run_comprehensive_data_quality_check()
            
            # 結果をログに記録
            result_log = {
                'timestamp': timestamp.isoformat(),
                'success': success,
                'details': self.get_detailed_quality_info()
            }
            
            self.save_quality_log(result_log)
            
            if success:
                print("✅ 品質チェック合格")
                return True
            else:
                print("🚨 品質問題を検出")
                self.handle_quality_issues()
                return False
                
        except Exception as e:
            print(f"❌ 品質チェック実行エラー: {e}")
            self.save_quality_log({
                'timestamp': timestamp.isoformat(),
                'success': False,
                'error': str(e)
            })
            return False
    
    def get_detailed_quality_info(self):
        """詳細な品質情報を取得"""
        all_results = self.system.query_analyses()
        
        if all_results.empty:
            return {'total_symbols': 0, 'total_analyses': 0}
        
        symbols = all_results['symbol'].unique()
        quality_info = {
            'total_symbols': len(symbols),
            'total_analyses': len(all_results),
            'symbols_detail': {}
        }
        
        for symbol in symbols:
            trades = self.test_suite.get_trade_data_for_symbol(symbol)
            if trades:
                leverages = [float(t.get('leverage', 0)) for t in trades]
                entry_prices = [float(t.get('entry_price', 0)) for t in trades if t.get('entry_price')]
                
                quality_info['symbols_detail'][symbol] = {
                    'total_trades': len(trades),
                    'leverage_unique': len(set(leverages)),
                    'price_unique': len(set(entry_prices)) if entry_prices else 0,
                    'win_rate': sum(1 for t in trades if t.get('is_success', t.get('is_win', False))) / len(trades)
                }
        
        return quality_info
    
    def save_quality_log(self, log_entry):
        """品質チェック履歴を保存"""
        history = []
        
        if os.path.exists(self.quality_log_path):
            try:
                with open(self.quality_log_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                pass
        
        history.append(log_entry)
        
        # 最新50件のみ保持
        if len(history) > 50:
            history = history[-50:]
        
        with open(self.quality_log_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def handle_quality_issues(self):
        """品質問題への対応"""
        print("\n🔧 品質問題対応開始...")
        
        # アラート送信
        if self.config['alert_email']['enabled']:
            self.send_alert_email()
        
        # 自動クリーンアップ
        if self.config['auto_cleanup']['enabled']:
            self.perform_auto_cleanup()
    
    def send_alert_email(self):
        """アラートメールを送信"""
        try:
            email_config = self.config['alert_email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = ', '.join(email_config['to_addresses'])
            msg['Subject'] = f"🚨 Long Trader データ品質アラート - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            body = f"""
Long Trader システムでデータ品質問題が検出されました。

検出時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

詳細確認のため、以下のコマンドを実行してください:
python tests/test_data_quality_validation.py

品質監視システムより
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            
            text = msg.as_string()
            server.sendmail(email_config['username'], email_config['to_addresses'], text)
            server.quit()
            
            print("📧 アラートメール送信完了")
            
        except Exception as e:
            print(f"❌ アラートメール送信失敗: {e}")
    
    def perform_auto_cleanup(self):
        """自動クリーンアップ実行"""
        print("🧹 自動クリーンアップ実行...")
        
        try:
            # バックアップ作成
            if self.config['auto_cleanup']['backup_before_cleanup']:
                backup_path = f"large_scale_analysis/auto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                import shutil
                shutil.copy2(self.system.db_path, backup_path)
                print(f"💾 バックアップ作成: {backup_path}")
            
            # 問題データの特定と削除は手動確認を推奨
            print("⚠️ 自動削除は実装されていません。手動確認を推奨します。")
            print("次のコマンドで詳細確認:")
            print("python fix_data_quality_issues.py")
            
        except Exception as e:
            print(f"❌ 自動クリーンアップエラー: {e}")
    
    def get_quality_history(self, days=7):
        """品質チェック履歴を取得"""
        if not os.path.exists(self.quality_log_path):
            return []
        
        try:
            with open(self.quality_log_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # 指定期間の履歴のみ返す
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_history = []
            
            for entry in history:
                entry_date = datetime.fromisoformat(entry['timestamp'])
                if entry_date >= cutoff_date:
                    filtered_history.append(entry)
            
            return filtered_history
            
        except Exception as e:
            print(f"履歴取得エラー: {e}")
            return []
    
    def print_quality_summary(self):
        """品質概要を表示"""
        print("\n📊 品質チェック概要")
        print("=" * 30)
        
        recent_history = self.get_quality_history(days=7)
        
        if not recent_history:
            print("履歴データがありません")
            return
        
        total_checks = len(recent_history)
        successful_checks = sum(1 for h in recent_history if h.get('success', False))
        success_rate = (successful_checks / total_checks * 100) if total_checks > 0 else 0
        
        print(f"過去7日間の品質チェック:")
        print(f"  総チェック回数: {total_checks}")
        print(f"  成功回数: {successful_checks}")
        print(f"  成功率: {success_rate:.1f}%")
        
        if recent_history:
            latest = recent_history[-1]
            print(f"  最新チェック: {latest['timestamp']}")
            print(f"  結果: {'✅ 合格' if latest.get('success', False) else '❌ 問題検出'}")
    
    def start_continuous_monitoring(self):
        """継続的監視を開始"""
        print("🚀 継続的品質監視システム開始")
        print(f"チェック間隔: {self.config['check_interval_hours']}時間")
        print("Ctrl+C で停止")
        
        # スケジュール設定
        schedule.every(self.config['check_interval_hours']).hours.do(self.run_quality_check)
        
        # 初回実行
        self.run_quality_check()
        
        # 継続実行
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1分ごとにスケジュールチェック
        except KeyboardInterrupt:
            print("\n🛑 継続的監視を停止しました")


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='継続的データ品質監視システム')
    parser.add_argument('--once', action='store_true', help='一回のみ実行')
    parser.add_argument('--summary', action='store_true', help='品質概要表示')
    parser.add_argument('--config', action='store_true', help='設定ファイル作成')
    
    args = parser.parse_args()
    
    monitor = ContinuousQualityMonitor()
    
    if args.config:
        monitor.save_config()
        print(f"✅ 設定ファイル作成: {monitor.config_path}")
        print("設定を編集してから再実行してください")
        return
    
    if args.summary:
        monitor.print_quality_summary()
        return
    
    if args.once:
        monitor.run_quality_check()
    else:
        monitor.start_continuous_monitoring()


if __name__ == '__main__':
    main()