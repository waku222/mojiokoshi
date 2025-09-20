#!/usr/bin/env python3
"""
文字起こしWebアプリケーション起動スクリプト
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """アプリケーションを起動"""
    
    # 現在のディレクトリを取得
    app_dir = Path(__file__).parent
    project_root = app_dir.parent
    
    # Python pathを設定
    sys.path.insert(0, str(project_root))
    
    # 必要な環境変数を設定
    os.environ['PYTHONPATH'] = str(project_root)
    
    # Streamlitアプリを起動
    app_path = app_dir / "app.py"
    
    print("🚀 文字起こしWebアプリケーションを起動します...")
    print(f"📁 アプリケーションパス: {app_path}")
    print("🌐 ブラウザで http://localhost:8501 にアクセスしてください")
    print("⏹️  停止するには Ctrl+C を押してください")
    print("-" * 60)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--server.address", "0.0.0.0",
            "--server.port", "8501",
            "--server.headless", "false",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 アプリケーションを停止しました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
