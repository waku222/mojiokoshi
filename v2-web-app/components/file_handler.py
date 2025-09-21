"""
ファイル処理用のUIコンポーネント
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Tuple

def display_file_info(uploaded_file) -> Tuple[str, float]:
    """
    アップロードされたファイルの情報を表示
    
    Args:
        uploaded_file: Streamlitアップロードファイルオブジェクト
        
    Returns:
        Tuple[str, float]: (ファイルタイプ, ファイルサイズMB)
    """
    if uploaded_file is None:
        return "", 0.0
    
    # ファイルサイズを計算
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    
    # ファイルタイプを判定
    file_extension = Path(uploaded_file.name).suffix.lower()
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm', '.m4v', '.3gp', '.mts'}
    audio_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.ogg'}
    
    if file_extension in video_extensions:
        file_type = "動画"
        icon = "🎬"
    elif file_extension in audio_extensions:
        file_type = "音声"
        icon = "🎵"
    else:
        file_type = "不明"
        icon = "📄"
    
    # 情報を表示
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style="
            background: linear-gradient(90deg, #f0f2f6, #ffffff);
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #1f77b4;
            margin: 10px 0;
        ">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 2em; margin-right: 15px;">{icon}</span>
                <div>
                    <h4 style="margin: 0; color: #333;">{file_type}ファイル</h4>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">
                        {uploaded_file.name}
                    </p>
                </div>
            </div>
            <div style="background: rgba(255,255,255,0.8); padding: 10px; border-radius: 5px;">
                <p style="margin: 0;"><strong>サイズ:</strong> {file_size_mb:.2f} MB</p>
                <p style="margin: 5px 0 0 0;"><strong>形式:</strong> {file_extension.upper()[1:]}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    return file_type, file_size_mb

def show_supported_formats():
    """サポートされているファイル形式を表示"""
    with st.expander("📋 対応ファイル形式"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🎵 音声ファイル**
            - WAV (推奨)
            - MP3
            - FLAC
            - M4A
            - OGG
            """)
        
        with col2:
            st.markdown("""
            **🎬 動画ファイル**
            - MP4 (推奨)
            - AVI
            - MOV
            - MKV
            - WMV
            - WEBM
            """)

def validate_file_size(file_size_mb: float, max_size_mb: float = 500) -> bool:
    """
    ファイルサイズの検証
    
    Args:
        file_size_mb: ファイルサイズ（MB）
        max_size_mb: 最大許可サイズ（MB）
        
    Returns:
        bool: 検証結果
    """
    if file_size_mb > max_size_mb:
        st.error(f"❌ ファイルサイズが大きすぎます（{file_size_mb:.2f}MB > {max_size_mb}MB）")
        return False
    
    if file_size_mb < 0.01:  # 10KB未満
        st.error("❌ ファイルが小さすぎます")
        return False
    
    return True

def create_file_uploader():
    """ファイルアップローダーの作成"""
    return st.file_uploader(
        "📁 音声ファイルまたは動画ファイルを選択してください",
        type=["wav", "mp3", "flac", "m4a", "ogg", "mp4", "avi", "mov", "mkv", "wmv", "webm"],
        help="最大ファイルサイズ: 500MB",
        label_visibility="visible"
    )

