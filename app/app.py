from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import sqlite3
import re
import hashlib
import secrets
import csv
import io
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.permanent_session_lifetime = timedelta(minutes=1)

DATABASE_PATH = 'data/survey.db'

# データベース初期化（テーブル存在チェック付き）
def ensure_db_exists():
  try:
    import os
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # テーブルが存在するかチェック
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='surveys'")
    if not cursor.fetchone():
      # surveysテーブルが存在しない場合は作成
      cursor.execute('''
        CREATE TABLE surveys (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name VARCHAR(256) NOT NULL,
          email VARCHAR(256) NOT NULL UNIQUE,
          age INTEGER NOT NULL,
          languages TEXT,
          pc_type VARCHAR(50) NOT NULL,
          pc_maker VARCHAR(50) NOT NULL,
          comment TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      ''')
      print("surveys table created")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admins'")
    if not cursor.fetchone():
      # adminsテーブルが存在しない場合は作成
      cursor.execute('''
        CREATE TABLE admins (
          username VARCHAR(256) NOT NULL PRIMARY KEY,
          password VARCHAR(256) NOT NULL
        )
      ''')
      print("admins table created")
    
    conn.commit()
    conn.close()
    return True
  except Exception as e:
    print(f"Error ensuring database exists: {e}")
    return False

# パスワード検証
def validate_password(password):
  if len(password) < 8 or len(password) > 32:
    return False
  
  has_upper = bool(re.search(r'[A-Z]', password))
  has_lower = bool(re.search(r'[a-z]', password))
  has_digit = bool(re.search(r'[0-9]', password))
  has_symbol = bool(re.search(r'[!"#$%&\'()*+,\-./:;<=>?@\[\]^_`{|}~]', password))
  
  return has_upper and has_lower and has_digit and has_symbol

# メールアドレス検証
def validate_email(email):
  # type="email"の基本的なチェック
  email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
  if not re.match(email_pattern, email):
    return False
  
  # @以降に1つ以上の.があるかチェック
  domain = email.split('@')[1] if '@' in email else ''
  if '.' not in domain:
    return False
    
  return True

# パスワードハッシュ化
def hash_password(password):
  salt = secrets.token_hex(16)
  password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
  return salt + password_hash

def verify_password(password, stored_hash):
  salt = stored_hash[:32]
  stored_password_hash = stored_hash[32:]
  password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
  return password_hash == stored_password_hash

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

@app.route('/')
def index():
  return render_template('survey_form.html')

@app.route('/submit', methods=['POST'])
def submit_survey():
  # データベースが存在することを確認
  if not ensure_db_exists():
    flash('システムエラーが発生しました。しばらく待ってから再度お試しください。')
    return render_template('survey_form.html')
  
  # フォームデータ取得
  name = request.form.get('name', '').strip()
  email = request.form.get('email', '').strip()
  age = request.form.get('age', '').strip()
  languages = request.form.getlist('languages')
  pc_type = request.form.get('pc_type', '')
  pc_maker = request.form.get('pc_maker', '')
  comment = request.form.get('comment', '')
  
  # バリデーション
  errors = []
  
  if not name:
    errors.append('名前を入力してください。')
  
  if not email:
    errors.append('メールアドレスを入力してください。')
  elif not validate_email(email):
    errors.append('正しいメールアドレスを入力してください。')
  else:
    # メールアドレス重複チェック
    try:
      conn = sqlite3.connect(DATABASE_PATH)
      cursor = conn.cursor()
      cursor.execute('SELECT id FROM surveys WHERE email = ?', (email,))
      if cursor.fetchone():
        errors.append('すでにこのメールアドレスで回答済みです。')
      conn.close()
    except Exception as e:
      print(f"Error checking email: {e}")
      errors.append('システムエラーが発生しました。')
  
  if not age:
    errors.append('年齢を入力してください。')
  else:
    try:
      age_int = int(age)
      if age_int < 18 or age_int > 110:
        errors.append('年齢は18才以上110才以下で入力してください。')
    except ValueError:
      errors.append('年齢は数字で入力してください。')
  
  if not pc_type:
    errors.append('学習に使っているパソコンを選択してください。')
  
  if not pc_maker or pc_maker == '選択してください':
    pc_maker = 'その他'
  
  # エラーがある場合は入力画面に戻る
  if errors:
    for error in errors:
      flash(error)
    return render_template('survey_form.html', 
                         name=name, email=email, age=age, 
                         languages=languages, pc_type=pc_type, 
                         pc_maker=pc_maker, comment=comment)
  
  # データベースに保存
  languages_str = '|'.join(languages) if languages else ''
  
  try:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
      INSERT INTO surveys (name, email, age, languages, pc_type, pc_maker, comment)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, email, int(age), languages_str, pc_type, pc_maker, comment))
    conn.commit()
    conn.close()
    
    return render_template('survey_complete.html', 
                         name=name, email=email, age=age,
                         languages=languages_str, pc_type=pc_type,
                         pc_maker=pc_maker, comment=comment)
  except Exception as e:
    print(f"Error saving survey: {e}")
    flash('データの保存中にエラーが発生しました。しばらく待ってから再度お試しください。')
    return render_template('survey_form.html', 
                         name=name, email=email, age=age, 
                         languages=languages, pc_type=pc_type, 
                         pc_maker=pc_maker, comment=comment)

