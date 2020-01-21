from flask import Blueprint, request, g, jsonify
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
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
    sortMethod = request.args.get('sort', default = "c", type = str)
    sortMethod = "CNT" if sortMethod == "c" else "artistID"
    # 順序　d(esc/降順/大きいものから) もしくは a(sc/昇順/小さいものから)
    order = request.args.get('order', default = "d", type = str)
    order = "DESC" if order == "d" else "ASC"
    # ページ番号 : 1番始まり
    page = request.args.get('page', default = 1, type = int)
    if page < 1:
        page = 1
    page -= 1
    # 一旦 artistID, COUNT(artistID)を実行してそれに対して繋げて引き出している(少し最適なSQL)
    datas = g.db.get(f"SELECT artistID,artistName,artistDescription,artistIcon,groupName,pixivID,pixiv,twitterID,twitter,mastodon,homepage,artistEndpoint,CNT,LIKES FROM (SELECT * FROM info_artist NATURAL JOIN (SELECT artistID,COUNT(artistID) AS CNT, TOTAL(illustLike) AS LIKES FROM illust_main GROUP BY artistID ORDER BY {sortMethod} {order})) LIMIT 20 OFFSET {page*20}")
    ls = [{
        "id": d[0],
        "name": d[1],
        "description": d[2],
        "icon": d[3],
        "group": d[4],
        "pixivID": d[5],
        "pixiv": d[6],
        "twitterID": d[7],
        "twitter": d[8],
        "mastodon": d[9],
        "homepage": d[10],
        "endpoint": "https://***REMOVED***",
        "count": d[11],
        "lcount": int(d[12])
    } for d in datas]
    return jsonify(status=200, data=ls)

@catalog_api.route('/tags', methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def listTags():
    #　ソート : c(ount) もしくは d(ate)
    sortMethod = request.args.get('sort', default = "c", type = str)
    sortMethod = "CNT" if sortMethod == "c" else "tagID"
    # 順序　d(esc/降順/大きいものから) もしくは a(sc/昇順/小さいものから)
    order = request.args.get('order', default = "d", type = str)
    order = "DESC" if order == "d" else "ASC"
    # ページ番号 : 1番始まり
    page = request.args.get('page', default = 1, type = int)
    if page < 1:
        page = 1
    page -= 1
    datas = g.db.get(f"SELECT tagID,tagName,tagDescription,nsfw,CNT FROM (SELECT * FROM info_tag NATURAL JOIN (SELECT tagName,count(tagID) AS CNT FROM illust_tag NATURAL JOIN info_tag GROUP BY tagID ORDER BY {sortMethod} {order})) LIMIT 20 OFFSET {page*20}")
    ls = [{
        "id": d[0],
        "name": d[1],
        "description": d[2],
        "nsfw": d[3],
        "endpoint": "https://***REMOVED***",
        "count": d[4]
    } for d in datas]
    return jsonify(status=200, data=ls)

@catalog_api.route('/characters', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def listCharacters():
    #　ソート : c(ount) もしくは d(ate) もしくは l(ikes)
    sortMethod = request.args.get('sort', default = "c", type = str)
    if sortMethod == "d":
        sortMethod = "LAST_UPDATE"
    elif sortMethod == "l":
        sortMethod = "LIKES"
    else:
        sortMethod = "CNT"
    # 順序　d(esc/降順/大きいものから) もしくは a(sc/昇順/小さいものから)
    order = request.args.get('order', default = "d", type = str)
    order = "DESC" if order == "d" else "ASC"
    # ページ番号 : 1番始まり
    page = request.args.get('page', default = 1, type = int)
    if page < 1:
        page = 1
    page -= 1
    datas = g.db.get(f"SELECT charaID,charaName,charaDescription,charaBackground,charaIcon,charaBirthday,charaEndpoint,CNT,LIKES,LAST_UPDATE FROM info_chara NATURAL JOIN ( SELECT charaID, COUNT(charaID) AS CNT FROM illust_chara NATURAL JOIN info_chara GROUP BY charaID ) NATURAL JOIN ( SELECT charaID, TOTAL(illustLike) AS LIKES FROM illust_main NATURAL JOIN illust_chara GROUP BY charaID ) NATURAL JOIN ( SELECT charaID, MAX(illustID) AS LAST_UPDATE FROM illust_chara GROUP BY charaID ) ORDER BY {sortMethod} {order} LIMIT 20 OFFSET {page*20}")
    ls = [{
        "id": d[0],
        "name": d[1],
        "description": d[2],
        "bg": d[3],
        "icon": d[4],
        "birthday": d[5],
        "endpoint": d[6],
        "count": d[7],
        "lcount": d[8]
    } for d in datas]
    return jsonify(status=200, data=ls)