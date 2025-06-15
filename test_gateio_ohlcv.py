#!/usr/bin/env python3
"""
マルチ取引所OHLCVエンドポイントテストツール
統合APIクライアントを使用してHyperliquid vs Gate.ioを比較
"""

import ccxt
import pandas as pd
import asyncio
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# 統合APIクライアントをインポート
try:
    from hyperliquid_api_client import MultiExchangeAPIClient, ExchangeType
    MULTI_EXCHANGE_AVAILABLE = True
except ImportError:
    MULTI_EXCHANGE_AVAILABLE = False
    st.warning("⚠️ Multi-Exchange API Client not available. Using legacy mode.")

# Streamlit設定
st.set_page_config(
    page_title="マルチ取引所OHLCVテスト",
    page_icon="📊",
    layout="wide"
)

st.title("🔧 マルチ取引所OHLCVエンドポイントテスト")
st.markdown("**Hyperliquid vs Gate.io 統合API比較ツール**")
st.markdown("---")

# サイドバー設定
with st.sidebar:
    st.header("⚙️ 設定")
    
    # 取引所選択
    if MULTI_EXCHANGE_AVAILABLE:
        exchange_mode = st.selectbox(
            "取引所選択",
            ["統合比較", "Hyperliquid", "Gate.io", "レガシー(Gate.io直接)"],
            help="使用する取引所を選択"
        )
    else:
        exchange_mode = "レガシー(Gate.io直接)"
        st.info("統合APIが利用できません。レガシーモードで動作します。")
    
    # 銘柄選択
    if exchange_mode in ["統合比較", "Hyperliquid", "Gate.io"]:
        symbol = st.text_input(
            "銘柄 (例: BTC)", 
            value="BTC",
            help="銘柄名（統合APIが自動でマッピング）"
        )
    else:
        symbol = st.text_input(
            "銘柄 (例: BTC/USDT:USDT)", 
            value="BTC/USDT:USDT",
            help="Gate.io先物の銘柄ペア"
        )
    
    # 時間足選択
    timeframe = st.selectbox(
        "時間足",
        ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"],
        index=5  # デフォルト: 1h
    )
    
    # 期間選択
    days = st.slider(
        "取得期間（日）",
        min_value=1,
        max_value=30,
        value=7
    )
    
    # 取得制限（レガシーモードのみ）
    if exchange_mode == "レガシー(Gate.io直接)":
        limit = st.number_input(
            "取得件数上限",
            min_value=100,
            max_value=1000,
            value=500,
            step=100
        )
    
    fetch_button = st.button("📥 データ取得", type="primary", use_container_width=True)

# メインエリア
col1, col2 = st.columns([2, 1])

def fetch_gateio_ohlcv_legacy():
    """Gate.ioからOHLCVデータを取得（レガシー版）"""
    try:
        # Gate.io Exchangeインスタンスを作成（同期版）
        exchange = ccxt.gateio({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # 先物市場を使用
            }
        })
        
        # 市場情報をロード
        exchange.load_markets()
        
        # 終了時刻と開始時刻を計算
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        since = int(start_time.timestamp() * 1000)
        
        # OHLCVデータを取得
        ohlcv = exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=since,
            limit=limit
        )
        
        # DataFrameに変換
        df = pd.DataFrame(
            ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df, None
        
    except Exception as e:
        return None, str(e)

@st.cache_data
def fetch_unified_ohlcv(exchange_type, symbol, timeframe, days):
    """統合APIを使用してOHLCVデータを取得"""
    if not MULTI_EXCHANGE_AVAILABLE:
        return None, "統合API利用不可"
    
    async def _fetch_data():
        try:
            client = MultiExchangeAPIClient(exchange_type=exchange_type)
            df = await client.get_ohlcv_data_with_period(symbol, timeframe, days=days)
            return df, None
        except Exception as e:
            return None, str(e)
    
    # イベントループを作成して実行
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_fetch_data())
        loop.close()
        return result
    except Exception as e:
        return None, str(e)