@app.route('/admin/')
def admin_index():
  if not check_admin_login():
    return redirect(url_for('admin_login'))
  
  # データベースが存在することを確認
  ensure_db_exists()
  
  # アンケート一覧を取得
  try:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
      SELECT id, created_at, name, email, age, languages, pc_type, pc_maker, comment
      FROM surveys ORDER BY created_at DESC
    ''')
    surveys = cursor.fetchall()
    conn.close()
  except Exception as e:
    print(f"Error fetching surveys: {e}")
    surveys = []
  
  return render_template('admin_dashboard.html', surveys=surveys)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
  if request.method == 'POST':
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
      flash('このフィールドを入力してください。')
      return render_template('admin_login.html', admin_exists=True)
    
    try:
      conn = sqlite3.connect(DATABASE_PATH)
      cursor = conn.cursor()
      cursor.execute('SELECT password FROM admins WHERE username = ?', (username,))
      result = cursor.fetchone()
      conn.close()
      
      if result and verify_password(password, result[0]):
        session['admin_username'] = username
        session['last_activity'] = datetime.now().isoformat()
        session.permanent = True
        return redirect(url_for('admin_index'))
      else:
        flash('管理者名またはパスワードが間違っています。')
    except Exception as e:
      flash('データベースエラーが発生しました。')
      print(f"Database error: {e}")
  
  # 管理者が登録済みかチェック
  admin_exists = False
  try:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM admins')
    admin_exists = cursor.fetchone()[0] > 0
    conn.close()
  except Exception as e:
    print(f"Database error checking admin existence: {e}")
    admin_exists = False
  
  return render_template('admin_login.html', admin_exists=admin_exists)

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
  # 既に管理者が存在するかチェック
  conn = sqlite3.connect(DATABASE_PATH)
  cursor = conn.cursor()
  cursor.execute('SELECT COUNT(*) FROM admins')
  admin_count = cursor.fetchone()[0]
  conn.close()
  
  if admin_count > 0:
    flash('管理者はすでに登録済みです。')
    return redirect(url_for('admin_login'))
  
  if request.method == 'POST':
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
      flash('このフィールドを入力してください。')
      return render_template('admin_register.html')
    
    if not validate_password(password):
      flash('パスワードは8-32文字で大文字英字・小文字英字・数字・記号をそれぞれ1文字以上含む必要があります。')
      return render_template('admin_register.html')
    
    password_hash = hash_password(password)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO admins (username, password) VALUES (?, ?)', 
                   (username, password_hash))
    conn.commit()
    conn.close()
    
    session['admin_username'] = username
    session['last_activity'] = datetime.now().isoformat()
    session.permanent = True
    return redirect(url_for('admin_index'))
  
  return render_template('admin_register.html')

@app.route('/admin/delete_survey/<int:survey_id>')
def delete_survey(survey_id):
  if not check_admin_login():
    return redirect(url_for('admin_login'))
  
  conn = sqlite3.connect(DATABASE_PATH)
  cursor = conn.cursor()
  cursor.execute('DELETE FROM surveys WHERE id = ?', (survey_id,))
  conn.commit()
  conn.close()
  
  return redirect(url_for('admin_index'))

@app.route('/admin/delete_all')
def delete_all_surveys():
  if not check_admin_login():
    return redirect(url_for('admin_login'))
  
  conn = sqlite3.connect(DATABASE_PATH)
  cursor = conn.cursor()
  cursor.execute('DELETE FROM surveys')
  conn.commit()
  conn.close()
  
  return redirect(url_for('admin_index'))

@app.route('/admin/download')
def download_csv():
  if not check_admin_login():
    return redirect(url_for('admin_login'))
  
  # データベースが存在することを確認
  ensure_db_exists()
  
  try:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
      SELECT created_at, name, email, age, languages, pc_type, pc_maker, comment
      FROM surveys ORDER BY created_at DESC
    ''')
    surveys = cursor.fetchall()
    conn.close()
  except Exception as e:
    print(f"Error fetching surveys for CSV: {e}")
    surveys = []
  
  # CSVファイル生成（UTF-8 BOM付き）
  output = io.StringIO()
  writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
  
  # ヘッダー
  writer.writerow(['回答日時', '名前', 'メールアドレス', '年齢', 
                   '興味のあるプログラミング言語', '学習に使っているパソコン', 
                   'パソコンメーカー', 'コメント'])
  
  # データ行
  for survey in surveys:
    created_at, name, email, age, languages, pc_type, pc_maker, comment = survey
    
    # 複数行のコメントは改行を保持
    if comment and '\n' in comment:
      comment = f'"{comment}"'
    elif comment:
      # 単一行でもカンマが含まれる場合はクォート
      if ',' in comment:
        comment = f'"{comment}"'
    
    writer.writerow([created_at, name, email, age, languages or '', pc_type, pc_maker, comment or ''])
  
  output.seek(0)
  csv_content = output.getvalue()
  output.close()
  
  # UTF-8 BOMを追加してExcelでの文字化けを防ぐ
  csv_content_with_bom = '\ufeff' + csv_content
  
  return Response(
    csv_content_with_bom.encode('utf-8'),
    mimetype='text/csv; charset=utf-8',
    headers={
      'Content-Disposition': 'attachment; filename=survey_results.csv',
      'Content-Type': 'text/csv; charset=utf-8'
    }
  )

@app.route('/admin/logout')
def admin_logout():
  if 'admin_username' in session:
    username = session['admin_username']
    session.clear()
    flash(f'{username} - ログアウトしました。')
  return render_template('admin_logout.html')

@app.route('/admin/delete_user')
def delete_admin_user():
  if not check_admin_login():
    return redirect(url_for('admin_login'))
  
  username = session['admin_username']
  
  conn = sqlite3.connect(DATABASE_PATH)
  cursor = conn.cursor()
  cursor.execute('DELETE FROM admins WHERE username = ?', (username,))
  conn.commit()
  conn.close()
  
  session.clear()
  flash(f'{username}の管理者登録を解除しました。')
  return render_template('admin_logout.html')

if __name__ == '__main__':
  # 明示的にデータベースを初期化
  ensure_db_exists()
  app.run(debug=True)