from flask import Blueprint, g, request, jsonify, escape
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest

search_api = Blueprint('search_api', __name__)

#
# 検索結果画面 関連 (キーワード/タグ/作者/キャラ/画像 とかは全部パラメータで取る)
#

@search_api.route("/tag",methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def searchByTag():
    '''
    REQ
     tagID=1,
     sort=d/l,
     order=d/a,
     page=1
    '''
    per_page = 20
    pageID = request.args.get('page', default = 1, type = int)
    if pageID < 1:
        pageID = 1
    tagID = request.args.get('id', default = None, type = int)
    if not tagID:
        return jsonify(status=400, message="tagID is required.")
    sortMethod = request.args.get('sort', default = "d", type = str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default = "d", type = str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_tag WHERE tagID = ?",
        (tagID,)
    )
    if not len(illustCount):
        return jsonify(status=404, message="No matched illusts.")
    illustCount = illustCount[0][0]
    tagName = g.db.get(
        "SELECT tagName FROM info_tag WHERE tagID = ?",
        (tagID,)
    )[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID,data_illust.artistID,illustName,illustDescription,"\
        + "illustDate,illustPage,illustLike,"\
        + "illustOriginUrl,illustOriginSite,artistName "\
        + "FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID "\
        + "WHERE illustID IN "\
        + "(SELECT illustID FROM data_tag WHERE tagID=?) "\
        + "ORDER BY %s %s "%(sortMethod, order)\
        + "LIMIT %s OFFSET %s"%(per_page, per_page*(pageID-1)),
        (tagID,)
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": "タグから検索 "+tagName,
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs":[{
                    "illustID": i[0],
                    "artistID": i[1],
                    "title": i[2],
                    "caption": i[3],
                    "date": i[4],
                    "pages": i[5],
                    "like": i[6],
                    "originUrl": i[7],
                    "originService": i[8],
                    "artist": {
                        "name": i[9]
                    },
            } for i in illusts]
        })
    
@search_api.route("/artist",methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def searchByArtist():
    '''
    REQ
     artistID=1,
     sort=d/l,
     order=d/a,
     page=1
    '''
    per_page = 20
    pageID = request.args.get('page', default = 1, type = int)
    if pageID < 1:
        pageID = 1
    artistID = request.args.get('id', default = None, type = int)
    if not artistID:
        return jsonify(status=400, message="artistID is required.")
    sortMethod = request.args.get('sort', default = "d", type = str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default = "d", type = str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_illust WHERE artistID = ?",
        (artistID,)
    )
    if not len(illustCount):
        return jsonify(status=404, message="No matched illusts.")
    illustCount = illustCount[0][0]
    artistName = g.db.get(
        "SELECT artistName FROM info_artist WHERE artistID = ?",
        (artistID,)
    )[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID,data_illust.artistID,illustName,illustDescription,"\
        + "illustDate,illustPage,illustLike,"\
        + "illustOriginUrl,illustOriginSite,artistName "\
        + "FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID "\
        + "WHERE data_illust.artistID = ? "\
        + "ORDER BY %s %s "%(sortMethod, order)\
        + "LIMIT %s OFFSET %s"%(per_page, per_page*(pageID-1)),
        (artistID,)
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": "絵師さんから検索 "+artistName,
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs":[{
                    "illustID": i[0],
                    "artistID": i[1],
                    "title": i[2],
                    "caption": i[3],
                    "date": i[4],
                    "pages": i[5],
                    "like": i[6],
                    "originUrl": i[7],
                    "originService": i[8],
                    "artist": {
                        "name": i[9]
                    },
            } for i in illusts]
        })
    
