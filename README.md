# 音声文字起こしサービス

このサービスは、ローカルの音声ファイル（WAV、MP3、FLAC、M4A、OGG）をGoogle Speech-to-Textを使用して文字起こしを行います。長時間音声でも非同期処理により効率的に処理できます。

## 主な機能

- **複数の音声形式対応**: WAV、MP3、FLAC、M4A、OGG形式の音声ファイル
- **自動音声最適化**: Google Speech-to-Textに最適な形式（16kHz、モノラル、WAV）に自動変換
- **長時間音声の自動分割処理**: 大きな音声ファイルを処理可能なチャンクに分割
- **Google Speech-to-Textによる高精度な日本語文字起こし**
- **複数チャンクの並行処理による高速化**
- **ローカル保存**: 結果をローカルのテキストファイルに保存
- **包括的なエラーハンドリングとログ出力**
- **メモリ効率的な処理**

## 必要な準備

### 0. システム要件

- Python 3.8以上
- FFmpeg（音声処理用）

**FFmpegのインストール:**
```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Windows
# https://ffmpeg.org/download.html からダウンロードしてPATHに追加
```

### 1. Google Cloud Platform設定

1. Google Cloud Consoleでプロジェクトを作成
2. Speech-to-Text APIとCloud Storage APIを有効化
3. サービスアカウントを作成し、JSONキーファイルをダウンロード
4. Cloud Storageバケットを作成

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 設定ファイルの編集

`config.py`ファイルを編集し、以下の値を設定してください：

- `SERVICE_ACCOUNT_PATH`: Google Cloud サービスアカウントキーファイルのパス
- `GCS_BUCKET_NAME`: Cloud Storageバケット名

## 使用方法

### 基本的な使用例

#### Pythonコードでの使用

```python
import asyncio
from speech import AudioTranscriptionService
from config import *

async def transcribe_audio():
    # サービス初期化
    service = AudioTranscriptionService(
        service_account_path=SERVICE_ACCOUNT_PATH,
        gcs_bucket_name=GCS_BUCKET_NAME
    )
    
    # 音声ファイルを文字起こし
    success = await service.process_audio_transcription(
        audio_path="/path/to/your/audio.wav",
        output_path="./transcription_result.txt"
    )
    
    if success:
        print("文字起こし完了！")
    else:
        print("処理に失敗しました")

# 実行
asyncio.run(transcribe_audio())
```

### コマンドライン実行

#### WAVファイルを文字起こし
```bash
python run_transcription.py --audio-file /path/to/audio.wav --output ./result.txt
```

#### MP3ファイルを文字起こし（自動でWAVに変換）
```bash
python run_transcription.py --audio-file /path/to/audio.mp3 --output ./result.txt
```

#### チャンクサイズを指定（3分間隔）
```bash
python run_transcription.py --audio-file /path/to/audio.wav --output ./result.txt --chunk-size 180000
```

## 処理フロー

1. **音声ファイル検証**: ファイルの存在、サイズ、形式をチェック
2. **音声最適化**: 必要に応じて16kHz、モノラル、WAV形式に変換
3. **音声分割**: 長時間音声を5分間隔のチャンクに分割
4. **GCSアップロード**: 音声チャンクをGoogle Cloud Storageにアップロード
5. **並行文字起こし**: 複数チャンクを同時に処理（最大5並行）
6. **結果統合**: 各チャンクの文字起こし結果を時系列順に結合
7. **ローカル保存**: 最終的な文字起こし結果をローカルのテキストファイルに保存

## 設定可能なパラメータ

- `CHUNK_LENGTH_MS`: 音声チャンクの長さ（デフォルト：5分）
- `MAX_CONCURRENT_TRANSCRIPTIONS`: 並行処理数（デフォルト：5）
- `TRANSCRIPTION_TIMEOUT`: 文字起こしタイムアウト（デフォルト：1時間）
- `AUDIO_SAMPLE_RATE`: 音声サンプリングレート（デフォルト：16kHz）

## 対応音声形式

- **WAV**: 推奨形式（最適化不要）
- **MP3**: 自動でWAVに変換
- **FLAC**: 自動でWAVに変換
- **M4A**: 自動でWAVに変換
- **OGG**: 自動でWAVに変換

## トラブルシューティング

### よくあるエラーと対処法

1. **認証エラー**: サービスアカウントキーファイルが正しいか確認
2. **権限エラー**: サービスアカウントにCloud StorageとSpeech-to-Text APIの権限があるか確認
3. **FFmpegエラー**: FFmpegがシステムにインストールされているか確認
4. **音声形式エラー**: 対応形式かファイルが破損していないか確認
5. **メモリエラー**: 大きな音声ファイルの場合、チャンクサイズを小さくする
6. **タイムアウトエラー**: `TRANSCRIPTION_TIMEOUT`の値を増やす

### ログの確認

処理中のログは標準出力に表示されます。詳細なデバッグ情報が必要な場合は、`config.py`の`LOG_LEVEL`を`"DEBUG"`に変更してください。

## 制限事項

- 音声言語：日本語（`language_code="ja-JP"`）
- 最大音声長：制限なし（ただし処理時間は音声長に比例）
- Google Cloud APIの利用料金が発生します
- インターネット接続が必要（Google Cloud APIを使用するため）

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。 