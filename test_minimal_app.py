#!/usr/bin/env python3
"""
Minimal Flask app to test the symbol/add endpoint isolation
"""

import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify

app = Flask(__name__)

# Test the exact symbol/add route
@app.route('/api/symbol/add', methods=['POST'])
def api_symbol_add():
    """Add new symbol with automatic training and backtesting."""
    try:
        data = request.get_json()
        if not data or 'symbol' not in data:
            return jsonify({'error': 'Symbol is required'}), 400
        
        symbol = data['symbol'].upper().strip()
        
        if not symbol:
            return jsonify({'error': 'Invalid symbol'}), 400
        
        # Optional validation - warn but don't block
        import asyncio
        from hyperliquid_validator import HyperliquidValidator, ValidationContext
        
        validation_warnings = []
        
        async def validate_symbol_async():
            async with HyperliquidValidator(strict_mode=False) as validator:  # 非厳格モード
                return await validator.validate_symbol(symbol, ValidationContext.NEW_ADDITION)
        
        # Run validation but don't fail on errors (with timeout)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 10秒タイムアウトを設定
            validation_result = loop.run_until_complete(
                asyncio.wait_for(validate_symbol_async(), timeout=10.0)
            )
            loop.close()
            
            if not validation_result.valid:
                # 警告として記録するが、処理は継続
                print(f"⚠️ Symbol validation warning for {symbol}: {validation_result.reason}")
                validation_warnings.append(f"Warning: {validation_result.reason}")
            else:
                print(f"✅ Symbol {symbol} validated successfully")
                
        except asyncio.TimeoutError:
            # タイムアウトエラー
            print(f"⚠️ Symbol validation timeout for {symbol} (exceeded 10 seconds)")
            validation_warnings.append("Validation timeout: exceeded 10 seconds")
        except Exception as validation_error:
            # バリデーションエラーでも処理を継続
            print(f"⚠️ Symbol validation error for {symbol}: {str(validation_error)}")
            validation_warnings.append(f"Validation error: {str(validation_error)}")
        
        # 基本的なフォーマットチェックのみ必須
        if not symbol.isalnum() or len(symbol) < 2 or len(symbol) > 10:
            return jsonify({
                'error': f'Invalid symbol format: {symbol}',
                'validation_status': 'format_error',
                'symbol': symbol,
                'suggestion': '銘柄名は2-10文字の英数字で入力してください'
            }), 400
        
        # Generate execution ID first, then start training
        from auto_symbol_training import AutoSymbolTrainer
        from datetime import datetime
        import uuid
        
        # Create execution ID that will be used
        execution_id = f"symbol_addition_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        trainer = AutoSymbolTrainer()
        
        # Execute training asynchronously with the predetermined ID
        import threading
        
        def run_training():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Pass the execution_id to ensure consistency
                result_execution_id = loop.run_until_complete(
                    trainer.add_symbol_with_training(symbol, execution_id=execution_id)
                )
                print(f"Symbol {symbol} training started with ID: {result_execution_id}")
            except Exception as e:
                print(f"Training failed for {symbol}: {e}")
            finally:
                loop.close()
        
        # Start training thread
        training_thread = threading.Thread(target=run_training, daemon=True)
        training_thread.start()
        
        print(f"Symbol addition request received: {symbol}")
        
        # レスポンス準備
        response_data = {
            'status': 'started',
            'symbol': symbol,
            'execution_id': execution_id,
            'message': f'{symbol}の学習・バックテストを開始しました'
        }
        
        # バリデーション結果があれば追加
        try:
            if 'validation_result' in locals():
                response_data['validation_status'] = validation_result.status
                if validation_result.market_info:
                    response_data['leverage_limit'] = validation_result.market_info.get('leverage_limit')
        except:
            pass
        
        # 警告があれば追加
        if validation_warnings:
            response_data['warnings'] = validation_warnings
            response_data['message'] += f' (警告: {len(validation_warnings)}件)'
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error adding symbol: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test')
def test():
    return jsonify({'status': 'test endpoint working'})

if __name__ == '__main__':
    print("Testing minimal app...")
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint} ({rule.methods})")
    
    # Test the endpoint
    with app.test_client() as client:
        response = client.post('/api/symbol/add', 
                              json={'symbol': 'ETH'},
                              content_type='application/json')
        print(f"\nTest result:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.get_json()}")