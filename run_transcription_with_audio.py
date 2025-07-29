#!/usr/bin/env python3
"""
音声文字起こし実行スクリプト（特定の音声ファイル用）
"""

import asyncio
import sys
from pathlib import Path

# 設定とメインクラスをインポート
from speech import AudioTranscriptionService
from config import *

async def main():
    """メイン処理"""
    
    # 音声ファイルのパス
    AUDIO_FILE_PATH = "/Users/macmini2022/Documents/Cursor/250726_収支予算書の作成方法.wav"
    OUTPUT_FILE_PATH = "./transcription_result.txt"
    
    print("=" * 60)
    print("音声文字起こしサービス")
    print("=" * 60)
    print(f"入力ファイル: {AUDIO_FILE_PATH}")
    print(f"出力ファイル: {OUTPUT_FILE_PATH}")
    print(f"バケット名: {GCS_BUCKET_NAME}")
    print("=" * 60)
    
    # 設定ファイルの検証
    if not Path(SERVICE_ACCOUNT_PATH).exists():
        print(f"エラー: サービスアカウントファイルが見つかりません: {SERVICE_ACCOUNT_PATH}")
        print("config.pyでSERVICE_ACCOUNT_PATHを正しく設定してください。")
        sys.exit(1)
    
    # 入力ファイルの検証
    if not Path(AUDIO_FILE_PATH).exists():
        print(f"エラー: 指定された音声ファイルが見つかりません: {AUDIO_FILE_PATH}")
        sys.exit(1)
    
    try:
        # サービス初期化
        print("サービスを初期化中...")
        service = AudioTranscriptionService(
            service_account_path=SERVICE_ACCOUNT_PATH,
            gcs_bucket_name=GCS_BUCKET_NAME
        )
        
        # 文字起こし処理実行
        print("文字起こし処理を開始します...")
        print("※長時間音声の場合、処理完了まで時間がかかる場合があります。")
        
        success = await service.process_audio_transcription(
            audio_path=AUDIO_FILE_PATH,
            output_path=OUTPUT_FILE_PATH,
            chunk_length_ms=CHUNK_LENGTH_MS
        )
        
        print("=" * 60)
        if success:
            print("✅ 文字起こし処理が完了しました！")
            print(f"結果ファイル: {OUTPUT_FILE_PATH}")
            
            # ファイルサイズを表示
            if Path(OUTPUT_FILE_PATH).exists():
                file_size = Path(OUTPUT_FILE_PATH).stat().st_size / 1024  # KB
                print(f"ファイルサイズ: {file_size:.2f}KB")
                
                # 結果の一部を表示
                with open(OUTPUT_FILE_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                    preview = content[:500] + "..." if len(content) > 500 else content
                    print(f"\n📄 結果プレビュー:\n{preview}")
        else:
            print("❌ 文字起こし処理に失敗しました")
        
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n処理が中断されました。")
        sys.exit(1)
        
    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")
        print("\n詳細なエラー情報:")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 