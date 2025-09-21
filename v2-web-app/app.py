"""
文字起こしWebアプリケーション（Streamlit）
音声ファイルと動画ファイルの両方に対応した文字起こしサービス
"""

import streamlit as st
import os
import tempfile
import asyncio
from pathlib import Path
import logging
from datetime import datetime

# 共通機能のインポート
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.transcription_service import AudioTranscriptionService
from shared.config import *

# 動画処理の条件付きインポート
try:
    from shared.video_processor import VideoProcessor
    # 実際のライブラリ可用性もチェック
    video_processor = VideoProcessor()
    VIDEO_PROCESSING_AVAILABLE = video_processor.video_processing_available
    if not VIDEO_PROCESSING_AVAILABLE:
        logger.warning("Video processing libraries (moviepy/opencv) not available")
except ImportError as e:
    VIDEO_PROCESSING_AVAILABLE = False
    logger.warning(f"Video processing not available: {e}")
except Exception as e:
    VIDEO_PROCESSING_AVAILABLE = False
    logger.warning(f"Video processor initialization failed: {e}")

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    st.title("🎤 AI文字起こしサービス")
    st.markdown("**音声ファイル・動画ファイルから高精度な日本語文字起こしを行います**")
    
    # タイトル画像の表示
    title_image_path = os.path.join(os.path.dirname(__file__), "assets", "title_wizard.png")
    if os.path.exists(title_image_path):
        # 中央寄せで画像を表示
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(title_image_path, width=300, caption="AI魔法使いコウイチくんによる文字起こし")
    
    st.markdown("---")  # セパレーター追加
    
    # 認証情報の確認（Streamlit Cloud対応強化版）
    credentials_path = os.path.join(os.path.dirname(__file__), "..", "credentials", "service-account-key.json")
    
    # Streamlit Cloudの場合はsecretsから認証情報を取得
    debug_info = []
    try:
        # デバッグ: 利用可能なSecretsキー確認
        available_secrets = list(st.secrets.keys())
        debug_info.append(f"利用可能なSecretsキー: {available_secrets}")
        
        # セクション形式とフラット形式の両方に対応
        try:
            # セクション形式を試行
            gcp_service_account = st.secrets["gcp_service_account"]
            debug_info.append("gcp_service_account取得成功（セクション形式）")
            
            # より詳細な認証情報確認
            if gcp_service_account and isinstance(gcp_service_account, dict):
                required_fields = ["type", "project_id", "private_key", "client_email"]
                existing_fields = [field for field in required_fields if field in gcp_service_account]
                missing_fields = [field for field in required_fields if field not in gcp_service_account]
                
                debug_info.append(f"存在するフィールド: {existing_fields}")
                if missing_fields:
                    debug_info.append(f"不足フィールド: {missing_fields}")
                
                credentials_exists = all(field in gcp_service_account for field in required_fields)
                use_streamlit_secrets = True
                if credentials_exists:
                    logger.info("Streamlit Secrets認証情報確認済み")
                    debug_info.append("認証情報: 全フィールド確認済み ✅")
                else:
                    debug_info.append("認証情報: 必須フィールド不足 ❌")
            else:
                debug_info.append("gcp_service_accountが辞書形式ではない（フラット形式を試行）")
                # フラット形式を試行
                flat_keys = [
                    "gcp_service_account_type",
                    "gcp_service_account_project_id", 
                    "gcp_service_account_private_key",
                    "gcp_service_account_client_email"
                ]
                flat_exists = all(key in st.secrets for key in flat_keys)
                
                if flat_exists:
                    # フラット形式でサービスアカウント情報を構築
                    gcp_service_account = {
                        "type": st.secrets["gcp_service_account_type"],
                        "project_id": st.secrets["gcp_service_account_project_id"],
                        "private_key_id": st.secrets.get("gcp_service_account_private_key_id", ""),
                        "private_key": st.secrets["gcp_service_account_private_key"],
                        "client_email": st.secrets["gcp_service_account_client_email"],
                        "client_id": st.secrets.get("gcp_service_account_client_id", ""),
                        "auth_uri": st.secrets.get("gcp_service_account_auth_uri", ""),
                        "token_uri": st.secrets.get("gcp_service_account_token_uri", ""),
                        "auth_provider_x509_cert_url": st.secrets.get("gcp_service_account_auth_provider_x509_cert_url", ""),
                        "client_x509_cert_url": st.secrets.get("gcp_service_account_client_x509_cert_url", "")
                    }
                    credentials_exists = True
                    use_streamlit_secrets = True
                    debug_info.append("フラット形式での認証情報構築成功 ✅")
                else:
                    credentials_exists = False
                    use_streamlit_secrets = True
                    debug_info.append("フラット形式キーも不足 ❌")
        except KeyError:
            debug_info.append("セクション形式取得失敗 - フラット形式を試行")
            # フラット形式を試行
            flat_keys = [
                "gcp_service_account_type",
                "gcp_service_account_project_id", 
                "gcp_service_account_private_key",
                "gcp_service_account_client_email"
            ]
            flat_exists = all(key in st.secrets for key in flat_keys)
            
            if flat_exists:
                # フラット形式でサービスアカウント情報を構築
                gcp_service_account = {
                    "type": st.secrets["gcp_service_account_type"],
                    "project_id": st.secrets["gcp_service_account_project_id"],
                    "private_key_id": st.secrets.get("gcp_service_account_private_key_id", ""),
                    "private_key": st.secrets["gcp_service_account_private_key"],
                    "client_email": st.secrets["gcp_service_account_client_email"],
                    "client_id": st.secrets.get("gcp_service_account_client_id", ""),
                    "auth_uri": st.secrets.get("gcp_service_account_auth_uri", ""),
                    "token_uri": st.secrets.get("gcp_service_account_token_uri", ""),
                    "auth_provider_x509_cert_url": st.secrets.get("gcp_service_account_auth_provider_x509_cert_url", ""),
                    "client_x509_cert_url": st.secrets.get("gcp_service_account_client_x509_cert_url", "")
                }
                credentials_exists = True
                use_streamlit_secrets = True
                debug_info.append("フラット形式での認証情報構築成功 ✅")
            else:
                credentials_exists = False
        use_streamlit_secrets = True
                debug_info.append("フラット形式キーも不足 ❌")
    except (KeyError, FileNotFoundError) as e:
        logger.warning(f"Streamlit Secrets取得エラー: {e}")
        debug_info.append(f"Secrets取得エラー: {str(e)}")
        # ローカル環境の場合
        credentials_exists = os.path.exists(credentials_path)
        use_streamlit_secrets = False
        debug_info.append("ローカル環境モードに切り替え")
    
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
gcp_service_account_project_id = "gen-lang-client-0653854891"
gcp_service_account_private_key_id = "27887a0412001d91181210877e3c88d14977e65f"
gcp_service_account_private_key = "-----BEGIN PRIVATE KEY-----\\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDO4Mio1jkcZviX\\nQiC8awDknwUHxIPD173ElFKBXVt17XsJjQMrDAmlFHk23Y1yM7uKtzkONjWNSqJ9\\ne8JWC1aE/mEegPzPkdUNOGFYiEJJ7fGpL826QWm5vGDbiWnV1zY1q/SFSeoyLacF\\nXzzum4kqEIIdxBNMMNiWR1/zmqd6AZ/zDSkOwLVxlcfzygTw9loSyS/Q1ofY5Vzw\\nUUPGoEufOWVy6sItxMc9ikEGkkB5a4kACmuLdYWa/17TC6FlLLkT76pvHEZD57sb\\n+vR58/frhaS+ZoPUMyIjGDxUAgcILctyogEjVE7/+FQvj632c2KZ0YgrX8Hh53Gx\\nZBg/ZvbXAgMBAAECggEAL6F/cagI9CodGC5IfTkhtoGKVfR/5epZLdZ8fH5zHV61\\nEkjeLt4RpmllUyWFeILCrjhrMYN3pvVFHiENaGQp4mrzD2PhUSUhaW7OsuSEZqMb\\nHbn84uJGplXh8wnbTTnEqGzT2pBfFHiAWPNJgyJaXU35t0K6srMYWtlKFTtJTgSB\\nv2jchhNjDwrSPkGCEkhhn9KKudxOo45rnrzR2qYIJkBRVvLDLO+/O1COPO0LRTEl\\ny7czEVSzEwxchvH3Rrnq964yBIoWtZ0cbgd4+6XIOgyOqA0FT0RsTgBlFLeQcdaT\\naArzAOxMrlMXlqpPynckveyZz+msiFrViV207+w16QKBgQDr0+fQdpVN4BmSX9BQ\\ngNs+TeyI+OL1V9JvlGHhntmLnaxjKLipwsDrArybp15UAoNiecMN98C4DraDz/M+\\npW38d+1YSsG9PLyOQWT9ZsxZF3ELIU+nzeipxc0sK8nYc1F5tPAVWF9axPTxkYen\\n2IjWBk5Na4T2Kflli8VeqRQDJQKBgQDgkvIKwWYAuua3jaJkaa9gPYV0QtYyFraL\\nWAaD14d0C2IXhtjv24BAjHKDIFbJFhvUQjpslTheDTxb2MG4OpwL5fpiykeDHKaR\\ndbl94ndhNfYD7eMKCA9VffmOmlJkRaVhFbEOFVBOQi096DEBijHAfbSa4xW2DWpT\\nQ9lsE2lvSwKBgQDDHKl4sgPJUJYXoqopUNMT80i18qVkM2rp4iwxjUmT17oeuDxA\\nR99xEOyXI5xJiWLGgNM+pTKPlayv1cb8l8Yt0dNO71rnhG7Ei5pQhVKgi2J9wOu0\\nfAn5HKwp1XjEWnSYa3kPT/RklvvJOYyw89gSq1jxePmi6QtsVn3PWbgy+QKBgBXM\\nDXQfy1+8xFICjEWEwIHt1rsvFY0tCTDDLXa0f7AyvqWb8Ahv3KXnO+IgTGweGjti\\n5jrNzPfL/xTHGB5iiezZuJDII2LFcCFkNMnUJlQoIaXF/ChoGdzpakR+FAspe2DN\\n8y5zwSSnZa7Bj6gfmq6dRN9XtS7DZJOKXVsRE0W7AoGBAJAe/2NLkynvIWfC2GSO\\npw48K5wGjOvBrRQ7F1U33g++uWBd8TTllIdo5alra0sgySYeWJdRD9FIknR20M2c\\nkLiKUbsnsBLxckCUuFfMeaWZTNQMwvOBUUaE1kTlGdpe25lOY1igzEKMgP9BXqoA\\nRZHgmigY14wDQpxLG1Ex1EuM\\n-----END PRIVATE KEY-----\\n"
gcp_service_account_client_email = "mojiokoshi@gen-lang-client-0653854891.iam.gserviceaccount.com"
gcp_service_account_client_id = "105257418930370464852"
gcp_service_account_auth_uri = "https://accounts.google.com/o/oauth2/auth"
gcp_service_account_token_uri = "https://oauth2.googleapis.com/token"
gcp_service_account_auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
gcp_service_account_client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/mojiokoshi%40gen-lang-client-0653854891.iam.gserviceaccount.com"

