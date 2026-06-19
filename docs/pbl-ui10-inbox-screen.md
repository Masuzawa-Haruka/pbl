# pbl-ui10 受信箱画面 実装指示書

## 担当者
沼田さん

## 担当ブランチ

```bash
git checkout -b feature/inbox-screen-ui
```

## 作業手順

1. ブランチを切る

```bash
git checkout main
git pull --rebase origin main
git checkout -b feature/inbox-screen-ui
```

2. 作業を始めるたびにpullする

```bash
git checkout feature/inbox-screen-ui
git pull --rebase origin main
```

3. HTML, CSSファイルを作成する
4. できたらcommit, pushする
5. GitHubでPRを作成する

## 参考画像

```txt
ui/inbox-screen.png
```

画面内容は「メッセージとお知らせを確認する受信箱画面」です。

## 実装ルール

- Tailwind CSSは使用禁止です。
- HTMLはDjangoテンプレートで実装してください。
- CSSは通常のCSSファイルに分けて書いてください。
- 既存の `base.html` を継承してください。
- 共通footerは既存の `components/footer.html` を使ってください。
- 画像をそのまま画面に貼り付けるのは禁止です。HTML/CSSで再現してください。

## 作成・編集するファイル

### 1. 受信箱テンプレート

作成ファイル:

```txt
trading_text/main/templates/main/inbox.html
```

テンプレート例:

```django
{% extends 'main/base.html' %}
{% load static %}

{% block title %}受信箱 | OU Textbook{% endblock %}

{% block extra_style %}
<link rel="stylesheet" href="{% static 'main/css/inbox.css' %}">
{% endblock %}

{% block header_title %}受信箱{% endblock %}

{% block content %}
<!-- ここに受信箱画面を実装 -->
{% endblock %}
```

### 2. 受信箱CSS

作成ファイル:

```txt
trading_text/main/static/main/css/inbox.css
```

### 3. viewの追加

編集ファイル:

```txt
trading_text/main/views.py
```

追加するview:

```python
def inbox(request):
    return render(request, 'main/inbox.html')
```

### 4. URLの追加

編集ファイル:

```txt
trading_text/main/urls.py
```

追加するURL:

```python
path('inbox/', views.inbox, name='inbox'),
```

## 画面仕様

### 表示要素

上から順番に配置してください。

1. ヘッダー

```txt
受信箱
```

左にメニューアイコン、右に縦三点メニューアイコンを配置してください。

2. タブ

```txt
すべて
取引中
お知らせ
```

`すべて` を青色の選択状態にし、下線を表示してください。

3. 受信一覧

静的データで最低5件表示してください。

```txt
山田 花子
取引中
基礎からの線形代数 第2版
こんにちは！購入希望です。まだ購入可能でしょうか？
10:30

佐藤 健太
取引中
ミクロ経済学の基礎
ありがとうございます！では、明日の午後に...
昨日

OU Textbook運営
お知らせ
サービスメンテナンスのお知らせ
いつもOU Textbookをご利用いただき...
2日前

田中 一郎
化学の新研究
コメントありがとうございます。もう少し...
3日前

鈴木 美咲
基礎からの微積分
購入を検討しています。状態について教えて...
5日前
```

各行は以下の構成にしてください。

- 左に丸いアバター
- 中央に名前、タグ、教材名、本文プレビュー
- 右に日時と矢印
- 行と行の間に薄い区切り線

## レイアウト目安

- 最大幅は `430px` 前後。
- 背景は白。
- タブは横3分割。
- 選択中タブは青文字、青下線。
- 名前は太字。
- タグは小さい角丸ラベル。
- 本文プレビューは薄いグレー寄りの文字色。
- footerに重ならないよう下余白を確保してください。

## 注意

この画面ではデータは静的でOKです。チャット詳細への遷移、未読管理、タブ切り替え処理は別タスクで実装します。

## 動作確認

```bash
cd /Users/haruk/prog/pbl
source .venv/bin/activate
cd trading_text
python manage.py runserver
```

確認URL:

```txt
http://127.0.0.1:8000/inbox/
```

## 完了条件

- `/inbox/` で受信箱画面が表示される。
- Tailwind CSSを使っていない。
- `base.html` を継承している。
- `inbox.html` と `inbox.css` に役割が分かれている。
- 既存footerが画面下部に表示される。
- footerの「受信箱」がアクティブに見える。
- スマホ幅で一覧の文字や行がはみ出さない。

## コミットメッセージ例

```bash
git add .
git commit -m "受信箱画面UIを追加"
```
