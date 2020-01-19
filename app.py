from flask import Flask, g, request, jsonify, escape, Blueprint
from blueprints import *
from db import SQLHandler
from flask_cors import CORS

'''
ごちイラAPI

TODO:
　各種データを追加したのが誰かをわかるようにすること
　(authorId とかなんかそういうカラムを追加する)

<<アカウント>>
POST   /accounts
POST   /accounts/force_generate_account
GET    /accounts/<int:accountId>
PUT    /accounts/<int:accountId>
DELETE /accounts/<int:accountId>
GET    /accounts/<int:accountId>/apiKey  
GET    /accounts/<int:accountId>/favorites
PUT    /accounts/<int:accountId>/favorites
DELETE /accounts/<int:accountId>/favorites

<<作者>> 完成!
POST   /artists
DELETE /artists/<int:artistId>
GET    /artists/<int:artistId>
PUT    /artists/<int:artistId>

<<イラスト>> 完成!
POST   /arts
DELETE /arts/<int:artId>
GET    /arts/<int:artId>
PUT    /arts/<int:artId>
DELETE /arts/<int:artId>/tags
GET    /arts/<int:artId>/tags
PUT    /arts/<int:artId>/tags
DELETE /arts/<int:artId>/characters
GET    /arts/<int:artId>/characters
PUT    /arts/<int:artId>/characters
PUT    /arts/<int:artId>/stars

<<カタログ/リスト>> 完成!
GET /catalog/tags
GET /catalog/characters
GET /catalog/artists

<<キャラクター>> 完成!
POST   /characters
DELETE /characters/<int:tagId>
GET    /characters/<int:tagId>
PUT    /characters/<int:tagId>

<<ナビゲーションバー>> 完成!
GET /navigations/tags
GET /navigations/artists
GET /navigations/characters

<<検索>> 完成!
GET    /
GET    /tag
GET    /artist
GET    /character
GET    /keyword

<<タグ>> 完成!
POST   /tags
DELETE /tags/<int:tagId>
GET    /tags/<int:tagId>
PUT    /tags/<int:tagId>

<<スクレイピング>>
POST /twitter
POST /pixiv

<<通報>>
POST /art/ID
POST /tag/ID
POST /user/ID

'''


'''
　メインアプリ構成
'''
def createApp():
    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.config['SECRET_KEY'] = '***REMOVED***'
    app.config['UPLOAD_FOLDER'] = 'resources/img'
    app.register_blueprint(accounts_api, url_prefix='/accounts')
    app.register_blueprint(artists_api, url_prefix='/artists')
    app.register_blueprint(arts_api, url_prefix='/arts')
    app.register_blueprint(catalog_api, url_prefix='/catalog')
    app.register_blueprint(characters_api, url_prefix='/characters')
    app.register_blueprint(navigations_api, url_prefix='/navigations')
    app.register_blueprint(search_api, url_prefix='/search')
    app.register_blueprint(tags_api, url_prefix='/tags')
    return app
app = createApp()
CORS(app)

'''
　いろんなとこで使うユーティリティ
'''

def validateRequestData(text, lengthMin=1, lengthMax=500):
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
        text = text.replace(ng,"")
    text = text[:lengthMax]
    if text == "" or len(text) < lengthMin:
        raise ValueError("Text not found")
    return text

# リクエストが来るたびにデータベースにつなぐ　TODO: MySQLに変更
@app.before_request
def start_db_connection():
    g.db = SQLHandler()
    g.validate = validateRequestData
    g.userPermission = None
    return

# リクエストの処理が終わるたびにデータベースを閉じる　TODO: MySQLに変更
@app.teardown_appcontext
def close_db_connection(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

# 認証失敗時のエラー
@app.errorhandler(401)
def unauthorized_handler(e):
    return jsonify(status=401, message="Authorization failed.")

# レート制限を超えたときのエラー
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify(status=429, message="ratelimit exceeded %s" % e.description)

# トップページ
@app.route('/', strict_slashes=False)
@apiLimiter.exempt
def index():
    return jsonify(status=200, message="API server is running.")

if __name__ == '__main__':
    apiLimiter.init_app(app)
    app.run(debug=False)