def compare_exchanges(symbol, timeframe, days):
    """両取引所のデータを比較取得"""
    results = {}
    
    # Hyperliquid
    try:
        hl_df, hl_error = fetch_unified_ohlcv("hyperliquid", symbol, timeframe, days)
        if hl_error is None and hl_df is not None:
            results['hyperliquid'] = {
                'data': hl_df,
                'status': 'success',
                'count': len(hl_df),
                'latest_price': hl_df['close'].iloc[-1] if len(hl_df) > 0 else 0
            }
        else:
            results['hyperliquid'] = {
                'data': None,
                'status': 'error',
                'error': hl_error or 'Unknown error'
            }
    except Exception as e:
        results['hyperliquid'] = {
            'data': None,
            'status': 'error',
            'error': str(e)
        }
    
    # Gate.io
    try:
        gate_df, gate_error = fetch_unified_ohlcv("gateio", symbol, timeframe, days)
        if gate_error is None and gate_df is not None:
            results['gateio'] = {
                'data': gate_df,
                'status': 'success',
                'count': len(gate_df),
                'latest_price': gate_df['close'].iloc[-1] if len(gate_df) > 0 else 0
            }
        else:
            results['gateio'] = {
                'data': None,
                'status': 'error',
                'error': gate_error or 'Unknown error'
            }
    except Exception as e:
        results['gateio'] = {
            'data': None,
            'status': 'error',
            'error': str(e)
        }
    
    return results

