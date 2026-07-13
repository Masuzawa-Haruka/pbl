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

## Renderへのデプロイ

このリポジトリではDjangoプロジェクトが `trading_text/` の中にあるため、RenderのRoot Directoryは `trading_text` にします。

### 1. GitHubへpush

```bash
cd /Users/haruk/prog/pbl
git add .
git commit -m "Prepare Render deployment"
git push origin main
```

### 2. RenderでWeb Serviceを作成

Render Dashboardで次の順番に進みます。

```txt
New
Web Service
GitHubリポジトリを選択
```

設定値は次にします。

```txt
Language: Python 3
Branch: main
Root Directory: trading_text
Build Command: ./build.sh
Start Command: python -m gunicorn trading_text.wsgi:application
```

`render.yaml` を使う場合は、RenderのBlueprintからこのリポジトリを選んでも同じ構成で作成できます。

### 3. RenderのEnvironment Variablesを設定

最低限、次を設定します。

```txt
DEBUG=False
SECRET_KEY=RenderのGenerateで作成
SUPABASE_URL=SupabaseのProject URL
SUPABASE_ANON_KEY=Supabaseのanon public key
```

本番でデータを消したくない場合は、次も設定します。

```txt
DATABASE_URL=Supabase PostgresまたはRender Postgresの接続URL
```

Supabase Postgresを使う場合は、接続URLの末尾に `?sslmode=require` を付けます。

`DATABASE_URL` を設定しない場合、Render上ではSQLiteで動きます。ただしRenderのファイルシステムは永続DB向きではないため、再デプロイや再起動でデータが消える可能性があります。発表用に画面だけ見せる程度ならSQLiteでも確認できますが、継続利用するならPostgreSQLを使ってください。

### 4. Supabase AuthのURL設定

RenderのデプロイURLが発行されたら、Supabase Dashboardで次を設定します。

```txt
Authentication
URL Configuration
Site URL: https://作成したRender名.onrender.com/login/
Redirect URLs: https://作成したRender名.onrender.com/login/
```

ローカルでも使う場合は、Redirect URLsにこれも残します。

```txt
http://127.0.0.1:8000/login/
```

### 5. デプロイ確認

RenderのDeploy Logsで次が成功していることを確認します。

```txt
python manage.py collectstatic --no-input
python manage.py migrate
python -m gunicorn trading_text.wsgi:application
```

公開URLを開いてログイン画面が表示されればOKです。
