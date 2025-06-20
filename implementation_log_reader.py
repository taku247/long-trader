#!/usr/bin/env python3
"""
実装ログ読み込みシステム

_docs/ ディレクトリの実装ログを読み込んで、システム起動時に
過去の実装内容を把握・表示する機能を提供
"""

import os
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import re

from real_time_system.utils.colored_log import get_colored_logger


class ImplementationLogReader:
    """実装ログ読み込み・表示システム"""
    
    def __init__(self, docs_dir: str = "_docs"):
        self.docs_dir = Path(docs_dir)
        self.logger = get_colored_logger(__name__)
        
    def read_all_logs(self) -> List[Dict]:
        """全ての実装ログを読み込み"""
        logs = []
        
        if not self.docs_dir.exists():
            self.logger.warning(f"📁 実装ログディレクトリが見つかりません: {self.docs_dir}")
            return logs
        
        # yyyy-mm-dd_機能名.md パターンのファイルを検索
        pattern = str(self.docs_dir / "*-*-*_*.md")
        log_files = glob.glob(pattern)
        
        for log_file in sorted(log_files):
            try:
                log_info = self._parse_log_file(log_file)
                if log_info:
                    logs.append(log_info)
            except Exception as e:
                self.logger.warning(f"📄 ログファイル読み込みエラー {log_file}: {e}")
        
        return logs
    
    def _parse_log_file(self, file_path: str) -> Optional[Dict]:
        """個別ログファイルを解析"""
        file_name = Path(file_path).name
        
        # ファイル名から日付と機能名を抽出
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(.+)\.md$', file_name)
        if not match:
            return None
        
        date_str, feature_name = match.groups()
        feature_name = feature_name.replace('-', ' ').replace('_', ' ')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # メタデータ抽出
            metadata = self._extract_metadata(content)
            
            return {
                'file_path': file_path,
                'date': date_str,
                'feature_name': feature_name,
                'title': metadata.get('title', feature_name),
                'status': metadata.get('status', 'unknown'),
                'summary': metadata.get('summary', ''),
                'content': content,
                'file_size': len(content)
            }
            
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー {file_path}: {e}")
            return None
    
    def _extract_metadata(self, content: str) -> Dict:
        """Markdownコンテンツからメタデータを抽出"""
        metadata = {}
        
        # タイトル抽出（最初の#）
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1)
        
        # ステータス抽出
        status_match = re.search(r'\*\*ステータス\*\*:\s*(.+)$', content, re.MULTILINE)
        if status_match:
            metadata['status'] = status_match.group(1)
        
        # サマリー抽出（問題の背景セクション）
        summary_match = re.search(r'## 問題の背景\s*\n\s*### 発生していた問題\s*\n-?\s*(.+?)(?=\n\n|\n###|\n##|$)', content, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
            # 改行を削除して簡潔にする
            summary = re.sub(r'\n+', ' ', summary)
            metadata['summary'] = summary[:200] + '...' if len(summary) > 200 else summary
        
        return metadata
    
    def display_startup_summary(self) -> None:
        """起動時サマリーを表示"""
        self.logger.info("📚 過去の実装ログを読み込み中...")
        
        logs = self.read_all_logs()
        
        if not logs:
            self.logger.info("📄 実装ログが見つかりませんでした")
            return
        
        print("\n" + "=" * 80)
        print("📋 実装履歴サマリー")
        print("=" * 80)
        
        # 最新5件を表示
        recent_logs = logs[-5:] if len(logs) > 5 else logs
        
        for i, log in enumerate(recent_logs, 1):
            status_emoji = self._get_status_emoji(log['status'])
            print(f"\n{i}. {status_emoji} {log['title']}")
            print(f"   📅 実装日: {log['date']}")
            print(f"   📝 機能: {log['feature_name']}")
            if log['summary']:
                print(f"   💡 概要: {log['summary']}")
        
        if len(logs) > 5:
            print(f"\n   ... 他 {len(logs) - 5} 件の実装ログがあります")
        
        print(f"\n📊 総実装数: {len(logs)} 件")
        print(f"📁 ログディレクトリ: {self.docs_dir}")
        print("=" * 80)
    
    def _get_status_emoji(self, status: str) -> str:
        """ステータスに応じた絵文字を返す"""
        status_lower = status.lower()
        if '完了' in status_lower or 'complete' in status_lower or '稼働' in status_lower:
            return '✅'
        elif '進行' in status_lower or 'progress' in status_lower:
            return '🚧'
        elif 'テスト' in status_lower or 'test' in status_lower:
            return '🧪'
        elif 'レビュー' in status_lower or 'review' in status_lower:
            return '👀'
        else:
            return '📄'
    
    def find_logs_by_keyword(self, keyword: str) -> List[Dict]:
        """キーワードで実装ログを検索"""
        logs = self.read_all_logs()
        
        matching_logs = []
        for log in logs:
            if (keyword.lower() in log['feature_name'].lower() or
                keyword.lower() in log['title'].lower() or
                keyword.lower() in log['content'].lower()):
                matching_logs.append(log)
        
        return matching_logs
    
    def get_recent_implementations(self, days: int = 7) -> List[Dict]:
        """最近N日以内の実装を取得"""
        logs = self.read_all_logs()
        recent_logs = []
        
        today = datetime.now()
        
        for log in logs:
            try:
                log_date = datetime.strptime(log['date'], '%Y-%m-%d')
                if (today - log_date).days <= days:
                    recent_logs.append(log)
            except ValueError:
                continue
        
        return sorted(recent_logs, key=lambda x: x['date'], reverse=True)


def load_implementation_context():
    """システム起動時に実装コンテキストを読み込み"""
    reader = ImplementationLogReader()
    reader.display_startup_summary()
    
    # 最近の実装をコンテキストとして返す
    recent_logs = reader.get_recent_implementations(days=30)
    
    context = {
        'total_implementations': len(reader.read_all_logs()),
        'recent_implementations': len(recent_logs),
        'latest_features': [log['feature_name'] for log in recent_logs[:3]],
        'docs_directory': str(reader.docs_dir),
        'reader_instance': reader
    }
    
    return context


# 使用例・テスト関数
def demo_usage():
    """使用例のデモ"""
    print("🔍 実装ログリーダー デモ")
    print("=" * 50)
    
    reader = ImplementationLogReader()
    
    # 1. 全ログ表示
    print("\n1. 起動時サマリー表示:")
    reader.display_startup_summary()
    
    # 2. キーワード検索
    print("\n2. キーワード検索（'early'）:")
    early_logs = reader.find_logs_by_keyword('early')
    for log in early_logs:
        print(f"   📄 {log['title']} ({log['date']})")
    
    # 3. 最近の実装
    print("\n3. 最近7日間の実装:")
    recent = reader.get_recent_implementations(7)
    for log in recent:
        print(f"   🕒 {log['date']}: {log['feature_name']}")
    
    # 4. コンテキスト読み込み
    print("\n4. コンテキスト読み込み:")
    context = load_implementation_context()
    print(f"   総実装数: {context['total_implementations']}")
    print(f"   最近の実装: {context['recent_implementations']}")
    print(f"   最新機能: {context['latest_features']}")


if __name__ == "__main__":
    demo_usage()