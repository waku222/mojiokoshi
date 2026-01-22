"""
文字起こしWebアプリケーション（Streamlit）
音声ファイルと動画ファイルの両方に対応した文字起こしサービス
"""

import streamlit as st

# ページ設定（UIクリーンアップ版）
st.set_page_config(
    page_title="AI文字起こしサービス（テスト版）",
    page_icon="🎤",
    layout="centered",
    initial_sidebar_state="collapsed"  # サイドバーを最初から閉じる
)

import os
import tempfile
import asyncio
from pathlib import Path
import logging
from datetime import datetime
import traceback
import importlib.util

# 共通機能のインポート
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.transcription_service import AudioTranscriptionService

# ログ設定（最初に定義）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境から取得するデフォルト値
# GCSバケット名のデフォルト: 環境変数 > デフォルト値の優先順位
DEFAULT_GCS_BUCKET = os.getenv("GCS_BUCKET_NAME", "250728transcription-bucket").strip()
DEFAULT_COMPANY_ACCESS_KEY = os.getenv("COMPANY_ACCESS_KEY", "tatsujiro25Koueki").strip()

# 動画処理の条件付きインポート（詳細診断版）
try:
    from shared.video_processor import VideoProcessor
    logger.info("VideoProcessor インポート成功")
    
    # 実際のライブラリ可用性もチェック
    video_processor = VideoProcessor()
    logger.info("VideoProcessor インスタンス化成功")
    
    VIDEO_PROCESSING_AVAILABLE = video_processor.video_processing_available
    if VIDEO_PROCESSING_AVAILABLE:
        logger.info("✅ 動画処理機能: 利用可能")
    else:
        logger.warning("⚠️ 動画処理機能: ライブラリ不足のため無効")
        # 具体的にどのライブラリが不足しているかを確認
        opencv_available = importlib.util.find_spec("cv2") is not None
        moviepy_available = importlib.util.find_spec("moviepy.editor") is not None
        if opencv_available:
            logger.info("OpenCV: 利用可能")
        else:
            logger.warning("OpenCV: 利用不可")
        if moviepy_available:
            logger.info("MoviePy: 利用可能")
        else:
            logger.warning("MoviePy: 利用不可")
            
except ImportError as e:
    VIDEO_PROCESSING_AVAILABLE = False
    logger.warning("VideoProcessor インポートエラー: %s", e)
except (RuntimeError, ValueError, OSError) as e:
    VIDEO_PROCESSING_AVAILABLE = False
    logger.error("VideoProcessor 初期化失敗: %s: %s", type(e).__name__, str(e))
    logger.error("詳細トレースバック: %s", traceback.format_exc())

