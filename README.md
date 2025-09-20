# 🎤 AI文字起こしサービス

Google Cloud Speech-to-Text APIを使用した高精度な日本語文字起こしサービスです。  
音声ファイルと動画ファイルの両方に対応しており、長時間の音声も効率的に処理できます。

## ✨ 機能概要

### v1-audio（コマンドライン版）
- 音声ファイル専用の文字起こし処理
- Python環境での直接実行
- 開発者向けの高度な設定が可能

### v2-web-app（Webアプリ版）⭐️
- **Streamlit**を使用したWebアプリケーション
- 動画ファイルからの音声抽出機能
- 社内専用アクセス認証機能
- ファイルサイズ最大500MB対応
- 非エンジニア向けの簡単操作

## 🚀 主な特徴

- **高精度**: Google Cloud Speech-to-Text APIによる高品質な文字起こし
- **長時間対応**: 自動チャンク分割で長時間音声も処理可能
- **動画対応**: MP4、AVI、MOV等の動画ファイルから音声を自動抽出
- **並列処理**: 複数チャンクの同時処理で高速化
- **自動最適化**: ファイルサイズに応じたチャンク長の自動調整
- **セキュリティ**: 社内専用アクセス認証システム

## 📂 プロジェクト構造

```
mojiokoshi/
├── v1-audio/           # コマンドライン版（音声のみ）
├── v2-web-app/         # Streamlitアプリ版（推奨）⭐️
│   ├── app.py          # メインアプリケーション
│   ├── assets/         # 画像リソース
│   └── .streamlit/     # Streamlit設定
├── shared/             # 共通機能
│   ├── transcription_service.py  # 文字起こしサービス
│   ├── video_processor.py        # 動画処理
│   └── config.py                 # 設定ファイル
└── requirements.txt    # Python依存関係
```

## 🛠️ セットアップ

### 1. 必要要件

- Python 3.8+
- Google Cloud Platform アカウント
- Google Cloud Speech-to-Text API有効化
- Google Cloud Storage バケット

### 2. 依存関係のインストール

```bash
# 仮想環境の作成（推奨）
python3 -m venv new_venv
source new_venv/bin/activate  # Mac/Linux
# new_venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt
```

### 3. Google Cloud認証設定

1. Google Cloud Consoleでサービスアカウントキーを作成
2. JSONファイルを `credentials/service-account-key.json` に配置
3. `shared/config.py` でGCSバケット名を設定

⚠️ **重要**: 認証ファイルは絶対にGitHubにコミットしないでください！

### 4. Streamlitアプリの起動

```bash
cd v2-web-app
streamlit run app.py
```

ブラウザで `http://localhost:8501` にアクセスしてください。

## 🔐 認証について

Webアプリは社内専用として設計されており、アクセスキーによる認証が必要です。
- アクセスキーは管理者から取得してください
- 認証後、メインアプリケーションにアクセス可能

## 📋 対応ファイル形式

### 音声ファイル
- WAV, MP3, FLAC, M4A, OGG

### 動画ファイル  
- MP4, AVI, MOV, MKV, WMV, WEBM

### ファイルサイズ制限
- 最大500MB（Streamlitアプリ）

## 🎯 使用方法

### Webアプリ（推奨）
1. ブラウザで `http://localhost:8501` にアクセス
2. アクセスキーを入力してログイン
3. 音声または動画ファイルをアップロード
4. 「文字起こし開始」ボタンをクリック
5. 結果をダウンロード

### コマンドライン（v1-audio）
```bash
cd v1-audio
python main.py --input audio_file.wav --output result.txt
```

## ⚙️ 技術仕様

- **フレームワーク**: Streamlit, asyncio
- **音声処理**: pydub, moviepy
- **クラウドAPI**: Google Cloud Speech-to-Text, Google Cloud Storage
- **認証**: セッション管理による社内専用アクセス
- **並列処理**: 最大5並列チャンク処理

## 📊 パフォーマンス

- **処理速度**: 音声長の約1/3の時間で処理完了
- **精度**: 日本語音声で95%以上の高精度
- **対応時間**: 数時間の長時間音声も処理可能

## 🔧 開発情報

### カスタマイズポイント
- `shared/config.py`: 基本設定
- `v2-web-app/app.py`: UI・認証・ワークフロー
- `.streamlit/config.toml`: Streamlit設定

### ログ出力
処理状況は詳細なログで確認可能です。

## 🏢 企業利用について

このアプリは社内専用として設計されており、以下の特徴があります：
- アクセス制御による社内限定利用
- 機密音声ファイルの安全な処理
- 管理者による設定・認証情報の一元管理

## 📝 ライセンス

このプロジェクトは社内利用を目的として開発されました。  
商用利用の際は、Google Cloud Speech-to-Text APIの利用規約をご確認ください。

## 👨‍💻 開発者

- AI魔法使いコウイチくんによる文字起こし
- Streamlit + Google Cloud Speech-to-Text API

---

**🎉 高精度な日本語文字起こしをお楽しみください！**