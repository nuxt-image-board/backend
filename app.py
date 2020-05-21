from flask import Flask
from flask_cors import CORS
from general import (
    app_before_request,
    app_after_request,
    app_teardown_appcontext,
    app_index,
    app_favicon,
    error_unauthorized,
    error_not_found,
    error_ratelimit,
    error_server_bombed
)
from blueprints import (
    accounts_api,
    artists_api,
    arts_api,
    catalog_api,
    characters_api,
    navigations_api,
    search_api,
    tags_api,
    scrape_api,
    news_api,
    invites_api,
    superuser_api,
    apiLimiter
)

'''
ごちイラAPI

<<アカウント>>
POST   /accounts
POST   /accounts/login/form
POST   /accounts/login/line
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

<<イラスト>> 完成! 16:38
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
POST /scrape/twitter
POST /scrape/pixiv
POSt /scrape/upload

<<通報>>
POST /art/ID
POST /tag/ID
POST /user/ID

'''


def createApp():
    app = Flask(__name__)
    # 設定
    app.config['JSON_AS_ASCII'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.config['SECRET_KEY'] = '***REMOVED***'
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
    app.config['ILLUST_FOLDER'] = 'static/illusts'
    app.config['TEMP_FOLDER'] = 'static/temp'
    # 各ページルールを登録
    app.add_url_rule('/', 'index', app_index, strict_slashes=False)
    app.add_url_rule('/favicon.ico', 'favicon.ico', app_favicon)
    app.register_blueprint(accounts_api, url_prefix='/accounts')
    app.register_blueprint(artists_api, url_prefix='/artists')
    app.register_blueprint(arts_api, url_prefix='/arts')
    app.register_blueprint(catalog_api, url_prefix='/catalog')
    app.register_blueprint(characters_api, url_prefix='/characters')
    app.register_blueprint(navigations_api, url_prefix='/navigations')
    app.register_blueprint(search_api, url_prefix='/search')
    app.register_blueprint(tags_api, url_prefix='/tags')
    app.register_blueprint(scrape_api, url_prefix='/scrape')
    app.register_blueprint(news_api, url_prefix='/news')
    app.register_blueprint(invites_api, url_prefix='/invites')
    app.register_blueprint(superuser_api, url_prefix='/superuser')
    # リクエスト共通処理の登録
    app.before_request(app_before_request)
    app.after_request(app_after_request)
    app.teardown_appcontext(app_teardown_appcontext)
    # エラーハンドリングの登録
    app.register_error_handler(401, error_unauthorized)
    app.register_error_handler(404, error_not_found)
    app.register_error_handler(429, error_ratelimit)
    app.register_error_handler(500, error_server_bombed)
    # Flask-Limiterの登録
    apiLimiter.init_app(app)
    # Flask-CORSの登録
    CORS(app)
    return app


app = createApp()

if __name__ == '__main__':
    app.debug = True
    app.run(host="localhost")
