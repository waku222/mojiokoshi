# Streamlit Cloud Secrets 設定ガイド

このドキュメントは、Streamlit Cloudで文字起こしアプリをデプロイする際に必要なSecretsの設定方法を説明します。

## 📋 必要な設定

Streamlit Cloud の **Settings → Secrets** に以下の内容を設定してください。

## 🔐 Secrets 設定内容（TOML形式）

```toml
# アクセスキー
COMPANY_ACCESS_KEY = "tatsujiro25Koueki"

# GCS設定
GCS_BUCKET_NAME = "250728transcription-bucket"

# サービスアカウント設定（フラット形式）
gcp_service_account_type = "service_account"
gcp_service_account_project_id = "gen-lang-client-0653854891"
gcp_service_account_private_key_id = "27887a0412001d91181210877e3c88d14977e65f"
gcp_service_account_client_email = "mojiokoshi@gen-lang-client-0653854891.iam.gserviceaccount.com"
gcp_service_account_client_id = "105257418930370464852"
gcp_service_account_auth_uri = "https://accounts.google.com/o/oauth2/auth"
gcp_service_account_token_uri = "https://oauth2.googleapis.com/token"
gcp_service_account_auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
gcp_service_account_client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/mojiokoshi%40gen-lang-client-0653854891.iam.gserviceaccount.com"

# private_key（3行に分割）
gcp_service_account_private_key = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDO4Mio1jkcZviXQiC8awDknwUHxIPD173ElFKBXVt17XsJjQMrDAmlFHk23Y1yM7uKtzkONjWNSqJ9e8JWC1aE/mEegPzPkdUNOGFYiEJJ7fGpL826QWm5vGDbiWnV1zY1q/SFSeoyLacFXzzum4kqEIIdxBNMMNiWR1/zmqd6AZ/zDSkOwLVxlcfzygTw9loSyS/Q1ofY5VzwUUPGoEufOWVy6sItxMc9ikEGkkB5a4kACmuLdYWa/17TC6FlLLkT76pvHEZD57sb+vR58/frhaS+ZoPUMyIjGDxUAgcILctyogEjVE7/+FQvj632c2KZ0YgrX8Hh53GxZBg/ZvbXAgMBAAECggEAL6F/cagI9CodGC5IfTkhtoGKVfR/5epZLdZ8fH5zHV61EkjeLt4RpmllUyWFeILCrjhrMYN3pvVFHiENaGQp4mrzD2PhUSUhaW7OsuSEZqMbHbn84uJGplXh8wnbTTnEqGzT2pBfFHiAWPNJgyJaXU35t0K6srMYWtlKFTtJTgSBv2jchhNjDwrSPkGCEkhhn9KKudxOo45rnrzR2qYIJkBRVvLDLO+/O1COPO0LRTEly7czEVSzEwxchvH3Rrnq964yBIoWtZ0cbgd4+6XIOgyOqA0FT0RsTgBlFLeQcdaTaArzAOxMrlMXlqpPynckveyZz+msiFrViV207+w16QKBgQDr0+fQdpVN4BmSX9BQgNs+TeyI+OL1V9JvlGHhntmLnaxjKLipwsDrArybp15UAoNiecMN98C4DraDz/M+pW38d+1YSsG9PLyOQWT9ZsxZF3ELIU+nzeipxc0sK8nYc1F5tPAVWF9axPTxkYen2IjWBk5Na4T2Kflli8VeqRQDJQKBgQDgkvIKwWYAuua3jaJkaa9gPYV0QtYyFraLWAaD14d0C2IXhtjv24BAjHKDIFbJFhvUQjpslTheDTxb2MG4OpwL5fpiykeDHKaRdbl94ndhNfYD7eMKCA9VffmOmlJkRaVhFbEOFVBOQi096DEBijHAfbSa4xW2DWpTQ9lsE2lvSwKBgQDDHKl4sgPJUJYXoqopUNMT80i18qVkM2rp4iwxjUmT17oeuDxAR99xEOyXI5xJiWLGgNM+pTKPlayv1cb8l8Yt0dNO71rnhG7Ei5pQhVKgi2J9wOu0fAn5HKwp1XjEWnSYa3kPT/RklvvJOYyw89gSq1jxePmi6QtsVn3PWbgy+QKBgBXMDXQfy1+8xFICjEWEwIHt1rsvFY0tCTDDLXa0f7AyvqWb8Ahv3KXnO+IgTGweGjti5jrNzPfL/xTHGB5iiezZuJDII2LFcCFkNMnUJlQoIaXF/ChoGdzpakR+FAspe2DN8y5zwSSnZa7Bj6gfmq6dRN9XtS7DZJOKXVsRE0W7AoGBAJAe/2NLkynvIWfC2GSOzw48K5wGjOvBrRQ7F1U33g++uWBd8TTllIdo5alra0sgySYeWJdRD9FIknR20M2ckLiKUbsnsBLxckCUuFfMeaWZTNQMwvOBUUaE1kTlGdpe25lOY1igzEKMgP9BXqoARZHgmigY14wDQpxLG1Ex1EuM
-----END PRIVATE KEY-----"""
```

