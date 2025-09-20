#!/usr/bin/env python3
"""
音声文字起こし実行スクリプト（ファイル選択ダイアログ対応）
"""

import asyncio
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# 設定とメインクラスをインポート
from speech import AudioTranscriptionService
from config import SERVICE_ACCOUNT_PATH, GCS_BUCKET_NAME, CHUNK_LENGTH_MS

def select_audio_file():
    """音声ファイル選択ダイアログを表示"""
    
    # macOSの場合、まずosascriptを試す
    if sys.platform == "darwin":
        try:
            return _macos_file_dialog()
        except Exception as e:
            print(f"macOSネイティブダイアログでエラー: {str(e)}")
            print("代替方法を使用します...")
    
    # tkinterダイアログを試す
    try:
        return _tkinter_file_dialog()
    except Exception as e:
        print(f"tkinterダイアログでエラー: {str(e)}")
        return _fallback_file_selection()

def _macos_file_dialog():
    """macOS osascriptを使用したファイル選択ダイアログ"""
    import subprocess
    
    print("macOSネイティブファイル選択ダイアログを開いています...")
    
    # AppleScriptでファイル選択ダイアログを作成
    script = '''
    tell application "System Events"
        activate
    end tell
    
    set allowedTypes to {"wav", "mp3", "m4a", "flac", "aac", "ogg", "WAV", "MP3", "M4A", "FLAC", "AAC", "OGG"}
    set selectedFile to choose file with prompt "文字起こししたい音声ファイルを選択してください" of type allowedTypes
    return POSIX path of selectedFile
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=120  # 2分のタイムアウト
        )
        
        if result.returncode == 0:
            file_path = result.stdout.strip()
            if file_path and Path(file_path).exists():
                print(f"選択されたファイル: {file_path}")
                return file_path
            else:
                print("無効なファイルが選択されました。")
                return None
        else:
            if "User canceled" in result.stderr or result.returncode == 1:
                print("ファイル選択がキャンセルされました。")
                return None
            else:
                raise Exception(f"osascript error: {result.stderr}")
    
    except subprocess.TimeoutExpired:
        print("ファイル選択がタイムアウトしました。")
        return None
    except Exception as e:
        raise Exception(f"macOSダイアログエラー: {str(e)}")

def _tkinter_file_dialog():
    """tkinterを使用したファイル選択ダイアログ"""
    
    # サポートされる音声ファイル形式
    supported_formats = [
        ("音声ファイル", "*.wav;*.mp3;*.m4a;*.flac;*.aac;*.ogg"),
        ("WAVファイル", "*.wav"),
        ("MP3ファイル", "*.mp3"),
        ("M4Aファイル", "*.m4a"),
        ("FLACファイル", "*.flac"),
        ("AACファイル", "*.aac"),
        ("OGGファイル", "*.ogg"),
        ("すべてのファイル", "*.*")
    ]
    
    print("tkinterファイル選択ダイアログを開いています...")
    
    root = None
    try:
        # tkinterのルートウィンドウを作成
        root = tk.Tk()
        root.withdraw()  # メインウィンドウを非表示
        
        # ファイル選択ダイアログを表示
        file_path = filedialog.askopenfilename(
            title="文字起こししたい音声ファイルを選択してください",
            filetypes=supported_formats,
            initialdir=str(Path.cwd())
        )
        
        if not file_path:
            print("ファイル選択がキャンセルされました。")
            return None
            
        if not Path(file_path).exists():
            print(f"エラー: 選択されたファイルが見つかりません: {file_path}")
            return None
        
        print(f"選択されたファイル: {file_path}")
        return file_path
        
    finally:
        if root:
            try:
                root.destroy()
            except:
                pass

def _fallback_file_selection():
    """ダイアログが使用できない場合の代替ファイル選択"""
    print("\nダイアログが使用できないため、代替方法でファイルを選択します。")
    print("コマンドライン版の使用も可能です:")
    print("python run_transcription.py --audio-file /path/to/your/audio.wav --output ./result.txt")
    
    # 現在のディレクトリの音声ファイルを表示
    audio_files = []
    for ext in ['.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg']:
        audio_files.extend(Path.cwd().glob(f'*{ext}'))
        audio_files.extend(Path.cwd().glob(f'*{ext.upper()}'))
    
    if audio_files:
        print("\n現在のディレクトリで利用可能な音声ファイル:")
        for i, file in enumerate(audio_files, 1):
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"{i}. {file.name} ({size_mb:.1f}MB)")
        
        try:
            choice = input(f"\n番号を選択してください (1-{len(audio_files)}): ")
            choice_num = int(choice) - 1
            if 0 <= choice_num < len(audio_files):
                selected_file = str(audio_files[choice_num])
                print(f"選択されたファイル: {selected_file}")
                return selected_file
            else:
                print("無効な番号です。")
                return None
        except (ValueError, KeyboardInterrupt):
            print("選択がキャンセルされました。")
            return None
    else:
        print("音声ファイルが見つかりませんでした。")
        return None

async def main():
    """メイン処理"""
    
    print("=" * 60)
    print("音声文字起こしサービス")
    print("=" * 60)
    print("音声ファイルを選択してください...")
    
    # ファイル選択ダイアログを表示
    AUDIO_FILE_PATH = select_audio_file()
    
    # ユーザーがキャンセルした場合は終了
    if not AUDIO_FILE_PATH:
        print("ファイルが選択されませんでした。処理を終了します。")
        sys.exit(0)
    
    # 出力ファイルのパスを入力ファイル名に基づいて生成
    input_file = Path(AUDIO_FILE_PATH)
    OUTPUT_FILE_PATH = f"./transcription_{input_file.stem}.txt"
    
    print(f"入力ファイル: {AUDIO_FILE_PATH}")
    print(f"出力ファイル: {OUTPUT_FILE_PATH}")
    print(f"バケット名: {GCS_BUCKET_NAME}")
    print("=" * 60)
    
    # 設定ファイルの検証
    if not Path(SERVICE_ACCOUNT_PATH).exists():
        print(f"エラー: サービスアカウントファイルが見つかりません: {SERVICE_ACCOUNT_PATH}")
        print("config.pyでSERVICE_ACCOUNT_PATHを正しく設定してください。")
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
        
    except (OSError, ImportError, RuntimeError) as e:
        print(f"\nエラーが発生しました: {str(e)}")
        print("\n詳細なエラー情報:")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-except
        print(f"\n予期しないエラーが発生しました: {str(e)}")
        print("\n詳細なエラー情報:")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 