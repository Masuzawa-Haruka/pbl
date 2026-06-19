# pbl-ui8 マイページ画面 実装指示書

## 担当
山下さん

## 担当ブランチ

```bash
git switch -c feature/mypage-screen-ui
```

## 作業手順

1. ブランチを切る

```bash
git switch main
git pull --rebase origin main
git switch -c feature/mypage-screen-ui
```

2. 作業を始めるたびにpullする

```bash
git switch feature/mypage-screen-ui
git pull --rebase origin main
```

3. HTML, CSSファイルを作成する
4. できたらcommit, pushする
5. GitHubでPRを作成する

## 参考画像

```txt
ui/mypage-screen.png
```

画面内容は「ユーザーのマイページ」です。

## 実装ルール

- Tailwind CSSは使用禁止です。
- HTMLはDjangoテンプレートで実装してください。
- CSSは通常のCSSファイルに分けて書いてください。
- 既存の `base.html` を継承してください。
- 共通footerは既存の `components/footer.html` を使ってください。
- 画像をそのまま貼るのは禁止です。HTML/CSSで再現してください。

## 作成・編集するファイル

### 1. マイページテンプレート

作成ファイル:

```txt
trading_text/main/templates/main/mypage.html
```

テンプレート例:

```django
{% extends 'main/base.html' %}
{% load static %}

{% block title %}マイページ | OU Textbook{% endblock %}

{% block extra_style %}
<link rel="stylesheet" href="{% static 'main/css/mypage.css' %}">
{% endblock %}

{% block header_title %}マイページ{% endblock %}

{% block content %}
<!-- ここにマイページを実装 -->
{% endblock %}
```

### 2. マイページCSS

作成ファイル:

```txt
trading_text/main/static/main/css/mypage.css
```

### 3. viewの追加

編集ファイル:

```txt
trading_text/main/views.py
```

追加するview:

```python
def mypage(request):
    return render(request, 'main/mypage.html')
```

### 4. URLの追加

編集ファイル:

```txt
trading_text/main/urls.py
```

追加するURL:

```python
path('mypage/', views.mypage, name='mypage'),
```

## 画面仕様

### 表示要素

上から順番に配置してください。

1. ヘッダー

```txt
マイページ
```

右上に設定アイコンを配置してください。

2. プロフィールエリア

```txt
大阪 太郎
大阪大学 学生
工学部　電子情報工学科　2年
プロフィール編集
```

左に丸いアバターを表示してください。仮の人物アイコンをCSSまたはSVGで作ってOKです。

3. 実績カード

3列で表示してください。

```txt
出品数
3 点

取引完了数
2 件

評価
4.8 / 5.0
★★★★★
```

4. メニューリスト

以下を縦並びで表示してください。

```txt
出品した商品
お気に入り
メッセージ
取引履歴
評価一覧
お知らせ
ヘルプ・お問い合わせ
利用規約
ログアウト
```

各行は左にアイコン、右に矢印を置いてください。お知らせには赤いバッジ `1` を表示してください。

5. 出品中の商品

見出し:

```txt
出品中の商品
すべて見る
```

商品カードを3件表示してください。

```txt
基礎からの線形代数
1,000円
いいね 3
出品中

ミクロ経済学の基礎
800円
いいね 2
出品中

化学の新研究
700円
いいね 1
出品中
```

## レイアウト目安

- 最大幅は `430px` 前後。
- 画面背景は薄いグレー寄りの白。
- カードは白背景、薄い枠線、角丸。
- メニューリストは1つの白いカードにまとめる。
- 価格は赤。
- 出品中ラベルは薄い緑背景。
- footerに重ならないよう下余白を確保してください。

## 注意

この画面ではデータは静的でOKです。DB連携は別タスクで実装します。

## 動作確認

```bash
cd /Users/haruk/prog/pbl
source .venv/bin/activate
cd trading_text
python manage.py runserver
```

確認URL:

```txt
http://127.0.0.1:8000/mypage/
```

## 完了条件

- `/mypage/` でマイページが表示される。
- Tailwind CSSを使っていない。
- `base.html` を継承している。
- `mypage.html` と `mypage.css` に役割が分かれている。
- 既存footerが画面下部に表示される。
- footerの「マイページ」がアクティブに見える。
- スマホ幅でカードやメニューがはみ出さない。

## コミットメッセージ例

```bash
git add .
git commit -m "マイページ画面UIを追加"
```
