from flask import Flask, request, render_template, session, abort, redirect, url_for, flash, jsonify 
#Flaskデフォルトのsessionで、クライアントのhttpリクエスト時に、 未ログインならブラウザからのクッキーをもとに空のsessionが、ログイン済ならブラウザからのクッキーをもとにuser_idが入ったsessionがサーバーに作られる。
import sqlite3 #データベース操作用モジュール
import secrets #Pythonで安全な乱数を生成するモジュール
from werkzeug.security import generate_password_hash, check_password_hash #パスワードの安全なハッシュ化と検証のためのモジュール ヴェルクツォイク

#ルートディレクトリにappを設定
app = Flask(__name__)

# クライアントに送るセッションクッキーの署名作成用秘密鍵を安全に生成・設定 (1バイト=16進数2桁なので、32バイト=64桁の16進数を生成)
app.secret_key = secrets.token_hex(32)



#データベース初期化(アプリ起動時)
def init_db():
	#calendar.dbの名前でDBファイル自動生成・接続(同名DBが既存なら接続のみ)
	with sqlite3.connect("calendar.db") as connect: 
		#SQLiteの外部キーを有効化(デフォルトは無効のため、eventsテーブル編集時は常にON)
		connect.execute("PRAGMA foreign_keys = ON") 
		
		c = connect.cursor()

		#ログイン情報管理テーブル users
		c.execute("""
			CREATE TABLE IF NOT EXISTS users (
				user_id TEXT PRIMARY KEY,
				password_hash TEXT NOT NULL
		)
		""")

		# スケジュール管理テーブル events
			# なお、user_idは外部キーとして親テーブルusersのuser_idと紐づけることで未登録ユーザーの予定追加を弾く
		c.execute("""
			CREATE TABLE IF NOT EXISTS events (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				user_id TEXT NOT NULL,
				schedule_title TEXT NOT NULL,
				schedule_datetime TEXT NOT NULL,
				FOREIGN KEY (user_id) REFERENCES users(user_id)
			)
		""")

# アプリ起動時にDB初期化実行
init_db()



#以下、ブラウザ表示用ページ-------------------------------------------------------------------------
# ホームページ (ブラウザのクッキーにuser_idがなければログインページへ遷移・あればホームページ表示)
@app.route("/")
def home_page():
	if "user_id" not in session: #既にサーバーにはsessionが作られている
		return redirect(url_for("login_page"))
	return render_template("index.html")



# ログインページ (ブラウザのクッキーにuser_idがあればトップページ遷移・なければログインページ表示)
@app.route("/login")
def login_page():
	if "user_id" in session:
		return redirect(url_for("home_page"))
	return render_template("login.html")



# 新規登録ページ (ログインページと同じガード節)
@app.route("/register")
def register_page():
	if "user_id" in session:
		return redirect(url_for("home_page"))
	return render_template("register.html")



#以下、通信用ページ-------------------------------------------------------------------------
# 新規登録処理 (HTMLのform形式・不適切な登録とID被りはガード節で除去)
@app.route("/action/register", methods = ["POST"])
def action_register():
	#form受信
	user_id = request.form.get("user_id", "").strip() #HTMLformからのテキストの前後の空白を除去・user_idが無ければ空文字
	password = request.form.get("password", "").strip() #同上

	#ユーザーIDかパスワード両方もしくはどちらかが無いか空入力ならフラッシュメッセージ&新規登録ページに戻る
	if not user_id or not password:
		flash("IDとパスワードを正しく入力してください。", "error") #errorはフラッシュメッセージのカテゴリ名
		return redirect(url_for("register_page"))

	#ユーザーIDとパスワードの長さ制限
	if(len(user_id) > 50) or (len(password) > 50):
		flash("IDとパスワードは50文字以内で入力してください。", "error")
		return redirect(url_for("register_page"))

	with sqlite3.connect("calendar.db") as connect:
		c = connect.cursor()

		# 既存のユーザーIDと重複しないかチェック(なお、SQLインジェクション対策としてプレースホルダ?にPythonのタプル型を渡す)
		c.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) #form送信されたuser_idの値が、user_id列にあれば1をSQLite内部バッファに返す
		existing_user = c.fetchone() #fetchoneでタプル型の1かNoneを変数に返す
		
		# 重複があればDB接続を閉じ、フラッシュメッセージ&新規登録ページに遷移(戻る)
		if existing_user:
			flash("このIDは既に別ユーザーに使用されています。違うIDを入力してください。", "error") 
			return redirect(url_for("register_page"))

		# パスワードを安全にハッシュ化
		password_hash = generate_password_hash(password)

		# データベースに挿入・保存・DB接続閉じる
		c.execute("INSERT INTO users (user_id, password_hash) VALUES (?, ?)", (user_id, password_hash))

	# 登録成功時はDB接続を閉じ、フラッシュメッセージ表示・ログイン画面へ遷移
	flash("アカウント登録が完了しました！ログインしてください。", "success")
	return redirect(url_for("login_page"))



