#!/usr/bin/env python3
"""
音声文字起こし実行スクリプト（ローカルWAVファイル専用）

使用方法:
python run_transcription.py --audio-file /path/to/audio.wav --output ./result.txt
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 設定とメインクラスをインポート
from speech import AudioTranscriptionService
from config import *

# 絶対パスに変換（スクリプトファイル基準）
SCRIPT_DIR = Path(__file__).parent
ABSOLUTE_SERVICE_ACCOUNT_PATH = SCRIPT_DIR / SERVICE_ACCOUNT_PATH

def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description='音声ファイルを文字起こしします（ローカルファイル→ローカル保存）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # WAVファイルを文字起こし
  python run_transcription.py --audio-file /path/to/audio.wav --output ./result.txt
  
  # MP3ファイルを文字起こし（自動でWAVに変換）
  python run_transcription.py --audio-file /path/to/audio.mp3 --output ./result.txt
  
  # チャンクサイズを指定
  python run_transcription.py --audio-file /path/to/audio.wav --output ./result.txt --chunk-size 180000
        """
    )
    
    parser.add_argument(
        '--audio-file',
        required=True,
        help='ローカル音声ファイルのパス（WAV、MP3、FLAC、M4A、OGG対応）'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='出力テキストファイルのパス'
    )
    
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=CHUNK_LENGTH_MS,
        help=f'音声チャンクサイズ（ミリ秒） (デフォルト: {CHUNK_LENGTH_MS})'
    )
    
    return parser.parse_args()

async def main():
    """メイン処理"""
    # 引数解析
    args = parse_arguments()
    
    print("=" * 60)
    print("音声文字起こしサービス")
    print("=" * 60)
    print(f"入力ファイル: {args.audio_file}")
    print(f"出力ファイル: {args.output}")
    print(f"チャンクサイズ: {args.chunk_size}ms")
    print("=" * 60)
    
    # 設定ファイルの検証
    if not ABSOLUTE_SERVICE_ACCOUNT_PATH.exists():
        print(f"エラー: サービスアカウントファイルが見つかりません: {ABSOLUTE_SERVICE_ACCOUNT_PATH}")
        print("config.pyでSERVICE_ACCOUNT_PATHを正しく設定してください。")
        sys.exit(1)
    
    # 入力ファイルの検証
    if not Path(args.audio_file).exists():
        print(f"エラー: 指定された音声ファイルが見つかりません: {args.audio_file}")
        sys.exit(1)
    
    try:
        # サービス初期化
        print("サービスを初期化中...")
        service = AudioTranscriptionService(
            service_account_path=str(ABSOLUTE_SERVICE_ACCOUNT_PATH),
            gcs_bucket_name=GCS_BUCKET_NAME
        )
        
        # 文字起こし処理実行
        print("文字起こし処理を開始します...")
        print("※長時間音声の場合、処理完了まで時間がかかる場合があります。")
        
        success = await service.process_audio_transcription(
            audio_path=args.audio_file,
            output_path=args.output,
            chunk_length_ms=args.chunk_size
        )
        
        print("=" * 60)
        if success:
            print("✅ 文字起こし処理が完了しました！")
            print(f"結果ファイル: {args.output}")
            
            # ファイルサイズを表示
            if Path(args.output).exists():
                file_size = Path(args.output).stat().st_size / 1024  # KB
                print(f"ファイルサイズ: {file_size:.2f}KB")
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
    # 非同期実行
    asyncio.run(main()) 