# その他の設定
GCS_BUCKET_NAME = "250728transcription-bucket"
COMPANY_ACCESS_KEY = "tatsujiro25"''', language="toml")
                    
                    with st.expander("🔸 セクション形式（代替）"):
                        st.code('''[gcp_service_account]
type = "service_account"
project_id = "gen-lang-client-0653854891"
private_key_id = "27887a0412001d91181210877e3c88d14977e65f"
private_key = "-----BEGIN PRIVATE KEY-----\\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDO4Mio1jkcZviX\\nQiC8awDknwUHxIPD173ElFKBXVt17XsJjQMrDAmlFHk23Y1yM7uKtzkONjWNSqJ9\\ne8JWC1aE/mEegPzPkdUNOGFYiEJJ7fGpL826QWm5vGDbiWnV1zY1q/SFSeoyLacF\\nXzzum4kqEIIdxBNMMNiWR1/zmqd6AZ/zDSkOwLVxlcfzygTw9loSyS/Q1ofY5Vzw\\nUUPGoEufOWVy6sItxMc9ikEGkkB5a4kACmuLdYWa/17TC6FlLLkT76pvHEZD57sb\\n+vR58/frhaS+ZoPUMyIjGDxUAgcILctyogEjVE7/+FQvj632c2KZ0YgrX8Hh53Gx\\nZBg/ZvbXAgMBAAECggEAL6F/cagI9CodGC5IfTkhtoGKVfR/5epZLdZ8fH5zHV61\\nEkjeLt4RpmllUyWFeILCrjhrMYN3pvVFHiENaGQp4mrzD2PhUSUhaW7OsuSEZqMb\\nHbn84uJGplXh8wnbTTnEqGzT2pBfFHiAWPNJgyJaXU35t0K6srMYWtlKFTtJTgSB\\nv2jchhNjDwrSPkGCEkhhn9KKudxOo45rnrzR2qYIJkBRVvLDLO+/O1COPO0LRTEl\\ny7czEVSzEwxchvH3Rrnq964yBIoWtZ0cbgd4+6XIOgyOqA0FT0RsTgBlFLeQcdaT\\naArzAOxMrlMXlqpPynckveyZz+msiFrViV207+w16QKBgQDr0+fQdpVN4BmSX9BQ\\ngNs+TeyI+OL1V9JvlGHhntmLnaxjKLipwsDrArybp15UAoNiecMN98C4DraDz/M+\\npW38d+1YSsG9PLyOQWT9ZsxZF3ELIU+nzeipxc0sK8nYc1F5tPAVWF9axPTxkYen\\n2IjWBk5Na4T2Kflli8VeqRQDJQKBgQDgkvIKwWYAuua3jaJkaa9gPYV0QtYyFraL\\nWAaD14d0C2IXhtjv24BAjHKDIFbJFhvUQjpslTheDTxb2MG4OpwL5fpiykeDHKaR\\ndbl94ndhNfYD7eMKCA9VffmOmlJkRaVhFbEOFVBOQi096DEBijHAfbSa4xW2DWpT\\nQ9lsE2lvSwKBgQDDHKl4sgPJUJYXoqopUNMT80i18qVkM2rp4iwxjUmT17oeuDxA\\nR99xEOyXI5xJiWLGgNM+pTKPlayv1cb8l8Yt0dNO71rnhG7Ei5pQhVKgi2J9wOu0\\nfAn5HKwp1XjEWnSYa3kPT/RklvvJOYyw89gSq1jxePmi6QtsVn3PWbgy+QKBgBXM\\nDXQfy1+8xFICjEWEwIHt1rsvFY0tCTDDLXa0f7AyvqWb8Ahv3KXnO+IgTGweGjti\\n5jrNzPfL/xTHGB5iiezZuJDII2LFcCFkNMnUJlQoIaXF/ChoGdzpakR+FAspe2DN\\n8y5zwSSnZa7Bj6gfmq6dRN9XtS7DZJOKXVsRE0W7AoGBAJAe/2NLkynvIWfC2GSO\\npw48K5wGjOvBrRQ7F1U33g++uWBd8TTllIdo5alra0sgySYeWJdRD9FIknR20M2c\\nkLiKUbsnsBLxckCUuFfMeaWZTNQMwvOBUUaE1kTlGdpe25lOY1igzEKMgP9BXqoA\\nRZHgmigY14wDQpxLG1Ex1EuM\\n-----END PRIVATE KEY-----\\n"
client_email = "mojiokoshi@gen-lang-client-0653854891.iam.gserviceaccount.com"
client_id = "105257418930370464852"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/mojiokoshi%40gen-lang-client-0653854891.iam.gserviceaccount.com"

