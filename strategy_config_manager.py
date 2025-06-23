#!/usr/bin/env python3
"""
戦略設定管理クラス

strategy_configurations テーブルの操作を行うクラス
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

class StrategyConfigManager:
    """戦略設定管理クラス"""
    
    def __init__(self, db_path: str = None):
        import os
        
        # テスト環境での DB パス優先
        if db_path is None:
            db_path = os.environ.get('TEST_STRATEGY_DB_PATH', "large_scale_analysis/analysis.db")
        
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        """データベースとテーブルの存在確認"""
        if not Path(self.db_path).exists():
            # DBが存在しない場合は親ディレクトリを作成
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
        with sqlite3.connect(self.db_path) as conn:
            # strategy_configurations テーブルが存在しない場合は作成
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    base_strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    description TEXT,
                    created_by TEXT DEFAULT 'system',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_default BOOLEAN DEFAULT 0,
                    
                    UNIQUE(name, base_strategy, timeframe)
                )
            """)
    
    def create_strategy(self, 
                       name: str,
                       base_strategy: str,
                       timeframe: str,
                       parameters: Dict[str, Any],
                       description: str = "",
                       created_by: str = "user") -> int:
        """
        新しい戦略設定を作成
        
        Args:
            name: 戦略名
            base_strategy: ベース戦略 (Conservative_ML, Aggressive_ML等)
            timeframe: 時間足 (15m, 30m, 1h等)
            parameters: パラメータ辞書
            description: 説明
            created_by: 作成者
            
        Returns:
            作成された戦略のID
            
        Raises:
            ValueError: パラメータが無効な場合
            sqlite3.IntegrityError: 重複する戦略名の場合
        """
        # パラメータバリデーション
        validation_result = self.validate_parameters(parameters)
        if not validation_result['valid']:
            raise ValueError(f"パラメータエラー: {', '.join(validation_result['errors'])}")
        
        parameters_json = json.dumps(parameters)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO strategy_configurations 
                (name, base_strategy, timeframe, parameters, description, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, base_strategy, timeframe, parameters_json, description, created_by))
            
            strategy_id = cursor.lastrowid
            conn.commit()
            
            return strategy_id
    
    def get_strategy(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """
        戦略設定を取得
        
        Args:
            strategy_id: 戦略ID
            
        Returns:
            戦略設定辞書 (存在しない場合はNone)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM strategy_configurations WHERE id = ?
            """, (strategy_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            strategy = dict(row)
            # パラメータをJSONから復元
            strategy['parameters'] = json.loads(strategy['parameters'])
            
            return strategy
    
    def list_strategies(self, 
                       base_strategy: Optional[str] = None,
                       timeframe: Optional[str] = None,
                       is_active: Optional[bool] = None,
                       is_default: Optional[bool] = None,
                       created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        戦略設定一覧を取得
        
        Args:
            base_strategy: ベース戦略でフィルタ
            timeframe: 時間足でフィルタ
            is_active: アクティブ状態でフィルタ
            is_default: デフォルト戦略でフィルタ
            created_by: 作成者でフィルタ
            
        Returns:
            戦略設定のリスト
        """
        where_conditions = []
        params = []
        
        if base_strategy is not None:
            where_conditions.append("base_strategy = ?")
            params.append(base_strategy)
        
        if timeframe is not None:
            where_conditions.append("timeframe = ?")
            params.append(timeframe)
        
        if is_active is not None:
            where_conditions.append("is_active = ?")
            params.append(is_active)
        
        if is_default is not None:
            where_conditions.append("is_default = ?")
            params.append(is_default)
        
        if created_by is not None:
            where_conditions.append("created_by = ?")
            params.append(created_by)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"""
                SELECT * FROM strategy_configurations 
                {where_clause}
                ORDER BY base_strategy, timeframe, name
            """, params)
            
            strategies = []
            for row in cursor.fetchall():
                strategy = dict(row)
                strategy['parameters'] = json.loads(strategy['parameters'])
                strategies.append(strategy)
            
            return strategies
    
    def update_strategy(self, 
                       strategy_id: int,
                       name: Optional[str] = None,
                       parameters: Optional[Dict[str, Any]] = None,
                       description: Optional[str] = None,
                       is_active: Optional[bool] = None) -> bool:
        """
        戦略設定を更新
        
        Args:
            strategy_id: 戦略ID
            name: 新しい戦略名
            parameters: 新しいパラメータ
            description: 新しい説明
            is_active: アクティブ状態
            
        Returns:
            更新成功の場合True
        """
        # 既存戦略の確認
        existing_strategy = self.get_strategy(strategy_id)
        if not existing_strategy:
            return False
        
        update_fields = []
        params = []
        
        if name is not None:
            update_fields.append("name = ?")
            params.append(name)
        
        if parameters is not None:
            # パラメータバリデーション
            validation_result = self.validate_parameters(parameters)
            if not validation_result['valid']:
                raise ValueError(f"パラメータエラー: {', '.join(validation_result['errors'])}")
            
            update_fields.append("parameters = ?")
            params.append(json.dumps(parameters))
        
        if description is not None:
            update_fields.append("description = ?")
            params.append(description)
        
        if is_active is not None:
            update_fields.append("is_active = ?")
            params.append(is_active)
        
        if not update_fields:
            return True  # 更新するフィールドがない場合は成功とする
        
        # updated_at を常に更新
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(strategy_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                UPDATE strategy_configurations 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """, params)
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_strategy(self, strategy_id: int) -> bool:
        """
        戦略設定を削除
        
        Args:
            strategy_id: 戦略ID
            
        Returns:
            削除成功の場合True
        """
        # デフォルト戦略は削除できない
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return False
        
        if strategy['is_default']:
            raise ValueError("デフォルト戦略は削除できません")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM strategy_configurations WHERE id = ?
            """, (strategy_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def deactivate_strategy(self, strategy_id: int) -> bool:
        """
        戦略設定を非アクティブ化
        
        Args:
            strategy_id: 戦略ID
            
        Returns:
            更新成功の場合True
        """
        return self.update_strategy(strategy_id, is_active=False)
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        戦略パラメータのバリデーション
        
        Args:
            parameters: パラメータ辞書
            
        Returns:
            バリデーション結果 {'valid': bool, 'errors': List[str]}
        """
        errors = []
        
        # パラメータ検証ルール
        validation_rules = {
            'risk_multiplier': {
                'type': (int, float),
                'min': 0.1,
                'max': 5.0,
                'required': True
            },
            'confidence_boost': {
                'type': (int, float),
                'min': -0.2,
                'max': 0.2,
                'required': False
            },
            'leverage_cap': {
                'type': int,
                'min': 1,
                'max': 500,
                'required': True
            },
            'min_risk_reward': {
                'type': (int, float),
                'min': 0.5,
                'max': 10.0,
                'required': True
            },
            'stop_loss_percent': {
                'type': (int, float),
                'min': 0.5,
                'max': 20.0,
                'required': False
            },
            'take_profit_percent': {
                'type': (int, float),
                'min': 1.0,
                'max': 50.0,
                'required': False
            },
            'custom_sltp_calculator': {
                'type': str,
                'allowed_values': [
                    'ConservativeSLTPCalculator',
                    'AggressiveSLTPCalculator',
                    'TraditionalSLTPCalculator',
                    'MLSLTPCalculator',
                    'DefaultSLTPCalculator',
                    'CustomSLTPCalculator'
                ],
                'required': False
            }
        }
        
        # 必須パラメータチェック
        for param_name, rule in validation_rules.items():
            if rule.get('required', False) and param_name not in parameters:
                errors.append(f"必須パラメータが不足: {param_name}")
        
        # 各パラメータの検証
        for param_name, value in parameters.items():
            if param_name not in validation_rules:
                errors.append(f"未知のパラメータ: {param_name}")
                continue
            
            rule = validation_rules[param_name]
            
            # 型チェック
            if not isinstance(value, rule['type']):
                errors.append(f"{param_name}: 型エラー (期待: {rule['type']}, 実際: {type(value)})")
                continue
            
            # 範囲チェック
            if 'min' in rule and value < rule['min']:
                errors.append(f"{param_name}: 値が最小値を下回る ({value} < {rule['min']})")
            
            if 'max' in rule and value > rule['max']:
                errors.append(f"{param_name}: 値が最大値を上回る ({value} > {rule['max']})")
            
            # 許可された値のチェック
            if 'allowed_values' in rule and value not in rule['allowed_values']:
                errors.append(f"{param_name}: 許可されていない値 '{value}'")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def get_available_base_strategies(self) -> List[str]:
        """利用可能なベース戦略のリストを取得"""
        return [
            'Conservative_ML',
            'Aggressive_ML',
            'Balanced',
            'Traditional',
            'Full_ML',
            'Custom_ML'
        ]
    
    def get_available_timeframes(self) -> List[str]:
        """利用可能な時間足のリストを取得"""
        return ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d']
    
    def duplicate_strategy(self, strategy_id: int, new_name: str, created_by: str = "user") -> int:
        """
        戦略設定を複製
        
        Args:
            strategy_id: 複製元の戦略ID
            new_name: 新しい戦略名
            created_by: 作成者
            
        Returns:
            新しい戦略のID
        """
        original_strategy = self.get_strategy(strategy_id)
        if not original_strategy:
            raise ValueError(f"戦略ID {strategy_id} が見つかりません")
        
        return self.create_strategy(
            name=new_name,
            base_strategy=original_strategy['base_strategy'],
            timeframe=original_strategy['timeframe'],
            parameters=original_strategy['parameters'],
            description=f"Copied from: {original_strategy['name']}",
            created_by=created_by
        )
    
    def search_strategies(self, search_term: str) -> List[Dict[str, Any]]:
        """
        戦略名または説明で検索
        
        Args:
            search_term: 検索語
            
        Returns:
            マッチした戦略のリスト
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM strategy_configurations 
                WHERE (name LIKE ? OR description LIKE ?) AND is_active = 1
                ORDER BY name
            """, (f"%{search_term}%", f"%{search_term}%"))
            
            strategies = []
            for row in cursor.fetchall():
                strategy = dict(row)
                strategy['parameters'] = json.loads(strategy['parameters'])
                strategies.append(strategy)
            
            return strategies
    
    def get_strategy_usage_stats(self, strategy_id: int) -> Dict[str, Any]:
        """
        戦略の使用統計を取得 (analyses テーブルから)
        
        Args:
            strategy_id: 戦略ID
            
        Returns:
            使用統計情報
        """
        with sqlite3.connect(self.db_path) as conn:
            # 分析回数
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses WHERE strategy_config_id = ?
            """, (strategy_id,))
            analysis_count = cursor.fetchone()[0]
            
            # パフォーマンス統計
            cursor = conn.execute("""
                SELECT 
                    AVG(sharpe_ratio) as avg_sharpe,
                    MAX(sharpe_ratio) as max_sharpe,
                    MIN(sharpe_ratio) as min_sharpe,
                    AVG(total_return) as avg_return,
                    MAX(total_return) as max_return,
                    AVG(win_rate) as avg_win_rate
                FROM analyses 
                WHERE strategy_config_id = ? AND sharpe_ratio IS NOT NULL
            """, (strategy_id,))
            
            stats_row = cursor.fetchone()
            
            return {
                'analysis_count': analysis_count,
                'avg_sharpe_ratio': stats_row[0] if stats_row[0] else 0,
                'max_sharpe_ratio': stats_row[1] if stats_row[1] else 0,
                'min_sharpe_ratio': stats_row[2] if stats_row[2] else 0,
                'avg_total_return': stats_row[3] if stats_row[3] else 0,
                'max_total_return': stats_row[4] if stats_row[4] else 0,
                'avg_win_rate': stats_row[5] if stats_row[5] else 0
            }