"""
╔════════════════════════════════════════════════════════════════════════════════════════════════╗
║                 Hyperliquid 仮想通貨データ取得・特徴量エンジニアリングスクリプト               ║
╚════════════════════════════════════════════════════════════════════════════════════════════════╝

【概要】
このスクリプトは、Hyperliquid取引所から仮想通貨の価格データを取得し、
機械学習用の特徴量を生成・選択するための包括的なデータ前処理を行います。

【主要機能】
1. OHLCVデータ取得
   - 直近90日分の価格データを1時間足で取得
   - 取得項目: タイムスタンプ、始値、高値、安値、終値、出来高、取引回数

2. 技術的指標（特徴量）の計算（100種類以上）
   - トレンド系: SMA, EMA, WMA, HMA, DEMA, TEMA, 一目均衡表, パラボリックSAR等
   - モメンタム系: RSI, MACD, ストキャスティクス, ROC, モメンタム, Williams %R等
   - ボラティリティ系: ボリンジャーバンド, ATR, ケルトナーチャネル, ドンチャンチャネル等
   - 出来高系: OBV, MFI, VWAP, CMF, A/Dライン等
   - その他: ピボットポイント、ローソク足パターン、季節性特徴等

3. 特徴量エンジニアリング（4段階の冗長削減）
   - ステップ1: 相関行列による高相関特徴量の削除（閾値: 0.95）
   - ステップ2: VIF（分散インフレ係数）による多重共線性チェック（閾値: 10）
   - ステップ3: 時系列クロスバリデーションによる重要度評価（下位20%削除）
   - ステップ4: SHAP値による特徴量重要度の最終評価（下位10%削除）

【出力ファイル】
1. {symbol}_1h_90days.csv                    - 生のOHLCVデータ
2. {symbol}_1h_90days_with_indicators.csv    - 全技術的指標を含むデータ
3. {symbol}_1h_90days_reduced_features.csv   - 特徴量選択後の最終データ
4. {symbol}_removed_features.json            - 各段階で削除された特徴量のリスト

【必要なライブラリ】
- hyperliquid: Hyperliquid APIクライアント
- pandas, numpy: データ処理
- statsmodels: VIF計算
- scikit-learn: 機械学習ユーティリティ
- lightgbm: SHAP値計算用モデル
- shap: 特徴量重要度評価

【使用方法】
1. COIN_SYMBOLを変更して取得したい通貨を指定
2. python ohlcv_by_claude.py を実行

【注意事項】
- インターネット接続が必要です
- 初回実行時は全ライブラリのインストールが必要です:
  pip install hyperliquid pandas numpy statsmodels scikit-learn lightgbm shap
"""

import csv
import time
import sys
import argparse
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from hyperliquid.info import Info
from hyperliquid.utils import constants

# websocketのエラーログを抑制
logging.getLogger('websocket').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

info = Info(constants.MAINNET_API_URL)

# ##############################################################################################################
# コマンドライン引数の処理
parser = argparse.ArgumentParser(description='Hyperliquid OHLCVデータ取得と特徴量エンジニアリング')
parser.add_argument('--symbol', type=str, default='HYPE', help='取得する通貨シンボル (例: BTC, HYPE, ETH, SOL)')
parser.add_argument('--timeframe', type=str, default='1h', 
                   choices=['1m', '3m', '5m', '15m', '30m', '1h'],
                   help='時間足 (1m, 3m, 5m, 15m, 30m, 1h)')
args = parser.parse_args()

COIN_SYMBOL = args.symbol.upper()
TIMEFRAME = args.timeframe

# 時間足に応じた設定
TIMEFRAME_CONFIG = {
    '1m': {'days': 7, 'annualize_factor': 60 * 24 * 365},      # 1分足: 7日間
    '3m': {'days': 21, 'annualize_factor': 20 * 24 * 365},     # 3分足: 21日間 (20 = 24*60/3)
    '5m': {'days': 30, 'annualize_factor': 288 * 365},         # 5分足: 30日間 (288 = 24*60/5)
    '15m': {'days': 60, 'annualize_factor': 96 * 365},         # 15分足: 60日間 (96 = 24*60/15)
    '30m': {'days': 90, 'annualize_factor': 48 * 365},         # 30分足: 90日間 (48 = 24*60/30)
    '1h': {'days': 90, 'annualize_factor': 24 * 365}           # 1時間足: 90日間
}

