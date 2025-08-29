# Flask ToDoアプリケーション

## 概要
ユーザーごとにToDoリストを管理するWebアプリケーションです。ユーザー登録・ログイン機能を持ち、各ユーザーが独自のタスクを作成・編集・削除することができます。セキュリティ対策として、パスワードのハッシュ化、セッション管理、XSS・SQLインジェクション対策を実装しています。

## フォルダ構成

```bash
todo-app
├─app
│  ├─app.py            # メインのFlaskアプリケーションファイル
│  ├─static            # 静的ファイル（CSS、JavaScript、画像など）を格納するフォルダ
│  │  └─style.css      # スタイルシート
│  ├─templates         # HTMLテンプレートを格納するフォルダ
│  │  ├─base.html      # ベーステンプレート
│  │  ├─login.html     # ログインページ用のテンプレート
│  │  ├─register.html  # ユーザー登録用のテンプレート
│  │  ├─todo.html      # ToDoメインページ用のテンプレート
│  │  ├─edit_task.html # タスク編集用のテンプレート
│  │  └─logout.html    # ログアウトページ用のテンプレート
│  ├─data              # SQLiteデータベースファイル格納フォルダ
│  ├─Dockerfile        # Dockerコンテナ設定ファイル
│  ├─requirements.txt  # Python依存関係ファイル
│  └─uwsgi.ini         # uWSGI設定ファイル
├─nginx                # Nginxの設定ファイルを格納するフォルダ
│  └─nginx.conf        # Nginx設定ファイル
├─compose.yaml         # Docker Compose設定ファイル
└─README.md
```

## 機能と実装

### データベース設計
- SQLiteを使用してユーザーとタスクデータを管理
- `users`テーブルにユーザー情報（ユーザー名、ハッシュ化パスワード）を保存
- `tasks`テーブルにタスク情報（ID、ユーザー名、タスク内容）を保存
- 外部キー制約によりユーザーとタスクを関連付け

### 実装した機能

#### 1. ユーザー認証システム

##### ユーザー登録（/register）
- フォームからユーザー情報を受け取りデータベースに挿入
- SQL: `INSERT INTO users (username, password) VALUES (?, ?)`
- パスワード強度チェック機能
  - 8-32文字の長さ制限
  - 大文字英字・小文字英字・数字・記号をそれぞれ1文字以上含む
  - 記号はASCIIコード33-126の範囲（!"#$%&'()*+,-./:;<=>?@[]^_`{|}~）
- ユーザー名重複チェック
- パスワードのソルト付きハッシュ化
- 登録完了後自動ログイン

##### ログイン・ログアウト（/login, /logout）
- データベースからユーザー情報を検索・認証
- SQL: `SELECT password FROM users WHERE username = ?`
- セッション管理（有効期限1分）
- アイドルタイムアウト機能
- ログアウト時のセッションクリア

#### 2. ToDoタスク管理

##### メインページ（/）
- ログイン確認とリダイレクト処理
- ユーザー専用のタスク一覧表示
- SQL: `SELECT id, task FROM tasks WHERE username = ?`
- タスク追加フォーム
- 複数行テキスト対応

##### タスク追加（/add_task）
- フォームからタスクデータを受け取りデータベースに挿入
- SQL: `INSERT INTO tasks (username, task) VALUES (?, ?)`
- 入力必須チェック
- ログイン状態確認

##### タスク編集（/edit_task/\<task_id\>, /update_task/\<task_id\>）
- 特定タスクIDのデータを取得してフォームに表示
- SQL: `SELECT id, task FROM tasks WHERE id = ? AND username = ?`
- 編集内容を受け取りデータベースを更新
- SQL: `UPDATE tasks SET task = ? WHERE id = ? AND username = ?`
- ユーザー権限チェック（自分のタスクのみ編集可能）

##### タスク削除（/delete_task/\<task_id\>）
- 特定タスクIDのタスクをデータベースから削除
- SQL: `DELETE FROM tasks WHERE id = ? AND username = ?`
- ユーザー権限チェック（自分のタスクのみ削除可能）

#### 3. ユーザー管理

##### ユーザー登録解除（/delete_user）
- ユーザーに関連する全タスクを削除
- SQL: `DELETE FROM tasks WHERE username = ?`
- ユーザー情報を削除
- SQL: `DELETE FROM users WHERE username = ?`
- セッションクリア

### 技術的な実装ポイント

#### セキュリティ対策

##### パスワードセキュリティ
- ソルト付きハッシュ化による安全な保存
  ```python
  def hash_password(password):
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return salt + password_hash
  ```
- 強力なパスワードポリシーの実装

##### SQLインジェクション対策
- プリペアードステートメント（パラメータ化クエリ）を使用
  ```python
  cursor.execute('INSERT INTO tasks (username, task) VALUES (?, ?)', (username, task))
  ```

##### XSS（クロスサイトスクリプティング）対策
- Jinja2のオートエスケープ機能を有効化
  ```python
  app.jinja_env.autoescape = True
  ```
- HTMLエスケープによる安全な表示

#### セッション管理
- Flask標準のセッション機能を使用
- 1分間のタイムアウト設定
- アイドル時間の自動チェック
  ```python
  def check_login():
    if 'last_activity' in session:
      last_activity = datetime.fromisoformat(session['last_activity'])
      if datetime.now() - last_activity > timedelta(minutes=1):
        session.clear()
        return False
  ```

#### バリデーション機能
- サーバーサイドでの包括的な入力チェック
  ```python
  def validate_password(password):
    if len(password) < 8 or len(password) > 32:
      return False
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    has_symbol = bool(re.search(r'[!"#$%&\'()*+,\-./:;<=>?@\[\]^_`{|}~]', password))
    return has_upper and has_lower and has_digit and has_symbol
  ```
- 重複チェック機能
- エラーメッセージの表示（Flask flash機能使用）

#### ユーザーエクスペリエンス
- 直感的なナビゲーション
- 操作完了後のフィードバックメッセージ
- レスポンシブデザイン対応
- 複数行テキスト対応のタスク入力

#### ルーティング設計
- RESTfulな設計を心がけ、適切なHTTPメソッド（GET/POST）を使用
- リダイレクトによるPRG（Post-Redirect-Get）パターンの実装
- セッション状態に基づく自動リダイレクト

## 起動方法

### 前提条件
- Docker
- Docker Compose

### 手順
1. リポジトリをクローン
2. プロジェクトディレクトリに移動
3. Docker Composeで起動
   ```bash
   docker-compose up --build
   ```
4. ブラウザで `http://localhost:8000` にアクセス

## 動作確認項目

### 正常系テスト
1. ログインしていない状態でのリダイレクト確認
2. ユーザー登録とログイン
3. セッションタイムアウト（1分）の確認
4. タスクの追加・表示
5. タスクの修正・削除
6. ログアウト機能
7. ユーザー登録解除機能

### 異常系テスト
1. 空白フィールドでの送信エラー
2. 間違ったログイン情報でのエラー
3. 重複ユーザー名登録エラー
4. パスワードルール違反エラー
5. XSS・SQLインジェクション対策の確認

## セキュリティ仕様
- パスワードはソルト付きSHA-256ハッシュで保存
- セッションタイムアウト: 1分
- HTMLエスケープによるXSS対策
- プリペアードステートメントによるSQLインジェクション対策
- 強力なパスワードポリシーの実装# oca-fourth-flask-app
