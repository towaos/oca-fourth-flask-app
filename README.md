# Flask版 アンケートアプリケーション

## 概要
一般ユーザーがアンケートに回答し、管理者がその結果を閲覧・管理するWebアプリケーションです。Python Flask フレームワークを使用して実装されています。

## フォルダ構成

```bash
flask_survey/
├── app.py                    # メインアプリケーション
├── templates/               # HTMLテンプレート
│   ├── survey_form.html     # アンケートフォーム
│   ├── survey_complete.html # 送信完了画面
│   ├── admin_login.html     # 管理者ログイン
│   ├── admin_register.html  # 管理者登録
│   ├── admin_dashboard.html # 管理者ダッシュボード
│   └── admin_logout.html    # ログアウト画面
└── data/
    └── survey.db           # SQLiteデータベース（自動作成）
```

## データベース設計

### surveysテーブル（アンケート回答）
```sql
CREATE TABLE surveys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(256) NOT NULL,                    -- 回答者名
  email VARCHAR(256) NOT NULL UNIQUE,           -- メールアドレス（重複不可）
  age INTEGER NOT NULL,                         -- 年齢（18-110）
  languages TEXT,                               -- 興味のある言語（パイプ区切り）
  pc_type VARCHAR(50) NOT NULL,                 -- パソコンタイプ
  pc_maker VARCHAR(50) NOT NULL,                -- パソコンメーカー
  comment TEXT,                                 -- コメント
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 回答日時
);
```

### adminsテーブル（管理者）
```sql
CREATE TABLE admins (
  username VARCHAR(256) NOT NULL PRIMARY KEY,   -- 管理者名
  password VARCHAR(256) NOT NULL                -- パスワード（ソルト付きハッシュ）
);
```

## 機能仕様

### アンケート機能

#### 入力項目と検証ルール
| 項目 | 入力タイプ | 検証内容 |
|------|-----------|----------|
| 名前 | text | 入力必須 |
| メールアドレス | email | 入力必須、形式検証、@以降に1つ以上の.、重複不可 |
| 年齢 | number | 入力必須、18-110才の範囲 |
| 興味のあるプログラム言語 | checkbox | PHP, JavaScript, Python, Java, C/C++, C#, Ruby（複数選択可） |
| 学習に使っているパソコン | radio | デスクトップPC, ノートPC（デフォルト: デスクトップPC） |
| パソコンメーカー | select | Lenovo, DELL, HP, Apple, Dynabook, NEC, VAIO, ASUS, 自作, その他（デフォルト: その他） |
| コメント | textarea | 任意入力、複数行対応 |

### 管理者機能

#### 管理者認証
- **ログイン**: 管理者名とパスワードによる認証
- **登録**: 初回のみ管理者を1人登録可能
- **セッション管理**: 1分のタイムアウト
- **登録解除**: 管理者の削除機能

#### パスワードポリシー
- 8-32文字の長さ制限
- 大文字英字・小文字英字・数字・記号をそれぞれ1文字以上含む
- 記号はASCIIコード33-126（`!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~`）

#### アンケート管理
- **一覧表示**: 回答日時順でソート表示
- **個別削除**: JavaScript確認ダイアログ付き
- **全削除**: 一括削除機能
- **CSV出力**: UTF-8 BOM付きでExcel対応

### CSV出力仕様

#### ファイル形式
- 文字エンコーディング: UTF-8（BOM付き）
- 区切り文字: カンマ
- 改行コード: CRLF

#### 出力項目
```csv
回答日時,名前,メールアドレス,年齢,興味のあるプログラミング言語,学習に使っているパソコン,パソコンメーカー,コメント
```

#### データ処理
- **複数言語**: パイプ（|）区切りで結合（例: `PHP|JavaScript|Python`）
- **複数行コメント**: ダブルクォートで囲んで改行を保持
- **特殊文字**: 自動エスケープ処理

## セキュリティ対策

### パスワードハッシュ化
```python
def hash_password(password):
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return salt + password_hash

def verify_password(password, stored_hash):
    salt = stored_hash[:32]
    stored_password_hash = stored_hash[32:]
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash == stored_password_hash
```

