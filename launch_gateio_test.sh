#!/bin/bash
# Gate.io OHLCVテスト画面を起動

echo "🚀 Gate.io先物OHLCVテストツールを起動中..."
echo ""
echo "ブラウザが自動的に開きます。"
echo "終了するには Ctrl+C を押してください。"
echo ""

# Streamlitアプリを起動
streamlit run test_gateio_ohlcv.py --server.port 8502