DAYS_TO_FETCH = TIMEFRAME_CONFIG[TIMEFRAME]['days']
ANNUALIZE_FACTOR = TIMEFRAME_CONFIG[TIMEFRAME]['annualize_factor']

# ##############################################################################################################
# 技術的指標の計算関数

def calculate_sma(data, period):
    """単純移動平均（SMA）"""
    return data.rolling(window=period, min_periods=1).mean()

def calculate_ema(data, period):
    """指数移動平均（EMA）"""
    return data.ewm(span=period, adjust=False).mean()

def calculate_rsi(data, period=14):
    """RSI（相対力指数）"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """MACD"""
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data, period=20, std_dev=2):
    """ボリンジャーバンド"""
    sma = calculate_sma(data, period)
    std = data.rolling(window=period, min_periods=1).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, sma, lower_band

def calculate_atr(high, low, close, period=14):
    """ATR（平均真のレンジ）"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=1).mean()
    return atr

def calculate_stochastic(high, low, close, k_period=14, d_period=3):
    """ストキャスティクス"""
    lowest_low = low.rolling(window=k_period, min_periods=1).min()
    highest_high = high.rolling(window=k_period, min_periods=1).max()
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_period, min_periods=1).mean()
    return k_percent, d_percent

def calculate_adx(high, low, close, period=14):
    """ADX（平均方向性指数）"""
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = calculate_atr(high, low, close, 1)
    atr = tr.rolling(window=period).mean()
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (abs(minus_dm).rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx, plus_di, minus_di

def calculate_obv(close, volume):
    """OBV（オンバランスボリューム）"""
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    return obv

def calculate_mfi(high, low, close, volume, period=14):
    """MFI（マネーフローインデックス）"""
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(), 0)
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + positive_mf / negative_mf))
    return mfi

def calculate_vwap(high, low, close, volume):
    """VWAP（出来高加重平均価格）"""
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap

def calculate_pivot_points(high, low, close):
    """ピボットポイント"""
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)
    return pivot, r1, r2, r3, s1, s2, s3

def calculate_wma(data, period):
    """加重移動平均（WMA）"""
    weights = np.arange(1, period + 1)
    return data.rolling(window=period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def calculate_hma(data, period):
    """ハル移動平均（HMA）"""
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))
    wma_half = calculate_wma(data, half_period)
    wma_full = calculate_wma(data, period)
    diff = 2 * wma_half - wma_full
    return calculate_wma(diff, sqrt_period)

def calculate_dema(data, period):
    """二重指数移動平均（DEMA）"""
    ema1 = calculate_ema(data, period)
    ema2 = calculate_ema(ema1, period)
    return 2 * ema1 - ema2

def calculate_tema(data, period):
    """三重指数移動平均（TEMA）"""
    ema1 = calculate_ema(data, period)
    ema2 = calculate_ema(ema1, period)
    ema3 = calculate_ema(ema2, period)
    return 3 * ema1 - 3 * ema2 + ema3

def calculate_ichimoku(high, low, close):
    """一目均衡表"""
    # 転換線 (9期間)
    tenkan = (high.rolling(window=9).max() + low.rolling(window=9).min()) / 2
    # 基準線 (26期間)
    kijun = (high.rolling(window=26).max() + low.rolling(window=26).min()) / 2
    # 先行スパンA (転換線と基準線の平均を26期間先行)
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    # 先行スパンB (52期間の最高値と最安値の平均を26期間先行)
    senkou_b = ((high.rolling(window=52).max() + low.rolling(window=52).min()) / 2).shift(26)
    # 遅行スパン (終値を26期間遅行)
    chikou = close.shift(-26)
    return tenkan, kijun, senkou_a, senkou_b, chikou

