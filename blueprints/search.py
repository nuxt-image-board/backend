from flask import Blueprint, g, request, jsonify, escape, current_app
from .authorizator import auth, token_serializer
from .limiter import apiLimiter, handleApiPermission
from .recorder import recordApiRequest
from .lib.saucenao_client import SauceNaoImageSearch
import json
from PIL import Image
import imagehash
from tempfile import TemporaryDirectory
from base64 import b64encode
from uuid import uuid4
import os.path
from imghdr import what as what_img

ALLOWED_EXTENSIONS = ["gif", "png", "jpg", "jpeg", "webp"]


def isNotAllowedFile(filename):
    if filename == ""\
        or '.' not in filename\
        or (filename.rsplit('.', 1)[1].lower()
            not in ALLOWED_EXTENSIONS):
        return True
    return False


search_api = Blueprint('search_api', __name__)

#
# 検索結果画面 関連 (キーワード/タグ/作者/キャラ/画像 とかは全部パラメータで取る)
#


@search_api.route("/tag", methods=["GET"])
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
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    tagID = request.args.get('id', default=None, type=int)
    if not tagID:
        return jsonify(status=400, message="tagID is required.")
    sortMethod = request.args.get('sort', default="d", type=str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_tag WHERE tagID = %s",
        (tagID,)
    )
    illustCount = illustCount[0][0]
    if illustCount == 0:
        return jsonify(status=404, message="No matched illusts.")
    tagName = g.db.get(
        "SELECT tagName FROM info_tag WHERE tagID = %s",
        (tagID,)
    )[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID,data_illust.artistID,illustName,illustDescription,"
        + "illustDate,illustPage,illustLike,"
        + "illustOriginUrl,illustOriginSite,illustNsfw,artistName "
        + "FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID "
        + "WHERE illustID IN "
        + "(SELECT illustID FROM data_tag WHERE tagID=%s) "
        + "ORDER BY %s %s " % (sortMethod, order)
        + "LIMIT %s OFFSET %s" % (per_page, per_page*(pageID-1)),
        (tagID,)
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": tagName,
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs": [{
                "illustID": i[0],
                "artistID": i[1],
                "title": i[2],
                "caption": i[3],
                "date": i[4].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[5],
                "like": i[6],
                "originUrl": i[7],
                "originService": i[8],
                "nsfw": i[9],
                "artist": {
                    "name": i[10]
                },
            } for i in illusts]
        }
    )


@search_api.route("/artist", methods=["GET"])
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
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    artistID = request.args.get('id', default=None, type=int)
    if not artistID:
        return jsonify(status=400, message="artistID is required.")
    sortMethod = request.args.get('sort', default="d", type=str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_illust WHERE artistID = %s",
        (artistID,)
    )
    illustCount = illustCount[0][0]
    if illustCount == 0:
        return jsonify(status=404, message="No matched illusts.")
    artistName = g.db.get(
        "SELECT artistName FROM info_artist WHERE artistID = %s",
        (artistID,)
    )[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID,data_illust.artistID,illustName,illustDescription,"
        + "illustDate,illustPage,illustLike,"
        + "illustOriginUrl,illustOriginSite,illustNsfw,artistName "
        + "FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID "
        + "WHERE data_illust.artistID = %s "
        + "ORDER BY %s %s " % (sortMethod, order)
        + "LIMIT %s OFFSET %s" % (per_page, per_page*(pageID-1)),
        (artistID,)
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": artistName,
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs": [{
                "illustID": i[0],
                "artistID": i[1],
                "title": i[2],
                "caption": i[3],
                "date": i[4].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[5],
                "like": i[6],
                "originUrl": i[7],
                "originService": i[8],
                "nsfw": i[9],
                "artist": {
                    "name": i[10]
                },
            } for i in illusts]
        })


@search_api.route("/character", methods=["GET"])
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
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    charaID = request.args.get('id', default=None, type=int)
    if not charaID:
        return jsonify(status=400, message="charaID is required.")
    sortMethod = request.args.get('sort', default="d", type=str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_tag WHERE tagID = %s",
        (charaID,)
    )
    illustCount = illustCount[0][0]
    if illustCount == 0:
        return jsonify(status=404, message="No matched illusts.")
    charaName = g.db.get(
        "SELECT tagName FROM info_tag WHERE tagID = %s",
        (charaID,)
    )[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID,data_illust.artistID,illustName,illustDescription,"
        + "illustDate,illustPage,illustLike,"
        + "illustOriginUrl,illustOriginSite,illustNsfw,artistName "
        + "FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID "
        + "WHERE illustID IN "
        + "(SELECT illustID FROM data_tag WHERE tagID=%s) "
        + "ORDER BY %s %s " % (sortMethod, order)
        + "LIMIT %s OFFSET %s" % (per_page, per_page*(pageID-1)),
        (charaID,)
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": charaName,
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs": [{
                "illustID": i[0],
                "artistID": i[1],
                "title": i[2],
                "caption": i[3],
                "date": i[4].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[5],
                "like": i[6],
                "originUrl": i[7],
                "originService": i[8],
                "nsfw": i[9],
                "artist": {
                    "name": i[10]
                },
            } for i in illusts]
        })


