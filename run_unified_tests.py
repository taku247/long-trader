#!/usr/bin/env python3
"""
プロジェクトルートからの統一テスト実行スクリプト
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tests_organized"))

# 統一テストランナーをインポートして実行
from tests_organized.test_runner import main

if __name__ == "__main__":
    # 作業ディレクトリをプロジェクトルートに設定
    os.chdir(project_root)
    
    print(f"🏠 プロジェクトルート: {project_root}")
    print(f"📂 作業ディレクトリ: {os.getcwd()}")
    
    # テストランナー実行
    main()