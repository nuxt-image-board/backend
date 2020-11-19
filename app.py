from flask import Flask
from flask_cors import CORS
from api.blueprints.general import (
    app_before_request,
    app_after_request,
    app_teardown_appcontext,
    app_index, app_favicon,
    error_unauthorized,
    error_not_found,
    error_ratelimit,
    error_server_bombed
)
from api.blueprints import (
    accounts_api, artists_api, arts_api,
    catalog_api, characters_api, navigations_api,
    search_api, tags_api, scrape_api,
    news_api, notify_api, invites_api,
    superuser_api, mylist_api, toymoney_api,
    wiki_api, mute_api, uploaders_api,
    ranking_api
)
from api.extensions import (
    limiter, cache
)
from dotenv import load_dotenv
from os import environ


# .env読み込み
load_dotenv(verbose=True, override=True)


def createApp():
    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
    app.config['ILLUST_FOLDER'] = 'static/illusts'
    app.config['TEMP_FOLDER'] = 'static/temp'
    app.config['onesignalAppId'] = environ.get('API_ONESIGNAL_APPID')
    app.config['onesignalToken'] = environ.get('API_ONESIGNAL_TOKEN')
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
    app.register_blueprint(notify_api, url_prefix='/notify')
    app.register_blueprint(invites_api, url_prefix='/invites')
    app.register_blueprint(superuser_api, url_prefix='/superuser')
    app.register_blueprint(mylist_api, url_prefix='/mylist')
    app.register_blueprint(toymoney_api, url_prefix='/toymoney')
    app.register_blueprint(wiki_api, url_prefix='/wiki')
    app.register_blueprint(mute_api, url_prefix='/mute')
    app.register_blueprint(uploaders_api, url_prefix='/uploaders')
    app.register_blueprint(ranking_api, url_prefix='/ranking')
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
    limiter.init_app(app)
    # Flask-Cacheの登録
    cache.init_app(app)
    # Flask-CORSの登録 (CORSは7日間キャッシュする)
    CORS(
        app,
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        origins=environ.get('API_CORS').split(','),
        max_age=604800
    )
    return app


app = createApp()

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
