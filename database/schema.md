# データベース（DB）設計

教科書売買アプリ（Trading Text）のデータベース設計です。

## ER図

```mermaid
erDiagram
    USER ||--o{ BOOK : "出品する (seller)"
    USER ||--o{ MESSAGE : "送信する / 受信する"
    USER ||--o{ FAVORITE : "いいねする"
    BOOK ||--o{ MESSAGE : "この本に関する取引"
    BOOK ||--o{ FAVORITE : "いいねされる"

    USER {
        int id PK
        string username "ユーザー名"
        string email "メールアドレス"
        string password "パスワード"
    }

    BOOK {
        int id PK
        int seller_id FK "出品者(USER)"
        string title "タイトル"
        string author "著者"
        int price "価格"
        string category "カテゴリー"
        string campus "キャンパス"
        string condition "状態"
        string description "説明文"
        string status "販売状況(出品中/取引中/売却済)"
        datetime created_at "出品日時"
    }

    MESSAGE {
        int id PK
        int book_id FK "対象の教科書(BOOK)"
        int sender_id FK "送信者(USER)"
        int receiver_id FK "受信者(USER)"
        text content "メッセージ内容"
        datetime created_at "送信日時"
    }

    FAVORITE {
        int id PK
        int user_id FK "いいねしたユーザー(USER)"
        int book_id FK "いいねされた本(BOOK)"
        datetime created_at "いいねした日時"
    }
```

## テーブル詳細

### 1. `User` テーブル（Django標準 `auth.User`）
ユーザー情報を管理する。Djangoの標準機能を使用。
- `id` (Primary Key)
- `username`
- `email`
- `password`

### 2. `Book` テーブル
出品された教科書データを管理する。
- `seller` (ForeignKey to User): 誰が出品したか。
- `status` (CharField): 「出品中(available)」「取引中(in_progress)」「売却済み(sold)」。

### 3. `Message` テーブル
ユーザー同士の取引メッセージ（チャット）を管理する。
- `book` (ForeignKey to Book): どの本の取引か。
- `sender` (ForeignKey to User): 送信者。
- `receiver` (ForeignKey to User): 受信者。
- `content` (TextField): メッセージ本文。
- `created_at` (DateTimeField): 送信日時。

### 4. `Favorite` テーブル
ユーザーの「いいね（お気に入り）」を管理する。
- `user` (ForeignKey to User): いいねした人。
- `book` (ForeignKey to Book): いいねされた本。
- `created_at` (DateTimeField): いいねした日時。
