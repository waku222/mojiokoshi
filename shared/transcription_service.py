import os
import asyncio
import tempfile
from pathlib import Path
from typing import Optional
import logging

# Google Cloud関連
from google.cloud import speech
from google.cloud import storage
from google.oauth2 import service_account
import json

# 音声処理関連
from pydub import AudioSegment
from pydub.utils import make_chunks

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AudioTranscriptionService:
    def __init__(self, 
                 service_account_path: str = None,
                 gcs_bucket_name: str = None,
                 service_account_info: dict = None):
        """
        音声文字起こしサービス（ローカルWAVファイル専用）
        
        Args:
            service_account_path: Google Cloud Speech-to-Text用のサービスアカウントキーファイルパス
            gcs_bucket_name: Google Cloud Storage バケット名（長時間音声処理用）
            service_account_info: サービスアカウントの認証情報（辞書形式）
        """
        self.service_account_path = service_account_path
        self.gcs_bucket_name = gcs_bucket_name
        self.service_account_info = service_account_info
        
        # 認証方法を決定（Base64エラー対策版）
        if service_account_info:
            # Streamlit Secrets等からのJSONデータを使用（Base64修正処理追加）
            try:
                # サービスアカウント情報のBase64関連データを修正
                fixed_service_account_info = self._fix_base64_in_service_account(service_account_info)
                
                credentials = service_account.Credentials.from_service_account_info(fixed_service_account_info)
                self.speech_client = speech.SpeechClient(credentials=credentials)
                self.storage_client = storage.Client(credentials=credentials)
                logger.info("✅ 認証成功（Base64修正版）")
                
            except Exception as e:
                logger.error(f"❌ 認証エラー（Base64関連）: {e}")
                # デバッグ情報を出力
                logger.error(f"サービスアカウント情報キー: {list(service_account_info.keys())}")
                if 'private_key' in service_account_info:
                    private_key_len = len(service_account_info['private_key'])
                    logger.error(f"private_key長: {private_key_len}")
                raise
        elif service_account_path:
            # ファイルパスから認証情報を読み込み
            self.speech_client = speech.SpeechClient.from_service_account_file(service_account_path)
            self.storage_client = storage.Client.from_service_account_json(service_account_path)
        else:
            raise ValueError("service_account_pathまたはservice_account_infoのいずれかを指定してください")
    
    def _fix_base64_in_service_account(self, service_account_info: dict) -> dict:
        """サービスアカウント情報のBase64データを修正"""
        import base64
        import re
        
        fixed_info = service_account_info.copy()
        
        if 'private_key' in fixed_info:
            private_key = fixed_info['private_key']
            logger.info(f"Private key修正開始（長さ: {len(private_key)}）")
            
            try:
                # 診断情報を詳細に記録
                has_begin = '-----BEGIN PRIVATE KEY-----' in private_key
                has_end = '-----END PRIVATE KEY-----' in private_key
                key_length = len(private_key)
                
                logger.info(f"🔍 Private key診断: 長さ={key_length}, BEGIN={has_begin}, END={has_end}")
                
                # 緩い早期バリデーション（基本的な構造のみチェック）
                if not has_begin or not has_end or key_length < 100:
                    error_msg = f'private_keyが不完全です。長さ:{key_length}, BEGIN:{has_begin}, END:{has_end}'
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # Step 1: エスケープ文字の修正
                if '\\n' in private_key:
                    private_key = private_key.replace('\\n', '\n')
                    logger.info("✅ エスケープ文字変換完了")
                
                # Step 2: Base64部分の抽出と修正
                if '-----BEGIN PRIVATE KEY-----' in private_key and '-----END PRIVATE KEY-----' in private_key:
                    lines = private_key.split('\n')
                    fixed_lines = []
                    
                    for line in lines:
                        if line and not line.startswith('-----'):
                            # Base64文字列のパディング修正
                            missing_padding = len(line) % 4
                            if missing_padding:
                                line += '=' * (4 - missing_padding)
                                logger.info(f"✅ Base64パディング追加: {4 - missing_padding}文字")
                            
                            # Base64文字列の妥当性チェック
                            try:
                                base64.b64decode(line, validate=True)
                                logger.info(f"✅ Base64行妥当性確認: {len(line)}文字")
                            except Exception as e:
                                logger.warning(f"⚠️ Base64行エラー: {len(line)}文字, エラー: {e}")
                                # 無効文字を削除
                                line = re.sub(r'[^A-Za-z0-9+/=]', '', line)
                                # 再パディング
                                missing_padding = len(line) % 4
                                if missing_padding:
                                    line += '=' * (4 - missing_padding)
                                logger.info(f"🔧 Base64行修正後: {len(line)}文字")
                        
                        fixed_lines.append(line)
                    
                    fixed_private_key = '\n'.join(fixed_lines)
                    fixed_info['private_key'] = fixed_private_key
                    logger.info("✅ Private key Base64修正完了")
                
                # Step 3: 全体的なBase64検証
                try:
                    test_credentials = service_account.Credentials.from_service_account_info(fixed_info)
                    logger.info("✅ 修正後認証情報検証成功")
                except Exception as e:
                    logger.error(f"❌ 修正後認証情報検証失敗: {e}")
                    raise
                    
            except Exception as e:
                logger.error(f"❌ Private key修正エラー: {e}")
                raise
        
        return fixed_info
    
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
        音声チャンクを文字起こし
        
        Args:
            gcs_uri: GCS上の音声ファイルURI
            chunk_index: チャンクのインデックス
            
        Returns:
            Optional[str]: 文字起こし結果
        """
        try:
            logger.info(f"チャンク {chunk_index} の文字起こし開始")
            
            audio = speech.RecognitionAudio(uri=gcs_uri)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="ja-JP",  # 日本語
                enable_automatic_punctuation=True,  # 自動句読点
                enable_word_time_offsets=True,  # 単語レベルのタイムスタンプ
                model="latest_long",  # 長時間音声用モデル
            )
            
            # ブロッキング処理をスレッドで実行
            operation = await asyncio.to_thread(
                self.speech_client.long_running_recognize,
                config=config,
                audio=audio
            )

            logger.info(f"チャンク {chunk_index} の認識処理を待機中...")

            # operation.result自体もブロッキングのためスレッド実行
            response = await asyncio.to_thread(operation.result, timeout=3600)  # 最大1時間待機
            
            # 結果を結合
            transcript = ""
            for result in response.results:
                transcript += result.alternatives[0].transcript + " "
            
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
            logger.info("音声ファイルの文字起こし処理を開始")
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
    
    # サービス初期化
    service = AudioTranscriptionService(
        service_account_path=SERVICE_ACCOUNT_PATH,
        gcs_bucket_name=GCS_BUCKET_NAME
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