def calculate_parabolic_sar(high, low, close, af_start=0.02, af_max=0.2):
    """パラボリックSAR"""
    n = len(high)
    sar = np.zeros(n)
    trend = np.zeros(n)
    ep = np.zeros(n)
    af = np.zeros(n)
    
    # 初期値設定
    sar[0] = low.iloc[0]
    trend[0] = 1
    ep[0] = high.iloc[0]
    af[0] = af_start
    
    for i in range(1, n):
        if trend[i-1] == 1:  # 上昇トレンド
            sar[i] = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])
            if low.iloc[i] <= sar[i]:
                trend[i] = -1
                sar[i] = ep[i-1]
                ep[i] = low.iloc[i]
                af[i] = af_start
            else:
                trend[i] = 1
                if high.iloc[i] > ep[i-1]:
                    ep[i] = high.iloc[i]
                    af[i] = min(af[i-1] + af_start, af_max)
                else:
                    ep[i] = ep[i-1]
                    af[i] = af[i-1]
        else:  # 下降トレンド
            sar[i] = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])
            if high.iloc[i] >= sar[i]:
                trend[i] = 1
                sar[i] = ep[i-1]
                ep[i] = high.iloc[i]
                af[i] = af_start
            else:
                trend[i] = -1
                if low.iloc[i] < ep[i-1]:
                    ep[i] = low.iloc[i]
                    af[i] = min(af[i-1] + af_start, af_max)
                else:
                    ep[i] = ep[i-1]
                    af[i] = af[i-1]
    
    return pd.Series(sar, index=high.index), pd.Series(trend, index=high.index)

def calculate_aroon(high, low, period=25):
    """アルーン指標"""
    aroon_up = high.rolling(window=period + 1).apply(lambda x: 100 * (period - x.argmax()) / period)
    aroon_down = low.rolling(window=period + 1).apply(lambda x: 100 * (period - x.argmin()) / period)
    return aroon_up, aroon_down

def calculate_roc(data, period=12):
    """変化率（ROC）"""
    return 100 * (data - data.shift(period)) / data.shift(period)

def calculate_momentum(data, period=10):
    """モメンタム"""
    return data - data.shift(period)

def calculate_williams_r(high, low, close, period=14):
    """ウィリアムズ%R"""
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    return -100 * (highest_high - close) / (highest_high - lowest_low)

def calculate_keltner_channel(high, low, close, ema_period=20, atr_period=10, multiplier=2):
    """ケルトナーチャネル"""
    middle = calculate_ema(close, ema_period)
    atr = calculate_atr(high, low, close, atr_period)
    upper = middle + multiplier * atr
    lower = middle - multiplier * atr
    return upper, middle, lower

def calculate_donchian_channel(high, low, period=20):
    """ドンチャンチャネル"""
    upper = high.rolling(window=period).max()
    lower = low.rolling(window=period).min()
    middle = (upper + lower) / 2
    return upper, middle, lower

def calculate_historical_volatility(close, period=20, annualize=True):
    """ヒストリカルボラティリティ"""
    log_returns = np.log(close / close.shift(1))
    hv = log_returns.rolling(window=period).std()
    if annualize:
        # 時間足に応じた年率換算
        hv = hv * np.sqrt(ANNUALIZE_FACTOR)
    return hv

def calculate_cmf(high, low, close, volume, period=20):
    """チャイキンマネーフロー"""
    mf_volume = ((close - low) - (high - close)) / (high - low) * volume
    return mf_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()

def calculate_ad_line(high, low, close, volume):
    """蓄積/配分ライン"""
    clv = ((close - low) - (high - close)) / (high - low)
    clv = clv.fillna(0)
    ad = (clv * volume).cumsum()
    return ad

def calculate_vpt(close, volume):
    """ボリュームプライストレンド"""
    price_change = close.pct_change()
    vpt = (price_change * volume).cumsum()
    return vpt

def calculate_eom(high, low, volume, period=14):
    """イーズオブムーブメント"""
    distance_moved = (high + low) / 2 - (high.shift(1) + low.shift(1)) / 2
    emv = distance_moved / (volume / 10000000) / (high - low)
    return emv.rolling(window=period).mean()

def calculate_volume_oscillator(volume, fast_period=5, slow_period=10):
    """ボリュームオシレーター"""
    fast_ma = volume.rolling(window=fast_period).mean()
    slow_ma = volume.rolling(window=slow_period).mean()
    return 100 * (fast_ma - slow_ma) / slow_ma

