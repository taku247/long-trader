# タイムゾーン表示ガイド

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