GCS_BUCKET_NAME = "250728transcription-bucket"
COMPANY_ACCESS_KEY = "tatsujiro25"''', language="toml")
            else:
                st.error(f"**管理者へ**: 以下の場所に配置してください:\n`{credentials_path}`")
        
        # GCSバケット名（Streamlit Cloud対応）
        try:
            default_bucket = st.secrets.get("GCS_BUCKET_NAME", GCS_BUCKET_NAME)
        except:
            default_bucket = GCS_BUCKET_NAME
            
        gcs_bucket = st.text_input(
            "GCSバケット名",
            value=default_bucket,
            help="長時間音声処理用のGCSバケット名"
        )
        
        # システム情報
        with st.expander("💻 システム情報"):
            st.markdown(f"""
            **認証状態**: {"✅ OK" if credentials_exists else "❌ 未設定"}
            **GCSバケット**: {gcs_bucket}
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
            
            # 処理ボタン
            if st.button("🚀 文字起こし開始", type="primary", use_container_width=True):
                if not credentials_exists:
                    st.error("❌ サービスアカウントキーファイルが見つかりません")
                    st.error("管理者にお問い合わせください")
                    return
                
                if not gcs_bucket.strip():
                    st.error("❌ GCSバケット名を入力してください")
                    return
                
                # 自動的に最適なチャンク長を決定
                optimal_chunk_length_ms = calculate_optimal_chunk_length(uploaded_file)
                
                # 文字起こし処理を実行
                process_transcription(
                    uploaded_file, 
                    credentials_path if not use_streamlit_secrets else None, 
                    gcs_bucket, 
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
            st.error("文字起こし処理に失敗しました")
        
        # 一時ファイルを削除
        os.unlink(input_file_path)
        # credentials_pathは固定ファイルなので削除しない
        
    except Exception as e:
        st.session_state.processing_status = "エラー"
        st.error(f"エラーが発生しました: {str(e)}")
        logger.error(f"文字起こし処理エラー: {str(e)}")

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
                raise Exception("動画処理機能が利用できません。必要なライブラリ（moviepy/opencv）がインストールされていない可能性があります。")
            
            status_text.text("🎬 動画から音声を抽出中...")
            progress_bar.progress(20)
            
            # 追加の安全チェック
            video_processor = VideoProcessor()
            if not video_processor.video_processing_available:
                raise Exception("動画処理ライブラリが実行時に利用できません（moviepy/opencv未インストール）")
            audio_file_path = await video_processor.process_video_for_transcription(input_file_path)
            
            if not audio_file_path:
                raise Exception("動画からの音声抽出に失敗しました")
        
        # 音声文字起こしサービスを初期化
        status_text.text("🤖 文字起こしサービス初期化中...")
        progress_bar.progress(30)
        
        if use_streamlit_secrets:
            # Streamlit Secretsから認証情報を取得
            gcp_service_account = st.secrets["gcp_service_account"]
            transcription_service = AudioTranscriptionService(
                service_account_info=dict(gcp_service_account),
                gcs_bucket_name=gcs_bucket
            )
        else:
            # ローカルファイルから認証
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
            raise Exception("文字起こし処理に失敗しました")
        
    except Exception as e:
        logger.error(f"非同期文字起こしエラー: {str(e)}")
        return None

def calculate_optimal_chunk_length(uploaded_file):
    """
    アップロードされたファイルに基づいて最適なチャンク長を自動計算
    
    Args:
        uploaded_file: Streamlitアップロードファイルオブジェクト
        
    Returns:
        int: チャンク長（ミリ秒）
    """
    # ファイルサイズを取得（MB単位）
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    
    # ファイルサイズに基づいて最適なチャンク長を決定
    if file_size_mb < 50:
        # 小さなファイル: 10分チャンク（高品質、少ないAPI呼び出し）
        chunk_length_ms = 10 * 60 * 1000  # 600,000ms
        logger.info(f"小ファイル検出 ({file_size_mb:.1f}MB) -> 10分チャンク")
    elif file_size_mb < 200:
        # 中程度のファイル: 5分チャンク（バランス）
        chunk_length_ms = 5 * 60 * 1000   # 300,000ms
        logger.info(f"中ファイル検出 ({file_size_mb:.1f}MB) -> 5分チャンク")
    else:
        # 大きなファイル: 3分チャンク（メモリ効率重視）
        chunk_length_ms = 3 * 60 * 1000   # 180,000ms
        logger.info(f"大ファイル検出 ({file_size_mb:.1f}MB) -> 3分チャンク")
    
    return chunk_length_ms

def check_company_access():
    """社内専用アクセス認証"""
    
    # 社内専用アクセスキー（環境変数またはSecretsから取得）
    try:
        COMPANY_ACCESS_KEY = st.secrets["COMPANY_ACCESS_KEY"]
    except:
        # フォールバック用のデフォルトキー（本番環境では削除推奨）
        COMPANY_ACCESS_KEY = "tatsujiro25"
    
    # セッション状態の初期化
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.login_attempts = 0
    
    if not st.session_state.authenticated:
        # 認証画面のスタイル設定
        st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 20px auto;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .login-title {
            text-align: center;
            font-size: 1.8rem;
            margin-bottom: 0.2rem;
            color: white;
        }
        .login-subtitle {
            text-align: center;
            font-size: 1rem;
            margin-bottom: 0.5rem;
            color: #ff6b6b;
            font-weight: bold;
        }
        .login-image {
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .stTextInput > div > div > input {
            background-color: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 中央寄せのログインフォーム
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            # タイトル画像をログイン画面にも表示
            title_image_path = os.path.join(os.path.dirname(__file__), "assets", "title_wizard.png")
            if os.path.exists(title_image_path):
                st.markdown('<div class="login-image">', unsafe_allow_html=True)
                st.image(title_image_path, width=180)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<h1 class="login-title">🎤 AI文字起こしサービス</h1>', unsafe_allow_html=True)
            st.markdown('<h3 class="login-subtitle">（テスト版）</h3>', unsafe_allow_html=True)
            st.markdown("**🔐 社内専用アクセス**")
            st.markdown("---")
            
            # アクセスキー入力
            access_key = st.text_input(
                "アクセスキーを入力してください",
                type="password",
                placeholder="社内配布されたキーを入力",
                help="社内で配布されているアクセスキーを入力してください"
            )
            
            # ログインボタン
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                login_button = st.button("🚀 ログイン", use_container_width=True, type="primary")
            
            if login_button:
                if access_key == COMPANY_ACCESS_KEY:
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
