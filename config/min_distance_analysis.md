# 最小距離制限（0.5%）の影響分析

## 現在の設定
- **min_distance_from_current_price_pct**: 0.5%
- 現在価格から0.5%以内のサポート・レジスタンスレベルは無視

## メリット
1. **ノイズ除去**: 短期的な価格変動による意味のないレベルを除外
2. **SL/TP計算の安定性**: 現在価格に近すぎるレベルによる計算エラーを防止
3. **取引コスト考慮**: 0.5%未満では手数料を考慮すると利益が出にくい

## デメリット（リスク）
1. **直近の強い抵抗線を見逃す**
   - 0.3-0.5%上に強い売り圧力がある場合、それを無視して上位目標を設定
   - 結果として、直近抵抗で反落するリスク

2. **スキャルピング機会の喪失**
   - 短期トレーダーにとっては0.3-0.5%でも十分な利益機会
   
3. **相場の天井圏での問題**
   - 抵抗線が密集している場合、有効なレベルが見つからない可能性

## 推奨される改善案

### 1. 動的な最小距離設定
```json
{
  "min_distance_settings": {
    "base_distance_pct": 0.5,
    "adjustments": {
      "high_volatility": 0.3,    // ボラティリティが高い場合は縮小
      "low_volatility": 0.7,     // ボラティリティが低い場合は拡大
      "scalping_mode": 0.2,      // スキャルピングモード
      "swing_mode": 1.0          // スイングトレードモード
    }
  }
}
```

### 2. レベル強度による例外処理
```json
{
  "strength_based_exceptions": {
    "enabled": true,
    "min_strength_for_exception": 0.8,  // 強度0.8以上なら0.5%以内でも考慮
    "min_touch_count_for_exception": 5   // 5回以上タッチなら例外
  }
}
```

### 3. 段階的な利確設定
```json
{
  "tiered_take_profit": {
    "enabled": true,
    "tiers": [
      {"distance_pct": 0.3, "position_pct": 30},  // 0.3%で30%利確
      {"distance_pct": 0.7, "position_pct": 50},  // 0.7%で50%利確
      {"distance_pct": 1.5, "position_pct": 20}   // 1.5%で残り利確
    ]
  }
}
```

## 実装優先度
1. **高**: レベル強度による例外処理（強い抵抗線は距離に関わらず考慮）
2. **中**: ボラティリティベースの動的調整
3. **低**: 段階的利確システム

## テスト項目
1. 0.5%以内に強い抵抗線がある銘柄でのバックテスト
2. 異なる最小距離設定での収益性比較
3. ボラティリティ別の最適な最小距離の検証