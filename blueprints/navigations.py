from flask import Blueprint, jsonify, g
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest

navigations_api = Blueprint('navigations_api', __name__)

#　ナビゲーション

@navigations_api.route("/characters",methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def nav_characters():
    datas = g.db.get("SELECT tagName,tagID,COUNT(tagID) as CNT FROM data_tag natural join info_tag GROUP BY tagID HAVING tagType=1 ORDER BY CNT LIMIT 5")
    ls = [{"name":d[0],"id":d[1],"count":d[2]} for d in datas]
    return jsonify(status=200, data=ls)

@navigations_api.route("/artists",methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def nav_artist():
    datas = g.db.get("SELECT artistName,data_illust.artistID,COUNT(data_illust.artistID) FROM info_artist INNER JOIN data_illust ON info_artist.artistID = data_illust.artistID GROUP BY data_illust.artistID ORDER BY COUNT(data_illust.artistID) DESC LIMIT 5")
    ls = [{"name":d[0],"id":d[1],"count":d[2]} for d in datas]
    return jsonify(status=200, data=ls)

@navigations_api.route("/tags",methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def nav_tag():
    datas = g.db.get("SELECT tagName,tagID,COUNT(tagID) as CNT FROM data_tag natural join info_tag GROUP BY tagID HAVING tagType=0 ORDER BY CNT LIMIT 5")
    ls = [{"name":d[0],"id":d[1],"count":d[2]} for d in datas]
    return jsonify(status=200, data=ls)