@search_api.route("/keyword", methods=["GET"])
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
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    keyword = request.args.get('keyword', default=None, type=str)
    if not keyword:
        return jsonify(status=400, message="keyword is required.")
    sortMethod = request.args.get('sort', default="d", type=str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_illust "
        + "WHERE illustName LIKE %s",
        ("%"+keyword+"%",)
    )
    illustCount = illustCount[0][0]
    if illustCount == 0:
        return jsonify(status=404, message="No matched illusts.")
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID,data_illust.artistID,illustName,illustDescription,"
        + "illustDate,illustPage,illustLike,"
        + "illustOriginUrl,illustOriginSite,illustNsfw,artistName "
        + "FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID "
        + "WHERE illustName LIKE %s"
        + "ORDER BY %s %s " % (sortMethod, order)
        + "LIMIT %s OFFSET %s" % (per_page, per_page*(pageID-1)),
        ("%"+keyword+"%",)
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    return jsonify(
        status=200,
        message="found",
        data={
            "title": keyword,
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs": [{
                "illustID": i[0],
                "artistID": i[1],
                "title": i[2],
                "caption": i[3],
                "date": i[4].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[5],
                "like": i[6],
                "originUrl": i[7],
                "originService": i[8],
                "nsfw":i[9],
                "artist": {
                    "name": i[10]
                },
            } for i in illusts]
        })


@search_api.route('/all', methods=["GET"], strict_slashes=False)
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
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    sortMethod = request.args.get('sort', default="d", type=str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_illust"
    )
    illustCount = illustCount[0][0]
    if illustCount == 0:
        return jsonify(status=404, message="No matched illusts.")
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID,data_illust.artistID,illustName,illustDescription,"
        + "illustDate,illustPage,illustLike,"
        + "illustOriginUrl,illustOriginSite,illustNsfw,artistName "
        + "FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID "
        + "ORDER BY %s %s " % (sortMethod, order)
        + "LIMIT %s OFFSET %s" % (per_page, per_page*(pageID-1))
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
            "imgs": [{
                "illustID": i[0],
                "artistID": i[1],
                "title": i[2],
                "caption": i[3],
                "date": i[4].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[5],
                "like": i[6],
                "originUrl": i[7],
                "originService": i[8],
                "nsfw": i[9],
                "artist": {
                    "name": i[10]
                },
            } for i in illusts]
        })


