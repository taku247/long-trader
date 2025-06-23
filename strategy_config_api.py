#!/usr/bin/env python3
"""
戦略設定管理API

Web Dashboard用の戦略設定CRUD API
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
from typing import Dict, Any, List
from strategy_config_manager import StrategyConfigManager
import sqlite3

class StrategyConfigAPI:
    """戦略設定管理API"""
    
    def __init__(self, app: Flask = None):
        self.manager = StrategyConfigManager()
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Flask アプリケーションにAPIルートを登録"""
        
        @app.route('/api/strategy-configs', methods=['GET'])
        def list_strategy_configs():
            """戦略設定一覧取得"""
            try:
                # クエリパラメータ取得
                base_strategy = request.args.get('base_strategy')
                timeframe = request.args.get('timeframe')
                is_active = request.args.get('is_active')
                is_default = request.args.get('is_default')
                created_by = request.args.get('created_by')
                search = request.args.get('search')
                
                # bool型パラメータの変換
                if is_active is not None:
                    is_active = is_active.lower() in ['true', '1']
                if is_default is not None:
                    is_default = is_default.lower() in ['true', '1']
                
                # 検索またはフィルタ実行
                if search:
                    strategies = self.manager.search_strategies(search)
                else:
                    strategies = self.manager.list_strategies(
                        base_strategy=base_strategy,
                        timeframe=timeframe,
                        is_active=is_active,
                        is_default=is_default,
                        created_by=created_by
                    )
                
                # 使用統計を含める場合
                include_stats = request.args.get('include_stats', '').lower() == 'true'
                if include_stats:
                    for strategy in strategies:
                        strategy['usage_stats'] = self.manager.get_strategy_usage_stats(strategy['id'])
                
                return jsonify({
                    'success': True,
                    'data': strategies,
                    'count': len(strategies)
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/strategy-configs', methods=['POST'])
        def create_strategy_config():
            """戦略設定作成"""
            try:
                data = request.get_json()
                
                # 必須フィールドの確認
                required_fields = ['name', 'base_strategy', 'timeframe', 'parameters']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            'success': False,
                            'error': f'必須フィールドが不足: {field}'
                        }), 400
                
                # 戦略作成
                strategy_id = self.manager.create_strategy(
                    name=data['name'],
                    base_strategy=data['base_strategy'],
                    timeframe=data['timeframe'],
                    parameters=data['parameters'],
                    description=data.get('description', ''),
                    created_by=data.get('created_by', 'api_user')
                )
                
                # 作成された戦略を取得
                created_strategy = self.manager.get_strategy(strategy_id)
                
                return jsonify({
                    'success': True,
                    'data': created_strategy,
                    'message': f'戦略設定 "{data["name"]}" を作成しました'
                }), 201
                
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400
            except sqlite3.IntegrityError as e:
                return jsonify({
                    'success': False,
                    'error': '同名の戦略が既に存在します'
                }), 409
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/strategy-configs/<int:strategy_id>', methods=['GET'])
        def get_strategy_config(strategy_id):
            """戦略設定詳細取得"""
            try:
                strategy = self.manager.get_strategy(strategy_id)
                
                if not strategy:
                    return jsonify({
                        'success': False,
                        'error': '戦略設定が見つかりません'
                    }), 404
                
                # 使用統計も含める
                strategy['usage_stats'] = self.manager.get_strategy_usage_stats(strategy_id)
                
                return jsonify({
                    'success': True,
                    'data': strategy
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/strategy-configs/<int:strategy_id>', methods=['PUT'])
        def update_strategy_config(strategy_id):
            """戦略設定更新"""
            try:
                data = request.get_json()
                
                # 更新実行
                success = self.manager.update_strategy(
                    strategy_id=strategy_id,
                    name=data.get('name'),
                    parameters=data.get('parameters'),
                    description=data.get('description'),
                    is_active=data.get('is_active')
                )
                
                if not success:
                    return jsonify({
                        'success': False,
                        'error': '戦略設定が見つかりません'
                    }), 404
                
                # 更新された戦略を取得
                updated_strategy = self.manager.get_strategy(strategy_id)
                
                return jsonify({
                    'success': True,
                    'data': updated_strategy,
                    'message': '戦略設定を更新しました'
                })
                
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/strategy-configs/<int:strategy_id>', methods=['DELETE'])
        def delete_strategy_config(strategy_id):
            """戦略設定削除"""
            try:
                success = self.manager.delete_strategy(strategy_id)
                
                if not success:
                    return jsonify({
                        'success': False,
                        'error': '戦略設定が見つかりません'
                    }), 404
                
                return jsonify({
                    'success': True,
                    'message': '戦略設定を削除しました'
                })
                
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/strategy-configs/<int:strategy_id>/duplicate', methods=['POST'])
        def duplicate_strategy_config(strategy_id):
            """戦略設定複製"""
            try:
                data = request.get_json()
                new_name = data.get('name')
                
                if not new_name:
                    return jsonify({
                        'success': False,
                        'error': '新しい戦略名が必要です'
                    }), 400
                
                new_strategy_id = self.manager.duplicate_strategy(
                    strategy_id=strategy_id,
                    new_name=new_name,
                    created_by=data.get('created_by', 'api_user')
                )
                
                # 作成された戦略を取得
                new_strategy = self.manager.get_strategy(new_strategy_id)
                
                return jsonify({
                    'success': True,
                    'data': new_strategy,
                    'message': f'戦略設定 "{new_name}" を複製しました'
                }), 201
                
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/strategy-configs/<int:strategy_id>/deactivate', methods=['POST'])
        def deactivate_strategy_config(strategy_id):
            """戦略設定非アクティブ化"""
            try:
                success = self.manager.deactivate_strategy(strategy_id)
                
                if not success:
                    return jsonify({
                        'success': False,
                        'error': '戦略設定が見つかりません'
                    }), 404
                
                return jsonify({
                    'success': True,
                    'message': '戦略設定を非アクティブ化しました'
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/strategy-configs/validate-parameters', methods=['POST'])
        def validate_strategy_parameters():
            """戦略パラメータバリデーション"""
            try:
                data = request.get_json()
                parameters = data.get('parameters', {})
                
                validation_result = self.manager.validate_parameters(parameters)
                
                return jsonify({
                    'success': True,
                    'data': validation_result
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/strategy-configs/options', methods=['GET'])
        def get_strategy_options():
            """戦略設定オプション取得"""
            try:
                return jsonify({
                    'success': True,
                    'data': {
                        'base_strategies': self.manager.get_available_base_strategies(),
                        'timeframes': self.manager.get_available_timeframes(),
                        'parameter_rules': self._get_parameter_rules()
                    }
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/strategy-configs/stats', methods=['GET'])
        def get_strategy_stats():
            """戦略統計情報取得"""
            try:
                # 全体統計
                all_strategies = self.manager.list_strategies(is_active=True)
                
                # ベース戦略別統計
                base_strategy_stats = {}
                for strategy in all_strategies:
                    base = strategy['base_strategy']
                    if base not in base_strategy_stats:
                        base_strategy_stats[base] = 0
                    base_strategy_stats[base] += 1
                
                # 時間足別統計
                timeframe_stats = {}
                for strategy in all_strategies:
                    tf = strategy['timeframe']
                    if tf not in timeframe_stats:
                        timeframe_stats[tf] = 0
                    timeframe_stats[tf] += 1
                
                # 作成者別統計
                creator_stats = {}
                for strategy in all_strategies:
                    creator = strategy['created_by']
                    if creator not in creator_stats:
                        creator_stats[creator] = 0
                    creator_stats[creator] += 1
                
                return jsonify({
                    'success': True,
                    'data': {
                        'total_strategies': len(all_strategies),
                        'base_strategy_distribution': base_strategy_stats,
                        'timeframe_distribution': timeframe_stats,
                        'creator_distribution': creator_stats
                    }
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _get_parameter_rules(self) -> Dict[str, Any]:
        """パラメータ検証ルールを取得"""
        return {
            'risk_multiplier': {
                'type': 'number',
                'min': 0.1,
                'max': 5.0,
                'required': True,
                'description': 'リスク乗数 (ポジションサイズ調整)'
            },
            'confidence_boost': {
                'type': 'number',
                'min': -0.2,
                'max': 0.2,
                'required': False,
                'description': '信頼度調整値'
            },
            'leverage_cap': {
                'type': 'integer',
                'min': 1,
                'max': 500,
                'required': True,
                'description': '最大レバレッジ制限'
            },
            'min_risk_reward': {
                'type': 'number',
                'min': 0.5,
                'max': 10.0,
                'required': True,
                'description': '最小リスクリワード比'
            },
            'stop_loss_percent': {
                'type': 'number',
                'min': 0.5,
                'max': 20.0,
                'required': False,
                'description': 'ストップロス％'
            },
            'take_profit_percent': {
                'type': 'number',
                'min': 1.0,
                'max': 50.0,
                'required': False,
                'description': 'テイクプロフィット％'
            },
            'custom_sltp_calculator': {
                'type': 'string',
                'allowed_values': [
                    'ConservativeSLTPCalculator',
                    'AggressiveSLTPCalculator',
                    'TraditionalSLTPCalculator',
                    'MLSLTPCalculator',
                    'DefaultSLTPCalculator',
                    'CustomSLTPCalculator'
                ],
                'required': False,
                'description': 'カスタムSL/TP計算機'
            }
        }

# スタンドアロン実行用
if __name__ == "__main__":
    from flask import Flask
    
    app = Flask(__name__)
    
    # CORS設定 (開発時のみ)
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    # API初期化
    api = StrategyConfigAPI(app)
    
    # テスト用ルート
    @app.route('/')
    def index():
        return """
        <h1>戦略設定管理API</h1>
        <h2>利用可能なエンドポイント:</h2>
        <ul>
            <li><strong>GET /api/strategy-configs</strong> - 戦略設定一覧</li>
            <li><strong>POST /api/strategy-configs</strong> - 戦略設定作成</li>
            <li><strong>GET /api/strategy-configs/{id}</strong> - 戦略設定詳細</li>
            <li><strong>PUT /api/strategy-configs/{id}</strong> - 戦略設定更新</li>
            <li><strong>DELETE /api/strategy-configs/{id}</strong> - 戦略設定削除</li>
            <li><strong>POST /api/strategy-configs/{id}/duplicate</strong> - 戦略設定複製</li>
            <li><strong>POST /api/strategy-configs/{id}/deactivate</strong> - 戦略設定非アクティブ化</li>
            <li><strong>POST /api/strategy-configs/validate-parameters</strong> - パラメータ検証</li>
            <li><strong>GET /api/strategy-configs/options</strong> - 設定オプション</li>
            <li><strong>GET /api/strategy-configs/stats</strong> - 戦略統計</li>
        </ul>
        """
    
    app.run(debug=True, port=5002)