### SQLインジェクション対策
```python
# プリペアドステートメントの使用
cursor.execute('SELECT id FROM surveys WHERE email = ?', (email,))
cursor.execute('INSERT INTO surveys (name, email, age, languages, pc_type, pc_maker, comment) VALUES (?, ?, ?, ?, ?, ?, ?)', 
               (name, email, age, languages_str, pc_type, pc_maker, comment))
```

### XSS（クロスサイトスクリプティング）対策
```python
# Jinja2の自動エスケープ有効化
app.jinja_env.autoescape = True

# テンプレートでの明示的エスケープ
{{ variable | e }}
{{ variable | tojson }}  # JavaScript用
```

### セッション管理
```python
def check_admin_login():
    if 'admin_username' in session:
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > timedelta(minutes=1):
                session.clear()
                return False
        session['last_activity'] = datetime.now().isoformat()
        return True
    return False
```

## 起動方法

### 前提条件
- Python 3.8以上
- Flask

### セットアップ
```bash
# 依存関係インストール
pip install flask

# アプリケーション起動
python app.py

# ブラウザでアクセス
http://localhost:5000
```

## URL構成
- `/` - アンケートフォーム
- `/submit` - アンケート送信処理（POST）
- `/admin/` - 管理者ダッシュボード  
- `/admin/login` - 管理者ログイン
- `/admin/register` - 管理者登録
- `/admin/download` - CSV ダウンロード
- `/admin/logout` - 管理者ログアウト
- `/admin/delete_user` - 管理者削除

## 動作確認チェックリスト

### 正常系テスト
- [ ] アンケート入力と送信
- [ ] 送信完了画面の表示
- [ ] メールアドレス重複チェック
- [ ] 管理者登録（初回のみ）
- [ ] 管理者ログイン・ログアウト
- [ ] セッションタイムアウト（1分）
- [ ] アンケート一覧表示
- [ ] CSV ダウンロード（日本語文字化けなし）
- [ ] アンケート削除（個別・一括）
- [ ] 管理者登録解除

### 異常系テスト
- [ ] 必須項目未入力エラー
- [ ] メールアドレス形式エラー
- [ ] 年齢範囲外エラー（18-110才）
- [ ] メールアドレス重複エラー
- [ ] 管理者重複登録エラー
- [ ] パスワードポリシー違反エラー
- [ ] 間違ったログイン情報エラー

### セキュリティテスト
```html
<!-- XSS テスト入力例 -->
<script>alert('XSS')</script>
<img src="x" onerror="alert('XSS')">

<!-- SQLインジェクション テスト入力例 -->
'; DROP TABLE surveys; --
0; DELETE FROM surveys
' OR '1'='1
```

## 技術スタック
- **フレームワーク**: Flask 2.0+
- **テンプレートエンジン**: Jinja2
- **データベース**: SQLite 3
- **セッション管理**: Flask標準セッション
- **セキュリティライブラリ**: secrets, hashlib
- **CSVライブラリ**: csv, io

## デプロイメント時の注意事項

### セキュリティ設定
```python
# 本番環境設定
app.run(debug=False)  # デバッグモードを無効化
app.secret_key = secrets.token_hex(32)  # ランダムなシークレットキー

# HTTPS環境での設定
app.permanent_session_lifetime = timedelta(minutes=1)
```

### パフォーマンス
- 大量データ対応時はページネーション実装を検討
- SQLiteの制限を超える場合はPostgreSQL/MySQLへの移行を検討

### バックアップ
- `data/survey.db` ファイルの定期バックアップを実装
- CSV出力機能をバックアップツールとして活用可能

## エラーハンドリング
- データベース接続エラー時の適切なメッセージ表示
- セッションタイムアウト時の自動ログイン画面リダイレクト
- ファイル権限エラー時の対処方法

## 拡張機能の実装案
- メール通知機能
- アンケート項目の動的追加
- 回答データの統計・グラフ表示
- 複数管理者対応
- API機能の追加
