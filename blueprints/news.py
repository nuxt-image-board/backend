from flask import Flask, g, request, jsonify, escape, Blueprint
from .authorizator import auth, token_serializer
from .limiter import apiLimiter, handleApiPermission
from .recorder import recordApiRequest
from .cache import apiCache

news_api = Blueprint('news_api', __name__)


@news_api.route('/', methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addNews(newsID):
    if g.userPermission != 9:
        return jsonify(status=400, message="Bad request")
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "color" not in params.keys()\
            or "title" not in params.keys()\
            or "body" not in params.keys():
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        params = {p: g.validate(params[p]) for p in params.keys()}
    except:
        return jsonify(status=400, message="Request parameter is invalid.")
    if g.userPermission != 9:
        return jsonify(status=401, message="You don't have permission")
    resp = g.db.edit(
        "INSERT INTO data_user (newsColor,newsTitle, newsBody) VALUES (%s,%s,%s)",
        (params["color"], params["title"], params["body"])
    )
    if resp:
        createdID = g.db.get(
            "SELECT MAX(newsID) FROM data_news"
        )[0][0]
        recordApiRequest(g.userID, "addNews", param1=createdID)
        return jsonify(status=201, message="Created", artistID=createdID)
    else:
        return jsonify(status=500, message="Server bombed.")


@news_api.route('/<int:newsID>', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def deleteNews(newsID):
    if g.userPermission != 9:
        return jsonify(status=401, message="You don't have permission")
    resp = g.db.edit(
        "DELETE FROM data_news WHERE newsID=%s",
        (newsID,)
    )
    if resp:
        recordApiRequest(g.userID, "removeNews", param1=newsID)
        return jsonify(status=200, message="Delete succeed.")
    else:
        return jsonify(status=500, message="Server bombed.")


@news_api.route('/list', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
@apiCache.cached(timeout=1800, query_string=True)
def listNews():
    maxNews = request.args.get('count', default=50, type=int)
    datas = g.db.get(
        "SELECT * FROM data_news ORDER BY newsID DESC LIMIT %s", (maxNews,))
    ls = [{"id": d[0], "date":d[1].strftime(
        '%Y-%m-%d %H:%M:%S'), "color":d[2], "title":d[3], "body":d[4][:30]} for d in datas]
    return jsonify(status=200, data=ls)


@news_api.route('/<int:newsID>', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
@apiCache.cached(timeout=1800)
def getNews(newsID):
    resp = g.db.get(
        "SELECT * FROM data_news WHERE newsID=%s",
        (newsID,)
    )
    if not len(resp):
        return jsonify(status=404, message="The news was not found")
    resp = resp[0]
    return jsonify(status=200, data={"id": resp[0], "date": resp[1].strftime('%Y-%m-%d %H:%M:%S'), "color": resp[2], "title": resp[3], "body": resp[4]})
