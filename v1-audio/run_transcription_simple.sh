#!/bin/bash

# 音声文字起こし実行スクリプト（簡単版）

echo "音声文字起こしを開始します..."
echo "音声ファイル: 250726_収支予算書の作成方法.wav"
echo "出力ファイル: transcription_result.txt"
echo ""

# 文字起こしディレクトリに移動
cd "$(dirname "$0")"

# Pythonスクリプトを実行
python run_transcription_with_audio.py

echo ""
echo "処理完了！" 