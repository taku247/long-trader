"""
アダプターモジュール

既存コードをプラグインインターフェースに適合させるアダプター群。
"""

from .existing_adapters import (
    ExistingSupportResistanceAdapter,
    ExistingMLPredictorAdapter,
    ExistingBTCCorrelationAdapter
)

__all__ = [
    'ExistingSupportResistanceAdapter',
    'ExistingMLPredictorAdapter',
    'ExistingBTCCorrelationAdapter'
]