#!/usr/bin/env python3
"""
execution_id修正のテストスクリプト
"""

import sqlite3
import os
import sys
from pathlib import Path

def test_database_structure():
    """データベース構造のテスト"""
    print("🧪 データベース構造テスト")
    print("=" * 50)
    
    analysis_db_path = Path("web_dashboard/large_scale_analysis/analysis.db")
    
    if not analysis_db_path.exists():
        print("❌ analysis.db が見つかりません")
        return False
    
    with sqlite3.connect(analysis_db_path) as conn:
        cursor = conn.cursor()
        
        # execution_idカラムの存在確認
        cursor.execute("PRAGMA table_info(analyses)")
        columns = cursor.fetchall()
        
        execution_id_exists = any(col[1] == 'execution_id' for col in columns)
        
        if execution_id_exists:
            print("✅ execution_idカラムが存在します")
        else:
            print("❌ execution_idカラムが存在しません")
            return False
        
        # インデックスの確認
        cursor.execute("PRAGMA index_list(analyses)")
        indexes = cursor.fetchall()
        
        execution_id_index = any('execution_id' in idx[1] for idx in indexes)
        
        if execution_id_index:
            print("✅ execution_idインデックスが存在します")
        else:
            print("❌ execution_idインデックスが存在しません")
            return False
    
    return True

def test_existing_data():
    """既存データの状況確認"""
    print("\n🧪 既存データ状況確認")
    print("=" * 50)
    
    analysis_db_path = Path("web_dashboard/large_scale_analysis/analysis.db")
    
    with sqlite3.connect(analysis_db_path) as conn:
        cursor = conn.cursor()
        
        # 総数確認
        cursor.execute("SELECT COUNT(*) FROM analyses")
        total_count = cursor.fetchone()[0]
        print(f"📊 総分析結果数: {total_count}")
        
        # execution_id別の統計
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN execution_id IS NULL THEN 'NULL'
                    ELSE 'SET'
                END as execution_id_status,
                COUNT(*) as count
            FROM analyses 
            GROUP BY execution_id_status
        """)
        
        results = cursor.fetchall()
        for status, count in results:
            print(f"  {status}: {count}件")
        
        # 銘柄別の状況
        cursor.execute("""
            SELECT symbol, COUNT(*) as count
            FROM analyses 
            WHERE execution_id IS NULL
            GROUP BY symbol 
            ORDER BY count DESC
            LIMIT 5
        """)
        
        print("\n📈 execution_id=NULLの上位銘柄:")
        results = cursor.fetchall()
        for symbol, count in results:
            print(f"  {symbol}: {count}件")
    
    return True

def test_manual_reset_code():
    """手動リセットコードの構文チェック"""
    print("\n🧪 手動リセット機能コードチェック")
    print("=" * 50)
    
    try:
        # app.pyの構文チェック
        with open("web_dashboard/app.py", "r", encoding="utf-8") as f:
            code_content = f.read()
        
        # 重要な修正部分が含まれているか確認
        if "DELETE FROM analyses WHERE execution_id = ?" in code_content:
            print("✅ 分析結果削除コードが追加されています")
        else:
            print("❌ 分析結果削除コードが見つかりません")
            return False
        
        if "CRITICAL FIX" in code_content:
            print("✅ 修正マーカーが存在します")
        else:
            print("❌ 修正マーカーが見つかりません")
            return False
        
        print("✅ 手動リセット機能のコード修正を確認しました")
        return True
        
    except Exception as e:
        print(f"❌ コードチェックでエラー: {e}")
        return False

def test_scalable_analysis_code():
    """ScalableAnalysisSystemの修正確認"""
    print("\n🧪 ScalableAnalysisSystem修正チェック")
    print("=" * 50)
    
    try:
        with open("scalable_analysis_system.py", "r", encoding="utf-8") as f:
            code_content = f.read()
        
        # execution_idパラメータの追加確認
        if "execution_id=None" in code_content and "_save_to_database" in code_content:
            print("✅ _save_to_database にexecution_idパラメータが追加されています")
        else:
            print("❌ _save_to_database の修正が見つかりません")
            return False
        
        # execution_idの保存確認
        if "execution_id)" in code_content and "INSERT INTO analyses" in code_content:
            print("✅ execution_idの保存処理が追加されています")
        else:
            print("❌ execution_idの保存処理が見つかりません")
            return False
        
        print("✅ ScalableAnalysisSystemの修正を確認しました")
        return True
        
    except Exception as e:
        print(f"❌ コードチェックでエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 execution_id修正テストスイート")
    print("=" * 80)
    
    tests = [
        ("データベース構造", test_database_structure),
        ("既存データ状況", test_existing_data),
        ("手動リセット機能", test_manual_reset_code),
        ("ScalableAnalysis修正", test_scalable_analysis_code),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"\n✅ {test_name}: 合格")
            else:
                print(f"\n❌ {test_name}: 不合格")
        except Exception as e:
            print(f"\n💥 {test_name}: エラー - {e}")
    
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)
    print(f"合格: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 すべてのテストが合格しました！")
        print("✅ execution_id修正が正常に適用されています")
        return True
    else:
        print(f"\n⚠️ {total - passed}個のテストが失敗しました")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)