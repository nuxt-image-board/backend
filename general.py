from flask import g, jsonify, current_app
from db import SQLHandler
from os import environ
from dotenv import load_dotenv
import html

'''
　Flaskのデフォルトですることなどの登録用
　　- リクエストを受け取ったときの処理
　　- リクエストを返すときの処理
　　- アプリを閉じるときの処理
　　- エラーハンドリング
　　- index
'''

# .env読み込み
load_dotenv(verbose=True, override=True)
DB_NAME = environ.get("DB_NAME")
DB_HOST = environ.get("DB_HOST")
DB_PORT = environ.get("PORT_DB")
DB_USER = environ.get("DB_USER")
DB_PASS = environ.get("DB_PASS")


def validateRequestData(text, lengthMin=1, lengthMax=500, escape=True):
    '''投稿されるデータを検証して弾く'''
    ng_words = [
        "{",
        "}",
        "[",
        "]",
        "request",
        "config",
        "<script>",
        "</script>",
        "class",
        "import",
        "__globals__",
        "__getitem__",
        "self"
    ]
    for ng in ng_words:
        text = text.replace(ng, "")
    text = text[:lengthMax]
    if text == "" or len(text) < lengthMin:
        return ""
    if escape:
        return html.escape(text)
    return text


# リクエストが来るたびにデータベースにつなぐ　TODO: MySQLに変更
def app_before_request():
    g.db = SQLHandler(
        DB_NAME,
        DB_HOST,
        DB_PORT,
        DB_USER,
        DB_PASS
    )
    if not hasattr(g, 'validate'):
        g.validate = validateRequestData
    g.userPermission = None


# リクエストの処理が完成するたびにヘッダーにセキュリティ上のあれをつける
def app_after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['X-Download-Options'] = 'noopen'
    # response.headers['Content-Security-Policy'] = 'default-src \'self\' ***REMOVED***'
    g.db.close()
    return response


# アプリ終了時にデータベースを閉じる　TODO: MySQLに変更
def app_teardown_appcontext(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        g.db.close()


# 認証失敗時のエラー
def error_unauthorized(e):
    return jsonify(status=401, message="Authorization failed")


# 存在しない場合のエラー
def error_not_found(e):
    return jsonify(status=404, message="Not found")


# レート制限を超えたときのエラー
def error_ratelimit(e):
    return jsonify(status=429, message=f"Ratelimit exceeded {e.description}")


# 処理に失敗した場合のエラー
def error_server_bombed(e):
    return jsonify(status=500, message="Server expoded")


# デフォルト
def app_index():
    return jsonify(status=200, message="Server is running")


# デフォルト
def app_favicon():
    return current_app.send_static_file('favicon.ico')
