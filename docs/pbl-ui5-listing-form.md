# pbl-ui5 出品フォーム画面 実装指示書

## 担当ブランチ

```bash
git switch -c feature/listing-form-ui
```

## 作業手順

1. ブランチを切る

```bash
git switch main
git pull --rebase origin main
git switch -c feature/listing-form-ui
```

2. 作業を始めるたびにpullする

```bash
git switch feature/listing-form-ui
git pull --rebase origin main
```

3. HTML, CSSファイルを作成する
4. できたらcommit, pushする
5. GitHubでPRを作成する

## 参考画像

```txt
ui/listing-form-screen.png
```

画面内容は「教科書を出品するフォーム画面」です。

## 実装ルール

- Tailwind CSSは使用禁止です。
- HTMLはDjangoテンプレートで実装してください。
- CSSは通常のCSSファイルに分けて書いてください。
- 既存の `base.html` を継承してください。
- この画面ではスマホ内footerは不要です。画像でもフォーム画面内にはfooterがありません。
- 画像をそのまま貼るのは禁止です。HTML/CSSで再現してください。

## 作成・編集するファイル

### 1. 出品フォームテンプレート

作成ファイル:

```txt
trading_text/main/templates/main/listing_form.html
```

テンプレート例:

```django
{% extends 'main/base.html' %}
{% load static %}

{% block title %}教科書を出品する | OU Textbook{% endblock %}

{% block extra_style %}
<link rel="stylesheet" href="{% static 'main/css/listing_form.css' %}">
{% endblock %}

{% block header_title %}教科書を出品する{% endblock %}

{% block footer %}{% endblock %}

{% block content %}
<!-- ここに出品フォームを実装 -->
{% endblock %}
```

### 2. 出品フォームCSS

作成ファイル:

```txt
trading_text/main/static/main/css/listing_form.css
```

### 3. viewの追加

編集ファイル:

```txt
trading_text/main/views.py
```

追加するview:

```python
def listing_form(request):
    return render(request, 'main/listing_form.html')
```

### 4. URLの追加

編集ファイル:

```txt
trading_text/main/urls.py
```

追加するURL:

```python
path('listing/new/', views.listing_form, name='listing_form'),
```

## 画面仕様

### 表示要素

上から順番に配置してください。

1. ヘッダー

```txt
教科書を出品する
```

左に戻るアイコンを配置してください。

2. 入力フォーム

以下の項目を表示してください。

```txt
書名
基礎からの線形代数

著者
石村園子

価格
300
円

状態
良い

キャンパス
豊中キャンパス

説明（任意）
書き込みはほとんどありません。
14/200

写真（最大5枚）
```

3. 写真アップロード欄

- 3枚のサムネイル風ボックスを表示してください。
- 各サムネイル右上に削除用の小さい `×` を置いてください。
- 4つ目に点線枠の追加ボックスを置き、中央に `+` を表示してください。

4. 送信ボタン

```txt
出品する
```

黄色背景、黒文字、太字にしてください。

## レイアウト目安

- 最大幅は `430px` 前後。
- フォーム全体は左右24px程度の余白。
- labelは青、太字。
- input/select/textareaは白背景、薄いグレー枠、角丸。
- 価格は入力欄と `円` ボックスを横並び。
- 下部ボタンは横幅いっぱい、角丸。
- スマホ画面で縦スクロールできるようにしてください。

## 注意

この指示書では見た目のみ実装します。実際のPOST処理、画像アップロード、バリデーションは別タスクで実装します。

## 動作確認

```bash
cd /Users/haruk/prog/pbl
source .venv/bin/activate
cd trading_text
python manage.py runserver
```

確認URL:

```txt
http://127.0.0.1:8000/listing/new/
```

## 完了条件

- `/listing/new/` で出品フォームが表示される。
- Tailwind CSSを使っていない。
- `base.html` を継承している。
- `listing_form.html` と `listing_form.css` に役割が分かれている。
- 入力欄、写真欄、黄色の出品ボタンが画像に近い。
- スマホ幅でフォームがはみ出さない。

## コミットメッセージ例

```bash
git add .
git commit -m "出品フォーム画面UIを追加"
```