@search_api.route("/character",methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def searchByCharacter():
    '''
    REQ
     charaID=1,
     sort=d/l
     order=d/a,
     page=1
    '''
    per_page = 20
    pageID = request.args.get('page', default = 1, type = int)
    if pageID < 1:
        pageID = 1
    charaID = request.args.get('id', default = None, type = int)
    if not charaID:
        return jsonify(status=400, message="charaID is required.")
    sortMethod = request.args.get('sort', default = "d", type = str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default = "d", type = str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_tag WHERE tagID = ?",
        (charaID,)
    )
    if not len(illustCount):
        return jsonify(status=404, message="No matched illusts.")
    illustCount = illustCount[0][0]
    charaName = g.db.get(
        "SELECT tagName FROM info_tag WHERE tagID = ?",
        (charaID,)
    )[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID,data_illust.artistID,illustName,illustDescription,"\
        + "illustDate,illustPage,illustLike,"\
        + "illustOriginUrl,illustOriginSite,artistName "\
        + "FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID "\
        + "WHERE illustID IN "\
        + "(SELECT illustID FROM data_tag WHERE tagID=?) "\
        + "ORDER BY %s %s "%(sortMethod, order)\
        + "LIMIT %s OFFSET %s"%(per_page, per_page*(pageID-1)),
        (charaID,)
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": "キャラクターから検索 "+charaName,
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs":[{
                    "illustID": i[0],
                    "artistID": i[1],
                    "title": i[2],
                    "caption": i[3],
                    "date": i[4],
                    "pages": i[5],
                    "like": i[6],
                    "originUrl": i[7],
                    "originService": i[8],
                    "artist": {
                        "name": i[9]
                    },
            } for i in illusts]
        })
        
@search_api.route("/keyword",methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def searchByKeyword():
    '''
    REQ
     keyword=1,
     sort=d/l
     order=d/a,
     page=1
    '''
    per_page = 20
    pageID = request.args.get('page', default = 1, type = int)
    if pageID < 1:
        pageID = 1
    keyword = request.args.get('keyword', default = None, type = str)
    if not keyword:
        return jsonify(status=400, message="keyword is required.")
    sortMethod = request.args.get('sort', default = "d", type = str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default = "d", type = str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_illust "\
        + "WHERE illustName LIKE ?",
        ("%"+keyword+"%",)
    )
    if not len(illustCount):
        return jsonify(status=404, message="No matched illusts.")
    illustCount = illustCount[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
		"SELECT illustID,data_illust.artistID,illustName,illustDescription,"\
        + "illustDate,illustPage,illustLike,"\
        + "illustOriginUrl,illustOriginSite,artistName "\
        + "FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID "\
        + "WHERE illustName LIKE ?"\
        + "ORDER BY %s %s "%(sortMethod, order)\
        + "LIMIT %s OFFSET %s"%(per_page, per_page*(pageID-1)),
        ("%"+keyword+"%",)
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": "キーワードから検索 "+keyword,
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs":[{
                    "illustID": i[0],
                    "artistID": i[1],
                    "title": i[2],
                    "caption": i[3],
                    "date": i[4],
                    "pages": i[5],
                    "like": i[6],
                    "originUrl": i[7],
                    "originService": i[8],
                    "artist": {
                        "name": i[9]
                    },
            } for i in illusts]
        })

@search_api.route('/all',methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def searchByAll():
    '''
    REQ
     keyword=1,
     sort=d/l
     order=d/a,
     page=1
    '''
    per_page = 20
    pageID = request.args.get('page', default = 1, type = int)
    if pageID < 1:
        pageID = 1
    sortMethod = request.args.get('sort', default = "d", type = str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default = "d", type = str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_illust"
    )
    if not len(illustCount):
        return jsonify(status=404, message="No matched illusts.")
    illustCount = illustCount[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
		"SELECT illustID,data_illust.artistID,illustName,illustDescription,"\
        + "illustDate,illustPage,illustLike,"\
        + "illustOriginUrl,illustOriginSite,artistName "\
        + "FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID "\
        + "ORDER BY %s %s "%(sortMethod, order)\
        + "LIMIT %s OFFSET %s"%(per_page, per_page*(pageID-1))
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": "全て",
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs":[{
                    "illustID": i[0],
                    "artistID": i[1],
                    "title": i[2],
                    "caption": i[3],
                    "date": i[4],
                    "pages": i[5],
                    "like": i[6],
                    "originUrl": i[7],
                    "originService": i[8],
                    "artist": {
                        "name": i[9]
                    },
            } for i in illusts]
        })