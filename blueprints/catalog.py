from flask import Blueprint, request, g, jsonify
from .authorizator import auth, token_serializer
from .limiter import apiLimiter, handleApiPermission
from .recorder import recordApiRequest

catalog_api = Blueprint('catalog_api', __name__)

#
# 一覧関連
#


@catalog_api.route('/artists', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def listArtists():
    #　ソート : c(ount) もしくは d(ate)
    sortMethod = request.args.get('sort', default="c", type=str)
    if sortMethod == "d":
        sortMethod = "LAST_UPDATE"
    elif sortMethod == "l":
        sortMethod = "LIKES"
    else:
        sortMethod = "CNT"
    # 順序　d(esc/降順/大きいものから) もしくは a(sc/昇順/小さいものから)
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    # ページ番号 : 1番始まり
    page = request.args.get('page', default=1, type=int)
    if page < 1:
        page = 1
    page -= 1
    datas = g.db.get(
        f"SELECT artistID,artistName,artistDescription,groupName,pixivID,twitterID,mastodon,homepage,CNT,LIKES,LAST_UPDATE FROM info_artist NATURAL JOIN ( SELECT artistID,COUNT(artistID) AS CNT, SUM(illustLike) AS LIKES, MAX(illustID) AS LAST_UPDATE FROM data_illust GROUP BY artistID ) AS T1 ORDER BY {sortMethod} {order} LIMIT 20 OFFSET {page*20}")
    ls = [{
        "id": d[0],
        "name": d[1],
        "description": d[2],
        "group": d[3],
        "pixivID": d[4],
        "twitterID": d[5],
        "mastodon": d[6],
        "homepage": d[7],
        "endpoint": "https://***REMOVED***",
        "count": d[8],
        "lcount": int(d[9])
    } for d in datas]
    return jsonify(status=200, data=ls)


@catalog_api.route('/tags', methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def listTags():
    # ソート : c(ount) もしくは d(ate)
    sortMethod = request.args.get('sort', default="c", type=str)
    if sortMethod == "d":
        sortMethod = "LAST_UPDATE"
    elif sortMethod == "l":
        sortMethod = "LIKES"
    else:
        sortMethod = "CNT"
    # 順序　d(esc/降順/大きいものから) もしくは a(sc/昇順/小さいものから)
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    # ページ番号 : 1番始まり
    page = request.args.get('page', default=1, type=int)
    if page < 1:
        page = 1
    page -= 1
    datas = g.db.get(
        f"SELECT tagID,tagName,tagDescription,tagNsfw,CNT,LIKES,LAST_UPDATE FROM info_tag NATURAL JOIN ( SELECT tagID, COUNT(tagID) AS CNT, MAX(illustID) AS LAST_UPDATE FROM data_tag NATURAL JOIN info_tag GROUP BY tagID) AS T1 NATURAL JOIN ( SELECT tagID, SUM(illustLike) AS LIKES FROM data_illust NATURAL JOIN data_tag GROUP BY tagID ) AS T2 WHERE tagType=0  ORDER BY {sortMethod} {order} LIMIT 20 OFFSET {page*20}")
    ls = [{
        "id": d[0],
        "name": d[1],
        "description": d[2],
        "nsfw": d[3],
        "endpoint": "https://***REMOVED***",
        "count": d[4],
        "lcount": int(d[5])
    } for d in datas]
    return jsonify(status=200, data=ls)


@catalog_api.route('/characters', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def listCharacters():
    # ソート : c(ount) もしくは d(ate) もしくは l(ikes)
    sortMethod = request.args.get('sort', default="c", type=str)
    if sortMethod == "d":
        sortMethod = "LAST_UPDATE"
    elif sortMethod == "l":
        sortMethod = "LIKES"
    else:
        sortMethod = "CNT"
    # 順序　d(esc/降順/大きいものから) もしくは a(sc/昇順/小さいものから)
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    # ページ番号 : 1番始まり
    page = request.args.get('page', default=1, type=int)
    if page < 1:
        page = 1
    page -= 1
    datas = g.db.get(
        f"SELECT tagID,tagName,tagDescription,tagNsfw,CNT,LIKES,LAST_UPDATE FROM info_tag NATURAL JOIN ( SELECT tagID, COUNT(tagID) AS CNT, MAX(illustID) AS LAST_UPDATE FROM data_tag NATURAL JOIN info_tag GROUP BY tagID) AS T1 NATURAL JOIN ( SELECT tagID, SUM(illustLike) AS LIKES FROM data_illust NATURAL JOIN data_tag GROUP BY tagID ) AS T2 WHERE tagType=1  ORDER BY {sortMethod} {order} LIMIT 20 OFFSET {page*20}")
    ls = [{
        "id": d[0],
        "name": d[1],
        "description": d[2],
        "nsfw": d[3],
        "count": d[4],
        "lcount": int(d[5])
    } for d in datas]
    return jsonify(status=200, data=ls)
