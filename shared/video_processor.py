"""
動画処理用のユーティリティクラス
動画ファイルから音声を抽出してフォーマット変換を行う
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, Tuple
import asyncio

# ログ設定（条件付きインポート前に定義）
logger = logging.getLogger(__name__)

# 動画処理関連（条件付きインポート）
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available - video preview disabled")

# MoviePyの詳細初期化（FFmpeg設定強化版）
try:
    # imageio-ffmpegを先に初期化
    import imageio_ffmpeg as iio_ffmpeg
    IMAGEIO_FFMPEG_AVAILABLE = True
    logger.info("imageio-ffmpeg 初期化成功")
    
    # FFmpeg実行可能ファイルの設定
    import os
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # MoviePyの環境変数設定
    os.environ['IMAGEIO_FFMPEG_EXE'] = ffmpeg_exe
    logger.info(f"FFmpeg実行パス設定: {ffmpeg_exe}")
    
    # MoviePyをimport
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
    logger.info("✅ MoviePy 初期化成功（imageio-ffmpeg連携）")
    
except ImportError as e:
    MOVIEPY_AVAILABLE = False
    IMAGEIO_FFMPEG_AVAILABLE = False
    logger.warning(f"❌ MoviePy 初期化失敗: {e}")

# ffmpeg-pythonライブラリの確認
try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
    logger.info("✅ ffmpeg-python ライブラリ利用可能")
except ImportError:
    FFMPEG_AVAILABLE = False
    logger.warning("❌ ffmpeg-python ライブラリ利用不可")

# 最終的な可用性確認
if not IMAGEIO_FFMPEG_AVAILABLE:
    try:
        import imageio_ffmpeg as iio_ffmpeg
        IMAGEIO_FFMPEG_AVAILABLE = True
        logger.info("imageio-ffmpeg 後期初期化成功")
    except ImportError:
        IMAGEIO_FFMPEG_AVAILABLE = False
        logger.warning("imageio-ffmpeg 完全に利用不可")

class VideoProcessor:
    """動画ファイル処理クラス"""
    
    def __init__(self):
        """VideoProcessorの初期化"""
        self.supported_video_formats = {
            '.mp4', '.avi', '.mov', '.wmv', '.flv', 
            '.mkv', '.webm', '.m4v', '.3gp', '.mts'
        }
        self.video_processing_available = MOVIEPY_AVAILABLE and CV2_AVAILABLE
        
        # 詳細な可用性情報をログ出力（強化版）
        logger.info("=" * 50)
        logger.info("🎬 動画処理ライブラリ状況詳細")
        logger.info("=" * 50)
        logger.info(f"✅ OpenCV available: {CV2_AVAILABLE}")
        logger.info(f"✅ MoviePy available: {MOVIEPY_AVAILABLE}")
        logger.info(f"✅ FFmpeg (ffmpeg-python) available: {FFMPEG_AVAILABLE}")
        logger.info(f"✅ imageio-ffmpeg available: {IMAGEIO_FFMPEG_AVAILABLE}")
        logger.info(f"🎯 Video processing available: {self.video_processing_available}")
        logger.info("=" * 50)
        
        # 不足ライブラリの詳細診断
        if not self.video_processing_available:
            missing = []
            if not MOVIEPY_AVAILABLE:
                missing.append("MoviePy")
            if not CV2_AVAILABLE:
                missing.append("OpenCV")
            logger.warning(f"❌ 動画処理無効: {', '.join(missing)} が不足")
        
        # FFmpeg環境変数の確認
        import os
        if 'IMAGEIO_FFMPEG_EXE' in os.environ:
            logger.info(f"🔧 IMAGEIO_FFMPEG_EXE: {os.environ['IMAGEIO_FFMPEG_EXE']}")
        else:
            logger.warning("⚠️ IMAGEIO_FFMPEG_EXE 未設定")
        
        if not self.video_processing_available:
            logger.warning("Video processing libraries not available. Audio-only mode enabled.")
    
    def validate_video_file(self, video_path: str) -> bool:
        """
        動画ファイルの存在と形式を検証
        
        Args:
            video_path: 動画ファイルパス
            
        Returns:
            bool: 検証成功フラグ
        """
        try:
            path = Path(video_path)
            
            # ファイル存在チェック
            if not path.exists():
                logger.error(f"ファイルが見つかりません: {video_path}")
                return False
            
            # ファイルサイズチェック
            file_size = path.stat().st_size
            if file_size == 0:
                logger.error(f"ファイルが空です: {video_path}")
                return False
            
            # ファイルサイズをログ出力
            size_mb = file_size / (1024 * 1024)
            logger.info(f"動画ファイルサイズ: {size_mb:.2f}MB")
            
            # 対応形式チェック
            if path.suffix.lower() not in self.supported_video_formats:
                logger.warning(f"未対応の可能性がある形式: {path.suffix}")
            
            # 動画ファイルの基本情報を取得
            try:
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    logger.error("動画ファイルを開けませんでした")
                    return False
                
                # 動画情報をログ出力
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                logger.info(f"動画情報 - 時間: {duration:.2f}秒, FPS: {fps:.2f}, 解像度: {width}x{height}")
                cap.release()
                
            except Exception as e:
                logger.warning(f"動画情報の取得に失敗: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"ファイル検証エラー: {str(e)}")
            return False
    
    async def extract_audio_from_video(self, video_path: str, output_audio_path: str) -> bool:
        """
        動画ファイルから音声を抽出してWAV形式で保存
        
        Args:
            video_path: 入力動画ファイルパス
            output_audio_path: 出力音声ファイルパス（WAV形式）
            
        Returns:
            bool: 抽出成功フラグ
        """
        try:
            logger.info("動画から音声を抽出中...")
            
            def extract_audio():
                try:
                    # MoviePyを使用して音声抽出
                    with VideoFileClip(video_path) as video:
                        # 動画情報をログ出力
                        logger.info(f"動画時間: {video.duration:.2f}秒")
                        
                        if video.audio is None:
                            raise Exception("動画に音声トラックが含まれていません")
                        
                        # 音声を抽出してWAV形式で保存（16kHz、モノラル）
                        video.audio.write_audiofile(
                            output_audio_path,
                            codec='pcm_s16le',  # 16-bit PCM
                            ffmpeg_params=['-ac', '1', '-ar', '16000'],  # モノラル、16kHz
                            verbose=False,
                            logger=None  # MoviePyのログを無効化
                        )
                        
                except Exception as e:
                    logger.error(f"音声抽出中にエラー: {str(e)}")
                    raise
            
            # 音声抽出処理をスレッドで実行
            await asyncio.to_thread(extract_audio)
            
            # 抽出された音声ファイルの検証
            if not os.path.exists(output_audio_path):
                raise Exception("音声ファイルの抽出に失敗")
            
            audio_size = os.path.getsize(output_audio_path) / (1024 * 1024)
            logger.info(f"音声抽出完了 - ファイルサイズ: {audio_size:.2f}MB")
            
            return True
            
        except Exception as e:
            logger.error(f"音声抽出エラー: {str(e)}")
            return False
    
    def get_video_info(self, video_path: str) -> Optional[dict]:
        """
        動画ファイルの詳細情報を取得
        
        Args:
            video_path: 動画ファイルパス
            
        Returns:
            dict: 動画情報辞書（duration, fps, width, height, format等）
        """
        try:
            with VideoFileClip(video_path) as video:
                info = {
                    'duration': video.duration,
                    'fps': video.fps,
                    'size': video.size,  # (width, height)
                    'has_audio': video.audio is not None,
                    'filename': Path(video_path).name,
                    'file_size_mb': os.path.getsize(video_path) / (1024 * 1024)
                }
                
                if video.audio:
                    info['audio_fps'] = video.audio.fps
                    info['audio_duration'] = video.audio.duration
                
                return info
                
        except Exception as e:
            logger.error(f"動画情報取得エラー: {str(e)}")
            return None
    
    async def process_video_for_transcription(self, video_path: str) -> Optional[str]:
        """
        動画ファイルを文字起こし用に処理（音声抽出）
        
        Args:
            video_path: 入力動画ファイルパス
            
        Returns:
            str: 抽出された音声ファイルのパス（一時ファイル）
        """
        try:
            # 動画処理ライブラリが利用できない場合
            if not self.video_processing_available:
                raise Exception("動画処理ライブラリが利用できません。音声ファイルをご利用ください。")
            
            # 入力ファイル検証
            if not self.validate_video_file(video_path):
                raise Exception("入力動画ファイルの検証に失敗")
            
            # 一時ファイルパスを生成
            temp_dir = tempfile.mkdtemp()
            audio_filename = f"extracted_audio_{os.getpid()}.wav"
            audio_path = os.path.join(temp_dir, audio_filename)
            
            # 音声抽出
            success = await self.extract_audio_from_video(video_path, audio_path)
            if not success:
                raise Exception("音声抽出に失敗")
            
            return audio_path
            
        except Exception as e:
            logger.error(f"動画処理エラー: {str(e)}")
            return None

# 使用例
async def main():
    """使用例のメイン関数"""
    processor = VideoProcessor()
    
    # 動画ファイルパス
    video_path = "/path/to/your/video.mp4"
    
    try:
        # 動画から音声を抽出
        audio_path = await processor.process_video_for_transcription(video_path)
        
        if audio_path:
            print(f"音声抽出完了: {audio_path}")
            # この後、AudioTranscriptionServiceで文字起こし処理を実行
        else:
            print("音声抽出に失敗しました")
            
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())