def display_ohlcv_chart(df):
    """OHLCVチャートを表示"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('価格チャート', '出来高')
    )
    
    # ローソク足チャート
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC'
        ),
        row=1, col=1
    )
    
    # 出来高
    fig.add_trace(
        go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name='Volume',
            marker_color='rgba(0,150,255,0.5)'
        ),
        row=2, col=1
    )
    
    # レイアウト設定
    fig.update_layout(
        title=f'{symbol} - {timeframe}',
        xaxis_title='時刻',
        yaxis_title='価格',
        height=600,
        showlegend=False
    )
    
    fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
    
    return fig

# データ取得処理
if fetch_button:
    with st.spinner('データ取得中...'):
        
        if exchange_mode == "統合比較":
            # 両取引所の比較
            results = compare_exchanges(symbol, timeframe, days)
            
            # 結果表示
            st.subheader("🔄 取引所比較結果")
            
            comparison_cols = st.columns(2)
            
            # Hyperliquid結果
            with comparison_cols[0]:
                st.markdown("### 🔥 Hyperliquid")
                hl_result = results.get('hyperliquid', {})
                if hl_result.get('status') == 'success':
                    st.success(f"✅ {hl_result['count']}件取得")
                    st.write(f"最新価格: ${hl_result['latest_price']:,.2f}")
                else:
                    st.error(f"❌ {hl_result.get('error', 'Unknown error')}")
            
            # Gate.io結果
            with comparison_cols[1]:
                st.markdown("### 🌐 Gate.io")
                gate_result = results.get('gateio', {})
                if gate_result.get('status') == 'success':
                    st.success(f"✅ {gate_result['count']}件取得")
                    st.write(f"最新価格: ${gate_result['latest_price']:,.2f}")
                else:
                    st.error(f"❌ {gate_result.get('error', 'Unknown error')}")
            
            # 価格差分析
            if (results.get('hyperliquid', {}).get('status') == 'success' and 
                results.get('gateio', {}).get('status') == 'success'):
                
                hl_price = results['hyperliquid']['latest_price']
                gate_price = results['gateio']['latest_price']
                price_diff = abs(hl_price - gate_price)
                price_diff_pct = (price_diff / hl_price) * 100
                
                st.markdown("### 📊 価格比較")
                st.write(f"**価格差**: ${price_diff:,.2f} ({price_diff_pct:.3f}%)")
                
                # チャート比較表示
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 🔥 Hyperliquid チャート")
                    hl_fig = display_ohlcv_chart(results['hyperliquid']['data'])
                    st.plotly_chart(hl_fig, use_container_width=True)
                
                with col2:
                    st.markdown("#### 🌐 Gate.io チャート")
                    gate_fig = display_ohlcv_chart(results['gateio']['data'])
                    st.plotly_chart(gate_fig, use_container_width=True)
        
        elif exchange_mode in ["Hyperliquid", "Gate.io"]:
            # 単一取引所モード
            exchange_type = exchange_mode.lower()
            df, error = fetch_unified_ohlcv(exchange_type, symbol, timeframe, days)
            
            if error:
                st.error(f"❌ エラー: {error}")
            elif df is not None and not df.empty:
                # 成功メッセージ
                st.success(f"✅ {exchange_mode}から{len(df)}件のデータを取得しました")
                
                # データ表示
                with col1:
                    st.subheader(f"📊 {exchange_mode} チャート")
                    fig = display_ohlcv_chart(df)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.subheader("📋 データ情報")
                    st.write(f"**取引所**: {exchange_mode}")
                    st.write(f"**取得件数**: {len(df)}件")
                    st.write(f"**開始日時**: {df['timestamp'].min()}")
                    st.write(f"**終了日時**: {df['timestamp'].max()}")
                    st.write(f"**最高値**: ${df['high'].max():,.2f}")
                    st.write(f"**最安値**: ${df['low'].min():,.2f}")
                    st.write(f"**平均出来高**: {df['volume'].mean():,.0f}")
                    
                    # データプレビュー
                    st.subheader("🔍 データプレビュー")
                    st.dataframe(df.tail(10), use_container_width=True)
            else:
                st.warning("データが取得できませんでした")
        
        else:
            # レガシーモード
            df, error = fetch_gateio_ohlcv_legacy()
            
            if error:
                st.error(f"❌ エラー: {error}")
            elif df is not None and not df.empty:
                # 成功メッセージ
                st.success(f"✅ {len(df)}件のデータを取得しました")
                
                # データ表示
                with col1:
                    st.subheader("📊 チャート")
                    fig = display_ohlcv_chart(df)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.subheader("📋 データ情報")
                    st.write(f"**取得件数**: {len(df)}件")
                    st.write(f"**開始日時**: {df['timestamp'].min()}")
                    st.write(f"**終了日時**: {df['timestamp'].max()}")
                    st.write(f"**最高値**: ${df['high'].max():,.2f}")
                    st.write(f"**最安値**: ${df['low'].min():,.2f}")
                    st.write(f"**平均出来高**: {df['volume'].mean():,.0f}")
                    
                    # データプレビュー
                    st.subheader("🔍 データプレビュー")
                    st.dataframe(df.tail(10), use_container_width=True)
            else:
                st.warning("データが取得できませんでした")

# 使用方法
with st.expander("📖 使用方法"):
    st.markdown("""
    ### マルチ取引所OHLCVテストツール
    
    #### 🔧 統合APIモード（推奨）
    1. **取引所選択**: 統合比較、Hyperliquid、Gate.ioから選択
    2. **銘柄を入力**: シンプルな銘柄名（例: BTC、ETH、SOL）
    3. **時間足を選択**: 1分足から日足まで
    4. **期間を設定**: 取得する日数
    5. **データ取得**: ボタンをクリックしてデータ取得
    
    #### 🌟 主要機能
    - **🔄 統合比較**: HyperliquidとGate.ioの価格・データを同時比較
    - **🔥 Hyperliquid**: 直接Hyperliquid APIからデータ取得
    - **🌐 Gate.io**: CCXT経由でGate.io先物データ取得
    - **🔧 レガシー**: 従来のGate.io直接アクセス
    
    #### ✨ 利点
    - ✅ **フラグ1つで取引所切り替え**
    - ✅ **統一されたAPIインターフェース**
    - ✅ **自動シンボルマッピング**（PEPE ⇄ kPEPE など）
    - ✅ **価格差分析機能**
    - ✅ **レート制限の自動処理**
    
    #### ⚠️ 注意点
    - Gate.ioの先物価格はHyperliquidと異なる場合があります
    - シンボルマッピングは自動で行われますが、一部銘柄は対応していない可能性があります
    - 統合比較モードでは両取引所のデータを取得するため、時間がかかる場合があります
    """)

# テスト用銘柄リスト
with st.expander("🪙 テスト用銘柄例"):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        **統合API推奨銘柄**
        - BTC (両取引所対応)
        - ETH (両取引所対応)  
        - SOL (両取引所対応)
        """)
    with col2:
        st.markdown("""
        **アルトコイン**
        - HYPE (新興トークン)
        - WIF (ミームコイン)
        - PEPE (自動マッピング)
        """)
    with col3:
        st.markdown("""
        **レガシーモード用**
        - BTC/USDT:USDT
        - ETH/USDT:USDT
        - SOL/USDT:USDT
        """)

# 設定ファイル情報
with st.expander("⚙️ 設定ファイル"):
    st.markdown("""
    ### 取引所切り替え設定
    
    `exchange_config.json`ファイルで動的に取引所を切り替え可能：
    
    ```json
    {
        "default_exchange": "hyperliquid",
        "exchanges": {
            "hyperliquid": {
                "enabled": true,
                "rate_limit_delay": 0.5
            },
            "gateio": {
                "enabled": true,
                "rate_limit_delay": 0.1,
                "futures_only": true
            }
        }
    }
    ```
    
    ### コマンドライン切り替え
    ```bash
    # Hyperliquidに切り替え
    python exchange_switcher.py hyperliquid
    
    # Gate.ioに切り替え  
    python exchange_switcher.py gateio
    
    # 現在の状態確認
    python exchange_switcher.py status
    ```
    """)