#!/usr/bin/env python3
"""
設定ファイルのテストスクリプト
"""

from pathlib import Path
from config import *

def test_config():
    """設定をテスト"""
    print("=" * 50)
    print("設定ファイルのテスト")
    print("=" * 50)
    
    print(f"SERVICE_ACCOUNT_PATH: {SERVICE_ACCOUNT_PATH}")
    print(f"GCS_BUCKET_NAME: {GCS_BUCKET_NAME}")
    
    # ファイルの存在確認
    service_account_path = Path(SERVICE_ACCOUNT_PATH)
    print(f"\nサービスアカウントファイルの存在: {service_account_path.exists()}")
    
    if service_account_path.exists():
        print(f"ファイルサイズ: {service_account_path.stat().st_size} bytes")
        print(f"絶対パス: {service_account_path.absolute()}")
    else:
        print("❌ サービスアカウントファイルが見つかりません")
        print(f"期待されるパス: {service_account_path.absolute()}")
    
    # 音声ファイルの存在確認
    audio_file_path = Path("/Users/macmini2022/Documents/Cursor/250726_収支予算書の作成方法.wav")
    print(f"\n音声ファイルの存在: {audio_file_path.exists()}")
    
    if audio_file_path.exists():
        print(f"ファイルサイズ: {audio_file_path.stat().st_size / (1024*1024):.2f} MB")
    else:
        print("❌ 音声ファイルが見つかりません")
    
    print("=" * 50)

if __name__ == "__main__":
    test_config() 