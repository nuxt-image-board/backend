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
    print(tagID,type(tagID))
    sortMethod = request.args.get('sort', default = "d", type = str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default = "d", type = str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM illust_tag WHERE tagID = ?",
        (tagID,)
    )
    if not len(illustCount):
        return jsonify(status=404, message="No matched illusts.")
    illustCount = illustCount[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID,artistID,illustName,illustDescription,"\
        + "illustDate,illustPage,illustLike,"\
        + "illustOriginUrl,illustOriginSite,artistName,artistIcon "\
        + "FROM illust_main NATURAL JOIN info_artist "\
        + "WHERE illustID = "\
        + "(SELECT illustID FROM illust_tag WHERE tagID=?) "\
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
            "count": illustCount,
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
                        "name": i[9],
                        "icon": i[10],
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
        "SELECT COUNT(illustID) FROM illust_main WHERE artistID = ?",
        (artistID,)
    )
    if not len(illustCount):
        return jsonify(status=404, message="No matched illusts.")
    illustCount = illustCount[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID,artistID,illustName,illustDescription,"\
        + "illustDate,illustPage,illustLike,"\
        + "illustOriginUrl,illustOriginSite,artistName,artistIcon "\
        + "FROM illust_main NATURAL JOIN info_artist "\
        + "WHERE artistID = ? "\
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
            "count": illustCount,
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
                        "name": i[9],
                        "icon": i[10],
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
        "SELECT COUNT(illustID) FROM illust_chara WHERE charaID = ?",
        (charaID,)
    )
    if not len(illustCount):
        return jsonify(status=404, message="No matched illusts.")
    illustCount = illustCount[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
		"SELECT illustID,artistID,illustName,illustDescription,"\
        + "illustDate,illustPage,illustLike,"\
        + "illustOriginUrl,illustOriginSite,artistName,artistIcon "\
        + "FROM illust_main NATURAL JOIN info_artist "\
        + "WHERE illustID = "\
        + "(SELECT illustID FROM illust_chara WHERE charaID=?) "\
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
            "count": illustCount,
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
                        "name": i[9],
                        "icon": i[10],
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
        "SELECT COUNT(illustID) FROM illust_main "\
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
		"SELECT illustID,artistID,illustName,illustDescription,"\
        + "illustDate,illustPage,illustLike,"\
        + "illustOriginUrl,illustOriginSite,artistName,artistIcon "\
        + "FROM illust_main NATURAL JOIN info_artist "\
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
            "count": illustCount,
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
                        "name": i[9],
                        "icon": i[10],
                    },
            } for i in illusts]
        })

@search_api.route('/',methods=["GET"], strict_slashes=False)
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
        "SELECT COUNT(illustID) FROM illust_main"
    )
    if not len(illustCount):
        return jsonify(status=404, message="No matched illusts.")
    illustCount = illustCount[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
		"SELECT illustID,artistID,illustName,illustDescription,"\
        + "illustDate,illustPage,illustLike,"\
        + "illustOriginUrl,illustOriginSite,artistName,artistIcon "\
        + "FROM illust_main NATURAL JOIN info_artist "\
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
            "count": illustCount,
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
                        "name": i[9],
                        "icon": i[10],
                    },
            } for i in illusts]
        })