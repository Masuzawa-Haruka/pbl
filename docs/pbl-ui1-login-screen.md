# pbl-ui1 ログイン画面 実装指示書

## 担当ブランチ

以下のブランチを作成して作業してください。

```bash
git switch -c feature/login-screen-ui
```

## 作業手順

1. ブランチを切る

```bash
git switch main
git pull --rebase origin main
git switch -c feature/login-screen-ui
```

2. 作業を始めるたびにpullする

```bash
git switch feature/login-screen-ui
git pull --rebase origin main
```

3. HTML, CSSファイルを作成する
4. できたらcommit, pushする
5. GitHubでPRを作成する

## 参考画像

実装対象は以下の画像です。

```txt
ui/login-screen.png
```

画面内容は「大阪大学生のみログインできる」ログイン画面です。

## 実装ルール

- Tailwind CSSは使用禁止です。
- HTMLはDjangoテンプレートで実装してください。
- CSSは通常のCSSファイルに分けて書いてください。
- 既存の `base.html` を継承してください。
- 共通footerは既存の `components/footer.html` を使ってください。
- 画像をそのまま画面に貼り付けるのは禁止です。HTML/CSSで再現してください。

## 作成・編集するファイル

### 1. ログイン画面テンプレート

作成ファイル:

```txt
trading_text/main/templates/main/login.html
```

役割:

ログイン画面本体を実装します。

このテンプレートは以下のように `base.html` を継承してください。

```django
{% extends 'main/base.html' %}
{% load static %}

{% block title %}ログイン | OU Textbook{% endblock %}

{% block extra_style %}
<link rel="stylesheet" href="{% static 'main/css/login.css' %}">
{% endblock %}

{% block header %}{% endblock %}

{% block content %}
<!-- ここにログイン画面を実装 -->
{% endblock %}
```

### 2. ログイン画面CSS

作成ファイル:

```txt
trading_text/main/static/main/css/login.css
```

役割:

`login.html` 専用のスタイルを書きます。

### 3. viewの追加

編集ファイル:

```txt
trading_text/main/views.py
```

以下のviewを追加してください。

```python
def login(request):
    return render(request, 'main/login.html')
```

### 4. URLの追加

編集ファイル:

```txt
trading_text/main/urls.py
```

以下のURLを追加してください。

```python
path('login/', views.login, name='login'),
```

## 画面仕様

### 全体

- スマホアプリのログイン画面として実装してください。
- 最大幅は既存の `base.css` に合わせて `430px` 前後にしてください。
- 背景は白。
- 文字色の基本は濃紺。
- メインカラーはOU Textbookの青を使用してください。

推奨色:

```css
--ou-blue: #0034b8;
--ou-navy: #070d2f;
--ou-border: #dce2ec;
```

### 表示する要素

上から順番に以下を配置してください。

1. サービス名

```txt
OU Textbook
```

2. サブタイトル

```txt
大阪大学生専用
参考書リユースアプリ
```

3. 利用対象説明

```txt
大阪大学の学生（学部生・院生）のみ
ご利用いただけます
```

4. ログイン方法の見出し

```txt
ログイン方法を選択
```

5. 大阪大学メールログインボタン

```txt
大阪大学メールでログイン
(~@osaka-u.ac.jp)
```

左側にメールアイコンを入れてください。SVGで実装してOKです。

6. 注意書き

```txt
※ 学生情報は認証のみに使用されます
```

7. 区切り線

8. 新規登録案内

```txt
アカウントをお持ちでない方はこちら
新規登録（大阪大学生のみ）
```

`新規登録（大阪大学生のみ）` は青色のリンク風にしてください。

## レイアウト目安

- 画面上部から余白を取って中央寄せにしてください。
- `OU Textbook` は大きめ、太字。
- サブタイトルは2行。
- ログインボタンは横幅いっぱいではなく、左右に余白を持たせてください。
- ログインボタンは角丸、薄いグレーの枠線、白背景。
- footerに重ならないよう、下部に十分な余白を入れてください。

## クラス名の例

CSSは以下のようなクラス名で実装してください。

```html
<section class="login-page">
  <div class="login-card">
    <h1 class="login-logo">OU Textbook</h1>
    <p class="login-subtitle">...</p>
    <p class="login-target">...</p>
    <h2 class="login-heading">...</h2>
    <a class="login-button" href="#">
      <span class="login-button__icon">...</span>
      <span class="login-button__text">...</span>
    </a>
  </div>
</section>
```

## 動作確認

以下でサーバーを起動してください。

```bash
cd /Users/haruk/prog/pbl
source .venv/bin/activate
cd trading_text
python manage.py runserver
```

ブラウザで以下を確認してください。

```txt
http://127.0.0.1:8000/login/
```

## 完了条件

- `/login/` でログイン画面が表示される。
- Tailwind CSSを使っていない。
- `base.html` を継承している。
- `login.html` と `login.css` に役割が分かれている。
- 既存footerが画面下部に表示される。
- スマホ幅で見ても文字やボタンがはみ出さない。

## コミットメッセージ例

```bash
git add .
git commit -m "ログイン画面UIを追加"
```
