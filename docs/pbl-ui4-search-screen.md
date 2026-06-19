# pbl-ui4 検索一覧画面 実装指示書

## 担当ブランチ

```bash
git switch -c feature/search-screen-ui
```

## 作業手順

1. ブランチを切る

```bash
git switch main
git pull --rebase origin main
git switch -c feature/search-screen-ui
```

2. 作業を始めるたびにpullする

```bash
git switch feature/search-screen-ui
git pull --rebase origin main
```

3. HTML, CSSファイルを作成する
4. できたらcommit, pushする
5. GitHubでPRを作成する

## 参考画像

```txt
ui/search-screen.png
```

画面内容は「出品されている教科書を検索する一覧画面」です。

## 実装ルール

- Tailwind CSSは使用禁止です。
- HTMLはDjangoテンプレートで実装してください。
- CSSは通常のCSSファイルに分けて書いてください。
- 既存の `base.html` を継承してください。
- 共通footerは既存の `components/footer.html` を使ってください。
- 画像をそのまま貼るのは禁止です。HTML/CSSで再現してください。

## 作成・編集するファイル

### 1. 検索一覧テンプレート

作成ファイル:

```txt
trading_text/main/templates/main/search.html
```

テンプレート例:

```django
{% extends 'main/base.html' %}
{% load static %}

{% block title %}探す | OU Textbook{% endblock %}

{% block extra_style %}
<link rel="stylesheet" href="{% static 'main/css/search.css' %}">
{% endblock %}

{% block header_title %}探す{% endblock %}

{% block content %}
<!-- ここに検索一覧画面を実装 -->
{% endblock %}
```

### 2. 検索一覧CSS

作成ファイル:

```txt
trading_text/main/static/main/css/search.css
```

### 3. viewの追加

編集ファイル:

```txt
trading_text/main/views.py
```

追加するview:

```python
def search(request):
    return render(request, 'main/search.html')
```

### 4. URLの追加

編集ファイル:

```txt
trading_text/main/urls.py
```

追加するURL:

```python
path('search/', views.search, name='search'),
```

## 画面仕様

### 表示要素

上から順番に配置してください。

1. 画面タイトル

```txt
探す
```

2. 検索フォーム

```txt
書名・著者・キーワードで検索
```

右側にフィルターアイコンのボタンを配置してください。

3. カテゴリチップ

```txt
すべて
教養・基礎
専門
理系
文系
```

`すべて` を青背景の選択状態にしてください。

4. キャンパスチップ

```txt
豊中
吹田
箕面
すべてのキャンパス
```

5. 並び替えセレクト風ボタン

```txt
新着順
```

6. 教科書一覧

最低4件を静的データで表示してください。

```txt
基礎からの線形代数
著者：石村園子
300円
豊中キャンパス
いいね 12

ミクロ経済学の基礎
著者：大山道広
400円
吹田キャンパス
いいね 8

化学の新研究
著者：卯田正彦
350円
豊中キャンパス
いいね 5

物理学のエッセンス
著者：浜島清利
300円
箕面キャンパス
いいね 3
```

## レイアウト目安

- 最大幅は `430px` 前後。
- 検索フォームは角丸の横長ボックス。
- チップは横並びで折り返し可能にしてください。
- 一覧は左に教科書画像枠、右にタイトル・著者・価格・キャンパス、右端にハート数。
- 価格は赤。
- footerに重ならないよう下余白を確保してください。

## 画像について

教科書画像は仮の四角でOKです。実画像を使う場合は、後で専用の教材画像フォルダを作ってから使用してください。

## 動作確認

```bash
cd /Users/haruk/prog/pbl
source .venv/bin/activate
cd trading_text
python manage.py runserver
```

確認URL:

```txt
http://127.0.0.1:8000/search/
```

## 完了条件

- `/search/` で検索一覧画面が表示される。
- Tailwind CSSを使っていない。
- `base.html` を継承している。
- `search.html` と `search.css` に役割が分かれている。
- footerの「探す」がアクティブに見える。
- スマホ幅で文字や一覧がはみ出さない。

## コミットメッセージ例

```bash
git add .
git commit -m "検索一覧画面UIを追加"
```