# Streamlitページ設定
st.set_page_config(
    page_title="AI文字起こしサービス",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """メインアプリケーション"""
    
    # タイトルとヘッダー（一番上に配置）
    st.title("AI文字起こしサービス")
    st.markdown("**音声ファイル・動画ファイルから高精度な日本語文字起こしを行います**")
    
    # タイトル画像の表示
    title_image_path = os.path.join(os.path.dirname(__file__), "assets", "title_wizard.png")
    if os.path.exists(title_image_path):
        # 中央寄せで画像を表示
        _, col2, _ = st.columns([1, 2, 1])
        with col2:
            st.image(title_image_path, width=300, caption="AI魔法使いコウイチくんによる文字起こし")
    
    st.markdown("---")  # セパレーター追加
    
    # 認証情報の確認（Streamlit Cloud対応強化版）
    credentials_path = os.path.join(os.path.dirname(__file__), "..", "credentials", "service-account-key.json")
    
    # 🔧 シンプルなSecrets処理（Base64エラー回避版）
    debug_info = []
    logger.info("🔧 シンプルなSecrets処理開始")
    
    # ローカルファイルの存在確認
    local_file_exists = os.path.exists(credentials_path)
    debug_info.append(f"📁 ローカルファイル: {'存在' if local_file_exists else '不存在'}")
    
    # Streamlit Cloud環境かどうか判定
    try:
        # Secretsが利用可能かチェック
        secrets_available = hasattr(st, 'secrets') and len(st.secrets) > 0
        debug_info.append(f"☁️ Streamlit Cloud: {'検出' if secrets_available else '未検出'}")
    except (AttributeError, TypeError):
        secrets_available = False
        debug_info.append("☁️ Streamlit Cloud: 未検出（エラー）")
    
    # 認証方式の決定
    if local_file_exists:
        # ローカル環境（開発環境）
        credentials_exists = True
        use_streamlit_secrets = False
        debug_info.append("✅ 認証方式: ローカルファイル")
        logger.info("ローカルファイル認証を使用")
    elif secrets_available:
        # Streamlit Cloud環境
        credentials_exists = True
        use_streamlit_secrets = True
        debug_info.append("✅ 認証方式: Streamlit Secrets")
        logger.info("Streamlit Secrets認証を使用")
    else:
        # 認証情報なし
        credentials_exists = False
        use_streamlit_secrets = False
        debug_info.append("❌ 認証情報: なし")
        logger.error("認証情報が見つかりません")
    
    # サイドバー設定
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # Google Cloud認証状況の表示
        st.subheader("Google Cloud認証")
        if credentials_exists:
            st.success("✅ 認証設定済み")
            if use_streamlit_secrets:
                st.info("🔐 Streamlit Secrets使用中")
            else:
                st.info(f"📁 認証ファイル: {os.path.basename(credentials_path)}")
        else:
            st.error("❌ サービスアカウントキーファイルが見つかりません")
            if use_streamlit_secrets:
                st.error("**管理者へ**: Streamlit CloudのSecretsでgcp_service_accountを設定してください")
                
                # デバッグ情報表示
                with st.expander("🔍 詳細デバッグ情報（管理者用）"):
                    for info in debug_info:
                        st.text(info)
                    
                    st.markdown("### ❗ 確認すべき項目")
                    st.markdown("""
                    1. **Streamlit Cloud Settings → Secrets** でSecretsが設定済みか？
                    2. **[gcp_service_account]** セクションが存在するか？
                    3. **必須フィールド** が全て含まれているか？
                       - type, project_id, private_key, client_email
                    4. **TOML形式** が正しいか？
                    5. **Save** ボタンを押してアプリが再起動したか？
                    """)
                    
                    st.markdown("### 🔧 緊急対処法")
                    if st.button("🔄 アプリ強制再起動", help="Secrets設定後にアプリを強制的に再起動します"):
                        st.info("⏳ アプリを再起動中...")
                        st.cache_data.clear()
                        st.cache_resource.clear()
                        st.rerun()
                    
                    st.markdown("### 📋 設定用TOML内容（フラット形式推奨）")
                    st.markdown("**セクション形式で問題がある場合は、以下のフラット形式をお試しください：**")
                    
                    with st.expander("🔹 フラット形式（推奨）", expanded=True):
                        st.code('''# Google Cloud Service Account (フラット形式)
gcp_service_account_type = "service_account"
gcp_service_account_project_id = "<YOUR_PROJECT_ID>"
gcp_service_account_private_key_id = "<YOUR_PRIVATE_KEY_ID>"
gcp_service_account_private_key = "<YOUR_PRIVATE_KEY>"
gcp_service_account_client_email = "<YOUR_CLIENT_EMAIL>"
gcp_service_account_client_id = "<YOUR_CLIENT_ID>"
gcp_service_account_auth_uri = "https://accounts.google.com/o/oauth2/auth"
gcp_service_account_token_uri = "https://oauth2.googleapis.com/token"
gcp_service_account_auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
gcp_service_account_client_x509_cert_url = "<YOUR_CERT_URL>"

# その他の設定
GCS_BUCKET_NAME = "<YOUR_GCS_BUCKET_NAME>"
COMPANY_ACCESS_KEY = "tatsujiro25Koueki"''', language="toml")
                    
                    with st.expander("🔸 セクション形式（代替）"):
                        st.code('''[gcp_service_account]
type = "service_account"
project_id = "<YOUR_PROJECT_ID>"
private_key_id = "<YOUR_PRIVATE_KEY_ID>"
private_key = "<YOUR_PRIVATE_KEY>"
client_email = "<YOUR_CLIENT_EMAIL>"
client_id = "<YOUR_CLIENT_ID>"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "<YOUR_CERT_URL>"

GCS_BUCKET_NAME = "<YOUR_GCS_BUCKET_NAME>"
COMPANY_ACCESS_KEY = "tatsujiro25Koueki"''', language="toml")
            else:
                st.error(f"**管理者へ**: 以下の場所に配置してください:\n`{credentials_path}`")
        
        # GCSバケット名（環境に応じて取得）
        # 優先順位: Streamlit Secrets > 環境変数 > デフォルト値
        secret_bucket = ""
        if use_streamlit_secrets:
            try:
                secret_bucket = st.secrets.get("GCS_BUCKET_NAME", "").strip()
            except (KeyError, AttributeError, TypeError):
                secret_bucket = ""
        env_bucket = os.getenv("GCS_BUCKET_NAME", "").strip()
        default_bucket = secret_bucket or env_bucket or DEFAULT_GCS_BUCKET
            
        gcs_bucket = st.text_input(
            "GCSバケット名",
            value=default_bucket,
            help="長時間音声処理用のGCSバケット名（デフォルト: 250728transcription-bucket）",
            placeholder="例: 250728transcription-bucket"
        )
        
        # システム情報
        with st.expander("💻 システム情報"):
            display_bucket = gcs_bucket if gcs_bucket.strip() else DEFAULT_GCS_BUCKET
            st.markdown(f"""
            **認証状態**: {"✅ OK" if credentials_exists else "❌ 未設定"}
            **GCSバケット**: {display_bucket}
            **処理方式**: 自動最適化
            """)
        
        # 使用方法
        with st.expander("📖 使用方法"):
            st.markdown("""
            1. **ファイル選択**: 音声またはビデオファイルをアップロード
            2. **処理開始**: 「文字起こし開始」ボタンをクリック
            3. **結果確認**: 文字起こし結果をダウンロード
            
            **対応形式**:
            - 音声: WAV, MP3, FLAC, M4A, OGG
            - 動画: MP4, AVI, MOV, MKV, WMV等
            
            **管理者向け**:
            認証ファイルは `credentials/service-account-key.json` に配置してください。
            """)
    
    # メイン処理エリア
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 ファイルアップロード")
        
        # 動画処理の可用性をチェック
        if VIDEO_PROCESSING_AVAILABLE:
            file_types = ["wav", "mp3", "flac", "m4a", "ogg", "mp4", "avi", "mov", "mkv", "wmv", "webm"]
            help_text = "音声ファイル・動画ファイル対応 | 最大ファイルサイズ: 500MB"
        else:
            file_types = ["wav", "mp3", "flac", "m4a", "ogg"]
            help_text = "音声ファイルのみ対応（動画処理は現在利用不可）| 最大ファイルサイズ: 500MB"
            st.warning("⚠️ 動画処理機能は現在利用できません。音声ファイルをご利用ください。")
        
        # ファイルアップロード
        uploaded_file = st.file_uploader(
            "音声ファイルを選択してください" if not VIDEO_PROCESSING_AVAILABLE else "音声ファイルまたは動画ファイルを選択してください",
            type=file_types,
            help=help_text
        )
        
        if uploaded_file is not None:
            # ファイル情報表示
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            is_video = uploaded_file.name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm'))
            
            if is_video and not VIDEO_PROCESSING_AVAILABLE:
                st.error("❌ 動画ファイルが選択されましたが、動画処理機能は現在利用できません。音声ファイルを選択してください。")
                return
            
            file_type = "動画" if is_video else "音声"
            st.info(f"**ファイル情報**  \nファイル名: {uploaded_file.name}  \nタイプ: {file_type}ファイル  \nサイズ: {file_size_mb:.2f}MB")
            
            # 大容量ファイル警告（動画・音声両対応）
            warning_threshold = 300 if is_video else 200  # 動画は300MB、音声は200MBで警告
            
            if file_size_mb > warning_threshold:
                file_type_name = "動画" if is_video else "音声"
                st.warning(f"⚠️ **大容量{file_type_name}ファイル警告** ({file_size_mb:.1f}MB)")
                st.warning(f"**Streamlit Cloud無料枠では{warning_threshold}MB以上の{file_type_name}ファイル処理に制限があります**")
                
                if is_video:
                    st.warning("**動画ファイル推奨対策:**")
                    st.markdown("""
                    - **動画圧縮**: H.264/MP4形式で再エンコード
                    - **解像度削減**: 720p以下に変更
                    - **フレームレート削減**: 30fps以下に変更
                    - **動画分割**: 5-10分単位で分割
                    - **音声のみ抽出**: 事前にMP3に変換
                    """)
                else:
                    st.warning("**音声ファイル推奨対策:**")
                    st.markdown("""
                    - **音声ファイル圧縮**: MP3形式で再エンコード
                    - **ファイル分割**: 複数の小さなファイルに分割
                    - **サンプリング**: より低いサンプリングレートで変換
                    """)
                
                if st.button("⚠️ 理解した上で処理を続行", type="secondary"):
                    st.session_state.large_file_confirmed = True
                
                if not st.session_state.get('large_file_confirmed', False):
                    recommended_size = "100MB" if is_video else "50MB"
                    st.info(f"💡 **推奨**: {recommended_size}以下の小さなファイルから試すことをお勧めします")
                    return
            
            # 処理ボタン
            if st.button("🚀 文字起こし開始", type="primary", use_container_width=True):
                if not credentials_exists:
                    st.error("❌ サービスアカウントキーファイルが見つかりません")
                    st.error("管理者にお問い合わせください")
                    return
                
                # GCSバケット名のバリデーション（デフォルト値を使用）
                final_gcs_bucket = gcs_bucket.strip() if gcs_bucket.strip() else DEFAULT_GCS_BUCKET
                if not final_gcs_bucket:
                    st.error("❌ GCSバケット名を入力してください")
                    st.info("💡 サイドバーの「GCSバケット名」欄に入力してください")
                    return
                
                # 自動的に最適なチャンク長を決定（動画・音声対応）
                optimal_chunk_length_ms = calculate_optimal_chunk_length(uploaded_file, is_video)
                
                # 文字起こし処理を実行
                process_transcription(
                    uploaded_file, 
                    credentials_path if not use_streamlit_secrets else None, 
                    final_gcs_bucket,  # デフォルト値を適用したバケット名を使用
                    optimal_chunk_length_ms,
                    use_streamlit_secrets
                )
    
    with col2:
        st.header("📊 処理状況")
        
        # セッション状態の初期化
        if 'processing_status' not in st.session_state:
            st.session_state.processing_status = "待機中"
        
        # 状態表示
        status_container = st.container()
        with status_container:
            if st.session_state.processing_status == "待機中":
                st.info("📋 ファイルのアップロードをお待ちしています")
            elif st.session_state.processing_status == "処理中":
                st.warning("⏳ 文字起こし処理中...")
                st.progress(50)
            elif st.session_state.processing_status == "完了":
                st.success("✅ 文字起こし完了！")
            elif st.session_state.processing_status == "エラー":
                st.error("❌ 処理中にエラーが発生しました")

def process_transcription(uploaded_file, credentials_path, gcs_bucket, chunk_length_ms, use_streamlit_secrets=False):
    """文字起こし処理の実行"""
    
    try:
        st.session_state.processing_status = "処理中"
        
        # プログレスバーと状況表示
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 一時ファイルとして保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            input_file_path = tmp_file.name
        
        # 認証ファイルは固定パスを使用
        # credentials_pathは既に渡されている
        
        status_text.text("🔄 初期化中...")
        progress_bar.progress(10)
        
        # 非同期処理を実行
        result = asyncio.run(async_transcribe(
            input_file_path, 
            credentials_path, 
            gcs_bucket, 
            chunk_length_ms,
            progress_bar,
            status_text,
            use_streamlit_secrets
        ))
        
        if result:
            st.session_state.processing_status = "完了"
            progress_bar.progress(100)
            status_text.text("✅ 処理完了！")
            
            # 結果表示
            st.header("📄 文字起こし結果")
            st.text_area("結果", result, height=400)
            
            # ダウンロードボタン
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transcription_{timestamp}.txt"
            
            st.download_button(
                label="📥 結果をダウンロード",
                data=result,
                file_name=filename,
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.session_state.processing_status = "エラー"
            st.error("❌ 文字起こし処理に失敗しました")
            st.error("💡 **管理者向け**: ログを確認して詳細な原因を特定してください")
        
        # 一時ファイルを削除
        os.unlink(input_file_path)
        # credentials_pathは固定ファイルなので削除しない
        
    except (RuntimeError, ValueError, OSError) as e:
        st.session_state.processing_status = "エラー"
        st.error(f"❌ **処理エラー**: {str(e)}")
        
        # 詳細なエラー情報を表示
        with st.expander("🔍 **エラー詳細情報（管理者用）**"):
            st.error(f"**エラータイプ**: {type(e).__name__}")
            st.error(f"**エラーメッセージ**: {str(e)}")
            st.error(f"**ファイル**: {uploaded_file.name}")
            st.error(f"**ファイルサイズ**: {len(uploaded_file.getvalue()) / (1024 * 1024):.2f}MB")
            st.error(f"**認証方式**: {'Streamlit Secrets' if use_streamlit_secrets else 'ローカルファイル'}")
            st.error(f"**GCSバケット**: {gcs_bucket}")
            
        logger.error("文字起こし処理エラー: %s: %s", type(e).__name__, str(e))
        logger.error("詳細トレースバック: %s", traceback.format_exc())

async def async_transcribe(input_file_path, credentials_path, gcs_bucket, chunk_length_ms, progress_bar, status_text, use_streamlit_secrets=False):
    """非同期文字起こし処理"""
    
    try:
        # ファイルタイプを判定
        file_extension = Path(input_file_path).suffix.lower()
        is_video = file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm']
        
        audio_file_path = input_file_path
        
        # 動画ファイルの場合は音声抽出
        if is_video:
            if not VIDEO_PROCESSING_AVAILABLE:
                raise RuntimeError("動画処理機能が利用できません。必要なライブラリ（moviepy/opencv）がインストールされていない可能性があります。")
            
            status_text.text("🎬 動画から音声を抽出中...")
            progress_bar.progress(20)
            
            # 追加の安全チェック
            runtime_video_processor = VideoProcessor()
            if not runtime_video_processor.video_processing_available:
                raise RuntimeError("動画処理ライブラリが実行時に利用できません（moviepy/opencv未インストール）")
            audio_file_path = await runtime_video_processor.process_video_for_transcription(input_file_path)
            
            if not audio_file_path:
                raise RuntimeError("動画からの音声抽出に失敗しました")
        
        # 音声文字起こしサービスを初期化
        status_text.text("🤖 文字起こしサービス初期化中...")
        progress_bar.progress(30)
        
        # 🔧 シンプルな認証方式選択（Base64エラー回避版 + RSA警告抑制）
        import warnings
        
        # RSA警告を抑制（Google認証の不完全なキーファイル警告）
        warnings.filterwarnings('ignore', message='You have provided a malformed keyfile')
        
        if use_streamlit_secrets:
            # Streamlit Cloud環境：Secretsから認証情報を取得
            logger.info("Streamlit Secrets認証を使用")
            try:
                # シンプルなSecrets取得（フラット形式のみ）
                # private_key の改行文字を正規化
                private_key = st.secrets["gcp_service_account_private_key"]
                if "\\n" in private_key:
                    private_key = private_key.replace("\\n", "\n")
                
                service_account_info = {
                    "type": st.secrets["gcp_service_account_type"],
                    "project_id": st.secrets["gcp_service_account_project_id"],
                    "private_key": private_key,
                    "client_email": st.secrets["gcp_service_account_client_email"],
                    "private_key_id": st.secrets.get("gcp_service_account_private_key_id", ""),
                    "client_id": st.secrets.get("gcp_service_account_client_id", ""),
                    "auth_uri": st.secrets.get("gcp_service_account_auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                    "token_uri": st.secrets.get("gcp_service_account_token_uri", "https://oauth2.googleapis.com/token"),
                    "auth_provider_x509_cert_url": st.secrets.get("gcp_service_account_auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
                    "client_x509_cert_url": st.secrets.get("gcp_service_account_client_x509_cert_url", "")
                }
                
                # 認証情報の検証（デバッグ用）
                logger.info("認証情報検証 - Project ID: %s", service_account_info["project_id"])
                logger.info("認証情報検証 - Client Email: %s", service_account_info["client_email"])
                
                transcription_service = AudioTranscriptionService(
                    service_account_info=service_account_info,
                    gcs_bucket_name=gcs_bucket
                )
            except (KeyError, ValueError, TypeError) as e:
                logger.error("Streamlit Secrets認証エラー: %s", e)
                raise RuntimeError(f"Streamlit Secrets認証に失敗しました: {str(e)}") from e
        else:
            # ローカル環境：ファイルから認証
            logger.info("ローカルファイル認証を使用")
            transcription_service = AudioTranscriptionService(
                service_account_path=credentials_path,
                gcs_bucket_name=gcs_bucket
            )
        
        # 出力用の一時ファイル
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w') as output_file:
            output_file_path = output_file.name
        
        # 文字起こし処理実行
        status_text.text("🎙️ 文字起こし処理中...")
        progress_bar.progress(50)
        
        success = await transcription_service.process_audio_transcription(
            audio_path=audio_file_path,
            output_path=output_file_path,
            chunk_length_ms=chunk_length_ms
        )
        
        if success:
            # 結果を読み込み
            with open(output_file_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            # 一時ファイルを削除
            os.unlink(output_file_path)
            if is_video and audio_file_path != input_file_path:
                os.unlink(audio_file_path)
            
            return result
        else:
            logger.error("音声ファイル処理結果が空です")
            logger.error("処理対象: %s", input_file_path)
            logger.error("ファイル存在確認: %s", os.path.exists(input_file_path))
            if os.path.exists(input_file_path):
                logger.error("ファイルサイズ: %s bytes", os.path.getsize(input_file_path))
            raise RuntimeError(f"文字起こし処理に失敗しました（結果が空）- ファイル: {os.path.basename(input_file_path)}")
        
    except (RuntimeError, ValueError, OSError, KeyError, TypeError) as e:
        logger.error("非同期文字起こしエラー: %s", str(e))
        return None

def calculate_optimal_chunk_length(uploaded_file, is_video: bool = False):
    """
    アップロードされたファイルに基づいて最適なチャンク長を自動計算
    
    Args:
        uploaded_file: Streamlitアップロードファイルオブジェクト
        is_video: 動画ファイルかどうか
        
    Returns:
        int: チャンク長（ミリ秒）
    """
    # ファイルサイズを取得（MB単位）
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    
    # 動画の場合は、より慎重なチャンク設定
    if is_video:
        if file_size_mb < 100:
            chunk_length_ms = 3 * 60 * 1000  # 3分チャンク
            logger.info("小動画検出 (%.1fMB) -> 3分チャンク", file_size_mb)
        elif file_size_mb < 300:
            chunk_length_ms = 2 * 60 * 1000  # 2分チャンク
            logger.info("中動画検出 (%.1fMB) -> 2分チャンク", file_size_mb)
        else:
            chunk_length_ms = 90 * 1000      # 1.5分チャンク
            logger.warning("大動画検出 (%.1fMB) -> 1.5分チャンク（メモリ制限対策）", file_size_mb)
    else:
        # 音声ファイルの場合（既存ロジック）
        if file_size_mb < 50:
            chunk_length_ms = 5 * 60 * 1000  # 300,000ms
            logger.info("小ファイル検出 (%.1fMB) -> 5分チャンク", file_size_mb)
        elif file_size_mb < 150:
            chunk_length_ms = 3 * 60 * 1000   # 180,000ms
            logger.info("中ファイル検出 (%.1fMB) -> 3分チャンク", file_size_mb)
        else:
            chunk_length_ms = 2 * 60 * 1000   # 120,000ms
            logger.warning("大ファイル検出 (%.1fMB) -> 2分チャンク（メモリ制限対策）", file_size_mb)
            logger.warning("⚠️ 大容量ファイルはStreamlit Cloudでの処理制限があります")
    
    return chunk_length_ms

def check_company_access():
    """社内専用アクセス認証"""
    
    # アクセスキー（環境に応じて取得）
    access_key_for_auth = ""
    try:
        # Secrets環境かどうかをチェック
        if hasattr(st, 'secrets') and len(st.secrets) > 0:
            access_key_for_auth = st.secrets.get("COMPANY_ACCESS_KEY", "").strip()
    except (AttributeError, KeyError, TypeError):
        access_key_for_auth = ""

    # Secretsに無い場合は環境変数を参照
    if not access_key_for_auth:
        access_key_for_auth = os.getenv("COMPANY_ACCESS_KEY", "").strip()

    # それでも無い場合はデフォルト値（環境経由のみに限定）
    if not access_key_for_auth:
        access_key_for_auth = DEFAULT_COMPANY_ACCESS_KEY

    if not access_key_for_auth:
        st.error("❌ アクセスキーが設定されていません。環境変数またはStreamlit SecretsにCOMPANY_ACCESS_KEYを設定してください。")
        st.stop()
    
    # セッション状態の初期化
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.login_attempts = 0
    
    if not st.session_state.authenticated:
        # 認証画面のスタイル設定（紫色ブロック完全削除版）
        st.markdown("""
        <style>
        /* Streamlit上部バーと紫色要素を完全削除 */
        .stApp > header[data-testid="stHeader"] {
            display: none !important;
        }
        
        /* プログレスバーを非表示 */
        .stProgress {
            display: none !important;
        }
        
        /* メインコンテナの上部パディング削除 */
        .main .block-container {
            padding-top: 0rem !important;
            max-width: 100% !important;
        }
        
        /* Streamlitのデフォルト背景削除 */
        .stApp {
            background-color: #f0f2f6 !important;
        }
        
        /* 上部の余白を完全削除 */
        section.main > div {
            padding-top: 0rem !important;
        }
        
        /* 紫色の要素を強制的に非表示 */
        div[style*="background-color: rgb(106, 92, 231)"] {
            display: none !important;
        }
        
        div[style*="background: linear-gradient"] {
            display: none !important;
        }
        
        /* Streamlitのメニューボタンを非表示 */
        button[kind="header"] {
            display: none !important;
        }
        
        /* Streamlitのデプロイボタンも非表示 */
        .stDeployButton {
            display: none !important;
        }
        
        /* その他の紫色系要素を非表示 */
        div[data-testid="stSidebar"] {
            display: none !important;
        }
        
        /* ツールバーを非表示 */
        .stToolbar {
            display: none !important;
        }
        
        /* ログインコンテナ（横幅拡大版） */
        .login-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        /* タイトルスタイル（横幅拡大対応） */
        .login-title {
            text-align: left;
            font-size: 2.2rem;
            margin-bottom: 0.2rem;
            color: white;
            font-weight: bold;
        }
        
        /* サブタイトルスタイル */
        .login-subtitle {
            text-align: left;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
            color: #ff6b6b;
            font-weight: bold;
        }
        
        /* 左側画像のスタイル */
        .login-image-left {
            text-align: center;
            margin-top: 0.5rem;
        }
        
        /* 右側タイトルのスタイル */
        .login-title-right {
            padding-left: 1rem;
            padding-top: 1rem;
        }
        
        /* アクセスキーラベルのスタイル */
        .access-key-label {
            color: black;
            background-color: rgba(255, 255, 255, 0.9);
            font-weight: bold;
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
            text-align: center;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid #ddd;
        }
        
        /* 入力欄のスタイル改善 */
        .stTextInput > div > div > input {
            background-color: white !important;
            color: black !important;
            border: 2px solid #4CAF50 !important;
            border-radius: 8px !important;
            padding: 12px !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
        }
        
        .stTextInput > div > div > input::placeholder {
            color: #666666 !important;
            font-style: italic;
        }
        
        /* フォーカス時のスタイル */
        .stTextInput > div > div > input:focus {
            border-color: #45a049 !important;
            box-shadow: 0 0 8px rgba(76, 175, 80, 0.3) !important;
        }
        
        /* 画像センター寄せ（強化版） */
        .login-image {
            text-align: center;
            margin: 0.5rem 0;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        /* 画像自体のスタイル */
        .login-image img {
            display: block;
            margin: 0 auto;
        }
        
        /* テキスト入力フィールド */
        .stTextInput > div > div > input {
            background-color: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        /* ページ全体の上部マージン削除 */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 中央寄せのログインフォーム（横幅拡大版）
        _, col2, _ = st.columns([0.5, 3, 0.5])
        
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            # 魔法使い画像とタイトルを横並び表示
            title_image_path = os.path.join(os.path.dirname(__file__), "assets", "title_wizard.png")
            if os.path.exists(title_image_path):
                # 画像とタイトルのカラム分割（横幅拡大対応）
                img_col, title_col = st.columns([1, 3])
                
                with img_col:
                    st.markdown('<div class="login-image-left">', unsafe_allow_html=True)
                    st.image(title_image_path, width=150)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with title_col:
                    st.markdown('<div class="login-title-right">', unsafe_allow_html=True)
                    st.markdown('<h1 class="login-title">AI文字起こし</h1>', unsafe_allow_html=True)
                    st.markdown('<h3 class="login-subtitle">（テスト版）</h3>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                # 画像がない場合はセンター表示
                st.markdown('<h1 class="login-title">AI文字起こし</h1>', unsafe_allow_html=True)
                st.markdown('<h3 class="login-subtitle">（テスト版）</h3>', unsafe_allow_html=True)
            
            st.markdown("**🔐 社内専用アクセス**")
            st.markdown("---")
            
            # アクセスキー入力（見やすく改良）
            st.markdown('<p class="access-key-label">🔑 アクセスキーを入力してください</p>', unsafe_allow_html=True)
            access_key = st.text_input(
                "アクセスキー",
                type="password",
                placeholder="社内配布されたキーを入力",
                help="社内で配布されているアクセスキーを入力してください",
                key="access_key_input",
                label_visibility="collapsed"
            )
            
            # ログインボタン
            _, col_btn2, _ = st.columns([1, 2, 1])
            with col_btn2:
                login_button = st.button("🚀 ログイン", use_container_width=True, type="primary")
            
            if login_button:
                if access_key == access_key_for_auth:
                    st.session_state.authenticated = True
                    st.success("✅ 認証に成功しました！")
                    st.balloons()  # お祝い効果
                    import time
                    time.sleep(1)
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    st.error("❌ アクセスキーが正しくありません")
                    
                    # 試行回数制限
                    if st.session_state.login_attempts >= 5:
                        st.error("⚠️ 試行回数が上限に達しました。管理者にお問い合わせください。")
                        st.stop()
            
            # 試行回数表示
            if st.session_state.login_attempts > 0:
                remaining = 5 - st.session_state.login_attempts
                st.warning(f"残り試行回数: {remaining}回")
            
            st.markdown("---")
            st.info("💡 アクセスキーは社内管理者から取得してください")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ここで処理を停止（認証されるまでメインアプリを表示しない）
        st.stop()

if __name__ == "__main__":
    # 認証チェック
    check_company_access()
    
    # 認証成功後にメインアプリを表示
    main()
