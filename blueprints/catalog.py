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
    '''
    REQ
     sort=c(ount)/d(ate)/l(ikes)
     order=d(esc)/a(sc)
     page=1
    '''
    per_page = 20
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    sortDict = {
        "d": "LAST_UPDATE",
        "l": "LIKES",
        "c": "CNT"
    }
    sortMethod = request.args.get('sort', default="c", type=str)
    sortMethod = sortDict[sortMethod] if sortMethod in sortDict.keys() else "CNT"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    artistCount = g.db.get(
        "SELECT COUNT(DISTINCT artistID) FROM data_illust"
    )[0][0]
    pages, extra_page = divmod(artistCount, per_page)
    if extra_page > 0:
        pages += 1
    datas = g.db.get(
        "SELECT artistID,artistName,artistDescription,groupName,"
        + "pixivID,twitterID,mastodon,homepage,CNT,LIKES,LAST_UPDATE "
        + "FROM info_artist NATURAL JOIN ( SELECT artistID,COUNT(artistID) AS CNT,"
        + "SUM(illustLike) AS LIKES,"
        + "MAX(illustID) AS LAST_UPDATE "
        + "FROM data_illust GROUP BY artistID ) AS T1 "
        + f"ORDER BY {sortMethod} {order} "
        + f"LIMIT {per_page} OFFSET {per_page*(pageID-1)}"
    )
    # ないとページ番号が不正なときに爆発する
    if not len(datas):
        return jsonify(status=404, message="No matched artists.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": "絵師",
            "count": artistCount,
            "current": pageID,
            "pages": pages,
            "contents": [{
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
        }
    )


@catalog_api.route('/tags', methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def listTags():
    '''
    REQ
     sort=c(ount)/d(ate)/l(ikes)
     order=d(esc)/a(sc)
     page=1
    '''
    per_page = 20
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    sortDict = {
        "d": "LAST_UPDATE",
        "l": "LIKES",
        "c": "CNT"
    }
    sortMethod = request.args.get('sort', default="c", type=str)
    sortMethod = sortDict[sortMethod] if sortMethod in sortDict.keys() else "CNT"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    tagCount = g.db.get(
        "SELECT COUNT(DISTINCT tagID) FROM data_tag NATURAL JOIN info_tag WHERE tagType = 0"
    )[0][0]
    pages, extra_page = divmod(tagCount, per_page)
    if extra_page > 0:
        pages += 1
    datas = g.db.get(
        "SELECT tagID,tagName,tagDescription,tagNsfw,CNT,LIKES,LAST_UPDATE"
        + " FROM info_tag NATURAL JOIN ( SELECT tagID, COUNT(tagID) AS CNT,"
        + " MAX(illustID) AS LAST_UPDATE FROM data_tag NATURAL JOIN info_tag"
        + " GROUP BY tagID) AS T1 NATURAL JOIN"
        + " ( SELECT tagID, SUM(illustLike) AS LIKES FROM data_illust"
        + " NATURAL JOIN data_tag GROUP BY tagID ) AS T2"
        + f" WHERE tagType=0  ORDER BY {sortMethod} {order}"
        + f" LIMIT {per_page} OFFSET {per_page*(pageID-1)}"
    )
    # ないとページ番号が不正なときに爆発する
    if not len(datas):
        return jsonify(status=404, message="No matched tags.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": "タグ",
            "count": tagCount,
            "current": pageID,
            "pages": pages,
            "contents": [{
                "id": d[0],
                "name": d[1],
                "description": d[2],
                "nsfw": d[3],
                "endpoint": "https://***REMOVED***",
                "count": d[4],
                "lcount": int(d[5])
            } for d in datas]
        }
    )


@catalog_api.route('/characters', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def listCharacters():
    '''
    REQ
     sort=c(ount)/d(ate)/l(ikes)
     order=d(esc)/a(sc)
     page=1
    '''
    per_page = 20
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    sortDict = {
        "d": "LAST_UPDATE",
        "l": "LIKES",
        "c": "CNT"
    }
    sortMethod = request.args.get('sort', default="c", type=str)
    sortMethod = sortDict[sortMethod] if sortMethod in sortDict.keys() else "CNT"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    tagCount = g.db.get(
        "SELECT COUNT(DISTINCT tagID) FROM data_tag NATURAL JOIN info_tag WHERE tagType = 1"
    )[0][0]
    pages, extra_page = divmod(tagCount, per_page)
    if extra_page > 0:
        pages += 1
    datas = g.db.get(
        "SELECT tagID,tagName,tagDescription,tagNsfw,"
        + " CNT,LIKES,LAST_UPDATE FROM info_tag"
        + " NATURAL JOIN ( SELECT tagID, COUNT(tagID) AS CNT,"
        + " MAX(illustID) AS LAST_UPDATE FROM data_tag"
        + " NATURAL JOIN info_tag GROUP BY tagID) AS T1"
        + " NATURAL JOIN ( SELECT tagID, SUM(illustLike) AS LIKES"
        + " FROM data_illust NATURAL JOIN data_tag GROUP BY tagID ) AS T2"
        + " WHERE tagType=1"
        + f" ORDER BY {sortMethod} {order}"
        + f" LIMIT {per_page} OFFSET {per_page*(pageID-1)}"
    )
    # ないとページ番号が不正なときに爆発する
    if not len(datas):
        return jsonify(status=404, message="No matched tags.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": "キャラ",
            "count": tagCount,
            "current": pageID,
            "pages": pages,
            "contents": [{
                "id": d[0],
                "name": d[1],
                "description": d[2],
                "nsfw": d[3],
                "count": d[4],
                "lcount": int(d[5])
            } for d in datas]
        }
    )
