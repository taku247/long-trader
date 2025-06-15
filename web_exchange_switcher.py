#!/usr/bin/env python3
"""
Webブラウザ上での取引所切り替えダッシュボード
HyperliquidとGate.ioをリアルタイムで切り替え可能
"""

import streamlit as st
import asyncio
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# 統合APIクライアントをインポート
try:
    from hyperliquid_api_client import MultiExchangeAPIClient, ExchangeType
    from exchange_switcher import ExchangeSwitcher
    MULTI_EXCHANGE_AVAILABLE = True
except ImportError:
    MULTI_EXCHANGE_AVAILABLE = False
    st.error("⚠️ Multi-Exchange API Client not available")

# Streamlit設定
st.set_page_config(
    page_title="取引所切り替えダッシュボード",
    page_icon="🔄",
    layout="wide"
)

# セッション状態の初期化
if 'current_exchange' not in st.session_state:
    st.session_state.current_exchange = 'hyperliquid'
if 'exchange_history' not in st.session_state:
    st.session_state.exchange_history = []

def log_exchange_switch(from_exchange, to_exchange):
    """取引所切り替えをログに記録"""
    st.session_state.exchange_history.append({
        'timestamp': datetime.now(),
        'from': from_exchange,
        'to': to_exchange,
        'action': 'switch'
    })

def save_exchange_config(exchange):
    """設定ファイルに保存"""
    config = {
        "default_exchange": exchange,
        "exchanges": {
            "hyperliquid": {"enabled": True, "rate_limit_delay": 0.5},
            "gateio": {"enabled": True, "rate_limit_delay": 0.1, "futures_only": True}
        },
        "last_updated": datetime.now().isoformat(),
        "updated_via": "web_interface"
    }
    
    with open('exchange_config.json', 'w') as f:
        json.dump(config, f, indent=2)

@st.cache_data
def fetch_exchange_data(exchange_type, symbol, timeframe, days):
    """指定取引所からデータを取得"""
    if not MULTI_EXCHANGE_AVAILABLE:
        return None, "統合API利用不可"
    
    async def _fetch_data():
        try:
            client = MultiExchangeAPIClient(exchange_type=exchange_type)
            df = await client.get_ohlcv_data_with_period(symbol, timeframe, days=days)
            
            # 追加情報を取得
            market_info = await client.get_market_info(symbol)
            
            return {
                'data': df,
                'market_info': market_info,
                'exchange': exchange_type,
                'symbol': symbol,
                'timeframe': timeframe,
                'fetch_time': datetime.now()
            }, None
        except Exception as e:
            return None, str(e)
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_fetch_data())
        loop.close()
        return result
    except Exception as e:
        return None, str(e)