@search_api.route('/random', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def searchByRandom():
    '''
    REQ
        nsfw= 1/0
        artistID=NUMBER
        tagID=NUMBER
        charaID=NUMBER
    '''
    acceptNsfw = request.args.get('nsfw', default=0, type=int)
    artistID = request.args.get('artistID', default=0, type=int)
    tagID = request.args.get('tagID', default=0, type=int)
    charaID = request.args.get('charaID', default=0, type=int)
    count = request.args.get('count', default=1, type=int)
    if acceptNsfw:
        acceptNsfw = 1
    if count > 10:
        count = 10
    # 完全ランダム
    if (not artistID) and (not tagID) and (not charaID):
        illusts = g.db.get(
            "SELECT illustID, data_illust.artistID,"
            + " illustName, illustDescription,"
            + " illustDate, illustPage, illustLike, illustOriginUrl,"
            + " illustOriginSite, illustNsfw, artistName"
            + " FROM `data_illust` INNER JOIN info_artist"
            + " ON info_artist.artistID = data_illust.artistID"
            + f" WHERE illustNsfw={acceptNsfw} ORDER BY RAND() LIMIT {count}"
        )
    # 作者指定ランダム
    elif artistID:
        illusts = g.db.get(
            "SELECT illustID, data_illust.artistID,"
            + " illustName, illustDescription,"
            + " illustDate, illustPage, illustLike, illustOriginUrl,"
            + " illustOriginSite, illustNsfw, artistName"
            + " FROM `data_illust` INNER JOIN info_artist"
            + " ON info_artist.artistID = data_illust.artistID"
            + f" WHERE illustNsfw={acceptNsfw}"
            + f" AND data_illust.artistID={artistID}"
            + f" ORDER BY RAND() LIMIT {count}"
        )
    # タグ指定ランダム
    # キャラ指定ランダム
    else:
        # つまりタグIDなので握りつぶす
        if charaID:
            tagID = charaID
        illusts = g.db.get(
            "SELECT illustID, data_illust.artistID,"
            + " illustName, illustDescription,"
            + " illustDate, illustPage, illustLike, illustOriginUrl,"
            + " illustOriginSite, illustNsfw, artistName"
            + " FROM `data_illust` INNER JOIN info_artist"
            + " ON info_artist.artistID = data_illust.artistID"
            + " WHERE illustID IN"
            + f" (SELECT illustID FROM data_tag WHERE tagID={tagID})"
            + f" AND illustNsfw={acceptNsfw} ORDER BY RAND() LIMIT {count}"
        )
    if not illusts:
        return jsonify(404, message="No matched arts.")
    return jsonify(
        status=200,
        message="found",
        data={
            "imgs": [{
                "illustID": illust[0],
                "artistID": illust[1],
                "title": illust[2],
                "caption": illust[3],
                "date": illust[4],
                "pages": illust[5],
                "like": illust[6],
                "originUrl": illust[7],
                "originService": illust[8],
                "nsfw": illust[9],
                "artist": {
                    "name": illust[10]
                }
            } for illust in illusts]
        }
    )


@search_api.route('/image/saucenao', methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def searchByImageAtSauceNao():
    if "file" not in request.files:
        return jsonify(status=400, message="File must be included")
    file = request.files['file']
    # ファイル拡張子確認
    if isNotAllowedFile(file.filename):
        return jsonify(status=400, message="The file is not allowed")
    with TemporaryDirectory() as temp_path:
        # 画像を一旦保存して確認
        uniqueID = str(uuid4()).replace("-", "")
        uniqueID = b64encode(uniqueID.encode("utf8")).decode("utf8")[:-1]
        tempPath = os.path.join(temp_path, uniqueID)
        file.save(tempPath)
        fileExt = what_img(tempPath)
        if not fileExt:
            return jsonify(status=400, message="The file is not allowed")
        cl = SauceNaoImageSearch(
            current_app.config['imgurToken'],
            current_app.config['saucenaoToken']
        )
        result = cl.search(tempPath)
        return jsonify(
            status=200,
            message='ok',
            data={
                'result': result
            }
        )


@search_api.route('/image', methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def searchByImage():
    if "file" not in request.files:
        return jsonify(status=400, message="File must be included")
    file = request.files['file']
    # ファイル拡張子確認
    if isNotAllowedFile(file.filename):
        return jsonify(status=400, message="The file is not allowed")
    with TemporaryDirectory() as temp_path:
        # 画像を一旦保存して確認
        uniqueID = str(uuid4()).replace("-", "")
        uniqueID = b64encode(uniqueID.encode("utf8")).decode("utf8")[:-1]
        tempPath = os.path.join(temp_path, uniqueID)
        file.save(tempPath)
        fileExt = what_img(tempPath)
        if not fileExt:
            return jsonify(status=400, message="The file is not allowed")
        # 大丈夫そうなのでハッシュ値を作成して検索
        hash = int(str(imagehash.phash(Image.open(tempPath))), 16)
        # 検索SQL
        illusts = g.db.get(
            "SELECT illustID, data_illust.artistID, BIT_COUNT(illustHash ^ %s) AS SAME, illustName, illustDescription, illustDate, illustPage, illustLike, illustOriginUrl, illustOriginSite, illustNsfw, artistName FROM `data_illust` INNER JOIN info_artist ON info_artist.artistID = data_illust.artistID HAVING SAME < 5 ORDER BY SAME DESC LIMIT 10",
            (hash,)
        )
        if len(illusts):
            illusts = [{
                "illustID": i[0],
                "artistID": i[1],
                "similarity": i[2],
                "title": i[3],
                "caption": i[4],
                "date": i[5].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[6],
                "like": i[7],
                "originUrl": i[8],
                "originService": i[9],
                "nsfw": i[10],
                "artist": {
                    "name": i[11]
                }
            } for i in illusts]
        else:
            illusts = []
        # データベースから検索
        return jsonify(
            status=200,
            message='ok',
            data={
                'hash': str(hash),
                'illusts': illusts
            }
        )
