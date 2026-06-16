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