def display_exchange_status():
    """現在の取引所状態を表示"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### 🔄 現在の取引所: **{st.session_state.current_exchange.upper()}**")
    
    with col2:
        if st.session_state.current_exchange == 'hyperliquid':
            st.markdown("**🔥 Hyperliquid**")
            st.success("アクティブ")
        else:
            st.markdown("**🔥 Hyperliquid**") 
            st.info("非アクティブ")
    
    with col3:
        if st.session_state.current_exchange == 'gateio':
            st.markdown("**🌐 Gate.io**")
            st.success("アクティブ")
        else:
            st.markdown("**🌐 Gate.io**")
            st.info("非アクティブ")

def display_exchange_switcher():
    """取引所切り替えUI"""
    st.markdown("### 🔄 取引所切り替え")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔥 Hyperliquidに切り替え", 
                    disabled=(st.session_state.current_exchange == 'hyperliquid'),
                    use_container_width=True):
            old_exchange = st.session_state.current_exchange
            st.session_state.current_exchange = 'hyperliquid'
            save_exchange_config('hyperliquid')
            log_exchange_switch(old_exchange, 'hyperliquid')
            st.success("✅ Hyperliquidに切り替えました")
            st.rerun()
    
    with col2:
        if st.button("🌐 Gate.ioに切り替え",
                    disabled=(st.session_state.current_exchange == 'gateio'),
                    use_container_width=True):
            old_exchange = st.session_state.current_exchange
            st.session_state.current_exchange = 'gateio'
            save_exchange_config('gateio')
            log_exchange_switch(old_exchange, 'gateio')
            st.success("✅ Gate.ioに切り替えました")
            st.rerun()
    
    with col3:
        if st.button("📊 設定ファイル確認", use_container_width=True):
            if os.path.exists('exchange_config.json'):
                with open('exchange_config.json', 'r') as f:
                    config = json.load(f)
                st.json(config)
            else:
                st.warning("設定ファイルが見つかりません")

def display_data_comparison(symbol, timeframe, days):
    """両取引所のデータ比較表示"""
    st.markdown("### 📊 取引所データ比較")
    
    # プログレスバー
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Hyperliquidデータ取得
    status_text.text("🔥 Hyperliquidからデータ取得中...")
    progress_bar.progress(25)
    hl_result, hl_error = fetch_exchange_data("hyperliquid", symbol, timeframe, days)
    
    # Gate.ioデータ取得
    status_text.text("🌐 Gate.ioからデータ取得中...")
    progress_bar.progress(75)
    gate_result, gate_error = fetch_exchange_data("gateio", symbol, timeframe, days)
    
    progress_bar.progress(100)
    status_text.text("✅ データ取得完了")
    
    # 結果表示
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔥 Hyperliquid")
        if hl_error:
            st.error(f"❌ エラー: {hl_error}")
        elif hl_result:
            df = hl_result['data']
            market_info = hl_result['market_info']
            
            st.success(f"✅ {len(df)}件のデータ取得")
            st.write(f"**最新価格**: ${df['close'].iloc[-1]:,.2f}")
            st.write(f"**レバレッジ制限**: {market_info.get('leverage_limit', 'N/A')}x")
            st.write(f"**取得時刻**: {hl_result['fetch_time'].strftime('%H:%M:%S')}")
            
            # 簡易チャート
            fig_hl = go.Figure()
            fig_hl.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['close'], 
                mode='lines',
                name='Hyperliquid',
                line=dict(color='orange')
            ))
            fig_hl.update_layout(title="Hyperliquid価格推移", height=300)
            st.plotly_chart(fig_hl, use_container_width=True)
    
    with col2:
        st.markdown("#### 🌐 Gate.io")
        if gate_error:
            st.error(f"❌ エラー: {gate_error}")
        elif gate_result:
            df = gate_result['data']
            
            st.success(f"✅ {len(df)}件のデータ取得")
            st.write(f"**最新価格**: ${df['close'].iloc[-1]:,.2f}")
            st.write(f"**先物ペア**: {symbol}_USDT")
            st.write(f"**取得時刻**: {gate_result['fetch_time'].strftime('%H:%M:%S')}")
            
            # 簡易チャート
            fig_gate = go.Figure()
            fig_gate.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['close'], 
                mode='lines',
                name='Gate.io',
                line=dict(color='blue')
            ))
            fig_gate.update_layout(title="Gate.io価格推移", height=300)
            st.plotly_chart(fig_gate, use_container_width=True)
    
    # 価格差分析
    if hl_result and gate_result and not hl_error and not gate_error:
        st.markdown("#### 💰 価格差分析")
        
        hl_price = hl_result['data']['close'].iloc[-1]
        gate_price = gate_result['data']['close'].iloc[-1]
        price_diff = abs(hl_price - gate_price)
        price_diff_pct = (price_diff / hl_price) * 100
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Hyperliquid", f"${hl_price:,.2f}")
        with col2:
            st.metric("Gate.io", f"${gate_price:,.2f}")
        with col3:
            st.metric("価格差", f"${price_diff:,.2f}", f"{price_diff_pct:.3f}%")

def display_switch_history():
    """切り替え履歴を表示"""
    if st.session_state.exchange_history:
        st.markdown("### 📝 切り替え履歴")
        
        history_df = pd.DataFrame(st.session_state.exchange_history)
        history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
        history_df = history_df.sort_values('timestamp', ascending=False)
        
        # 最新5件を表示
        st.dataframe(
            history_df[['timestamp', 'from', 'to']].head(5),
            use_container_width=True,
            column_config={
                'timestamp': '時刻',
                'from': '切り替え前',
                'to': '切り替え後'
            }
        )
    else:
        st.info("切り替え履歴がありません")

def main():
    """メインアプリケーション"""
    st.title("🔄 取引所切り替えダッシュボード")
    st.markdown("**HyperliquidとGate.ioをブラウザ上でリアルタイム切り替え**")
    st.markdown("---")
    
    if not MULTI_EXCHANGE_AVAILABLE:
        st.error("❌ マルチ取引所APIが利用できません")
        return
    
    # 現在の状態表示
    display_exchange_status()
    st.markdown("---")
    
    # 切り替えUI
    display_exchange_switcher()
    st.markdown("---")
    
    # サイドバー設定
    with st.sidebar:
        st.header("⚙️ データ取得設定")
        
        symbol = st.text_input("銘柄", value="BTC", help="取得する銘柄名")
        timeframe = st.selectbox("時間足", ["1m", "5m", "15m", "30m", "1h", "4h"], index=4)
        days = st.slider("期間（日）", 1, 14, 7)
        
        st.markdown("---")
        st.markdown("### 📊 現在アクティブ")
        if st.session_state.current_exchange == 'hyperliquid':
            st.markdown("🔥 **Hyperliquid**")
            st.markdown("- 高精度データ")
            st.markdown("- レバレッジ制限情報")
            st.markdown("- 直接API接続")
        else:
            st.markdown("🌐 **Gate.io**")
            st.markdown("- CCXT統合API")
            st.markdown("- 先物データ")
            st.markdown("- 豊富な銘柄")
        
        st.markdown("---")
        
        # 自動更新設定
        auto_refresh = st.checkbox("自動更新", value=False)
        if auto_refresh:
            refresh_interval = st.slider("更新間隔（秒）", 5, 60, 30)
            st.markdown(f"⏰ {refresh_interval}秒ごとに自動更新")
    
    # データ比較
    tab1, tab2, tab3 = st.tabs(["📊 データ比較", "🔄 現在の取引所", "📝 履歴"])
    
    with tab1:
        if st.button("📥 データ取得・比較", type="primary", use_container_width=True):
            display_data_comparison(symbol, timeframe, days)
    
    with tab2:
        st.markdown(f"### 現在の取引所: {st.session_state.current_exchange.upper()}")
        
        # 現在の取引所でデータ取得
        if st.button(f"📊 {st.session_state.current_exchange.upper()}からデータ取得", use_container_width=True):
            with st.spinner(f'{st.session_state.current_exchange}からデータ取得中...'):
                result, error = fetch_exchange_data(st.session_state.current_exchange, symbol, timeframe, days)
                
                if error:
                    st.error(f"❌ エラー: {error}")
                elif result:
                    df = result['data']
                    st.success(f"✅ {len(df)}件のデータを取得しました")
                    
                    # チャート表示
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=df['timestamp'],
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name=st.session_state.current_exchange.upper()
                    ))
                    fig.update_layout(
                        title=f"{symbol} - {timeframe} ({st.session_state.current_exchange.upper()})",
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # データテーブル
                    st.dataframe(df.tail(10), use_container_width=True)
    
    with tab3:
        display_switch_history()
        
        if st.button("🗑️ 履歴クリア"):
            st.session_state.exchange_history = []
            st.success("履歴をクリアしました")
            st.rerun()
    
    # 自動更新
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
    
    # フッター
    st.markdown("---")
    st.markdown("### 💡 使用方法")
    st.markdown("""
    1. **🔄 取引所切り替え**: 上部のボタンでHyperliquidとGate.ioを切り替え
    2. **📊 データ比較**: 両取引所のデータを同時取得・比較
    3. **⚙️ 設定保存**: 切り替えは自動的に設定ファイルに保存
    4. **📝 履歴確認**: 切り替え履歴を時系列で確認
    
    **⚠️ 重要**: 切り替えはユーザーが明示的にボタンを押した場合のみ実行されます
    """)

if __name__ == "__main__":
    main()