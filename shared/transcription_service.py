import os
import asyncio
import tempfile
from pathlib import Path
from typing import Optional
import logging
import warnings

# Google Cloud関連 - Speech-to-Text v2 API
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.cloud import storage
from google.oauth2 import service_account
from google.api_core.client_options import ClientOptions
import json

# 音声処理関連
from pydub import AudioSegment
from pydub.utils import make_chunks

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# RSA警告を抑制（Google認証の不完全なキーファイル警告）
warnings.filterwarnings('ignore', message='You have provided a malformed keyfile')

class AudioTranscriptionService:
    """
    Speech-to-Text v2 API (Chirp) を使用した音声文字起こしサービス
    """
    
    # v2 APIで利用可能なリージョン
    SUPPORTED_REGIONS = ["us-central1", "eu-west4", "asia-southeast1"]
    
    def __init__(self, 
                 service_account_path: str = None,
                 gcs_bucket_name: str = None,
                 service_account_info: dict = None,
                 location: str = "asia-southeast1"):
        """
        音声文字起こしサービス（ローカルWAVファイル専用）- v2 API対応
        
        Args:
            service_account_path: Google Cloud Speech-to-Text用のサービスアカウントキーファイルパス
            gcs_bucket_name: Google Cloud Storage バケット名（長時間音声処理用）
            service_account_info: サービスアカウントの認証情報（辞書形式）
            location: v2 APIのリージョン（デフォルト: asia-southeast1）
        """
        self.service_account_path = service_account_path
        self.gcs_bucket_name = gcs_bucket_name
        self.service_account_info = service_account_info
        self.location = location
        
        # リージョンの検証
        if location not in self.SUPPORTED_REGIONS:
            logger.warning(f"指定されたリージョン '{location}' はv2 APIでサポートされていない可能性があります")
            logger.info(f"サポートされているリージョン: {self.SUPPORTED_REGIONS}")
        
        # 認証方法を決定
        if service_account_info:
            # Streamlit Secrets等からのJSONデータを使用
            credentials = service_account.Credentials.from_service_account_info(service_account_info)
            self.project_id = service_account_info.get("project_id")
            
            # v2 API用のクライアントオプション（リージョンエンドポイント）
            client_options = ClientOptions(
                api_endpoint=f"{location}-speech.googleapis.com"
            )
            self.speech_client = SpeechClient(
                credentials=credentials,
                client_options=client_options
            )
            self.storage_client = storage.Client(credentials=credentials)
            
        elif service_account_path:
            # ファイルパスから認証情報を読み込み
            with open(service_account_path, 'r') as f:
                sa_info = json.load(f)
            self.project_id = sa_info.get("project_id")
            
            credentials = service_account.Credentials.from_service_account_file(service_account_path)
            
            # v2 API用のクライアントオプション（リージョンエンドポイント）
            client_options = ClientOptions(
                api_endpoint=f"{location}-speech.googleapis.com"
            )
            self.speech_client = SpeechClient(
                credentials=credentials,
                client_options=client_options
            )
            self.storage_client = storage.Client.from_service_account_json(service_account_path)
        else:
            raise ValueError("service_account_pathまたはservice_account_infoのいずれかを指定してください")
        
        # Recognizerのパスを設定（v2 APIでは必須）
        self.recognizer_path = f"projects/{self.project_id}/locations/{self.location}/recognizers/_"
        logger.info(f"Speech-to-Text v2 API (Chirp) を使用 - リージョン: {location}")
    
    def validate_audio_file(self, audio_path: str) -> bool:
        """
        ローカル音声ファイルの存在と形式を検証
        
        Args:
            audio_path: ローカル音声ファイルパス
            
        Returns:
            bool: 検証成功フラグ
        """
        try:
            path = Path(audio_path)
            
            # ファイル存在チェック
            if not path.exists():
                logger.error(f"ファイルが見つかりません: {audio_path}")
                return False
            
            # ファイルサイズチェック
            file_size = path.stat().st_size
            if file_size == 0:
                logger.error(f"ファイルが空です: {audio_path}")
                return False
            
            # ファイルサイズをログ出力
            size_mb = file_size / (1024 * 1024)
            logger.info(f"音声ファイルサイズ: {size_mb:.2f}MB")
            
            # 対応形式チェック（拡張子ベース）
            supported_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.ogg'}
            if path.suffix.lower() not in supported_extensions:
                logger.warning(f"未対応の可能性がある形式: {path.suffix}")
                logger.info("WAV形式への変換を試行します")
            
            return True
            
        except Exception as e:
            logger.error(f"ファイル検証エラー: {str(e)}")
            return False
    
    async def convert_to_wav_if_needed(self, audio_path: str, output_path: str) -> bool:
        """
        音声ファイルをWAV形式に変換（必要な場合のみ）
        
        Args:
            audio_path: 入力音声ファイルパス
            output_path: 出力WAVファイルパス
            
        Returns:
            bool: 変換成功フラグ
        """
        try:
            path = Path(audio_path)
            
            # すでにWAVファイルで適切な形式の場合はコピーのみ
            if path.suffix.lower() == '.wav':
                # WAVファイルの詳細チェック
                audio = AudioSegment.from_wav(audio_path)
                
                # Google Speech-to-Textに最適な形式かチェック
                if audio.frame_rate == 16000 and audio.channels == 1:
                    logger.info("音声ファイルは既に最適な形式です")
                    if audio_path != output_path:
                        import shutil
                        shutil.copy2(audio_path, output_path)
                    return True
            
            logger.info("音声ファイルを最適化中...")
            
            def convert_audio():
                try:
                    # 音声ファイルを読み込み
                    if path.suffix.lower() == '.wav':
                        audio = AudioSegment.from_wav(audio_path)
                    elif path.suffix.lower() == '.mp3':
                        audio = AudioSegment.from_mp3(audio_path)
                    elif path.suffix.lower() == '.flac':
                        # FLACファイルの場合、librosaを使用してFFmpegの依存関係を回避
                        try:
                            import librosa
                            import soundfile as sf
                            import numpy as np
                            
                            # librosaで読み込み
                            y, sr = librosa.load(audio_path, sr=None)
                            
                            # AudioSegmentオブジェクトを作成
                            # float32をint16に変換
                            y_int16 = (y * 32767).astype(np.int16)
                            audio = AudioSegment(
                                y_int16.tobytes(),
                                frame_rate=sr,
                                sample_width=2,  # 16-bit = 2 bytes
                                channels=1
                            )
                            
                        except ImportError:
                            # librosaがない場合はpydubで試行
                            audio = AudioSegment.from_file(audio_path, format="flac")
                    elif path.suffix.lower() == '.m4a':
                        audio = AudioSegment.from_file(audio_path, format="m4a")
                    elif path.suffix.lower() == '.ogg':
                        audio = AudioSegment.from_ogg(audio_path)
                    else:
                        # 汎用的な読み込み
                        audio = AudioSegment.from_file(audio_path)
                    
                    # 音声情報をログ出力
                    logger.info(f"音声時間: {len(audio) / 1000:.2f}秒")
                    logger.info(f"サンプリングレート: {audio.frame_rate}Hz")
                    logger.info(f"チャンネル数: {audio.channels}")
                    
                    # Google Speech-to-Textに最適化（16kHz、モノラル）
                    audio = audio.set_frame_rate(16000).set_channels(1)
                    
                    # WAV形式で保存
                    audio.export(output_path, format="wav")
                    
                except Exception as e:
                    logger.error(f"音声変換中にエラー: {str(e)}")
                    raise
            
            await asyncio.to_thread(convert_audio)
            
            # 変換された音声ファイルの検証
            if not os.path.exists(output_path):
                raise Exception("音声ファイルの変換に失敗")
            
            audio_size = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"音声最適化完了 - ファイルサイズ: {audio_size:.2f}MB")
            return True
            
        except Exception as e:
            logger.error(f"音声変換エラー: {str(e)}")
            return False
    
    async def split_audio_for_processing(self, audio_path: str, chunk_length_ms: int = 300000) -> list:
        """
        長時間音声を処理可能なチャンクに分割
        
        Args:
            audio_path: 音声ファイルパス
            chunk_length_ms: チャンクの長さ（ミリ秒）デフォルト5分
            
        Returns:
            list: 分割された音声ファイルパスのリスト
        """
        try:
            logger.info("音声ファイルを分割中...")
            
            # 音声分割処理をスレッドで実行
            def split_audio():
                audio = AudioSegment.from_wav(audio_path)
                chunks = make_chunks(audio, chunk_length_ms)
                
                chunk_files = []
                temp_dir = tempfile.mkdtemp()
                
                for i, chunk in enumerate(chunks):
                    chunk_path = os.path.join(temp_dir, f"chunk_{i:04d}.wav")
                    chunk.export(chunk_path, format="wav")
                    chunk_files.append(chunk_path)
                
                return chunk_files
            
            chunk_files = await asyncio.to_thread(split_audio)
                
            logger.info(f"音声を{len(chunk_files)}個のチャンクに分割完了")
            return chunk_files
            
        except Exception as e:
            logger.error(f"音声分割エラー: {str(e)}")
            return []
    
    async def upload_to_gcs(self, local_path: str, gcs_path: str) -> bool:
        """
        ファイルをGoogle Cloud Storageにアップロード
        
        Args:
            local_path: ローカルファイルパス
            gcs_path: GCS上のパス
            
        Returns:
            bool: アップロード成功フラグ
        """
        try:
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(local_path)
            logger.info(f"GCSにアップロード完了: {gcs_path}")
            return True
            
        except Exception as e:
            logger.error(f"GCSアップロードエラー: {str(e)}")
            return False
    
    async def transcribe_audio_chunk(self, gcs_uri: str, chunk_index: int) -> Optional[str]:
        """
        音声チャンクを文字起こし（v2 API - Chirpモデル使用）
        
        Args:
            gcs_uri: GCS上の音声ファイルURI
            chunk_index: チャンクのインデックス
            
        Returns:
            Optional[str]: 文字起こし結果
        """
        try:
            logger.info(f"チャンク {chunk_index} の文字起こし開始 (Chirpモデル)")
            
            # v2 API用の認識設定
            config = cloud_speech.RecognitionConfig(
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                language_codes=["ja-JP"],  # 日本語
                model="chirp",  # Chirpモデル（最新の高精度モデル）
                features=cloud_speech.RecognitionFeatures(
                    enable_automatic_punctuation=True,  # 自動句読点
                    enable_word_time_offsets=True,  # 単語レベルのタイムスタンプ
                ),
            )
            
            # バッチ認識用のファイル設定
            file_metadata = cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri)
            
            # 出力設定（インラインで結果を取得）
            output_config = cloud_speech.RecognitionOutputConfig(
                inline_response_config=cloud_speech.InlineOutputConfig()
            )
            
            # バッチ認識リクエスト
            request = cloud_speech.BatchRecognizeRequest(
                recognizer=self.recognizer_path,
                config=config,
                files=[file_metadata],
                recognition_output_config=output_config,
            )
            
            # ブロッキング処理をスレッドで実行
            operation = await asyncio.to_thread(
                self.speech_client.batch_recognize,
                request=request
            )

            logger.info(f"チャンク {chunk_index} の認識処理を待機中...")

            # operation.result自体もブロッキングのためスレッド実行
            response = await asyncio.to_thread(operation.result, timeout=3600)  # 最大1時間待機
            
            # 結果を結合
            transcript = ""
            for file_result in response.results.values():
                if hasattr(file_result, 'inline_result') and file_result.inline_result:
                    for result in file_result.inline_result.transcript.results:
                        for alternative in result.alternatives:
                            transcript += alternative.transcript + " "
            
            logger.info(f"チャンク {chunk_index} の文字起こし完了")
            return transcript.strip()
            
        except Exception as e:
            logger.error(f"チャンク {chunk_index} の文字起こしエラー: {str(e)}")
            return None
    
    async def process_audio_chunks_parallel(self, chunk_files: list) -> list:
        """
        複数の音声チャンクを並行処理で文字起こし
        
        Args:
            chunk_files: 音声チャンクファイルのリスト
            
        Returns:
            list: 文字起こし結果のリスト
        """
        tasks = []
        gcs_uris = []
        
        # 各チャンクをGCSにアップロード
        for i, chunk_file in enumerate(chunk_files):
            gcs_path = f"audio_chunks/chunk_{i:04d}.wav"
            await self.upload_to_gcs(chunk_file, gcs_path)
            gcs_uri = f"gs://{self.gcs_bucket_name}/{gcs_path}"
            gcs_uris.append(gcs_uri)
        
        # 並行処理で文字起こし実行
        for i, gcs_uri in enumerate(gcs_uris):
            task = self.transcribe_audio_chunk(gcs_uri, i)
            tasks.append(task)
        
        # 同時実行数を制限（APIレート制限対策）
        semaphore = asyncio.Semaphore(5)  # 最大5並行
        
        async def limited_transcribe(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[limited_transcribe(task) for task in tasks])
        return results
    
    async def save_transcript_locally(self, 
                                    transcript: str, 
                                    output_path: str) -> bool:
        """
        文字起こし結果をローカルファイルに保存
        
        Args:
            transcript: 文字起こし結果
            output_path: ローカル保存パス
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            logger.info(f"文字起こし結果をローカルに保存中: {output_path}")
            
            # ディレクトリが存在しない場合は作成
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # UTF-8でファイル保存
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transcript)
            
            # ファイルサイズ確認
            file_size = os.path.getsize(output_path) / 1024  # KB
            logger.info(f"ローカル保存完了 - ファイルサイズ: {file_size:.2f}KB")
            
            return True
            
        except Exception as e:
            logger.error(f"ローカル保存エラー: {str(e)}")
            return False
    
    async def process_audio_transcription(self, 
                                        audio_path: str, 
                                        output_path: str,
                                        chunk_length_ms: int = 300000) -> bool:
        """
        ローカル音声ファイルの文字起こし処理
        
        Args:
            audio_path: ローカル音声ファイルパス
            output_path: 出力テキストファイルパス
            chunk_length_ms: チャンクの長さ（ミリ秒）
            
        Returns:
            bool: 処理成功フラグ
        """
        # 入力ファイル検証
        if not self.validate_audio_file(audio_path):
            raise Exception("入力音声ファイルの検証に失敗")
        
        temp_dir = tempfile.mkdtemp()
        wav_path = os.path.join(temp_dir, "optimized_audio.wav")
        chunk_files = []
        
        try:
            logger.info("音声ファイルの文字起こし処理を開始 (Speech-to-Text v2 API - Chirp)")
            logger.info(f"入力ファイル: {audio_path}")
            logger.info(f"出力ファイル: {output_path}")
            
            # 1. 音声ファイルをWAV形式に変換・最適化（必要な場合のみ）
            if not await self.convert_to_wav_if_needed(audio_path, wav_path):
                raise Exception("音声ファイルの最適化に失敗")
            
            # 2. 音声を処理可能なチャンクに分割
            chunk_files = await self.split_audio_for_processing(wav_path, chunk_length_ms)
            if not chunk_files:
                raise Exception("音声分割に失敗")
            
            # 3. 並行処理で文字起こし実行
            transcripts = await self.process_audio_chunks_parallel(chunk_files)
            
            # 4. 結果を結合
            final_transcript = "\n".join([t for t in transcripts if t])
            
            if not final_transcript.strip():
                raise Exception("文字起こし結果が空です")
            
            # 5. 結果をローカルに保存
            success = await self.save_transcript_locally(final_transcript, output_path)
            if not success:
                raise Exception("ローカル保存に失敗")
            
            logger.info("音声ファイルの文字起こし処理完了")
            return True
            
        except Exception as e:
            logger.error(f"処理エラー: {str(e)}")
            raise
        
        finally:
            # クリーンアップ
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            for chunk_file in chunk_files:
                if os.path.exists(chunk_file):
                    os.unlink(chunk_file)

# 使用例
async def main():
    """
    使用例のメイン関数
    """
    # 設定
    SERVICE_ACCOUNT_PATH = "path/to/google-cloud-service-account.json"
    GCS_BUCKET_NAME = "your-gcs-bucket-name"
    
    # 音声ファイルパス
    AUDIO_FILE_PATH = "/path/to/your/audio.wav"
    
    # 出力設定
    OUTPUT_FILE_PATH = "./transcription_result.txt"
    
    # サービス初期化（v2 API - Chirpモデル）
    service = AudioTranscriptionService(
        service_account_path=SERVICE_ACCOUNT_PATH,
        gcs_bucket_name=GCS_BUCKET_NAME,
        location="asia-southeast1"  # アジア圏に近いリージョン
    )
    
    try:
        # 文字起こし処理実行
        success = await service.process_audio_transcription(
            audio_path=AUDIO_FILE_PATH,
            output_path=OUTPUT_FILE_PATH,
            chunk_length_ms=300000  # 5分チャンク
        )
        
        if success:
            print(f"文字起こし完了！結果: {OUTPUT_FILE_PATH}")
        else:
            print("文字起こし処理に失敗しました")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    # 非同期実行
    asyncio.run(main())