def calculate_fractals(high, low, period=2):
    """フラクタル"""
    up_fractal = pd.Series(index=high.index, dtype=float)
    down_fractal = pd.Series(index=low.index, dtype=float)
    
    for i in range(period, len(high) - period):
        # 上昇フラクタル
        if all(high.iloc[i] > high.iloc[i-j] for j in range(1, period+1)) and \
           all(high.iloc[i] > high.iloc[i+j] for j in range(1, period+1)):
            up_fractal.iloc[i] = high.iloc[i]
        
        # 下降フラクタル
        if all(low.iloc[i] < low.iloc[i-j] for j in range(1, period+1)) and \
           all(low.iloc[i] < low.iloc[i+j] for j in range(1, period+1)):
            down_fractal.iloc[i] = low.iloc[i]
    
    return up_fractal, down_fractal

def calculate_true_range_percent(high, low, close):
    """True Range %"""
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return 100 * tr / close

def detect_candlestick_patterns(open_price, high, low, close):
    """ローソク足パターン検出"""
    patterns = pd.DataFrame(index=open_price.index)
    
    # Doji（同事線）
    body = abs(close - open_price)
    range_hl = high - low
    patterns['doji'] = (body <= range_hl * 0.1).astype(int)
    
    # Hammer（ハンマー）
    lower_shadow = np.minimum(open_price, close) - low
    upper_shadow = high - np.maximum(open_price, close)
    patterns['hammer'] = ((lower_shadow >= body * 2) & (upper_shadow <= body * 0.5)).astype(int)
    
    # Engulfing（包み線）
    patterns['bullish_engulfing'] = ((open_price > close.shift()) & 
                                     (close > open_price.shift()) & 
                                     (open_price.shift() > close.shift())).astype(int)
    
    patterns['bearish_engulfing'] = ((open_price < close.shift()) & 
                                     (close < open_price.shift()) & 
                                     (open_price.shift() < close.shift())).astype(int)
    
    return patterns

def calculate_ma_slope(ma_series, period=1):
    """移動平均の傾き"""
    return ma_series.diff(period) / period

def calculate_seasonality_features(timestamp):
    """季節性特徴量"""
    features = pd.DataFrame(index=timestamp.index)
    
    # 時間帯特徴
    features['hour'] = timestamp.dt.hour
    features['day_of_week'] = timestamp.dt.dayofweek
    features['day_of_month'] = timestamp.dt.day
    features['month'] = timestamp.dt.month
    
    # 取引セッション（UTC基準）
    features['asian_session'] = ((features['hour'] >= 0) & (features['hour'] < 8)).astype(int)
    features['european_session'] = ((features['hour'] >= 8) & (features['hour'] < 16)).astype(int)
    features['us_session'] = ((features['hour'] >= 16) & (features['hour'] < 24)).astype(int)
    
    # 週末フラグ
    features['is_weekend'] = (features['day_of_week'].isin([5, 6])).astype(int)
    
    return features

# ##############################################################################################################
# OHLCV
now_ms = int(time.time() * 1000)
one_day_ms = 24 * 60 * 60 * 1000
start_ms = now_ms - DAYS_TO_FETCH * one_day_ms  # 時間足に応じた期間を取得

csv_data = []

print(f"\n{COIN_SYMBOL}の価格データを取得中...")
print(f"時間足: {TIMEFRAME}, 期間: {DAYS_TO_FETCH}日間\n")