# ログイン処理 HTMLのform形式・今度はログイン情報一致をガード節で除去
@app.route("/action/login", methods = ["POST"])
def action_login():
	user_id = request.form.get("user_id", "").strip() #これをセッションクッキーの値にする
	password = request.form.get("password", "").strip()

	if not user_id or not password:
		flash("IDとパスワードを正しく入力してください。", "error")
		return redirect(url_for("login_page"))
	
	if(len(user_id) > 50) or (len(password) > 50):
		flash("IDとパスワードは50文字以内で入力してください。", "error")
		return redirect(url_for("login_page"))

	with sqlite3.connect("calendar.db") as connect:
		c = connect.cursor()

		#usersテーブル内を検索し、一致するuser_id行のpassword_hash(タプル型)をrowに代入・DB接続閉じる
		c.execute("SELECT password_hash FROM users WHERE user_id = ?", (user_id,))
		row = c.fetchone()

		# 一致するuser_idが存在し、かつそのuser_id行のpassword_hashも一致するか検証・セッションID設定
			#最初のrowはタプル型インスタンスで、row[0]がpassword_hashの値を表す。
			#最初のrowをrow[0]と書かないのは、一致するpassword_hashが無かった時に、Noneからrow[0]のナンバーのデータを取り出そうとしてエラーになるため。
		if (row and check_password_hash(row[0], password)):#Pythonには短絡処理があるので条件反転してorでも可(ド・モルガンの法則)
			#ログイン状態キープのため、サーバーのsessionにuser_idを代入し、それをもとにsecret_keyを使って作ったセッションクッキーを、直後のレスポンス時にブラウザに送る
			session["user_id"] = user_id
			return redirect(url_for("home_page"))

	# 上記IF文がFalseならDB接続を閉じ、フラッシュメッセージ&ログインページに戻す
	flash("IDまたはパスワードが間違っています。", "error")
	return redirect(url_for("login_page"))



# ログアウト処理（ページの状態遷移なのでPOST）
@app.route("/logout", methods = ["POST"])
def action_logout():
	#popでサーバーのsessionからuser_id削除をリクエスト・無ければNoneでエラー回避
	session.pop("user_id", None)
	flash("ログアウトしました。", "success")
	return redirect(url_for("login_page")) #このレスポンスでブラウザのクッキー削除



# 予定追加API（ホームページ用）
@app.route("/add_event", methods = ["POST"])
def action_add_event():
	if "user_id" not in session: #ログイン中のユーザー以外予定追加不可
		abort(401) #不正アクセスのステータスコード=401

	data = request.get_json()
	
	#このガード節で直後のdata.get()で、Noneをget()するエラーを防ぐ
	if not data:
		return jsonify({"status":"error", "message": "入力データがありません"})
	
	#Noneなら空文字を返し、前後の空白を除去
	schedule_title = data.get("schedule_title", "").strip()
	schedule_datetime = data.get("schedule_datetime", "").strip()

	#どちらかがなければエラー返す
	if not schedule_title or not schedule_datetime: 
		return jsonify({"status": "error", "message": "予定の名前と日時の両方を入力してください"})
	
	if (len(schedule_title) > 100) or (len(schedule_datetime) > 100):
		return jsonify({"status": "error", "message": "入力は100文字以内でお願いします"})

	with sqlite3.connect("calendar.db") as connect:
		#eventsテーブルを編集するので外部キーを有効化 (これを忘れると、未登録ユーザーの予定追加ができてしまう)
		connect.execute("PRAGMA foreign_keys = ON") 
		c = connect.cursor()
		c.execute("INSERT INTO events (user_id, schedule_title, schedule_datetime) VALUES (?, ?, ?)", (session["user_id"], schedule_title, schedule_datetime))
	return jsonify({"status": "ok"}) #このJSON型文字列をJavaScriptで受け取る



# 予定取得API（ホームページ用）
@app.route("/get_events", methods = ["GET"])
def action_get_events():
	if "user_id" not in session:
		abort(401)

	with sqlite3.connect("calendar.db") as connect:
		c = connect.cursor()

		#idは予定の確実な識別用・予定の日時昇順に並べるためORDER BY schedule_datetimeを指定
		c.execute("SELECT id, schedule_title, schedule_datetime FROM events WHERE user_id = ? ORDER BY schedule_datetime", (session["user_id"],))
		rows = c.fetchall() #ユーザーの予定が複数あっても全てタプル型で返す
		if not rows:
			return jsonify([("なし", "", "予定がありません")]) #予定がない場合は空のリストをJSON形式で返す
	return jsonify(rows) #JSON形式で予定をブラウザに返す



# 予定削除API（ホームページ用）
@app.route("/delete_event", methods = ["POST"])
def action_delete_event():
	if "user_id" not in session:
		abort(401)
	
	data = request.get_json()
	if not data:
		return jsonify({"status": "error", "message": "入力データがありません"})
	
	delete_id = data.get("delete_id").strip() #Noneなら空文字を返し、前後の空白を除去
	if not delete_id:
		return jsonify({"status": "error", "message": "削除する予定のID番号を正しく入力してください"})
	
	#ID番号は整数であるべきなので、整数に変換し、エラーをexceptで処理
	try:
		delete_id = int(delete_id)

	#整数型に変換できない入力があった場合のエラー処理
	except (TypeError, ValueError):
		return jsonify({"status": "error", "message": "無効なID番号です"})

	#ID番号は正の整数であるべきなので、0以下の数値を弾く
	if delete_id <= 0:
		return jsonify({"status": "error", "message": "正の整数のID番号を入力してください"})
	
	#ID番号の上限
	if delete_id > 99999: 
		return jsonify({"status": "error", "message": "ID番号上限エラー"})
	
	with sqlite3.connect("calendar.db") as connect:
		c = connect.cursor()
		#ユーザーの予定DBの中から、user_idと削除する予定IDが一致する行を検索して削除
		c.execute("DELETE FROM events WHERE user_id = ? AND id = ?", (session["user_id"], delete_id))
		
	return jsonify({"status": "ok"})