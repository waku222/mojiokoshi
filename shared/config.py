"""
音声文字起こしサービスの設定ファイル（ローカルWAVファイル専用）
使用前に適切な値を設定してください
"""

import os

# Google Cloud Speech-to-Text用のサービスアカウントキーファイルパス
SERVICE_ACCOUNT_PATH = "./credentials/service-account-key.json"

# Google Cloud Storage バケット名（長時間音声処理用）
# 環境変数GCS_BUCKET_NAMEから取得し、未設定の場合は空文字列
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")

# 音声チャンクの長さ（ミリ秒）デフォルト5分
CHUNK_LENGTH_MS = 300000

# 並行処理の最大数（APIレート制限対策）
MAX_CONCURRENT_TRANSCRIPTIONS = 5

# 長時間認識のタイムアウト（秒）
TRANSCRIPTION_TIMEOUT = 3600

# 音声設定
AUDIO_SAMPLE_RATE = 16000  # Hz
AUDIO_CHANNELS = 1  # モノラル
AUDIO_FORMAT = "wav"

# ログレベル
LOG_LEVEL = "INFO"