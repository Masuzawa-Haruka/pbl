# pbl

## Djangoの実行方法

### 初回セットアップ

```bash
cd /Users/haruk/prog/pbl
python3 -m venv .venv
source .venv/bin/activate
pip install django
cd trading_text
python manage.py migrate
python manage.py runserver
```

ブラウザで以下を開きます。

```txt
http://127.0.0.1:8000/
```

### 2回目以降の起動

```bash
cd /Users/haruk/prog/pbl
source .venv/bin/activate
cd trading_text
python manage.py runserver
```

### Supabase Authを使う場合

このアプリでは、ログイン・メール確認は Supabase Auth を使います。Django 側のユーザーは、Supabaseログイン成功後に同じメールアドレスで自動同期されます。

1. Supabaseでプロジェクトを作成
2. Authentication > Providers > Email を有効化
3. Authentication > URL Configuration の Site URL にローカルURLを設定
   - 例: `http://127.0.0.1:8000/login/`
4. Project Settings > API から Project URL と anon public key を確認
5. 起動前に環境変数を設定

```bash
export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_ANON_KEY="Supabaseのanon public key"
cd /Users/haruk/prog/pbl/trading_text
../.venv/bin/python manage.py runserver
```

登録できるメールアドレスはアプリ側の制限により `@ecs.osaka-u.ac.jp` のみです。

### 通知メールをGmailから送る場合

Googleアカウントで2段階認証を有効化し、アプリパスワードを作成してから起動前に設定します。

```bash
export EMAIL_HOST_USER="your-gmail-address@gmail.com"
export EMAIL_HOST_PASSWORD="Googleのアプリパスワード"
export DEFAULT_FROM_EMAIL="OU Textbook <your-gmail-address@gmail.com>"
cd /Users/haruk/prog/pbl/trading_text
../.venv/bin/python manage.py runserver
```

登録できるメールアドレスはアプリ側の制限により `@ecs.osaka-u.ac.jp` のみです。

### Windows PowerShellの場合

```powershell
cd C:\path\to\pbl
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install django
cd trading_text
python manage.py migrate
python manage.py runserver
```

### Windows Command Promptの場合

```bat
cd C:\path\to\pbl
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install django
cd trading_text
python manage.py migrate
python manage.py runserver
```

## メモ

`manage.py` は `trading_text` フォルダの中にあるため、サーバー起動前に `cd trading_text` してください。
