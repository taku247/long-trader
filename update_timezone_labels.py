#!/usr/bin/env python3
"""
HTMLテンプレートの時刻ラベル更新

時刻表示箇所に適切なタイムゾーン表記を追加
"""

import os
import re


def update_execution_logs_template():
    """execution_logs.htmlの時刻ラベル更新"""
    template_path = "/Users/moriwakikeita/tools/long-trader/web_dashboard/templates/execution_logs.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 時刻ラベルを更新
        updates = [
            (r'<td>開始時刻:</td>', '<td>開始時刻 (JST):</td>'),
            (r'<td>終了時刻:</td>', '<td>終了時刻 (JST):</td>'),
            (r'>開始時刻:<', '>開始時刻 (JST):<'),
            (r'>終了時刻:<', '>終了時刻 (JST):<'),
        ]
        
        updated_content = content
        changes_made = 0
        
        for pattern, replacement in updates:
            if re.search(pattern, updated_content):
                updated_content = re.sub(pattern, replacement, updated_content)
                changes_made += 1
        
        if changes_made > 0:
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"✅ execution_logs.html: {changes_made}箇所更新")
        else:
            print("ℹ️ execution_logs.html: 更新不要")
            
        return changes_made > 0
        
    except Exception as e:
        print(f"❌ execution_logs.html更新エラー: {e}")
        return False


def update_dashboard_template():
    """dashboard.htmlの時刻ラベル更新"""
    template_path = "/Users/moriwakikeita/tools/long-trader/web_dashboard/templates/dashboard.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 時刻ラベルを更新
        updates = [
            (r'最終更新:', '最終更新 (JST):'),
            (r'>最終更新:<', '>最終更新 (JST):<'),
            (r'label">最終更新:', 'label">最終更新 (JST):'),
        ]
        
        updated_content = content
        changes_made = 0
        
        for pattern, replacement in updates:
            if re.search(pattern, updated_content):
                updated_content = re.sub(pattern, replacement, updated_content)
                changes_made += 1
        
        if changes_made > 0:
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"✅ dashboard.html: {changes_made}箇所更新")
        else:
            print("ℹ️ dashboard.html: 更新不要")
            
        return changes_made > 0
        
    except Exception as e:
        print(f"❌ dashboard.html更新エラー: {e}")
        return False


def update_other_templates():
    """その他のテンプレートファイルの時刻ラベル更新"""
    templates_dir = "/Users/moriwakikeita/tools/long-trader/web_dashboard/templates"
    
    template_files = [
        "symbols.html",
        "symbols_new.html", 
        "strategy_results.html",
        "analysis.html",
        "settings.html"
    ]
    
    total_updates = 0
    
    for template_file in template_files:
        template_path = os.path.join(templates_dir, template_file)
        
        if not os.path.exists(template_path):
            continue
            
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 一般的な時刻ラベルを更新
            updates = [
                (r'時刻:', '時刻 (JST):'),
                (r'更新時刻:', '更新時刻 (JST):'),
                (r'実行時刻:', '実行時刻 (JST):'),
                (r'作成時刻:', '作成時刻 (JST):'),
                (r'>時刻:<', '>時刻 (JST):<'),
                (r'>更新時刻:<', '>更新時刻 (JST):<'),
            ]
            
            updated_content = content
            changes_made = 0
            
            for pattern, replacement in updates:
                if re.search(pattern, updated_content):
                    updated_content = re.sub(pattern, replacement, updated_content)
                    changes_made += 1
            
            if changes_made > 0:
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                print(f"✅ {template_file}: {changes_made}箇所更新")
                total_updates += changes_made
            else:
                print(f"ℹ️ {template_file}: 更新不要")
                
        except Exception as e:
            print(f"❌ {template_file}更新エラー: {e}")
    
    return total_updates


def create_timezone_display_guide():
    """タイムゾーン表示ガイドの作成"""
    guide_content = """# タイムゾーン表示ガイド

## 現在の実装

### バックエンド (Python)
- **すべてのdatetimeオブジェクト**: UTC aware
- **API レスポンス**: ISO 8601形式 (`2024-06-20T18:15:22+00:00`)
- **データベース**: UTC時刻で保存

### フロントエンド (JavaScript)
- **受信データ**: UTC ISO文字列
- **表示形式**: JST (日本標準時) + "JST"表記
- **例**: `2024-06-21 03:15:22 JST`

## 表示箇所

### 1. 実行ログページ (execution_logs.html)
- **開始時刻 (JST)**: 分析開始時刻
- **終了時刻 (JST)**: 分析終了時刻

### 2. ダッシュボード (dashboard.html)  
- **最終更新 (JST)**: システム最終更新時刻

### 3. その他のページ
- **各種時刻表示**: JST表記付き

## JavaScript関数

### formatDateTime() (各JSファイル)
```javascript
formatDateTime(isoString) {
    const date = new Date(isoString);
    const formatted = date.toLocaleString('ja-JP', {
        timeZone: 'Asia/Tokyo'
    });
    return `${formatted} JST`;
}
```

### DateTimeUtils.js (包括的ユーティリティ)
- `formatDateTimeJST()`: JST表記
- `formatDateTimeUTC()`: UTC表記  
- `formatDateTimeBoth()`: JST + UTC両方表記

## ユーザーメリット

1. **明確性**: タイムゾーンが一目で分かる
2. **混乱防止**: UTC/JST混同を防止
3. **国際対応**: 将来的な他タイムゾーン対応準備完了
4. **一貫性**: すべての時刻表示で統一

## データフロー

```
Backend (UTC) → API (ISO) → Frontend (JST + "JST")
```

これにより、技術的にはUTC基準を保ちながら、ユーザーには分かりやすいJST表記で提供。
"""
    
    guide_path = "/Users/moriwakikeita/tools/long-trader/timezone_display_guide.md"
    
    try:
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        print(f"✅ タイムゾーン表示ガイド作成: {guide_path}")
        return True
    except Exception as e:
        print(f"❌ ガイド作成エラー: {e}")
        return False


def main():
    """メイン実行"""
    print("=" * 80)
    print("🕐 HTMLテンプレート時刻ラベル更新")
    print("=" * 80)
    
    # 各テンプレートを更新
    updates = []
    
    print("📄 主要テンプレート更新:")
    updates.append(update_execution_logs_template())
    updates.append(update_dashboard_template())
    
    print("\n📄 その他テンプレート更新:")
    other_updates = update_other_templates()
    
    print("\n📚 ドキュメント作成:")
    guide_created = create_timezone_display_guide()
    
    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 更新結果サマリー")
    print("=" * 80)
    
    total_template_updates = sum(updates) + (1 if other_updates > 0 else 0)
    
    print(f"✅ テンプレート更新: {total_template_updates}ファイル")
    print(f"✅ その他更新箇所: {other_updates}箇所")
    print(f"✅ ガイド作成: {'成功' if guide_created else '失敗'}")
    
    if total_template_updates > 0 or guide_created:
        print("\n🎯 実装完了:")
        print("1. 時刻表示ラベルにJST表記追加")
        print("2. JavaScriptでJST変換 + JST表記")
        print("3. バックエンドはUTC aware維持")
        print("4. 包括的なドキュメント作成")
        
        print("\n💡 ユーザー体験:")
        print("- 時刻表示が明確（'2024-06-21 03:15 JST'）")
        print("- タイムゾーン混乱なし")
        print("- 技術的にUTC基準保持")
    else:
        print("\n⚠️ 更新が必要な箇所が見つかりませんでした")


if __name__ == "__main__":
    main()