## 📝 設定手順

### 1. Streamlit Cloud にログイン

[https://share.streamlit.io/](https://share.streamlit.io/) にアクセスし、GitHubアカウントでログインします。

### 2. アプリを選択

デプロイ済みの「文字起こしコウイチくん」アプリを選択します。

### 3. Settings を開く

アプリ管理画面で、右上の **⋮** メニューから **Settings** を選択します。

### 4. Secrets を設定

1. 左側メニューから **Secrets** を選択
2. 上記の TOML 形式の設定内容をコピー＆ペースト
3. **Save** ボタンをクリック
4. アプリが自動的に再起動します

### 5. 動作確認

アプリが再起動したら、以下を確認してください：

- ✅ ログイン画面でアクセスキーが認証される
- ✅ GCSバケット名が自動入力されている（`250728transcription-bucket`）
- ✅ ファイルアップロードと文字起こしが正常動作する

## ⚠️ 重要な注意事項

### セキュリティ

- **private_key は絶対に公開リポジトリにコミットしないでください**
- Secrets は Streamlit Cloud の安全な環境でのみ管理してください
- サービスアカウントキーは定期的にローテーションすることを推奨します

### トラブルシューティング

#### Secrets が反映されない場合

1. **Save** ボタンを押したか確認
2. アプリが再起動したか確認（数秒〜数十秒かかります）
3. ブラウザのキャッシュをクリアして再読み込み
4. Streamlit Cloud のログを確認（Settings → Logs）

#### 認証エラーが出る場合

1. `gcp_service_account_private_key` の改行が正しいか確認
2. TOMLの形式（引用符、インデントなど）が正しいか確認
3. サービスアカウントがGoogle Cloud で有効化されているか確認
4. Speech-to-Text API が有効化されているか確認

#### GCSバケットが見つからない場合

1. `GCS_BUCKET_NAME` が正しいか確認（`250728transcription-bucket`）
2. サービスアカウントにバケットへのアクセス権限があるか確認
3. Google Cloud Console でバケットが存在するか確認

## 📚 関連ドキュメント

- [Streamlit Secrets 管理](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Google Cloud Speech-to-Text](https://cloud.google.com/speech-to-text/docs)
- [Google Cloud Storage](https://cloud.google.com/storage/docs)

## 💡 ヒント

### ローカル開発環境での設定

ローカルで開発する場合は、`.streamlit/secrets.toml` ファイルを作成して同じ内容を設定してください。

```bash
mkdir -p .streamlit
nano .streamlit/secrets.toml
# 上記の内容をペースト
```

⚠️ **注意**: `.streamlit/secrets.toml` は `.gitignore` に追加して、Gitにコミットしないでください。

---

**最終更新**: 2026-01-22