for i in range(DAYS_TO_FETCH):
    s = start_ms + i * one_day_ms
    e = s + one_day_ms
    print(f"取得: {datetime.utcfromtimestamp(s/1000)} → {datetime.utcfromtimestamp(e/1000)}")
    try:
        candles = info.candles_snapshot(COIN_SYMBOL, TIMEFRAME, s, e)  # 指定された時間足
        for c in candles:
            row = {
                "timestamp": datetime.utcfromtimestamp(c["t"] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                "open": c["o"],
                "high": c["h"],
                "low": c["l"],
                "close": c["c"],
                "volume": c["v"],
                "trades": c["n"],
            }
            csv_data.append(row)
    except Exception as ex:
        print(f"エラー: {ex}")

# 保存
if csv_data:
    file_path = f"{COIN_SYMBOL.lower()}_{TIMEFRAME}_{DAYS_TO_FETCH}days.csv"
    with open(file_path, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)
    print(f"\n保存完了: {file_path}")
    print(f"取得したデータ数: {len(csv_data)}件")
    
    # ##############################################################################################################
    # 技術的指標の計算と保存
    print(f"\n技術的指標を計算中...")
    
    # DataFrameに変換
    df = pd.DataFrame(csv_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    # 数値型に変換
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # トレンド系指標
    # 単純移動平均
    df['sma_10'] = calculate_sma(df['close'], 10)
    df['sma_20'] = calculate_sma(df['close'], 20)
    df['sma_50'] = calculate_sma(df['close'], 50)
    
    # 指数移動平均
    df['ema_10'] = calculate_ema(df['close'], 10)
    df['ema_20'] = calculate_ema(df['close'], 20)
    df['ema_50'] = calculate_ema(df['close'], 50)
    
    # 加重移動平均
    df['wma_20'] = calculate_wma(df['close'], 20)
    
    # ハル移動平均
    df['hma_20'] = calculate_hma(df['close'], 20)
    
    # 二重・三重指数移動平均
    df['dema_20'] = calculate_dema(df['close'], 20)
    df['tema_20'] = calculate_tema(df['close'], 20)
    
    # 一目均衡表
    ichimoku_data = calculate_ichimoku(df['high'], df['low'], df['close'])
    df['ichimoku_tenkan'], df['ichimoku_kijun'], df['ichimoku_senkou_a'], df['ichimoku_senkou_b'], df['ichimoku_chikou'] = ichimoku_data
    
    # パラボリックSAR
    df['psar'], df['psar_trend'] = calculate_parabolic_sar(df['high'], df['low'], df['close'])
    
    # アルーン
    df['aroon_up'], df['aroon_down'] = calculate_aroon(df['high'], df['low'])
    
    # モメンタム系指標
    df['rsi_14'] = calculate_rsi(df['close'], 14)
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df['close'])
    df['stoch_k'], df['stoch_d'] = calculate_stochastic(df['high'], df['low'], df['close'])
    df['roc_12'] = calculate_roc(df['close'], 12)
    df['momentum_10'] = calculate_momentum(df['close'], 10)
    df['williams_r'] = calculate_williams_r(df['high'], df['low'], df['close'])
    
    # ボラティリティ系指標
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = calculate_bollinger_bands(df['close'])
    df['atr_14'] = calculate_atr(df['high'], df['low'], df['close'], 14)
    df['kc_upper'], df['kc_middle'], df['kc_lower'] = calculate_keltner_channel(df['high'], df['low'], df['close'])
    df['dc_upper'], df['dc_middle'], df['dc_lower'] = calculate_donchian_channel(df['high'], df['low'])
    df['historical_volatility'] = calculate_historical_volatility(df['close'])
    
    # ADX
    df['adx'], df['di_plus'], df['di_minus'] = calculate_adx(df['high'], df['low'], df['close'])
    
    # 出来高系指標
    df['obv'] = calculate_obv(df['close'], df['volume'])
    df['mfi_14'] = calculate_mfi(df['high'], df['low'], df['close'], df['volume'], 14)
    df['vwap'] = calculate_vwap(df['high'], df['low'], df['close'], df['volume'])
    df['cmf'] = calculate_cmf(df['high'], df['low'], df['close'], df['volume'])
    df['ad_line'] = calculate_ad_line(df['high'], df['low'], df['close'], df['volume'])
    df['vpt'] = calculate_vpt(df['close'], df['volume'])
    df['eom'] = calculate_eom(df['high'], df['low'], df['volume'])
    df['volume_oscillator'] = calculate_volume_oscillator(df['volume'])
    
    # ピボットポイント（日次データなので前日のデータを使用）
    pivot_data = calculate_pivot_points(
        df['high'].shift(1), 
        df['low'].shift(1), 
        df['close'].shift(1)
    )
    df['pivot'], df['r1'], df['r2'], df['r3'], df['s1'], df['s2'], df['s3'] = pivot_data
    
    # 追加の特徴量
    # 価格変化率
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    
    # ハイローレンジ
    df['high_low_ratio'] = (df['high'] - df['low']) / df['close']
    df['close_location'] = (df['close'] - df['low']) / (df['high'] - df['low'])
    
    # ローリング統計
    df['rolling_std_20'] = df['close'].rolling(window=20).std()
    df['rolling_max_20'] = df['close'].rolling(window=20).max()
    df['rolling_min_20'] = df['close'].rolling(window=20).min()
    
    # Z-Score
    df['z_score'] = (df['close'] - df['sma_20']) / df['rolling_std_20']
    
    # フラクタル
    df['fractal_up'], df['fractal_down'] = calculate_fractals(df['high'], df['low'])
    
    # True Range %
    df['true_range_pct'] = calculate_true_range_percent(df['high'], df['low'], df['close'])
    
    # ローソク足パターン
    patterns = detect_candlestick_patterns(df['open'], df['high'], df['low'], df['close'])
    for pattern_name in patterns.columns:
        df[f'pattern_{pattern_name}'] = patterns[pattern_name]
    
    # 移動平均の傾き
    df['sma_20_slope'] = calculate_ma_slope(df['sma_20'])
    df['ema_20_slope'] = calculate_ma_slope(df['ema_20'])
    
    # 季節性特徴量
    seasonality = calculate_seasonality_features(df['timestamp'])
    for col in seasonality.columns:
        df[col] = seasonality[col]
    
    # Price-Volume Divergence
    df['price_obv_divergence'] = ((df['close'].diff() > 0) != (df['obv'].diff() > 0)).astype(int)
    
    # Lag/Lead Transforms
    df['close_lag_1'] = df['close'].shift(1)
    df['close_lag_5'] = df['close'].shift(5)
    df['close_lead_1'] = df['close'].shift(-1)
    
    # 拡張データを保存
    extended_file_path = f"{COIN_SYMBOL.lower()}_{TIMEFRAME}_{DAYS_TO_FETCH}days_with_indicators.csv"
    df.to_csv(extended_file_path, index=False)
    print(f"\n技術的指標を含むファイルを保存: {extended_file_path}")
    print(f"カラム数: {len(df.columns)}個")
    print(f"\n含まれる指標:")
    print("【トレンド系】")
    print("- 移動平均: SMA(10,20,50), EMA(10,20,50), WMA(20), HMA(20), DEMA(20), TEMA(20)")
    print("- 一目均衡表: 転換線, 基準線, 先行スパンA/B, 遅行スパン")
    print("- Parabolic SAR, Aroon Up/Down")
    print("\n【モメンタム系】")
    print("- RSI(14), MACD/Signal/Histogram, Stochastic(%K/%D)")
    print("- ROC(12), Momentum(10), Williams %R")
    print("\n【ボラティリティ系】")
    print("- Bollinger Bands, Keltner Channel, Donchian Channel")
    print("- ATR(14), Historical Volatility")
    print("\n【出来高系】")
    print("- OBV, MFI(14), VWAP, CMF, A/D Line")
    print("- VPT, EOM, Volume Oscillator")
    print("\n【価格位置・レンジ】")
    print("- Pivot Points (P,R1-R3,S1-S3)")
    print("- Fractals (Up/Down), True Range %")
    print("\n【複合・その他】")
    print("- Z-Score, Returns, Candlestick Patterns")
    print("- MA Slope, Seasonality Features, Price-Volume Divergence")
    print("- Lag/Lead Transforms")
    
else:
    print(f"\nエラー: {COIN_SYMBOL}のデータが取得できませんでした。")

# ##############################################################################################################
# 特徴量エンジニアリング（冗長削減）

if csv_data:
    print("\n========== 特徴量エンジニアリング（冗長削減）開始 ==========")
    
    # 数値型の特徴量のみを抽出（タイムスタンプとカテゴリカル変数を除外）
    numeric_cols = [col for col in df.columns if col not in ['timestamp', 'trades'] and df[col].dtype in ['float64', 'int64']]
    df_numeric = df[numeric_cols].copy()
    
    # NaN値を前方補完
    df_numeric = df_numeric.ffill().bfill()
    
    # ##############################################################################################################
    # 1. 相関行列による冗長削減
    print("\n【1/4】相関行列による冗長削減")
    
    # 相関行列を計算
    corr_matrix = df_numeric.corr()
    
    # 高相関ペアを特定（閾値: 0.95）
    corr_threshold = 0.95
    high_corr_pairs = []
    
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            if abs(corr_matrix.iloc[i, j]) > corr_threshold:
                col1 = corr_matrix.columns[i]
                col2 = corr_matrix.columns[j]
                high_corr_pairs.append((col1, col2, corr_matrix.iloc[i, j]))
    
    # 削除する特徴量を決定（高相関ペアのうち、後に出現する方を削除）
    cols_to_remove_corr = set()
    for col1, col2, corr_val in high_corr_pairs:
        if col1 not in cols_to_remove_corr:
            cols_to_remove_corr.add(col2)
    
    print(f"- 高相関ペア数: {len(high_corr_pairs)}")
    print(f"- 削除対象特徴量数: {len(cols_to_remove_corr)}")
    
    # 相関による削減後の特徴量
    remaining_cols_after_corr = [col for col in numeric_cols if col not in cols_to_remove_corr]
    df_after_corr = df_numeric[remaining_cols_after_corr].copy()
    
    # ##############################################################################################################
    # 2. VIF（分散インフレ係数）による多重共線性チェック
    print("\n【2/4】VIFによる多重共線性チェック")
    
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    
    def calculate_vif(df):
        vif_data = pd.DataFrame()
        vif_data["Feature"] = df.columns
        vif_data["VIF"] = [variance_inflation_factor(df.values, i) for i in range(df.shape[1])]
        return vif_data
    
    # VIF計算（エラー回避のため、標準化を行う）
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    df_scaled = pd.DataFrame(
        scaler.fit_transform(df_after_corr),
        columns=df_after_corr.columns,
        index=df_after_corr.index
    )
    
    # VIF閾値（10以上は多重共線性が高い）
    vif_threshold = 10
    cols_to_remove_vif = set()
    
    # 反復的にVIFが高い特徴量を削除
    max_iterations = 10
    for iteration in range(max_iterations):
        if len(df_scaled.columns) <= 1:
            break
            
        try:
            vif_df = calculate_vif(df_scaled)
            max_vif = vif_df['VIF'].max()
            
            if max_vif <= vif_threshold:
                break
                
            # 最もVIFが高い特徴量を削除
            max_vif_feature = vif_df.loc[vif_df['VIF'].idxmax(), 'Feature']
            cols_to_remove_vif.add(max_vif_feature)
            df_scaled = df_scaled.drop(columns=[max_vif_feature])
            
        except Exception as e:
            print(f"  VIF計算エラー: {e}")
            break
    
    print(f"- VIFによる削除対象特徴量数: {len(cols_to_remove_vif)}")
    
    # VIF削減後の特徴量
    remaining_cols_after_vif = [col for col in remaining_cols_after_corr if col not in cols_to_remove_vif]
    df_after_vif = df_after_corr[remaining_cols_after_vif].copy()
    
    # ##############################################################################################################
    # 3. 時系列クロスバリデーション
    print("\n【3/4】時系列クロスバリデーション")
    
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_squared_error
    import warnings
    warnings.filterwarnings('ignore')
    
    # ターゲット変数の準備（次の時間の終値を予測）
    target = df['close'].shift(-1).fillna(method='ffill')
    
    # 時系列分割
    tscv = TimeSeriesSplit(n_splits=5)
    
    # 各特徴量の重要度を保存
    feature_importance_cv = pd.DataFrame(index=df_after_vif.columns, columns=['mean_importance', 'std_importance'])
    
    all_importances = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(df_after_vif)):
        if len(train_idx) < 100 or len(val_idx) < 20:  # 最小サンプル数チェック
            continue
            
        X_train = df_after_vif.iloc[train_idx]
        X_val = df_after_vif.iloc[val_idx]
        y_train = target.iloc[train_idx]
        y_val = target.iloc[val_idx]
        
        # ランダムフォレストで特徴量重要度を計算
        rf = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)
        
        importances = pd.Series(rf.feature_importances_, index=X_train.columns)
        all_importances.append(importances)
    
    if all_importances:
        # 平均重要度と標準偏差を計算
        importance_df = pd.DataFrame(all_importances)
        feature_importance_cv['mean_importance'] = importance_df.mean()
        feature_importance_cv['std_importance'] = importance_df.std()
        
        # 重要度が低い特徴量を特定（平均重要度の下位20%）
        importance_threshold = feature_importance_cv['mean_importance'].quantile(0.2)
        low_importance_features = feature_importance_cv[feature_importance_cv['mean_importance'] < importance_threshold].index.tolist()
        
        print(f"- 低重要度特徴量数: {len(low_importance_features)}")
    else:
        low_importance_features = []
        print("- 時系列CVスキップ（データ不足）")
    
    # 時系列CV後の特徴量
    remaining_cols_after_cv = [col for col in remaining_cols_after_vif if col not in low_importance_features]
    df_after_cv = df_after_vif[remaining_cols_after_cv].copy()
    
    # ##############################################################################################################
    # 4. SHAP値による特徴量重要度評価
    print("\n【4/4】SHAP値による特徴量重要度評価")
    
    try:
        import shap
        
        # サンプル数を制限（計算時間短縮）
        sample_size = min(1000, len(df_after_cv))
        sample_indices = np.random.choice(df_after_cv.index[:-1], size=sample_size, replace=False)
        
        X_sample = df_after_cv.loc[sample_indices]
        y_sample = target.loc[sample_indices]
        
        # LightGBMモデルを使用（SHAPとの相性が良い）
        import lightgbm as lgb
        
        lgb_model = lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            verbosity=-1
        )
        lgb_model.fit(X_sample, y_sample)
        
        # SHAP値を計算
        explainer = shap.TreeExplainer(lgb_model)
        shap_values = explainer.shap_values(X_sample)
        
        # 特徴量重要度（SHAP値の絶対値の平均）
        shap_importance = pd.Series(
            np.abs(shap_values).mean(axis=0),
            index=X_sample.columns
        ).sort_values(ascending=False)
        
        # 重要度が低い特徴量を特定（下位10%）
        shap_threshold = shap_importance.quantile(0.1)
        low_shap_features = shap_importance[shap_importance < shap_threshold].index.tolist()
        
        print(f"- SHAP低重要度特徴量数: {len(low_shap_features)}")
        
        # 最終的な特徴量選択
        final_features = [col for col in remaining_cols_after_cv if col not in low_shap_features]
        
    except ImportError:
        print("- SHAPライブラリがインストールされていません。スキップします。")
        final_features = remaining_cols_after_cv
    except Exception as e:
        print(f"- SHAP計算エラー: {e}")
        final_features = remaining_cols_after_cv
    
    # ##############################################################################################################
    # 結果の保存
    print("\n========== 冗長削減結果 ==========")
    print(f"元の特徴量数: {len(numeric_cols)}")
    print(f"相関削減後: {len(remaining_cols_after_corr)} (-{len(cols_to_remove_corr)})")
    print(f"VIF削減後: {len(remaining_cols_after_vif)} (-{len(cols_to_remove_vif)})")
    print(f"時系列CV削減後: {len(remaining_cols_after_cv)} (-{len(low_importance_features)})")
    print(f"最終特徴量数: {len(final_features)}")
    
    # 選択された特徴量のみを含むデータフレームを作成
    df_final = pd.concat([
        df[['timestamp']],  # タイムスタンプは保持
        df[final_features]
    ], axis=1)
    
    # 削減後のデータを保存
    reduced_file_path = f"{COIN_SYMBOL.lower()}_{TIMEFRAME}_{DAYS_TO_FETCH}days_reduced_features.csv"
    df_final.to_csv(reduced_file_path, index=False)
    print(f"\n特徴量削減後のファイルを保存: {reduced_file_path}")
    
    # 削除された特徴量のリストを保存
    removed_features = {
        'correlation': list(cols_to_remove_corr),
        'vif': list(cols_to_remove_vif),
        'cv_importance': low_importance_features,
        'shap_importance': low_shap_features if 'low_shap_features' in locals() else []
    }
    
    import json
    with open(f"{COIN_SYMBOL.lower()}_{TIMEFRAME}_removed_features.json", 'w') as f:
        json.dump(removed_features, f, indent=2)
    
    print(f"削除された特徴量リストを保存: {COIN_SYMBOL.lower()}_{TIMEFRAME}_removed_features.json")
    print("\n✅ ohlcv_by_claude.py の処理が完了しました！")
    sys.stdout.flush()  # 出力をフラッシュ
    
# ╔════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                                          プログラム終了                                         ║
# ╚════════════════════════════════════════════════════════════════════════════════════════════════╝